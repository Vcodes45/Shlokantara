from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Commentary(Base):
    __tablename__ = "commentaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    verse_id: Mapped[str] = mapped_column(
        ForeignKey("verses.verse_id", ondelete="CASCADE"), index=True
    )
    language_code: Mapped[str] = mapped_column(String(16), index=True)
    commentator: Mapped[str | None] = mapped_column(String(255))
    tradition: Mapped[str | None] = mapped_column(String(255))
    section_reference: Mapped[str | None] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    verse: Mapped["Verse"] = relationship(back_populates="commentaries")
    source: Mapped["Source"] = relationship(back_populates="commentaries")
