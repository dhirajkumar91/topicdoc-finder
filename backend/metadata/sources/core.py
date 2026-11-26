
import os
import requests

from metadata.metadata_normalizer import normalize_metadata
from metadata.sources.base import BaseSourceAdapter


CORE_API_URL = "https://api.core.ac.uk/v3/search/works"


def search_core(topic, max_results=10):
    if not topic or not topic.strip():
        raise ValueError("Search topic cannot be empty.")

    if max_results < 1:
        raise ValueError("max_results must be at least 1.")

    api_key = os.getenv("CORE_API_KEY")

    if not api_key:
        raise RuntimeError(
            "CORE_API_KEY environment variable is not configured."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    params = {
        "q": topic.strip(),
        "limit": min(max_results, 100),
    }

    try:
        response = requests.get(
            CORE_API_URL,
            headers=headers,
            params=params,
            timeout=30,
        )
        response.raise_for_status()

    except requests.RequestException as exc:
        raise RuntimeError(
            f"CORE search failed: {exc}"
        ) from exc

    data = response.json()

    papers = []

    for work in data.get("results", []):
        title = work.get("title")
        abstract = work.get("abstract")

        authors = []

        for author in work.get("authors") or []:
            if isinstance(author, dict):
                author_name = author.get("name")
            else:
                author_name = author

            if author_name:
                authors.append(author_name)

        published_date = work.get("publishedDate")

        doi = work.get("doi")

        core_id = work.get("id")

        source_url = (
            f"https://core.ac.uk/works/{core_id}"
            if core_id
            else work.get("sourceUrl")
        )

        pdf_url = work.get("downloadUrl")

        if not pdf_url:
            full_text_urls = work.get("fullTextUrls") or []

            for url in full_text_urls:
                if url:
                    pdf_url = url
                    break

        metadata = {
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "published_date": published_date,
            "source_name": "core",
            "external_id": str(core_id) if core_id is not None else None,
            "doi": doi,
            "source_url": source_url,
            "pdf_url": pdf_url,
            "matched_keywords": [topic.strip()],
        }

        papers.append(
            normalize_metadata(metadata)
        )

    return papers


class CoreAdapter(BaseSourceAdapter):

    source_name = "core"

    def search(self, topic: str, max_results: int = 10) -> list[dict]:
        return search_core(topic, max_results)