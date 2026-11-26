
from datetime import datetime, timezone

from pdf_processing.pdf_extractor import process_pdf

from chunking.text_chunker import (
    split_into_sections,
    chunk_sections,
)

from embeddings.batch_processor import (
    generate_embeddings_in_batches,
    generate_table_embeddings_in_batches,
)

from database.content_repository import save_document_content

from database.document_repository import (
    update_document_processing_status,
    claim_document_for_processing,
)


def process_document(document_id, file_path, progress_callback=None):
    """
    Process a single PDF document.

    Pipeline:
    1. Claim document.
    2. Extract PDF information, including tables.
    3. Split text into sections.
    4. Generate text chunks.
    5. Generate text chunk embeddings.
    6. Generate table embeddings.
    7. Save chunks and tables in one database transaction.
    8. Mark document as completed.

    Progress reporting is optional and does not affect
    processing if the callback fails.
    """

    print(f"\nProcessing document: {file_path}")

    def report_progress(stage, progress, details=None, **extra):
        if progress_callback is None:
            return

        payload = {
            "stage": stage,
            "progress_percent": progress,
            "details": details,
            **extra,
        }

        try:
            progress_callback(payload)
        except Exception as error:
            print(f"Progress callback failed: {error}")

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
                "table_count": 0,
            }

        report_progress(
            "PDF extraction",
            5,
            "Extracting pages, headings and tables",
        )

        # Step 2: Extract PDF content.
        extracted_data = process_pdf(file_path)

        pages = extracted_data["pages"]
        headings = extracted_data["headings"]
        tables = extracted_data.get("tables", [])

        print(f"Pages extracted: {len(pages)}")
        print(f"Headings detected: {len(headings)}")
        print(f"Tables extracted: {len(tables)}")

        report_progress(
            "PDF extraction",
            10,
            (
                f"Extracted {len(pages)} pages, "
                f"{len(headings)} headings and "
                f"{len(tables)} tables"
            ),
        )

        # Step 3: Split extracted content into sections.
        sections = split_into_sections(
            pages=pages,
            headings=headings,
        )

        print(f"Sections generated: {len(sections)}")

        report_progress(
            "Section generation",
            20,
            f"Generated {len(sections)} sections",
        )

        # Step 4: Generate text chunks.
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

        report_progress(
            "Chunk generation",
            30,
            f"Generated {len(chunks)} chunks",
            total_chunks=len(chunks),
        )

        # Step 5: Generate text chunk embeddings.
        def embedding_progress(progress):
            completed = progress["completed_chunks"]
            total = progress["total_chunks"]

            embedding_percentage = (
                completed / total * 100
                if total
                else 100
            )

            # Text embedding stage occupies 30% to 65%.
            overall_percentage = 30 + (
                embedding_percentage * 0.35
            )

            report_progress(
                "Embedding generation",
                round(overall_percentage, 2),
                (
                    f"Generated embeddings for "
                    f"{completed}/{total} chunks"
                ),
                completed_chunks=completed,
                total_chunks=total,
                successful_chunks=progress["successful_chunks"],
                failed_chunks=progress["failed_chunks"],
                current_batch=progress["current_batch"],
                total_batches=progress["total_batches"],
            )

        embedding_result = generate_embeddings_in_batches(
            chunks=chunks,
            progress_callback=embedding_progress,
        )

        successful_embeddings = embedding_result["results"]
        failures = embedding_result["failures"]

        print(
            f"Successful chunk embeddings: "
            f"{len(successful_embeddings)}"
        )

        print(f"Failed chunk embeddings: {len(failures)}")

        # Do not save incomplete chunk embeddings.
        if failures or len(successful_embeddings) != len(chunks):
            raise RuntimeError(
                f"Chunk embedding generation incomplete: "
                f"{len(failures)} chunk failures."
            )

        # Step 6: Generate table embeddings.
        def table_embedding_progress(progress):
            completed = progress["completed_chunks"]
            total = progress["total_chunks"]

            embedding_percentage = (
                completed / total * 100
                if total
                else 100
            )

            # Table embedding stage occupies 65% to 85%.
            overall_percentage = 65 + (
                embedding_percentage * 0.20
            )

            report_progress(
                "Table embedding generation",
                round(overall_percentage, 2),
                (
                    f"Generated table embeddings for "
                    f"{completed}/{total} tables"
                ),
                completed_tables=completed,
                total_tables=total,
                successful_tables=progress["successful_chunks"],
                failed_tables=progress["failed_chunks"],
                current_batch=progress["current_batch"],
                total_batches=progress["total_batches"],
            )

        table_embedding_result = generate_table_embeddings_in_batches(
            tables=tables,
            progress_callback=table_embedding_progress,
        )

        embedded_tables = table_embedding_result["results"]
        table_failures = table_embedding_result["failures"]

        print(
            f"Successful table embeddings: "
            f"{len(embedded_tables)}"
        )

        print(f"Failed table embeddings: {len(table_failures)}")

        # Do not save if any table embedding failed.
        if (
            table_failures
            or len(embedded_tables) != len(tables)
        ):
            raise RuntimeError(
                f"Table embedding generation incomplete: "
                f"{len(table_failures)} table failures."
            )

        # Step 7: Save chunks and tables together.
        # Both record types are replaced in one database transaction.
        report_progress(
            "Database storage",
            90,
            (
                f"Saving {len(successful_embeddings)} chunks "
                f"and {len(embedded_tables)} tables"
            ),
        )

        save_result = save_document_content(
            document_id=document_id,
            chunks=successful_embeddings,
            tables=embedded_tables,
        )

        saved_chunk_count = save_result["chunk_count"]
        saved_table_count = save_result["table_count"]

        print(f"Chunks saved: {saved_chunk_count}")
        print(f"Tables saved: {saved_table_count}")

        report_progress(
            "Database storage",
            95,
            (
                f"Saved {saved_chunk_count} chunks and "
                f"{saved_table_count} tables"
            ),
            chunk_count=saved_chunk_count,
            table_count=saved_table_count,
        )

        # Step 8: Mark document as completed.
        update_document_processing_status(
            document_id=document_id,
            status="completed",
            chunk_count=saved_chunk_count,
            processed_at=datetime.now(timezone.utc),
            processing_error=None,
        )

        report_progress(
            "Completed",
            100,
            (
                f"Successfully processed {saved_chunk_count} chunks "
                f"and {saved_table_count} tables"
            ),
            chunk_count=saved_chunk_count,
            table_count=saved_table_count,
        )

        print("Document processing completed successfully.")

        return {
            "document_id": str(document_id),
            "file_path": str(file_path),
            "status": "completed",
            "chunk_count": saved_chunk_count,
            "table_count": saved_table_count,
            "sections_count": len(sections),
            "extracted_data": extracted_data,
            "sections": sections,
            "chunks": successful_embeddings,
            "tables": embedded_tables,
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
