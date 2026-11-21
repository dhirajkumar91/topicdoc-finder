from pdf_processing.pdf_extractor import process_pdf
from chunking.text_chunker import split_into_sections, chunk_sections


file_path = "downloads/0903.1704v1.pdf"

extracted_data = process_pdf(file_path)

sections = split_into_sections(
    pages=extracted_data["pages"],
    headings=extracted_data["headings"],
)

chunks = chunk_sections(sections)

print(f"Total chunks: {len(chunks)}")

for chunk in chunks:

    content = chunk["content"]
    section_title = chunk["section_title"]

    content_null_count = content.count("\x00")
    title_null_count = section_title.count("\x00") if section_title else 0

    if content_null_count or title_null_count:

        print("\nProblem detected!")

        print("Chunk index:", chunk["chunk_index"])
        print("Content NUL bytes:", content_null_count)
        print("Title NUL bytes:", title_null_count)

        if content_null_count:
            print("Content preview:", repr(content[:300]))

        if title_null_count:
            print("Section title:", repr(section_title))