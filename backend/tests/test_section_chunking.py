from pdf_processing.pdf_extractor import (
    extract_text_from_pdf,
    extract_headings_from_pdf
)

from chunking.text_chunker import (
    split_into_sections,
    normalize_heading,
    chunk_sections
)


pdf_path = "downloads/1404.7766v1.pdf"


# Extract PDF content
pages = extract_text_from_pdf(pdf_path)

headings = extract_headings_from_pdf(pdf_path)


print("\n========== HEADING LEVEL DIAGNOSTICS ==========")

for heading in headings:
    print(
        f"Page: {heading['page_number']} | "
        f"Font size: {heading['font_size']:.2f} | "
        f"Bold: {heading['is_bold']} | "
        f"Heading: {heading['text']}"
    )


print("\n========== DETECTED HEADING ORDER ==========")

for heading in headings:
    print(
        f"Page: {heading['page_number']} | "
        f"Heading: {heading['text']}"
    )


print("\n========== HEADING MATCH DIAGNOSTICS ==========")

page_lines = {
    normalize_heading(line)
    for page in pages
    for line in page["text"].splitlines()
    if line.strip()
}

for heading in headings:

    heading_text = heading["text"]

    if normalize_heading(heading_text) not in page_lines:
        print("UNMATCHED HEADING:", repr(heading_text))


# Split document into sections
sections = split_into_sections(pages, headings)


document_chunks = chunk_sections(
    sections,
    chunk_size=1200,
    overlap=200,
)


print("\n========== CHUNK VALIDATION ==========")

# Check maximum chunk size.
oversized_chunks = [
    chunk for chunk in document_chunks
    if chunk["character_count"] > 1200
]

print("Oversized chunks:", len(oversized_chunks))

# Check whether consecutive chunks in each section overlap.
overlap_checks = []

for previous, current in zip(document_chunks, document_chunks[1:]):

    if previous["section_title"] != current["section_title"]:
        continue

    previous_words = previous["content"].split()
    current_words = current["content"].split()

    overlap_found = False

    for size in range(min(50, len(previous_words), len(current_words)), 0, -1):
        if previous_words[-size:] == current_words[:size]:
            overlap_found = True
            break

    overlap_checks.append(overlap_found)

print("Section-level overlap checks:", len(overlap_checks))
print("Overlaps detected:", sum(overlap_checks))
print(
    "Missing overlaps:",
    len(overlap_checks) - sum(overlap_checks)
)

# Check chunk metadata.
invalid_metadata = [
    chunk for chunk in document_chunks
    if not chunk["content"].strip()
    or chunk["page_start"] > chunk["page_end"]
]

print("Chunks with invalid metadata:", len(invalid_metadata))

print("\n========== TEXT CHUNKING SUMMARY ==========")

print("Total sections:", len(sections))
print("Total chunks:", len(document_chunks))

if document_chunks:

    print(
        "Average chunk size:",
        round(
            sum(chunk["character_count"] for chunk in document_chunks)
            / len(document_chunks),
            2
        )
    )

    print(
        "Largest chunk:",
        max(chunk["character_count"] for chunk in document_chunks)
    )

    print(
        "Smallest chunk:",
        min(chunk["character_count"] for chunk in document_chunks)
    )

    for chunk in document_chunks[:5]:

        print("\n" + "=" * 70)
        print("Chunk index:", chunk["chunk_index"])
        print("Section:", chunk["section_title"])
        print("Parent:", chunk["parent_section_title"])
        print("Page range:", chunk["page_start"], "-", chunk["page_end"])
        print("Character count:", chunk["character_count"])
        print("\nContent preview:")
        print(chunk["content"][:400])


print("\n========== SECTION CHUNKING SUMMARY ==========")

print("Total sections:", len(sections))


for index, section in enumerate(sections, start=1):

    print("\n" + "=" * 70)
    print("Section:", index)
    print("Title:", section["section_title"])
    print("Parent section:", section["parent_section_title"])
    print("Starting page:", section["page_start"])
    print("Ending page:", section["page_end"])
    print("Content length:", len(section["content"]))
    print("\nContent preview:")
    print(section["content"][:500])