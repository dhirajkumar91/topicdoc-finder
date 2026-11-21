"""add document processing status tracking

Revision ID: a621f9a644bf
Revises: 0de52fd5c4c6
Create Date: 2026-11-21 14:20:46.571279

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a621f9a644bf'
down_revision: Union[str, Sequence[str], None] = '0de52fd5c4c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "documents",
        sa.Column(
            "processing_status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
    )

    op.add_column(
        "documents",
        sa.Column(
            "chunk_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )

    op.add_column(
        "documents",
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "documents",
        sa.Column(
            "processing_error",
            sa.Text(),
            nullable=True,
        ),
    )

    # Add processing status constraints
    op.create_check_constraint(
        "ck_documents_processing_status",
        "documents",
        "processing_status IN ('pending', 'processing', 'completed', 'failed')",
    )

    op.create_check_constraint(
        "ck_documents_chunk_count",
        "documents",
        "chunk_count >= 0",
    )

    # Backfill existing documents that already have stored chunks
    op.execute("""
        UPDATE documents
        SET
            chunk_count = (
                SELECT COUNT(*)
                FROM document_chunks
                WHERE document_chunks.document_id = documents.id
            ),
            processing_status = 'completed',
            processed_at = NOW()
        WHERE EXISTS (
            SELECT 1
            FROM document_chunks
            WHERE document_chunks.document_id = documents.id
        )
    """)


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_constraint(
        "ck_documents_chunk_count",
        "documents",
        type_="check",
    )

    op.drop_constraint(
        "ck_documents_processing_status",
        "documents",
        type_="check",
    )

    op.drop_column("documents", "processing_error")
    op.drop_column("documents", "processed_at")
    op.drop_column("documents", "chunk_count")
    op.drop_column("documents", "processing_status")