# BookSkills Plugin Usage

## Uploading Books

1. Open the Hermes dashboard (usually http://127.0.0.1:9119)
2. Navigate to the `/books` tab
3. Click "Upload Book" and select a PDF, EPUB, or TXT file

Supported formats:
- `.pdf` — Portable Document Format (PyPDF2)
- `.epub` — Electronic Publication (EbookLib)
- `.txt` — Plain text

## Creating Skills

After uploading:
1. Click "Create Skill" on any book in the library
2. The system automatically:
   - Extracts text from the book
   - Runs LLM extraction to find key concepts/methods
   - Generates a Hermes skill file
3. A progress bar shows the extraction/generation status
4. Once complete, the skill appears in the Skills tab

## Viewing and Editing Skills

In the Skills tab:
- Click the **Eye icon** to view/edit skill markdown
- Edit the content in the modal textarea
- Click "Save Skill" to persist changes
- The edited skill can be loaded with `/skill book-skills/<skill-name>`

## Managing Libraries

### Books Library
- **Create Skill** — Extract text and generate skill via LLM
- **Delete** — Remove book (any generated skill remains)

### Skills Library
- **View/Edit** — Click Eye icon to modify skill markdown
- **Rename** — Change the skill name (updates directory/files)
- **Delete** — Remove skill (book remains in library)

## Generated Skill Format

Skills are stored at `~/.hermes/skills/book-skills/<skill-name>/SKILL.md`

Each skill includes:
- YAML frontmatter (name, description, version)
- Core concepts list
- Methods & techniques list
- Usage instructions for applying the skill