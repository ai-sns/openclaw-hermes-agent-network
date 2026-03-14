import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from backend.apps.sns.memory.memory_config import MemoryConfig
from backend.apps.sns.memory.memory_index import MemoryIndex

logger = logging.getLogger(__name__)


@dataclass
class MemoryVectorHit:
    doc_id: str
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    score: float


def _chunk_text_advanced(text: str, *, chunk_size: int, overlap: int) -> List[str]:
    if not text:
        return []

    s = str(text)
    if len(s) <= chunk_size:
        return [s.strip()] if s.strip() else []

    # Split by strong boundaries first.
    import re

    parts = re.split(r"([\n。！？；.!?;])", s)
    segments: List[str] = []
    buf = ""
    for p in parts:
        if p is None:
            continue
        buf += p
        if p in {"\n", "。", "！", "？", "；", ".", "!", "?", ";"}:
            seg = buf.strip()
            if seg:
                segments.append(seg)
            buf = ""
    tail = buf.strip()
    if tail:
        segments.append(tail)

    # Assemble into chunks with overlap.
    chunks: List[str] = []
    cur = ""
    for seg in segments:
        if not cur:
            cur = seg
            continue
        if len(cur) + 1 + len(seg) <= chunk_size:
            cur = cur + " " + seg
            continue
        chunks.append(cur.strip())
        # overlap: take last N chars
        if overlap > 0:
            cur = (cur[-overlap:] + " " + seg).strip()
        else:
            cur = seg

    if cur.strip():
        chunks.append(cur.strip())

    # Final fallback: hard split if any chunk still too large
    out: List[str] = []
    for c in chunks:
        c = c.strip()
        if not c:
            continue
        if len(c) <= chunk_size:
            out.append(c)
            continue
        start = 0
        while start < len(c):
            end = min(len(c), start + chunk_size)
            out.append(c[start:end].strip())
            if end >= len(c):
                break
            start = max(0, end - overlap)

    return [x for x in out if x]


class MemoryVectorIndex:
    def __init__(self, *, persist_directory: str = "km/chroma_db"):
        self.persist_directory = persist_directory

    def _get_vector_service(self):
        # Import lazily so memory can run without vector deps.
        from backend.modules.km.vector_service import get_vector_service

        return get_vector_service()

    def _collection(self, agent_id: str):
        vs = self._get_vector_service()
        name = f"mem_{str(agent_id or 'default')}"
        return vs.client.get_or_create_collection(name=name, metadata={"type": "memory", "agent_id": str(agent_id or '')})

    def _ensure_state_table(self, conn) -> None:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS vector_state ("
            " agent_id TEXT PRIMARY KEY,"
            " last_rowid INTEGER NOT NULL,"
            " updated_at TEXT"
            ")"
        )

    def _get_last_rowid(self, conn, agent_id: str) -> int:
        row = conn.execute("SELECT last_rowid FROM vector_state WHERE agent_id=?", (agent_id,)).fetchone()
        if not row:
            return 0
        try:
            return int(row[0] or 0)
        except Exception:
            return 0

    def _set_last_rowid(self, conn, agent_id: str, last_rowid: int) -> None:
        conn.execute(
            "INSERT INTO vector_state(agent_id, last_rowid, updated_at) VALUES(?,?,?) "
            "ON CONFLICT(agent_id) DO UPDATE SET last_rowid=excluded.last_rowid, updated_at=excluded.updated_at",
            (agent_id, int(last_rowid or 0), datetime.utcnow().isoformat()),
        )

    def sync_from_fts(self, memory_index: MemoryIndex, *, agent_id: str) -> Dict[str, Any]:
        if not (MemoryConfig.ENABLED and MemoryConfig.EMBEDDING_ENABLED):
            return {"success": True, "docs": 0, "chunks": 0}

        # Sync FTS first so we see latest rows.
        try:
            memory_index.sync()
        except Exception:
            pass

        import sqlite3

        conn = sqlite3.connect(str(memory_index.index_path))
        conn.row_factory = sqlite3.Row
        docs_added = 0
        chunks_added = 0
        try:
            self._ensure_state_table(conn)
            last_rowid = self._get_last_rowid(conn, agent_id)

            # Include global source docs (agent_id='*') and current agent docs.
            rows = conn.execute(
                "SELECT rowid, doc_id, agent_id, memory_type, ts, session_id, key, content, metadata "
                "FROM memory_fts "
                "WHERE rowid > ? AND (agent_id=? OR agent_id='*') "
                "ORDER BY rowid ASC LIMIT 200",
                (int(last_rowid), str(agent_id)),
            ).fetchall()

            if not rows:
                return {"success": True, "docs": 0, "chunks": 0}

            vs = self._get_vector_service()
            col = self._collection(agent_id)

            batch_texts: List[str] = []
            batch_ids: List[str] = []
            batch_metas: List[dict] = []
            batch_docs: List[str] = []

            def flush():
                nonlocal chunks_added
                if not batch_ids:
                    return
                try:
                    # Try batch embedding to reduce API calls.
                    embs = None
                    try:
                        resp = vs.openai_client.embeddings.create(
                            input=batch_texts,
                            model=getattr(vs, 'embedding_model', None) or getattr(vs, 'embedding_model', 'text-embedding-3-small'),
                        )
                        embs = [d.embedding for d in resp.data]
                    except Exception:
                        embs = [vs.get_embedding(t) for t in batch_texts]

                    try:
                        col.upsert(ids=batch_ids, embeddings=embs, documents=batch_docs, metadatas=batch_metas)
                    except Exception:
                        # Fallback for older chroma
                        try:
                            col.delete(ids=batch_ids)
                        except Exception:
                            pass
                        col.add(ids=batch_ids, embeddings=embs, documents=batch_docs, metadatas=batch_metas)

                    chunks_added += len(batch_ids)
                except Exception as e:
                    logger.warning("Memory vector upsert failed: %s", e)
                finally:
                    batch_texts.clear()
                    batch_ids.clear()
                    batch_metas.clear()
                    batch_docs.clear()

            max_chunk = int(getattr(MemoryConfig, 'EMBEDDING_CHUNK_SIZE', 1200) or 1200)
            overlap = int(getattr(MemoryConfig, 'EMBEDDING_CHUNK_OVERLAP', 150) or 150)

            max_seen_rowid = last_rowid
            for r in rows:
                try:
                    rowid = int(r['rowid'])
                    max_seen_rowid = max(max_seen_rowid, rowid)
                    doc_id = str(r['doc_id'])
                    key = str(r['key'] or '')
                    content = str(r['content'] or '')
                    ts = str(r['ts'] or '')
                    mem_type = str(r['memory_type'] or '')
                    sess = r['session_id']

                    md = {}
                    try:
                        md = json.loads(r['metadata'] or '{}')
                    except Exception:
                        md = {}
                    if not isinstance(md, dict):
                        md = {"metadata": md}

                    base_text = (key + "\n" + content).strip()
                    if not base_text:
                        continue

                    chunks = _chunk_text_advanced(base_text, chunk_size=max_chunk, overlap=overlap)
                    if not chunks:
                        continue

                    docs_added += 1

                    for i, ch in enumerate(chunks):
                        chunk_id = f"{doc_id}#c{i}"
                        meta = {
                            **(md or {}),
                            "doc_id": doc_id,
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                            "ts": ts,
                            "key": key,
                            "memory_type": mem_type,
                        }
                        if sess is not None:
                            meta["session_id"] = str(sess)

                        batch_texts.append(ch)
                        batch_ids.append(chunk_id)
                        batch_docs.append(ch)
                        batch_metas.append(meta)

                        if len(batch_ids) >= 24:
                            flush()
                except Exception:
                    continue

            flush()
            self._set_last_rowid(conn, agent_id, max_seen_rowid)
            conn.commit()
            return {"success": True, "docs": docs_added, "chunks": chunks_added}
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def search(
        self,
        query: str,
        *,
        agent_id: str,
        top_k: int = 8,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[MemoryVectorHit]:
        if not (MemoryConfig.ENABLED and MemoryConfig.EMBEDDING_ENABLED):
            return []

        q = (query or '').strip()
        if not q:
            return []

        try:
            vs = self._get_vector_service()
            col = self._collection(agent_id)
            emb = vs.get_embedding(q)

            try:
                res = col.query(
                    query_embeddings=[emb],
                    n_results=max(1, int(top_k or 8)),
                    where=where or None,
                    include=["documents", "metadatas", "distances", "ids"],
                )
            except Exception:
                if where:
                    res = col.query(
                        query_embeddings=[emb],
                        n_results=max(1, int(top_k or 8)),
                        where=None,
                        include=["documents", "metadatas", "distances", "ids"],
                    )
                else:
                    raise

            out: List[MemoryVectorHit] = []
            docs = (res.get('documents') or [[]])[0] or []
            metas = (res.get('metadatas') or [[]])[0] or []
            dists = (res.get('distances') or [[]])[0] or []
            ids = (res.get('ids') or [[]])[0] or []

            for doc, md, dist, cid in zip(docs, metas, dists, ids):
                if not isinstance(md, dict):
                    md = {"metadata": md}
                doc_id = str(md.get('doc_id') or str(cid).split('#c', 1)[0])
                score = 1.0
                try:
                    score = 1.0 - float(dist)
                except Exception:
                    score = 0.0

                out.append(
                    MemoryVectorHit(
                        doc_id=doc_id,
                        chunk_id=str(cid),
                        content=str(doc or ''),
                        metadata=md,
                        score=score,
                    )
                )

            return out
        except Exception as e:
            logger.warning("Memory vector search failed: %s", e)
            return []


_default_vec: Optional[MemoryVectorIndex] = None


def get_default_memory_vector_index() -> MemoryVectorIndex:
    global _default_vec
    if _default_vec is None:
        _default_vec = MemoryVectorIndex()
    return _default_vec
