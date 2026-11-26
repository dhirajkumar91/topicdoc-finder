from database.document_repository import get_pending_documents
from document_processor import process_document


pending_documents = get_pending_documents(limit=1)

if not pending_documents:
    print("No pending documents found.")
else:
    document = pending_documents[0]

    print("\nSelected document:")
    print(document["original_filename"])

    result = process_document(
        document_id=document["document_id"],
        file_path=document["file_path"],
    )

    print("\n========== FINAL RESULT ==========")
    print("Status:", result["status"])
    print("Chunks saved:", result["chunk_count"])
    print("Sections:", result["sections_count"])
    print("Document ID:", result["document_id"])