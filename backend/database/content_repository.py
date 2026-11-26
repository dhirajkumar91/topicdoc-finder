
import uuid

from sqlalchemy import delete, select

from database.models import Document, DocumentChunk, DocumentTable
from database.session import SessionLocal


EMBEDDING_DIMENSION = 768


def _validate_embedding(embedding, record_type, record_index):
    if not isinstance(embedding, (list, tuple)):
        raise ValueError(
            f"Invalid embedding for {record_type} {record_index}."
        )

    if len(embedding) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"{record_type.capitalize()} {record_index} must have "
            f"{EMBEDDING_DIMENSION} embedding values."
        )

    return list(embedding)


def _prepare_chunks(document_id, chunks):
    if not chunks:
        raise ValueError("Chunks list cannot be empty.")

    records = []

    for chunk in chunks:
        chunk_index = chunk.get("chunk_index")

        embedding = _validate_embedding(
            chunk.get("embedding"),
            "chunk",
            chunk_index,
        )

        content = chunk.get("content")

        if not isinstance(content, str) or not content.strip():
            raise ValueError(
                f"Chunk {chunk_index} has empty content."
            )

        character_count = chunk.get("character_count")

        if len(content) != character_count:
            raise ValueError(
                f"Character count mismatch for chunk {chunk_index}."
            )

        records.append(
            DocumentChunk(
                document_id=document_id,
                chunk_index=chunk_index,
                section_chunk_index=chunk["section_chunk_index"],
                section_title=chunk["section_title"],
                parent_section_title=chunk.get("parent_section_title"),
                page_start=chunk["page_start"],
                page_end=chunk["page_end"],
                content=content,
                character_count=character_count,
                embedding=embedding,
            )
        )

    return records


def _prepare_tables(document_id, tables):
    records = []
    seen_indexes = set()

    for table in tables:
        table_index = table.get("table_index")

        if (
            not isinstance(table_index, int)
            or isinstance(table_index, bool)
            or table_index <= 0
        ):
            raise ValueError(
                "Table index must be a positive integer."
            )

        if table_index in seen_indexes:
            raise ValueError(
                f"Duplicate table index: {table_index}."
            )

        seen_indexes.add(table_index)

        # Normalized structured data is preferred.
        # Fall back to table_data for compatibility with the current extractor.
        table_data = table.get("normalized_table_data")

        if table_data is None:
            table_data = table.get("table_data")

        if not isinstance(table_data, list) or not table_data:
            raise ValueError(
                f"Table {table_index} must contain structured row data."
            )

        # Preserve the original extracted data separately.
        raw_table_data = table.get("raw_table_data")

        if raw_table_data is None:
            raw_table_data = table.get("original_data")

        if raw_table_data is None:
            raw_table_data = table.get("data")

        if raw_table_data is None:
            raw_table_data = table_data

        if not isinstance(raw_table_data, list):
            raise ValueError(
                f"Raw table data for table {table_index} must be a list."
            )

        table_text = table.get("table_text")

        if not isinstance(table_text, str) or not table_text.strip():
            raise ValueError(
                f"Table {table_index} has empty searchable text."
            )

        embedding = _validate_embedding(
            table.get("embedding"),
            "table",
            table_index,
        )

        page_start = table.get("page_start")
        page_end = table.get("page_end")

        if (
            not isinstance(page_start, int)
            or isinstance(page_start, bool)
            or not isinstance(page_end, int)
            or isinstance(page_end, bool)
            or page_start <= 0
            or page_end < page_start
        ):
            raise ValueError(
                f"Invalid page range for table {table_index}."
            )

        records.append(
            DocumentTable(
                document_id=document_id,
                table_index=table_index,
                table_number=table.get("table_number"),
                table_title=table.get("table_title"),
                section_title=table.get("section_title"),
                parent_section_title=table.get("parent_section_title"),
                page_start=page_start,
                page_end=page_end,
                column_headers=table.get("column_headers"),
                raw_table_data=raw_table_data,
                table_data=table_data,
                table_text=table_text,
                footnotes=table.get("footnotes"),
                page_fragments=table.get("page_fragments"),
                coordinates=table.get("coordinates"),
                embedding=embedding,
            )
        )

    return records


def save_document_content(document_id, chunks, tables):
    """
    Replace all stored chunks and tables for a document.

    Both replacements happen in one transaction.
    If any database operation fails, previous chunks and tables
    remain unchanged.

    Table data:
        raw_table_data:
            Original extracted rows, preserved separately.

        table_data:
            Normalized structured rows when provided.
            Falls back to table_data for compatibility.

        table_text and embedding:
            Must be generated upstream from the normalized
            table representation.

    Chunks must not be empty.
    Tables may be empty, which clears previously stored tables.

    Returns:
        {
            "chunk_count": int,
            "table_count": int
        }
    """

    document_id = uuid.UUID(str(document_id))

    # Validate and prepare everything before opening the transaction.
    chunk_records = _prepare_chunks(document_id, chunks)
    table_records = _prepare_tables(document_id, tables)

    with SessionLocal.begin() as session:

        document = session.scalar(
            select(Document).where(Document.id == document_id)
        )

        if document is None:
            raise ValueError(
                f"Document not found in database: {document_id}"
            )

        # Delete existing records.
        session.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document_id
            )
        )

        session.execute(
            delete(DocumentTable).where(
                DocumentTable.document_id == document_id
            )
        )

        # Insert replacement records.
        session.add_all(chunk_records)
        session.add_all(table_records)

    return {
        "chunk_count": len(chunk_records),
        "table_count": len(table_records),
    }
