
import uuid

from sqlalchemy import delete, select

from database.models import Document, DocumentTable
from database.session import SessionLocal


EMBEDDING_DIMENSION = 768


def save_document_tables(document_id, tables):
    """
    Replace all stored tables for a document with newly generated tables.

    Deletion and insertion happen in one transaction.
    If insertion fails, previously stored tables remain unchanged.

    An empty tables list is allowed. This clears previously stored
    tables when a document is reprocessed and no tables are extracted.

    Returns the number of tables saved.
    """

    document_id = uuid.UUID(str(document_id))

    table_records = []
    seen_indexes = set()

    for table in tables:

        table_index = table.get("table_index")

        if not isinstance(table_index, int) or isinstance(table_index, bool):
            raise ValueError("Table index must be an integer.")

        if table_index <= 0:
            raise ValueError("Table index must be greater than zero.")

        if table_index in seen_indexes:
            raise ValueError(
                f"Duplicate table index: {table_index}."
            )

        seen_indexes.add(table_index)

        table_data = table.get("table_data")

        if not isinstance(table_data, list) or not table_data:
            raise ValueError(
                f"Table {table_index} must contain structured row data."
            )

        table_text = table.get("table_text")

        if not isinstance(table_text, str) or not table_text.strip():
            raise ValueError(
                f"Table {table_index} has empty searchable text."
            )

        embedding = table.get("embedding")

        if not isinstance(embedding, (list, tuple)):
            raise ValueError(
                f"Invalid embedding for table {table_index}."
            )

        if len(embedding) != EMBEDDING_DIMENSION:
            raise ValueError(
                f"Table {table_index} must have "
                f"{EMBEDDING_DIMENSION} embedding values."
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

        table_records.append(
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
                table_data=table_data,
                table_text=table_text,
                footnotes=table.get("footnotes"),
                page_fragments=table.get("page_fragments"),
                coordinates=table.get("coordinates"),
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
            delete(DocumentTable).where(
                DocumentTable.document_id == document_id
            )
        )

        session.add_all(table_records)

    return len(table_records)
