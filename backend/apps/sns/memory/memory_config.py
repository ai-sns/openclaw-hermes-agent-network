"""Configuration for the AI SNS Engine memory system."""

import logging

logger = logging.getLogger(__name__)


class MemoryConfig:
    """Central configuration for the memory system."""

    # Whether memory capture is enabled
    ENABLED: bool = True

    # Whether embedding/vector search is enabled (requires KM vector dependencies)
    EMBEDDING_ENABLED: bool = False

    # Maximum number of memories to return in a recall query
    MAX_RECALL_RESULTS: int = 5

    # Minimum keyword match score (0.0 - 1.0) to include in recall results
    MIN_RECALL_SCORE: float = 0.1

    # Maximum number of memories to cache in-memory on engine start
    PRELOAD_COUNT: int = 20

    # Embedding chunking defaults (character-based)
    EMBEDDING_CHUNK_SIZE: int = 1200
    EMBEDDING_CHUNK_OVERLAP: int = 150

    # Default importance score for auto-captured memories (0-100)
    DEFAULT_IMPORTANCE: int = 50

    # Importance thresholds for different memory types
    IMPORTANCE_BY_TYPE: dict = {
        "episode": 40,
        "conversation": 60,
        "trade": 70,
        "observation": 30,
        "reflection": 65,
        "human_note": 80,
    }

    # Maximum age in days before a memory is considered for cleanup (0 = never)
    MAX_AGE_DAYS: int = 0

    # Maximum total memories to keep per agent (0 = unlimited)
    MAX_MEMORIES_PER_AGENT: int = 500

    @classmethod
    def get_importance_for_type(cls, memory_type: str) -> int:
        """Return the default importance score for a given memory type."""
        return cls.IMPORTANCE_BY_TYPE.get(memory_type, cls.DEFAULT_IMPORTANCE)
