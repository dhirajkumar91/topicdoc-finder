from pdf_processing.pdf_extractor import extract_headings_from_pdf


pdf_files = [
    "downloads/1112.3867v1.pdf",
    "downloads/1404.7766v1.pdf"
]


for pdf_path in pdf_files:

    headings = extract_headings_from_pdf(pdf_path)

    print("\n" + "=" * 70)
    print("PDF:", pdf_path)
    print("Total headings:", len(headings))
    print("=" * 70)

    for heading in headings:

        print(
            f"Page {heading['page_number']}: "
            f"{heading['text']}"
        )