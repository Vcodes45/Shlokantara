import re

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Translation, Verse
from app.db.session import get_db

router = APIRouter()


@router.get("")
def search_verses(
    q: str = Query(min_length=1, max_length=250),
    language: str | None = Query(default=None, max_length=16),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query_text = q.strip()
    if not query_text:
        return {"query": q, "count": 0, "results": []}

    options = [
        selectinload(Verse.source),
        selectinload(Verse.translations).selectinload(
            Translation.source
        ),
    ]

    statement = select(Verse).options(*options)

    reference = re.fullmatch(
        r"(?:BG[_\s-]*)?(\d{1,2})[._:/\s-]+(\d{1,3})",
        query_text,
        flags=re.IGNORECASE,
    )

    if reference:
        chapter_number = int(reference.group(1))
        verse_number = int(reference.group(2))

        statement = statement.where(
            Verse.chapter_number == chapter_number,
            Verse.verse_number == verse_number,
        )
    else:
        pattern = f"%{query_text}%"

        translation_conditions = [
            Translation.text.ilike(pattern)
        ]

        if language:
            translation_conditions.append(
                Translation.language_code == language.strip().lower()
            )

        statement = statement.where(
            or_(
                Verse.verse_id.ilike(pattern),
                Verse.sanskrit_text.ilike(pattern),
                Verse.transliteration.ilike(pattern),
                Verse.translations.any(
                    and_(*translation_conditions)
                ),
            )
        )

    statement = statement.order_by(
        Verse.chapter_number,
        Verse.verse_number,
    ).limit(limit)

    verses = db.scalars(statement).unique().all()

    results = []

    for verse in verses:
        translations = verse.translations

        if language and not reference:
            translations = [
                item
                for item in translations
                if item.language_code == language.strip().lower()
            ]

        results.append(
            {
                "verse_id": verse.verse_id,
                "chapter_number": verse.chapter_number,
                "verse_number": verse.verse_number,
                "sanskrit_text": verse.sanskrit_text,
                "transliteration": verse.transliteration,
                "source": {
                    "title": verse.source.title,
                    "creator": verse.source.creator,
                    "source_url": verse.source.source_url,
                },
                "translations": [
                    {
                        "language_code": item.language_code,
                        "text": item.text,
                        "translator": item.translator,
                        "edition": item.edition,
                        "source": {
                            "title": item.source.title,
                            "creator": item.source.creator,
                            "source_url": item.source.source_url,
                        },
                    }
                    for item in translations
                ],
            }
        )

    return {
        "query": query_text,
        "language_filter": language,
        "count": len(results),
        "results": results,
    }
