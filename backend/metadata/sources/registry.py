from metadata.sources.openalex import OpenAlexAdapter
from metadata.sources.crossref import CrossrefAdapter
from metadata.sources.arxiv import ArxivAdapter
from metadata.sources.pubmed import PubMedAdapter
from metadata.sources.semantic_scholar import SemanticScholarAdapter
from metadata.sources.core import CoreAdapter

from metadata.sources.base import BaseSourceAdapter


class SourceRegistry:

    def __init__(self):
        self._adapters: dict[str, BaseSourceAdapter] = {}

    def register(self, adapter: BaseSourceAdapter) -> None:
        source_name = adapter.source_name.lower().strip()

        if source_name in self._adapters:
            raise ValueError(f"Source '{source_name}' is already registered.")

        self._adapters[source_name] = adapter

    def get(self, source_name: str) -> BaseSourceAdapter:
        source_name = source_name.lower().strip()

        if source_name not in self._adapters:
            raise ValueError(f"Source '{source_name}' is not registered.")

        return self._adapters[source_name]

    def get_all(self) -> list[BaseSourceAdapter]:
        return list(self._adapters.values())

    def get_source_names(self) -> list[str]:
        return list(self._adapters.keys())

    def __len__(self) -> int:
        return len(self._adapters)
    

def create_default_registry() -> SourceRegistry:
    registry = SourceRegistry()

    adapters = [
        OpenAlexAdapter(),
        CrossrefAdapter(),
        ArxivAdapter(),
        PubMedAdapter(),
        SemanticScholarAdapter(),
        CoreAdapter(),
    ]

    for adapter in adapters:
        registry.register(adapter)

    return registry