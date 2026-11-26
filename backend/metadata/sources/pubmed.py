
import requests
import xml.etree.ElementTree as ET

from metadata.metadata_normalizer import normalize_metadata
from metadata.sources.base import BaseSourceAdapter


NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

ESEARCH_URL = f"{NCBI_BASE_URL}/esearch.fcgi"
EFETCH_URL = f"{NCBI_BASE_URL}/efetch.fcgi"


def extract_pubmed_date(article):
    date_element = article.find(
        ".//PubDate"
    )

    if date_element is None:
        return None

    year = date_element.findtext("Year")
    month = date_element.findtext("Month")
    day = date_element.findtext("Day")

    if not year:
        medline_date = date_element.findtext("MedlineDate")

        if medline_date:
            year = medline_date[:4]

    if not year:
        return None

    month_map = {
        "Jan": "01",
        "Feb": "02",
        "Mar": "03",
        "Apr": "04",
        "May": "05",
        "Jun": "06",
        "Jul": "07",
        "Aug": "08",
        "Sep": "09",
        "Oct": "10",
        "Nov": "11",
        "Dec": "12",
    }

    if month:
        month = month_map.get(month, month)

    if not month:
        month = "01"

    if not day:
        day = "01"

    try:
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    except (ValueError, TypeError):
        return None


def extract_pubmed_abstract(article):
    abstract_sections = article.findall(
        ".//Abstract/AbstractText"
    )

    if not abstract_sections:
        return None

    parts = []

    for section in abstract_sections:
        text = "".join(section.itertext()).strip()

        if not text:
            continue

        label = section.attrib.get("Label")

        if label:
            parts.append(f"{label}: {text}")
        else:
            parts.append(text)

    return " ".join(parts) if parts else None


def extract_pubmed_authors(article):
    authors = []

    author_elements = article.findall(
        ".//AuthorList/Author"
    )

    for author_element in author_elements:
        collective_name = author_element.findtext(
            "CollectiveName"
        )

        if collective_name:
            authors.append(collective_name.strip())
            continue

        last_name = author_element.findtext("LastName")
        fore_name = author_element.findtext("ForeName")
        initials = author_element.findtext("Initials")

        name_parts = []

        if fore_name:
            name_parts.append(fore_name.strip())
        elif initials:
            name_parts.append(initials.strip())

        if last_name:
            name_parts.append(last_name.strip())

        author_name = " ".join(name_parts)

        if author_name:
            authors.append(author_name)

    return authors


def extract_pubmed_doi(article):
    article_ids = article.findall(
        ".//PubmedData/ArticleIdList/ArticleId"
    )

    for article_id in article_ids:
        if article_id.attrib.get("IdType") == "doi":
            return article_id.text.strip() if article_id.text else None

    return None


def search_pubmed(topic, max_results=10):
    if not topic or not topic.strip():
        raise ValueError("Search topic cannot be empty.")

    if max_results < 1:
        raise ValueError("max_results must be at least 1.")

    search_params = {
        "db": "pubmed",
        "term": topic.strip(),
        "retmax": min(max_results, 100),
        "retmode": "json",
        "sort": "relevance",
    }

    try:
        search_response = requests.get(
            ESEARCH_URL,
            params=search_params,
            timeout=30,
        )

        search_response.raise_for_status()

    except requests.RequestException as exc:
        raise RuntimeError(
            f"PubMed search failed: {exc}"
        ) from exc

    search_data = search_response.json()

    pmids = (
        search_data.get("esearchresult", {})
        .get("idlist", [])
    )

    if not pmids:
        return []

    fetch_params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    }

    try:
        fetch_response = requests.get(
            EFETCH_URL,
            params=fetch_params,
            timeout=30,
        )

        fetch_response.raise_for_status()

    except requests.RequestException as exc:
        raise RuntimeError(
            f"PubMed metadata retrieval failed: {exc}"
        ) from exc

    try:
        root = ET.fromstring(fetch_response.content)

    except ET.ParseError as exc:
        raise RuntimeError(
            f"Failed to parse PubMed XML: {exc}"
        ) from exc

    papers = []

    for article in root.findall(".//PubmedArticle"):
        medline_article = article.find(
            ".//MedlineCitation/Article"
        )

        if medline_article is None:
            continue

        title_element = medline_article.find("ArticleTitle")

        title = (
            "".join(title_element.itertext()).strip()
            if title_element is not None
            else None
        )

        pmid_element = article.find(
            ".//MedlineCitation/PMID"
        )

        pmid = (
            pmid_element.text.strip()
            if pmid_element is not None and pmid_element.text
            else None
        )

        if not pmid:
            continue

        abstract = extract_pubmed_abstract(
            medline_article
        )

        authors = extract_pubmed_authors(
            medline_article
        )

        published_date = extract_pubmed_date(
            medline_article
        )

        doi = extract_pubmed_doi(article)

        source_url = (
            f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        )

        metadata = {
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "published_date": published_date,
            "source_name": "pubmed",
            "external_id": pmid,
            "doi": doi,
            "source_url": source_url,
            "pdf_url": None,
            "matched_keywords": [topic.strip()],
        }

        papers.append(
            normalize_metadata(metadata)
        )

    return papers


class PubMedAdapter(BaseSourceAdapter):

    source_name = "pubmed"

    def search(self, topic: str, max_results: int = 10) -> list[dict]:
        return search_pubmed(topic, max_results)