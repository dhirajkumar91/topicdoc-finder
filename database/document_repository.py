# import hashlib
# from pathlib import Path

# from sqlalchemy import select, update
# from sqlalchemy.exc import IntegrityError

# from database.models import Document
# from database.session import SessionLocal


# def calculate_file_hash(file_path):
#     """
#     Calculate SHA-256 hash without loading the entire file into memory.
#     """

#     sha256 = hashlib.sha256()

#     with open(file_path, "rb") as file:
#         for chunk in iter(lambda: file.read(8192), b""):
#             sha256.update(chunk)

#     return sha256.hexdigest()


# def save_document_metadata(
#     file_path,
#     pdf_url,
#     source_name,
#     title=None,
#     abstract=None,
#     authors=None,
#     published_date=None,
#     external_id=None,
#     source_url=None,
#     matched_keywords=None,
# ):
#     """
#     Save downloaded PDF metadata in PostgreSQL.

#     Returns:
#         Dictionary containing status and document ID.
#     """

#     file_path = Path(file_path)

#     if not file_path.exists():
#         raise FileNotFoundError(
#             f"Downloaded file not found: {file_path}"
#         )

#     if file_path.suffix.lower() != ".pdf":
#         raise ValueError("Only PDF files can be registered.")

#     file_hash = calculate_file_hash(file_path)
#     file_size = file_path.stat().st_size

#     with SessionLocal() as session:

#         # Check whether this exact PDF already exists.
#         existing_document = session.scalar(
#             select(Document).where(
#                 Document.file_hash == file_hash
#             )
#         )

#         if existing_document:
#             return {
#                 "status": "duplicate",
#                 "document_id": str(existing_document.id),
#             }

#         document = Document(
#             title=title,
#             abstract=abstract,
#             authors=authors,
#             published_date=published_date,
#             source_name=source_name,
#             external_id=external_id,
#             source_url=source_url,
#             pdf_url=pdf_url,
#             original_filename=file_path.name,
#             file_path=str(file_path.resolve()),
#             file_hash=file_hash,
#             file_size=file_size,
#             content_type="application/pdf",
#             matched_keywords=matched_keywords,

#             # Processing tracking initialization
#             processing_status="pending",
#             chunk_count=0,
#             processed_at=None,
#             processing_error=None,
#         )

#         try:
#             session.add(document)
#             session.commit()

#             return {
#                 "status": "saved",
#                 "document_id": str(document.id),
#             }

#         except IntegrityError:
#             session.rollback()

#             # Handles a duplicate inserted concurrently.
#             existing_document = session.scalar(
#                 select(Document).where(
#                     Document.file_hash == file_hash
#                 )
#             )

#             if existing_document:
#                 return {
#                     "status": "duplicate",
#                     "document_id": str(existing_document.id),
#                 }

#             raise


# def get_pending_documents(limit=10):
#     """
#     Retrieve documents awaiting processing.

#     Args:
#         limit: Maximum number of documents to retrieve.

#     Returns:
#         List of dictionaries containing document information.
#     """

#     with SessionLocal() as session:
#         documents = session.scalars(
#             select(Document)
#             .where(Document.processing_status == "pending")
#             .order_by(Document.created_at.asc())
#             .limit(limit)
#         ).all()

#         return [
#             {
#                 "document_id": str(document.id),
#                 "file_path": document.file_path,
#                 "title": document.title,
#                 "original_filename": document.original_filename,
#             }
#             for document in documents
#         ]
    

# def update_document_processing_status(
#     document_id,
#     status,
#     chunk_count=None,
#     processed_at=None,
#     processing_error=None,
# ):
#     """
#     Update document processing status and related fields.

#     Args:
#         document_id: UUID of the document.
#         status: pending, processing, completed, or failed.
#         chunk_count: Number of stored chunks.
#         processed_at: Processing completion timestamp.
#         processing_error: Error details if processing fails.

#     Returns:
#         True if the document was updated, otherwise False.
#     """

#     from uuid import UUID

#     allowed_statuses = {
#         "pending",
#         "processing",
#         "completed",
#         "failed",
#     }

#     if status not in allowed_statuses:
#         raise ValueError(f"Invalid processing status: {status}")

#     document_id = UUID(str(document_id))

#     with SessionLocal() as session:
#         document = session.get(Document, document_id)

#         if document is None:
#             return False

#         document.processing_status = status

#         if chunk_count is not None:
#             document.chunk_count = chunk_count

#         document.processed_at = processed_at
#         document.processing_error = processing_error

#         session.commit()

#         return True
    

# def claim_document_for_processing(document_id):
#     """
#     Atomically claim a pending document for processing.

#     Returns:
#         True if the document was successfully claimed.
#         False if the document is not pending or doesn't exist.
#     """

#     from uuid import UUID

#     document_id = UUID(str(document_id))

#     with SessionLocal.begin() as session:

#         result = session.execute(
#             update(Document)
#             .where(
#                 Document.id == document_id,
#                 Document.processing_status == "pending",
#             )
#             .values(
#                 processing_status="processing",
#                 processed_at=None,
#                 processing_error=None,
#             )
#         )

#         return result.rowcount == 1















import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from database.models import Document
from database.session import SessionLocal


def calculate_file_hash(file_path):
    """
    Calculate SHA-256 hash without loading the entire file into memory.
    """

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def save_document_metadata(
    file_path,
    pdf_url,
    source_name,
    title=None,
    abstract=None,
    authors=None,
    published_date=None,
    external_id=None,
    source_url=None,
    matched_keywords=None,
):
    """
    Save downloaded PDF metadata in PostgreSQL.

    Returns:
        Dictionary containing status and document ID.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Downloaded file not found: {file_path}"
        )

    if file_path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files can be registered.")

    file_hash = calculate_file_hash(file_path)
    file_size = file_path.stat().st_size

    with SessionLocal() as session:

        # Check whether this exact PDF already exists.
        existing_document = session.scalar(
            select(Document).where(
                Document.file_hash == file_hash
            )
        )

        if existing_document:
            return {
                "status": "duplicate",
                "document_id": str(existing_document.id),
            }

        document = Document(
            title=title,
            abstract=abstract,
            authors=authors,
            published_date=published_date,
            source_name=source_name,
            external_id=external_id,
            source_url=source_url,
            pdf_url=pdf_url,
            original_filename=file_path.name,
            file_path=str(file_path.resolve()),
            file_hash=file_hash,
            file_size=file_size,
            content_type="application/pdf",
            matched_keywords=matched_keywords,

            # Processing tracking initialization
            processing_status="pending",
            chunk_count=0,
            processed_at=None,
            processing_started_at=None,
            processing_error=None,
        )

        try:
            session.add(document)
            session.commit()

            return {
                "status": "saved",
                "document_id": str(document.id),
            }

        except IntegrityError:
            session.rollback()

            # Handles a duplicate inserted concurrently.
            existing_document = session.scalar(
                select(Document).where(
                    Document.file_hash == file_hash
                )
            )

            if existing_document:
                return {
                    "status": "duplicate",
                    "document_id": str(existing_document.id),
                }

            raise


def get_pending_documents(limit=10):
    """
    Retrieve documents awaiting processing.

    Args:
        limit: Maximum number of documents to retrieve.

    Returns:
        List of dictionaries containing document information.
    """

    with SessionLocal() as session:
        documents = session.scalars(
            select(Document)
            .where(Document.processing_status == "pending")
            .order_by(Document.created_at.asc())
            .limit(limit)
        ).all()

        return [
            {
                "document_id": str(document.id),
                "file_path": document.file_path,
                "title": document.title,
                "original_filename": document.original_filename,
            }
            for document in documents
        ]


def update_document_processing_status(
    document_id,
    status,
    chunk_count=None,
    processed_at=None,
    processing_error=None,
):
    """
    Update document processing status and related fields.

    Args:
        document_id: UUID of the document.
        status: pending, processing, completed, or failed.
        chunk_count: Number of stored chunks.
        processed_at: Processing completion timestamp.
        processing_error: Error details if processing fails.

    Returns:
        True if the document was updated, otherwise False.
    """

    from uuid import UUID

    allowed_statuses = {
        "pending",
        "processing",
        "completed",
        "failed",
    }

    if status not in allowed_statuses:
        raise ValueError(f"Invalid processing status: {status}")

    document_id = UUID(str(document_id))

    # Track when processing begins.
    if status == "processing":
        processing_started_at = datetime.now(timezone.utc)
    else:
        processing_started_at = None

    with SessionLocal() as session:

        document = session.get(Document, document_id)

        if document is None:
            return False

        document.processing_status = status

        if chunk_count is not None:
            document.chunk_count = chunk_count

        document.processed_at = processed_at
        document.processing_started_at = processing_started_at
        document.processing_error = processing_error

        session.commit()

        return True


def claim_document_for_processing(document_id):
    """
    Atomically claim a pending document for processing.

    Returns:
        True if the document was successfully claimed.
        False if the document is not pending or doesn't exist.
    """

    from uuid import UUID

    document_id = UUID(str(document_id))

    with SessionLocal.begin() as session:

        result = session.execute(
            update(Document)
            .where(
                Document.id == document_id,
                Document.processing_status == "pending",
            )
            .values(
                processing_status="processing",
                processing_started_at=datetime.now(timezone.utc),
                processed_at=None,
                processing_error=None,
            )
        )

        return result.rowcount == 1


def recover_stale_documents(stale_after_minutes=30):
    """
    Reset documents stuck in processing beyond the specified timeout.

    Args:
        stale_after_minutes: Time after which a processing document
                            is considered stale.

    Returns:
        Number of documents recovered.
    """

    if stale_after_minutes <= 0:
        raise ValueError(
            "stale_after_minutes must be greater than 0."
        )

    cutoff_time = datetime.now(timezone.utc) - timedelta(
        minutes=stale_after_minutes
    )

    with SessionLocal.begin() as session:

        result = session.execute(
            update(Document)
            .where(
                Document.processing_status == "processing",
                Document.processing_started_at.is_not(None),
                Document.processing_started_at < cutoff_time,
            )
            .values(
                processing_status="pending",
                processing_started_at=None,
                processed_at=None,
                processing_error=(
                    f"Recovered after being stuck in processing "
                    f"for more than {stale_after_minutes} minutes."
                ),
            )
        )

        recovered_count = result.rowcount

    print(f"Stale documents recovered: {recovered_count}")

    return recovered_count
