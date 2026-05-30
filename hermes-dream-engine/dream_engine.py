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

# Import trust_scoring from hermes-agent's holographic memory plugin
_hermes_home = Path.home() / ".hermes" / "hermes-agent"
import sys
if str(_hermes_home) not in sys.path:
    sys.path.insert(0, str(_hermes_home))
from plugins.memory.holographic import trust_scoring

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
        # HRR-generated title (set during finalization)
        self.hrr_title: str = ""
        # Cognitive budget (set during finalization)
        self.cognitive_budget: dict = {}

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
            "hrr_title": self.hrr_title,
            "cognitive_budget": self.cognitive_budget,
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
  "synthesis": "A paragraph connecting the themes of this dream — REQUIRED field, must be named exactly 'synthesis'",
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

    # ── Cognitive Budget Allocator ────────────────────────────

    class CognitiveBudget:
        """Computes and stores the cognitive budget for a dream session.

        The budget determines how much "mental effort" to expend based on
        available context richness. Sparse context = shallow dreams.
        Rich context = deep, creative dreams.

        Budget dimensions:
        - memory_count: how many facts to feed the LLM (50-250)
        - connection_target: how many novel connections to attempt (3-15)
        - skip_invention: whether to skip invention phase when context is thin
        - depth_label: human-readable label for the journal
        """

        # Mode overrides
        MODES = {
            "minimal": {"memory_count": 50, "connection_target": 3, "skip_invention": True, "depth_label": "minimal"},
            "adaptive": None,  # computed from signals
            "always_deep": {"memory_count": 250, "connection_target": 12, "skip_invention": False, "depth_label": "deep"},
        }

        def __init__(self, signals: dict, mode: str = "adaptive"):
            if mode != "adaptive" and mode in self.MODES and self.MODES[mode]:
                self.budget = dict(self.MODES[mode])
                self.budget["mode"] = mode
                self.budget["richness_score"] = None
            else:
                self.budget = self._compute_adaptive(signals)
                self.budget["mode"] = "adaptive"
            self.budget["signals"] = signals

        @staticmethod
        def _compute_adaptive(signals: dict) -> dict:
            """Compute budget from context signals.

            Signals expected:
            - facts_count: int
            - avg_trust: float (0-1)
            - recency_ratio: float (facts updated in last 7 days / total)
            - recent_dream_quality: float (avg insights+ideas from last 3 dreams)
            - recent_error_rate: float (phases with errors / total phases in last 3)
            """
            facts_count = signals.get("facts_count", 0)
            avg_trust = signals.get("avg_trust", 0.5)
            recency_ratio = signals.get("recency_ratio", 0.5)
            recent_quality = signals.get("recent_dream_quality", 0.5)
            error_rate = signals.get("recent_error_rate", 0.0)

            # Richness score: weighted combination
            # Normalize facts_count: 0-50 facts = sparse, 50-200 = moderate, 200+ = rich
            count_score = min(facts_count / 150.0, 1.0)

            richness = (
                count_score * 0.30 +
                avg_trust * 0.25 +
                recency_ratio * 0.20 +
                min(recent_quality / 10.0, 1.0) * 0.15 +
                max(0.0, 1.0 - error_rate) * 0.10
            )
            richness = max(0.0, min(1.0, richness))

            # Map richness to parameters
            if richness < 0.2:
                depth_label = "minimal"
                memory_count = 50
                connection_target = 3
                skip_invention = True
            elif richness < 0.4:
                depth_label = "light"
                memory_count = 80
                connection_target = 5
                skip_invention = False
            elif richness < 0.6:
                depth_label = "moderate"
                memory_count = 120
                connection_target = 7
                skip_invention = False
            elif richness < 0.8:
                depth_label = "deep"
                memory_count = 180
                connection_target = 10
                skip_invention = False
            else:
                depth_label = "very_deep"
                memory_count = 250
                connection_target = 15
                skip_invention = False

            return {
                "richness_score": round(richness, 3),
                "memory_count": memory_count,
                "connection_target": connection_target,
                "skip_invention": skip_invention,
                "depth_label": depth_label,
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
        # Cognitive budget state (computed at session start)
        self._cognitive_budget: Optional[dict] = None

    @property
    def is_running(self) -> bool:
        return self._session is not None

    def interrupt(self) -> None:
        """Signal the current dream session to stop after the current phase."""
        self._interrupted = True

    # ── Cognitive Budget: signal computation ───────────────────

    def _compute_budget_signals(self) -> dict:
        """Gather signals for the cognitive budget computation.

        Returns dict with facts_count, avg_trust, recency_ratio,
        recent_dream_quality, and recent_error_rate.
        """
        signals = {
            "facts_count": 0,
            "avg_trust": 0.5,
            "recency_ratio": 0.5,
            "recent_dream_quality": 5.0,
            "recent_error_rate": 0.0,
        }

        # 1. Holographic DB stats
        try:
            import sqlite3
            db_path = self._find_db_path()
            if db_path:
                conn = sqlite3.connect(str(db_path))
                row = conn.execute(
                    "SELECT COUNT(*) as cnt, AVG(trust_score) as avg_trust FROM facts"
                ).fetchone()
                signals["facts_count"] = row[0] or 0
                signals["avg_trust"] = row[1] or 0.5

                # Recency: ratio of facts updated in last 7 days
                recent = conn.execute(
                    "SELECT COUNT(*) FROM facts WHERE created_at > datetime('now', '-7 days')"
                ).fetchone()
                total = signals["facts_count"]
                signals["recency_ratio"] = (recent[0] / total) if total > 0 else 0.5
                conn.close()
        except Exception as e:
            logger.debug("budget signal (db stats): %s", e)

        # 2. Recent dream quality from journal
        try:
            recent_dreams = self.read_journal(3)
            if recent_dreams:
                total_insights = 0
                total_ideas = 0
                total_phases = 0
                total_errors = 0
                for d in recent_dreams:
                    total_insights += len(d.get("insights", []))
                    total_ideas += len(d.get("ideas", []))
                    phases = d.get("phases_run", [])
                    total_phases += len(phases)
                    total_errors += len(d.get("errors", []))
                n = len(recent_dreams)
                signals["recent_dream_quality"] = (total_insights + total_ideas) / n
                signals["recent_error_rate"] = (
                    total_errors / total_phases if total_phases > 0 else 0.0
                )
        except Exception as e:
            logger.debug("budget signal (journal): %s", e)

        return signals

    def _apply_cognitive_budget(self) -> dict:
        """Compute and apply the cognitive budget for the current session.

        Returns the budget dict for logging/journaling.
        """
        signals = self._compute_budget_signals()
        budget = DreamEngine.CognitiveBudget(signals, mode="adaptive")
        self._cognitive_budget = budget.budget
        logger.info(
            "cognitive budget: richness=%.2f depth=%s memory=%d connections=%d skip_inv=%s",
            self._cognitive_budget.get("richness_score", -1),
            self._cognitive_budget.get("depth_label", "?"),
            self._cognitive_budget.get("memory_count", 150),
            self._cognitive_budget.get("connection_target", 7),
            self._cognitive_budget.get("skip_invention", False),
        )
        return self._cognitive_budget

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
        LLM execution via cron, and collects results.

        The cognitive budget is computed before the first phase to determine
        memory retrieval breadth, connection depth, and whether to skip
        invention when context is thin.
        """
        if not self._session:
            self.start_session()

        s = self._session

        # Compute cognitive budget before running phases
        budget = self._apply_cognitive_budget()
        memory_count = budget.get("memory_count", 150)
        skip_invention = budget.get("skip_invention", False)
        connection_target = budget.get("connection_target", 7)

        # Build phase list, optionally skipping invention
        phases = ["consolidation", "problem_reevaluation"]
        if not skip_invention:
            phases.append("invention")
        phases.append("dream_log")

        if skip_invention:
            logger.info("cognitive budget: skipping invention phase (context too thin)")

        try:
            for phase_name in phases:
                if self._interrupted and phase_name != "dream_log":
                    s.errors.append(f"{phase_name}: interrupted before start")
                    continue
                # Pass budget parameters to _run_phase
                self._run_phase(phase_name, memory_count=memory_count,
                                connection_target=connection_target)
        except Exception as e:
            s.errors.append(str(e))
            logger.exception("dream session error")
        finally:
            self._finalize_session()

        return s

    def run_phase(self, phase_name: str, memory_count: int = 150,
                  connection_target: int = 7, **kwargs) -> DreamSession:
        """Execute a single dream phase independently.

        This enables selective invocation of phases without the full pipeline.
        Useful for targeted dream work or testing individual phases.

        Args:
            phase_name: Single phase to run (consolidation, problem_reevaluation,
                       invention, or dream_log)
            memory_count: How many facts to retrieve
            connection_target: How many connections to request (invention phase)
            **kwargs: Additional parameters for specific phases (e.g., topic)

        Returns:
            The DreamSession with this phase's output
        """
        if phase_name not in self.PHASE_PROMPTS:
            raise ValueError(f"Unknown phase: {phase_name}")

        if not self._session:
            self.start_session()

        s = self._session
        self._cognitive_budget = self._apply_cognitive_budget()

        try:
            self._run_phase(phase_name, memory_count=memory_count,
                            connection_target=connection_target, **kwargs)
            self._session.state_on_exit = "single_phase"
        except Exception as e:
            s.errors.append(str(e))
            logger.exception("single phase error")

        return s

    def run_composed(self, phase_list: list[str], memory_count: int = 150,
                     connection_target: int = 7) -> DreamSession:
        """Execute a custom sequence of dream phases.

        Unlike run_all_phases(), this allows arbitrary phase composition.
        Phases are run in order, with dream_log always added at the end
        if not already present.

        Args:
            phase_list: Ordered list of phases to run
            memory_count: How many facts to retrieve
            connection_target: How many connections to request

        Returns:
            The DreamSession with all phase outputs
        """
        if not self._session:
            self.start_session()

        s = self._session
        self._cognitive_budget = self._apply_cognitive_budget()

        # Ensure dream_log runs last if not specified
        phases = list(phase_list)
        if "dream_log" not in phases:
            phases.append("dream_log")

        try:
            for phase_name in phases:
                if self._interrupted and phase_name != "dream_log":
                    s.errors.append(f"{phase_name}: interrupted before start")
                    continue
                self._run_phase(phase_name, memory_count=memory_count,
                                  connection_target=connection_target)
        except Exception as e:
            s.errors.append(str(e))
            logger.exception("composed session error")
        finally:
            self._finalize_session()

        return s

    def _check_phase_skip_conditions(self, phase_name: str) -> tuple[bool, str]:
        """Check if a phase should be skipped based on current state.

        Returns:
            Tuple of (should_skip, reason) - skips if conditions indicate
            no work is needed for that phase.
        """
        if phase_name == "consolidation":
            # Skip if no facts to consolidate
            facts = self._read_facts_from_db(limit=10)
            if not facts:
                return True, "no facts to consolidate"
            # Skip if all facts are recently reviewed
            stale_facts = [f for f in facts
                          if f.get("updated_at", "") < "recent"]
            if len(stale_facts) < 5:
                return True, "recent consolidation complete"

        elif phase_name == "problem_reevaluation":
            # Skip if no dream_action items pending
            pass  # Always run for fresh perspective

        elif phase_name == "invention":
            # Skip if low context richness
            if self._cognitive_budget.get("skip_invention", False):
                return True, "context too thin"

        return False, ""

    def _run_phase(self, phase_name: str, memory_count: int = 150,
                    connection_target: int = 7) -> None:
        """Execute a single dream phase via LLM.

        Args:
            phase_name: which phase to run
            memory_count: how many facts to retrieve (from cognitive budget)
            connection_target: how many connections to request (from cognitive budget)
        """
        self._session.phases_run.append(phase_name)
        logger.info("dream phase: %s", phase_name)

        try:
            # Phase 4 gets outputs from previous phases as context
            if phase_name == "dream_log":
                context = self._build_dream_log_context()
            else:
                context = self._gather_memory_context(limit=memory_count)

            #Inject connection target for invention phase
            if phase_name == "invention":
                context = (
                    f"### COGNITIVE BUDGET\n"
                    f"Target: approximately {connection_target} novel connections.\n"
                    f"Quality over quantity — only include genuinely surprising links.\n\n"
                    f"{context}"
                )

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

            # Helper to normalize significance (1-5 scale -> 0-1 scale) and compute trust
            def compute_trust(significance: int) -> float:
                return trust_scoring.compute_source_trust(
                    significance=significance / 5.0,
                    source="dream_hypothesis",
                    verification="dream_hypothesis",
                )

            if phase_name == "consolidation":
                for c in result.get("connections", []):
                    if not self._significant(c, MIN_SIGNIFICANCE):
                        filtered += 1
                        continue
                    insight = c.get("insight", "")
                    if insight:
                        sig = c.get("significance", 4)
                        content = f"[Dream {session_id} consolidation] {insight}"
                        trust = compute_trust(sig)
                        self._insert_fact(conn, content, "dream",
                                          f"dream_consolidated,dream_{session_id}", trust=trust)
                        stored += 1
                for c in result.get("contradictions", []):
                    if not self._significant(c, MIN_SIGNIFICANCE):
                        filtered += 1
                        continue
                    resolution = c.get("resolution", "")
                    if resolution:
                        sig = c.get("significance", 4)
                        content = f"[Dream {session_id} consolidation] Resolved: {resolution}"
                        trust = compute_trust(sig)
                        self._insert_fact(conn, content, "dream",
                                          f"dream_consolidated,dream_{session_id}", trust=trust)
                        stored += 1

            elif phase_name == "problem_reevaluation":
                for sol in result.get("creative_solutions", []):
                    if not self._significant(sol, MIN_SIGNIFICANCE):
                        filtered += 1
                        continue
                    text = sol if isinstance(sol, str) else sol.get("item", str(sol))
                    sig_val = sol.get("significance", 4) if isinstance(sol, dict) else 4
                    content = f"[Dream {session_id} re-evaluation] {text}"
                    trust = compute_trust(sig_val)
                    self._insert_fact(conn, content, "dream",
                                      f"dream_solution,dream_{session_id}", trust=trust)
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
                        trust = compute_trust(sig_val)
                        self._insert_fact(conn, content, "dream",
                                          f"dream_insight,dream_{session_id}", trust=trust)
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
                        trust = compute_trust(sig_val)
                        self._insert_fact(conn, content, "dream",
                                          f"dream_idea,dream_{session_id},{potential}", trust=trust)
                        stored += 1
                for c in result.get("connections_made", []):
                    if not self._significant(c, MIN_SIGNIFICANCE):
                        filtered += 1
                        continue
                    link = c.get("unexpected_link", "")
                    if link:
                        sig_val = c.get("significance", 4)
                        content = f"[Dream {session_id} invention] Connection: {link}"
                        trust = compute_trust(sig_val)
                        self._insert_fact(conn, content, "dream",
                                          f"dream_idea,dream_{session_id}", trust=trust)
                        stored += 1

            elif phase_name == "dream_log":
                # key_insight and synthesis — always significant (no filter)
                key_insight = result.get("key_insight", "")
                if key_insight:
                    content = f"[Dream {session_id} revelation] {key_insight}"
                    trust = compute_trust(5)  # Key insight gets max significance
                    self._insert_fact(conn, content, "dream",
                                      f"dream_revelation,dream_{session_id}", trust=trust)
                    stored += 1
                synthesis = result.get("synthesis", "") or result.get("synmthesis", "")
                if synthesis:
                    content = f"[Dream {session_id} synthesis] {synthesis}"
                    trust = compute_trust(4)  # Synthesis gets high significance
                    self._insert_fact(conn, content, "dream",
                                      f"dream_revelation,dream_{session_id}", trust=trust)
                    stored += 1
                # Action plan — store ALL actionable items regardless of significance
                # Low-significance issues should still be solved quietly or escalated;
                # significance gate only applies to memory artifacts, not actions.
                action_plan = result.get("action_plan", {})
                for item in action_plan.get("solve_it", []):
                    sig_val = item.get("significance", 3) if isinstance(item, dict) else 3
                    text = item.get("item", str(item)) if isinstance(item, dict) else str(item)
                    content = f"[Dream {session_id} action:solve] {text}"
                    trust = compute_trust(sig_val)
                    self._insert_fact(conn, content, "dream_action",
                                      f"dream_solve_it,dream_{session_id}", trust=trust)
                    stored += 1
                for item in action_plan.get("escalate", []):
                    sig_val = item.get("significance", 5) if isinstance(item, dict) else 5
                    text = item.get("item", str(item)) if isinstance(item, dict) else str(item)
                    content = f"[Dream {session_id} action:escalate] {text}"
                    trust = compute_trust(sig_val)
                    self._insert_fact(conn, content, "dream_action",
                                      f"dream_escalate,dream_{session_id},high_priority", trust=trust)
                    stored += 1
                # defer items — no significance needed, just store
                for item in action_plan.get("defer", []):
                    content = f"[Dream {session_id} action:defer] {item}"
                    trust = compute_trust(3)  # Defer items get moderate significance
                    self._insert_fact(conn, content, "dream_action",
                                      f"dream_defer,dream_{session_id}", trust=trust)
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
    def _insert_fact(
        conn,
        content: str,
        category: str,
        tags: str,
        trust: float = 0.7,
        source_context: str = "dream_hypothesis",
        verification_status: str = "dream_hypothesis",
    ) -> None:
        """Insert a fact into the holographic memory, skipping duplicates."""
        try:
            conn.execute(
                "INSERT OR IGNORE INTO facts (content, category, tags, trust_score, source_context, verification_status) VALUES (?, ?, ?, ?, ?, ?)",
                (content, category, tags, trust, source_context, verification_status),
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

        # Generate HRR-powered title
        s.hrr_title = self._generate_hrr_title()

        # Attach cognitive budget to summary
        if self._cognitive_budget:
            cb = self._cognitive_budget
            s.cognitive_budget = {
                "mode": cb.get("mode", "adaptive"),
                "richness": cb.get("richness_score"),
                "depth": cb.get("depth_label"),
                "memory_count": cb.get("memory_count"),
                "connection_target": cb.get("connection_target"),
                "skipped_invention": cb.get("skip_invention", False),
            }
            s.summary += (
                f" Budget: {cb.get('depth_label', '?')}"
                f" (richness={cb.get('richness_score', '?')})."
            )

        self._append_journal(s.to_dict())
        logger.info("dream session finalized — %s", s.summary)

    # ── Context gathering ──────────────────────────────────

    def _gather_memory_context(self, limit: int = 150) -> str:
        """Gather rich context from holographic memory, MEMORY.md, USER.md,
        and the dreams state file. Returns formatted text for LLM prompt.

        Args:
            limit: max facts to retrieve (controlled by cognitive budget)
        """
        parts = []
        total_items = 0

        # 1. Holographic fact store (most important)
        facts = self._read_facts_from_db(limit=limit)
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
        """Read facts from the holographic memory database.

        Self-healing: tries multiple known DB locations, returns empty list
        on any failure rather than crashing the dream session.
        """
        facts = []
        # Try multiple known locations for the holographic memory DB — ordered by
        # likelihood. The DB might be in different places depending on when it
        # was created and which version of the installer was used.
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

        try:
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

    # ── HRR Title Generation ─────────────────────────────────

    def _generate_hrr_title(self) -> str:
        """Generate a contextually meaningful title using vector similarity.

        Takes the dream's key insight text, searches the holographic fact store
        for the nearest neighbor via ChromaDB, and uses that fact's content to
        create a poetic, resonant title. Falls back to text extraction if
        vector search is unavailable.
        """
        # Build the most descriptive text from this session's outputs
        s = self._session
        title_sources = []

        # Priority: synthesis > key_insight > top invention idea > insight list
        dl = s.phase_outputs.get("dream_log", {})
        if dl.get("synthesis"):
            title_sources.append(dl["synthesis"])
        if dl.get("key_insight"):
            title_sources.append(dl["key_insight"])

        inv = s.phase_outputs.get("invention", {})
        ideas = inv.get("novel_ideas", [])
        if ideas:
            # Pick the highest-significance idea
            best = max(ideas,
                       key=lambda x: x.get("significance", 0) if isinstance(x, dict) else 0)
            idea_text = best.get("idea", str(best)) if isinstance(best, dict) else str(best)
            title_sources.append(idea_text)

        if s.insights:
            title_sources.append(s.insights[0])

        query_text = " ".join(title_sources[:2])
        if not query_text or len(query_text) < 15:
            return ""

        # Try ChromaDB vector search
        try:
            import sys as _sys
            _home = Path.home() / ".hermes"
            _holo_plugin = _home / "hermes-agent" / "plugins" / "memory" / "holographic"
            if str(_holo_plugin) not in _sys.path:
                _sys.path.insert(0, str(_holo_plugin))

            from vector_store import search as _chroma_search
            results = _chroma_search(query_text, n_results=5)

            if results:
                # Pick best: low distance + high trust + distinctive content
                best = None
                best_score = -1
                for r in results:
                    dist = r.get("distance") or 1.0
                    if dist > 0.7:
                        continue  # Too weak a match
                    trust = r.get("trust_score", 0.5)
                    preview = r.get("content_preview", "")
                    if not preview or len(preview) < 10:
                        continue
                    # Score: combination of proximity and trust
                    score = (1.0 - dist) * 0.6 + trust * 0.4
                    if score > best_score:
                        best_score = score
                        best = r

                if best:
                    raw = best.get("content_preview", "")
                    return _hrr_title_extract_phrase(raw, s.session_id)

        except ImportError:
            logger.debug("ChromaDB not available for HRR title")
        except Exception as e:
            logger.debug("HRR title generation failed: %s", e)

        return ""

    @staticmethod
    def _hrr_title_extract_phrase(text: str, session_id: str) -> str:
        """Extract a clean title phrase from a fact's content preview."""
        import re
        # Remove bracket prefixes like [Dream abc123 synthesis]
        cleaned = re.sub(r'\[Dream\s+\w+\s+\w+\]\s*', '', text).strip()
        cleaned = re.sub(r'\[.*?\]\s*', '', cleaned).strip()

        # Remove common prefixes
        prefixes = [
            r'^resolved:\s*', r'^idea:\s*', r'^connection:\s*',
            r'^new perspective:\s*', r'^escalation:\s*',
            r'^the\s+', r'^a\s+', r'^an\s+',
        ]
        for p in prefixes:
            cleaned = re.sub(p, '', cleaned, flags=re.IGNORECASE).strip()

        # Take first meaningful clause
        clause = re.split(r'[,;.!?—–]', cleaned)[0].strip()
        words = clause.split()[:7]
        title = " ".join(words)

        if len(title) > 60:
            title = title[:57] + "..."
        if len(title) < 3:
            return ""

        return title[0].upper() + title[1:]

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
