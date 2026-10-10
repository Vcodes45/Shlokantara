from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Verse(Base):
    __tablename__ = "verses"
    __table_args__ = (
        UniqueConstraint(
            "chapter_number",
            "verse_number",
            name="uq_verse_chapter_number",
        ),
    )

    verse_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    chapter_number: Mapped[int] = mapped_column(Integer, index=True)
    verse_number: Mapped[int] = mapped_column(Integer)
    sanskrit_text: Mapped[str] = mapped_column(Text)
    transliteration: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    source: Mapped["Source"] = relationship(back_populates="verses")
    translations: Mapped[list["Translation"]] = relationship(
        back_populates="verse", cascade="all, delete-orphan"
    )
    commentaries: Mapped[list["Commentary"]] = relationship(
        back_populates="verse", cascade="all, delete-orphan"
    )
