
from metadata.sources.pubmed import search_pubmed


if __name__ == "__main__":
    topic = "machine learning for disease detection"

    results = search_pubmed(topic, max_results=5)

    print(f"\nFound {len(results)} papers\n")

    for i, paper in enumerate(results, start=1):
        print("=" * 80)
        print(f"Paper {i}")
        print("=" * 80)

        print("Title:", paper.get("title"))
        print("Abstract:", paper.get("abstract"))
        print("Authors:", paper.get("authors"))
        print("Published:", paper.get("published_date"))
        print("DOI:", paper.get("doi"))
        print("External ID:", paper.get("external_id"))
        print("Source:", paper.get("source_name"))
        print("Paper URL:", paper.get("source_url"))
        print("PDF URL:", paper.get("pdf_url"))
        print("Matched Keywords:", paper.get("matched_keywords"))
        print()
