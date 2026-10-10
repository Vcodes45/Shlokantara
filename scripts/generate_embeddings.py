import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select

from app.db.models import KnowledgeChunk
from app.db.session import SessionLocal
from app.rag.embedding_service import embed_texts

DB_BATCH_SIZE = 128
EXPECTED_DIMENSIONS = 1024


def main():
    total = 0

    while True:
        with SessionLocal() as db:
            try:
                chunks = db.scalars(
                    select(KnowledgeChunk)
                    .where(KnowledgeChunk.embedding.is_(None))
                    .order_by(KnowledgeChunk.id)
                    .limit(DB_BATCH_SIZE)
                ).all()

                if not chunks:
                    break

                vectors = embed_texts(
                    [chunk.content for chunk in chunks]
                )

                if len(vectors) != len(chunks):
                    raise RuntimeError(
                        "Embedding count does not match chunk count."
                    )

                for chunk, vector in zip(
                    chunks, vectors, strict=True
                ):
                    if len(vector) != EXPECTED_DIMENSIONS:
                        raise ValueError(
                            f"Unexpected vector dimension: {len(vector)}"
                        )

                    chunk.embedding = vector

                db.commit()
                total += len(chunks)

                print(
                    f"Embedded {total} chunks in this run."
                )

            except Exception:
                db.rollback()
                raise

    print(f"Embedding generation completed. New embeddings: {total}")


if __name__ == "__main__":
    main()
