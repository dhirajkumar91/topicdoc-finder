
from pdf_processing.pdf_extractor import extract_text_from_pdf


pdf_path = "downloads/1112.3867v1.pdf"

pages = extract_text_from_pdf(pdf_path)

print("\nTotal pages extracted:", len(pages))

for page in pages:
    print("\n" + "=" * 60)
    print("PAGE:", page["page_number"])
    print("=" * 60)

    print(page["text"][:500])
