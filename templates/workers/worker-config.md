---
id: worker-config
name: ATP Worker Configuration
version: 0.1.0
status: active
classification: template
created: "2000-01-01"
last_verified: "2000-01-01"
verified_by: <agent-id>
staleness_policy: on-change-only
validator: json-config
source: config
---

# ATP Worker Configuration

## Current Value

### Model Class Assignments
| Class | Current Model | Cost ($/MTok in/out) |
|-------|--------------|----------------------|
| `fast` | `<provider/model>` | `<in>` / `<out>` |
| `balanced` | `<provider/model>` | `<in>` / `<out>` |
| `capable` | `<provider/model>` | `<in>` / `<out>` |

### T3 Cost-Efficiency Ratio
```
baseline_t3_model_cost_per_mtok_out: <baseline-value>   # Set when ATP workers were first deployed
current_t3_model_cost_per_mtok_out:  <current-value>
cost_efficiency_ratio:               <current / baseline>
```

### Derived T3 Schedule
```
base_frequency: weekly (0 3 * * 0)
frequency_multiplier: <1 / cost_efficiency_ratio>
max_frequency_multiplier: 20     # Cap on effective_multiplier = min(1/ratio, this value)
effective_schedule: <recalculated cron expression>
```

### Worker Schedules
| Worker | Trigger | Current Schedule | Session Type |
|--------|---------|-----------------|--------------|
| T1 Scanner | Cron | `<cron expression>` | isolated |
| T2 Watcher | Webhook | on push | isolated |
| T3 Validator | PR event + Cron | `<cron expression>` | session:atp-t3-validator |

### Report Retention Policy
```
clean reports: 90 days → archive, 180 days → delete
findings reports: 180 days → archive, 365 days → delete
critical escalation reports: permanent
```

## Change History

| Date | Change | Changed By | Notes |
|------|--------|------------|-------|
| YYYY-MM-DD | Initial config | <agent-id> | |

## Notes
- Update `current_t3_model_cost_per_mtok_out` and recalculate `cost_efficiency_ratio` when T3 model changes or pricing changes
- Recalculate `effective_schedule` after any ratio change and update the T3 cron job accordingly
- `baseline_t3_model_cost_per_mtok_out` is locked at initial deployment. Never update it — it is the reference point for the ratio. If updated, all historical ratio calculations become invalid.
