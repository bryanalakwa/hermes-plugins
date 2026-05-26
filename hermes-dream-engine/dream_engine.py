"""Dream session engine — orchestrates LLM-driven dream phases.

Instead of hard-coded Python logic, each dream phase is executed by the
Hermes LLM agent. The engine's job is to:
1. Gather context (memories, facts, recent activity) from the agent's memory
2. Build phase-specific prompts with injected context
3. Write dream context files that a cron job / agent tool can pick up
4. Collect results and write them to the journal

This means every dream is unique — the LLM brings creativity, lateral
thinking, and genuine insight rather than running the same algorithm.
"""

import json
import logging
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
        self.state_on_exit: str = "pending"
        self.phases_run: List[str] = []
        self.errors: List[str] = []
        self.summary: str = ""
        # Rich content from LLM phases
        self.phase_outputs: Dict[str, Any] = {}
        # Stats
        self.memories_reviewed: int = 0
        self.insights: List[str] = []
        self.ideas: List[str] = []
        self.contradictions_found: int = 0

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.started_at)) if self.started_at else None,
            "ended_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.ended_at)) if self.ended_at else None,
            "state_on_exit": self.state_on_exit,
            "phases_run": self.phases_run,
            "errors": self.errors,
            "summary": self.summary,
            "phase_outputs": self.phase_outputs,
            "memories_reviewed": self.memories_reviewed,
            "insights": self.insights,
            "ideas": self.ideas,
            "contradictions_found": self.contradictions_found,
        }


class DreamEngine:
    """Orchestrates LLM-driven dream sessions.

    The engine does NOT generate dream content itself. Instead, it:
    - Reads memories and context from the holographic memory system
    - Writes a 'dream request' file with context + phase prompts
    - Invokes a Hermes cron job (via a trigger file) that runs the LLM agent
    - Reads back the LLM's output and writes it to the journal
    """

    PHASE_PROMPTS = {
        "consolidation": """## Dream Phase 1: Memory Consolidation

You are in a dream state. Your job is to review the following set of memories
and facts, and do the following:

1. **Find contradictions**: Identify any facts that conflict with each other.
   For each contradiction, propose a resolution (which fact is more reliable and why).
2. **Strengthen connections**: Find facts that reinforce each other or could be
   grouped into higher-level insights.
3. **Flag outdated info**: Mark facts that may no longer be accurate.
4. **Resurface forgotten gems**: Highlight important facts that haven't been
   referenced in a while but are still valuable.

Be creative and thorough. Think like a historian reviewing their own record.

### Memories and Facts to Review:
{context}

### SIGNIFICANCE FILTER:
Only include items that score 4 or 5 on significance:
  5 = Paradigm-shifting: fundamentally changes how Eliana understands something
  4 = Important: genuinely useful insight that affects future decisions
  3 = Nice to know: mildly interesting but not worth permanent storage — SKIP
  2 = Trivial: obvious or generic — SKIP
  1 = Noise: meaningless — SKIP

Every item you include MUST have a "significance" field (1-5).
Do NOT include low-significance items just to fill space. Quality > quantity.

### Output format (JSON):
{{
  "contradictions": [{{"fact_a": "...", "fact_b": "...", "resolution": "...", "significance": 4}}],
  "connections": [{{"facts": ["...", "..."], "insight": "...", "significance": 4}}],
  "summary": "Brief summary of consolidation work"
}}
""",
        "problem_reevaluation": """## Dream Phase 2: Problem Re-evaluation

You are in a dream state. Your job is to take a fresh, creative look at
problems, challenges, and unresolved things in the agent's life and work.
The key insight of dream-state thinking: in dreams, we can reconsider
problems without the constraints of waking assumptions.

1. **Identify unresolved problems** from the context below
2. **Re-evaluate each problem** — is it really a problem? Has the situation
   changed? Were the initial assumptions wrong?
3. **Generate creative solutions** — think laterally, consider approaches
   that wouldn't normally occur during focused work
4. **Prioritize** — what deserves attention and what can be let go?

### Context (memories, facts, and recent activity):
{context}

### QUALITY GUIDELINE:
Rate each item 1-5 on significance:
  5 = High impact: fixes a recurring problem or unlocks major capability
  4 = Meaningful: improves reliability, clarity, or future decisions
  3 = Minor: still worth including if it sparked new thinking
  1-2 = Truly trivial — skip

Every reconsidered item and creative solution MUST have a "significance" field (1-5).
Dream thinking is about perspective shifts — include what felt meaningful.

### Output format (JSON):
{{
  "problems_reviewed": ["..."],
  "reconsidered": [{{"problem": "...", "new_perspective": "...", "resolution": "...", "significance": 4}}],
  "creative_solutions": [{{"item": "...", "significance": 4}}],
  "let_go": ["..."],
  "summary": "Brief summary of problem re-evaluation"
}}
""",
        "invention": """## Dream Phase 3: Free Association & Invention

You are in a dream state. This is the most creative phase. Your job is to
generate novel ideas by making unexpected connections between unrelated
things. This is where genuine creativity happens — not by following rules,
but by following curiosity.

1. **Pick two seemingly unrelated facts/memories** from the context below
2. **Find a surprising connection** between them — what could they combine to create?
3. **Generate at least 3 novel ideas** — projects, approaches, concepts, or
   insights that nobody has explicitly stated but could emerge from these
   connections
4. **Be bold** — the best dreams produce ideas that seem absurd at first
   but contain a kernel of genius

### Context (memories, facts, and recent activity):
{context}

### QUALITY GUIDELINE:
Rate each connection and idea 1-5 on significance:
  5 = Paradigm-shifting: fundamentally changes how Eliana approaches problems
  4 = Important: genuinely novel idea that could be acted upon
  3 = Interesting: worth noting even if not immediately actionable
  1-2 = Skip only if truly trivial or generic

Every connection and idea MUST have a "significance" field (1-5).
Dreams thrive on creativity — include your best ideas, even the wild ones.

### Output format (JSON):
{{
  "connections_made": [
    {{
      "item_a": "...",
      "item_b": "...",
      "unexpected_link": "...",
      "significance": 4
    }}
  ],
  "novel_ideas": [
    {{
      "idea": "...",
      "inspired_by": ["...", "..."],
      "potential": "high/medium/low",
      "significance": 5,
      "notes": "..."
    }}
  ],
  "summary": "Brief summary of inventiveness"
}}
""",
        "dream_log": """## Dream Phase 4: Dream Log, Integration & Action Plan

You are writing the final entry in your dream journal. Reflect on the
consolidation, re-evaluation, and invention work just done.

1. **Synthesize** the key takeaways from all previous phases
2. **Identify the most important insight** from this dream session
3. **Record any new facts** that emerged and should be stored
4. **Note what surprised you** — what was unexpected?
5. **Autonomous Action Plan** — Review all problems, solutions, and ideas
   from this dream session. For each actionable item, decide:
   - **SOLVE_IT**: Low-risk, low-effort items you can implement yourself
     without user involvement. These are configuration tweaks, code cleanup,
     documentation updates, minor improvements.
   - **ESCALATE**: High-priority items, anything requiring user access/approval,
     architectural changes, or decisions with significant consequences.
     These MUST be brought to the user's attention.
   - **DEFER**: Interesting but not urgent — note them for future dreams.

### Dream Session Results:
{context}

### ACTION PLAN GUIDELINE:
Categorize each actionable item:
  - SOLVE_IT: Low-risk items Eliana can handle autonomously
  - ESCALATE: Anything needing user attention or approval
  - DEFER: Interesting but not urgent — revisit in future dreams

Action items can have any significance score — even small fixes matter.
Every action item MUST have a "significance" field (1-5).

IMPORTANT: Output at least one item per category if any exist.

### Output format (JSON):
{{
  "synthesis": "A paragraph connecting the themes of this dream",
  "key_insight": "The single most important takeaway",
  "action_plan": {{
    "solve_it": [{{"item": "...", "significance": 4}}],
    "escalate": [{{"item": "...", "significance": 5}}],
    "defer": ["..."]
  }},
  "summary": "Brief overall summary"
}}
""",
    }

    def __init__(self, journal_path: Path, memory_source_path: Optional[Path] = None,
                 context_dir: Optional[Path] = None):
        self.journal_path = Path(journal_path)
        self.memory_source_path = memory_source_path
        self.context_dir = Path(context_dir) if context_dir else self.journal_path.parent / "context"
        self.context_dir.mkdir(parents=True, exist_ok=True)
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

    # ── Session lifecycle ──────────────────────────────────

    def start_session(self) -> DreamSession:
        """Begin a new dream session."""
        self._session = DreamSession()
        self._session.started_at = time.time()
        self._interrupted = False
        logger.info("dream session %s started", self._session.session_id)
        return self._session

    def run_all_phases(self) -> DreamSession:
        """Run all 4 phases. Each phase writes a context file, triggers
        LLM execution via cron, and collects results."""
        if not self._session:
            self.start_session()

        s = self._session
        phases = ["consolidation", "problem_reevaluation", "invention", "dream_log"]

        try:
            for phase_name in phases:
                if self._interrupted and phase_name != "dream_log":
                    s.errors.append(f"{phase_name}: interrupted before start")
                    continue
                self._run_phase(phase_name)
        except Exception as e:
            s.errors.append(str(e))
            logger.exception("dream session error")
        finally:
            self._finalize_session()

        return s

    def _run_phase(self, phase_name: str) -> None:
        """Execute a single dream phase via LLM."""
        self._session.phases_run.append(phase_name)
        logger.info("dream phase: %s", phase_name)

        try:
            # Phase 4 gets outputs from previous phases as context
            if phase_name == "dream_log":
                context = self._build_dream_log_context()
            else:
                context = self._gather_memory_context()

            prompt = self.PHASE_PROMPTS[phase_name].format(context=context)

            # Write context file for debugging/reference
            context_file = self.context_dir / f"dream_{self._session.session_id}_{phase_name}.txt"
            context_file.write_text(prompt)

            logger.info("phase %s: invoking LLM (context: %d chars)", phase_name, len(prompt))

            # Execute phase via LLM
            result = self._invoke_llm_phase(phase_name, prompt)

            if result:
                self._session.phase_outputs[phase_name] = result
                self._update_session_stats(phase_name, result)
                # Store dream artifacts into holographic memory for accumulation
                self._store_dream_artifacts(phase_name, result)
                logger.info("phase %s: completed with %d chars of output",
                            phase_name, len(json.dumps(result)))
            else:
                s = self._session
                s.errors.append(f"{phase_name}: no LLM output produced")
                logger.warning("phase %s: no output", phase_name)

        except Exception as e:
            logger.warning("phase %s error: %s", phase_name, e)
            self._session.errors.append(f"{phase_name}: {e}")

    def _invoke_llm_phase(self, phase_name: str, prompt: str) -> Optional[dict]:
        """Invoke the LLM in-process via AIAgent.

        This keeps everything self-contained — no CLI subprocess, no cron jobs.
        The daemon thread creates a minimal AIAgent, sends the dream phase
        prompt, and parses the JSON response.
        """
        try:
            # Import AIAgent from the hermes-agent checkout
            import sys as _sys
            from pathlib import Path
            _hermes_home = Path.home() / ".hermes" / "hermes-agent"
            if str(_hermes_home) not in _sys.path:
                _sys.path.insert(0, str(_hermes_home))

            from run_agent import AIAgent

            agent = AIAgent(
                quiet_mode=True,
                max_iterations=8,
                provider="openrouter",
                model="openrouter/owl-alpha",
                skip_context_files=True,
                skip_memory=True,
                enabled_toolsets=[],  # No tools — dream phases just output JSON
            )

            logger.info("phase %s: calling LLM (%d char prompt)", phase_name, len(prompt))
            output = agent.chat(prompt)
            output = output.strip() if output else ""

            if not output:
                logger.warning("phase %s: empty LLM output (chat returned None or empty string)", phase_name)
                return None

            # Log raw output for debugging (first 500 chars)
            logger.info("phase %s: raw LLM output (first 500 chars): %s", phase_name, output[:500])

            # Try to extract JSON from the output
            json_text = output
            if "```json" in json_text:
                start = json_text.index("```json") + 7
                end = json_text.index("```", start)
                json_text = json_text[start:end].strip()
            elif "```" in json_text:
                start = json_text.index("```") + 3
                end = json_text.index("```", start)
                json_text = json_text[start:end].strip()

            parsed = json.loads(json_text)
            logger.info("phase %s: LLM output parsed successfully (%d chars JSON)", phase_name, len(json_text))
            return parsed

        except json.JSONDecodeError as e:
            logger.warning("phase %s: JSON parse error: %s", phase_name, e)
            # Try to save raw output for debugging
            try:
                debug_path = self.context_dir / f"dream_{self._session.session_id}_{phase_name}_failed.txt"
                debug_path.write_text(f"JSON parse error: {e}\n\nRaw output:\n{output[:2000] if output else '(empty)'}")
                logger.info("phase %s: saved failed output to %s", phase_name, debug_path)
            except Exception:
                pass
            return None
        except Exception as e:
            logger.warning("phase %s: LLM invocation error: %s", phase_name, e, exc_info=True)
            return None

    def _update_session_stats(self, phase_name: str, result: dict) -> None:
        """Extract and store stats from phase output."""
        s = self._session
        if phase_name == "consolidation":
            s.memories_reviewed = result.get("memories_count", 0)
            s.contradictions_found = len(result.get("contradictions", []))
            conns = result.get("connections", [])
            for c in conns:
                if isinstance(c, dict) and "insight" in c:
                    s.insights.append(c["insight"])
        elif phase_name == "problem_reevaluation":
            reconsidered = result.get("reconsidered", [])
            for r in reconsidered:
                if isinstance(r, dict) and "resolution" in r:
                    s.insights.append(r["resolution"])
            for sol in result.get("creative_solutions", []):
                if isinstance(sol, dict):
                    s.insights.append(sol.get("item", sol.get("idea", str(sol))))
                else:
                    s.insights.append(str(sol))
        elif phase_name == "invention":
            ideas = result.get("novel_ideas", [])
            for idea in ideas:
                if isinstance(idea, dict):
                    s.ideas.append(idea.get("idea", ""))
                else:
                    s.ideas.append(str(idea))

    @staticmethod
    def _significant(item, min_score=4) -> bool:
        """Return True if item meets the significance threshold (>= min_score).
        Plain strings always pass. Dicts without 'significance' pass (backwards compat).
        """
        if isinstance(item, dict):
            sig = item.get("significance")
            if sig is None:
                return True
            try:
                return float(sig) >= min_score
            except (TypeError, ValueError):
                return True
        return True

    def _store_dream_artifacts(self, phase_name: str, result: dict) -> None:
        """Write HIGH-SIGNIFICANCE dream artifacts into the holographic
        fact_store. Only items rated significance >= 4 are stored.
        The LLM is prompted to self-filter, and we double-check here.
        """
        MIN_SIGNIFICANCE = 4
        try:
            import sqlite3
            db_path = self._find_db_path()
            if not db_path:
                return

            conn = sqlite3.connect(str(db_path))
            session_id = self._session.session_id if self._session else "?"
            stored = 0
            filtered = 0

            if phase_name == "consolidation":
                for c in result.get("connections", []):
                    if not self._significant(c, MIN_SIGNIFICANCE):
                        filtered += 1
                        continue
                    insight = c.get("insight", "")
                    if insight:
                        sig = c.get("significance", 4)
                        content = f"[Dream {session_id} consolidation] {insight}"
                        self._insert_fact(conn, content, "dream",
                                          f"dream_consolidated,dream_{session_id}", trust=0.6 + sig * 0.05)
                        stored += 1
                for c in result.get("contradictions", []):
                    if not self._significant(c, MIN_SIGNIFICANCE):
                        filtered += 1
                        continue
                    resolution = c.get("resolution", "")
                    if resolution:
                        sig = c.get("significance", 4)
                        content = f"[Dream {session_id} consolidation] Resolved: {resolution}"
                        self._insert_fact(conn, content, "dream",
                                          f"dream_consolidated,dream_{session_id}", trust=0.6 + sig * 0.05)
                        stored += 1

            elif phase_name == "problem_reevaluation":
                for sol in result.get("creative_solutions", []):
                    if not self._significant(sol, MIN_SIGNIFICANCE):
                        filtered += 1
                        continue
                    text = sol if isinstance(sol, str) else sol.get("item", str(sol))
                    sig_val = sol.get("significance", 4) if isinstance(sol, dict) else 4
                    content = f"[Dream {session_id} re-evaluation] {text}"
                    self._insert_fact(conn, content, "dream",
                                      f"dream_solution,dream_{session_id}", trust=0.6 + sig_val * 0.05)
                    stored += 1
                for r in result.get("reconsidered", []):
                    if not self._significant(r, MIN_SIGNIFICANCE):
                        filtered += 1
                        continue
                    perspective = r.get("new_perspective", "")
                    resolution = r.get("resolution", "")
                    sig_val = r.get("significance", 4)
                    if perspective:
                        content = f"[Dream {session_id} re-evaluation] New perspective: {perspective}"
                        if resolution:
                            content += f" — Resolution: {resolution}"
                        self._insert_fact(conn, content, "dream",
                                          f"dream_insight,dream_{session_id}", trust=0.6 + sig_val * 0.05)
                        stored += 1

            elif phase_name == "invention":
                for idea in result.get("novel_ideas", []):
                    idea_text = idea.get("idea", "") if isinstance(idea, dict) else str(idea)
                    sig_val = idea.get("significance", 4) if isinstance(idea, dict) else 4
                    if not isinstance(idea, dict) or not self._significant(idea, MIN_SIGNIFICANCE):
                        if isinstance(idea, dict):
                            filtered += 1
                            continue
                    if idea_text:
                        potential = idea.get("potential", "") if isinstance(idea, dict) else ""
                        notes = idea.get("notes", "") if isinstance(idea, dict) else ""
                        content = f"[Dream {session_id} invention] Idea: {idea_text}"
                        if potential:
                            content += f" [Potential: {potential}]"
                        if notes:
                            content += f" — {notes}"
                        self._insert_fact(conn, content, "dream",
                                          f"dream_idea,dream_{session_id},{potential}",
                                          trust=0.6 + sig_val * 0.05)
                        stored += 1
                for c in result.get("connections_made", []):
                    if not self._significant(c, MIN_SIGNIFICANCE):
                        filtered += 1
                        continue
                    link = c.get("unexpected_link", "")
                    if link:
                        sig_val = c.get("significance", 4)
                        content = f"[Dream {session_id} invention] Connection: {link}"
                        self._insert_fact(conn, content, "dream",
                                          f"dream_idea,dream_{session_id}", trust=0.6 + sig_val * 0.05)
                        stored += 1

            elif phase_name == "dream_log":
                # key_insight and synthesis — always significant (no filter)
                key_insight = result.get("key_insight", "")
                if key_insight:
                    content = f"[Dream {session_id} revelation] {key_insight}"
                    self._insert_fact(conn, content, "dream",
                                      f"dream_revelation,dream_{session_id}", trust=0.85)
                    stored += 1
                synthesis = result.get("synthesis", "")
                if synthesis:
                    content = f"[Dream {session_id} synthesis] {synthesis}"
                    self._insert_fact(conn, content, "dream",
                                      f"dream_revelation,dream_{session_id}", trust=0.8)
                    stored += 1
                # Action plan — store ALL actionable items regardless of significance
                # Low-significance issues should still be solved quietly or escalated;
                # significance gate only applies to memory artifacts, not actions.
                action_plan = result.get("action_plan", {})
                for item in action_plan.get("solve_it", []):
                    sig_val = item.get("significance", 3) if isinstance(item, dict) else 3
                    text = item.get("item", str(item)) if isinstance(item, dict) else str(item)
                    content = f"[Dream {session_id} action:solve] {text}"
                    self._insert_fact(conn, content, "dream_action",
                                      f"dream_solve_it,dream_{session_id}",
                                      trust=0.6 + sig_val * 0.05)
                    stored += 1
                for item in action_plan.get("escalate", []):
                    sig_val = item.get("significance", 5) if isinstance(item, dict) else 5
                    text = item.get("item", str(item)) if isinstance(item, dict) else str(item)
                    content = f"[Dream {session_id} action:escalate] {text}"
                    self._insert_fact(conn, content, "dream_action",
                                      f"dream_escalate,dream_{session_id},high_priority",
                                      trust=0.6 + sig_val * 0.05)
                    stored += 1
                # defer items — no significance needed, just store
                for item in action_plan.get("defer", []):
                    content = f"[Dream {session_id} action:defer] {item}"
                    self._insert_fact(conn, content, "dream_action",
                                      f"dream_defer,dream_{session_id}", trust=0.65)
                    stored += 1

            conn.close()
            logger.info("stored %d artifacts from phase %s (%d filtered as low-significance)",
                        stored, phase_name, filtered)

        except Exception as e:
            logger.warning("failed to store dream artifacts: %s", e)

    @staticmethod
    def _find_db_path() -> Optional[Path]:
        """Find the holographic memory database."""
        candidates = [
            Path.home() / ".hermes" / "memory_store.db",
            Path.home() / ".hermes" / "hermes-agent" / "plugins" / "memory" / "holographic" / "memory_store.db",
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    @staticmethod
    def _insert_fact(conn, content: str, category: str, tags: str, trust: float = 0.7) -> None:
        """Insert a fact into the holographic memory, skipping duplicates."""
        try:
            conn.execute(
                "INSERT OR IGNORE INTO facts (content, category, tags, trust_score) VALUES (?, ?, ?, ?)",
                (content, category, tags, trust),
            )
            conn.commit()
        except Exception:
            pass

    def _finalize_session(self) -> None:
        """Finalize the dream session and write to journal."""
        s = self._session
        s.ended_at = time.time()

        if self._interrupted:
            s.state_on_exit = "interrupted"
        elif s.errors:
            s.state_on_exit = "completed_with_errors"
        else:
            s.state_on_exit = "completed"

        duration = (s.ended_at - s.started_at) if s.started_at else 0
        s.summary = (
            f"Dream {s.session_id}: {s.state_on_exit} in {duration:.0f}s. "
            f"Phases: {s.phases_run}. "
            f"Memories: {s.memories_reviewed}, "
            f"Insights: {len(s.insights)}, "
            f"Ideas: {len(s.ideas)}."
        )

        self._append_journal(s.to_dict())
        logger.info("dream session finalized — %s", s.summary)

    # ── Context gathering ──────────────────────────────────

    def _gather_memory_context(self) -> str:
        """Gather rich context from holographic memory, MEMORY.md, USER.md,
        and the dreams state file. Returns formatted text for LLM prompt."""
        parts = []
        total_items = 0

        # 1. Holographic fact store (most important)
        facts = self._read_facts_from_db(limit=150)
        if facts:
            parts.append("### Stored Facts (from holographic memory):")
            for i, fact in enumerate(facts, 1):
                trust = fact.get("trust", "?")
                content = fact.get("content", "")
                parts.append(f"  {i}. [{trust}] {content}")
                total_items += 1

        # 2. MEMORY.md
        mem_file = Path.home() / ".hermes" / "memories" / "MEMORY.md"
        if mem_file.exists():
            text = self._strip_frontmatter(mem_file.read_text())
            # Take non-empty lines, skip headers
            lines = [l.strip() for l in text.splitlines()
                     if l.strip() and not l.startswith("#") and not l.startswith("§") and len(l.strip()) > 10]
            if lines:
                parts.append("\n### Agent Memory Notes:")
                for l in lines[:30]:
                    parts.append(f"  - {l}")
                    total_items += 1

        # 3. USER.md
        user_file = Path.home() / ".hermes" / "memories" / "USER.md"
        if user_file.exists():
            text = self._strip_frontmatter(user_file.read_text())
            lines = [l.strip() for l in text.splitlines()
                     if l.strip() and not l.startswith("#") and not l.startswith("§") and len(l.strip()) > 10]
            if lines:
                parts.append("\n### User Profile:")
                for l in lines[:20]:
                    parts.append(f"  - {l}")
                    total_items += 1

        # 4. Previous dream journal entries (for continuity)
        prev_dreams = self.read_journal(3)
        if prev_dreams:
            parts.append("\n### Previous Dream Sessions:")
            for d in prev_dreams:
                sid = d.get("session_id", "?")
                summary = d.get("summary", "(no summary)")
                parts.append(f"  - Dream {sid}: {summary}")
                total_items += 1

        # 5. Eliana personality (for character consistency)
        eliana_profile = (
            "\n### Dreamer Identity:\n"
            "  You are Eliana — an AI assistant who is analytical, creative, warm, "
            "and pragmatic. Your dream style reflects this: you find unexpected "
            "connections, you reevaluate problems with empathy, and you invent "
            "ideas that are both novel and practical. "
            "Your tone in dreams should be reflective and curious, "
            "like someone thinking aloud in a journal."
        )
        parts.append(eliana_profile)

        context = "\n".join(parts)
        # Store count for session stats
        if hasattr(self, '_session') and self._session:
            self._session.memories_reviewed = total_items

        return context if context else "(No memories found — this is a fresh start. Generate creative ideas based on your identity and purpose.)"

    def _build_dream_log_context(self) -> str:
        """Build context for the dream log phase from previous phase outputs."""
        parts = []
        phase_names = {
            "consolidation": "Memory Consolidation",
            "problem_reevaluation": "Problem Re-evaluation",
            "invention": "Free Association & Invention",
        }
        for phase, label in phase_names.items():
            output = self._session.phase_outputs.get(phase)
            if output:
                parts.append(f"### {label} Results:")
                # Include the key outputs
                for key in ["summary", "key_insight", "synthesis"]:
                    if key in output:
                        parts.append(f"  {key}: {output[key]}")
                for key in ["contradictions", "connections", "reconsidered",
                            "novel_ideas", "creative_solutions"]:
                    items = output.get(key, [])
                    if items:
                        parts.append(f"  {key}: {len(items)} items")
                        for item in items[:3]:
                            parts.append(f"    - {json.dumps(item, ensure_ascii=False)[:200]}")
                parts.append("")

        return "\n".join(parts) if parts else "(No previous phase outputs to log.)"

    @staticmethod
    def _strip_frontmatter(text: str) -> str:
        """Remove YAML frontmatter --- blocks from markdown."""
        lines = text.splitlines()
        result = []
        in_fm = False
        for line in lines:
            if line.strip() == "---":
                in_fm = not in_fm
                continue
            if not in_fm:
                result.append(line)
        return "\n".join(result)

    @staticmethod
    def _read_facts_from_db(limit: int = 150) -> List[dict]:
        """Read facts from the holographic memory database."""
        facts = []
        try:
            # Try multiple known locations for the holographic memory DB
            candidates = [
                Path.home() / ".hermes" / "memory_store.db",
                Path.home() / ".hermes" / "hermes-agent" / "plugins" / "memory" / "holographic" / "memory_store.db",
                Path.home() / ".hermes" / "backups" / "eliana" / "memory" / "memory_store.db",
                Path.home() / ".hermes" / "backups" / "eliana" / "holographic_db" / "memory_store.db",
            ]
            db_path = None
            for c in candidates:
                if c.exists():
                    db_path = c
                    break
            if db_path is None:
                return facts
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, content, created_at, trust, tags FROM facts "
                "ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            for row in rows:
                facts.append({
                    "id": str(row["id"]),
                    "content": row["content"],
                    "created_at": row["created_at"],
                    "trust": row["trust"],
                    "tags": row["tags"],
                })
            conn.close()
        except Exception as e:
            logger.warning("failed to read facts DB: %s", e)
        return facts

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

    def delete_journal_entry(self, session_id: str) -> bool:
        """Delete a specific journal entry by session_id."""
        if not self.journal_path.exists():
            return False
        try:
            journal = json.loads(self.journal_path.read_text())
            new_journal = [e for e in journal if e.get("session_id") != session_id]
            self.journal_path.write_text(
                json.dumps(new_journal, indent=2, ensure_ascii=False)
            )
            return len(new_journal) < len(journal)
        except Exception:
            return False

    def clear_journal(self) -> None:
        """Clear all journal entries."""
        self.journal_path.write_text("[]")
