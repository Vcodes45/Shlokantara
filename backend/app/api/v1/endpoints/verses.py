from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.db.models import Verse

router = APIRouter()


@router.get("/{chapter_number}/{verse_number}")
def get_verse(
    chapter_number: int,
    verse_number: int,
    db: Session = Depends(get_db),
):
    statement = (
        select(Verse)
        .where(
            Verse.chapter_number == chapter_number,
            Verse.verse_number == verse_number,
        )
        .options(
            selectinload(Verse.source),
            selectinload(Verse.translations),
            selectinload(Verse.commentaries),
        )
    )

    verse = db.scalar(statement)

    if verse is None:
        raise HTTPException(
            status_code=404,
            detail="Verse not found in the Shlokantara corpus.",
        )

    return {
        "verse_id": verse.verse_id,
        "chapter_number": verse.chapter_number,
        "verse_number": verse.verse_number,
        "sanskrit_text": verse.sanskrit_text,
        "transliteration": verse.transliteration,
        "source": {
            "id": verse.source.id,
            "title": verse.source.title,
            "creator": verse.source.creator,
            "source_url": verse.source.source_url,
        },
        "translations": [
            {
                "language_code": translation.language_code,
                "text": translation.text,
                "translator": translation.translator,
                "edition": translation.edition,
                "source_id": translation.source_id,
            }
            for translation in verse.translations
        ],
        "commentaries": [
            {
                "language_code": commentary.language_code,
                "commentator": commentary.commentator,
                "tradition": commentary.tradition,
                "text": commentary.text,
                "source_id": commentary.source_id,
            }
            for commentary in verse.commentaries
        ],
    }
