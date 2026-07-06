import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

// ESM-compatible __dirname shim
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * ATP Hook — handler.ts
 *
 * Implements the Agent Task Protocol (ATP) execution loop at the OpenClaw
 * hook layer. Trigger configuration is loaded from an external JSON file
 * so the hook stays portable across deployments.
 *
 * Config lookup order:
 *   1. <workspace>/atp-instance/hook-config.json   (deployment overrides)
 *        workspace = event.context.workspaceDir ||
 *                    process.env.OPENCLAW_WORKSPACE ||
 *                    process.cwd()
 *   2. Built-in default (co-located hook-config.default.json)
 *   3. Hard-coded minimal fallback (template protocols only)
 *
 * See hook-config.schema.json for the expected shape.
 */

type HookConfig = {
  protocol_triggers: Record<string, string[]>;
  state_change_indicators: string[];
};

// Hard-coded minimal fallback used only if neither the instance config nor
// the co-located default file can be loaded. Contains ONLY the two protocols
// that ship as templates in this repo — no deployment-specific vocabulary.
const BUILTIN_FALLBACK: HookConfig = {
  protocol_triggers: {
    "memory-maintenance": [
      "memory update", "memory review", "update memory.md", "daily log",
      "memory maintenance", "soul review", "morning brief", "promote to long-term",
    ],
    "atp-protocol-review": [
      "atp review", "protocol staleness", "review protocols",
      "atp maintenance", "protocol drift",
    ],
  },
  state_change_indicators: [
    "git commit", "npm publish", "docker run", "docker restart",
    "config set",
  ],
};

function resolveWorkspaceDir(eventWorkspaceDir?: string): string {
  return (
    eventWorkspaceDir ||
    process.env.OPENCLAW_WORKSPACE ||
    process.cwd()
  );
}

function isValidConfig(candidate: unknown): candidate is HookConfig {
  if (!candidate || typeof candidate !== "object") return false;
  const c = candidate as Record<string, unknown>;
  if (!c.protocol_triggers || typeof c.protocol_triggers !== "object") return false;
  if (!Array.isArray(c.state_change_indicators)) return false;
  for (const v of Object.values(c.protocol_triggers as Record<string, unknown>)) {
    if (!Array.isArray(v)) return false;
    if (!v.every(item => typeof item === "string")) return false;
  }
  if (!(c.state_change_indicators as unknown[]).every(item => typeof item === "string")) {
    return false;
  }
  return true;
}

function tryLoadJson(filePath: string): HookConfig | null {
  try {
    if (!fs.existsSync(filePath)) return null;
    const raw = fs.readFileSync(filePath, "utf8");
    const parsed = JSON.parse(raw);
    if (!isValidConfig(parsed)) {
      console.error(`[atp hook] config at ${filePath} failed schema validation; ignoring`);
      return null;
    }
    return parsed;
  } catch (err) {
    console.error(`[atp hook] failed to load config at ${filePath}:`, err);
    return null;
  }
}

let _cachedConfig: HookConfig | null = null;
let _cachedConfigSource: string | null = null;

function loadConfig(workspaceDir: string): HookConfig {
  if (_cachedConfig) return _cachedConfig;

  // 1. Instance override in the workspace
  const instancePath = path.join(workspaceDir, "atp-instance", "hook-config.json");
  const instanceConfig = tryLoadJson(instancePath);
  if (instanceConfig) {
    _cachedConfig = instanceConfig;
    _cachedConfigSource = instancePath;
    return instanceConfig;
  }

  // 2. Co-located default shipped with this hook
  const defaultPath = path.join(__dirname, "hook-config.default.json");
  const defaultConfig = tryLoadJson(defaultPath);
  if (defaultConfig) {
    _cachedConfig = defaultConfig;
    _cachedConfigSource = defaultPath;
    return defaultConfig;
  }

  // 3. Built-in fallback
  _cachedConfig = BUILTIN_FALLBACK;
  _cachedConfigSource = "<builtin-fallback>";
  return BUILTIN_FALLBACK;
}

// Exposed for tests / diagnostics
export function __resetConfigCache(): void {
  _cachedConfig = null;
  _cachedConfigSource = null;
}
export function __getConfigSource(): string | null {
  return _cachedConfigSource;
}

function classifyProtocol(content: string, config: HookConfig): string | null {
  const lower = content.toLowerCase();
  for (const [protocolId, triggers] of Object.entries(config.protocol_triggers)) {
    for (const trigger of triggers) {
      if (lower.includes(trigger.toLowerCase())) {
        return protocolId;
      }
    }
  }
  return null;
}

function detectStateChanges(content: string, config: HookConfig): string[] {
  const lower = content.toLowerCase();
  return config.state_change_indicators.filter(indicator =>
    lower.includes(indicator.toLowerCase())
  );
}

function getAtpAgentPath(workspaceDir: string): string {
  return path.join(workspaceDir, "ATP_AGENT.md");
}

const handler = async (event: any) => {
  try {
    const workspaceDir = resolveWorkspaceDir(event?.context?.workspaceDir);
    const config = loadConfig(workspaceDir);

    // ── agent:bootstrap ──────────────────────────────────────────────────────
    if (event.type === "agent" && event.action === "bootstrap") {
      if (!event.context?.workspaceDir) return;
      const atpAgentPath = getAtpAgentPath(event.context.workspaceDir);

      // Inject ATP_AGENT.md into bootstrap files if it exists and isn't already present
      if (fs.existsSync(atpAgentPath)) {
        const bootstrapFiles: string[] = event.context?.bootstrapFiles ?? [];
        if (!bootstrapFiles.includes(atpAgentPath)) {
          bootstrapFiles.push(atpAgentPath);
        }
      }
      return;
    }

    // ── message:preprocessed ─────────────────────────────────────────────────
    if (event.type === "message" && event.action === "preprocessed") {
      const content: string = event.context?.bodyForAgent ?? event.context?.content ?? "";
      if (!content) return;

      const matchedProtocol = classifyProtocol(content, config);
      if (matchedProtocol) {
        // Append a brief ATP context note to the body for the agent
        const atpNote = `\n\n<!-- ATP: Protocol match → ${matchedProtocol}. Follow ATP execution loop: validate vars → pre-load → execute → post-update. See ATP_AGENT.md. -->`;
        if (event.context) {
          event.context.bodyForAgent = (event.context.bodyForAgent ?? content) + atpNote;
        }
      }
      return;
    }

    // ── message:sent ─────────────────────────────────────────────────────────
    if (event.type === "message" && event.action === "sent") {
      const content: string = event.context?.content ?? "";
      if (!content) return;

      const changes = detectStateChanges(content, config);
      if (changes.length > 0) {
        // Log detected state changes for agent awareness on next turn
        // (Non-blocking — just surface as a note if the platform supports it)
        const changeNote = `[ATP post-execution: detected potential state changes (${changes.slice(0, 3).join(", ")}). Review and update relevant var files or create new protocol if pattern is unmatched.]`;
        console.log(changeNote);
      }
      return;
    }

  } catch (err) {
    // Never throw — let other hooks run
    console.error("[atp hook] error:", err);
  }
};

export default handler;
