
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
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from pgvector.sqlalchemy import Vector

from database.base import Base


class DocumentTable(Base):
    __tablename__ = "document_tables"

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "table_index",
            name="uq_document_tables_document_index",
        ),
        CheckConstraint(
            "table_index > 0",
            name="ck_document_tables_table_index",
        ),
        CheckConstraint(
            "page_start > 0 AND page_end >= page_start",
            name="ck_document_tables_page_range",
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

    # Unique sequence of the table within the document.
    table_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Table number detected during PDF extraction.
    table_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    table_title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    section_title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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

    # Column headers retained as structured JSON.
    column_headers: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    raw_table_data: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Original table rows and cells.
    table_data: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
    )

    # Text representation used for search and embeddings.
    table_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Table notes, units and footnotes.
    footnotes: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Page-level fragments, including bounding boxes.
    # Useful for multi-page tables and source traceability.
    page_fragments: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Overall extraction coordinates, when available.
    coordinates: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Gemini embedding with 768 dimensions.
    embedding: Mapped[list[float]] = mapped_column(
        Vector(768),
        nullable=False,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
