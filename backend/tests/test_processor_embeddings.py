from database.document_repository import get_pending_documents
from document_processor import process_document
from embeddings.batch_processor import generate_embeddings_in_batches


pending_documents = get_pending_documents(limit=1)

if not pending_documents:
    print("No pending documents found.")
else:
    document = pending_documents[0]

    result = process_document(
        document_id=document["document_id"],
        file_path=document["file_path"],
    )

    # Test embedding generation on only 2 chunks.
    test_chunks = result["chunks"][:2]

    embedding_result = generate_embeddings_in_batches(
        chunks=test_chunks,
        batch_size=2,
    )

    print("\n--- Embedding Test Results ---")

    print(
        "Successful embeddings:",
        len(embedding_result["results"]),
    )

    print(
        "Failed embeddings:",
        len(embedding_result["failures"]),
    )

    if embedding_result["results"]:
        embedding = embedding_result["results"][0]["embedding"]

        print("Embedding dimensions:", len(embedding))
        print("First 5 values:", embedding[:5])