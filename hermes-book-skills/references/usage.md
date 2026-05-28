# BookSkills Plugin Usage

## Uploading Books

1. Open the Hermes dashboard (usually http://127.0.0.1:9119)
2. Navigate to the `/books` tab
3. Click "Upload Book" and select a PDF, EPUB, or TXT file

Supported formats:
- `.pdf` — Portable Document Format
- `.epub` — Electronic Publication
- `.txt` — Plain text

## Processing Books

After uploading:
1. Click "Process" on a book to extract its text
2. The system splits large books into chunks for LLM processing
3. Use the chat interface to ask for key concepts, methods, and techniques

Example prompts:
- "What are the key concepts in this book?"
- "Extract the main methods or frameworks described"
- "Summarize the important techniques"

## Generating Skills

Once concepts are extracted:
1. Click "Generate Skill" in the preview modal
2. A skill file is created in `~/.hermes/skills/book-skills/`
3. Load the skill anytime with: `/skill book-skills/<skill-name>`

## Managing Libraries

### Books Library
- **Process** — Extract text from a new book
- **Regenerate Skill** — Recreate the skill if deleted
- **Delete** — Remove book (skill remains)

### Skills Library
- **Rename** — Change the skill name
- **Delete** — Remove skill (book remains)