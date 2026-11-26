from datetime import date, datetime


def normalize_metadata(metadata):
    """
    Normalize academic paper metadata from different sources
    into a common structure.
    """

    title = metadata.get("title")
    abstract = metadata.get("abstract")
    authors = metadata.get("authors")
    published_date = metadata.get("published_date")
    source_name = metadata.get("source_name")
    external_id = metadata.get("external_id")
    doi = metadata.get("doi")
    source_url = metadata.get("source_url")
    pdf_url = metadata.get("pdf_url")
    matched_keywords = metadata.get("matched_keywords")

    # Normalize title
    if title:
        title = " ".join(title.split())

    # Normalize abstract
    if abstract:
        abstract = " ".join(abstract.split())

    # Normalize authors
    if authors:
        if isinstance(authors, str):
            authors = [authors]

        authors = [
            author.strip()
            for author in authors
            if isinstance(author, str) and author.strip()
        ]

    # Normalize publication date
    if isinstance(published_date, datetime):
        published_date = published_date.date()

    elif isinstance(published_date, str):
        try:
            published_date = date.fromisoformat(
                published_date[:10]
            )
        except ValueError:
            published_date = None

    # Normalize DOI
    if doi:
        doi = doi.strip()

        prefixes = [
            "https://doi.org/",
            "http://doi.org/",
            "https://dx.doi.org/",
            "http://dx.doi.org/",
            "doi:",
        ]

        for prefix in prefixes:
            if doi.lower().startswith(prefix):
                doi = doi[len(prefix):]
                break

        doi = doi.strip()

    # Normalize source name
    if source_name:
        source_name = source_name.strip().lower()

    # Normalize matched keywords
    if matched_keywords:
        if isinstance(matched_keywords, str):
            matched_keywords = [matched_keywords]

        matched_keywords = [
            keyword.strip()
            for keyword in matched_keywords
            if isinstance(keyword, str) and keyword.strip()
        ]

    return {
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "published_date": published_date,
        "source_name": source_name,
        "external_id": external_id,
        "doi": doi,
        "source_url": source_url,
        "pdf_url": pdf_url,
        "matched_keywords": matched_keywords,
    }