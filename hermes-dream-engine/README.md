# Dream Engine — Hermes Agent Plugin

Autonomous event-driven dreaming system with 5-state sleep detection.

## States

1. **ACTIVE** — Normal operation, heartbeat timer running
2. **IDLE** — No heartbeat for T1 (5 min default)
3. **DORMANT** — No heartbeat for T2 (30 min cumulative)
4. **HYPNAGOGIC** — Pre-dream prep, T4 (2 min default)
5. **DREAMING** — Active dream session running

## Dream Session Phases

1. **Memory Consolidation** — Review recent memories, resolve contradictions
2. **Problem Re-evaluation** — Revisit unresolved problems with fresh context
3. **Free Association / Invention** — Generate novel ideas from distant memory pairs
4. **Dream Log** — Audit record (always runs, even on interruption)

## Installation

Run `install.sh` or copy the plugin directory to `~/.hermes/plugins/hermes-dream-engine/`.

```bash
./install.sh
```

## Configuration

Thresholds are configurable via `config.yaml`:

```yaml
plugins:
  hermes-dream-engine:
    idle_threshold_seconds: 300        # T1
    dormant_threshold_seconds: 1800    # T2
    soak_threshold_seconds: 3000       # T3
    hypnagogic_duration_seconds: 120   # T4
    max_dreams_per_day: 2
    consolidation_memory_count: 150
    invention_sample_size: 10
```

## Dashboard Tab

Access the dashboard at `/dream-engine` (configured in `dashboard/manifest.json`).

Features:
- Real-time state machine visualization
- Timer bars for idle, soak, and hypnagogic phases
- Dream journal history
- Manual controls (force dream, reset state, send heartbeat)
- Configuration editor
