from database.document_repository import save_document_metadata


file_path = "downloads/1112.3867v1.pdf"

metadata = {
    "file_path": file_path,
    "pdf_url": "https://arxiv.org/pdf/1112.3867v1",
    "source_name": "arXiv",
    "external_id": "1112.3867v1",
    "doi": "10.48550/arXiv.1112.3867",
    "source_url": "https://arxiv.org/abs/1112.3867",
    "matched_keywords": [],
}

# First attempt
print("\nFirst registration:")
result = save_document_metadata(**metadata)
print(result)

# Second attempt: should detect the duplicate
print("\nSecond registration:")
result = save_document_metadata(**metadata)
print(result)