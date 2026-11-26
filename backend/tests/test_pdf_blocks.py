
from pdf_processing.pdf_extractor import extract_text_blocks_from_pdf

pdf_path = "downloads/1112.3867v1.pdf"

blocks = extract_text_blocks_from_pdf(pdf_path)

print("Total text blocks:", len(blocks))

for block in blocks[:10]:

    print("\n" + "=" * 60)

    print("Page:", block["page_number"])
    print("Block:", block["block_number"])
    print("Text:", block["text"][:200])
    print("Coordinates:", block["coordinates"])
