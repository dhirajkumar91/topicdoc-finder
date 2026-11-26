import requests

from bs4 import BeautifulSoup

from metadata.metadata_normalizer import normalize_metadata
from metadata.sources.base import BaseSourceAdapter


CROSSREF_API_URL = "https://api.crossref.org/works"


def extract_publication_date(work):
    """
    Extract the best available publication date from Crossref metadata.
    """

    date_fields = [
        "published",
        "published-print",
        "published-online",
        "issued",
    ]

    for field in date_fields:
        date_info = work.get(field, {})
        date_parts = date_info.get("date-parts", [])

        if date_parts:
            parts = date_parts[0]

            try:
                year = parts[0]
                month = parts[1] if len(parts) > 1 else 1
                day = parts[2] if len(parts) > 2 else 1

                return f"{year:04d}-{month:02d}-{day:02d}"

            except (ValueError, TypeError, IndexError):
                continue

    return None


def extract_abstract(work):
    """
    Extract and clean abstract text from Crossref metadata.
    """

    abstract = work.get("abstract")

    if not abstract:
        return None

    soup = BeautifulSoup(abstract, "html.parser")

    return " ".join(soup.get_text(" ", strip=True).split())


def extract_authors(work):
    """
    Extract author names from Crossref metadata.
    """

    authors = []

    for author in work.get("author", []):

        given_name = author.get("given", "")
        family_name = author.get("family", "")

        name = f"{given_name} {family_name}".strip()

        if name:
            authors.append(name)

    return authors


def extract_pdf_url(work):
    """
    Extract a PDF URL if Crossref provides one.

    Checks content-type, intended application content,
    and URL hints where possible.
    """

    for link in work.get("link", []):

        url = link.get("URL")
        content_type = link.get("content-type", "").lower()
        intended_application = link.get("intended-application", "").lower()

        if not url:
            continue

        # Explicit PDF content type
        if "pdf" in content_type:
            return url

        # Intended for text mining or similar PDF delivery
        if "pdf" in intended_application:
            return url

        # URL itself suggests PDF
        if ".pdf" in url.lower():
            return url

    return None


def search_crossref(topic, max_results=10):
    """
    Search Crossref for research publications matching a topic.

    Returns:
        A list of normalized metadata dictionaries.
    """

    if not topic or not topic.strip():
        raise ValueError("Search topic cannot be empty.")

    if max_results < 1:
        raise ValueError("max_results must be at least 1.")

    params = {
        "query": topic.strip(),
        "rows": min(max_results, 1000),
    }

    headers = {
        "User-Agent": (
            "TopicDocFinder/1.0 "
            "(academic research discovery application)"
        ),
    }

    try:
        response = requests.get(
            CROSSREF_API_URL,
            params=params,
            headers=headers,
            timeout=30,
        )

        response.raise_for_status()

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Crossref search failed: {exc}"
        ) from exc

    data = response.json()

    items = data.get("message", {}).get("items", [])

    papers = []

    for work in items:

        doi = work.get("DOI")

        # Crossref DOI URL
        source_url = (
            f"https://doi.org/{doi}"
            if doi
            else work.get("URL")
        )

        metadata = {
            "title": (
                work.get("title", [None])[0]
                if work.get("title")
                else None
            ),
            "abstract": extract_abstract(work),
            "authors": extract_authors(work),
            "published_date": extract_publication_date(work),
            "source_name": "crossref",
            "external_id": doi,
            "doi": doi,
            "source_url": source_url,
            "pdf_url": extract_pdf_url(work),
            "matched_keywords": [topic.strip()],
        }

        papers.append(
            normalize_metadata(metadata)
        )

    return papers


class CrossrefAdapter(BaseSourceAdapter):

    source_name = "crossref"

    def search(self, topic: str, max_results: int = 10) -> list[dict]:
        return search_crossref(topic, max_results)