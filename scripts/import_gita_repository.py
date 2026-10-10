import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import delete, select
from app.db.session import SessionLocal
from app.db.models import (
    Commentary,
    KnowledgeChunk,
    Source,
    Translation,
    Verse,
)

DATA_DIR = ROOT / "data" / "raw" / "gita-main" / "data"

VERSE_SOURCE_KEY = "gita_repo_verse_corpus"
TEST_SOURCE_KEYS = {
    "shlokantara_dev_fixture",
    "shlokantara_en_draft",
}

LANGUAGES = {
    "english": "en",
    "hindi": "hi",
    "sanskrit": "sa",
}

SOURCE_LICENSE_NOTE = (
    "The upstream repository contains an Unlicense file, but rights in "
    "this individual translation/commentary have not been independently "
    "verified. Check the text-level rights before public redistribution."
)


def load_json(filename):
    path = DATA_DIR / filename
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def clean_text(value):
    return str(value or "").strip()


def language_code(value):
    language = clean_text(value).lower()
    return LANGUAGES.get(language, language[:16] or "und")


def author_slug(name):
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug[:55] or "unknown_author"


def build_source_key(kind, lang, author_id, author_name):
    if author_id is not None:
        author_key = str(author_id)
    else:
        author_key = author_slug(author_name)

    return f"gita_repo_{kind}_{lang}_{author_key}"


def main():
    verse_records = load_json("verse.json")
    translation_records = load_json("translation.json")
    commentary_records = load_json("commentary.json")
    authors = load_json("authors.json")

    author_names = {
        str(author["id"]): author["name"]
        for author in authors
    }

    source_specs = {
        VERSE_SOURCE_KEY: {
            "title": "Bhagavad Gita Sanskrit verse corpus",
            "creator": "gita/gita repository contributors",
            "language_code": "sa",
            "source_url": (
                "https://github.com/gita/gita/blob/main/data/verse.json"
            ),
            "license_name": (
                "Repository-level Unlicense; review data provenance"
            ),
            "license_url": (
                "https://github.com/gita/gita/blob/main/LICENSE"
            ),
            "edition": "gita/gita JSON dataset",
            "notes": (
                "Original source record fields are preserved where possible. "
                "The repository includes verse text, transliteration and "
                "word meanings."
            ),
        }
    }

    prepared_translations = []
    prepared_commentaries = []
    skipped_translations = 0
    skipped_commentaries = 0

    def prepare_records(records, kind, filename, destination):
        nonlocal skipped_translations, skipped_commentaries

        for record in records:
            content = clean_text(record.get("description"))

            if not content:
                if kind == "translation":
                    skipped_translations += 1
                else:
                    skipped_commentaries += 1
                continue

            raw_language = record.get("lang")
            lang = language_code(raw_language)
            author_id = record.get("author_id")
            author_name = (
                clean_text(record.get("authorName"))
                or author_names.get(str(author_id), "")
                or "Unknown author"
            )

            source_key = build_source_key(
                kind, lang, author_id, author_name
            )

            source_specs[source_key] = {
                "title": (
                    f"Bhagavad Gita {kind} — {author_name} ({lang})"
                ),
                "creator": author_name,
                "language_code": lang,
                "source_url": (
                    f"https://github.com/gita/gita/blob/main/data/{filename}"
                ),
                "license_name": (
                    "Text-level rights not independently verified"
                ),
                "license_url": None,
                "edition": "gita/gita JSON dataset; edition not specified",
                "notes": (
                    f"Upstream dataset record ID: {record.get('id')}. "
                    f"{SOURCE_LICENSE_NOTE}"
                ),
            }

            destination.append({
                "record": record,
                "content": content,
                "language_code": lang,
                "author_name": author_name,
                "source_key": source_key,
            })

    prepare_records(
        translation_records,
        "translation",
        "translation.json",
        prepared_translations,
    )
    prepare_records(
        commentary_records,
        "commentary",
        "commentary.json",
        prepared_commentaries,
    )

    canonical_by_internal_id = {}
    seen_references = set()

    for record in verse_records:
        chapter = int(record["chapter_number"])
        number = int(record["verse_number"])
        reference = (chapter, number)

        if reference in seen_references:
            raise ValueError(f"Duplicate chapter/verse: {reference}")

        seen_references.add(reference)
        canonical_by_internal_id[record["id"]] = (
            f"BG_{chapter:02d}_{number:03d}"
        )

    missing_translation_refs = [
        item["record"].get("verse_id")
        for item in prepared_translations
        if item["record"].get("verse_id") not in canonical_by_internal_id
    ]
    missing_commentary_refs = [
        item["record"].get("verse_id")
        for item in prepared_commentaries
        if item["record"].get("verse_id") not in canonical_by_internal_id
    ]

    if missing_translation_refs or missing_commentary_refs:
        raise ValueError(
            "Dataset contains unmatched internal verse IDs. "
            f"Translations: {len(missing_translation_refs)}; "
            f"commentaries: {len(missing_commentary_refs)}. "
            "No data was imported."
        )

    counts = {
        "verses": 0,
        "translations": 0,
        "commentaries": 0,
        "sources": 0,
        "removed_test_sources": 0,
    }

    with SessionLocal() as db:
        try:
            existing_sources = {
                item.source_key: item
                for item in db.scalars(select(Source)).all()
            }

            for source_key, values in source_specs.items():
                source = existing_sources.get(source_key)

                if source is None:
                    source = Source(
                        source_key=source_key,
                        **values,
                    )
                    db.add(source)
                    existing_sources[source_key] = source
                    counts["sources"] += 1
                else:
                    for field, value in values.items():
                        setattr(source, field, value)

            db.flush()

            source_ids = {
                key: source.id
                for key, source in existing_sources.items()
            }

            existing_verses = {
                item.verse_id: item
                for item in db.scalars(select(Verse)).all()
            }

            for record in verse_records:
                chapter = int(record["chapter_number"])
                number = int(record["verse_number"])
                verse_id = canonical_by_internal_id[record["id"]]

                values = {
                    "chapter_number": chapter,
                    "verse_number": number,
                    "sanskrit_text": clean_text(record.get("text")),
                    "transliteration": (
                        clean_text(record.get("transliteration")) or None
                    ),
                    "source_id": source_ids[VERSE_SOURCE_KEY],
                }

                if not values["sanskrit_text"]:
                    raise ValueError(f"Empty Sanskrit text: {verse_id}")

                verse = existing_verses.get(verse_id)

                if verse is None:
                    verse = Verse(verse_id=verse_id, **values)
                    db.add(verse)
                    existing_verses[verse_id] = verse
                else:
                    for field, value in values.items():
                        setattr(verse, field, value)

                counts["verses"] += 1

            db.flush()

            existing_translations = {
                (
                    item.verse_id,
                    item.language_code,
                    item.source_id,
                ): item
                for item in db.scalars(select(Translation)).all()
            }

            for item in prepared_translations:
                record = item["record"]
                verse_id = canonical_by_internal_id[record["verse_id"]]
                source_id = source_ids[item["source_key"]]
                lang = item["language_code"]

                key = (verse_id, lang, source_id)
                values = {
                    "verse_id": verse_id,
                    "language_code": lang,
                    "text": item["content"],
                    "translator": item["author_name"],
                    "edition": "gita/gita JSON dataset",
                    "source_id": source_id,
                }

                translation = existing_translations.get(key)

                if translation is None:
                    translation = Translation(**values)
                    db.add(translation)
                    existing_translations[key] = translation
                else:
                    for field, value in values.items():
                        setattr(translation, field, value)

                counts["translations"] += 1

            existing_commentaries = {
                (
                    item.verse_id,
                    item.source_id,
                    item.text,
                    item.commentator,
                    item.section_reference,
                ): item
                for item in db.scalars(select(Commentary)).all()
            }

            for item in prepared_commentaries:
                record = item["record"]
                verse_id = canonical_by_internal_id[record["verse_id"]]
                source_id = source_ids[item["source_key"]]
                lang = item["language_code"]

                values = {
                    "verse_id": verse_id,
                    "language_code": lang,
                    "commentator": item["author_name"],
                    "tradition": None,
                    "section_reference": None,
                    "text": item["content"],
                    "source_id": source_id,
                }

                key = (
                    verse_id,
                    source_id,
                    values["text"],
                    values["commentator"],
                    values["section_reference"],
                )

                if key not in existing_commentaries:
                    commentary = Commentary(**values)
                    db.add(commentary)
                    existing_commentaries[key] = commentary

                counts["commentaries"] += 1

            db.flush()

            # Remove only the two known development-fixture sources.
            test_sources = db.scalars(
                select(Source).where(
                    Source.source_key.in_(TEST_SOURCE_KEYS)
                )
            ).all()
            test_ids = [source.id for source in test_sources]

            if test_ids:
                db.execute(
                    delete(KnowledgeChunk).where(
                        KnowledgeChunk.source_id.in_(test_ids)
                    )
                )
                db.execute(
                    delete(Translation).where(
                        Translation.source_id.in_(test_ids)
                    )
                )
                db.execute(
                    delete(Commentary).where(
                        Commentary.source_id.in_(test_ids)
                    )
                )
                db.flush()

                remaining_verses = db.scalars(
                    select(Verse).where(Verse.source_id.in_(test_ids))
                ).all()

                if remaining_verses:
                    raise RuntimeError(
                        "Test sources are still referenced by verse rows; "
                        "aborting cleanup to protect data."
                    )

                db.execute(
                    delete(Source).where(Source.id.in_(test_ids))
                )
                counts["removed_test_sources"] = len(test_ids)

            db.commit()

        except Exception:
            db.rollback()
            raise

    print("\nShlokantara corpus import completed.")
    print(f"Verse records processed: {counts['verses']}")
    print(f"Translation records processed: {counts['translations']}")
    print(f"Commentary records processed: {counts['commentaries']}")
    print(f"New source records: {counts['sources']}")
    print(f"Development sources removed: {counts['removed_test_sources']}")
    print(f"Empty translations skipped: {skipped_translations}")
    print(f"Empty commentaries skipped: {skipped_commentaries}")
    print("\nSource rights for individual translations/commentaries")
    print("remain unverified; do not publicly redistribute them yet.")


if __name__ == "__main__":
    main()
