import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

logger = logging.getLogger(__name__)


@dataclass
class MemoryIndexHit:
    doc_id: str
    agent_id: str
    memory_type: str
    key: str
    content: str
    metadata: Dict[str, Any]
    ts: str
    session_id: Optional[str] = None
    score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.doc_id,
            "agent_id": self.agent_id,
            "memory_type": self.memory_type,
            "key": self.key,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.ts,
            "session_id": self.session_id,
            "score": self.score,
            "importance": int((self.metadata or {}).get("importance") or 0),
            "access_count": 0,
        }


class MemoryIndex:
    def __init__(self, *, files_root: Path, index_path: Path):
        self.files_root = files_root
        self.index_path = index_path
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.index_path))
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
        except Exception:
            pass
        return conn

    def _ensure_schema(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS sources ("
                " path TEXT PRIMARY KEY,"
                " mtime REAL NOT NULL,"
                " size INTEGER NOT NULL,"
                " last_line INTEGER NOT NULL"
                ")"
            )
            try:
                conn.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5("
                    " doc_id UNINDEXED,"
                    " agent_id UNINDEXED,"
                    " memory_type UNINDEXED,"
                    " ts UNINDEXED,"
                    " session_id UNINDEXED,"
                    " key,"
                    " content,"
                    " metadata,"
                    " tokenize='unicode61'"
                    ")"
                )
            except sqlite3.OperationalError as e:
                raise RuntimeError(f"FTS5 is not available in this sqlite build: {e}")
            conn.commit()
        finally:
            conn.close()

    def _get_source_state(self, conn: sqlite3.Connection, path: str) -> Optional[sqlite3.Row]:
        cur = conn.execute("SELECT path, mtime, size, last_line FROM sources WHERE path=?", (path,))
        return cur.fetchone()

    def _upsert_source_state(self, conn: sqlite3.Connection, *, path: str, mtime: float, size: int, last_line: int) -> None:
        conn.execute(
            "INSERT INTO sources(path, mtime, size, last_line) VALUES(?,?,?,?) "
            "ON CONFLICT(path) DO UPDATE SET mtime=excluded.mtime, size=excluded.size, last_line=excluded.last_line",
            (path, float(mtime), int(size), int(last_line)),
        )

    def rebuild(self) -> None:
        conn = self._connect()
        try:
            conn.execute("DROP TABLE IF EXISTS sources")
            conn.execute("DROP TABLE IF EXISTS memory_fts")
            conn.commit()
        finally:
            conn.close()
        self._ensure_schema()
        self.sync()

    def sync(self) -> Dict[str, Any]:
        paths: List[Path] = []
        mem_md = self.files_root / "Memory.md"
        if mem_md.exists():
            paths.append(mem_md)
        events_dir = self.files_root / "events"
        if events_dir.exists():
            paths.extend(sorted([p for p in events_dir.glob("*.jsonl") if p.is_file()]))
        sessions_dir = self.files_root / "sessions"
        if sessions_dir.exists():
            paths.extend(sorted([p for p in sessions_dir.glob("*.jsonl") if p.is_file()]))
        return self.sync_paths(paths)

    def sync_paths(self, paths: Sequence[Path]) -> Dict[str, Any]:
        conn = self._connect()
        indexed_docs = 0
        touched_sources = 0
        try:
            for p in paths:
                try:
                    if not p.exists() or not p.is_file():
                        continue
                    st = p.stat()
                    state = self._get_source_state(conn, str(p))
                    prev_mtime = float(state["mtime"]) if state else None
                    prev_size = int(state["size"]) if state else None
                    prev_last_line = int(state["last_line"]) if state else 0

                    is_append_only = state is not None and prev_size is not None and int(st.st_size) >= prev_size
                    if state is not None and prev_mtime == float(st.st_mtime) and prev_size == int(st.st_size):
                        continue

                    if p.name.lower() == "memory.md":
                        indexed_docs += self._index_memory_md(conn, p)
                        self._upsert_source_state(
                            conn,
                            path=str(p),
                            mtime=st.st_mtime,
                            size=st.st_size,
                            last_line=0,
                        )
                        touched_sources += 1
                        continue

                    if p.suffix.lower() == ".jsonl":
                        if not is_append_only:
                            indexed_docs += self._reindex_jsonl(conn, p)
                            self._upsert_source_state(
                                conn,
                                path=str(p),
                                mtime=st.st_mtime,
                                size=st.st_size,
                                last_line=self._count_lines(p),
                            )
                            touched_sources += 1
                        else:
                            added, last_line = self._index_jsonl_append(conn, p, start_line=prev_last_line)
                            indexed_docs += added
                            self._upsert_source_state(
                                conn,
                                path=str(p),
                                mtime=st.st_mtime,
                                size=st.st_size,
                                last_line=last_line,
                            )
                            touched_sources += 1
                except Exception as e:
                    logger.warning("MemoryIndex sync failed for path=%s err=%s", p, e)
                    continue

            conn.commit()
        finally:
            conn.close()

        return {"success": True, "sources": touched_sources, "docs": indexed_docs}

    def _count_lines(self, p: Path) -> int:
        try:
            return len(p.read_text(encoding="utf-8", errors="ignore").splitlines())
        except Exception:
            return 0

    def _index_memory_md(self, conn: sqlite3.Connection, p: Path) -> int:
        try:
            content = (p.read_text(encoding="utf-8", errors="ignore") or "").strip()
        except Exception:
            content = ""
        ts = ""
        try:
            ts = datetime.utcfromtimestamp(p.stat().st_mtime).isoformat()
        except Exception:
            ts = datetime.utcnow().isoformat()

        doc_id = "memory_md"
        metadata = {"path": str(p), "importance": 90}
        conn.execute(
            "INSERT OR REPLACE INTO memory_fts(doc_id, agent_id, memory_type, ts, session_id, key, content, metadata) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (doc_id, "*", "source", ts, None, "Memory.md", content[:20000], json.dumps(metadata, ensure_ascii=False)),
        )
        return 1

    def _reindex_jsonl(self, conn: sqlite3.Connection, p: Path) -> int:
        try:
            lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            lines = []

        indexed = 0
        for i, ln in enumerate(lines, 1):
            ln = (ln or "").strip()
            if not ln:
                continue
            try:
                obj = json.loads(ln)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            if self._index_event_obj(conn, p, i, obj):
                indexed += 1
        return indexed

    def _index_jsonl_append(self, conn: sqlite3.Connection, p: Path, *, start_line: int) -> (int, int):
        try:
            lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            lines = []

        total = len(lines)
        indexed = 0
        for i in range(max(0, int(start_line)), total):
            ln = (lines[i] or "").strip()
            if not ln:
                continue
            try:
                obj = json.loads(ln)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            if self._index_event_obj(conn, p, i + 1, obj):
                indexed += 1
        return indexed, total

    def _index_event_obj(self, conn: sqlite3.Connection, p: Path, line_no: int, obj: Dict[str, Any]) -> bool:
        agent_id = str(obj.get("agent_id") or "*")
        session_id = obj.get("session_id")
        event_type = str(obj.get("event_type") or "event")
        memory_type = str(obj.get("memory_type") or event_type)
        ts = str(obj.get("ts") or "")
        if not ts:
            ts = datetime.utcnow().isoformat()

        key = str(obj.get("key") or event_type)
        content = str(obj.get("content") or obj.get("summary") or "")
        metadata = obj.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {"metadata": metadata}
        if "importance" not in metadata and obj.get("importance") is not None:
            metadata["importance"] = obj.get("importance")
        metadata.setdefault("source_path", str(p))
        metadata.setdefault("source_line", line_no)
        metadata.setdefault("event_type", event_type)

        doc_id = f"{str(p)}:{line_no}"

        conn.execute(
            "INSERT OR REPLACE INTO memory_fts(doc_id, agent_id, memory_type, ts, session_id, key, content, metadata) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (
                doc_id,
                agent_id,
                memory_type,
                ts,
                str(session_id) if session_id is not None else None,
                key[:500],
                content[:20000],
                json.dumps(metadata, ensure_ascii=False),
            ),
        )
        return True

    def search(
        self,
        query: str,
        *,
        agent_id: Optional[str] = None,
        memory_types: Optional[Sequence[str]] = None,
        session_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[MemoryIndexHit]:
        q = (query or "").strip()
        limit = max(1, int(limit or 5))

        conn = self._connect()
        try:
            where = []
            params: List[Any] = []
            if q:
                where.append("memory_fts MATCH ?")
                params.append(q)
            else:
                where.append("1=1")

            if agent_id:
                where.append("agent_id=?")
                params.append(agent_id)

            if session_id:
                where.append("session_id=?")
                params.append(session_id)

            if memory_types:
                placeholders = ",".join(["?"] * len(list(memory_types)))
                where.append(f"memory_type IN ({placeholders})")
                params.extend(list(memory_types))

            where_sql = " AND ".join(where)

            if q:
                sql = (
                    "SELECT doc_id, agent_id, memory_type, ts, session_id, key, content, metadata, "
                    " bm25(memory_fts) AS score "
                    "FROM memory_fts "
                    f"WHERE {where_sql} "
                    "ORDER BY score ASC, ts DESC "
                    "LIMIT ?"
                )
            else:
                sql = (
                    "SELECT doc_id, agent_id, memory_type, ts, session_id, key, content, metadata, 0.0 AS score "
                    "FROM memory_fts "
                    f"WHERE {where_sql} "
                    "ORDER BY ts DESC "
                    "LIMIT ?"
                )

            params.append(limit)
            rows = conn.execute(sql, tuple(params)).fetchall()

            hits: List[MemoryIndexHit] = []
            for r in rows:
                try:
                    md = {}
                    try:
                        md = json.loads(r["metadata"] or "{}")
                    except Exception:
                        md = {}
                    if not isinstance(md, dict):
                        md = {"metadata": md}

                    hits.append(
                        MemoryIndexHit(
                            doc_id=str(r["doc_id"]),
                            agent_id=str(r["agent_id"]),
                            memory_type=str(r["memory_type"]),
                            key=str(r["key"] or ""),
                            content=str(r["content"] or ""),
                            metadata=md,
                            ts=str(r["ts"] or ""),
                            session_id=str(r["session_id"]) if r["session_id"] is not None else None,
                            score=float(r["score"] or 0.0),
                        )
                    )
                except Exception:
                    continue
            return hits
        finally:
            conn.close()

    def get(self, doc_id: str) -> Optional[MemoryIndexHit]:
        did = (doc_id or "").strip()
        if not did:
            return None

        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT doc_id, agent_id, memory_type, ts, session_id, key, content, metadata, 0.0 AS score "
                "FROM memory_fts WHERE doc_id=?",
                (did,),
            ).fetchone()
            if not row:
                return None

            md = {}
            try:
                md = json.loads(row["metadata"] or "{}")
            except Exception:
                md = {}
            if not isinstance(md, dict):
                md = {"metadata": md}

            return MemoryIndexHit(
                doc_id=str(row["doc_id"]),
                agent_id=str(row["agent_id"]),
                memory_type=str(row["memory_type"]),
                key=str(row["key"] or ""),
                content=str(row["content"] or ""),
                metadata=md,
                ts=str(row["ts"] or ""),
                session_id=str(row["session_id"]) if row["session_id"] is not None else None,
                score=0.0,
            )
        finally:
            conn.close()


_default_index: Optional[MemoryIndex] = None


def get_default_memory_index(*, files_root: Path) -> MemoryIndex:
    global _default_index
    if _default_index is None or _default_index.files_root != files_root:
        index_path = Path(__file__).resolve().parent / "index" / "memory_index.sqlite"
        _default_index = MemoryIndex(files_root=files_root, index_path=index_path)
    return _default_index
