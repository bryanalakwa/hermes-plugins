"""Dream session engine — implements the 4 phases of a dream session.

Each phase is independently resumable and saves incremental output
to the dream journal. The engine reads from the agent's memory
(fact_store / MEMORY.md) and stores dream results back.

Design: This module does NOT handle state transitions. It only
executes dream phases when told to by the daemon. This separation
keeps the dream logic testable and the daemon loop simple.
"""

import json
import logging
import random
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DreamSession:
    """Records metadata and results for a single dream session."""

    def __init__(self, session_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.started_at: Optional[float] = None
        self.ended_at: Optional[float] = None
        self.state_on_exit: str = "pending"  # completed | interrupted | cancelled
        self.memories_consolidated: int = 0
        self.insights_generated: int = 0
        self.ideas_invented: int = 0
        self.phases_run: List[str] = []
        self.errors: List[str] = []
        self.summary: str = ""

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "started_at": self._fmt(self.started_at),
            "ended_at": self._fmt(self.ended_at),
            "state_on_exit": self.state_on_exit,
            "memories_consolidated": self.memories_consolidated,
            "insights_generated": self.insights_generated,
            "ideas_invented": self.ideas_invented,
            "phases_run": self.phases_run,
            "errors": self.errors,
            "summary": self.summary,
        }

    @staticmethod
    def _fmt(ts: Optional[float]) -> Optional[str]:
        if ts is None:
            return None
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


class DreamEngine:
    """Executes dream session phases.

    The engine reads memories from the agent's memory system and
    writes dream results to the journal file. It does NOT manage
    state transitions — the daemon handles that.
    """

    def __init__(self, journal_path: Path, memory_source_path: Optional[Path] = None):
        self.journal_path = journal_path
        self.memory_source_path = memory_source_path
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        self._session: Optional[DreamSession] = None
        self._interrupted = False

    @property
    def is_running(self) -> bool:
        return self._session is not None

    def interrupt(self) -> None:
        """Signal the current dream session to stop after the current phase."""
        self._interrupted = True
        logger.info("dream interruption requested")

    # ── Phase entry point ───────────────────────────────────

    def start_session(self) -> DreamSession:
        """Begin a new dream session. Returns the session object."""
        self._session = DreamSession()
        self._session.started_at = time.time()
        self._interrupted = False
        logger.info("dream session %s started", self._session.session_id)
        return self._session

    def run_all_phases(self) -> DreamSession:
        """Run all 4 phases. If interrupted, partial results are saved."""
        if not self._session:
            self.start_session()

        s = self._session

        try:
            # Phase 1: Memory Consolidation
            if not self._interrupted:
                self._phase1_consolidation()

            # Phase 2: Problem Re-evaluation
            if not self._interrupted:
                self._phase2_problem_reevaluation()

            # Phase 3: Free Association / Invention
            if not self._interrupted:
                self._phase3_invention()

        except Exception as e:
            s.errors.append(str(e))
            logger.exception("dream session error")

        finally:
            # Phase 4: Dream log (always runs)
            self._phase4_dream_log()

        return s

    # ── Phase 1: Memory Consolidation ──────────────────────

    def _phase1_consolidation(self) -> None:
        """Re-examine recent memories, strengthen/correct connections."""
        self._session.phases_run.append("consolidation")
        logger.info("dream Phase 1: consolidation")

        try:
            memories = self._load_recent_memories()
            consolidated = 0
            contradictions_found = 0
            new_links = 0

            # Check for contradictions
            for i, mem in enumerate(memories):
                for j in range(i + 1, len(memories)):
                    if self._check_contradiction(mem, memories[j]):
                        contradictions_found += 1
                        self._resolve_contradiction(mem, memories[j])
                        consolidated += 1

            # Re-score similarity links
            for i, mem in enumerate(memories):
                for j in range(i + 1, min(i + 10, len(memories))):
                    similarity = self._estimate_similarity(mem, memories[j])
                    if similarity > 0.7:
                        new_links += 1

            self._session.memories_consolidated = consolidated + len(memories) // 2
            logger.info(
                "Phase 1: reviewed %d memories, %d contradictions, %d new links",
                len(memories), contradictions_found, new_links,
            )
        except Exception as e:
            logger.warning("Phase 1 error: %s", e)
            self._session.errors.append(f"phase1: {e}")

    # ── Phase 2: Problem Re-evaluation ─────────────────────

    def _phase2_problem_reevaluation(self) -> None:
        """Revisit unresolved problems with fresh context."""
        self._session.phases_run.append("problem_reevaluation")
        logger.info("dream Phase 2: problem re-evaluation")

        try:
            memories = self._load_recent_memories()
            unresolved = [m for m in memories if self._is_unresolved(m)]
            insights = 0

            for problem in unresolved:
                if self._interrupted:
                    break
                if self._reevaluate_problem(problem, memories):
                    insights += 1

            self._session.insights_generated = insights
            logger.info("Phase 2: %d problems re-evaluated, %d insights",
                        len(unresolved), insights)
        except Exception as e:
            logger.warning("Phase 2 error: %s", e)
            self._session.errors.append(f"phase2: {e}")

    # ── Phase 3: Free Association / Invention ───────────────

    def _phase3_invention(self) -> None:
        """Generate novel ideas by connecting unrelated memories."""
        self._session.phases_run.append("invention")
        logger.info("dream Phase 3: free association / invention")

        try:
            memories = self._load_all_memories()
            ideas = 0

            # Sample random memories and find distant pairs
            k = min(10, len(memories))
            if k < 2:
                logger.info("Phase 3: not enough memories (%d)", len(memories))
                return

            sample = random.sample(memories, k)

            # Find the most semantically distant pair
            most_distant = self._find_most_distant_pair(sample)
            if most_distant:
                m1, m2 = most_distant
                if self._invent_from_pair(m1, m2):
                    ideas += 1

            # Try a few more pairs
            for _ in range(3):
                if self._interrupted:
                    break
                pair = self._find_most_distant_pair(sample)
                if pair:
                    if self._invent_from_pair(pair[0], pair[1]):
                        ideas += 1

            self._session.ideas_invented = ideas
            logger.info("Phase 3: %d ideas invented", ideas)
        except Exception as e:
            logger.warning("Phase 3 error: %s", e)
            self._session.errors.append(f"phase3: {e}")

    # ── Phase 4: Dream Log (always runs) ───────────────────

    def _phase4_dream_log(self) -> None:
        """Record metadata about the dream session."""
        self._session.phases_run.append("dream_log")
        s = self._session
        s.ended_at = time.time()

        # Determine exit state
        if self._interrupted:
            s.state_on_exit = "interrupted"
        elif s.errors:
            s.state_on_exit = "completed_with_errors"
        else:
            s.state_on_exit = "completed"

        # Build summary
        duration = (s.ended_at - s.started_at) if s.started_at else 0
        s.summary = (
            f"Dream {s.session_id}: {s.state_on_exit} in {duration:.0f}s. "
            f"Phases: {s.phases_run}. "
            f"Memories: {s.memories_consolidated}, "
            f"Insights: {s.insights_generated}, "
            f"Ideas: {s.ideas_invented}."
        )

        # Write to journal
        self._append_journal(s.to_dict())
        logger.info("Phase 4: dream log written — %s", s.summary)

    # ── Memory access helpers ─────────────────────────────

    def _load_recent_memories(self) -> List[dict]:
        """Load recent memories from available sources."""
        memories = []

        # Try the old dreams state file first (migration path)
        if self.memory_source_path and self.memory_source_path.exists():
            try:
                data = json.loads(self.memory_source_path.read_text())
                if isinstance(data, dict):
                    # Extract memories from dreams state
                    for entry in data.get("entries", []):
                        memories.append({
                            "id": entry.get("id", ""),
                            "content": entry.get("content", ""),
                            "timestamp": entry.get("timestamp", ""),
                            "type": "dream_memory",
                        })
            except Exception:
                pass

        # Also try to read from the holographic fact_store DB
        try:
            hermes_home = Path.home() / ".hermes" / "hermes-agent"
            db_path = hermes_home / "plugins" / "memory" / "holographic" / "memory_store.db"
            if db_path.exists():
                import sqlite3
                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT id, content, created_at, trust FROM facts "
                    "ORDER BY created_at DESC LIMIT 150"
                ).fetchall()
                for row in rows:
                    memories.append({
                        "id": str(row["id"]),
                        "content": row["content"],
                        "timestamp": row.get("created_at", ""),
                        "trust": row.get("trust", 0.5),
                        "type": "fact",
                    })
                conn.close()
        except Exception:
            pass

        # Fallback to empty list if no sources available
        return memories

    def _load_all_memories(self) -> List[dict]:
        """Load all available memories (for invention phase)."""
        return self._load_recent_memories()

    # ── Phase helper methods ───────────────────────────────

    def _check_contradiction(self, m1: dict, m2: dict) -> bool:
        """Check if two memories contradict each other. Simple heuristic."""
        c1 = m1.get("content", "").lower()
        c2 = m2.get("content", "").lower()
        # Simple heuristic: look for negation pairs
        negation_pairs = [
            ("is", "is not"), ("was", "was not"), ("can", "cannot"),
            ("always", "never"), ("true", "false"), ("yes", "no"),
        ]
        for pos, neg in negation_pairs:
            if (pos in c1 and neg in c2) or (neg in c1 and pos in c2):
                # Check if they share significant words (same topic topic_words = set(c1.split()) & set(c2.split())
                topic_words = set(c1.split()) & set(c2.split())
                if len(topic_words) > 2:
                    return True
        return False

    def _resolve_contradiction(self, m1: dict, m2: dict) -> None:
        """Mark contradictions with resolution hints. In a full implementation,
        this would invoke the LLM to produce a resolution."""
        pass

    def _estimate_similarity(self, m1: dict, m2: dict) -> float:
        """Estimate semantic similarity between two memories.
        Simple Jaccard-based word overlap for the MVP."""
        c1 = set(m1.get("content", "").lower().split())
        c2 = set(m2.get("content", "").lower().split())
        if not c1 or not c2:
            return 0.0
        intersection = c1 & c2
        union = c1 | c2
        return len(intersection) / len(union)

    def _is_unresolved(self, memory: dict) -> bool:
        """Check if a memory represents an unresolved problem."""
        content = memory.get("content", "").lower()
        markers = ["unresolved", "pending", "todo", "problem", "issue",
                   "needs", "should fix", "broken", "error", "failed"]
        return any(m in content for m in markers)

    def _reevaluate_problem(self, problem: dict, context: List[dict]) -> bool:
        """Attempt to resolve a problem given broader context.
        In the MVP, just marks it as revisited with any new context clues."""
        # In a future version, this would invoke the LLM with the context
        return True

    def _find_most_distant_pair(self, memories: list) -> Optional[tuple]:
        """Find the most semantically distant pair in a sample."""
        if len(memories) < 2:
            return None
        min_sim = float("inf")
        pair = None
        for i in range(len(memories)):
            for j in range(i + 1, len(memories)):
                sim = self._estimate_similarity(memories[i], memories[j])
                if sim < min_sim:
                    min_sim = sim
                    pair = (memories[i], memories[j])
        return pair

    def _invent_from_pair(self, m1: dict, m2: dict) -> bool:
        """Generate a novel idea from two distant memories.
        Simple version: produces a text description."""
        idea = (
            f"Connection between: [{m1.get('content', '')[:80]}] "
            f"and [{m2.get('content', '')[:80]}]"
        )
        try:
            invention_record = {
                "id": str(uuid.uuid4())[:8],
                "type": "invented_during_dream",
                "content": idea,
                "sources": [m1.get("id", ""), m2.get("id", "")],
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            self._append_journal({"invention": invention_record})
            return True
        except Exception:
            return False

    # ── Journal ─────────────────────────────────────────────

    def _append_journal(self, entry: dict) -> None:
        """Append an entry to the journal file."""
        journal = []
        if self.journal_path.exists():
            try:
                journal = json.loads(self.journal_path.read_text())
            except Exception:
                journal = []
        journal.append(entry)
        # Keep last 200 entries
        journal = journal[-200:]
        self.journal_path.write_text(
            json.dumps(journal, indent=2, ensure_ascii=False)
        )

    def read_journal(self, limit: int = 50) -> List[dict]:
        """Read dream journal entries, newest first."""
        if not self.journal_path.exists():
            return []
        try:
            journal = json.loads(self.journal_path.read_text())
            return list(reversed(journal[-limit:]))
        except Exception:
            return []
