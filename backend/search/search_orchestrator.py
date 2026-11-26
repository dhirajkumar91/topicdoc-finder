from search.deduplication import deduplicate_papers
from metadata.sources.registry import create_default_registry


class SearchOrchestrator:

    def __init__(self):
        self.registry = create_default_registry()

    def search(self, topic: str, max_results: int = 10) -> dict:
        if not topic or not topic.strip():
            raise ValueError("Search topic cannot be empty.")

        papers = []
        errors = {}

        for adapter in self.registry.get_all():
            source_name = adapter.source_name

            try:
                source_results = adapter.search(
                    topic=topic,
                    max_results=max_results
                )

                for paper in source_results:
                    paper = dict(paper)
                    paper["source_name"] = source_name
                    papers.append(paper)

            except Exception as e:
                errors[source_name] = str(e)

        unique_papers = deduplicate_papers(papers)

        return {
            "papers": unique_papers,
            "errors": errors
        }