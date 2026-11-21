from sqlalchemy import select

from database.models import Document
from database.session import SessionLocal


document_id = "a389eb78-80f1-4e1a-b2ef-5bc7c3af3bb2"

with SessionLocal() as session:
    document = session.scalar(
        select(Document).where(
            Document.id == document_id
        )
    )

    if document is None:
        print("Document not found.")
    else:
        print("Document found.")
        print("Filename:", document.original_filename)
        print("Current status:", document.processing_status)
        print("Current chunk count:", document.chunk_count)