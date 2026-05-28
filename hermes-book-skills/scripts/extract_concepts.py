#!/usr/bin/env python3
"""Extract key concepts from book text using LLM."""
import json
import re
import subprocess
import sys
from pathlib import Path

def extract_concepts_with_llm(text: str) -> dict:
    """Use hermes -z to extract concepts from book text."""
    prompt = """Extract the most important concepts, methods, and techniques from this book excerpt. Return ONLY valid JSON:

{{
  "concepts": ["short phrase: 1-sentence actionable definition for other AIs"],
  "methods": ["short phrase: 1-sentence actionable definition for other AIs"],
  "techniques": ["short phrase: 1-sentence actionable definition for other AIs"]
}}

IMPORTANT: Each item must be a SHORT descriptive phrase (5-8 words max) followed by a colon and a 1-sentence actionable definition that any AI can understand and apply.

BOOK TEXT:
{{}}""".format(text[:15000])
    
    try:
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
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    except Exception:
        pass
    
    return {"concepts": [], "methods": [], "techniques": []}

def read_book(filepath):
    """Read text from PDF/EPUB/TXT file."""
    suffix = filepath.suffix.lower()
    if suffix == ".txt":
        return filepath.read_text(encoding="utf-8", errors="replace")
    elif suffix == ".pdf":
        from PyPDF2 import PdfReader
        reader = PdfReader(str(filepath))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix in {".epub", ".mobi", ".azw"}:
        from ebooklib import epub
        from bs4 import BeautifulSoup
        book = epub.read_epub(str(filepath))
        chapters = []
        for item in book.get_items_of_type(9):
            soup = BeautifulSoup(item.get_content(), "html.parser")
            if soup.get_text().strip():
                chapters.append(soup.get_text().strip())
        return "\n\n".join(chapters)
    else:
        return filepath.read_text(encoding="utf-8", errors="replace")

def main():
    if len(sys.argv) < 2:
        print("Usage: extract_concepts.py <book_file_path>", file=sys.stderr)
        sys.exit(1)
    
    book_path = Path(sys.argv[1])
    
    if not book_path.exists():
        print("File not found", file=sys.stderr)
        sys.exit(1)
    
    text = read_book(book_path)
    
    if text:
        result = extract_concepts_with_llm(text[:20000])
        print(json.dumps(result))
    else:
        print(json.dumps({"concepts": [], "methods": [], "techniques": []}))

if __name__ == "__main__":
    main()