"""Trust scoring module for holographic memory plugin.

Provides source-aware trust computation with association-distance weighting,
supporting both memory plugin and dream engine use cases.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Source weights - trust multipliers based on fact origin
SOURCE_WEIGHTS: dict[str, float] = {
    "realtime": 1.0,
    "awake_observation": 1.0,  # Fact confirmed/proven during awake state
    "manual_entry": 0.9,
    "dream_hypothesis": 0.6,
    "voice_note": 0.85,
}

# Verification multipliers - adjustments based on verification status
VERIFICATION_MULTIPLIERS: dict[str, float] = {
    "verified": 1.0,
    "awake_validated": 1.0,  # Dream hypothesis confirmed in reality
    "dream_hypothesis": 0.7,
    "pending_validation": 0.85,
}


def compute_source_trust(
    significance: float,
    source: str,
    verification: str,
    association_distance: float = 0.0,
) -> float:
    """Compute trust score based on source, verification, and association distance.

    Trust is computed as:
        trust = significance * source_weight * verification_multiplier * distance_decay

    Args:
        significance: Base significance score (0.0 to 1.0)
        source: Source type (realtime, manual_entry, dream_hypothesis, voice_note)
        verification: Verification status (verified, dream_hypothesis, pending_validation)
        association_distance: Distance factor (0.0 = exact match, higher = more distant)

    Returns:
        Computed trust score clamped to [0.0, 1.0]
    """
    # Get source weight with fallback to lowest weight for unknown sources
    source_weight = SOURCE_WEIGHTS.get(source, min(SOURCE_WEIGHTS.values()))

    # Get verification multiplier with fallback to pending_validation multiplier
    verification_mult = VERIFICATION_MULTIPLIERS.get(
        verification, VERIFICATION_MULTIPLIERS.get("pending_validation", 0.85)
    )

    # Distance decay: facts further from known entities get lower trust
    # Uses exponential decay: closer to 0 = higher trust, further = lower
    # At distance 0.0: full weight (1.0), at distance 1.0: ~0.37, at distance 2.0: ~0.14
    distance_decay = max(0.0, min(1.0, 2.718 ** (-association_distance)))

    # Compute final trust score
    trust = significance * source_weight * verification_mult * distance_decay

    # Clamp to valid range
    return max(0.0, min(1.0, trust))


def get_source_facts(conn: sqlite3.Connection, source: str) -> list[dict[str, Any]]:
    """Retrieve all facts matching a given source context.

    Args:
        conn: SQLite database connection
        source: Source context to filter by (e.g., 'dream_hypothesis')

    Returns:
        List of fact dictionaries with source_context matching the given source
    """
    cursor = conn.execute(
        """
        SELECT
            fact_id,
            content,
            category,
            tags,
            trust_score,
            retrieval_count,
            helpful_count,
            created_at,
            updated_at,
            source_context,
            verification_status
        FROM facts
        WHERE source_context = ?
        ORDER BY trust_score DESC, created_at DESC
        """,
        (source,),
    )
    return [dict(row) for row in cursor.fetchall()]


def flag_stale_dream_hypotheses(db_path: str, days_old: int = 30) -> int:
    """Flag dream hypothesis facts older than specified days as requiring validation.

    This function identifies dream_hypothesis facts that haven't been validated
    and updates their verification_status to indicate they need review.

    Args:
        db_path: Path to the SQLite database
        days_old: Minimum age in days for facts to be considered stale

    Returns:
        Number of facts flagged
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        cutoff_date = datetime.now() - timedelta(days=days_old)

        cursor = conn.execute(
            """
            UPDATE facts
            SET verification_status = 'pending_validation',
                updated_at = CURRENT_TIMESTAMP
            WHERE source_context = 'dream_hypothesis'
              AND verification_status = 'dream_hypothesis'
              AND created_at < ?
            """,
            (cutoff_date.isoformat(),),
        )
        conn.commit()

        return cursor.rowcount
    finally:
        conn.close()


def verify_fact(db_path: str, fact_id: int, new_status: str) -> bool:
    """Update a fact's verification status.

    Args:
        db_path: Path to the SQLite database
        fact_id: The ID of the fact to verify
        new_status: New verification status (verified, dream_hypothesis, pending_validation)

    Returns:
        True if the fact was updated, False if fact_id not found
    """
    if new_status not in VERIFICATION_MULTIPLIERS:
        # Still accept the status even if not in multipliers (for future extensibility)
        pass

    conn = sqlite3.connect(db_path)

    try:
        cursor = conn.execute(
            "SELECT fact_id FROM facts WHERE fact_id = ?",
            (fact_id,),
        )
        if cursor.fetchone() is None:
            return False

        conn.execute(
            """
            UPDATE facts
            SET verification_status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE fact_id = ?
            """,
            (new_status, fact_id),
        )
        conn.commit()

        return True
    finally:
        conn.close()


def validate_dream_hypothesis(db_path: str, fact_id: int, evidence: str = "") -> bool:
    """Mark a dream hypothesis as validated in reality.

    This is the key function for awake-dream state tracking: when a dream-generated
    idea or solution is proven to work in reality, call this to promote it to
    'awake_validated' status with full trust.

    Args:
        db_path: Path to the SQLite database
        fact_id: The ID of the dream hypothesis to validate
        evidence: Optional evidence text about how it was validated

    Returns:
        True if the fact was validated, False otherwise
    """
    conn = sqlite3.connect(db_path)
    try:
        # Check this is actually a dream hypothesis
        row = conn.execute(
            "SELECT source_context, verification_status FROM facts WHERE fact_id = ?",
            (fact_id,),
        ).fetchone()
        if row is None:
            return False

        if row["source_context"] != "dream_hypothesis":
            # Not a dream fact — nothing to validate
            return False

        # Mark as awake_validated with evidence in tags
        tags_update = f"awake_validated"
        if evidence:
            tags_update += f"|evidence:{evidence[:100]}"
        elif row["tags"]:
            tags_update = row["tags"] + f",awake_validated"

        conn.execute(
            """
            UPDATE facts
            SET verification_status = 'awake_validated',
                source_context = 'awake_observation',
                trust_score = 1.0,  -- Full trust when proven in reality
                tags = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE fact_id = ?
            """,
            (tags_update, fact_id),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def get_dream_hypotheses(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Retrieve all unvalidated dream hypothesis facts.

    These are facts that originated in dreams and haven't been proven in reality yet.
    They should be treated with caution to prevent hallucinations.

    Args:
        conn: SQLite database connection

    Returns:
        List of fact dictionaries with source_context='dream_hypothesis'
    """
    cursor = conn.execute(
        """
        SELECT
            fact_id,
            content,
            category,
            tags,
            trust_score,
            retrieval_count,
            helpful_count,
            created_at,
            updated_at,
            source_context,
            verification_status
        FROM facts
        WHERE source_context = 'dream_hypothesis'
        ORDER BY trust_score DESC, created_at DESC
        """,
    )
    return [dict(row) for row in cursor.fetchall()]


def get_awake_validated_facts(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Retrieve all facts validated in reality.

    These facts have been proven to work — they serve as anchors against hallucination.

    Args:
        conn: SQLite database connection

    Returns:
        List of fact dictionaries with verification_status='awake_validated'
    """
    cursor = conn.execute(
        """
        SELECT
            fact_id,
            content,
            category,
            tags,
            trust_score,
            retrieval_count,
            helpful_count,
            created_at,
            updated_at,
            source_context,
            verification_status
        FROM facts
        WHERE verification_status = 'awake_validated'
        ORDER BY trust_score DESC, created_at DESC
        """,
    )
    return [dict(row) for row in cursor.fetchall()]


def get_uncertain_facts(min_trust: float = 0.4) -> list[dict]:
    """Get facts that might be dream artifacts masquerading as truth.

    This is the anti-hallucination checker: finds facts with medium trust that
    could be questionable. Facts from dreams should be re-examined if trust is low.

    Args:
        min_trust: Minimum trust threshold (default 0.4 to catch borderline cases)

    Returns:
        List of potentially hallucinated facts
    """
    db_candidates = [
        Path.home() / ".hermes" / "memory_store.db",
        Path.home() / ".hermes" / "hermes-agent" / "plugins" / "memory" / "holographic" / "memory_store.db",
    ]

    for db_path in db_candidates:
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            try:
                cursor = conn.execute(
                    """
                    SELECT * FROM facts
                    WHERE trust_score BETWEEN ? AND ?
                      AND (source_context = 'dream_hypothesis' OR source_context = 'dream')
                    ORDER BY trust_score ASC, created_at DESC
                    """,
                    (0.0, min_trust),
                )
                return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()
    return []