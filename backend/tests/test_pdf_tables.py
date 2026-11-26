from pdf_processing.pdf_extractor import extract_tables_from_pdf

pdf_path = "downloads/1404.7766v1.pdf"

tables = extract_tables_from_pdf(pdf_path)

print("\nTotal tables detected:", len(tables))

for table in tables:

    print("\n" + "=" * 60)
    print("PAGE:", table["page_number"])
    print("TABLE:", table["table_number"])
    print("ROWS:", table["row_count"])
    print("COLUMNS:", table["column_count"])
    print("=" * 60)

    print("\nNormalized table data:")

    for row in table["data"]:
        print(row)

    print("\nOriginal table data:")

    for row in table["original_data"]:
        print(row)