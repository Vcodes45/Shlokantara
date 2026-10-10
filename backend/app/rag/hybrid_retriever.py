import re

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import KnowledgeChunk, Source, Verse
from app.rag.embedding_service import embed_query

STOPWORDS = {
    "what", "does", "the", "say", "about", "how", "why",
    "is", "are", "in", "of", "to", "and", "a", "an",
    "for", "me", "can", "according", "gita", "tell",
}


def base_statement():
    return (
        select(KnowledgeChunk, Verse, Source)
        .join(Verse, KnowledgeChunk.verse_id == Verse.verse_id)
        .join(Source, KnowledgeChunk.source_id == Source.id)
    )


def apply_filters(statement, language=None, content_type=None):
    if language:
        statement = statement.where(
            KnowledgeChunk.language_code == language.strip().lower()
        )

    if content_type:
        statement = statement.where(
            KnowledgeChunk.content_type == content_type.strip().lower()
        )

    return statement


def serialize_result(chunk, verse, source):
    return {
        "chunk_key": chunk.chunk_key,
        "verse_id": verse.verse_id,
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
    }


def retrieve_hybrid(
    db: Session,
    query: str,
    language: str | None = None,
    content_type: str | None = None,
    limit: int = 5,
):
    candidate_limit = min(max(limit * 10, 30), 100)
    ranked = {}

    def add_result(row, rank_type, rank, similarity=None):
        chunk, verse, source = row[:3]
        key = chunk.chunk_key

        if key not in ranked:
            ranked[key] = serialize_result(chunk, verse, source)
            ranked[key]["semantic_rank"] = None
            ranked[key]["keyword_rank"] = None
            ranked[key]["semantic_similarity"] = None
            ranked[key]["hybrid_score"] = 0.0

        ranked[key][rank_type] = rank

        if similarity is not None:
            ranked[key]["semantic_similarity"] = round(
                similarity, 4
            )

        # Reciprocal Rank Fusion: higher-ranked results contribute more.
        ranked[key]["hybrid_score"] += 1.0 / (60 + rank)

    # 1. Handle direct verse references without embedding the query.
    reference = re.fullmatch(
        r"(?:BG[_\s-]*)?(\d{1,2})[._:/\s-]+(\d{1,3})",
        query.strip(),
        flags=re.IGNORECASE,
    )

    if reference:
        chapter, verse_number = map(int, reference.groups())

        exact_statement = (
            base_statement()
            .where(
                Verse.chapter_number == chapter,
                Verse.verse_number == verse_number,
            )
        )
        exact_statement = apply_filters(
            exact_statement, language, content_type
        )

        exact_rows = db.execute(
            exact_statement.order_by(
                KnowledgeChunk.content_type,
                KnowledgeChunk.language_code,
            )
        ).all()

        return [
            {
                **serialize_result(chunk, verse, source),
                "semantic_rank": None,
                "keyword_rank": None,
                "semantic_similarity": None,
                "hybrid_score": 1.0,
            }
            for chunk, verse, source in exact_rows
        ][:limit]

    # 2. Semantic retrieval.
    query_vector = embed_query(query)

    semantic_statement = base_statement().where(
        KnowledgeChunk.embedding.is_not(None)
    )
    semantic_statement = apply_filters(
        semantic_statement, language, content_type
    )

    distance = KnowledgeChunk.embedding.cosine_distance(query_vector)

    semantic_rows = db.execute(
        semantic_statement
        .add_columns(distance.label("distance"))
        .order_by(distance)
        .limit(candidate_limit)
    ).all()

    for rank, row in enumerate(semantic_rows, start=1):
        distance_value = float(row[3])
        add_result(
            row,
            "semantic_rank",
            rank,
            similarity=1.0 - distance_value,
        )

    # 3. Keyword retrieval. Individual query terms can match independently.
    terms = list(
        dict.fromkeys(
            word
            for word in re.findall(r"[^\W_]+", query.casefold())
            if len(word) > 2 and word not in STOPWORDS
        )
    )

    if terms:
        conditions = [
            KnowledgeChunk.content.ilike(f"%{term}%")
            for term in terms
        ]

        keyword_statement = base_statement().where(
            or_(*conditions)
        )
        keyword_statement = apply_filters(
            keyword_statement, language, content_type
        )

        keyword_rows = db.execute(keyword_statement).all()

        keyword_rows.sort(
            key=lambda row: (
                -sum(
                    term in row[0].content.casefold()
                    for term in terms
                ),
                row[0].chunk_key,
            )
        )

        for rank, row in enumerate(
            keyword_rows[:candidate_limit], start=1
        ):
            add_result(row, "keyword_rank", rank)

    # 4. Return the combined ranking.
    results = list(ranked.values())
    results.sort(
        key=lambda item: (
            -item["hybrid_score"],
            item["verse_id"],
            item["language_code"],
        )
    )

    return results[:limit]
