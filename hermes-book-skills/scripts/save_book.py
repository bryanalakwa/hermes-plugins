#!/usr/bin/env python3
"""Save uploaded book file to the library."""
import sys
import shutil
from pathlib import Path

HERMES_HOME = Path.home() / ".hermes"
LIBRARY_PATH = HERMES_HOME / "book-library"

def main():
    if len(sys.argv) < 2:
        print("Usage: save_book.py <source_file> [new_name]")
        sys.exit(1)

    source = Path(sys.argv[1])
    if not source.exists():
        print(f"Error: File not found: {source}")
        sys.exit(1)

    LIBRARY_PATH.mkdir(parents=True, exist_ok=True)

    dest_name = sys.argv[2] if len(sys.argv) > 2 else source.name
    dest = LIBRARY_PATH / dest_name

    shutil.copy2(source, dest)
    print(f"Saved: {dest}")

if __name__ == "__main__":
    main()