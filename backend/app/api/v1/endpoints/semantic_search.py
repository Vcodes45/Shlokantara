from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.db.models import KnowledgeChunk, Source, Verse
from app.db.session import get_db
from app.rag.embedding_service import embed_query

router = APIRouter()


@router.get("/semantic")
def semantic_search(
    q: str = Query(min_length=1, max_length=1000),
    language: str | None = Query(default=None, max_length=16),
    content_type: str | None = Query(default=None, max_length=30),
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    query_text = q.strip()

    if not query_text:
        raise HTTPException(status_code=422, detail="Query cannot be empty.")

    query_vector = embed_query(query_text)
    chunk_source = aliased(Source)
    distance = KnowledgeChunk.embedding.cosine_distance(query_vector)

    statement = (
        select(
            KnowledgeChunk,
            Verse,
            chunk_source,
            distance.label("distance"),
        )
        .join(Verse, KnowledgeChunk.verse_id == Verse.verse_id)
        .join(chunk_source, KnowledgeChunk.source_id == chunk_source.id)
        .where(KnowledgeChunk.embedding.is_not(None))
    )

    if language:
        statement = statement.where(
            KnowledgeChunk.language_code == language.strip().lower()
        )

    if content_type:
        statement = statement.where(
            KnowledgeChunk.content_type == content_type.strip().lower()
        )

    rows = db.execute(
        statement.order_by(distance).limit(limit)
    ).all()

    results = []

    for chunk, verse, source, distance_value in rows:
        results.append(
            {
                "verse_id": chunk.verse_id,
                "chapter_number": verse.chapter_number,
                "verse_number": verse.verse_number,
                "content_type": chunk.content_type,
                "language_code": chunk.language_code,
                "content": chunk.content,
                "source": {
                    "title": source.title,
                    "creator": source.creator,
                    "source_url": source.source_url,
                    "license_name": source.license_name,
                },
                "similarity_score": round(
                    1.0 - float(distance_value), 4
                ),
            }
        )

    return {
        "query": query_text,
        "embedding_model": "BAAI/bge-m3",
        "count": len(results),
        "results": results,
    }
