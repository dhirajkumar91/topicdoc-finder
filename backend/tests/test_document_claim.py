from uuid import UUID

from database.models import Document
from database.session import SessionLocal
from database.document_repository import claim_document_for_processing


document_id = UUID(
    "a389eb78-80f1-4e1a-b2ef-5bc7c3af3bb2"
)


# Save the document's original state.
with SessionLocal() as session:

    document = session.get(Document, document_id)

    if document is None:
        raise ValueError("Test document not found.")

    original_status = document.processing_status
    original_chunk_count = document.chunk_count
    original_processed_at = document.processed_at
    original_processing_error = document.processing_error


try:

    # Temporarily reset the document to pending.
    with SessionLocal.begin() as session:

        document = session.get(Document, document_id)

        document.processing_status = "pending"
        document.chunk_count = 0
        document.processed_at = None
        document.processing_error = None

    print("Document temporarily reset to pending.")

    # First claim.
    first_claim = claim_document_for_processing(
        document_id
    )

    print("First claim:", first_claim)

    # Second claim.
    second_claim = claim_document_for_processing(
        document_id
    )

    print("Second claim:", second_claim)

    assert first_claim is True
    assert second_claim is False

    print("\nAtomic claim test passed!")

finally:

    # Restore the document's original state.
    with SessionLocal.begin() as session:

        document = session.get(Document, document_id)

        document.processing_status = original_status
        document.chunk_count = original_chunk_count
        document.processed_at = original_processed_at
        document.processing_error = original_processing_error

    print("Original document state restored.")