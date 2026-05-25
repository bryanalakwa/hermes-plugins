"""Dream Engine — constants and state definitions."""

from enum import Enum


class DreamState(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    DORMANT = "dormant"
    HYPNAGOGIC = "hypnagogic"
    DREAMING = "dreaming"


DEFAULT_CONFIG = {
    "idle_threshold_seconds": 300,          # T1 = 5 min
    "dormant_threshold_seconds": 1800,      # T2 = 30 min
    "soak_threshold_seconds": 3000,         # T3 = 50 min
    "hypnagogic_duration_seconds": 120,     # T4 = 2 min
    "max_dreams_per_day": 2,
    "consolidation_memory_count": 150,
    "invention_sample_size": 10,
}
