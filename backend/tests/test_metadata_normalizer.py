from metadata.metadata_normalizer import normalize_metadata


# Simulated Crossref-style metadata
crossref_metadata = {
    "title": "  Machine Learning   for Scientific Discovery ",
    "abstract": " This paper explores   machine learning methods. ",
    "authors": ["Alice Smith", "Bob Jones"],
    "published_date": "2024-03-15",
    "source_name": "Crossref",
    "external_id": "crossref-123",
    "doi": "https://doi.org/10.1234/example.123",
    "source_url": "https://doi.org/10.1234/example.123",
    "pdf_url": None,
    "matched_keywords": ["machine learning", "scientific discovery"],
}


# Simulated arXiv-style metadata
arxiv_metadata = {
    "title": "Deep Learning for Research",
    "abstract": "A study of deep learning applications.",
    "authors": "Alice Smith",
    "published_date": "2023-06-20T12:00:00Z",
    "source_name": "arXiv",
    "external_id": "2306.04338",
    "doi": None,
    "source_url": "https://arxiv.org/abs/2306.04338",
    "pdf_url": "https://arxiv.org/pdf/2306.04338",
    "matched_keywords": "deep learning",
}


# Simulated incomplete metadata
incomplete_metadata = {
    "title": None,
    "abstract": None,
    "authors": None,
    "published_date": "invalid-date",
    "source_name": " OpenAlex ",
    "external_id": "W123456",
    "doi": "doi:10.5678/test",
    "source_url": None,
    "pdf_url": None,
    "matched_keywords": None,
}


test_cases = [
    crossref_metadata,
    arxiv_metadata,
    incomplete_metadata,
]


for index, metadata in enumerate(test_cases, start=1):

    normalized = normalize_metadata(metadata)

    print(f"\n--- Test Case {index} ---")

    for key, value in normalized.items():
        print(f"{key}: {value}")
        