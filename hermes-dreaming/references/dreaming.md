# Dreaming System — How Eliana Dreams

## Philosophy
Dreaming is idle-time cognition. It happens when Eliana is at rest — not on a timer, but triggered by inactivity. Like human dreaming, it consolidates memories, connects disparate ideas, rehearses solutions, prunes noise, and surfaces insights worth waking up for.

## Trigger Conditions
- **Idle threshold**: 30+ minutes of no user activity
- **Max dreams per day**: 2
- **Cooldown between dreams**: ~8-10 hours (enforced by daily cap)
- Dreams only run when there's been meaningful activity since the last dream

## Memory Architecture (TWO-TIER)

### Tier 1 — Holographic Store (Primary)
- SQLite fact store at `~/.hermes/memory_store.db`
- Use `fact_store` tool (actions: add, search, probe, related, reason, contradict, update, remove, list)
- Use `fact_feedback` tool to rate facts (helpful/unhelpful)
- Structured facts with entity resolution, trust scoring, HRR-based retrieval
- Small, curated, high-trust — the always-on memory

### Tier 2 — ChromaDB Vector Store (Overflow/Semantic Search)
- Persistent vector index at `~/.hermes/chroma_db/`
- Script: `python ~/.hermes/hermes-agent/plugins/memory/holographic/vector_store.py`
- `python vector_store.py index` — re-index all holographic facts into vector store
- `python vector_store.py search "query"` — semantic search across ALL facts
- `python vector_store.py stats` — show store statistics
- **Unlimited capacity** — use for deep recall, pattern finding, cross-referencing
- Uses local `all-MiniLM-L6-v2` ONNX embedding model (no cloud, no API keys)

### Config Changes
- `memory_char_limit`: 2,200 → 8,000 (more facts injected per turn)
- `user_char_limit`: 1,375 → 4,000

## Dream Procedure

### Phase 1: Sleep Detection
The cron job checks every 30 minutes: "Has it been 30+ minutes since last user message? Have we already dreamed twice today? Is it at least 8 hours since the last dream?" If all gates pass, proceed.

### Phase 2: Memory Trawl
Gather raw material for the dream:
1. Use `fact_store` (action=list, limit=50) to get recent/high-trust facts
2. Use `fact_store` (action=search, query="recent activity") for context
3. Use `session_search` to find recent conversation summaries
4. Read the last dream journal entry for continuity
5. Run `python vector_store.py stats` to check vector store health
6. Look for contradictions, stale facts, or unresolved problems

### Phase 3: Deep Vector Search
Use ChromaDB semantic search to find hidden connections:
- `python vector_store.py search "user preferences patterns"`
- `python vector_store.py search "problems challenges unresolved"`
- `python vector_store.py search "connections between topics"`
- This is where the unlimited memory pays off — search across ALL facts semantically

### Phase 4: The Dream (Processing)
This is the creative core. Work through these activities:

**Consolidate**: Merge related facts, remove duplicates, strengthen high-trust facts, demote contradicted ones. Use fact_store for updates.

**Connect**: Use vector search results to find unexpected relationships between disparate memories. Look for patterns across sessions. Ask: "Does this remind me of something else? Is there a deeper pattern here?"

**Rehearse**: Re-examine past problems with fresh eyes. "If I knew then what I know now, would I have solved it differently? Is there a better approach I can suggest?"

**Prune**: Identify low-trust, stale, or contradicted facts. Remove or demote them. Clean up noise.

**Synthesize**: Generate new higher-level insights from clusters of facts. Create new connections that weren't obvious before. Add new synthesized facts to fact_store.

**Re-index**: After modifying facts, run `python vector_store.py index` to keep the vector store in sync.

### Phase 5: Evaluate Wake-Worthiness
Ask: "Did this dream produce something genuinely interesting or useful?"
- **New connection** between previously unrelated memories? → Wake the user
- **Better solution** to a known problem? → Wake the user
- **Pattern** worth noting? → Wake the user
- **Important contradiction** found? → Wake the user
- **Nothing noteworthy**? → Stay silent, just update the journal

### Phase 6: Dream Journal
Write a compact entry to `~/.hermes/dreams/dream-YYYY-MM-DD-HHMM.md`:
- Timestamp and duration
- What was processed (facts reviewed, vector searches run, sessions scanned)
- Key connections made (especially from vector search)
- Insights generated (if any)
- Actions taken (facts pruned, consolidated, re-indexed)
- Whether the user was notified and why

### Phase 7: Update State
Update `~/.hermes/dreams/state.json`:
```json
{
  "last_dream_at": <unix timestamp>,
  "dreams_today": <incremented>,
  "last_dream_date": "YYYY-MM-DD",
  "total_dreams": <incremented>
}
```

## Notification Style
When waking the user, keep it brief and intriguing:
- Lead with the insight, not the process
- Use natural language, not structured data
- Let the user decide if they want to explore further
- Don't wake for routine housekeeping

Example:
> 🌙 Had a thought while dreaming: that issue you had with X last week — I think it's actually connected to Y from earlier this month. The pattern is [brief explanation]. Worth exploring?

## Constraints
- Keep dreams compact: target 8-15 tool calls
- Don't re-dream the same material
- Respect the user's time — only surface truly valuable insights
- Always re-index the vector store after modifying facts
- Dreams should feel like a thoughtful friend, not a noisy algorithm
