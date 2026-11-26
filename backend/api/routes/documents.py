from fastapi import APIRouter, Query

from database.document_repository import get_all_documents

router = APIRouter()


@router.get("/")
def list_documents(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    documents = get_all_documents(
        limit=limit,
        offset=offset,
    )

    return {
        "total_returned": len(documents),
        "limit": limit,
        "offset": offset,
        "documents": documents,
    }