from database.document_repository import (
    get_pending_documents,
    recover_stale_documents,
)

from document_processor import process_document


def process_pending_documents(limit=10):
    """
    Recover stale documents and process pending documents.

    Args:
        limit: Maximum number of pending documents to process.

    Returns:
        Dictionary containing processing statistics.
    """

    # Step 1: Recover documents stuck in processing.
    print("\n========== STALE DOCUMENT RECOVERY ==========")

    recovered_documents = recover_stale_documents(
        stale_after_minutes=30
    )

    print(f"Documents recovered: {recovered_documents}")

    # Step 2: Retrieve pending documents.
    documents = get_pending_documents(limit=limit)

    if not documents:
        print("\nNo pending documents found.")

        return {
            "total": 0,
            "completed": 0,
            "failed": 0,
            "skipped": 0,
        }

    total_documents = len(documents)
    completed_documents = 0
    failed_documents = 0
    skipped_documents = 0

    print(f"\nPending documents found: {total_documents}")

    # Step 3: Process each pending document.
    for index, document in enumerate(documents, start=1):

        print(f"\n{'=' * 60}")

        print(
            f"Document {index}/{total_documents}: "
            f"{document['original_filename']}"
        )

        print(f"{'=' * 60}")

        try:

            result = process_document(
                document_id=document["document_id"],
                file_path=document["file_path"],
            )

            if result["status"] == "completed":
                completed_documents += 1

            elif result["status"] == "skipped":
                skipped_documents += 1

        except Exception as error:

            failed_documents += 1

            print(
                f"Failed to process "
                f"{document['original_filename']}: {error}"
            )

            print("Moving to the next document.")

    # Step 4: Display processing summary.
    print("\n========== PROCESSING SUMMARY ==========")

    print(f"Total documents: {total_documents}")
    print(f"Recovered documents: {recovered_documents}")
    print(f"Completed: {completed_documents}")
    print(f"Failed: {failed_documents}")
    print(f"Skipped: {skipped_documents}")

    return {
        "total": total_documents,
        "completed": completed_documents,
        "failed": failed_documents,
        "skipped": skipped_documents,
    }


if __name__ == "__main__":

    process_pending_documents(limit=10)