import requests

from metadata.metadata_normalizer import normalize_metadata
from metadata.sources.base import BaseSourceAdapter


OPENALEX_API_URL = "https://api.openalex.org/works"


def reconstruct_abstract(inverted_index):
    """
    Reconstruct an abstract from OpenAlex's inverted-index format.
    """

    if not inverted_index:
        return None

    words = []

    for word, positions in inverted_index.items():
        for position in positions:
            words.append((position, word))

    words.sort(key=lambda item: item[0])

    return " ".join(word for _, word in words)


def search_openalex(topic, max_results=10):
    """
    Search OpenAlex for research papers matching a topic.

    Returns:
        A list of normalized paper metadata dictionaries.
    """

    if not topic or not topic.strip():
        raise ValueError("Search topic cannot be empty.")

    if max_results < 1:
        raise ValueError("max_results must be at least 1.")

    params = {
        "search": topic.strip(),
        "per-page": min(max_results, 200),
    }

    try:
        response = requests.get(
            OPENALEX_API_URL,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

    except requests.RequestException as exc:
        raise RuntimeError(
            f"OpenAlex search failed: {exc}"
        ) from exc

    data = response.json()

    papers = []

    for work in data.get("results", []):

        # Extract authors
        authors = []

        for authorship in work.get("authorships", []):
            author = authorship.get("author", {})
            author_name = author.get("display_name")

            if author_name:
                authors.append(author_name)

        # Reconstruct abstract
        abstract = reconstruct_abstract(
            work.get("abstract_inverted_index")
        )

        # Extract DOI
        doi = work.get("doi")

        # Extract source URL
        source_url = work.get("id")

        # Extract available PDF URL
        pdf_url = None

        locations = work.get("locations") or []

        for location in locations:
            if location.get("pdf_url"):
                pdf_url = location["pdf_url"]
                break

        # Extract publication date
        published_date = work.get("publication_date")

        metadata = {
            "title": work.get("title"),
            "abstract": abstract,
            "authors": authors,
            "published_date": published_date,
            "source_name": "openalex",
            "external_id": work.get("id"),
            "doi": doi,
            "source_url": source_url,
            "pdf_url": pdf_url,
            "matched_keywords": [topic.strip()],
        }

        papers.append(
            normalize_metadata(metadata)
        )

    return papers


class OpenAlexAdapter(BaseSourceAdapter):

    source_name = "openalex"

    def search(self, topic: str, max_results: int = 10) -> list[dict]:
        return search_openalex(topic, max_results)