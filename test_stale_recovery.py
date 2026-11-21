
from datetime import datetime, timedelta, timezone
from uuid import UUID

from database.models import Document
from database.session import SessionLocal
from database.document_repository import recover_stale_documents


DOCUMENT_ID = UUID("a389eb78-80f1-4e1a-b2ef-5bc7c3af3bb2")


def test_stale_document_recovery():

    # Save the original state.
    with SessionLocal() as session:

        document = session.get(Document, DOCUMENT_ID)

        if document is None:
            raise RuntimeError("Test document not found.")

        original_state = {
            "processing_status": document.processing_status,
            "processing_started_at": document.processing_started_at,
            "processed_at": document.processed_at,
            "processing_error": document.processing_error,
            "chunk_count": document.chunk_count,
        }

    try:

        # Temporarily simulate a document stuck for 2 hours.
        with SessionLocal() as session:

            document = session.get(Document, DOCUMENT_ID)

            document.processing_status = "processing"
            document.processing_started_at = (
                datetime.now(timezone.utc) - timedelta(hours=2)
            )
            document.processed_at = None
            document.processing_error = None

            session.commit()

        print("Temporary stale state created.")

        # Recover documents older than 30 minutes.
        recovered_count = recover_stale_documents(
            stale_after_minutes=30
        )

        print(f"Recovered count: {recovered_count}")

        # Verify the recovered state.
        with SessionLocal() as session:

            document = session.get(Document, DOCUMENT_ID)

            assert document.processing_status == "pending"
            assert document.processing_started_at is None
            assert document.processed_at is None
            assert document.processing_error is not None

        print("Recovery verification passed!")

    finally:

        # Restore the original state.
        with SessionLocal() as session:

            document = session.get(Document, DOCUMENT_ID)

            if document is not None:

                document.processing_status = (
                    original_state["processing_status"]
                )

                document.processing_started_at = (
                    original_state["processing_started_at"]
                )

                document.processed_at = (
                    original_state["processed_at"]
                )

                document.processing_error = (
                    original_state["processing_error"]
                )

                document.chunk_count = (
                    original_state["chunk_count"]
                )

                session.commit()

        print("Original document state restored.")


def test_fresh_document_not_recovered():

    # Save the original state.
    with SessionLocal() as session:

        document = session.get(Document, DOCUMENT_ID)

        original_state = {
            "processing_status": document.processing_status,
            "processing_started_at": document.processing_started_at,
            "processed_at": document.processed_at,
            "processing_error": document.processing_error,
            "chunk_count": document.chunk_count,
        }

    try:

        # Simulate a document currently being processed.
        with SessionLocal() as session:

            document = session.get(Document, DOCUMENT_ID)

            document.processing_status = "processing"
            document.processing_started_at = (
                datetime.now(timezone.utc) - timedelta(minutes=10)
            )
            document.processed_at = None
            document.processing_error = None

            session.commit()

        print("Temporary fresh processing state created.")

        recovered_count = recover_stale_documents(
            stale_after_minutes=30
        )

        assert recovered_count == 0

        # Verify the document remains processing.
        with SessionLocal() as session:

            document = session.get(Document, DOCUMENT_ID)

            assert document.processing_status == "processing"
            assert document.processing_started_at is not None

        print("Fresh document was correctly ignored!")

    finally:

        # Restore the original state.
        with SessionLocal() as session:

            document = session.get(Document, DOCUMENT_ID)

            if document is not None:

                document.processing_status = (
                    original_state["processing_status"]
                )

                document.processing_started_at = (
                    original_state["processing_started_at"]
                )

                document.processed_at = (
                    original_state["processed_at"]
                )

                document.processing_error = (
                    original_state["processing_error"]
                )

                document.chunk_count = (
                    original_state["chunk_count"]
                )

                session.commit()

        print("Original document state restored.")


if __name__ == "__main__":
    test_stale_document_recovery()
    test_fresh_document_not_recovered()
