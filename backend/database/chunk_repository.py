import uuid

from sqlalchemy import delete, select

from database.models import Document, DocumentChunk
from database.session import SessionLocal


EMBEDDING_DIMENSION = 768


def save_document_chunks(document_id, chunks):
    """
    Replace all chunks for a document with newly generated chunks.

    The deletion and insertion happen in one transaction.
    If insertion fails, the previous chunks remain unchanged.

    Returns the number of chunks saved.
    """

    if not chunks:
        raise ValueError("Chunks list cannot be empty.")

    document_id = uuid.UUID(str(document_id))

    chunk_records = []

    for chunk in chunks:

        embedding = chunk.get("embedding")

        if not isinstance(embedding, (list, tuple)):
            raise ValueError(
                f"Invalid embedding for chunk {chunk.get('chunk_index')}."
            )

        if len(embedding) != EMBEDDING_DIMENSION:
            raise ValueError(
                f"Chunk {chunk.get('chunk_index')} must have "
                f"{EMBEDDING_DIMENSION} embedding values."
            )

        content = chunk.get("content")

        if not content or not content.strip():
            raise ValueError(
                f"Chunk {chunk.get('chunk_index')} has empty content."
            )

        if len(content) != chunk.get("character_count"):
            raise ValueError(
                f"Character count mismatch for chunk "
                f"{chunk.get('chunk_index')}."
            )

        chunk_records.append(
            DocumentChunk(
                document_id=document_id,
                chunk_index=chunk["chunk_index"],
                section_chunk_index=chunk["section_chunk_index"],
                section_title=chunk["section_title"],
                parent_section_title=chunk.get("parent_section_title"),
                page_start=chunk["page_start"],
                page_end=chunk["page_end"],
                content=content,
                character_count=chunk["character_count"],
                embedding=list(embedding),
            )
        )

    with SessionLocal.begin() as session:

        document = session.scalar(
            select(Document).where(Document.id == document_id)
        )

        if document is None:
            raise ValueError(
                f"Document not found in database: {document_id}"
            )

        session.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document_id
            )
        )

        session.add_all(chunk_records)

    return len(chunk_records)