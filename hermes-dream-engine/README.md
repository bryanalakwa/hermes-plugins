# Dream Engine

Autonomous idle-time dreaming for Hermes Agent. When you're away, the agent enters sleep-like states and runs LLM-driven dream sessions: consolidating memories, re-evaluating free associations, and surfacing insights — all without being asked.

## What It Does

- **Event-driven state machine**: Active → Idle → Dormant → Hypnagogic → Dreaming
- **LLM-driven dream phases**: Memory consolidation, problem re-evaluation, free association &amp; invention, dream log &amp; integration
- **Telegram escalation**: High-priority items get sent to you automatically
- **Blog-style journal**: Human-readable titles, expandable detail modal in dashboard
- **Holographic fact store**: Dreams make the agent smarter over time — insights accumulate across sessions

## Install

```bash
# From the hermes-plugins repo root:
cd hermes-dream-engine/
chmod +x install.sh
./install.sh
systemctl --user restart hermes-gateway.service
```

That's it. The installer handles everything:
1. Holographic fact store setup (SQLite + FTS5)
2. Memory directories and files
3. Plugin file installation
4. Dependency installation
5. Config updates

After restart, open the **Dream Engine** tab in the dashboard (port 9119).

## Requirements

- Hermes Agent installed at `~/.hermes/hermes-agent/`
- Python 3.11+ venv
- `memory.provider: holographic` in config.yaml (set automatically by installer)

## Configuration

Config is managed through the dashboard UI (Config tab). Changes are persisted to `config.yaml` automatically.

| Parameter | Default | Description |
|---|---|---|
| `idle_threshold_seconds` | 300 | Active → Idle (5 min) |
| `dormant_threshold_seconds` | 1800 | Idle → Dormant (30 min) |
| `soak_threshold_seconds` | 3000 | Dormant soak before dream gate (50 min) |
| `hypnagogic_duration_seconds` | 120 | Pre-dream prep window (2 min) |
| `max_dreams_per_day` | 2 | Dream quota |
| `consolidation_memory_count` | 150 | Memories reviewed per dream |
| `invention_sample_size` | 10 | Random memories sampled for invention |

## Dashboard

The dashboard tab shows:
- **Status**: Current state, timer bars, dreams-today quota, recent transitions
- **Journal**: Blog-style dream entries with expandable detail modal
- **Config**: Live editing of all parameters

## How Dreaming Works

1. Agent activity keeps the state at **Active**
2. After `T1` seconds of no activity → **Idle**
3. After `T2` cumulative idle → **Dormant** (soak timer starts)
4. After `T3` soak → **Hypnagogic** (pre-dream prep, `T4` seconds)
5. → **Dreaming**: LLM runs 4 phases, writes journal entry, escalates if needed
6. Back to **Active** on next heartbeat

Max 2 dreams per day (resets at midnight). Quota is configurable.

## Files

```
~/.hermes/hermes-agent/plugins/hermes-dream-engine/  # Plugin code
~/.hermes/dream_engine/state.json                     # Runtime state
~/.hermes/dream_engine/journal.json                   # Dream journal
~/.hermes/memory_store.db                             # Holographic fact store
~/.hermes/memories/MEMORY.md                          # Agent memory
~/.hermes/memories/USER.md                            # User profile
```

## Troubleshooting

- **Plugin not showing in dashboard**: Restart gateway, then check `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9119/api/plugins/hermes-dream-engine/status` — should return 401
- **Config changes not saving**: Ensure `~/.hermes/config.yaml` is writable
- **No dreams happening**: Check the state machine — send a heartbeat via the dashboard or wait for natural idle time
