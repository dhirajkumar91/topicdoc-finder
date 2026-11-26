
import pymupdf

pdf_path = (
    r"downloads\Covid-_19_Confirmed,_Recovered,_Death_Cases_In_India_"
    r"Ratio_Analysis_httpsopenalex.orgW4206782812.pdf"
)

with pymupdf.open(pdf_path) as pdf:

    page = pdf[1]  # Page 2
    tables = page.find_tables()

    table = tables.tables[0]

    extracted = table.extract()

    print("TABLE 2 WORD-LEVEL GEOMETRY")
    print("Table bounding box:", table.bbox)

    # Inspect the header and first four data rows.
    for row_index in range(5):

        cell = table.rows[row_index].cells[1]

        if cell is None:
            continue

        x0, y0, x1, y1 = cell

        print(f"\nROW {row_index}")
        print("Cell bounding box:", cell)
        print("Extracted cell:", extracted[row_index][1])

        words = page.get_text("words")

        for word in words:

            wx0, wy0, wx1, wy1 = word[:4]

            # Check whether the word belongs to this cell.
            if (
                wx0 >= x0 - 1
                and wx1 <= x1 + 1
                and wy0 >= y0 - 1
                and wy1 <= y1 + 1
            ):
                print({
                    "word": word[4],
                    "x0": round(wx0, 2),
                    "x1": round(wx1, 2),
                    "y0": round(wy0, 2),
                    "y1": round(wy1, 2),
                })
