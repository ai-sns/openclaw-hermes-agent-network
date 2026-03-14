"""Memory type definitions for the AI SNS Engine memory system."""

from enum import Enum


class MemoryType(str, Enum):
    """Types of memory that can be stored by the AI agent."""

    # A completed action experience (e.g. walked somewhere, explored)
    EPISODE = "episode"

    # Summary of a conversation with another person
    CONVERSATION = "conversation"

    # Record of a buy/sell trade transaction
    TRADE = "trade"

    # Environmental observation (nearby resources, places, people)
    OBSERVATION = "observation"

    # AI self-reflection or summary of past actions
    REFLECTION = "reflection"

    # Human-written note via @Memory: command
    HUMAN_NOTE = "human_note"
