from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_key: Mapped[str] = mapped_column(
        String(120), unique=True, index=True
    )
    title: Mapped[str] = mapped_column(String(300))
    creator: Mapped[str | None] = mapped_column(String(255))
    language_code: Mapped[str | None] = mapped_column(String(16))
    source_url: Mapped[str | None] = mapped_column(Text)
    license_name: Mapped[str | None] = mapped_column(String(255))
    license_url: Mapped[str | None] = mapped_column(Text)
    edition: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    verses: Mapped[list["Verse"]] = relationship(back_populates="source")
    translations: Mapped[list["Translation"]] = relationship(
        back_populates="source"
    )
    commentaries: Mapped[list["Commentary"]] = relationship(
        back_populates="source"
    )
