"""Hermes Dreaming Plugin — Idle-time memory consolidation.

Provides:
- Two-tier memory: holographic fact store + ChromaDB vector search
- Dashboard plugin at /dreams tab
- Cron-triggered dreaming every 30 minutes
- Dashboard API for journal entries, vector stats, and re-indexing

Install: run install.sh from the plugin root directory.
"""

__version__ = "2.0.0"
