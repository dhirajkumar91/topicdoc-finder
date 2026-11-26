
import json
from pathlib import Path

from pdf_processing.pdf_extractor import process_pdf


PDF_PATH = Path("downloads/1905.04749v2.pdf")
OUTPUT_PATH = Path("table_extraction_test_output.json")

EXPECTED_TABLES = {
    3: {"rows": 8, "columns": 14},
    4: {"rows": 6, "columns": 13},
    5: {"rows": 5, "columns": 13},
}


def main():
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH.resolve()}")

    print("=" * 75)
    print("TOPICDOC FINDER - PDF TABLE EXTRACTION TEST")
    print("=" * 75)

    result = process_pdf(PDF_PATH)
    tables = result.get("tables", [])

    print(f"\nPDF: {PDF_PATH}")
    print(f"Total pages: {result.get('total_pages')}")
    print(f"Total extracted tables: {len(tables)}")

    all_passed = True
    test_results = {}

    for table_number, expected in EXPECTED_TABLES.items():

        matches = [
            table for table in tables
            if table.get("table_number") == table_number
        ]

        print("\n" + "-" * 75)
        print(f"TABLE {table_number}")
        print("-" * 75)

        if not matches:
            print("[FAIL] Table not found.")
            all_passed = False
            test_results[table_number] = {
                "status": "FAILED",
                "reason": "Table not found"
            }
            continue

        table = matches[0]

        data = table.get("data", [])
        headers = table.get("column_headers") or []
        row_count = len(data)
        column_count = table.get("column_count", 0)

        expected_rows = expected["rows"]
        expected_columns = expected["columns"]

        # Validate row and column counts.
        rows_valid = row_count == expected_rows
        columns_valid = column_count == expected_columns

        # Validate that every row has the expected number of cells.
        cells_valid = all(
            len(row) == expected_columns
            for row in data
        )

        # Tables 3, 4 and 5 contain 12 metric values per row.
        metric_start_index = 2 if table_number == 3 else 1

        metrics_valid = all(
            len(row[metric_start_index:]) == 12
            and all(
                value not in (None, "")
                for value in row[metric_start_index:]
            )
            for row in data
        )

        extraction_method = table.get("extraction_method")
        confidence = table.get("extraction_confidence")

        passed = (
            rows_valid
            and columns_valid
            and cells_valid
            and metrics_valid
            and extraction_method == "horizontal_layout_reconstruction"
        )

        if not passed:
            all_passed = False

        print(f"Page: {table.get('page_number')}")
        print(f"Title: {table.get('table_title')}")
        print(f"Extraction method: {extraction_method}")
        print(f"Confidence: {confidence}")

        print(f"\nExpected rows: {expected_rows}")
        print(f"Actual rows:   {row_count}")
        print(f"Expected columns: {expected_columns}")
        print(f"Actual columns:   {column_count}")

        print(f"\nRows valid:    {rows_valid}")
        print(f"Columns valid: {columns_valid}")
        print(f"Cells valid:   {cells_valid}")
        print(f"Metrics valid: {metrics_valid}")

        print("\nColumn headers:")
        print(headers)

        print("\nExtracted table data:")

        for index, row in enumerate(data, start=1):
            print(f"\nRow {index}:")
            print(json.dumps(row, indent=2, ensure_ascii=False))

        print("\nResult:", "PASS" if passed else "FAIL")

        test_results[table_number] = {
            "status": "PASSED" if passed else "FAILED",
            "page_number": table.get("page_number"),
            "table_title": table.get("table_title"),
            "extraction_method": extraction_method,
            "extraction_confidence": confidence,
            "expected_rows": expected_rows,
            "actual_rows": row_count,
            "expected_columns": expected_columns,
            "actual_columns": column_count,
            "rows_valid": rows_valid,
            "columns_valid": columns_valid,
            "cells_valid": cells_valid,
            "metrics_valid": metrics_valid,
            "column_headers": headers,
            "data": data,
            "validation": table.get("validation"),
        }

    # Include Table 6 as a diagnostic, without making it a required test.
    table_6 = [
        table for table in tables
        if table.get("table_number") == 6
    ]

    print("\n" + "=" * 75)
    print("TABLE 6 - ROTATED TABLE DIAGNOSTIC")
    print("=" * 75)

    if table_6:
        for table in table_6:
            print(f"Page: {table.get('page_number')}")
            print(f"Rows: {table.get('row_count')}")
            print(f"Columns: {table.get('column_count')}")
            print(f"Method: {table.get('extraction_method')}")
            print(f"Confidence: {table.get('extraction_confidence')}")
    else:
        print("Table 6 was not detected in this extraction run.")

    output = {
        "file_name": result.get("file_name"),
        "total_pages": result.get("total_pages"),
        "total_tables": len(tables),
        "test_results": test_results,
    }

    OUTPUT_PATH.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\n" + "=" * 75)
    print("FINAL TEST SUMMARY")
    print("=" * 75)

    for table_number, test in test_results.items():
        print(f"Table {table_number}: {test['status']}")

    print(f"\nOverall result: {'PASS' if all_passed else 'FAIL'}")
    print(f"Detailed output saved to: {OUTPUT_PATH.resolve()}")


if __name__ == "__main__":
    main()
