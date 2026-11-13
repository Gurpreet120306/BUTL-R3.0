from fastapi import APIRouter, HTTPException, Query, Request

from backend.shared.contracts import AnalyzedObservation, DeleteResult, MemoryList

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("", response_model=MemoryList)
async def recent(request: Request, limit: int = Query(default=20, ge=1, le=50)):
    return MemoryList(items=await request.app.state.retriever.recent(limit))


@router.get("/search", response_model=MemoryList)
async def search(request: Request, q: str = Query(min_length=1, max_length=500), limit: int = Query(default=10, ge=1, le=50)):
    return MemoryList(items=await request.app.state.retriever.search(q, limit))


@router.get("/{memory_id}", response_model=AnalyzedObservation)
async def get(request: Request, memory_id: str):
    item = await request.app.state.retriever.get(memory_id)
    if item is None:
        raise HTTPException(404, "Memory was not found")
    return item


@router.delete("/{memory_id}", response_model=DeleteResult)
async def delete(request: Request, memory_id: str):
    count = await request.app.state.memory.delete(memory_id)
    if not count:
        raise HTTPException(404, "Memory was not found")
    request.app.state.latest = None
    return DeleteResult(deleted=count)


@router.delete("", response_model=DeleteResult)
async def clear(request: Request, confirm: str = Query(default="")):
    if confirm != "DELETE ALL MEMORIES":
        raise HTTPException(400, "Explicit confirmation is required: DELETE ALL MEMORIES")
    count = await request.app.state.memory.clear()
    request.app.state.latest = None
    return DeleteResult(deleted=count)
