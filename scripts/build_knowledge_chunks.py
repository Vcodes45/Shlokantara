import hashlib

from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models import Commentary, KnowledgeChunk, Translation, Verse


def make_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def save_chunk(
    db,
    chunk_key,
    verse_id,
    source_id,
    content_type,
    language_code,
    content,
):
    content_hash = make_hash(content)

    chunk = db.scalar(
        select(KnowledgeChunk).where(
            KnowledgeChunk.chunk_key == chunk_key
        )
    )

    if chunk is None:
        chunk = KnowledgeChunk(
            chunk_key=chunk_key,
            content_hash=content_hash,
            verse_id=verse_id,
            source_id=source_id,
            content_type=content_type,
            language_code=language_code,
            content=content,
            embedding=None,
        )
        db.add(chunk)
    else:
        if chunk.content_hash != content_hash:
            chunk.embedding = None

        chunk.content_hash = content_hash
        chunk.verse_id = verse_id
        chunk.source_id = source_id
        chunk.content_type = content_type
        chunk.language_code = language_code
        chunk.content = content

    db.flush()


def main():
    counts = {
        "sanskrit": 0,
        "translation": 0,
        "commentary": 0,
    }

    with SessionLocal() as db:
        try:
            verses = db.scalars(
                select(Verse).order_by(
                    Verse.chapter_number, Verse.verse_number
                )
            ).all()

            for verse in verses:
                source = verse.source

                content = (
                    f"Bhagavad Gita Chapter {verse.chapter_number}, "
                    f"Verse {verse.verse_number}.\n"
                    f"Language: Sanskrit.\n"
                    f"Original verse: {verse.sanskrit_text}\n"
                    f"Transliteration: {verse.transliteration or ''}\n"
                    f"Source: {source.title}.\n"
                    f"Creator: {source.creator or 'Not specified'}."
                )

                save_chunk(
                    db,
                    f"verse:{verse.verse_id}",
                    verse.verse_id,
                    verse.source_id,
                    "sanskrit",
                    "sa",
                    content,
                )
                counts["sanskrit"] += 1

            translations = db.scalars(select(Translation)).all()

            for item in translations:
                verse = item.verse
                source = item.source

                content = (
                    f"Bhagavad Gita Chapter {verse.chapter_number}, "
                    f"Verse {verse.verse_number}.\n"
                    f"Language: {item.language_code}.\n"
                    f"Content type: translation.\n"
                    f"Translator: {item.translator or 'Not specified'}.\n"
                    f"Edition: {item.edition or 'Not specified'}.\n"
                    f"Source: {source.title}.\n"
                    f"Translation: {item.text}"
                )

                save_chunk(
                    db,
                    f"translation:{item.id}",
                    item.verse_id,
                    item.source_id,
                    "translation",
                    item.language_code,
                    content,
                )
                counts["translation"] += 1

            commentaries = db.scalars(select(Commentary)).all()

            for item in commentaries:
                verse = item.verse
                source = item.source

                content = (
                    f"Bhagavad Gita Chapter {verse.chapter_number}, "
                    f"Verse {verse.verse_number}.\n"
                    f"Language: {item.language_code}.\n"
                    f"Content type: commentary.\n"
                    f"Commentator: {item.commentator or 'Not specified'}.\n"
                    f"Tradition: {item.tradition or 'Not specified'}.\n"
                    f"Source: {source.title}.\n"
                    f"Commentary: {item.text}"
                )

                save_chunk(
                    db,
                    f"commentary:{item.id}",
                    item.verse_id,
                    item.source_id,
                    "commentary",
                    item.language_code,
                    content,
                )
                counts["commentary"] += 1

            db.commit()

        except Exception:
            db.rollback()
            raise

    print("Knowledge chunk preparation completed.")
    print(f"Sanskrit records processed: {counts['sanskrit']}")
    print(f"Translation records processed: {counts['translation']}")
    print(f"Commentary records processed: {counts['commentary']}")


if __name__ == "__main__":
    main()
