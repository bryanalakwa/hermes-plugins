"""BookSkills Dashboard Plugin — Backend API routes.

Mounted at /api/plugins/hermes-book-skills/ by the dashboard plugin system.
Manages book uploads, processing, and skill generation.
"""
from __future__ import annotations

import json
import os
import re
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
    from fastapi.responses import JSONResponse
    _fastapi_available = True
except Exception:
    _fastapi_available = False
    # Stub classes for import failure case
    class APIRouter:
        def get(self, *_args, **_kwargs):
            return lambda fn: fn
        def post(self, *_args, **_kwargs):
            return lambda fn: fn
        def put(self, *_args, **_kwargs):
            return lambda fn: fn
        def delete(self, *_args, **_kwargs):
            return lambda fn: fn

    def UploadFile(*args, **kwargs):
        pass

# Create the router at module level (available in both success and failure cases)
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
    """Extract key concepts and methods from book text using LLM.
    
    Calls the hermes chat process to extract actionable concepts, methods, and techniques.
    """
    import subprocess
    
    prompt = f"""Extract the most important concepts, methods, and techniques from this book text. Return ONLY valid JSON:

{{
  "concepts": ["short descriptive phrase: 1-sentence actionable definition for other AIs"],
  "methods": ["short descriptive phrase: 1-sentence actionable definition for other AIs"],
  "techniques": ["short descriptive phrase: 1-sentence actionable definition for other AIs"]
}}

IMPORTANT: Each concept/method/technique must be a SHORT descriptive phrase (5-8 words max) followed by a colon and a 1-sentence actionable definition that any AI can understand and apply. Example: "Grand Slam Offer: A compelling offer combining ultimate value, scarcity, and social proof to create irresistible urgency."

Focus on actionable frameworks, principles, and methods. Remove duplicates. Limit to 10 items each.

BOOK TEXT (first 10k chars):
{text[:10000]}
"""
    
    try:
        # Use hermes -z to process the prompt
        result = subprocess.run(
            ["hermes", "-z", prompt, "--yolo"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        output = result.stdout
        
        # Extract JSON from response
        match = re.search(r"\{[\s\S]*\}", output)
        if match:
            try:
                data = json.loads(match.group())
                return {
                    "concepts": (data.get("concepts") or [])[:10],
                    "methods": (data.get("methods") or [])[:10],
                    "techniques": (data.get("techniques") or [])[:10],
                }
            except json.JSONDecodeError:
                pass
    except Exception:
        pass
    
    # Fallback: return empty lists
    return {"concepts": [], "methods": [], "techniques": []}


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
async def upload_book(file: UploadFile = File(...)) -> dict:
    """Upload a book file and save to library."""
    _ensure_paths()

    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # Read file content
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    # Save to library
    safe_name = file.filename.replace("/", "_").replace("\\", "_")
    dest = LIBRARY_PATH / safe_name

    # Check for existing file with same name
    if dest.exists():
        base = dest.stem
        ext = dest.suffix
        counter = 1
        while dest.exists():
            dest = LIBRARY_PATH / f"{base}_{counter}{ext}"
            counter += 1

    dest.write_bytes(content)

    return {"ok": True, "uploaded": dest.name, "path": str(dest)}


@router.get("/books/{book_id}/extract")
async def extract_book(book_id: str) -> dict:
    """Extract raw text from a book and run LLM extraction."""
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
    
    # Extract concepts with LLM
    extraction = _extract_key_concepts(text)
    
    return {
        "book_id": book_id,
        "title": book_file.name,
        "total_chunks": len(chunks),
        "chunks": chunks[:5],  # First 5 chunks preview
        "total_length": len(text),
        "concepts": extraction["concepts"],
        "methods": extraction["methods"],
        "techniques": extraction["techniques"],
    }


@router.post("/books/{book_id}/create")
async def create_skill(book_id: str) -> dict:
    """Full pipeline: extract text, run LLM, generate skill."""
    _ensure_paths()
    
    # Find the book file
    book_file = None
    for f in LIBRARY_PATH.iterdir():
        if f.is_file() and f.stem == book_id:
            book_file = f
            break
    
    if not book_file:
        raise HTTPException(status_code=404, detail=f"Book '{book_id}' not found")
    
    # Extract text
    text = _read_book(book_file)
    
    # Run LLM extraction
    extraction = _extract_key_concepts(text)
    
    # Generate and save skill
    skill_name = book_id.replace(" ", "-").lower()
    skill_content = _generate_skill_content(
        book_file.name,
        extraction["concepts"],
        extraction["methods"],
        extraction["techniques"]
    )
    
    skill_dir = SKILLS_PATH / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(skill_content)
    
    # Update state
    state = _load_state()
    if "generated" not in state:
        state["generated"] = {}
    state["generated"][book_id] = {
        "book_name": book_file.name,
        "skill_name": skill_name,
        "generated_at": time.strftime("%Y-%m-%d %H:%M"),
        "concepts_count": len(extraction["concepts"]),
        "methods_count": len(extraction["methods"]),
        "techniques_count": len(extraction["techniques"]),
    }
    _save_state(state)
    
    return {
        "ok": True,
        "skill_name": skill_name,
        "path": str(skill_file),
        "extraction": extraction,
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


@router.get("/skills/{skill_name}/content")
async def get_skill_content(skill_name: str) -> dict:
    """Get the SKILL.md content for editing."""
    _ensure_paths()
    
    skill_file = SKILLS_PATH / skill_name / "SKILL.md"
    if not skill_file.exists():
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
    
    return {
        "ok": True,
        "content": skill_file.read_text(),
        "skill_name": skill_name,
    }


@router.put("/skills/{skill_name}/content")
async def update_skill_content(skill_name: str, data: dict) -> dict:
    """Update the SKILL.md content."""
    _ensure_paths()
    
    skill_dir = SKILLS_PATH / skill_name
    if not skill_dir.exists():
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
    
    content = data.get("content", "")
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content)
    
    return {"ok": True, "updated": skill_name}


@router.get("/status")
async def get_status() -> dict:
    """Plugin status endpoint."""
    return {
        "ok": True,
        "library_path": str(LIBRARY_PATH),
        "skills_path": str(SKILLS_PATH),
        "library_exists": LIBRARY_PATH.exists(),
    }