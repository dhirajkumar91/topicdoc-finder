import re


def normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None

    doi = doi.strip().lower()

    doi = re.sub(
        r"^(https?://(dx\.)?doi\.org/|doi:\s*)",
        "",
        doi
    )

    return doi.strip()


def normalize_title(title: str | None) -> str:
    if not title:
        return ""

    title = title.lower().strip()
    title = re.sub(r"[^\w\s]", "", title)
    title = re.sub(r"\s+", " ", title)

    return title


def merge_paper_metadata(existing: dict, incoming: dict) -> dict:
    merged = existing.copy()

    for key, value in incoming.items():

        if key == "source_name":
            continue

        if key == "sources":
            merged.setdefault("sources", [])
            for source in value or []:
                if source not in merged["sources"]:
                    merged["sources"].append(source)
            continue

        if value is None or value == "":
            continue

        if key not in merged or merged[key] is None or merged[key] == "":
            merged[key] = value

    existing_sources = existing.get("sources", [])

    if existing.get("source_name"):
        existing_sources = existing_sources + [existing["source_name"]]

    incoming_sources = incoming.get("sources", [])

    if incoming.get("source_name"):
        incoming_sources = incoming_sources + [incoming["source_name"]]

    merged["sources"] = list(
        dict.fromkeys(existing_sources + incoming_sources)
    )

    merged.pop("source_name", None)

    return merged


def deduplicate_papers(papers: list[dict]) -> list[dict]:
    unique_papers = []
    doi_index = {}
    title_index = {}

    for paper in papers:
        paper = dict(paper)

        normalized_doi = normalize_doi(paper.get("doi"))
        normalized_title = normalize_title(paper.get("title"))

        duplicate_index = None

        # Stage 1: DOI matching
        if normalized_doi and normalized_doi in doi_index:
            duplicate_index = doi_index[normalized_doi]

        # Stage 2: Compatible title matching
        elif normalized_title and normalized_title in title_index:
            for candidate_index in title_index[normalized_title]:
                existing = unique_papers[candidate_index]
                existing_doi = normalize_doi(existing.get("doi"))

                # Do not merge papers with conflicting DOIs
                if normalized_doi and existing_doi:
                    if normalized_doi != existing_doi:
                        continue

                duplicate_index = candidate_index
                break

        if duplicate_index is not None:
            existing = unique_papers[duplicate_index]

            merged = merge_paper_metadata(existing, paper)

            unique_papers[duplicate_index] = merged

            # Update DOI index
            merged_doi = normalize_doi(merged.get("doi"))

            if merged_doi:
                doi_index[merged_doi] = duplicate_index

        else:
            paper["sources"] = list(
                dict.fromkeys(
                    paper.get("sources", [])
                    + ([paper["source_name"]] if paper.get("source_name") else [])
                )
            )

            paper.pop("source_name", None)

            index = len(unique_papers)
            unique_papers.append(paper)

            if normalized_doi:
                doi_index[normalized_doi] = index

            if normalized_title:
                title_index.setdefault(normalized_title, []).append(index)

    return unique_papers