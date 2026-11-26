from search.semantic_search_service import search_documents


def main():

    query = "machine learning methods for scientific research"

    results = search_documents(query, limit=5)

    print("\n" + "=" * 80)
    print(f"SEARCH QUERY: {query}")
    print("=" * 80)

    if not results:
        print("\nNo relevant results found.")
        return

    for index, result in enumerate(results, start=1):

        print(f"\nRESULT #{index}")
        print("-" * 80)

        print(f"Title: {result['title']}")
        print(f"Similarity Score: {result['similarity_score']:.4f}")
        print(f"Section: {result['section_title']}")
        print(f"Pages: {result['page_start']} - {result['page_end']}")

        print("\nContent:")
        print(result["content"])

        print("\n" + "-" * 80)


if __name__ == "__main__":
    main()