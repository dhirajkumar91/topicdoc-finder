
from embeddings.embedding_service import generate_query_embedding

from database.search_repository import (
    semantic_search,
    semantic_table_search,
)


def search_documents(query, limit=10):
    """
    Perform semantic search for text chunks.
    """

    if not query or not query.strip():
        raise ValueError("Search query cannot be empty.")

    query_embedding = generate_query_embedding(query)

    results = semantic_search(
        query_embedding=query_embedding,
        limit=limit,
    )

    return results


def search_document_content(
    query,
    chunk_limit=50,
    table_limit=50,
):
    """
    Perform semantic search across text chunks and tables.

    A single query embedding is reused for both searches.

    Returns:
        {
            "chunks": [...],
            "tables": [...]
        }
    """

    if not query or not query.strip():
        raise ValueError("Search query cannot be empty.")

    if chunk_limit <= 0:
        raise ValueError("Chunk limit must be greater than 0.")

    if table_limit <= 0:
        raise ValueError("Table limit must be greater than 0.")

    # Generate only one query embedding.
    query_embedding = generate_query_embedding(query)

    # Retrieve relevant text chunks.
    chunk_results = semantic_search(
        query_embedding=query_embedding,
        limit=chunk_limit,
    )

    # Retrieve relevant tables using the same embedding.
    table_results = semantic_table_search(
        query_embedding=query_embedding,
        limit=table_limit,
    )

    return {
        "chunks": chunk_results,
        "tables": table_results,
    }
