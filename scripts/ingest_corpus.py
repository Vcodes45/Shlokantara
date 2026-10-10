import json
import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db.session import SessionLocal
from app.db.models import Commentary, Source, Translation, Verse


DATA_FILE = ROOT / "data" / "sample" / "sample_verses.json"


def upsert_source(db, record):
    source = db.scalar(
        select(Source).where(Source.source_key == record["source_key"])
    )

    if source is None:
        source = Source(**record)
        db.add(source)
    else:
        for key, value in record.items():
            setattr(source, key, value)

    db.flush()
    return source


def get_source(source_map, source_key):
    source = source_map.get(source_key)

    if source is None:
        raise ValueError(
            f"Source '{source_key}' is missing from the input file."
        )

    return source


def upsert_verse(db, record, source_map):
    source = get_source(source_map, record["source_key"])

    values = {
        key: value
        for key, value in record.items()
        if key != "source_key"
    }
    values["source_id"] = source.id

    verse = db.get(Verse, values["verse_id"])

    if verse is None:
        verse = Verse(**values)
        db.add(verse)
    else:
        for key, value in values.items():
            setattr(verse, key, value)

    db.flush()
    return verse


def upsert_translation(db, record, source_map):
    source = get_source(source_map, record["source_key"])

    values = {
        key: value
        for key, value in record.items()
        if key != "source_key"
    }
    values["source_id"] = source.id

    existing = db.scalar(
        select(Translation).where(
            Translation.verse_id == values["verse_id"],
            Translation.language_code == values["language_code"],
            Translation.source_id == source.id,
        )
    )

    if existing is None:
        existing = Translation(**values)
        db.add(existing)
    else:
        for key, value in values.items():
            setattr(existing, key, value)

    db.flush()


def upsert_commentary(db, record, source_map):
    source = get_source(source_map, record["source_key"])

    values = {
        key: value
        for key, value in record.items()
        if key != "source_key"
    }
    values["source_id"] = source.id

    existing = db.scalar(
        select(Commentary).where(
            Commentary.verse_id == values["verse_id"],
            Commentary.source_id == source.id,
            Commentary.text == values["text"],
            Commentary.commentator == values.get("commentator"),
            Commentary.section_reference
            == values.get("section_reference"),
        )
    )

    if existing is None:
        db.add(Commentary(**values))

    db.flush()


def main():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Corpus file not found: {DATA_FILE}")

    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    source_map = {}

    with SessionLocal() as db:
        try:
            for record in data.get("sources", []):
                source = upsert_source(db, record)
                source_map[record["source_key"]] = source

            for record in data.get("verses", []):
                upsert_verse(db, record, source_map)

            for record in data.get("translations", []):
                upsert_translation(db, record, source_map)

            for record in data.get("commentaries", []):
                upsert_commentary(db, record, source_map)

            db.commit()

        except Exception:
            db.rollback()
            raise

    print("Corpus ingestion completed successfully.")
    print(f"Sources processed: {len(data.get('sources', []))}")
    print(f"Verses processed: {len(data.get('verses', []))}")
    print(f"Translations processed: {len(data.get('translations', []))}")
    print(f"Commentaries processed: {len(data.get('commentaries', []))}")


if __name__ == "__main__":
    main()
