#!/usr/bin/env python3
"""
Document Reader - Extract text from PDF and ebook files

Supports:
- PDF files (via PyPDF2 - basic text extraction, fast)
- EPUB books (via EbookLib)
- TXT files (plain text)

Usage:
    python read_document.py <file_path>
"""

import argparse
import sys
from pathlib import Path

def read_pdf(filepath: Path) -> str:
    """Extract text from PDF using PyPDF2 (fast, no model downloads)."""
    try:
        import PyPDF2
        text = []
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
        return '\n'.join(text) if text else "PDF contains no extractable text"
    except Exception as e:
        return f"Error reading PDF: {e}"

def read_epub(filepath: Path) -> str:
    """Extract text from EPUB ebook."""
    try:
        from ebooklib import epub
        from bs4 import BeautifulSoup
        
        book = epub.read_epub(str(filepath))
        chapters = []
        
        for item in book.get_items_of_type(9):  # ITEM_DOCUMENT = 9
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            text = soup.get_text()
            if text.strip():
                chapters.append(text.strip())
        
        return '\n\n'.join(chapters)
    except Exception as e:
        return f"Error reading EPUB: {e}"

def read_txt(filepath: Path) -> str:
    """Read plain text file."""
    return filepath.read_text(encoding='utf-8', errors='replace')

def main():
    parser = argparse.ArgumentParser(description="Read PDF and ebook files")
    parser.add_argument("file", help="Path to the document file")
    args = parser.parse_args()
    
    filepath = Path(args.file)
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    
    suffix = filepath.suffix.lower()
    
    if suffix == '.pdf':
        content = read_pdf(filepath)
    elif suffix in {'.epub', '.mobi', '.azw'}:
        content = read_epub(filepath)
    elif suffix == '.txt':
        content = read_txt(filepath)
    else:
        # Try PDF reader as default
        content = read_pdf(filepath)
    
    print(content)

if __name__ == "__main__":
    main()