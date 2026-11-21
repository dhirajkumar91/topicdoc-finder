from datetime import datetime, timezone

from pdf_processing.pdf_extractor import process_pdf

from chunking.text_chunker import (
    split_into_sections,
    chunk_sections,
)

from embeddings.batch_processor import (
    generate_embeddings_in_batches,
)

from database.chunk_repository import (
    save_document_chunks,
)

from database.document_repository import (
    get_pending_documents,
    update_document_processing_status,
    claim_document_for_processing,
)


def process_document(document_id, file_path):
    """
    Process a single PDF document.

    Pipeline:
    1. Mark document as processing.
    2. Extract PDF information.
    3. Split text into sections.
    4. Generate chunks.
    5. Generate embeddings.
    6. Save chunks to the database.
    7. Mark document as completed.

    If processing fails, mark the document as failed.
    """

    print(f"\nProcessing document: {file_path}")

    try:
        # Step 1: Atomically claim the document.
        claimed = claim_document_for_processing(document_id)

        if not claimed:

            print(
                "Document could not be claimed. "
                "It may already be processing or no longer pending."
            )

            return {
                "document_id": str(document_id),
                "file_path": str(file_path),
                "status": "skipped",
                "chunk_count": 0,
            }

        # Step 2: Extract PDF content.
        extracted_data = process_pdf(file_path)

        pages = extracted_data["pages"]
        headings = extracted_data["headings"]

        print(f"Pages extracted: {len(pages)}")
        print(f"Headings detected: {len(headings)}")

        # Step 3: Split extracted content into sections.
        sections = split_into_sections(
            pages=pages,
            headings=headings,
        )

        print(f"Sections generated: {len(sections)}")

        # Step 4: Generate chunks.
        chunks = chunk_sections(sections)

        print(f"Chunks generated: {len(chunks)}")

        # Sanitize chunk content before embedding generation.
        sanitized_chunks = 0

        for chunk in chunks:

            original_content = chunk["content"]

            cleaned_content = original_content.replace("\x00", "")

            if cleaned_content != original_content:

                sanitized_chunks += 1

                chunk["content"] = cleaned_content
                chunk["character_count"] = len(cleaned_content)

        print(f"Chunks sanitized: {sanitized_chunks}")

        # Step 5: Generate embeddings.
        embedding_result = generate_embeddings_in_batches(
            chunks=chunks,
        )

        successful_embeddings = embedding_result["results"]
        failures = embedding_result["failures"]

        print(
            f"Successful embeddings: "
            f"{len(successful_embeddings)}"
        )

        print(
            f"Failed embeddings: {len(failures)}"
        )

        # Do not replace existing chunks if embedding
        # generation was incomplete.
        if failures or len(successful_embeddings) != len(chunks):
            raise RuntimeError(
                f"Embedding generation incomplete: "
                f"{len(failures)} chunk failures."
            )

        # Step 6: Store the complete chunk set.
        saved_chunk_count = save_document_chunks(
            document_id=document_id,
            chunks=successful_embeddings,
        )

        print(f"Chunks saved: {saved_chunk_count}")

        # Step 7: Mark document as completed.
        update_document_processing_status(
            document_id=document_id,
            status="completed",
            chunk_count=saved_chunk_count,
            processed_at=datetime.now(timezone.utc),
            processing_error=None,
        )

        print("Document processing completed successfully.")

        return {
            "document_id": str(document_id),
            "file_path": str(file_path),
            "status": "completed",
            "chunk_count": saved_chunk_count,
            "sections_count": len(sections),
            "extracted_data": extracted_data,
            "sections": sections,
            "chunks": successful_embeddings,
        }

    except Exception as error:

        print(f"Processing failed: {error}")

        update_document_processing_status(
            document_id=document_id,
            status="failed",
            processed_at=None,
            processing_error=str(error),
        )

        raise