"""BookSkills Dashboard Plugin — Backend API routes.

Mounted at /api/plugins/hermes-book-skills/ by the dashboard plugin system.
Manages book uploads, processing, and skill generation.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from hermes_constants import get_hermes_home
except ImportError:
    def get_hermes_home() -> Path:
        val = (os.environ.get("HERMES_HOME") or "").strip()
        return Path(val) if val else Path.home() / ".hermes"

try:
    from fastapi import APIRouter, HTTPException, Query, UploadFile, File
except Exception:
    class APIRouter:
        def get(self, *_args, **_kwargs):
            return lambda fn: fn
        def post(self, *_args, **_kwargs):
            return lambda fn: fn
        def put(self, *_args, **_kwargs):
            return lambda fn: fn
        def delete(self, *_args, **_kwargs):
            return lambda fn: fn

router = APIRouter()

HOME = get_hermes_home()
LIBRARY_PATH = HOME / "book-library"
SKILLS_PATH = HOME / "skills" / "book-skills"
STATE_PATH = LIBRARY_PATH / ".processing_state.json"


# ── Path helpers ────────────────────────────────────────

def _ensure_paths() -> None:
    """Create library and skills directories if needed."""
    LIBRARY_PATH.mkdir(parents=True, exist_ok=True)
    SKILLS_PATH.mkdir(parents=True, exist_ok=True)


def _load_state() -> dict:
    """Load processing state (tracks which books have skills generated)."""
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    """Save processing state."""
    LIBRARY_PATH.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


# ── Book reading helpers ─────────────────────────────────

def _read_book(filepath: Path) -> str:
    """Extract text from PDF/EPUB/TXT files."""
    suffix = filepath.suffix.lower()
    try:
        if suffix == ".txt":
            return filepath.read_text(encoding="utf-8", errors="replace")
        elif suffix == ".pdf":
            from PyPDF2 import PdfReader
            reader = PdfReader(str(filepath))
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
            return text
        elif suffix in {".epub", ".mobi", ".azw"}:
            from ebooklib import epub
            from bs4 import BeautifulSoup
            book = epub.read_epub(str(filepath))
            chapters = []
            for item in book.get_items_of_type(9):
                soup = BeautifulSoup(item.get_content(), "html.parser")
                text = soup.get_text()
                if text.strip():
                    chapters.append(text.strip())
            return "\n\n".join(chapters)
        else:
            return filepath.read_text(encoding="utf-8", errors="replace")
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Missing dependency: {e}")


def _chunk_text(text: str, max_tokens: int = 4000) -> List[str]:
    """Split text into chunks for LLM processing (rough token estimation)."""
    words = text.split()
    chunks = []
    current_chunk = []
    current_size = 0
    
    for word in words:
        word_tokens = len(word) // 4 + 1
        if current_size + word_tokens > max_tokens and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_size = 0
        current_chunk.append(word)
        current_size += word_tokens
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks


# ── Skill generation ─────────────────────────────────────

def _extract_key_concepts(text: str) -> dict:
    """Extract key concepts and methods from book text using LLM."""
    # This would be called via the agent's LLM - for now return placeholder
    # The actual LLM call happens in the frontend via the chat endpoint
    return {
        "concepts": ["extraction via LLM pending"],
        "methods": ["structured extraction pending"],
        "techniques": ["pending"],
    }


def _generate_skill_content(book_title: str, concepts: list, methods: list, techniques: list) -> str:
    """Generate a Hermes skill SKILL.md content from extracted concepts."""
    concept_list = "\n".join(f"- {c}" for c in concepts[:10])
    method_list = "\n".join(f"- {m}" for m in methods[:10])
    tech_list = "\n".join(f"- {t}" for t in techniques[:10])
    
    skill_name = book_title.lower().replace(" ", "-").replace(".", "").replace("/", "")
    
    return f"""---
name: {skill_name}
description: "Extracted concepts and methods from '{book_title}'"
version: 1.0.0
author: BookSkills Plugin
license: MIT
---

# {book_title} — Key Concepts

Generated from book analysis.

## Core Concepts

{concept_list}

## Methods & Techniques

{method_list}

## Techniques

{tech_list}

## Usage

Load this skill to apply concepts from {book_title} to relevant tasks.
"""


# ── API Routes ───────────────────────────────────────────

@router.get("/books")
async def list_books() -> dict:
    """List all uploaded books with status."""
    _ensure_paths()
    state = _load_state()
    
    books = []
    for book_file in LIBRARY_PATH.iterdir():
        if book_file.is_file() and book_file.suffix.lower() in {".pdf", ".epub", ".txt", ".mobi", ".azw"}:
            book_id = book_file.stem
            book_info = {
                "id": book_id,
                "name": book_file.name,
                "size": book_file.stat().st_size,
                "uploaded_at": time.strftime("%Y-%m-%d %H:%M"),
                "has_skill": book_id in state.get("generated", {}),
                "skill_name": state.get("generated", {}).get(book_id, {}).get("skill_name", ""),
            }
            books.append(book_info)
    
    return {"books": books, "library_path": str(LIBRARY_PATH)}


@router.post("/books/upload")
async def upload_book(filename: str = "", content: str = "") -> dict:
    """Upload a book file. For now, copies file from a temp location or receives content."""
    _ensure_paths()

    # This endpoint receives a filename hint - actual file handling
    # requires frontend to save to library path directly
    # For now, return instructions
    return {"ok": True, "message": "Use the dashboard file picker to select a book file"}


@router.get("/books/{book_id}/extract")
async def extract_book(book_id: str) -> dict:
    """Extract raw text from a book for LLM processing."""
    _ensure_paths()
    
    # Find the book file
    book_file = None
    for f in LIBRARY_PATH.iterdir():
        if f.is_file() and f.stem == book_id:
            book_file = f
            break
    
    if not book_file:
        raise HTTPException(status_code=404, detail=f"Book '{book_id}' not found")
    
    text = _read_book(book_file)
    chunks = _chunk_text(text, max_tokens=4000)
    
    return {
        "book_id": book_id,
        "title": book_file.name,
        "total_chunks": len(chunks),
        "chunks": chunks[:5],  # First 5 chunks preview
        "total_length": len(text),
    }


@router.post("/books/{book_id}/generate")
async def generate_skill(book_id: str, data: dict) -> dict:
    """Generate skill from extracted concepts."""
    _ensure_paths()
    
    concepts = data.get("concepts", [])
    methods = data.get("methods", [])
    techniques = data.get("techniques", [])
    skill_name = data.get("skill_name", book_id)
    
    book_file = None
    for f in LIBRARY_PATH.iterdir():
        if f.is_file() and f.stem == book_id:
            book_file = f
            break
    
    if not book_file:
        raise HTTPException(status_code=404, detail=f"Book '{book_id}' not found")
    
    # Generate skill content
    skill_content = _generate_skill_content(book_file.name, concepts, methods, techniques)
    
    # Save skill
    skill_dir = SKILLS_PATH / skill_name.replace(" ", "-").lower()
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(skill_content)
    
    # Update state
    state = _load_state()
    if "generated" not in state:
        state["generated"] = {}
    state["generated"][book_id] = {
        "book_name": book_file.name,
        "skill_name": skill_name.replace(" ", "-").lower(),
        "generated_at": time.strftime("%Y-%m-%d %H:%M"),
    }
    _save_state(state)
    
    return {
        "ok": True,
        "skill_name": skill_name.replace(" ", "-").lower(),
        "path": str(skill_file),
    }


@router.get("/skills")
async def list_skills() -> dict:
    """List all generated skills."""
    _ensure_paths()
    
    skills = []
    for skill_dir in SKILLS_PATH.iterdir():
        if skill_dir.is_dir():
            skill_file = skill_dir / "SKILL.md"
            skill_info = {
                "name": skill_dir.name,
                "path": str(skill_dir),
                "has_skill_md": skill_file.exists(),
            }
            skills.append(skill_info)
    
    return {"skills": skills, "skills_path": str(SKILLS_PATH)}


@router.delete("/books/{book_id}")
async def delete_book(book_id: str) -> dict:
    """Delete a book from the library."""
    _ensure_paths()
    
    # Remove book file
    for f in LIBRARY_PATH.iterdir():
        if f.is_file() and f.stem == book_id:
            f.unlink()
            break
    
    # Update state
    state = _load_state()
    if "generated" in state and book_id in state["generated"]:
        del state["generated"][book_id]
        _save_state(state)
    
    return {"ok": True, "deleted": book_id}


@router.delete("/skills/{skill_name}")
async def delete_skill(skill_name: str) -> dict:
    """Delete a generated skill."""
    _ensure_paths()
    
    skill_dir = SKILLS_PATH / skill_name
    if skill_dir.exists():
        import shutil
        shutil.rmtree(skill_dir)
    
    # Update state
    state = _load_state()
    for book_id, info in list(state.get("generated", {}).items()):
        if info.get("skill_name") == skill_name:
            del state["generated"][book_id]
            _save_state(state)
            break
    
    return {"ok": True, "deleted": skill_name}


@router.put("/skills/{skill_name}/rename")
async def rename_skill(skill_name: str, data: dict) -> dict:
    """Rename a skill (update directory and state)."""
    _ensure_paths()
    
    new_name = (data.get("new_name") or "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="New skill name required")
    
    old_dir = SKILLS_PATH / skill_name
    new_dir = SKILLS_PATH / new_name
    
    if not old_dir.exists():
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
    
    if new_dir.exists():
        raise HTTPException(status_code=400, detail=f"Skill '{new_name}' already exists")
    
    old_dir.rename(new_dir)
    
    # Update state
    state = _load_state()
    for book_id, info in state.get("generated", {}).items():
        if info.get("skill_name") == skill_name:
            info["skill_name"] = new_name
            state["generated"][book_id] = info
            _save_state(state)
            break
    
    return {"ok": True, "old_name": skill_name, "new_name": new_name}


@router.get("/status")
async def get_status() -> dict:
    """Plugin status endpoint."""
    return {
        "ok": True,
        "library_path": str(LIBRARY_PATH),
        "skills_path": str(SKILLS_PATH),
        "library_exists": LIBRARY_PATH.exists(),
    }