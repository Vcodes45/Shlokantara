from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.rag.hybrid_retriever import retrieve_hybrid

router = APIRouter()


@router.get("/hybrid")
def hybrid_search(
    q: str = Query(min_length=1, max_length=1000),
    language: str | None = Query(default=None, max_length=16),
    content_type: str | None = Query(default=None, max_length=30),
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    query = q.strip()

    if not query:
        raise HTTPException(
            status_code=422,
            detail="Query cannot be empty.",
        )

    results = retrieve_hybrid(
        db=db,
        query=query,
        language=language,
        content_type=content_type,
        limit=limit,
    )

    return {
        "query": query,
        "strategy": "hybrid_rrf",
        "count": len(results),
        "results": results,
    }
