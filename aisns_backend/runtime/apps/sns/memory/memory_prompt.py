"""
Utilities for formatting recalled memories into prompt segments
that can be injected into the AI agent's context.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from db.DBFactory import get_prompt_by_title

logger = logging.getLogger(__name__)


def format_memories_for_prompt(
    memories: List[dict],
    max_chars: int = 2000,
) -> str:
    """
    Format a list of memory dicts into a Markdown section suitable for
    injection into an LLM prompt.

    Parameters
    ----------
    memories : list[dict]
        Each dict should contain at minimum: memory_type, content, importance,
        created_at.
    max_chars : int
        Approximate character budget for the whole section.

    Returns
    -------
    str
        A Markdown section starting with ``## Memory Recall``, or an empty
        string if there are no memories.
    """
    if not memories:
        return ""

    # Load template from DB; fall back to hardcoded default
    template = ""
    try:
        template = (get_prompt_by_title("__memory_recall_header__") or "").strip()
    except Exception:
        template = ""
    if not template:
        template = (
            "## Memory Recall\n"
            "The following memories from your past experience may be relevant:\n"
            "\n"
            "__memory_entries__\n"
            "Use these memories to inform your decision, but prioritize current context."
        )

    # Build memory entries
    entry_lines: List[str] = []
    total_chars = 0

    for idx, mem in enumerate(memories, start=1):
        mem_type = mem.get("memory_type", "unknown")
        content = (mem.get("content") or "").strip()
        importance = mem.get("importance", 0)
        created_at = mem.get("created_at", "")
        time_ago = _format_time_ago(created_at)

        entry = f"{idx}. [{mem_type}] ({time_ago}, importance: {importance})\n   {content}\n"

        if total_chars + len(entry) > max_chars:
            break

        entry_lines.append(entry)
        total_chars += len(entry)

    entries_str = "\n".join(entry_lines)
    return template.replace("__memory_entries__", entries_str)


def format_person_memories_for_prompt(
    memories: List[dict],
    person_name: str = "",
    max_chars: int = 1200,
) -> str:
    """
    Format memories related to a specific person for prompt injection.

    Parameters
    ----------
    memories : list[dict]
        Memories filtered for a specific person.
    person_name : str
        Display name of the person.
    max_chars : int
        Character budget.

    Returns
    -------
    str
        A Markdown section, or empty string.
    """
    if not memories:
        return ""

    header = f"## Past Interactions with {person_name}" if person_name else "## Past Interactions"
    lines: List[str] = [header, ""]

    total_chars = len(header) + 2

    for idx, mem in enumerate(memories, start=1):
        mem_type = mem.get("memory_type", "unknown")
        content = (mem.get("content") or "").strip()
        time_ago = _format_time_ago(mem.get("created_at", ""))

        entry = f"- [{mem_type}] ({time_ago}) {content}\n"
        if total_chars + len(entry) > max_chars:
            break

        lines.append(entry)
        total_chars += len(entry)

    return "\n".join(lines)


def _format_time_ago(created_at_str: str) -> str:
    """Return a human-friendly relative time string like '2 hours ago'."""
    if not created_at_str:
        return "unknown time"
    try:
        if isinstance(created_at_str, datetime):
            created = created_at_str
        else:
            # Try common datetime formats
            for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    created = datetime.strptime(created_at_str, fmt)
                    break
                except ValueError:
                    continue
            else:
                return "some time ago"

        now = datetime.utcnow()
        delta = now - created
        seconds = delta.total_seconds()

        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} min ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        else:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days > 1 else ''} ago"
    except Exception:
        return "some time ago"
