from sqlalchemy import select

from database.models import (
     Document,
     DocumentChunk,
     DocumentTable,
)
from database.session import SessionLocal


EMBEDDING_DIMENSION = 768

def semantic_search(
    query_embedding,
    limit=10,
):
    """
    Retrieve the most semantically relevant document chunks.

    Args:
        query_embedding: 768-dimensional query embedding.
        limit: Maximum number of chunks to retrieve.

    Returns:
        List of dictionaries containing relevant chunks
        and document metadata.
    """

    # Validate the query embedding.
    if not isinstance(query_embedding, (list, tuple)):
        raise TypeError(
            "Query embedding must be a list or tuple."
        )

    if len(query_embedding) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Query embedding must contain "
            f"{EMBEDDING_DIMENSION} dimensions."
        )

    if limit <= 0:
        raise ValueError(
            "Search limit must be greater than 0."
        )

    # Calculate cosine distance between query and stored embeddings.
    distance = DocumentChunk.embedding.cosine_distance(
        list(query_embedding)
    ).label("distance")

    statement = (
        select(
            DocumentChunk.id.label("chunk_id"),
            DocumentChunk.document_id,
            DocumentChunk.chunk_index,
            DocumentChunk.section_chunk_index,
            DocumentChunk.section_title,
            DocumentChunk.parent_section_title,
            DocumentChunk.page_start,
            DocumentChunk.page_end,
            DocumentChunk.content,
            DocumentChunk.character_count,
            Document.title,
            Document.abstract,
            Document.authors,
            Document.published_date,
            Document.source_name,
            Document.source_url,
            Document.pdf_url,
            Document.file_path,
            Document.original_filename,
            distance,
        )
        .join(
            Document,
            Document.id == DocumentChunk.document_id,
        )
        .where(
            Document.processing_status == "completed"
        )
        .order_by(distance.asc())
        .limit(limit)
    )

    with SessionLocal() as session:

        results = session.execute(statement).all()

    # Convert database results into dictionaries.
    search_results = []

    for result in results:

        result_data = result._mapping

        cosine_distance = float(result_data["distance"])

        search_results.append(
            {
                "chunk_id": result_data["chunk_id"],
                "document_id": result_data["document_id"],
                "chunk_index": result_data["chunk_index"],
                "section_chunk_index": result_data[
                    "section_chunk_index"
                ],
                "section_title": result_data["section_title"],
                "parent_section_title": result_data[
                    "parent_section_title"
                ],
                "page_start": result_data["page_start"],
                "page_end": result_data["page_end"],
                "content": result_data["content"],
                "character_count": result_data[
                    "character_count"
                ],

                # Document metadata
                "title": result_data["title"],
                "abstract": result_data["abstract"],
                "authors": result_data["authors"],
                "published_date": result_data[
                    "published_date"
                ],
                "source_name": result_data["source_name"],
                "source_url": result_data["source_url"],
                "pdf_url": result_data["pdf_url"],
                "file_path": result_data["file_path"],
                "original_filename": result_data["original_filename"],

                # Relevance information
                "cosine_distance": cosine_distance,
                "similarity_score": 1.0 - cosine_distance,
            }
        )

    return search_results



def semantic_table_search(query_embedding, limit=10):
    """
    Retrieve semantically relevant tables from completed documents.
    """

    if not isinstance(query_embedding, (list, tuple)):
        raise TypeError(
            "Query embedding must be a list or tuple."
        )

    if len(query_embedding) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Query embedding must contain "
            f"{EMBEDDING_DIMENSION} dimensions."
        )

    if limit <= 0:
        raise ValueError(
            "Search limit must be greater than 0."
        )

    distance = DocumentTable.embedding.cosine_distance(
        list(query_embedding)
    ).label("distance")

    statement = (
        select(
            DocumentTable.id.label("table_id"),
            DocumentTable.document_id,
            DocumentTable.table_index,
            DocumentTable.table_number,
            DocumentTable.table_title,
            DocumentTable.section_title,
            DocumentTable.parent_section_title,
            DocumentTable.page_start,
            DocumentTable.page_end,
            DocumentTable.column_headers,
            DocumentTable.table_data,
            DocumentTable.raw_table_data,
            DocumentTable.table_text,
            DocumentTable.footnotes,
            Document.title,
            Document.abstract,
            Document.authors,
            Document.published_date,
            Document.source_name,
            Document.source_url,
            Document.pdf_url,
            Document.file_path,
            Document.original_filename,
            distance,
        )
        .join(
            Document,
            Document.id == DocumentTable.document_id,
        )
        .where(
            Document.processing_status == "completed"
        )
        .order_by(distance.asc())
        .limit(limit)
    )

    with SessionLocal() as session:
        results = session.execute(statement).all()

    search_results = []

    for result in results:
        result_data = result._mapping
        cosine_distance = float(result_data["distance"])

        search_results.append({
            "table_id": result_data["table_id"],
            "document_id": result_data["document_id"],
            "table_index": result_data["table_index"],
            "table_number": result_data["table_number"],
            "table_title": result_data["table_title"],
            "section_title": result_data["section_title"],
            "parent_section_title": result_data[
                "parent_section_title"
            ],
            "page_start": result_data["page_start"],
            "page_end": result_data["page_end"],
            "column_headers": result_data["column_headers"],
            "table_data": result_data["table_data"],
            "raw_table_data": result_data["raw_table_data"],
            "table_text": result_data["table_text"],
            "footnotes": result_data["footnotes"],

            # Document metadata
            "title": result_data["title"],
            "abstract": result_data["abstract"],
            "authors": result_data["authors"],
            "published_date": result_data["published_date"],
            "source_name": result_data["source_name"],
            "source_url": result_data["source_url"],
            "pdf_url": result_data["pdf_url"],
            "file_path": result_data["file_path"],
            "original_filename": result_data["original_filename"],

            # Relevance information
            "cosine_distance": cosine_distance,
            "similarity_score": 1.0 - cosine_distance,
        })

    return search_results
