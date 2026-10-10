import json
from collections import Counter
from pathlib import Path

root = Path("data/raw/gita-main/data")


def load(filename):
    with (root / filename).open(encoding="utf-8") as file:
        return json.load(file)


verses = load("verse.json")
translations = load("translation.json")
commentaries = load("commentary.json")
languages = load("languages.json")
authors = load("authors.json")
chapters = load("chapters.json")

print("\n========== LANGUAGES ==========")
for language in languages:
    print(language)

print("\n========== AUTHORS ==========")
print("Total authors:", len(authors))
for author in authors[:8]:
    print(author)

print("\n========== RECORD COUNTS ==========")
print("Verses:", len(verses))
print("Translations:", len(translations))
print("Commentaries:", len(commentaries))
print("Chapters:", len(chapters))

print("\n========== TRANSLATION LANGUAGES ==========")
print(Counter(str(x.get("lang")) for x in translations))

print("\n========== COMMENTARY LANGUAGES ==========")
print(Counter(str(x.get("lang")) for x in commentaries))

print("\n========== VERSES PER CHAPTER ==========")
chapter_counts = Counter(
    int(v["chapter_number"]) for v in verses
)

for chapter in sorted(chapter_counts):
    metadata = next(
        (
            c for c in chapters
            if int(c["chapter_number"]) == chapter
        ),
        {},
    )
    print(
        f"Chapter {chapter}: "
        f"{chapter_counts[chapter]} records; "
        f"metadata count={metadata.get('verses_count')}"
    )

print("\n========== DUPLICATE REFERENCES ==========")
references = Counter(
    (int(v["chapter_number"]), int(v["verse_number"]))
    for v in verses
)
print([
    reference for reference, count in references.items()
    if count > 1
] or "None")

print("\n========== UNMATCHED REFERENCES ==========")
verse_ids = {v["id"] for v in verses}

for name, records in [
    ("Translations", translations),
    ("Commentaries", commentaries),
]:
    unmatched = [
        x for x in records
        if x.get("verse_id") not in verse_ids
    ]
    print(f"{name}: {len(unmatched)}")

print("\n========== VERSE 2.47 ==========")
target = next(
    (
        v for v in verses
        if int(v["chapter_number"]) == 2
        and int(v["verse_number"]) == 47
    ),
    None,
)

if target:
    print("Verse record:", target)
    print("Matching translations:")

    for item in translations:
        if item.get("verse_id") == target["id"]:
            print({
                "language": item.get("lang"),
                "author": item.get("authorName"),
                "text": str(item.get("description", ""))[:200],
            })

print("\n========== AUDIT COMPLETE ==========")
