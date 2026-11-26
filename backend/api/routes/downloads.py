
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from download_service import download_and_register_paper
from database.document_repository import save_document_metadata


router = APIRouter()

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


class DownloadRequest(BaseModel):
    papers: list[dict[str, Any]]


def normalize_source(paper: dict[str, Any]) -> str:
    """
    Extract a meaningful research source name from paper metadata.
    """

    source_name = paper.get("source_name")

    if source_name and str(source_name).strip():
        return str(source_name).strip()

    sources = paper.get("sources")

    if isinstance(sources, list) and sources:
        first_source = sources[0]

        if first_source and str(first_source).strip():
            return str(first_source).strip()

    source = paper.get("source")

    if source and str(source).strip():
        return str(source).strip()

    # Try deriving the source from the source URL.
    source_url = paper.get("source_url")

    if source_url:
        hostname = urlparse(source_url).hostname

        if hostname:
            hostname = hostname.lower()

            if hostname.startswith("www."):
                hostname = hostname[4:]

            return hostname

    # Try deriving the source from the PDF URL.
    pdf_url = paper.get("pdf_url")

    if pdf_url:
        hostname = urlparse(pdf_url).hostname

        if hostname:
            hostname = hostname.lower()

            if hostname.startswith("www."):
                hostname = hostname[4:]

            return hostname

    return "manual-upload"


@router.post("/")
def download_selected_papers(request: DownloadRequest):

    results = []

    for paper in request.papers:
        result = download_and_register_paper(paper)
        results.append(result)

    downloaded = sum(
        1 for result in results
        if result["status"] == "saved"
    )

    duplicates = sum(
        1 for result in results
        if result["status"] == "duplicate"
    )

    failed = sum(
        1 for result in results
        if result["status"] == "failed"
    )

    return {
        "total_requested": len(request.papers),
        "downloaded": downloaded,
        "duplicates": duplicates,
        "failed": failed,
        "results": results,
    }


@router.post("/manual")
async def manual_pdf_upload(
    file: UploadFile = File(...),
    metadata: str = Form(...),
):
    """
    Upload a manually downloaded PDF and register it
    against the supplied research-paper metadata.
    """

    try:
        paper = json.loads(metadata)

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid paper metadata JSON.",
        )

    if not isinstance(paper, dict):
        raise HTTPException(
            status_code=400,
            detail="Paper metadata must be a JSON object.",
        )

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted.",
        )

    # Create a safe filename.
    title = paper.get("title") or "research_paper"

    title = re.sub(
        r'[<>:"/\\|?*]',
        "",
        title,
    )

    title = re.sub(
        r"\s+",
        "_",
        title.strip(),
    )

    title = title[:100]

    external_id = paper.get("external_id") or paper.get("doi") or ""

    external_id = re.sub(
        r'[<>:"/\\|?*]',
        "",
        str(external_id),
    )

    external_id = re.sub(
        r"\s+",
        "_",
        external_id,
    )

    external_id = external_id[-40:]

    if external_id:
        filename = f"{title}_{external_id}.pdf"
    else:
        filename = f"{title}.pdf"

    file_path = DOWNLOAD_DIR / filename
    temporary_path = file_path.with_suffix(".part")

    try:

        # Save the upload temporarily.
        with open(temporary_path, "wb") as output_file:

            while True:

                chunk = await file.read(8192)

                if not chunk:
                    break

                output_file.write(chunk)

        # Validate PDF signature.
        with open(temporary_path, "rb") as uploaded_file:
            file_signature = uploaded_file.read(5)

        if file_signature != b"%PDF-":

            temporary_path.unlink(missing_ok=True)

            raise HTTPException(
                status_code=400,
                detail="Uploaded file is not a valid PDF.",
            )

        # Move to final location.
        temporary_path.replace(file_path)

        # Normalize publication date.
        published_date = paper.get("published_date")

        if isinstance(published_date, str):

            try:
                published_date = date.fromisoformat(
                    published_date[:10]
                )

            except ValueError:
                published_date = None

        # Normalize the original research source.
        source_name = normalize_source(paper)

        # Register in PostgreSQL.
        result = save_document_metadata(
            file_path=file_path,
            pdf_url=paper.get("pdf_url") or "manual-upload",
            source_name=source_name,
            title=paper.get("title"),
            abstract=paper.get("abstract"),
            authors=paper.get("authors"),
            published_date=published_date,
            external_id=paper.get("external_id"),
            source_url=paper.get("source_url"),
            matched_keywords=paper.get("matched_keywords"),
            doi=paper.get("doi"),
        )

        return {
            "status": result["status"],
            "title": paper.get("title"),
            "document_id": result.get("document_id"),
            "filename": file_path.name,
            "source_name": source_name,
            "message": "PDF uploaded and registered successfully.",
        }

    except HTTPException:
        raise

    except Exception as error:

        temporary_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

    finally:
        await file.close()
