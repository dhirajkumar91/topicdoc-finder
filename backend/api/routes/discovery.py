from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException

from api.schemas.discovery import (
    DiscoveryRequest,
    DiscoveryResponse,
)
from search.search_orchestrator import SearchOrchestrator


router = APIRouter()
orchestrator = SearchOrchestrator()


def serialize_value(value):
    """Convert dates and UUIDs into JSON-friendly values."""

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    return value


def serialize_paper(paper):
    """Prepare a paper's metadata for the API response."""

    serialized = {}

    for key, value in paper.items():

        if key == "authors":
            serialized[key] = value or []

        elif key == "sources":
            serialized[key] = value or []

        else:
            serialized[key] = serialize_value(value)

    return serialized


@router.post("/", response_model=DiscoveryResponse)
def discovery_endpoint(request: DiscoveryRequest):

    try:
        response = orchestrator.search(
            topic=request.query.strip(),
            max_results=request.max_results_per_source,
        )

        papers = [
            serialize_paper(paper)
            for paper in response["papers"]
        ]

        return {
            "query": request.query.strip(),
            "total_results": len(papers),
            "results": papers,
            "source_errors": response["errors"],
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="An error occurred while discovering research papers.",
        ) from exc