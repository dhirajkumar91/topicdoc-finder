
import requests

from metadata.metadata_normalizer import normalize_metadata
from metadata.sources.base import BaseSourceAdapter

SEMANTIC_SCHOLAR_API_URL = (
    "https://api.semanticscholar.org/graph/v1/paper/search"
)


def search_semantic_scholar(topic, max_results=10):
    if not topic or not topic.strip():
        raise ValueError("Search topic cannot be empty.")

    if max_results < 1:
        raise ValueError("max_results must be at least 1.")

    fields = (
        "title,abstract,authors,year,externalIds,url,"
        "openAccessPdf,publicationDate"
    )

    params = {
        "query": topic.strip(),
        "limit": min(max_results, 100),
        "fields": fields,
    }

    try:
        response = requests.get(
            SEMANTIC_SCHOLAR_API_URL,
            params=params,
            timeout=30,
        )
        response.raise_for_status()

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Semantic Scholar search failed: {exc}"
        ) from exc

    data = response.json()

    papers = []

    for paper in data.get("data", []):
        authors = []

        for author in paper.get("authors") or []:
            author_name = author.get("name")

            if author_name:
                authors.append(author_name)

        external_ids = paper.get("externalIds") or {}
        doi = external_ids.get("DOI")

        paper_id = paper.get("paperId")
        source_url = paper.get("url")

        if not source_url and paper_id:
            source_url = (
                f"https://www.semanticscholar.org/paper/{paper_id}"
            )

        open_access_pdf = paper.get("openAccessPdf") or {}
        pdf_url = open_access_pdf.get("url")

        published_date = paper.get("publicationDate")

        if not published_date and paper.get("year"):
            published_date = f"{paper['year']}-01-01"

        metadata = {
            "title": paper.get("title"),
            "abstract": paper.get("abstract"),
            "authors": authors,
            "published_date": published_date,
            "source_name": "semantic_scholar",
            "external_id": paper_id,
            "doi": doi,
            "source_url": source_url,
            "pdf_url": pdf_url,
            "matched_keywords": [topic.strip()],
        }

        papers.append(normalize_metadata(metadata))

    return papers


class SemanticScholarAdapter(BaseSourceAdapter):

    source_name = "semantic_scholar"

    def search(self, topic: str, max_results: int = 10) -> list[dict]:
        return search_semantic_scholar(topic, max_results)