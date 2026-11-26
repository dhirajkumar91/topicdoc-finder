from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException

from api.schemas.search import SearchRequest, SearchResponse
from search.document_search_service import search_research_papers


router = APIRouter()


def serialize_value(value):
    """Convert UUIDs and dates into JSON-friendly values."""

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            key: serialize_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            serialize_value(item)
            for item in value
        ]

    return value


def serialize_paper(paper):
    """Serialize a paper, its passages and nested tables."""

    serialized = {}

    for key, value in paper.items():

        if key == "authors":
            serialized[key] = serialize_value(value or [])

        elif key in ("relevant_passages", "relevant_tables"):
            serialized[key] = [
                serialize_value(item)
                for item in (value or [])
            ]

        else:
            serialized[key] = serialize_value(value)

    return serialized


def serialize_table(table):
    """Serialize an independently retrieved table."""

    return serialize_value(table)


@router.post("/", response_model=SearchResponse)
def search_endpoint(request: SearchRequest):

    try:
        search_data = search_research_papers(
            query=request.query,
            limit=request.limit,
            chunk_pool_size=max(request.limit * 5, 50),
            passages_per_document=2,
            table_pool_size=max(request.limit * 5, 50),
            tables_per_document=2,
        )

        document_results = search_data["results"]
        table_results = search_data["relevant_tables"]

        serialized_results = [
            serialize_paper(paper)
            for paper in document_results
        ]

        serialized_tables = [
            serialize_table(table)
            for table in table_results
        ]

        return {
            "query": request.query.strip(),
            "total_results": len(serialized_results),
            "results": serialized_results,
            "total_tables": len(serialized_tables),
            "relevant_tables": serialized_tables,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="An error occurred while searching research papers.",
        ) from exc