# Plugin Development Guide

## User Data Preservation Pattern

The single most important rule for Hermes plugins: **Never store user data inside the plugin code directory**.

### Directory Separation

```
User data (PERSISTENT)     Plugin code (REPLACEABLE)
====================     =========================
$HERMES_HOME/             $HERMES_AGENT/plugins/<name>/
├── config.yaml           ├── __init__.py
├── <plugin-name>/        ├── plugin.yaml
│   ├── state.json        ├── daemon.py
│   ├── history.json      ├── dashboard/
│   └── ...               └── scripts/
├── memories/             └── references/
└── other_data/           └── ...
```

**Why this matters:** The installer (`rm -rf "$PLUGIN_DEST"`) completely replaces plugin code during upgrades. User data must survive this.

### User Data vs Plugin Code Examples

| Type | Location | Survives Upgrade? |
|------|----------|-------------------|
| State files | `$HERMES_HOME/<plugin>/state.json` | ✅ Yes |
| Journal/logs | `$HERMES_HOME/<plugin>/journal.json` | ✅ Yes |
| Message history | `$HERMES_HOME/webhookHistory.json` | ✅ Yes |
| Settings | `$HERMES_HOME/config.yaml` | ✅ Yes |
| Dreams archive | `$HERMES_HOME/dream_engine/archive/` | ✅ Yes |
| Facts DB | `$HERMES_HOME/memory_store.db` | ✅ Yes |
| Plugin code | `$HERMES_AGENT/plugins/<plugin>/` | ❌ Replaced |
| Dashboard JS | `$PLUGIN_DEST/dashboard/dist/index.js` | ❌ Replaced |

### Install Script Pattern

From `templates/install-sh-template.sh`:

```bash
# USER DATA PRESERVATION
USER_DATA_FILES=(
  "<plugin>/state.json"
  "<plugin>/journal.json"
)

# Preserve before destructive ops
for data_file in "${USER_DATA_FILES[@]}"; do
  full_path="$HERMES_HOME/$data_file"
  [ -f "$full_path" ] && cp "$full_path" "${full_path}.upgrade_backup"
done

# Safe to remove plugin code — user data lives elsewhere
rm -rf "$PLUGIN_DEST"

# Restore after fresh copy
for data_file in "${USER_DATA_FILES[@]}"; do
  full_path="$HERMES_HOME/$data_file"
  backup="${full_path}.upgrade_backup"
  [ -f "$backup" ] && [ ! -f "$full_path" ] && mv "$backup" "$full_path"
done
```

### Existing Plugin Examples

**hermes-dream-engine:**
- User data: `$HERMES_HOME/dream_engine/*` and `$HERMES_HOME/*memory*`
- Plugin code: `$HERMES_AGENT/plugins/hermes-dream-engine/`
- Separation: ✅ Clean — `install.sh` creates `$HERMES_HOME/dream_engine/` but never removes it

**hermes-webhook:**
- User data: `$HERMES_HOME/webhookHistory.json`
- Plugin code: `$HERMES_AGENT/plugins/hermes-webhook/`
- Separation: ✅ Clean — `install.sh` creates history if missing, never deletes existing

### Checklist for New Plugins

- [ ] All user data stored in `$HERMES_HOME/<plugin-name>/`
- [ ] Plugin code only in `$HERMES_AGENT/plugins/<plugin-name>/`
- [ ] Install script preserves existing user data files
- [ ] Install script idempotent (safe to re-run)
- [ ] Install script handles fresh install vs upgrade gracefully