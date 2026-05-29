# BookSkills

Upload PDF, EPUB, or TXT books to generate reusable Hermes skills via LLM extraction.

## What It Does

- **Book upload**: Drag-and-drop or file picker for PDF, EPUB, TXT, MOBI files
- **LLM extraction**: Extracts key concepts and methods from book text
- **Skill generation**: Creates reusable Hermes skill files from extracted content
- **Library management**: Separate tabs for books and skills, with delete/rename/regen capabilities

## Install

```bash
# From the hermes-plugins repo root:
cd hermes-book-skills/
chmod +x install.sh
./install.sh
systemctl --user restart hermes-gateway.service
```

That's it. The installer handles everything:
1. Creates necessary directories
2. Installs the plugin to `~/.hermes/hermes-agent/plugins/`
3. Updates config.yaml with plugin enabled

After restart, open the **BookSkills** tab in the dashboard (port 9119).

## Requirements

- Hermes Agent installed at `~/.hermes/hermes-agent/`
- Python 3.11+ venv
- `memory.provider: holographic` in config.yaml (for memory integration)

## Usage

1. Switch to **Books** tab
2. Click **Upload Book** and select a PDF/EPUB/TXT file
3. Click **Create Skill** on the uploaded book
4. The LLM extracts concepts and methods, generating a skill
5. Switch to **Skills** tab to view/edit the generated skill
6. Click any skill card to open in a modal editor
7. Edit and **Save Changes** to update the skill

## Features

- Textarea editor with preserved cursor position during typing
- Pointer cursor on skill cards for click indication
- Modal styling matching dream-engine for consistency
- Progress bar showing extraction stages
- Skill metadata display (concepts count, methods count)

## Files

```
~/.hermes/hermes-agent/plugins/hermes-book-skills/  # Plugin code
~/.hermes/books/                                       # Uploaded book library
~/.hermes/skills/                                      # Generated skills
```

## Troubleshooting

- **Plugin not showing in dashboard**: Restart gateway, check `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9119/api/plugins/hermes-book-skills/status` — should return 401
- **Upload fails**: Check file size (< 10MB recommended) and format (PDF/EPUB/TXT/MOBI/AZW)
- **Skill generation slow**: Large books take longer — extraction happens in stages shown in the progress bar