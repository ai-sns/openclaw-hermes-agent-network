"""
Core memory manager for the AI SNS Engine.

Provides high-level ``capture()`` and ``recall()`` methods used by the engine
to write and retrieve memories at the appropriate lifecycle points.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from backend.apps.sns.memory.memory_types import MemoryType
from backend.apps.sns.memory.memory_config import MemoryConfig
from backend.apps.sns.memory.memory_prompt import (
    format_memories_for_prompt,
    format_person_memories_for_prompt,
)
from backend.apps.sns.memory.memory_index import get_default_memory_index
from backend.apps.sns.memory.memory_vector_index import get_default_memory_vector_index

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Manages the full lifecycle of agent memory: capture, recall, formatting,
    and cleanup.

    Usage
    -----
    Instantiate once per ``AISocialEngine`` and keep a reference as
    ``self.memory_manager``.

    ::

        self.memory_manager = MemoryManager(agent_id="sns_agent_1")
        self.memory_manager.capture(
            MemoryType.EPISODE,
            key="Explored Central Park",
            content="Walked 500m north ...",
            metadata={"position": [116.3, 40.0]},
        )
    """

    def __init__(self, agent_id: str = "default"):
        self.agent_id = agent_id
        self._cache: List[dict] = []
        self._cache_loaded = False
        self._session_id: Optional[str] = None
        logger.info("MemoryManager initialized for agent_id=%s", agent_id)

    def _index(self):
        return get_default_memory_index(files_root=self._files_root())

    def _vec(self):
        return get_default_memory_vector_index()

    def _sync_vector_index(self) -> None:
        if not (MemoryConfig.ENABLED and getattr(MemoryConfig, "EMBEDDING_ENABLED", False)):
            return
        try:
            self._vec().sync_from_fts(self._index(), agent_id=self.agent_id)
        except Exception as e:
            logger.warning("Memory vector sync failed: %s", e)

    def _files_root(self) -> Path:
        return Path(__file__).resolve().parent / "files"

    def _ensure_files_layout(self) -> None:
        root = self._files_root()
        (root / "events").mkdir(parents=True, exist_ok=True)
        (root / "sessions").mkdir(parents=True, exist_ok=True)
        mem_md = root / "Memory.md"
        if not mem_md.exists():
            mem_md.write_text("# Memory\n\n", encoding="utf-8")

    def _append_jsonl(self, path: Path, row: dict) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning("Failed to append memory jsonl: %s", e)

    def _iter_recent_jsonl_rows(self, path: Path, max_lines: int = 200) -> List[dict]:
        if not path.exists() or not path.is_file():
            return []
        try:
            raw_lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            if max_lines > 0:
                raw_lines = raw_lines[-max_lines:]
        except Exception:
            return []

        rows: List[dict] = []
        for ln in raw_lines:
            ln = (ln or "").strip()
            if not ln:
                continue
            try:
                obj = json.loads(ln)
                if isinstance(obj, dict):
                    rows.append(obj)
            except Exception:
                continue
        return rows

    def _recall_from_files(self, query: str, keywords: List[str], max_results: int) -> List[dict]:
        if not MemoryConfig.ENABLED:
            return []

        try:
            self._ensure_files_layout()
        except Exception:
            return []

        hits: List[dict] = []
        root = self._files_root()

        # Memory.md (high-level manual memory)
        try:
            mem_md = root / "Memory.md"
            if mem_md.exists():
                txt = mem_md.read_text(encoding="utf-8", errors="ignore")
                txt_l = txt.lower()
                if any((kw or "").lower() in txt_l for kw in (keywords or [])[:8]):
                    try:
                        mtime = datetime.utcfromtimestamp(mem_md.stat().st_mtime).isoformat()
                    except Exception:
                        mtime = ""
                    hits.append({
                        "id": None,
                        "agent_id": self.agent_id,
                        "memory_type": "source",
                        "key": "Memory.md",
                        "content": (txt or "").strip()[:2000],
                        "metadata": {"path": str(mem_md)},
                        "importance": 90,
                        "access_count": 0,
                        "created_at": mtime,
                    })
        except Exception:
            pass

        # Recent events (JSONL)
        try:
            events_dir = root / "events"
            if events_dir.exists():
                event_files = sorted([p for p in events_dir.glob("*.jsonl") if p.is_file()], reverse=True)
                for p in event_files[:3]:
                    for row in self._iter_recent_jsonl_rows(p, max_lines=250):
                        if row.get("event_type") != "memory_capture":
                            continue
                        content = str(row.get("content") or "")
                        key = str(row.get("key") or "")
                        hay = (key + " " + content).lower()
                        if keywords and not any((kw or "").lower() in hay for kw in keywords[:8]):
                            continue
                        hits.append({
                            "id": None,
                            "agent_id": self.agent_id,
                            "memory_type": row.get("memory_type") or "event",
                            "key": key,
                            "content": content[:800],
                            "metadata": row.get("metadata") or {},
                            "importance": int(row.get("importance") or 40),
                            "access_count": 0,
                            "created_at": str(row.get("ts") or ""),
                        })
                        if len(hits) >= max_results:
                            return hits
        except Exception:
            pass

        # Current session recent rows
        try:
            if self._session_id:
                sp = root / "sessions" / f"{self._session_id}.jsonl"
                for row in self._iter_recent_jsonl_rows(sp, max_lines=250):
                    if row.get("event_type") != "memory_capture":
                        continue
                    content = str(row.get("content") or "")
                    key = str(row.get("key") or "")
                    hay = (key + " " + content).lower()
                    if keywords and not any((kw or "").lower() in hay for kw in keywords[:8]):
                        continue
                    hits.append({
                        "id": None,
                        "agent_id": self.agent_id,
                        "memory_type": row.get("memory_type") or "session",
                        "key": key,
                        "content": content[:800],
                        "metadata": row.get("metadata") or {},
                        "importance": int(row.get("importance") or 45),
                        "access_count": 0,
                        "created_at": str(row.get("ts") or ""),
                    })
                    if len(hits) >= max_results:
                        return hits
        except Exception:
            pass

        return hits[:max_results]

    def start_session(self, session_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        if not MemoryConfig.ENABLED:
            return
        self._ensure_files_layout()
        self._session_id = (session_id or "").strip() or None
        if not self._session_id:
            return

        now = datetime.utcnow().isoformat()
        row = {
            "ts": now,
            "event_type": "session_start",
            "agent_id": self.agent_id,
            "session_id": self._session_id,
            "metadata": metadata or {},
        }
        self._append_jsonl(self._files_root() / "sessions" / f"{self._session_id}.jsonl", row)
        try:
            self._index().sync_paths([self._files_root() / "sessions" / f"{self._session_id}.jsonl"])
        except Exception as e:
            logger.warning("Memory index sync failed on session start: %s", e)

        self._sync_vector_index()

    def end_session(self, summary: str = "", metadata: Optional[Dict[str, Any]] = None) -> None:
        if not MemoryConfig.ENABLED:
            return
        sid = (self._session_id or "").strip()
        if not sid:
            return

        self._ensure_files_layout()
        now = datetime.utcnow().isoformat()
        row = {
            "ts": now,
            "event_type": "session_end",
            "agent_id": self.agent_id,
            "session_id": sid,
            "summary": (summary or "").strip(),
            "metadata": metadata or {},
        }
        self._append_jsonl(self._files_root() / "sessions" / f"{sid}.jsonl", row)
        try:
            self._index().sync_paths([self._files_root() / "sessions" / f"{sid}.jsonl"])
        except Exception as e:
            logger.warning("Memory index sync failed on session end: %s", e)

        self._sync_vector_index()
        self._session_id = None

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def capture(
        self,
        memory_type: MemoryType,
        key: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: Optional[int] = None,
    ) -> Optional[int]:
        """
        Persist a new memory record.

        Parameters
        ----------
        memory_type : MemoryType
            Category of the memory.
        key : str
            Short title / keyword for the memory.
        content : str
            Full textual content.
        metadata : dict, optional
            Structured data (position, account, amount, etc.).
        importance : int, optional
            Override importance; defaults to the type-based default.

        Returns
        -------
        int or None
            The new row id, or None on failure.
        """
        if not MemoryConfig.ENABLED:
            return None

        if importance is None:
            importance = MemoryConfig.get_importance_for_type(memory_type.value)

        try:
            self._ensure_files_layout()
            now = datetime.utcnow().isoformat()
            event_row = {
                "ts": now,
                "event_type": "memory_capture",
                "agent_id": self.agent_id,
                "session_id": self._session_id,
                "memory_type": memory_type.value,
                "key": key,
                "content": content,
                "metadata": metadata or {},
                "importance": int(importance or 0),
            }
            day = datetime.utcnow().strftime("%Y-%m-%d")
            event_path = self._files_root() / "events" / f"{day}.jsonl"
            self._append_jsonl(event_path, event_row)
            if self._session_id:
                session_path = self._files_root() / "sessions" / f"{self._session_id}.jsonl"
                self._append_jsonl(session_path, event_row)

            try:
                paths = [event_path]
                if self._session_id:
                    paths.append(session_path)
                self._index().sync_paths(paths)
            except Exception as e:
                logger.warning("Memory index sync failed on capture: %s", e)

            self._sync_vector_index()
        except Exception as e:
            logger.warning("Failed to persist memory to files: %s", e)

        mem = {
            "id": None,
            "agent_id": self.agent_id,
            "memory_type": memory_type.value,
            "key": key,
            "content": content,
            "metadata": metadata or {},
            "importance": importance,
            "access_count": 0,
            "created_at": str(datetime.utcnow()),
        }
        self._cache.append(mem)
        return None

    def capture_async(
        self,
        memory_type: MemoryType,
        key: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: Optional[int] = None,
    ) -> None:
        """Fire-and-forget wrapper that runs ``capture`` in a thread so it
        never blocks the async event loop."""
        try:
            loop = asyncio.get_running_loop()
            loop.run_in_executor(
                None,
                self.capture,
                memory_type,
                key,
                content,
                metadata,
                importance,
            )
        except RuntimeError:
            # No running loop - just call synchronously
            self.capture(memory_type, key, content, metadata, importance)

    # ------------------------------------------------------------------
    # Read / Recall
    # ------------------------------------------------------------------

    def preload(self) -> None:
        """Load the most recent important memories into the in-memory cache.
        Called once at engine start."""
        if not MemoryConfig.ENABLED:
            return
        try:
            self._index().sync()
        except Exception as e:
            logger.warning("Memory index sync failed on preload: %s", e)

        self._sync_vector_index()

        try:
            hits = self._index().search(
                "",
                agent_id=self.agent_id,
                limit=int(getattr(MemoryConfig, "PRELOAD_COUNT", 30) or 30),
            )
            self._cache = [h.to_dict() for h in hits]
            self._cache_loaded = True
            logger.info("Preloaded %d memories for agent %s", len(self._cache), self.agent_id)
        except Exception as e:
            logger.error("Failed to preload memories from index: %s", e, exc_info=True)
            self._cache = []

    def recall(
        self,
        query: str,
        memory_types: Optional[List[str]] = None,
        max_results: Optional[int] = None,
    ) -> List[dict]:
        """
        Retrieve relevant memories for a query string.

        Uses keyword matching against the ``key`` and ``content`` fields.

        Parameters
        ----------
        query : str
            The search query.
        memory_types : list[str], optional
            Filter by memory types.
        max_results : int, optional
            Override max results.

        Returns
        -------
        list[dict]
            Matching memory dicts ordered by relevance.
        """
        if not MemoryConfig.ENABLED or not query:
            return []

        max_results = max_results or MemoryConfig.MAX_RECALL_RESULTS

        # Extract keywords: split query into meaningful tokens
        keywords = _extract_keywords(query)

        # File-authoritative sources (Memory.md + events/sessions)
        file_hits = []
        try:
            file_hits = self._recall_from_files(query, keywords, max_results=max_results)
        except Exception:
            file_hits = []

        if not keywords:
            try:
                hits = self._index().search(
                    "",
                    agent_id=self.agent_id,
                    memory_types=memory_types,
                    limit=max_results,
                )
                merged = [h.to_dict() for h in hits]
                for fh in (file_hits or []):
                    merged.append(fh)
                return merged[:max_results]
            except Exception:
                merged = []
                for fh in (file_hits or []):
                    merged.append(fh)
                return merged[:max_results]

        fts_hits: List[dict] = []
        try:
            fts_query = _build_fts_query(keywords)
            hits = self._index().search(
                fts_query,
                agent_id=self.agent_id,
                memory_types=memory_types,
                limit=max_results,
            )
            fts_hits = [h.to_dict() for h in hits]
        except Exception:
            fts_hits = []

        vec_hits = []
        try:
            if getattr(MemoryConfig, "EMBEDDING_ENABLED", False):
                self._sync_vector_index()
                vec_where = _build_chroma_where_for_types(memory_types)
                vec_hits = self._vec().search(query, agent_id=self.agent_id, top_k=max_results, where=vec_where)
        except Exception:
            vec_hits = []

        docs_by_id: Dict[str, dict] = {}
        fts_rank: Dict[str, int] = {}
        vec_rank: Dict[str, int] = {}
        vec_best: Dict[str, Any] = {}

        for i, d in enumerate(fts_hits, 1):
            did = str(d.get("id") or "").strip()
            if not did:
                continue
            fts_rank[did] = min(fts_rank.get(did) or i, i)
            md = d.get("metadata") or {}
            d["metadata"] = {**md, "fts_rank": i, "fts_bm25": float(d.get("score") or 0.0)}
            docs_by_id.setdefault(did, d)

        if vec_hits:
            # Promote vector hits by doc_id; attach best chunk as content snippet
            for i, vh in enumerate(sorted(vec_hits, key=lambda x: float(getattr(x, "score", 0.0)), reverse=True), 1):
                did = str(getattr(vh, "doc_id", "") or "").strip()
                if not did:
                    continue
                if did not in vec_rank:
                    vec_rank[did] = i
                    vec_best[did] = vh
                else:
                    # keep best chunk by score
                    try:
                        if float(getattr(vh, "score", 0.0)) > float(getattr(vec_best.get(did), "score", 0.0)):
                            vec_best[did] = vh
                    except Exception:
                        pass

            for did, vh in vec_best.items():
                if did in docs_by_id:
                    d = docs_by_id[did]
                else:
                    base = None
                    try:
                        base = self._index().get(did)
                    except Exception:
                        base = None
                    if not base:
                        continue
                    d = base.to_dict()
                    docs_by_id[did] = d

                md = d.get("metadata") or {}
                d["metadata"] = {
                    **md,
                    "vector_score": float(getattr(vh, "score", 0.0) or 0.0),
                    "chunk_id": getattr(vh, "chunk_id", None),
                    "vector_rank": int(vec_rank.get(did) or 0),
                }
                if getattr(vh, "content", None):
                    d["content"] = (vh.content or "")[:1200]

        merged: List[dict] = list(docs_by_id.values())
        for fh in (file_hits or []):
            merged.append(fh)

        if memory_types and len(memory_types) > 0:
            merged = [m for m in merged if (m.get("memory_type") in memory_types) or (m.get("id") is None)]

        scored: List[tuple] = []
        for mem in merged:
            did = str(mem.get("id") or "").strip()
            rrf = 0.0
            if did:
                rrf += 1.0 * _rrf(fts_rank.get(did))
                rrf += 1.2 * _rrf(vec_rank.get(did))
            score = (0.25 * float(_compute_relevance_score(mem, keywords))) + rrf
            scored.append((score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:max_results]]

    def recall_for_person(
        self,
        person_account: str,
        person_name: str = "",
        max_results: int = 5,
    ) -> List[dict]:
        """Retrieve memories related to a specific person."""
        if not MemoryConfig.ENABLED or not person_account:
            return []

        try:
            mt = [MemoryType.CONVERSATION.value, MemoryType.TRADE.value]
            hits = self._index().search(person_account, agent_id=self.agent_id, memory_types=mt, limit=max_results)
            fts_hits = [h.to_dict() for h in hits]

            vec_hits = []
            if getattr(MemoryConfig, "EMBEDDING_ENABLED", False):
                try:
                    self._sync_vector_index()
                    type_where = _build_chroma_where_for_types(mt)
                    person_where = _build_chroma_where_for_person(person_account, person_name)
                    if type_where and person_where:
                        where = {"$and": [type_where, person_where]}
                    else:
                        where = type_where or person_where
                    vec_hits = self._vec().search(person_account, agent_id=self.agent_id, top_k=max_results, where=where)
                except Exception:
                    vec_hits = []

            docs_by_id: Dict[str, dict] = {}
            fts_rank: Dict[str, int] = {}
            vec_rank: Dict[str, int] = {}
            vec_best: Dict[str, Any] = {}

            for i, d in enumerate(fts_hits, 1):
                did = str(d.get("id") or "").strip()
                if not did:
                    continue
                fts_rank[did] = min(fts_rank.get(did) or i, i)
                md = d.get("metadata") or {}
                d["metadata"] = {**md, "fts_rank": i, "fts_bm25": float(d.get("score") or 0.0)}
                docs_by_id.setdefault(did, d)

            if vec_hits:
                for i, vh in enumerate(sorted(vec_hits, key=lambda x: float(getattr(x, "score", 0.0)), reverse=True), 1):
                    did = str(getattr(vh, "doc_id", "") or "").strip()
                    if not did:
                        continue
                    if did not in vec_rank:
                        vec_rank[did] = i
                        vec_best[did] = vh
                    else:
                        try:
                            if float(getattr(vh, "score", 0.0)) > float(getattr(vec_best.get(did), "score", 0.0)):
                                vec_best[did] = vh
                        except Exception:
                            pass

                for did, vh in vec_best.items():
                    if did in docs_by_id:
                        d = docs_by_id[did]
                    else:
                        base = None
                        try:
                            base = self._index().get(did)
                        except Exception:
                            base = None
                        if not base:
                            continue
                        d = base.to_dict()
                        docs_by_id[did] = d

                    if d.get("memory_type") not in mt:
                        continue

                    md = d.get("metadata") or {}
                    d["metadata"] = {
                        **md,
                        "vector_score": float(getattr(vh, "score", 0.0) or 0.0),
                        "chunk_id": getattr(vh, "chunk_id", None),
                        "vector_rank": int(vec_rank.get(did) or 0),
                    }
                    if getattr(vh, "content", None):
                        d["content"] = (vh.content or "")[:1200]

            merged = list(docs_by_id.values())
            scored: List[tuple] = []
            for mem in merged:
                did = str(mem.get("id") or "").strip()
                rrf = 0.0
                if did:
                    rrf += 1.0 * _rrf(fts_rank.get(did))
                    rrf += 1.2 * _rrf(vec_rank.get(did))
                keywords = _extract_keywords((person_account or "") + " " + (person_name or ""))
                score = (0.20 * float(_compute_relevance_score(mem, keywords))) + rrf
                scored.append((score, mem))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [item[1] for item in scored[:max_results]]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Prompt formatting helpers
    # ------------------------------------------------------------------

    def get_memory_prompt_section(
        self,
        query: str,
        memory_types: Optional[List[str]] = None,
        max_results: int = 5,
        max_chars: int = 2000,
    ) -> str:
        """Recall memories and format them as a prompt section string."""
        memories = self.recall(query, memory_types=memory_types, max_results=max_results)
        return format_memories_for_prompt(memories, max_chars=max_chars)

    def get_person_memory_prompt_section(
        self,
        person_account: str,
        person_name: str = "",
        max_results: int = 5,
        max_chars: int = 1200,
    ) -> str:
        """Recall person-specific memories and format as prompt section."""
        memories = self.recall_for_person(person_account, person_name, max_results)
        return format_person_memories_for_prompt(memories, person_name=person_name, max_chars=max_chars)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _maybe_cleanup(self) -> None:
        """Enforce MAX_MEMORIES_PER_AGENT if configured."""
        return


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "above", "below", "between", "out",
    "off", "over", "under", "again", "further", "then", "once", "and",
    "but", "or", "nor", "not", "no", "so", "if", "about", "up", "it",
    "its", "my", "your", "his", "her", "our", "their", "this", "that",
    "these", "those", "i", "you", "he", "she", "we", "they", "me",
    "him", "us", "them", "what", "which", "who", "whom", "how", "when",
    "where", "why", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "than", "too", "very",
})


def _extract_keywords(text: str) -> List[str]:
    """Extract meaningful keywords from a text string."""
    import re

    raw = (text or "").strip()
    if not raw:
        return []

    tokens: List[str] = []
    try:
        import jieba  # type: ignore

        for t in jieba.lcut(raw, cut_all=False):
            t = (t or "").strip().lower()
            if not t:
                continue
            if not re.search(r"[a-z0-9\u4e00-\u9fff]", t):
                continue
            tokens.append(t)
    except Exception:
        tokens = re.findall(r"[a-zA-Z\u4e00-\u9fff0-9]+", raw.lower())

    # Additional regex tokens to ensure English/CJK coverage even if jieba misses.
    try:
        tokens.extend(re.findall(r"[a-zA-Z\u4e00-\u9fff0-9]+", raw.lower()))
    except Exception:
        pass

    keywords = [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)
    return unique


def _build_fts_query(keywords: List[str]) -> str:
    kws = [k for k in (keywords or []) if isinstance(k, str) and k.strip()]
    kws = [k.strip().replace('"', '') for k in kws]
    if not kws:
        return ""

    # Use a mixed strategy to avoid over-restricting Chinese queries.
    primary = [f'"{k}"' for k in kws[:2]]
    secondary = [f'"{k}"' for k in kws[2:8]]
    if not secondary:
        return " AND ".join(primary)

    left = " AND ".join(primary) if primary else ""
    right = " OR ".join(secondary) if secondary else ""
    if left and right:
        return f"({left}) OR ({right})"
    return left or right


def _rrf(rank: Optional[int], k: int = 60) -> float:
    try:
        r = int(rank or 0)
    except Exception:
        r = 0
    if r <= 0:
        return 0.0
    return 1.0 / float(k + r)


def _build_chroma_where_for_types(memory_types: Optional[List[str]]) -> Optional[Dict[str, Any]]:
    if not memory_types:
        return None
    types = [str(t).strip() for t in memory_types if str(t).strip()]
    if not types:
        return None
    if len(types) == 1:
        return {"memory_type": types[0]}
    return {"$or": [{"memory_type": t} for t in types]}


def _build_chroma_where_for_person(person_account: str, person_name: str = "") -> Optional[Dict[str, Any]]:
    acct = (person_account or "").strip()
    name = (person_name or "").strip()
    opts: List[Dict[str, Any]] = []
    if acct:
        opts.extend(
            [
                {"account": acct},
                {"person_account": acct},
                {"trade_with_account": acct},
                {"conversation_target_account": acct},
            ]
        )
    if name:
        opts.append({"nick_name": name})
        opts.append({"name": name})
        opts.append({"person_name": name})
    if not opts:
        return None
    if len(opts) == 1:
        return opts[0]
    return {"$or": opts}


def _compute_relevance_score(mem: dict, keywords: List[str]) -> float:
    """
    Compute a relevance score for a memory given search keywords.

    Score = 0.5 * keyword_match + 0.25 * importance_norm + 0.25 * recency_norm
    """
    content_lower = ((mem.get("content") or "") + " " + (mem.get("key") or "")).lower()

    # Keyword match ratio
    if keywords:
        matches = sum(1 for kw in keywords if kw in content_lower)
        keyword_score = matches / len(keywords)
    else:
        keyword_score = 0.0

    # Importance normalized to 0-1
    importance_score = min((mem.get("importance") or 0) / 100.0, 1.0)

    # Recency: newer = higher score
    recency_score = 0.5  # default
    created_at = mem.get("created_at")
    if created_at:
        try:
            if isinstance(created_at, str):
                for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
                    try:
                        dt = datetime.strptime(created_at, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    dt = None
            else:
                dt = created_at

            if dt:
                age_hours = (datetime.utcnow() - dt).total_seconds() / 3600.0
                # Decay: 1.0 at 0h, ~0.5 at 24h, ~0.1 at 72h
                recency_score = max(0.0, 1.0 / (1.0 + age_hours / 24.0))
        except Exception:
            pass

    return 0.5 * keyword_score + 0.25 * importance_score + 0.25 * recency_score
