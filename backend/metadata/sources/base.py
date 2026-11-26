from abc import ABC, abstractmethod


class BaseSourceAdapter(ABC):
    """
    Base interface for academic research metadata source adapters.
    """

    source_name: str

    @abstractmethod
    def search(self, topic: str, max_results: int = 10) -> list[dict]:
        """
        Search the source for research papers.

        Args:
            topic: Research topic or query.
            max_results: Maximum number of results to return.

        Returns:
            A list of normalized paper metadata dictionaries.
        """
        pass