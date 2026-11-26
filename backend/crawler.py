import re
import requests
import xml.etree.ElementTree as ET
from datetime import date

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from pathlib import Path
from requests.utils import unquote
from email.message import Message


DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".xlsx",
    ".xls",
    ".csv",
    ".docx",
    ".doc",
    ".pptx",
    ".ppt"
}

TOPIC_KEYWORDS = [
    "machine learning",
    "artificial intelligence",
    "deep learning",
    "neural networks",
    "natural language processing",
    "computer vision",
    "reinforcement learning"
]

MAX_DOWNLOAD_SIZE = 20 * 1024 * 1024  # 20 MB


RESEARCH_WEBSITES = [
    "https://arxiv.org/",
    "https://core.ac.uk/",
    "https://openaccessbutton.org/",
    "https://scholar.google.com/",
    "https://repository.mit.edu/",
    "https://dspace.mit.edu/",
    "https://research.tudelft.nl/",
    "https://openaccess.thecvf.com/",
    "https://www.fhwa.dot.gov/research/",
    "https://www.usgs.gov/",
    "https://www.worldbank.org/en/research",
    "https://www.tandfonline.com/",
    "https://www.mdpi.com/",
    "https://www.sciencedirect.com/",
    "https://link.springer.com/",
    "https://onlinelibrary.wiley.com/",
    "https://journals.sagepub.com/",
    "https://ieeexplore.ieee.org/",
    "https://asmedigitalcollection.asme.org/",
    "https://ascelibrary.org/",
    "https://saemobilus.sae.org/",
    "https://www.semanticscholar.org/",
    "https://www.techrxiv.org/",
    "https://zenodo.org/"
]




def fetch_page(url):
    """
    Fetch a webpage and return its HTML content.
    """

    try:
        response = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "TopicDocFinder/1.0"
            }
        )

        print(f"Status: {response.status_code} | URL: {url}")

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type", ""
        ).lower()

        if "text/html" not in content_type:
            print("The URL does not contain an HTML page.")
            return None

        return response.text

    except requests.RequestException as error:
        print(f"Error fetching {url}: {error}")
        return None


def extract_links(html, base_url):
    """
    Extract webpage links and direct document links.
    """

    soup = BeautifulSoup(html, "html.parser")

    webpage_links = []
    document_links = []

    for anchor in soup.find_all("a", href=True):

        href = anchor["href"].strip()

        if not href:
            continue

        full_url = urljoin(base_url, href)

        parsed_url = urlparse(full_url)

        if parsed_url.scheme not in ("http", "https"):
            continue

        link_text = anchor.get_text(" ", strip=True)

        extension = Path(parsed_url.path).suffix.lower()

        if extension in DOCUMENT_EXTENSIONS:

            document_links.append({
                "url": full_url,
                "text": link_text
            })

        else:

            webpage_links.append({
                "url": full_url,
                "text": link_text
            })

    return webpage_links, document_links


def is_relevant(url, keywords):
    """
    Check whether a webpage URL is relevant to the topic.
    """

    url = url.lower()

    return any(
        keyword.lower() in url
        for keyword in keywords
    )


def is_document_relevant(url, link_text, keywords):
    """
    Check whether a document URL or its link text is relevant.
    """

    combined_text = f"{url} {link_text}".lower()

    return any(
        keyword.lower() in combined_text
        for keyword in keywords
    )


# Document Downloader

def get_filename(response, url):
    """
    Extract a filename from Content-Disposition or the URL.
    """

    content_disposition = response.headers.get(
        "Content-Disposition", ""
    )

    if content_disposition:

        message = Message()
        message["Content-Disposition"] = content_disposition

        filename = message.get_filename()

        if filename:
            return unquote(filename)

    filename = Path(
        urlparse(url).path
    ).name

    return unquote(filename) if filename else "downloaded_document"


def validate_document(file_path):
    """
    Perform basic file-signature validation.
    """

    file_path = Path(file_path)

    extension = file_path.suffix.lower()

    try:
        with open(file_path, "rb") as file:
            signature = file.read(8)

        if extension == ".pdf":
            return signature.startswith(b"%PDF-")

        if extension in {".docx", ".xlsx", ".pptx"}:
            return signature.startswith(b"PK")

        if extension in {".doc", ".xls", ".ppt"}:
            return signature.startswith(
                bytes.fromhex("D0CF11E0A1B11AE1")
            )

        if extension == ".csv":
            return True

        return False

    except OSError:
        return False


def download_document(
    url,
    download_dir="downloads",
    *,
    source_name="Unknown",
    title=None,
    abstract=None,
    authors=None,
    published_date=None,
    external_id=None,
    doi=None,
    source_url=None,
    matched_keywords=None,
):
    """
    Download a document safely.

    Features:
    - Maximum download size of 20 MB.
    - Streaming download.
    - File extension validation.
    - Basic file-signature validation.
    - Duplicate filename protection.
    - Removes incomplete or invalid files.
    - Automatically registers downloaded PDFs in PostgreSQL.
    - Does not register other document formats.
    """

    download_path = Path(download_dir)
    download_path.mkdir(parents=True, exist_ok=True)

    file_path = None

    try:
        with requests.get(
            url,
            stream=True,
            timeout=30,
            allow_redirects=True,
            headers={
                "User-Agent": "TopicDocFinder/1.0"
            }
        ) as response:

            response.raise_for_status()

            content_type = response.headers.get(
                "Content-Type", ""
            ).lower()

            if "text/html" in content_type:
                print("Skipped: URL returned an HTML page.")
                return None

            filename = get_filename(response, response.url)

            extension = Path(filename).suffix.lower()

            if extension not in DOCUMENT_EXTENSIONS:
                print(
                    f"Skipped: Unsupported document format: "
                    f"{extension or 'unknown'}"
                )
                return None

            content_length = response.headers.get(
                "Content-Length"
            )

            if content_length:
                if int(content_length) > MAX_DOWNLOAD_SIZE:
                    print("Skipped: File exceeds the 20 MB limit.")
                    return None

            # Avoid overwriting an existing file.
            original_path = download_path / filename
            file_path = original_path

            counter = 1

            while file_path.exists():
                file_path = (
                    download_path
                    / f"{original_path.stem}_{counter}"
                    f"{original_path.suffix}"
                )

                counter += 1

            total_size = 0

            # Download the file in 8 KB chunks.
            with open(file_path, "wb") as file:

                for chunk in response.iter_content(
                    chunk_size=8192
                ):

                    if not chunk:
                        continue

                    total_size += len(chunk)

                    if total_size > MAX_DOWNLOAD_SIZE:
                        raise ValueError(
                            "File exceeds the 20 MB download limit."
                        )

                    file.write(chunk)

            if total_size == 0:
                raise ValueError("Downloaded file is empty.")

            # Validate the downloaded file.
            if not validate_document(file_path):
                raise ValueError(
                    "Downloaded file failed signature validation."
                )

            # Register PDFs in PostgreSQL.
            # Other supported formats are downloaded normally.
            if file_path.suffix.lower() == ".pdf":

                try:
                    from database.document_repository import (
                        save_document_metadata
                    )

                    result = save_document_metadata(
                        file_path=str(file_path),
                        pdf_url=response.url,
                        source_name=source_name,
                        title=title,
                        abstract=abstract,
                        authors=authors,
                        published_date=published_date,
                        external_id=external_id,
                        doi=doi,
                        source_url=source_url or url,
                        matched_keywords=matched_keywords,
                    )

                    print(
                        f"Database registration: {result['status']}"
                    )

                except Exception as error:
                    print(
                        "PDF downloaded, but database registration failed:",
                        type(error).__name__,
                        error
                    )

            print(f"Downloaded successfully: {file_path}")

            return str(file_path)

    except (
        requests.RequestException,
        OSError,
        ValueError
    ) as error:

        print(f"Download failed: {error}")

        if file_path and file_path.exists():
            file_path.unlink()

        return None


# Website Crawling

def crawl_website(
    start_url,
    max_pages=10,
    keywords=None,
    download=False
):
    """
    Crawl a website and identify relevant documents.

    Crawling is restricted to the starting website's host.
    """

    if keywords is None:
        keywords = TOPIC_KEYWORDS

    start_host = urlparse(start_url).netloc

    visited = set()
    queue = [start_url]

    discovered_documents = {}

    pages_crawled = 0

    
    while queue and pages_crawled < max_pages:

        current_url = queue.pop(0)

        if current_url in visited:
            continue

        if urlparse(current_url).netloc != start_host:
            continue

        visited.add(current_url)

        print(f"\nCrawling: {current_url}")

        html = fetch_page(current_url)

        if not html:
            continue

        pages_crawled += 1

        webpage_links, document_links = extract_links(
            html,
            current_url
        )

        # Identify relevant documents.
        for document in document_links:

            document_url = document["url"]
            link_text = document["text"]

            if is_document_relevant(
                document_url,
                link_text,
                keywords
            ):

                discovered_documents[document_url] = document

        # Add relevant webpages to the crawling queue.
        for link in webpage_links:

            link_url = link["url"]

            if (
                urlparse(link_url).netloc == start_host
                and link_url not in visited
                and (
                    is_relevant(link_url, keywords)
                    or is_document_relevant(
                        link_url,
                        link["text"],
                        keywords
                    )
                )
            ):

                queue.append(link_url)

    print("\n" + "=" * 60)
    print("WEBSITE CRAWLING COMPLETED")
    print("=" * 60)

    print("Pages crawled:", pages_crawled)

    print(
        "Relevant documents found:",
        len(discovered_documents)
    )

    documents = list(discovered_documents.values())

    for index, document in enumerate(documents, start=1):

        print(
            f"\n{index}. "
            f"{document['text'] or 'Untitled document'}"
        )

        print("URL:", document["url"])

    # Download discovered documents if requested.
    if download:

        source_name = urlparse(start_url).netloc or "Unknown"

        for document in documents:

            print(f"\nDownloading: {document['url']}")

            download_document(
                document["url"],
                source_name=source_name,
                title=document.get("text") or None,
                source_url=document["url"],
                matched_keywords=keywords,
            )

    return documents


def crawl_research_websites(
    keywords,
    max_pages_per_site=5,
    download=False
):
    """
    Crawl the configured research websites using AI-generated keywords.

    Each website is crawled independently, and duplicate document URLs
    are removed from the combined results.
    """

    unique_documents = {}

    for website in RESEARCH_WEBSITES:

        print("\\n" + "=" * 60)
        print("SEARCHING WEBSITE:", website)
        print("=" * 60)

        documents = crawl_website(
            start_url=website,
            max_pages=max_pages_per_site,
            keywords=keywords,
            download=download
        )

        for document in documents:
            document_url = document["url"]

            if document_url not in unique_documents:
                document["source_website"] = website
                unique_documents[document_url] = document

    return list(unique_documents.values())



# 5. ARXIV research paper search

def search_arxiv(topic, max_results=10):
    """
    Search arXiv using individual terms from an academic keyword.

    Instead of requiring the complete phrase to match,
    search for papers containing one or more important terms.
    """

    url = "https://export.arxiv.org/api/query"

    # Remove common words from the search phrase.
    stop_words = {
        "and", "or", "the", "a", "an", "of", "in",
        "on", "for", "to", "with", "into", "from"
    }

    terms = [
        word
        for word in re.findall(r"[a-zA-Z0-9]+", topic.lower())
        if word not in stop_words and len(word) > 2
    ]

    if not terms:
        return []

    # Combine individual terms using OR.
    search_query = " OR ".join(
        f"all:{term}" for term in terms
    )

    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending"
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=30,
            headers={
                "User-Agent": "TopicDocFinder/1.0"
            }
        )

        response.raise_for_status()

        root = ET.fromstring(response.content)

        namespace = {
            "atom": "http://www.w3.org/2005/Atom"
        }

        papers = []

        for entry in root.findall("atom:entry", namespace):

            title = entry.findtext(
                "atom:title",
                default="No title",
                namespaces=namespace
            ).strip().replace("\n", " ")

            summary = entry.findtext(
                "atom:summary",
                default="No abstract available",
                namespaces=namespace
            ).strip().replace("\n", " ")

            published = entry.findtext(
                "atom:published",
                default="Unknown",
                namespaces=namespace
            )

            doi = entry.findtext(
                "arxiv:doi",
                default=None,
                namespaces={
                    **namespace,
                    "arxiv": "http://arxiv.org/schemas/atom",
                },
            )

            authors = [
                author.findtext(
                    "atom:name",
                    default="Unknown",
                    namespaces=namespace
                )
                for author in entry.findall(
                    "atom:author",
                    namespace
                )
            ]

            pdf_url = None

            for link in entry.findall("atom:link", namespace):

                if link.attrib.get("title") == "pdf":
                    pdf_url = link.attrib.get("href")
                    break

            # Construct the PDF URL if it is not provided.
            if not pdf_url:

                paper_id = entry.findtext(
                    "atom:id",
                    default="",
                    namespaces=namespace
                )

                if paper_id:

                    paper_id = paper_id.replace(
                        "http://arxiv.org/abs/",
                        ""
                    )

                    pdf_url = (
                        f"https://arxiv.org/pdf/{paper_id}"
                    )

            if not pdf_url:
                continue

            papers.append({
                "title": title,
                "summary": summary,
                "published": published,
                "authors": authors,
                "pdf_url": pdf_url,
                "doi": doi,
            })

        return papers

    except requests.RequestException as error:

        print(f"arXiv request failed: {error}")
        return []

    except ET.ParseError as error:

        print(f"Could not parse arXiv response: {error}")
        return []



# 6. Search ARXIV using AI-Generated keywords

def search_arxiv_by_keywords(keywords, max_results=10):
    """
    Search arXiv using multiple academic keywords.

    Combine results and remove duplicate papers.
    """

    unique_papers = {}

    for keyword in keywords:

        print(f"\nSearching arXiv for: {keyword}")

        papers = search_arxiv(
            keyword,
            max_results=max_results
        )

        print(
            "Papers found for this keyword:",
            len(papers)
        )

        for paper in papers:

            # Use PDF URL as a unique identifier.
            paper_id = paper["pdf_url"].rstrip("/")

            if paper_id not in unique_papers:

                paper["matched_keywords"] = [keyword]

                unique_papers[paper_id] = paper

            else:

                unique_papers[paper_id][
                    "matched_keywords"
                ].append(keyword)

    return list(unique_papers.values())



if __name__ == "__main__":

    from ai_keyword_generator import generate_research_keywords

    question = input(
        "Enter your research question: "
    ).strip()

    if not question:

        print("Please enter a research question.")

    else:

        try:

            # Step 1: Generate academic keywords using Gemini.
            print("\nGenerating academic keywords using Gemini...")

            ai_result = generate_research_keywords(question)

            research_topic = ai_result["research_topic"]
            keywords = ai_result["keywords"]

            print("\n" + "=" * 60)
            print("AI-GENERATED RESEARCH TOPIC")
            print("=" * 60)

            print(research_topic)

            print("\nAI-generated academic keywords:")

            for index, keyword in enumerate(
                keywords,
                start=1
            ):

                print(f"{index}. {keyword}")

            # Step 2: Search the additional research websites.
            website_documents = crawl_research_websites(
                keywords,
                max_pages_per_site=5,
                download=False
            )

            print("\\n" + "=" * 60)
            print("ADDITIONAL WEBSITE SEARCH RESULTS")
            print("=" * 60)

            print(
                "Total unique documents found:",
                len(website_documents)
            )

            for index, document in enumerate(
                website_documents,
                start=1
            ):
                print(
                    f"\\n{index}. "
                    f"{document['text'] or 'Untitled document'}"
                )
                print("Source:", document.get("source_website", "Unknown"))
                print("URL:", document["url"])

            if website_documents:
                website_selection = input(
                    "\\nEnter website document numbers to download "
                    "(e.g. 1,3,5), type 'all', or press Enter to skip: "
                ).strip().lower()

                if website_selection == "all":
                    selected_website_indices = list(
                        range(len(website_documents))
                    )
                elif website_selection:
                    try:
                        selected_website_indices = sorted({
                            int(value.strip()) - 1
                            for value in website_selection.split(",")
                        })

                        if any(
                            index < 0 or index >= len(website_documents)
                            for index in selected_website_indices
                        ):
                            raise ValueError(
                                "Document number out of range."
                            )
                    except ValueError:
                        print(
                            "Invalid selection. "
                            "Skipping website document downloads."
                        )
                        selected_website_indices = []
                else:
                    selected_website_indices = []

                for index in selected_website_indices:
                    document = website_documents[index]

                    print(
                        f"\\nDownloading: "
                        f"{document['text'] or document['url']}"
                    )

                    # result = download_document(document["url"])
                    source_website = document.get("source_website", "")
                    source_name = urlparse(source_website).netloc or "Unknown"

                    result = download_document(
                        document["url"],
                        source_name=source_name,
                        title=document.get("text") or None,
                        source_url=document["url"],
                        matched_keywords=keywords,
                    )

                    if result:
                        print("Saved successfully:", result)

            # Step 3: Search arXiv using generated keywords.
            papers = search_arxiv_by_keywords(
                keywords,
                max_results=10
            )

            # Step 3: Display research results.
            print("\n" + "=" * 60)
            print("RESEARCH SEARCH RESULTS")
            print("=" * 60)

            print("Original question:", question)
            print("Research topic:", research_topic)
            print("Total unique papers found:", len(papers))

            if not papers:

                print("\nNo papers found.")

            else:

                for index, paper in enumerate(
                    papers,
                    start=1
                ):

                    print(f"\n{index}. {paper['title']}")

                    print(
                        "Published:",
                        paper["published"]
                    )

                    print(
                        "Authors:",
                        ", ".join(paper["authors"][:3])
                    )

                    print("PDF:", paper["pdf_url"])

                    print(
                        "Matched keywords:",
                        ", ".join(paper["matched_keywords"])
                    )

                    print(
                        "Abstract:",
                        paper["summary"][:250],
                        "..."
                    )

                # Step 4: Ask which papers to download.
                selection = input(
                    "\nEnter paper numbers to download "
                    "(e.g. 1,3,5), or type 'all': "
                ).strip().lower()

                if selection == "all":

                    selected_indices = list(
                        range(len(papers))
                    )

                else:

                    try:

                        selected_indices = sorted({
                            int(value.strip()) - 1
                            for value in selection.split(",")
                        })

                        if any(
                            index < 0 or index >= len(papers)
                            for index in selected_indices
                        ):

                            raise ValueError(
                                "Paper number out of range."
                            )

                    except ValueError:

                        print(
                            "Invalid selection. "
                            "Enter valid paper numbers."
                        )

                        selected_indices = []

                # Step 5: Download selected research papers.
                for index in selected_indices:

                    paper = papers[index]

                    print(
                        f"\nDownloading: {paper['title']}"
                    )

                    # Extract the arXiv identifier from the PDF URL.
                    paper_id = (
                        urlparse(paper["pdf_url"])
                        .path
                        .rstrip("/")
                        .split("/")[-1]
                        .removesuffix(".pdf")
                    )

                    # Convert the publication date to a Python date object.
                    published_date = None
                    published_value = paper.get("published")

                    if published_value and published_value != "Unknown":
                        try:
                            published_date = date.fromisoformat(
                                published_value[:10]
                            )
                        except ValueError:
                            print(
                                "Could not parse publication date:",
                                published_value
                            )

                    result = download_document(
                        paper["pdf_url"],
                        source_name="arXiv",
                        title=paper.get("title"),
                        abstract=paper.get("summary"),
                        authors=paper.get("authors"),
                        published_date=published_date,
                        external_id=paper_id or None,
                        doi=paper.get("doi"),
                        source_url=(
                            f"https://arxiv.org/abs/{paper_id}"
                            if paper_id else paper["pdf_url"]
                        ),
                        matched_keywords=paper.get("matched_keywords", []),
                    )

                    if result:

                        print(
                            "Saved successfully:",
                            result
                        )

        except Exception as error:

            print("\nResearch search failed:")
            print(type(error).__name__, error)
