from database.document_repository import (
    get_pending_documents,
    update_document_processing_status,
)

document_id = "a389eb78-80f1-4e1a-b2ef-5bc7c3af3bb2"

# Temporarily mark the document as processing
updated = update_document_processing_status(
    document_id=document_id,
    status="processing",
    processing_error=None,
)

print("Updated:", updated)

# Restore the document to pending
restored = update_document_processing_status(
    document_id=document_id,
    status="pending",
    chunk_count=0,
    processed_at=None,
    processing_error=None,
)

print("Restored:", restored)

# Verify
print("Pending documents:", get_pending_documents())
