
from pdf_processing.pdf_extractor import extract_headings_from_pdf


pdf_path = "downloads/1112.3867v1.pdf"

headings = extract_headings_from_pdf(pdf_path)

print("Total headings detected:", len(headings))

for heading in headings:

    print("\n" + "=" * 60)

    print("Page:", heading["page_number"])
    print("Heading:", heading["text"])
    print("Font size:", heading["font_size"])
    print("Bold:", heading["is_bold"])
