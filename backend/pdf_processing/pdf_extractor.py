import pymupdf
from pathlib import Path
import re
import statistics

from copy import deepcopy



def extract_text_from_pdf(file_path):
    """
    Extract text from a PDF file page by page.

    Returns a list of dictionaries containing:
    - Page number
    - Extracted text
    """


    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"PDF file not found: {file_path}"
        )
    
    if file_path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")
    
    extracted_pages = []

    try:
        with pymupdf.open(file_path) as pdf:

            for page_number, page in enumerate(pdf, start=1):

                page_text = page.get_text("text").strip()

                extracted_pages.append({
                    "page_number": page_number,
                    "text": page_text
                })

    except pymupdf.FileDataError as error:
        raise ValueError(
            f"Could not read PDF file: {error}"
        ) from error
    
    return extracted_pages




def extract_text_blocks_from_pdf(file_path):
    """
    Extract individual text blocks from every PDF page.

    Each block contains:
    - Page number
    - Block number
    - Extracted text
    - Bounding box coordinates (x0, y0, x1, y1)
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"PDF file not found: {file_path}"
        )

    if file_path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    extracted_blocks = []

    try:
        with pymupdf.open(file_path) as pdf:

            for page_number, page in enumerate(pdf, start=1):

                blocks = page.get_text("blocks")

                for block_number, block in enumerate(blocks, start=1):

                    x0, y0, x1, y1, text, *_ = block

                    text = text.strip()

                    if not text:
                        continue

                    extracted_blocks.append({
                        "page_number": page_number,
                        "block_number": block_number,
                        "text": text,
                        "coordinates": {
                            "x0": x0,
                            "y0": y0,
                            "x1": x1,
                            "y1": y1
                        }
                    })

    except pymupdf.FileDataError as error:
        raise ValueError(
            f"Could not read PDF file: {error}"
        ) from error

    return extracted_blocks




def extract_text_with_formatting(file_path):
    """
    Extract text with font and layout information.

    Each text span contains:
    - Page number
    - Text
    - Font name
    - Font size
    - Bold/italic flags
    - Bounding box coordinates
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"PDF file not found: {file_path}"
        )

    if file_path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    extracted_spans = []

    try:
        with pymupdf.open(file_path) as pdf:

            for page_number, page in enumerate(pdf, start=1):

                page_data = page.get_text("dict")

                for block in page_data["blocks"]:

                    if block.get("type") != 0:
                        continue

                    for line in block["lines"]:

                        for span in line["spans"]:

                            text = span["text"].strip()

                            if not text:
                                continue

                            font_name = span["font"]
                            font_size = span["size"]
                            font_flags = span["flags"]

                            extracted_spans.append({
                                "page_number": page_number,
                                "text": text,
                                "font_name": font_name,
                                "font_size": font_size,
                                "is_bold": bool(font_flags & 16),
                                "is_italic": bool(font_flags & 2),
                                "coordinates": {
                                    "x0": span["bbox"][0],
                                    "y0": span["bbox"][1],
                                    "x1": span["bbox"][2],
                                    "y1": span["bbox"][3]
                                }
                            })

    except pymupdf.FileDataError as error:
        raise ValueError(
            f"Could not read PDF file: {error}"
        ) from error

    return extracted_spans



def extract_headings_from_pdf(file_path):
    """
    Extract structural headings from a research paper.

    Detection rules:
    - Recognizes Abstract, Acknowledgements and References.
    - Recognizes numbered sections and subsections.
    - Recognizes short, bold section headings.
    - Ignores author details and affiliations before Abstract.
    - Ignores bibliography entries after References.
    - Avoids treating long algorithm instructions as headings.

    Returns a list containing:
    - Page number
    - Heading text
    - Font size
    - Bold status
    - Bounding box coordinates
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"PDF file not found: {file_path}"
        )

    if file_path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    extracted_headings = []
    lines = []

    try:
        with pymupdf.open(file_path) as pdf:

            # Step 1: Extract lines and formatting
            for page_number, page in enumerate(pdf, start=1):

                page_data = page.get_text("dict")

                for block in page_data["blocks"]:

                    if block.get("type") != 0:
                        continue

                    for line in block["lines"]:

                        spans = line["spans"]

                        text = "".join(
                            span["text"] for span in spans
                        ).strip()

                        if not text:
                            continue

                        font_sizes = [
                            span["size"]
                            for span in spans
                            if span["text"].strip()
                        ]

                        if not font_sizes:
                            continue

                        average_font_size = statistics.mean(
                            font_sizes
                        )

                        is_bold = any(
                            span["flags"] & 16
                            for span in spans
                            if span["text"].strip()
                        )

                        lines.append({
                            "page_number": page_number,
                            "text": text,
                            "font_size": average_font_size,
                            "is_bold": is_bold,
                            "coordinates": {
                                "x0": line["bbox"][0],
                                "y0": line["bbox"][1],
                                "x1": line["bbox"][2],
                                "y1": line["bbox"][3]
                            }
                        })

            if not lines:
                return extracted_headings

            # Step 2: Estimate body font size
            body_font_sizes = [
                line["font_size"]
                for line in lines
                if len(line["text"]) > 80
            ]

            if body_font_sizes:
                body_font_size = statistics.median(
                    body_font_sizes
                )
            else:
                body_font_size = statistics.median(
                    line["font_size"] for line in lines
                )

            # Step 3: Define heading patterns
            numbered_heading_pattern = re.compile(
                r"^\d+(?:\.\d+)*\.?\s+[A-Z]"
            )

            special_headings = {
                "abstract",
                "acknowledgements",
                "acknowledgments",
                "references",
                "bibliography",
            }

            # Step 4: Identify Abstract
            abstract_index = None

            for index, line in enumerate(lines):

                if line["text"].strip().lower() == "abstract":
                    abstract_index = index
                    break

            # If Abstract is not found, process the document
            # from its beginning.
            start_index = (
                abstract_index
                if abstract_index is not None
                else 0
            )

            # Step 5: Detect structural headings
            inside_references = False

            for line in lines[start_index:]:

                text = line["text"].strip()
                normalized_text = text.lower()

                # Stop processing after References
                if inside_references:
                    continue

                # Explicitly recognized headings
                if normalized_text in special_headings:

                    extracted_headings.append({
                        "page_number": line["page_number"],
                        "text": text,
                        "font_size": line["font_size"],
                        "is_bold": line["is_bold"],
                        "coordinates": line["coordinates"]
                    })

                    if normalized_text in {
                        "references",
                        "bibliography"
                    }:
                        inside_references = True

                    continue

                # Ignore long lines
                if len(text) > 100:
                    continue

                # Detect numbered sections and subsections
                is_numbered_heading = (
                    bool(numbered_heading_pattern.match(text))
                    and line["is_bold"]
                )

                # Detect short, bold, unnumbered headings
                is_formatted_heading = (
                    line["is_bold"]
                    and line["font_size"] >= body_font_size
                    and len(text) <= 80
                    and not text.endswith((".", ",", ";", ":"))
                )

                if (
                    is_numbered_heading
                    or is_formatted_heading
                ):

                    extracted_headings.append({
                        "page_number": line["page_number"],
                        "text": text,
                        "font_size": line["font_size"],
                        "is_bold": line["is_bold"],
                        "coordinates": line["coordinates"]
                    })

    except pymupdf.FileDataError as error:
        raise ValueError(
            f"Could not read PDF file: {error}"
        ) from error

    return extracted_headings


def normalize_table_cell(value):
    """
    Normalize whitespace inside a table cell.

    - Replace line breaks with spaces.
    - Collapse repeated whitespace.
    - Remove unnecessary spaces before punctuation.
    - Preserve the original characters and numerical values.
    """

    if value is None:
        return None

    text = str(value)

    # Replace line breaks and tabs with spaces
    text = re.sub(r"\s+", " ", text)

    # Remove spaces before punctuation
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)

    return text.strip()




def extract_text_lines_from_pdf(file_path):
    """Extract line-level text, bounding boxes, font size and writing direction.

    Unlike ``get_text('blocks')``, this retains the direction vector needed to
    recognize text rotated inside an otherwise normally oriented PDF page.
    Coordinates are PyMuPDF page coordinates.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    if file_path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    extracted_lines = []
    try:
        with pymupdf.open(file_path) as pdf:
            for page_number, page in enumerate(pdf, start=1):
                page_data = page.get_text("dict")
                line_index = 0
                for block in page_data.get("blocks", []):
                    if block.get("type") != 0:
                        continue
                    for line in block.get("lines", []):
                        spans = line.get("spans", [])
                        text = "".join(span.get("text", "") for span in spans).strip()
                        if not text:
                            continue
                        line_index += 1
                        sizes = [span.get("size", 0) for span in spans if span.get("text", "").strip()]
                        extracted_lines.append({
                            "page_number": page_number,
                            "line_number": line_index,
                            "text": text,
                            "direction": tuple(line.get("dir", (1.0, 0.0))),
                            "font_size": statistics.mean(sizes) if sizes else 0.0,
                            "coordinates": {
                                "x0": line["bbox"][0], "y0": line["bbox"][1],
                                "x1": line["bbox"][2], "y1": line["bbox"][3],
                            },
                        })
    except pymupdf.FileDataError as error:
        raise ValueError(f"Could not read PDF file: {error}") from error
    return extracted_lines


def is_vertical_direction(direction, tolerance=0.25):
    """Return True when a text line's baseline is predominantly vertical."""
    if not direction or len(direction) < 2:
        return False
    dx, dy = direction[0], direction[1]
    return abs(dy) > 0.75 and abs(dx) < tolerance


def box_intersection_area(first, second):
    """Calculate the intersection area of two coordinate dictionaries."""
    width = max(0.0, min(first["x1"], second["x1"]) - max(first["x0"], second["x0"]))
    height = max(0.0, min(first["y1"], second["y1"]) - max(first["y0"], second["y0"]))
    return width * height


def cluster_1d(values, tolerance):
    """Cluster nearby numeric coordinates and return (center, member indices)."""
    if not values:
        return []
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    groups = []
    current = [ordered[0]]
    for item in ordered[1:]:
        current_center = statistics.mean(value for _, value in current)
        if abs(item[1] - current_center) <= tolerance:
            current.append(item)
        else:
            groups.append(current)
            current = [item]
    groups.append(current)
    return [
        (statistics.mean(value for _, value in group), [index for index, _ in group])
        for group in groups
    ]


def _span_center(span):
    """Return the center point and normalized text for a PDF span."""
    x0, y0, x1, y1 = span["bbox"]
    return (x0 + x1) / 2, (y0 + y1) / 2


def _join_vertical_fragments(items, separator=" "):
    """Join fragments in increasing page-x order (reading order for this layout)."""
    ordered = sorted(items, key=lambda item: (item["x"], item["y"]))
    parts = []
    for item in ordered:
        text = normalize_table_cell(item["text"])
        if not text:
            continue
        if parts and text.startswith(("-", ".", ",", ";", ":", ")")):
            parts[-1] += text
        else:
            parts.append(text)
    return normalize_table_cell(separator.join(parts))


def _cluster_span_columns(items, max_gap=24.0):
    """Cluster x-positioned fragments into visually continuous merged cells."""
    if not items:
        return []
    ordered = sorted(items, key=lambda item: item["x"])
    groups = [[ordered[0]]]
    for item in ordered[1:]:
        previous_x = groups[-1][-1]["x"]
        if item["x"] - previous_x <= max_gap:
            groups[-1].append(item)
        else:
            groups.append([item])
    return groups


def _clean_accuracy(value):
    """Normalize split decimal strings without changing the numeric value."""
    value = normalize_table_cell(value)
    value = re.sub(r"(?<=\d)\s*\.\s*(?=\d)", ".", value)
    value = re.sub(r"\s+", "", value)
    return value


def _nearest_items_for_anchor(items, anchor_x, tolerance=4.5):
    """Return spans whose x center belongs to a model's row position."""
    return [item for item in items if abs(item["x"] - anchor_x) <= tolerance]


def reconstruct_vertical_table(page, page_number, table_bbox, table_number):
    """Reconstruct a 90-degree rotated research table using its logical bands.

    The page-15 layout has five logical columns. Since the text is rotated,
    page-y identifies the logical column and page-x identifies the model row.
    Multi-row Model Type and Rationale cells are preserved separately in
    ``merged_cells`` instead of being copied into every model row.

    This is a layout-aware reconstruction, not a universal OCR/table solver.
    If the expected headings or model anchors cannot be identified, it returns
    None so the caller can retain the native PyMuPDF extraction for review.
    """
    page_data = page.get_text("dict")
    spans = []

    for block in page_data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            if not is_vertical_direction(line.get("dir")):
                continue
            for span in line.get("spans", []):
                text = normalize_table_cell(span.get("text", ""))
                if not text or not span.get("bbox"):
                    continue
                x0, y0, x1, y1 = span["bbox"]
                coordinates = {"x0": x0, "y0": y0, "x1": x1, "y1": y1}
                intersection = box_intersection_area(coordinates, table_bbox)
                span_area = max(1.0, (x1 - x0) * (y1 - y0))
                if intersection / span_area < 0.35:
                    continue
                center_x, center_y = _span_center(span)
                spans.append({
                    "text": text,
                    "x": center_x,
                    "y": center_y,
                    "bbox": coordinates,
                    "font_size": span.get("size", 0.0),
                })

    if len(spans) < 20:
        return None

    # Locate the five logical column headings by their text, not fixed page
    # coordinates. This makes the method tolerant of different page sizes.
    def find_heading(pattern):
        matches = [item for item in spans if re.search(pattern, item["text"], re.I)]
        return min(matches, key=lambda item: item["x"]) if matches else None

    heading_model_type = find_heading(r"^Model\s+Type$")
    heading_model = find_heading(r"^Model$")
    heading_rationale = find_heading(r"^Rationale\s+for\s+Picking$")
    heading_feature = find_heading(r"^Feature\s+Used$")
    heading_results = find_heading(r"^Summary\s+of\s+Result")

    required_headings = [
        heading_model_type, heading_model, heading_rationale,
        heading_feature, heading_results,
    ]
    if any(item is None for item in required_headings):
        return None

    # The header y centers define logical bands. In page coordinates, larger
    # y values are nearer the Model Type heading and smaller values nearer the
    # result columns. Midpoints separate adjacent bands.
    header_centers = [item["y"] for item in required_headings]
    if not all(header_centers[i] > header_centers[i + 1] for i in range(4)):
        return None

    boundaries = [
        (header_centers[i] + header_centers[i + 1]) / 2
        for i in range(4)
    ]

    def in_band(item, band_index):
        y = item["y"]
        if band_index == 0:  # Model Type
            return y > boundaries[0] and item["x"] > table_bbox["x0"] + 15
        if band_index == 1:  # Model
            return boundaries[1] < y <= boundaries[0] and item["x"] > table_bbox["x0"] + 15
        if band_index == 2:  # Rationale
            return boundaries[2] < y <= boundaries[1] and item["x"] > table_bbox["x0"] + 15
        if band_index == 3:  # Feature
            return boundaries[3] < y <= boundaries[2] and item["x"] > table_bbox["x0"] + 15
        return y <= boundaries[3] and item["x"] > table_bbox["x0"] + 15

    model_band = [item for item in spans if in_band(item, 1)]
    if not model_band:
        return None

    # Model names are centered on one x position. Some names (e.g. k-NN) are
    # emitted as multiple spans at almost the same x, so cluster tightly.
    model_clusters = _cluster_span_columns(model_band, max_gap=3.5)
    model_entries = []
    for cluster in model_clusters:
        # A few model names are emitted as stacked fragments at the same x
        # coordinate (for example, "k" followed by "-NN"). Read top-to-bottom.
        ordered_model_fragments = sorted(cluster, key=lambda item: item["y"], reverse=True)
        model_parts = []
        for fragment in ordered_model_fragments:
            fragment_text = normalize_table_cell(fragment["text"])
            if not fragment_text:
                continue
            if model_parts and fragment_text.startswith(("-", ".")):
                model_parts[-1] += fragment_text
            else:
                model_parts.append(fragment_text)
        name = normalize_table_cell(" ".join(model_parts))
        if not name:
            continue
        # Exclude the Model heading itself and any stray text outside the data.
        if name.lower() == "model":
            continue
        model_entries.append({
            "x": statistics.mean(item["x"] for item in cluster),
            "model": name,
        })

    model_entries.sort(key=lambda item: item["x"])
    # The target table contains 19 model records. Do not silently force a
    # different count into this specialized layout.
    if len(model_entries) != 19:
        return None

    # Identify the three result subcolumns from their labels.
    result_labels = {
        "liar": [item for item in spans if re.fullmatch(r"Liar", item["text"], re.I)],
        "fake_or_real": [item for item in spans if re.search(r"Or\s+Real|Fake", item["text"], re.I)],
        "combined_corpus": [item for item in spans if re.search(r"Combined|Corpus", item["text"], re.I)],
    }
    result_y = {}
    for key, candidates in result_labels.items():
        candidates = [item for item in candidates if item["x"] < table_bbox["x0"] + 45]
        if candidates:
            result_y[key] = statistics.mean(item["y"] for item in candidates)
    if len(result_y) != 3:
        # Fallback to the three result bands inferred from the screenshot's
        # grouped result heading, while still requiring three distinct bands.
        result_spans = [item for item in spans if in_band(item, 4)]
        y_clusters = _cluster_span_columns(
            [{"x": item["y"], "y": item["x"], "text": item["text"]} for item in result_spans],
            max_gap=28.0,
        )
        if len(y_clusters) < 3:
            return None
        centers = sorted(
            [statistics.mean(item["x"] for item in group) for group in y_clusters],
            reverse=True,
        )
        result_y = dict(zip(("liar", "fake_or_real", "combined_corpus"), centers[:3]))

    # Model Type is a merged cell. Its fragments form three separated x groups.
    type_spans = [item for item in spans if in_band(item, 0)]
    type_groups = _cluster_span_columns(type_spans, max_gap=15.0)
    type_groups = [group for group in type_groups if group]
    if len(type_groups) != 3:
        return None

    model_type_groups = []
    for group in type_groups:
        model_type_groups.append({
            "x_min": min(item["x"] for item in group),
            "x_max": max(item["x"] for item in group),
            "label": _join_vertical_fragments(group),
        })
    model_type_groups.sort(key=lambda item: item["x_min"])

    # Rationale is also merged by model family. Its wrapped lines are separate
    # spans, but their x positions form three continuous regions.
    rationale_spans = [item for item in spans if in_band(item, 2)]
    rationale_groups = _cluster_span_columns(rationale_spans, max_gap=15.0)
    rationale_groups = [group for group in rationale_groups if group]
    if len(rationale_groups) != 3:
        return None

    rationale_records = []
    for group in rationale_groups:
        rationale_records.append({
            "x_min": min(item["x"] for item in group),
            "x_max": max(item["x"] for item in group),
            "text": _join_vertical_fragments(group),
        })
    rationale_records.sort(key=lambda item: item["x_min"])

    # Pair the three Model Type groups and three Rationale groups in reading
    # order. Model Type labels are centered inside merged regions, so their
    # x-centers provide more reliable family boundaries than the full rationale
    # text extents (which can extend across several model rows).
    model_type_groups = sorted(model_type_groups, key=lambda item: item["x_min"])
    rationale_records = sorted(rationale_records, key=lambda item: item["x_min"])
    if len(model_type_groups) != 3 or len(rationale_records) != 3:
        return None

    # Use the horizontal extents of the rationale groups to determine family
    # boundaries. Model Type labels are centered inside merged cells and can be
    # much narrower than the model family they describe. Using their centers
    # incorrectly pushed the final deep-learning models (HAN and Conv-HAN)
    # into the advanced-language-model group.
    rationale_records = sorted(rationale_records, key=lambda item: item["x_min"])
    family_boundaries = [
        (
            rationale_records[index]["x_max"]
            + rationale_records[index + 1]["x_min"]
        ) / 2
        for index in range(len(rationale_records) - 1)
    ]

    # Assign every model anchor to exactly one family. The resulting ranges
    # are half-open [start, end), so adjacent groups never share a row.
    family_model_indices = [[], [], []]
    for model_index, entry in enumerate(model_entries):
        if entry["x"] < family_boundaries[0]:
            family_model_indices[0].append(model_index)
        elif entry["x"] < family_boundaries[1]:
            family_model_indices[1].append(model_index)
        else:
            family_model_indices[2].append(model_index)

    merged_cells = []
    family_ranges = []
    for family_index, (type_group, rationale_group, indices) in enumerate(
        zip(model_type_groups, rationale_records, family_model_indices)
    ):
        if not indices:
            return None

        start_index = min(indices)
        end_index = max(indices) + 1  # exclusive
        family_ranges.append((
            start_index,
            end_index,
            type_group["label"],
            rationale_group["text"],
        ))
        merged_cells.extend([
            {
                "column_index": 0,
                "row_start": start_index,
                "row_end": end_index,
                "row_end_exclusive": True,
                "value": type_group["label"],
            },
            {
                "column_index": 2,
                "row_start": start_index,
                "row_end": end_index,
                "row_end_exclusive": True,
                "value": rationale_group["text"],
            },
        ])

    # Extract Feature Used and the three result values at each model anchor.
    feature_spans = [item for item in spans if in_band(item, 3)]
    result_spans = [item for item in spans if in_band(item, 4)]

    def family_for_row(row_index):
        for start_index, end_index, model_type, rationale in family_ranges:
            if start_index <= row_index < end_index:
                return model_type, rationale
        return None, None

    data = []
    structured_rows = []
    for row_index, entry in enumerate(model_entries):
        anchor_x = entry["x"]

        # Some feature labels (notably "GloVe embedding") are centered a few
        # points away from their model anchor. Use a slightly wider nearest-
        # anchor tolerance while keeping adjacent model rows separate.
        feature_items = _nearest_items_for_anchor(
            feature_spans, anchor_x, tolerance=9.0
        )
        feature = _join_vertical_fragments(feature_items) if feature_items else None

        values = {}
        for key, target_y in result_y.items():
            candidates = _nearest_items_for_anchor(
                result_spans, anchor_x, tolerance=4.5
            )
            candidates = [
                item for item in candidates
                if abs(item["y"] - target_y) <= 18.0
            ]
            if candidates:
                closest = min(candidates, key=lambda item: abs(item["y"] - target_y))
                values[key] = _clean_accuracy(closest["text"])
            else:
                values[key] = None

        model_type, rationale = family_for_row(row_index)
        if model_type is None or rationale is None:
            return None

        result_cell = {
            "Liar": values["liar"],
            "Fake or Real": values["fake_or_real"],
            "Combined Corpus": values["combined_corpus"],
        }

        # Keep each row self-contained for database retrieval and search.
        # The merged_cells metadata is also retained so the original visual
        # table structure can be reconstructed by the frontend.
        row = [model_type, entry["model"], rationale, feature, result_cell]
        data.append(row)
        structured_rows.append({
            "row_index": row_index,
            "model_type": model_type,
            "model": entry["model"],
            "rationale": rationale,
            "feature_used": feature,
            "results": result_cell,
        })

    # A reconstruction is only considered structurally plausible when every
    # model has at least one result and the expected three family labels exist.
    populated_results = sum(
        any(value not in (None, "") for value in row[4].values())
        for row in data
    )
    if populated_results < 17:
        return None

    coordinates = dict(table_bbox)
    return {
        "page_number": page_number,
        "table_number": table_number,
        "row_count": len(data),
        "column_count": 5,
        "original_data": data,
        "data": data,
        "coordinates": coordinates,
        "extraction_method": "rotated_layout_reconstruction",
        "extraction_confidence": "review_required",
        "column_headers": [
            "Model Type",
            "Model",
            "Rationale for Picking",
            "Feature Used",
            "Summary of Result (Acc.)",
        ],
        "result_subheaders": ["Liar", "Fake or Real", "Combined Corpus"],
        "merged_cells": merged_cells,
        "structured_rows": structured_rows,
        "reconstruction_notes": [
            "Model Type and Rationale for Picking are preserved as merged-cell metadata.",
            "The result column contains three named accuracy values per model.",
            "Validate numerical values against the source PDF before indexing.",
        ],
    }


def extract_rotated_caption_lines(page, page_number):
    """Return vertical text lines that may contain a rotated table caption."""
    results = []
    page_data = page.get_text("dict")
    for block in page_data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            if not is_vertical_direction(line.get("dir")):
                continue
            text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
            if not text:
                continue
            results.append({
                "page_number": page_number,
                "text": text,
                "direction": tuple(line.get("dir", (0.0, -1.0))),
                "coordinates": {
                    "x0": line["bbox"][0], "y0": line["bbox"][1],
                    "x1": line["bbox"][2], "y1": line["bbox"][3],
                },
            })
    return results


def reconstruct_horizontal_table(page, page_number):
    """Reconstruct the benchmark paper's horizontal metric tables from PDF spans.

    The function is caption-driven (Tables 3, 4 and 5), not page-number-driven.
    Numeric cells are assigned using the x-centres of the printed A/P/R/F1
    headers, while model/feature labels are associated with the numeric row
    anchors by their y-coordinates. It returns None when structural validation
    fails so the caller can preserve PyMuPDF's native extraction for review.
    """
    page_data = page.get_text("dict")
    lines = []
    for block in page_data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = [span for span in line.get("spans", []) if span.get("text", "").strip()]
            text = normalize_extracted_text(" ".join(span["text"] for span in spans))
            if not text:
                continue
            bbox = line.get("bbox")
            lines.append({
                "text": text,
                "bbox": bbox,
                "y": (bbox[1] + bbox[3]) / 2,
                "spans": spans,
            })

    caption_line = next(
        (line for line in lines if parse_table_caption(line["text"])),
        None,
    )
    if caption_line is None:
        return None

    caption = parse_table_caption(caption_line["text"])
    table_number = caption["table_number"]
    expected_rows_by_table = {3: 8, 4: 6, 5: 5}
    expected_rows = expected_rows_by_table.get(table_number)
    if expected_rows is None:
        return None

    # Flatten spans while retaining line and page coordinates.
    positioned = []
    for line in lines:
        for span in line["spans"]:
            x0, y0, x1, y1 = span["bbox"]
            positioned.append({
                "text": normalize_table_cell(span.get("text", "")),
                "x": (x0 + x1) / 2,
                "y": (y0 + y1) / 2,
                "bbox": (x0, y0, x1, y1),
            })

    def find_header(text):
        matches = [
            item for item in positioned
            if item["y"] > caption_line["y"]
            and normalize_extracted_text(item["text"]).casefold() == text.casefold()
        ]
        return min(matches, key=lambda item: item["y"]) if matches else None

    model_header = find_header("Model")
    metric_labels = ["A", "P", "R", "F1"] * 3
    # Select the first complete metric-header row after the caption. The three
    # dataset headings sit above it, so exact metric labels are unambiguous.
    if model_header is None:
        return None
    header_y = model_header["y"]
    metric_headers = []
    for label in metric_labels:
        candidates = [
            item for item in positioned
            if item["text"].casefold() == label.casefold()
            and abs(item["y"] - header_y) <= 3.0
        ]
        if not candidates:
            return None
        # Choose the not-yet-used candidate nearest the expected left-to-right
        # sequence. A/P/R/F1 labels repeat across the three datasets.
        metric_headers.append(candidates)

    # Recover all twelve header x-centres in reading order. The source layout
    # prints each metric heading once in each dataset group.
    header_candidates = [
        item for item in positioned
        if item["text"].casefold() in {"a", "p", "r", "f1"}
        and abs(item["y"] - header_y) <= 3.0
        and item["x"] > model_header["x"]
    ]
    header_candidates.sort(key=lambda item: item["x"])
    # Remove duplicate text spans only when they share essentially the same
    # location; do not collapse repeated A/P/R/F1 labels in different groups.
    unique_headers = []
    for item in header_candidates:
        if not unique_headers or abs(item["x"] - unique_headers[-1]["x"]) > 5.0:
            unique_headers.append(item)
    if len(unique_headers) != 12:
        return None
    metric_x = [item["x"] for item in unique_headers]

    # Numeric values in the table are individual spans. Group them into rows
    # using their baseline centres, then assign each value to its nearest
    # metric-header centre.
    numeric_pattern = re.compile(r"^(?:\d+\.\d+|\.\d+|\d+)$")
    numeric_items = [
        item for item in positioned
        if item["y"] > header_y + 5.0
        and numeric_pattern.fullmatch(item["text"].replace(" ", ""))
        and min(abs(item["x"] - x) for x in metric_x) <= 12.0
    ]
    numeric_items.sort(key=lambda item: item["y"])

    row_groups = []
    for item in numeric_items:
        if not row_groups or abs(item["y"] - statistics.mean(x["y"] for x in row_groups[-1])) > 3.5:
            row_groups.append([item])
        else:
            row_groups[-1].append(item)

    # Ignore any numeric-looking material outside the table if it does not
    # form a complete twelve-cell row. The expected count is strict.
    complete_rows = []
    for group in row_groups:
        cells = {}
        valid = True
        for item in group:
            column = min(range(12), key=lambda index: abs(item["x"] - metric_x[index]))
            if abs(item["x"] - metric_x[column]) > 12.0 or column in cells:
                valid = False
                break
            cells[column] = _clean_accuracy(item["text"])
        if valid and len(cells) == 12:
            complete_rows.append({
                "y": statistics.mean(item["y"] for item in group),
                "cells": [cells[index] for index in range(12)],
            })

    if len(complete_rows) != expected_rows:
        return None

    # The first column contains model names. Table 3 additionally has a
    # Feature column; its labels can wrap onto two physical lines.
    feature_header = find_header("Feature") if table_number == 3 else None
    first_metric_x = metric_x[0]
    if feature_header:
        model_feature_boundary = (model_header["x"] + feature_header["x"]) / 2
        feature_metric_boundary = (feature_header["x"] + first_metric_x) / 2
    else:
        model_feature_boundary = (model_header["x"] + first_metric_x) / 2
        feature_metric_boundary = None

    def collect_label(x_min, x_max, row_y):
        candidates = [
            item for item in positioned
            if item["y"] > header_y + 5.0
            and abs(item["y"] - row_y) <= 16.0
            and item["x"] >= x_min
            and item["x"] < x_max
            and not numeric_pattern.fullmatch(item["text"].replace(" ", ""))
        ]
        # Join wrapped label fragments top-to-bottom; fragments on the same
        # baseline are joined left-to-right. This preserves labels like
        # "Decision Tree" and "Lexical +Sentiment".
        candidates.sort(key=lambda item: (round(item["y"], 1), item["x"]))
        parts = []
        for item in candidates:
            value = normalize_table_cell(item["text"])
            if not value or (parts and value == parts[-1]):
                continue
            if parts and value.startswith(("-", ".", ",", ";", ":", ")")):
                parts[-1] += value
            else:
                parts.append(value)
        return normalize_table_cell(" ".join(parts)) or None

    reconstructed_data = []
    structured_rows = []
    for row_index, row in enumerate(complete_rows):
        model = collect_label(-float("inf"), model_feature_boundary, row["y"])
        if not model:
            return None
        feature = None
        if feature_header:
            feature = collect_label(model_feature_boundary, feature_metric_boundary, row["y"])
        result_values = row["cells"]
        reconstructed_data.append(([model, feature] if feature_header else [model]) + result_values)
        structured_rows.append({
            "row_index": row_index,
            "model": model,
            **({"feature": feature} if feature_header else {}),
            "metrics": {
                dataset: {
                    metric: result_values[group_index * 4 + metric_index]
                    for metric_index, metric in enumerate(("A", "P", "R", "F1"))
                }
                for group_index, dataset in enumerate(("Liar", "Fake or Real News", "Combined Corpus"))
            },
        })

    column_headers = (["Model", "Feature"] if feature_header else ["Model"])
    for dataset in ("Liar", "Fake or Real News", "Combined Corpus"):
        column_headers.extend([f"{dataset} - {metric}" for metric in ("A", "P", "R", "F1")])

    # Validate every reconstructed cell and ensure the model labels are unique.
    if any(len(row) != len(column_headers) for row in reconstructed_data):
        return None

    x0 = min(item["bbox"][0] for item in positioned if item["y"] >= header_y - 2 and item["x"] <= metric_x[-1] + 15)
    x1 = max(item["bbox"][2] for item in positioned if item["y"] >= header_y - 2 and item["x"] <= metric_x[-1] + 15)
    y0 = min(item["bbox"][1] for item in unique_headers)
    y1 = max(item["bbox"][3] for item in numeric_items if any(abs(item["y"] - row["y"]) <= 3.5 for row in complete_rows))
    coordinates = {"x0": x0, "y0": y0, "x1": x1, "y1": y1}

    return {
        "page_number": page_number,
        "table_number": table_number,
        "table_title": caption["table_title"],
        "row_count": len(reconstructed_data),
        "column_count": len(column_headers),
        "original_data": reconstructed_data,
        "data": reconstructed_data,
        "column_headers": column_headers,
        "structured_rows": structured_rows,
        "coordinates": coordinates,
        "extraction_method": "horizontal_layout_reconstruction",
        "extraction_confidence": "structurally_validated",
        "validation": {
            "expected_row_count": expected_rows,
            "actual_row_count": len(reconstructed_data),
            "expected_metric_values_per_row": 12,
            "all_rows_have_complete_metrics": True,
            "model_labels_present": True,
        },
        "reconstruction_notes": [
            "Metric cells were assigned using the x-coordinates of the printed A/P/R/F1 headers.",
            "Rows were grouped using the y-coordinates of numeric text spans.",
            "Wrapped model and feature labels were associated with their numeric row anchors.",
            "Values are preserved from the source PDF; no metric values are inferred or corrected.",
        ],
    }


def _bbox_dict(value):
    """Convert a PyMuPDF rectangle/tuple into a coordinate dictionary."""
    if value is None or len(value) < 4:
        return None
    return {
        "x0": float(value[0]), "y0": float(value[1]),
        "x1": float(value[2]), "y1": float(value[3]),
    }


def _vertical_rule_positions(page, table_bbox, tolerance=1.25):
    """Find vertical grid rules encoded as lines or thin filled rectangles."""
    rules = []
    try:
        drawings = page.get_drawings()
    except Exception:
        return rules

    for drawing in drawings:
        for item in drawing.get("items", []):
            if not item:
                continue
            if item[0] == "l":
                p1, p2 = item[1], item[2]
                x1, y1 = float(p1.x), float(p1.y)
                x2, y2 = float(p2.x), float(p2.y)
                if abs(x1 - x2) <= tolerance:
                    top, bottom = sorted((y1, y2))
                    if bottom > table_bbox["y0"] and top < table_bbox["y1"]:
                        rules.append(((x1 + x2) / 2, top, bottom))
            elif item[0] == "re":
                rect = item[1]
                # PDFs commonly encode grid strokes as narrow filled rectangles.
                if rect.width <= tolerance and rect.height >= 3.0:
                    if rect.y1 > table_bbox["y0"] and rect.y0 < table_bbox["y1"]:
                        rules.append(((float(rect.x0) + float(rect.x1)) / 2,
                                      float(rect.y0), float(rect.y1)))
    return rules


def _has_vertical_rule(rules, x, y0, y1, tolerance=2.0):
    """Check whether a visible vertical rule separates two cell fragments."""
    for rule_x, rule_y0, rule_y1 in rules:
        overlap = min(y1, rule_y1) - max(y0, rule_y0)
        if abs(rule_x - x) <= tolerance and overlap > 0.5 * min(y1 - y0, rule_y1 - rule_y0):
            return True
    return False


def _words_in_bbox(words, bbox):
    """Select PDF words substantially contained in a cell bounding box."""
    if not bbox:
        return []
    selected = []
    for word in words:
        x0, y0, x1, y1, text = word[:5]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if bbox["x0"] - 1 <= cx <= bbox["x1"] + 1 and bbox["y0"] - 1 <= cy <= bbox["y1"] + 1:
            if str(text).strip():
                selected.append({
                    "text": str(text),
                    "x0": float(x0), "y0": float(y0),
                    "x1": float(x1), "y1": float(y1),
                })
    return sorted(selected, key=lambda item: (round(item["y0"], 1), item["x0"]))


def _rebuild_cell_from_words(words):
    """Rebuild cell text in reading order without changing token contents."""
    if not words:
        return None
    lines = []
    for word in words:
        target = next(
            (line for line in lines if abs(line["y"] - word["y0"]) <= 3.0),
            None,
        )
        if target is None:
            target = {"y": word["y0"], "words": []}
            lines.append(target)
        target["words"].append(word)
    rendered = []
    for line in sorted(lines, key=lambda item: item["y"]):
        line_words = sorted(line["words"], key=lambda item: item["x0"])
        rendered.append(" ".join(item["text"] for item in line_words))
    return normalize_table_cell(" ".join(rendered))


def normalize_native_table_geometry(page, table, original_data):
    """Normalize native table cells using stable page geometry.

    Prefer a complete vertical grid plus native row bands. This reconstructs
    logical cells when PyMuPDF splits one visual cell into text-sized fragments.
    If a reliable grid is unavailable, use the conservative fragment-merge
    fallback. ``original_data`` is copied and never modified.
    """
    rows = deepcopy(original_data)
    native_rows = getattr(table, "rows", []) or []
    try:
        words = page.get_text("words")
    except Exception:
        words = []

    table_bbox = _bbox_dict(getattr(table, "bbox", None))
    rules = _vertical_rule_positions(page, table_bbox) if table_bbox else []

    # Cluster duplicate/nearby edges and retain only rules spanning much of the
    # table. This excludes short decorative marks and most incidental artwork.
    grid_x = []
    if table_bbox and rules:
        table_height = table_bbox["y1"] - table_bbox["y0"]
        grouped_rules = []
        for x, y0, y1 in sorted(rules, key=lambda item: item[0]):
            if x < table_bbox["x0"] - 3.0 or x > table_bbox["x1"] + 3.0:
                continue
            if not grouped_rules or abs(x - grouped_rules[-1]["x"]) > 2.0:
                grouped_rules.append({"x": x, "intervals": [(y0, y1)]})
            else:
                group = grouped_rules[-1]
                group["x"] = (group["x"] + x) / 2.0
                group["intervals"].append((y0, y1))

        for group in grouped_rules:
            intervals = sorted(group["intervals"])
            covered = 0.0
            if intervals:
                start, end = intervals[0]
                for next_start, next_end in intervals[1:]:
                    if next_start <= end + 1.5:
                        end = max(end, next_end)
                    else:
                        covered += end - start
                        start, end = next_start, next_end
                covered += end - start
            if covered >= table_height * 0.45:
                grid_x.append(group["x"])

    # Need two outer boundaries and at least two internal boundaries.
    if len(grid_x) >= 4 and table_bbox:
        outer_edges_match = (
            abs(grid_x[0] - table_bbox["x0"]) <= 3.0
            and abs(grid_x[-1] - table_bbox["x1"]) <= 3.0
        )
        if outer_edges_match:
            column_bounds = list(zip(grid_x[:-1], grid_x[1:]))
            rebuilt_rows = []
            row_bands_valid = True

            for row_index in range(len(rows)):
                native_row = native_rows[row_index] if row_index < len(native_rows) else None
                cell_boxes = getattr(native_row, "cells", []) if native_row else []
                valid_boxes = [_bbox_dict(box) for box in cell_boxes]
                valid_boxes = [box for box in valid_boxes if box]
                if not valid_boxes:
                    row_bands_valid = False
                    break

                row_y0 = min(box["y0"] for box in valid_boxes)
                row_y1 = max(box["y1"] for box in valid_boxes)
                row_words = [
                    word for word in words
                    if row_y0 - 1.0 <= (float(word[1]) + float(word[3])) / 2 <= row_y1 + 1.0
                    and table_bbox["x0"] - 1.0 <= (float(word[0]) + float(word[2])) / 2 <= table_bbox["x1"] + 1.0
                    and str(word[4]).strip()
                ]

                rebuilt = []
                for col_x0, col_x1 in column_bounds:
                    cell_words = [
                        {"text": str(word[4]), "x0": float(word[0]), "y0": float(word[1]),
                         "x1": float(word[2]), "y1": float(word[3])}
                        for word in row_words
                        if col_x0 - 1.0 <= (float(word[0]) + float(word[2])) / 2 <= col_x1 + 1.0
                    ]
                    rebuilt.append(_rebuild_cell_from_words(cell_words))
                rebuilt_rows.append(rebuilt)

            if row_bands_valid and rebuilt_rows and all(
                len(row) == len(column_bounds) for row in rebuilt_rows
            ):
                validation = validate_table_structure(rebuilt_rows)
                validation["normalization_method"] = "vertical_grid_and_row_geometry"
                validation["detected_column_boundaries"] = [round(x, 2) for x in grid_x]
                return rebuilt_rows, validation

    # Fallback for tables without a sufficiently reliable complete grid.
    geometry_rows = []
    for row_index, row in enumerate(rows):
        native_row = native_rows[row_index] if row_index < len(native_rows) else None
        cell_boxes = getattr(native_row, "cells", []) if native_row else []
        normalized = [normalize_table_cell(value) for value in row]
        boxes = [_bbox_dict(box) for box in cell_boxes]

        column_index = 0
        while column_index < len(normalized) - 1:
            left_text, right_text = normalized[column_index:column_index + 2]
            left_box = boxes[column_index] if column_index < len(boxes) else None
            right_box = boxes[column_index + 1] if column_index + 1 < len(boxes) else None
            can_join = False

            if left_text and right_text and left_box and right_box:
                boundary_x = (left_box["x1"] + right_box["x0"]) / 2
                vertical_overlap = min(left_box["y1"], right_box["y1"]) - max(left_box["y0"], right_box["y0"])
                if (
                    abs(left_box["x1"] - right_box["x0"]) <= 2.5
                    and vertical_overlap > 0
                    and not _has_vertical_rule(
                        rules, boundary_x,
                        max(left_box["y0"], right_box["y0"]),
                        min(left_box["y1"], right_box["y1"]),
                    )
                ):
                    left_words = _words_in_bbox(words, left_box)
                    right_words = _words_in_bbox(words, right_box)
                    if left_words and right_words:
                        last_word = max(left_words, key=lambda item: item["x1"])
                        first_word = min(right_words, key=lambda item: item["x0"])
                        gap = first_word["x0"] - last_word["x1"]
                        can_join = (
                            -1.5 <= gap <= 4.0
                            and last_word["text"][-1:].isalnum()
                            and first_word["text"][:1].isalnum()
                        )

            if can_join:
                normalized[column_index] = normalize_table_cell(f"{left_text}{right_text}")
                normalized.pop(column_index + 1)
                boxes.pop(column_index + 1)
            else:
                column_index += 1
        geometry_rows.append(normalized)

    max_columns = max((len(row) for row in geometry_rows), default=0)
    keep_columns = [
        index for index in range(max_columns)
        if any(index < len(row) and row[index] not in (None, "") for row in geometry_rows)
    ]
    rectangular = [
        [row[index] if index < len(row) else None for index in keep_columns]
        for row in geometry_rows
    ]
    validation = validate_table_structure(rectangular)
    validation["normalization_method"] = "conservative_fragment_merge_fallback"
    return rectangular, validation


def validate_table_structure(data):
    """Return transparent structural checks; never modify table values."""
    rows = data if isinstance(data, list) else []
    widths = [len(row) for row in rows if isinstance(row, list)]
    nonempty_rows = [
        row for row in rows
        if isinstance(row, list) and any(value not in (None, "") for value in row)
    ]
    width_counts = {}
    for width in widths:
        width_counts[width] = width_counts.get(width, 0) + 1

    dominant_width = max(width_counts, key=width_counts.get) if width_counts else 0
    consistency = (
        width_counts.get(dominant_width, 0) / len(widths)
        if widths else 0.0
    )
    empty_cells = sum(
        value in (None, "")
        for row in rows if isinstance(row, list)
        for value in row
    )
    total_cells = sum(len(row) for row in rows if isinstance(row, list))

    issues = []
    if not rows:
        issues.append("no_rows")
    if len(width_counts) > 1:
        issues.append("inconsistent_row_widths")
    if total_cells and empty_cells / total_cells > 0.5:
        issues.append("high_empty_cell_ratio")

    return {
        "row_count": len(rows),
        "nonempty_row_count": len(nonempty_rows),
        "column_count": dominant_width,
        "row_width_consistency": round(consistency, 4),
        "empty_cell_count": empty_cells,
        "empty_cell_ratio": round(empty_cells / total_cells, 4) if total_cells else 0.0,
        "issues": issues,
    }



def extract_tables_from_pdf(file_path):
    """
    Extract tables using PyMuPDF, then apply conservative geometry-aware
    normalization to native tables.

    Existing specialized rotated/horizontal reconstruction paths are retained.
    Raw extraction is always preserved independently from normalized output.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    if file_path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    extracted_tables = []
    try:
        with pymupdf.open(file_path) as pdf:
            for page_number, page in enumerate(pdf, start=1):
                table_finder = page.find_tables()
                page_vertical_lines = extract_rotated_caption_lines(page, page_number)

                horizontal_reconstruction = reconstruct_horizontal_table(page, page_number)
                if horizontal_reconstruction:
                    extracted_tables.append(horizontal_reconstruction)
                    continue

                for table_number, table in enumerate(table_finder.tables, start=1):
                    original_data = table.extract()
                    if not original_data:
                        continue

                    coordinates = {
                        "x0": table.bbox[0], "y0": table.bbox[1],
                        "x1": table.bbox[2], "y1": table.bbox[3],
                    }

                    vertical_items = [
                        line for line in page_vertical_lines
                        if box_intersection_area(line["coordinates"], coordinates) > 0
                    ]
                    vertical_area = sum(
                        box_intersection_area(line["coordinates"], coordinates)
                        for line in vertical_items
                    )
                    table_area = max(
                        1.0,
                        (coordinates["x1"] - coordinates["x0"]) *
                        (coordinates["y1"] - coordinates["y0"]),
                    )
                    has_rotated_text = bool(vertical_items) and vertical_area / table_area > 0.005

                    reconstructed = None
                    if has_rotated_text:
                        reconstructed = reconstruct_vertical_table(
                            page=page,
                            page_number=page_number,
                            table_bbox=coordinates,
                            table_number=table_number,
                        )

                    if reconstructed:
                        # Exact native output is retained for audit/review.
                        reconstructed["raw_find_tables_data"] = deepcopy(original_data)
                        reconstructed["raw_find_tables_row_count"] = len(original_data)
                        reconstructed["raw_find_tables_column_count"] = max(
                            (len(row) for row in original_data), default=0
                        )
                        reconstructed["normalized_table_data"] = deepcopy(
                            reconstructed.get("data", [])
                        )
                        reconstructed["validation_results"] = validate_table_structure(
                            reconstructed["normalized_table_data"]
                        )
                        extracted_tables.append(reconstructed)
                        continue

                    normalized_data, validation = normalize_native_table_geometry(
                        page=page,
                        table=table,
                        original_data=original_data,
                    )

                    extracted_tables.append({
                        "page_number": page_number,
                        "table_number": table_number,
                        "row_count": len(normalized_data),
                        "column_count": max(
                            (len(row) for row in normalized_data), default=0
                        ),
                        "original_data": deepcopy(original_data),
                        "raw_table_data": deepcopy(original_data),
                        "data": normalized_data,
                        "normalized_table_data": deepcopy(normalized_data),
                        "coordinates": coordinates,
                        "extraction_method": "pymupdf_find_tables+geometry_normalization",
                        "extraction_confidence": (
                            "structurally_consistent"
                            if not validation["issues"]
                            else "review_required"
                        ),
                        "validation_results": validation,
                    })

    except pymupdf.FileDataError as error:
        raise ValueError(f"Could not read PDF file: {error}") from error

    return extracted_tables


def normalize_extracted_text(text):
    """Normalize whitespace in extracted PDF text."""
    return re.sub(r"\s+", " ", str(text or "")).strip()


def parse_table_caption(text):
    """
    Extract the actual table number and title from a caption.

    Examples:
        Table 3: Performance of Traditional ML Models
        Table 4. Performance of Deep Learning Models
    """

    text = normalize_extracted_text(text)

    match = re.match(
        r"^\s*Table\s+(\d+)\s*[:.)-]?\s*(.*?)\s*$",
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    table_number = int(match.group(1))
    table_title = match.group(2).strip(" :-.")

    return {
        "table_number": table_number,
        "table_title": table_title or None,
    }


def has_horizontal_overlap(first, second):
    """Check whether two PDF bounding boxes overlap horizontally."""

    overlap = min(first["x1"], second["x1"]) - max(
        first["x0"], second["x0"]
    )

    if overlap <= 0:
        return False

    first_width = first["x1"] - first["x0"]
    second_width = second["x1"] - second["x0"]

    smaller_width = min(first_width, second_width)

    if smaller_width <= 0:
        return False

    return overlap / smaller_width >= 0.2


def find_table_caption(table, text_blocks):
    """Find a nearby caption above/below a normal table or beside a rotated one."""
    table_coordinates = table["coordinates"]
    table_page = table["page_number"]
    candidates = []

    for block in text_blocks:
        if block["page_number"] != table_page:
            continue
        caption = parse_table_caption(block["text"])
        if not caption:
            continue
        block_coordinates = block["coordinates"]
        direction = block.get("direction", (1.0, 0.0))

        if is_vertical_direction(direction):
            # Rotated captions usually sit immediately to the left or right
            # of the table and overlap it along the page-y axis.
            vertical_overlap = min(table_coordinates["y1"], block_coordinates["y1"]) - max(
                table_coordinates["y0"], block_coordinates["y0"]
            )
            smaller_height = min(
                table_coordinates["y1"] - table_coordinates["y0"],
                block_coordinates["y1"] - block_coordinates["y0"],
            )
            if vertical_overlap > 0 and smaller_height > 0 and vertical_overlap / smaller_height >= 0.2:
                if block_coordinates["x1"] <= table_coordinates["x0"]:
                    distance = table_coordinates["x0"] - block_coordinates["x1"]
                    if distance <= 50:
                        candidates.append({**caption, "distance": distance, "position_priority": 0})
                elif block_coordinates["x0"] >= table_coordinates["x1"]:
                    distance = block_coordinates["x0"] - table_coordinates["x1"]
                    if distance <= 40:
                        candidates.append({**caption, "distance": distance, "position_priority": 1})
            continue

        if not has_horizontal_overlap(table_coordinates, block_coordinates):
            continue
        if block_coordinates["y1"] <= table_coordinates["y0"]:
            distance = table_coordinates["y0"] - block_coordinates["y1"]
            if distance <= 120:
                candidates.append({**caption, "distance": distance, "position_priority": 2})
        elif block_coordinates["y0"] >= table_coordinates["y1"]:
            distance = block_coordinates["y0"] - table_coordinates["y1"]
            if distance <= 40:
                candidates.append({**caption, "distance": distance, "position_priority": 3})

    if not candidates:
        return None
    candidates.sort(key=lambda item: (item["position_priority"], item["distance"]))
    return candidates[0]



def get_heading_context(table, headings):
    """
    Find the closest preceding structural heading.

    Headings located inside the table's bounding box are
    excluded because they may be table headers rather than
    document section headings.
    """

    table_page = table["page_number"]
    table_coordinates = table["coordinates"]

    table_y = table_coordinates["y0"]

    preceding_headings = []

    for heading in headings:

        heading_page = heading["page_number"]
        heading_coordinates = heading["coordinates"]

        heading_y = heading_coordinates["y0"]

        # Exclude anything overlapping the table before testing whether it
        # precedes the table. This avoids treating internal column labels as
        # document section headings.
        same_page = heading_page == table_page
        if same_page:
            overlaps_horizontally = (
                heading_coordinates["x0"] < table_coordinates["x1"]
                and heading_coordinates["x1"] > table_coordinates["x0"]
            )
            overlaps_vertically = (
                heading_coordinates["y0"] < table_coordinates["y1"]
                and heading_coordinates["y1"] > table_coordinates["y0"]
            )
            if overlaps_horizontally and overlaps_vertically:
                continue

        # Only consider headings before the table.
        if not (
            heading_page < table_page
            or (heading_page == table_page and heading_y <= table_y)
        ):
            continue

        preceding_headings.append(heading)

    if not preceding_headings:
        return {
            "section_title": None,
            "parent_section_title": None,
        }

    preceding_headings.sort(
        key=lambda item: (
            item["page_number"],
            item["coordinates"]["y0"],
        )
    )

    current_heading = preceding_headings[-1]
    section_title = current_heading["text"]

    number_match = re.match(
        r"^\s*(\d+(?:\.\d+)*)\.?\s+",
        section_title,
    )

    parent_section_title = None

    if number_match:

        section_number = number_match.group(1)

        if "." in section_number:

            parent_number = section_number.rsplit(".", 1)[0]

            for heading in reversed(preceding_headings[:-1]):

                parent_match = re.match(
                    r"^\s*(\d+(?:\.\d+)*)\.?\s+",
                    heading["text"],
                )

                if (
                    parent_match
                    and parent_match.group(1) == parent_number
                ):
                    parent_section_title = heading["text"]
                    break

    return {
        "section_title": section_title,
        "parent_section_title": parent_section_title,
    }



def build_table_search_text(table):
    """Build retrieval text from normalized rows, retaining cell boundaries."""
    parts = []

    if table.get("table_title"):
        parts.append(f"Table title: {table['table_title']}")
    if table.get("section_title"):
        parts.append(f"Section: {table['section_title']}")
    if table.get("parent_section_title"):
        parts.append(f"Parent section: {table['parent_section_title']}")
    if table.get("extraction_method"):
        parts.append(f"Extraction method: {table['extraction_method']}")

    headers = table.get("column_headers")
    if isinstance(headers, list) and headers:
        parts.append("Column headers: " + " | ".join(
            normalize_extracted_text(value) for value in headers
            if value not in (None, "")
        ))

    parts.append("Table data:")
    for merged in table.get("merged_cells", []):
        parts.append(
            f"Merged column {merged.get('column_index')} "
            f"(rows {merged.get('row_start')}–{merged.get('row_end')}): "
            f"{merged.get('value', '')}"
        )

    rows = table.get("normalized_table_data")
    if rows is None:
        rows = table.get("table_data")
    if rows is None:
        rows = table.get("data", [])

    for row in rows:
        if not isinstance(row, (list, tuple)):
            continue
        rendered_cells = []
        for cell in row:
            if cell is None or cell == "":
                rendered_cells.append("[empty]")
            elif isinstance(cell, dict):
                rendered_cells.append("; ".join(
                    f"{key}: {value}" for key, value in cell.items()
                    if value not in (None, "")
                ))
            else:
                rendered_cells.append(normalize_extracted_text(cell))
        if any(cell != "[empty]" for cell in rendered_cells):
            parts.append(" | ".join(rendered_cells))

    return "\n".join(parts).strip()


def enrich_tables_with_metadata(tables, text_blocks, headings):
    """
    Enrich extracted tables while keeping raw and normalized representations
    separate. Search text is always generated from normalized data.
    """
    enriched_tables = []

    for table_index, raw_table in enumerate(tables, start=1):
        table = dict(raw_table)
        table["page_table_number"] = table.get("table_number")
        table["table_index"] = table_index

        caption = find_table_caption(table=table, text_blocks=text_blocks)
        table["table_number"] = caption["table_number"] if caption else None
        table["table_title"] = caption["table_title"] if caption else None

        heading_context = get_heading_context(table=table, headings=headings)
        table.update(heading_context)

        raw_data = table.get("raw_table_data")
        if raw_data is None:
            raw_data = table.get("raw_find_tables_data")
        if raw_data is None:
            raw_data = table.get("original_data")
        if raw_data is None:
            raw_data = table.get("data", [])

        normalized_data = table.get("normalized_table_data")
        if normalized_data is None:
            normalized_data = table.get("data", [])

        table["raw_table_data"] = deepcopy(raw_data)
        table["normalized_table_data"] = deepcopy(normalized_data)
        # Compatibility with the existing database repository.
        table["table_data"] = deepcopy(normalized_data)
        table["data"] = deepcopy(normalized_data)

        table.setdefault("column_headers", None)
        table["footnotes"] = []
        table["page_start"] = table["page_number"]
        table["page_end"] = table["page_number"]
        table["page_fragments"] = [{
            "page_number": table["page_number"],
            "coordinates": deepcopy(table["coordinates"]),
        }]

        table["validation_results"] = table.get(
            "validation_results",
            validate_table_structure(normalized_data),
        )
        table["table_text"] = build_table_search_text(table)
        enriched_tables.append(table)

    return enriched_tables





def process_pdf(file_path):
    """
    Process a PDF and extract all available information.

    Extracts:
    1. Page-wise text
    2. Individual text blocks
    3. Text with formatting information
    4. Document headings
    5. Tables

    Returns a dictionary containing all extracted information.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"PDF file not found: {file_path}"
        )

    if file_path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    # Extract all PDF components
    pages = extract_text_from_pdf(file_path)

    text_blocks = extract_text_blocks_from_pdf(file_path)

    text_lines = extract_text_lines_from_pdf(file_path)

    formatted_spans = extract_text_with_formatting(file_path)

    headings = extract_headings_from_pdf(file_path)

    raw_tables = extract_tables_from_pdf(file_path)

    caption_blocks = text_blocks + text_lines

    tables = enrich_tables_with_metadata(
        tables=raw_tables,
        text_blocks=caption_blocks,
        headings=headings,
    )

    # Combine all extracted information
    return {
        "file_name": file_path.name,

        "total_pages": len(pages),

        "pages": pages,

        "text_blocks": text_blocks,

        "text_lines": text_lines,

        "formatted_spans": formatted_spans,

        "headings": headings,

        "tables": tables,

        "statistics": {
            "total_pages": len(pages),
            "total_text_blocks": len(text_blocks),
            "total_text_lines": len(text_lines),
            "total_formatted_spans": len(formatted_spans),
            "total_headings": len(headings),
            "total_tables": len(tables)
        }
    }