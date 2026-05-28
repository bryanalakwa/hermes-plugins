---
name: hermes-book-skills
description: "Book-to-skill generation plugin. Upload PDF/EPUB/TXT books, extract key concepts via LLM processing, and generate reusable Hermes skills."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [books, skills, knowledge, learning, extraction]
    homepage: https://github.com/bryanalakwa/hermes-plugins
    related_skills: []
  linked_files:
    references:
      - references/usage.md
    scripts:
      - scripts/extract_concepts.py
      - scripts/save_book.py
    dashboard:
      - dashboard/dist/index.js
      - dashboard/plugin_api.py
---

# BookSkills Plugin

Upload books and generate reusable Hermes skills from their key concepts.

## Features

- **Book Library**: Upload PDF, EPUB, or TXT files
- **Skill Generation**: Extract concepts and methods via LLM processing
- **Independent Management**: Delete books without affecting skills, delete skills without affecting books
- **Rename Skills**: Customize auto-generated skill names

## Dashboard

Access via `/books` tab in the Hermes web dashboard (port 9119).

### Workflow

1. **Upload** a book via the file picker (auto-saved to `~/.hermes/book-library/`)
2. **Create Skill** — extracts text and runs LLM concept extraction automatically
3. **Skill Generated** appears — view/edit the skill markdown in the Skills tab
4. **Manage**: Books and skills maintain independent lifecycles (delete one without affecting the other)

## API Endpoints

- `GET /api/plugins/hermes-book-skills/books` — List uploaded books
- `POST /api/plugins/hermes-book-skills/books/upload` — Upload and save book
- `GET /api/plugins/hermes-book-skills/books/{id}/extract` — Extract text + LLM concepts
- `POST /api/plugins/hermes-book-skills/books/{id}/create` — Full pipeline (extract + generate)
- `GET /api/plugins/hermes-book-skills/skills` — List generated skills
- `GET /api/plugins/hermes-book-skills/skills/{name}/content` — Get skill markdown for editing
- `PUT /api/plugins/hermes-book-skills/skills/{name}/content` — Save edited skill
- `DELETE /api/plugins/hermes-book-skills/books/{id}` — Delete book
- `DELETE /api/plugins/hermes-book-skills/skills/{name}` — Delete skill
- `PUT /api/plugins/hermes-book-skills/skills/{name}/rename` — Rename skill

## Dependencies

- PyPDF2 (PDF reading)
- EbookLib + beautifulsoup4 (EPUB/MOBI reading)