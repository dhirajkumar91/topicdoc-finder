
from pdf_processing.pdf_extractor import extract_text_with_formatting

pdf_path = "downloads/1112.3867v1.pdf"

spans = extract_text_with_formatting(pdf_path)

print("Total text spans:", len(spans))

for span in spans[:20]:

    print("\n" + "=" * 60)

    print("Page:", span["page_number"])
    print("Text:", span["text"])
    print("Font:", span["font_name"])
    print("Font size:", span["font_size"])
    print("Bold:", span["is_bold"])
    print("Italic:", span["is_italic"])
    print("Coordinates:", span["coordinates"])
