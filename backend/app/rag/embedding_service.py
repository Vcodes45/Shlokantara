from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-m3"
EMBEDDING_DIMENSIONS = 1024


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    model = get_model()

    vectors = model.encode(
        texts,
        batch_size=4,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    vectors = embed_texts([text])
    return vectors[0]
