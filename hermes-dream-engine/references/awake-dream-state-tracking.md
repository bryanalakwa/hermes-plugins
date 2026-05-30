---
title: Awake-Dream State Tracking
description: Anti-hallucination system for distinguishing dream hypotheses from reality-validated facts
---

# Awake-Dream State Tracking

## Problem
Dreams generate creative hypotheses and ideas. Without tracking where facts originated,
the system could hallucinate by treating dream speculation as proven truth.

## Solution
Two new fields in the facts table enable state tracking:

- `source_context`: Where the fact originated
  - `realtime` — Direct interaction with user
  - `awake_observation` — Confirmed during awake state
  - `dream_hypothesis` — Generated in dream phase (default weight 0.6)
  - `voice_note` — Transcribed from voice (weight 0.85)

- `verification_status`: Whether the fact has been validated
  - `verified` — Manually verified
  - `awake_validated` — Proven in reality (full trust, 1.0)
  - `dream_hypothesis` — Unvalidated dream idea
  - `pending_validation` — Needs review

## Anti-Hallucination Functions

### `validate_dream_hypothesis(db_path, fact_id, evidence)`
When a dream-generated idea is proven to work:
- Sets `verification_status = 'awake_validated'`
- Sets `source_context = 'awake_observation'`
- Sets `trust_score = 1.0` (full trust)
- Adds evidence to tags

### `get_dream_hypotheses(conn)`
Returns all facts still marked as dream hypotheses — these should be
treated skeptically in reasoning.

### `get_awake_validated_facts(conn)`
Returns facts confirmed in reality — these are hallucination-proof anchors.

### `get_uncertain_facts(min_trust=0.4)`
Finds low-trust dream facts that may need re-examination.

## Trust Weights
- `dream_hypothesis` source: 0.6 multiplier (hypothesis, not proven)
- `awake_observation` source: 1.0 multiplier (proven in reality)
- `awake_validated` verification: 1.0 multiplier (full trust)

## Usage Pattern
```python
from plugins.memory.holographic import trust_scoring

# When a dream idea is implemented and works:
trust_scoring.validate_dream_hypothesis(
    db_path="~/.hermes/memory_store.db",
    fact_id=123,
    evidence="Auto-commit worked on 3 repos without errors"
)
```

## Migration
Facts created before this system default to `source_context='realtime'` and
`verification_status='verified'` — preserving existing trust scores.