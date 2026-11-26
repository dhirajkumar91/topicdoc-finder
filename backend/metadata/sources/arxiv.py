
import requests
import xml.etree.ElementTree as ET

from metadata.metadata_normalizer import normalize_metadata
from metadata.sources.base import BaseSourceAdapter


ARXIV_API_URL = "https://export.arxiv.org/api/query"

ATOM_NAMESPACE = {"atom": "http://www.w3.org/2005/Atom"}
ARXIV_NAMESPACE = {"arxiv": "http://arxiv.org/schemas/atom"}


def search_arxiv(topic, max_results=10):
    if not topic or not topic.strip():
        raise ValueError("Search topic cannot be empty.")

    if max_results < 1:
        raise ValueError("max_results must be at least 1.")

    params = {
        "search_query": f"all:{topic.strip()}",
        "start": 0,
        "max_results": min(max_results, 100),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    try:
        response = requests.get(
            ARXIV_API_URL,
            params=params,
            timeout=30,
        )
        response.raise_for_status()

    except requests.RequestException as exc:
        raise RuntimeError(
            f"arXiv search failed: {exc}"
        ) from exc

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as exc:
        raise RuntimeError(
            f"Failed to parse arXiv response: {exc}"
        ) from exc

    papers = []

    entries = root.findall("atom:entry", ATOM_NAMESPACE)

    for entry in entries:
        title_element = entry.find("atom:title", ATOM_NAMESPACE)
        abstract_element = entry.find("atom:summary", ATOM_NAMESPACE)
        published_element = entry.find("atom:published", ATOM_NAMESPACE)
        id_element = entry.find("atom:id", ATOM_NAMESPACE)

        title = (
            title_element.text.strip()
            if title_element is not None and title_element.text
            else None
        )

        abstract = (
            abstract_element.text.strip()
            if abstract_element is not None and abstract_element.text
            else None
        )

        published_date = (
            published_element.text[:10]
            if published_element is not None
            and published_element.text
            else None
        )

        paper_url = (
            id_element.text.strip()
            if id_element is not None and id_element.text
            else None
        )

        authors = []

        for author_element in entry.findall(
            "atom:author", ATOM_NAMESPACE
        ):
            name_element = author_element.find(
                "atom:name", ATOM_NAMESPACE
            )

            if name_element is not None and name_element.text:
                authors.append(name_element.text.strip())

        pdf_url = None

        for link in entry.findall("atom:link", ATOM_NAMESPACE):
            if link.attrib.get("title") == "pdf":
                pdf_url = link.attrib.get("href")
                break

        if not pdf_url:
            for link in entry.findall("atom:link", ATOM_NAMESPACE):
                if link.attrib.get("type") == "application/pdf":
                    pdf_url = link.attrib.get("href")
                    break

        doi_element = entry.find(
            "arxiv:doi", ARXIV_NAMESPACE
        )

        doi = (
            doi_element.text.strip()
            if doi_element is not None and doi_element.text
            else None
        )

        external_id = paper_url

        metadata = {
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "published_date": published_date,
            "source_name": "arxiv",
            "external_id": external_id,
            "doi": doi,
            "source_url": paper_url,
            "pdf_url": pdf_url,
            "matched_keywords": [topic.strip()],
        }

        papers.append(normalize_metadata(metadata))

    return papers


class ArxivAdapter(BaseSourceAdapter):

    source_name = "arxiv"

    def search(self, topic: str, max_results: int = 10) -> list[dict]:
        return search_arxiv(topic, max_results)
