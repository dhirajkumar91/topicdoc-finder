from metadata.sources.crossref import search_crossref


topic = "machine learning for disease detection"

papers = search_crossref(topic, max_results=5)

print(f"\nFound {len(papers)} papers for: {topic}\n")

for index, paper in enumerate(papers, start=1):

    print("=" * 80)
    print(f"Paper {index}")
    print("=" * 80)

    for key, value in paper.items():
        print(f"{key}: {value}")

    print()