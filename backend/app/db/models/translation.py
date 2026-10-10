from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Translation(Base):
    __tablename__ = "translations"
    __table_args__ = (
        UniqueConstraint(
            "verse_id",
            "language_code",
            "source_id",
            name="uq_translation_verse_language_source",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    verse_id: Mapped[str] = mapped_column(
        ForeignKey("verses.verse_id", ondelete="CASCADE"), index=True
    )
    language_code: Mapped[str] = mapped_column(String(16), index=True)
    text: Mapped[str] = mapped_column(Text)
    translator: Mapped[str | None] = mapped_column(String(255))
    edition: Mapped[str | None] = mapped_column(String(255))
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    verse: Mapped["Verse"] = relationship(back_populates="translations")
    source: Mapped["Source"] = relationship(back_populates="translations")
