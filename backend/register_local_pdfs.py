from pathlib import Path

from database.document_repository import save_document_metadata


DOWNLOAD_DIR = Path("downloads")


def register_local_pdfs():

    pdf_files = sorted(DOWNLOAD_DIR.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found.")
        return

    registered = 0
    duplicates = 0
    failed = 0

    print(f"Found {len(pdf_files)} PDFs.\n")

    for pdf_file in pdf_files:

        try:

            result = save_document_metadata(
                file_path=pdf_file,
                pdf_url=pdf_file.resolve().as_uri(),
                source_name="local",
                title=None,
                abstract=None,
                authors=None,
                published_date=None,
                external_id=pdf_file.stem,
                source_url=None,
                matched_keywords=None,
            )

            if result["status"] == "saved":

                registered += 1

                print(
                    f"[REGISTERED] {pdf_file.name}"
                )

            elif result["status"] == "duplicate":

                duplicates += 1

                print(
                    f"[DUPLICATE] {pdf_file.name}"
                )

        except Exception as error:

            failed += 1

            print(
                f"[FAILED] {pdf_file.name}: {error}"
            )

    print("\n" + "=" * 50)
    print("REGISTRATION SUMMARY")
    print("=" * 50)
    print(f"Newly registered: {registered}")
    print(f"Already registered: {duplicates}")
    print(f"Failed: {failed}")
    print(f"Total scanned: {len(pdf_files)}")


if __name__ == "__main__":
    register_local_pdfs()