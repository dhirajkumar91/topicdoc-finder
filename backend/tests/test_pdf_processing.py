from pprint import pprint

from pdf_processing.pdf_extractor import process_pdf


pdf_path = "downloads/1404.7766v1.pdf"

result = process_pdf(pdf_path)


print("\n========== PDF PROCESSING SUMMARY ==========")

print("File:", result["file_name"])

print("\nStatistics:")
pprint(result["statistics"])


print("\n========== FIRST PAGE TEXT ==========")

print(result["pages"][0]["text"][:1000])


print("\n========== FIRST 5 TEXT BLOCKS ==========")

pprint(result["text_blocks"][:5])


print("\n========== FIRST 5 FORMATTED SPANS ==========")

pprint(result["formatted_spans"][:5])


print("\n========== DETECTED HEADINGS ==========")

for heading in result["headings"]:
    print(
        f"Page {heading['page_number']}: "
        f"{heading['text']}"
    )


print("\n========== DETECTED TABLES ==========")

print("Total tables:", result["statistics"]["total_tables"])