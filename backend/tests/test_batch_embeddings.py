
from pdf_processing.pdf_extractor import process_pdf

from database.chunk_repository import save_document_chunks

from chunking.text_chunker import (
    split_into_sections,
    chunk_sections,
)

from embeddings.batch_processor import (
    generate_embeddings_in_batches,
)


PDF_PATH = "downloads/1404.7766v1.pdf"

DOCUMENT_ID = "5279860a-c502-4901-abf8-2266d633a9e7"


def main():

    print("Processing PDF...")

    processed_data = process_pdf(PDF_PATH)

    pages = processed_data["pages"]
    headings = processed_data["headings"]

    sections = split_into_sections(
        pages,
        headings,
    )

    chunks = chunk_sections(
        sections,
        chunk_size=1200,
        overlap=200,
    )

    print("\nTotal chunks:", len(chunks))

    print("\nGenerating embeddings...")

    batch_output = generate_embeddings_in_batches(
        chunks,
        batch_size=10,
        max_retries=3,
    )

    results = batch_output["results"]
    failures = batch_output["failures"]

    print("\n========== EMBEDDING SUMMARY ==========")

    print("Total chunks:", len(chunks))
    print("Successful embeddings:", len(results))
    print("Failed embeddings:", len(failures))

    if results:

        print(
            "Embedding dimensions:",
            len(results[0]["embedding"]),
        )

        print(
            "First chunk index:",
            results[0]["chunk_index"],
        )

        print(
            "First chunk section:",
            results[0]["section_title"],
        )

        print(
            "First five embedding values:",
            results[0]["embedding"][:5],
        )

    if failures:

        print("\n========== FAILED CHUNKS ==========")

        for failure in failures:
            print(failure)

    # Save embeddings only if every chunk was processed successfully.
    if not failures and len(results) == len(chunks):

        print("\nSaving chunks and embeddings to PostgreSQL...")

        saved_count = save_document_chunks(
            document_id=DOCUMENT_ID,
            chunks=results,
        )

        print("\n========== DATABASE STORAGE SUMMARY ==========")
        print("Document ID:", DOCUMENT_ID)
        print("Chunks saved:", saved_count)

    else:

        print(
            "\nSkipping database storage because "
            "some embeddings failed."
        )


if __name__ == "__main__":
    main()
