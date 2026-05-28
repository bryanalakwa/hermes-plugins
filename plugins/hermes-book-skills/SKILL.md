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
      - scripts/process_book.py
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

1. **Upload** a book via the file picker
2. **Process** to extract text chunks
3. **Chat with the agent** to analyze the book and extract key concepts
4. **Generate Skill** to create a reusable Hermes skill
5. **Manage**: Books list and Skills list maintain independent lifecycles

## API Endpoints

- `GET /api/plugins/hermes-book-skills/books` — List uploaded books
- `POST /api/plugins/hermes-book-skills/books/upload` — Upload book
- `GET /api/plugins/hermes-book-skills/books/{id}/extract` — Extract text
- `POST /api/plugins/hermes-book-skills/books/{id}/generate` — Generate skill
- `GET /api/plugins/hermes-book-skills/skills` — List generated skills
- `DELETE /api/plugins/hermes-book-skills/books/{id}` — Delete book
- `DELETE /api/plugins/hermes-book-skills/skills/{name}` — Delete skill
- `PUT /api/plugins/hermes-book-skills/skills/{name}/rename` — Rename skill

## Dependencies

- PyPDF2 (PDF reading)
- EbookLib + beautifulsoup4 (EPUB/MOBI reading)