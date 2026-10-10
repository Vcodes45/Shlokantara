from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    chunk_key: Mapped[str] = mapped_column(
        String(160), unique=True, index=True
    )
    content_hash: Mapped[str] = mapped_column(String(64))
    verse_id: Mapped[str] = mapped_column(
        ForeignKey("verses.verse_id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), index=True
    )
    content_type: Mapped[str] = mapped_column(String(30), index=True)
    language_code: Mapped[str] = mapped_column(String(16), index=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1024), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
