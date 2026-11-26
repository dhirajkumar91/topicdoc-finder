import re
from pathlib import Path
from datetime import date
from urllib.parse import urlparse

import requests

from database.document_repository import save_document_metadata


DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,*/*",
}


def create_filename(paper):
    """Create a safe filename for a research paper."""

    title = paper.get("title") or "research_paper"
    external_id = paper.get("external_id") or paper.get("doi") or ""

    title = re.sub(r'[<>:"/\\|?*]', "", title)
    title = re.sub(r"\s+", "_", title.strip())
    title = title[:100]

    external_id = re.sub(r'[<>:"/\\|?*]', "", str(external_id))
    external_id = re.sub(r"\s+", "_", external_id)
    external_id = external_id[-40:]

    if external_id:
        filename = f"{title}_{external_id}.pdf"
    else:
        filename = f"{title}.pdf"

    return filename


def infer_source_name(paper, successful_pdf_url=None):
    """Return a meaningful source name from metadata or URLs."""

    source_name = paper.get("source_name")
    if source_name and str(source_name).strip().lower() != "unknown":
        return str(source_name).strip()

    sources = paper.get("sources")
    if isinstance(sources, list) and sources:
        first_source = sources[0]
        if first_source and str(first_source).strip():
            return str(first_source).strip()

    source = paper.get("source")
    if source and str(source).strip().lower() != "unknown":
        return str(source).strip()

    # Prefer the original source URL when present; otherwise use the URL
    # from which the PDF was actually retrieved.
    for url in (paper.get("source_url"), successful_pdf_url, paper.get("pdf_url")):
        if not url:
            continue
        hostname = urlparse(str(url)).hostname
        if hostname:
            hostname = hostname.lower()
            if hostname.startswith("www."):
                hostname = hostname[4:]

            # Normalize common academic hosts to recognizable names.
            known_sources = {
                "arxiv.org": "arXiv",
                "openalex.org": "OpenAlex",
                "semanticscholar.org": "Semantic Scholar",
                "core.ac.uk": "CORE",
                "doi.org": "DOI",
                "pubmed.ncbi.nlm.nih.gov": "PubMed",
                "ncbi.nlm.nih.gov": "PubMed/NCBI",
                "researchgate.net": "ResearchGate",
                "ieee.org": "IEEE",
                "acm.org": "ACM",
                "springer.com": "Springer",
                "springerlink.com": "Springer",
                "sciencedirect.com": "ScienceDirect",
                "nature.com": "Nature",
                "wiley.com": "Wiley",
                "mdpi.com": "MDPI",
                "frontiersin.org": "Frontiers",
                "tandfonline.com": "Taylor & Francis",
                "sagepub.com": "SAGE",
                "jstor.org": "JSTOR",
            }

            for domain, label in known_sources.items():
                if hostname == domain or hostname.endswith("." + domain):
                    return label

            return hostname

    return "unknown"


def find_alternative_pdf_urls(paper):
    """Discover alternative Open Access PDF URLs using paper metadata.

    OpenAlex is used as a metadata discovery service.
    Actual downloading is source-independent.
    """

    doi = paper.get("doi")
    title = paper.get("title")

    headers = {
        "User-Agent": "TopicDocFinder/1.0",
    }

    try:
        work = None

        # Attempt DOI-based lookup
        if doi:
            doi = str(doi).strip()
            doi = doi.replace("https://doi.org/", "")
            doi = doi.replace("http://doi.org/", "")
            doi = doi.replace("https://dx.doi.org/", "")

            response = requests.get(
                "https://api.openalex.org/works/"
                f"https://doi.org/{doi}",
                headers=headers,
                timeout=20,
            )

            if response.status_code == 200:
                work = response.json()

        # Fallback to title-based lookup
        if not work and title:
            response = requests.get(
                "https://api.openalex.org/works",
                params={
                    "search": title,
                    "per-page": 5,
                },
                headers=headers,
                timeout=20,
            )

            response.raise_for_status()
            results = response.json().get("results", [])

            if results:
                work = results[0]

        if not work:
            return []

        pdf_urls = []

        # Prioritize the best OA location
        best_location = work.get("best_oa_location") or {}
        best_pdf_url = best_location.get("pdf_url")

        if best_pdf_url:
            pdf_urls.append(best_pdf_url)

        # Collect other OA locations
        for location in work.get("locations", []):
            pdf_url = location.get("pdf_url")
            if pdf_url and pdf_url not in pdf_urls:
                pdf_urls.append(pdf_url)

        return pdf_urls

    except requests.RequestException as error:
        print(f"Alternative URL discovery failed: {error}")
        return []


def download_pdf_to_temp(url, temporary_path):
    response = None

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=60,
            stream=True,
            allow_redirects=True,
        )

        print(f"\nPDF URL: {url}")
        print(f"HTTP Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print(f"Final URL: {response.url}")

        response.raise_for_status()

        iterator = response.iter_content(chunk_size=8192)

        first_chunk = b""

        for chunk in iterator:
            if chunk:
                first_chunk = chunk
                break

        if not first_chunk:
            print("Rejected: Empty response.")
            return False

        # PDF headers may occur within the first 1024 bytes.
        header_position = first_chunk[:1024].find(b"%PDF-")

        if header_position == -1:
            print("Rejected: Response is not a valid PDF.")
            print(f"Response preview: {first_chunk[:300]!r}")
            return False

        with open(temporary_path, "wb") as file:
            file.write(first_chunk)

            for chunk in iterator:
                if chunk:
                    file.write(chunk)

        print(f"PDF downloaded successfully: {temporary_path}")
        return True

    except requests.RequestException as exc:
        print(f"PDF request failed: {type(exc).__name__}: {exc}")

        if response is not None:
            print(f"HTTP Status: {response.status_code}")
            print(f"Final URL: {response.url}")

        return False

    except OSError as exc:
        print(f"PDF file writing failed: {exc}")
        return False

    finally:
        if response is not None:
            response.close()



def download_and_register_paper(paper):
    """Download a paper PDF and register its metadata.

    Workflow:
    1. Attempt the original PDF URL.
    2. If unsuccessful, discover alternative OA URLs.
    3. Try alternative URLs sequentially.
    4. Validate the PDF.
    5. Register the document in PostgreSQL.

    Returns a dictionary containing the download status.
    """

    original_pdf_url = paper.get("pdf_url")

    if not original_pdf_url:
        return {
            "status": "failed",
            "title": paper.get("title"),
            "message": "No PDF URL available.",
        }

    if not original_pdf_url.startswith(("http://", "https://")):
        return {
            "status": "failed",
            "title": paper.get("title"),
            "message": "Invalid PDF URL.",
        }

    file_path = DOWNLOAD_DIR / create_filename(paper)
    temporary_path = file_path.with_suffix(".part")
    successful_pdf_url = None

    try:
        # STEP 1: Attempt the original PDF URL
        print(f"Attempting original PDF URL: {original_pdf_url}")

        if download_pdf_to_temp(original_pdf_url, temporary_path):
            successful_pdf_url = original_pdf_url
            print("Original PDF download successful.")
        else:
            temporary_path.unlink(missing_ok=True)

            # STEP 2: Discover alternative PDF URLs
            print(
                "Original PDF unavailable or invalid. "
                "Searching alternative OA locations..."
            )

            alternative_pdf_urls = find_alternative_pdf_urls(paper)

            if not alternative_pdf_urls:
                return {
                    "status": "failed",
                    "title": paper.get("title"),
                    "message": (
                        "Original PDF unavailable. "
                        "No alternative Open Access PDFs found."
                    ),
                }

            # STEP 3: Try alternative URLs sequentially
            for alternative_url in alternative_pdf_urls:
                if alternative_url == original_pdf_url:
                    continue

                print(f"Trying alternative PDF URL: {alternative_url}")
                temporary_path.unlink(missing_ok=True)

                if download_pdf_to_temp(alternative_url, temporary_path):
                    successful_pdf_url = alternative_url
                    print("Alternative PDF download successful.")
                    break

                temporary_path.unlink(missing_ok=True)

            if not successful_pdf_url:
                return {
                    "status": "failed",
                    "title": paper.get("title"),
                    "message": (
                        "Original PDF unavailable. All discovered "
                        "alternative URLs failed or returned invalid PDFs."
                    ),
                }

        # STEP 4: Move validated PDF to final location
        temporary_path.replace(file_path)

        # STEP 5: Normalize publication date
        published_date = paper.get("published_date")

        if isinstance(published_date, str):
            try:
                published_date = date.fromisoformat(published_date[:10])
            except ValueError:
                published_date = None

        # STEP 6: Resolve a meaningful source name
        source_name = infer_source_name(paper, successful_pdf_url)

        print(f"Resolved document source: {source_name}")

        # STEP 7: Register metadata in PostgreSQL
        result = save_document_metadata(
            file_path=file_path,
            pdf_url=successful_pdf_url,
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
        }

    except Exception as error:
        temporary_path.unlink(missing_ok=True)
        print(f"Paper processing failed: {error}")

        return {
            "status": "failed",
            "title": paper.get("title"),
            "message": str(error),
        }

    finally:
        temporary_path.unlink(missing_ok=True)
