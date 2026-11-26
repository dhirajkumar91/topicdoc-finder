
import re


# Configurable top-level headings.
# These headings start a new parent section.
TOP_LEVEL_HEADINGS = {
    "abstract",
    "introduction",
    "results",
    "discussion",
    "material and methods",
    "materials and methods",
    "methods",
    "methodology",
    "acknowledgements",
    "acknowledgments",
    "references",
    "bibliography",
}


def normalize_heading(text):
    """
    Normalize heading text for reliable comparison.
    """
    return re.sub(r"\s+", " ", text).strip().lower()


def split_into_sections(pages, headings):
    """
    Split PDF content into non-empty sections while preserving
    parent-child heading relationships.

    Preserves:
    - Section titles
    - Parent section titles
    - Page numbers
    - Section content

    Ignores:
    - Content before the first detected heading
    - Standalone page numbers
    - Empty sections
    """

    sections = []

    heading_lookup = {
        normalize_heading(heading["text"]): heading["text"]
        for heading in headings
    }

    current_section_title = None
    current_parent_title = None
    active_parent_title = None

    current_page_start = None
    current_page_end = None
    current_content = []

    def save_section():
        """
        Save the current section only when it contains text.
        """

        if current_section_title is None:
            return

        content = "\n".join(current_content).strip()

        if not content:
            return

        sections.append({
            "section_title": current_section_title,
            "parent_section_title": current_parent_title,
            "page_start": current_page_start,
            "page_end": current_page_end,
            "content": content,
        })

    for page in pages:

        page_number = page["page_number"]

        for line in page["text"].splitlines():

            line = line.strip()

            if not line:
                continue

            # Ignore standalone page numbers.
            if re.fullmatch(r"\d{1,4}", line):
                continue

            normalized_line = normalize_heading(line)

            # Check whether the line is a detected heading.
            if normalized_line in heading_lookup:

                # Save the previous content-bearing section.
                save_section()

                current_section_title = heading_lookup[
                    normalized_line
                ]

                # A top-level heading starts a new parent section.
                if normalized_line in TOP_LEVEL_HEADINGS:

                    active_parent_title = current_section_title
                    current_parent_title = None

                else:
                    # Keep the current parent for all its subsections.
                    current_parent_title = active_parent_title

                current_page_start = page_number
                current_page_end = page_number
                current_content = []

                continue

            # Ignore front matter before the first heading.
            if current_section_title is None:
                continue

            current_content.append(line)
            current_page_end = page_number

    # Save the final section.
    save_section()

    return sections




def find_chunk_boundary(text, start, max_end):
    """
    Find a natural chunk boundary.

    Preference:
    1. Paragraph boundary
    2. Sentence boundary
    3. Word boundary
    4. Hard character boundary
    """

    if max_end >= len(text):
        return len(text)

    minimum_end = start + int((max_end - start) * 0.70)

    # Prefer paragraph boundaries.
    boundary = text.rfind("\n\n", minimum_end, max_end)

    if boundary != -1:
        return boundary

    # Next, prefer sentence boundaries.
    sentence_matches = list(
        re.finditer(r"[.!?]\s+", text[minimum_end:max_end])
    )

    if sentence_matches:
        return minimum_end + sentence_matches[-1].end()

    # Next, prefer word boundaries.
    boundary = text.rfind(" ", minimum_end, max_end)

    if boundary != -1:
        return boundary

    return max_end


def chunk_text(text, chunk_size=1200, overlap=200):
    """
    Split text into overlapping chunks.

    Tries to preserve paragraph, sentence, and word boundaries,
    including when calculating the next chunk's starting position.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if overlap < 0:
        raise ValueError("overlap cannot be negative.")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size.")

    text = text.strip()

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):

        max_end = min(start + chunk_size, len(text))

        end = find_chunk_boundary(text, start, max_end)

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        # Calculate the approximate next starting position.
        next_start = max(start + 1, end - overlap)

        # Move forward to the next word boundary.
        while next_start < end and not text[next_start - 1].isspace():
            next_start += 1

        if next_start >= end:
            next_start = end

        start = next_start

    return chunks


def chunk_sections(
    sections,
    chunk_size=1200,
    overlap=200,
    include_references=False,
):
    """
    Convert extracted sections into smaller overlapping chunks.

    Each chunk retains:
    - Chunk index
    - Section title
    - Parent section title
    - Page range
    - Text content
    """

    document_chunks = []

    for section in sections:

        section_title = section["section_title"]

        # Keep bibliography content separate from semantic chunks.
        if (
            not include_references
            and normalize_heading(section_title)
            in {"references", "bibliography"}
        ):
            continue

        text_chunks = chunk_text(
            section["content"],
            chunk_size=chunk_size,
            overlap=overlap,
        )

        for chunk_number, content in enumerate(
            text_chunks,
            start=1,
        ):

            document_chunks.append({
                "chunk_index": len(document_chunks) + 1,
                "section_chunk_index": chunk_number,
                "section_title": section_title,
                "parent_section_title": section["parent_section_title"],
                "page_start": section["page_start"],
                "page_end": section["page_end"],
                "content": content,
                "character_count": len(content),
            })

    return document_chunks
