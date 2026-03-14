from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from backend.apps.sns.memory.memory_manager import MemoryManager


router = APIRouter()


class MemorySyncResponse(BaseModel):
    success: bool
    sources: int = 0
    docs: int = 0


class MemorySearchRequest(BaseModel):
    query: str = ""
    agent_id: Optional[str] = None
    memory_types: Optional[List[str]] = None
    session_id: Optional[str] = None
    limit: int = 5


class MemorySearchResponse(BaseModel):
    success: bool
    results: List[Dict[str, Any]]


class MemoryGetResponse(BaseModel):
    success: bool
    result: Optional[Dict[str, Any]] = None


@router.post("/memory/sync", response_model=MemorySyncResponse)
async def memory_sync(agent_id: str = "default"):
    try:
        mm = MemoryManager(agent_id=agent_id)
        res = mm._index().sync()
        return MemorySyncResponse(**res)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/search", response_model=MemorySearchResponse)
async def memory_search(req: MemorySearchRequest):
    try:
        mm = MemoryManager(agent_id=req.agent_id or "default")
        mm._index().sync()
        hits = mm._index().search(
            req.query or "",
            agent_id=req.agent_id,
            memory_types=req.memory_types,
            session_id=req.session_id,
            limit=req.limit,
        )
        return MemorySearchResponse(success=True, results=[h.to_dict() for h in hits])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/get", response_model=MemoryGetResponse)
async def memory_get(doc_id: str, agent_id: str = "default"):
    try:
        mm = MemoryManager(agent_id=agent_id)
        mm._index().sync()
        hit = mm._index().get(doc_id)
        return MemoryGetResponse(success=True, result=hit.to_dict() if hit else None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
