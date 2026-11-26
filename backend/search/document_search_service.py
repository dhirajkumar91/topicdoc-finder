from collections import defaultdict
from pathlib import Path

from search.semantic_search_service import search_document_content


def get_fallback_title(paper):
    """Return the paper title or a readable filename fallback."""

    title = paper.get("title")

    if title and title.strip():
        return title.strip()

    filename = paper.get("original_filename")

    if filename:
        filename = Path(filename).stem
        filename = filename.replace("_", " ").replace("-", " ")
        return filename.strip()

    return "Untitled research paper"


def normalize_source_name(source_name):
    """Convert source labels into user-friendly names."""

    if not source_name:
        return "Unknown source"

    source_name = source_name.strip().lower()

    source_labels = {
        "local": "Local PDF",
        "arxiv": "arXiv",
        "crossref": "Crossref",
        "pubmed": "PubMed",
        "core": "CORE",
        "openalex": "OpenAlex",
        "semantic_scholar": "Semantic Scholar",
    }

    return source_labels.get(
        source_name,
        source_name.replace("_", " ").title(),
    )


def search_research_papers(
    query,
    limit=10,
    chunk_pool_size=50,
    passages_per_document=2,
    table_pool_size=50,
    tables_per_document=2,
):
    """
    Search document passages and tables independently.

    Returns:
        {
            "results": [...],
            "relevant_tables": [...]
        }

    Document results are ranked by their best matching text chunk.
    Table results are ranked independently by table similarity.
    """

    if not query or not query.strip():
        raise ValueError("Search query cannot be empty.")

    if limit <= 0:
        raise ValueError("Document limit must be greater than 0.")

    if chunk_pool_size <= 0:
        raise ValueError("Chunk pool size must be greater than 0.")

    if passages_per_document <= 0:
        raise ValueError(
            "Passages per document must be greater than 0."
        )

    if table_pool_size <= 0:
        raise ValueError("Table pool size must be greater than 0.")

    if tables_per_document <= 0:
        raise ValueError(
            "Tables per document must be greater than 0."
        )

    # Retrieve chunks and tables independently using one query embedding.
    search_results = search_document_content(
        query=query.strip(),
        chunk_limit=chunk_pool_size,
        table_limit=table_pool_size,
    )

    chunk_results = search_results.get("chunks", [])
    table_results = search_results.get("tables", [])

    # Group text chunks by document.
    grouped_documents = defaultdict(list)

    for chunk in chunk_results:
        grouped_documents[chunk["document_id"]].append(chunk)

    # Group tables by document for backward-compatible nested results.
    grouped_tables = defaultdict(list)

    for table in table_results:
        grouped_tables[table["document_id"]].append(table)

    document_results = []

    for document_id, chunks in grouped_documents.items():

        chunks.sort(
            key=lambda chunk: chunk["similarity_score"],
            reverse=True,
        )

        best_chunk = chunks[0]

        document_tables = grouped_tables.get(document_id, [])

        document_tables.sort(
            key=lambda table: table["similarity_score"],
            reverse=True,
        )

        document_result = {
            "document_id": str(document_id),
            "title": get_fallback_title(best_chunk),
            "abstract": best_chunk.get("abstract"),
            "authors": best_chunk.get("authors") or [],
            "published_date": best_chunk.get("published_date"),
            "source_name": normalize_source_name(
                best_chunk.get("source_name")
            ),
            "source_url": best_chunk.get("source_url"),
            "pdf_url": best_chunk.get("pdf_url"),
            "file_path": best_chunk.get("file_path"),
            "similarity_score": best_chunk["similarity_score"],
            "retrieved_chunk_count": len(chunks),
            "relevant_passages": chunks[:passages_per_document],

            # Retain nested tables for compatibility with existing consumers.
            "relevant_tables": document_tables[:tables_per_document],
        }

        document_results.append(document_result)

    # Preserve existing document ranking behavior.
    document_results.sort(
        key=lambda document: document["similarity_score"],
        reverse=True,
    )

    # Rank tables independently of document text results.
    relevant_tables = sorted(
        table_results,
        key=lambda table: table["similarity_score"],
        reverse=True,
    )

    return {
        "results": document_results[:limit],
        "relevant_tables": relevant_tables,
    }