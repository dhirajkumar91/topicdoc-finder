import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pgvector.sqlalchemy import Vector

from database.base import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_document_chunks_document_chunk",
        ),
        CheckConstraint(
            "chunk_index > 0",
            name="ck_document_chunks_chunk_index",
        ),
        CheckConstraint(
            "section_chunk_index > 0",
            name="ck_document_chunks_section_chunk_index",
        ),
        CheckConstraint(
            "page_start > 0 AND page_end >= page_start",
            name="ck_document_chunks_page_range",
        ),
        CheckConstraint(
            "character_count > 0",
            name="ck_document_chunks_character_count",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    section_chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    section_title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    parent_section_title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    page_start: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    page_end: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    character_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    embedding: Mapped[list[float]] = mapped_column(
        Vector(768),
        nullable=False,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )