#!/usr/bin/env python3
"""Extract key concepts from book text using LLM."""
import sys
import json
from pathlib import Path

try:
    # Try to use hermes LLM
    from hermes_agent import AIAgent
    HAS_HERMES = True
except ImportError:
    HAS_HERMES = False

PROMPT_TEMPLATE = """Extract the most important concepts, methods, and techniques from this book excerpt. Return ONLY valid JSON:

{{
  "concepts": ["concept 1", "concept 2", ... up to 10],
  "methods": ["method 1", "method 2", ... up to 10],
  "techniques": ["technique 1", "technique 2", ... up to 10]
}}

Focus on actionable frameworks, principles, and methods the reader would want to apply.
"""

def extract_concepts_with_llm(text: str) -> dict:
    """Use LLM to extract concepts from book text."""
    if HAS_HERMES:
        agent = AIAgent()
        prompt = PROMPT_TEMPLATE + "\n\nBOOK TEXT:\n" + text[:15000]  # Limit for context
        result = agent.run(prompt)
        # Extract JSON from response
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            return json.loads(result[start:end])
        except Exception:
            pass
    
    # Fallback: simple keyword extraction
    return {
        "concepts": [],
        "methods": [],
        "techniques": []
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: extract_concepts.py <book_file_path>")
        sys.exit(1)
    
    book_path = Path(sys.argv[1])
    
    # Read the book
    suffix = book_path.suffix.lower()
    text = ""
    
    if suffix == ".txt":
        text = book_path.read_text(encoding="utf-8", errors="replace")
    elif suffix == ".pdf":
        from PyPDF2 import PdfReader
        reader = PdfReader(str(book_path))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    
    if text:
        result = extract_concepts_with_llm(text[:20000])
        print(json.dumps(result))
    else:
        print(json.dumps({"concepts": [], "methods": [], "techniques": []}))

if __name__ == "__main__":
    main()