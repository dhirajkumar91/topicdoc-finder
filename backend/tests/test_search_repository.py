from unittest.mock import MagicMock, patch

import pytest

from database.search_repository import semantic_search


def test_invalid_embedding_type():

    with pytest.raises(TypeError):
        semantic_search("invalid_embedding")


def test_invalid_embedding_dimension():

    with pytest.raises(ValueError):
        semantic_search([0.1, 0.2, 0.3])


def test_invalid_limit():

    embedding = [0.1] * 768

    with pytest.raises(ValueError):
        semantic_search(embedding, limit=0)


def test_semantic_search_returns_results():

    embedding = [0.1] * 768

    mock_row = {
        "chunk_id": "chunk-123",
        "document_id": "document-123",
        "chunk_index": 1,
        "section_chunk_index": 1,
        "section_title": "Introduction",
        "parent_section_title": None,
        "page_start": 1,
        "page_end": 2,
        "content": "Machine learning research content.",
        "character_count": 34,
        "title": "Machine Learning Research",
        "abstract": "Research on machine learning.",
        "authors": ["Author A"],
        "published_date": None,
        "source_name": "arXiv",
        "source_url": "https://example.com/paper",
        "pdf_url": "https://example.com/paper.pdf",
        "file_path": "downloads/paper.pdf",
        "distance": 0.15,
    }

    mock_session = MagicMock()

    mock_session.execute.return_value.all.return_value = [
        MagicMock(_mapping=mock_row)
    ]

    mock_session_context = MagicMock()
    mock_session_context.__enter__.return_value = mock_session

    with patch(
        "database.search_repository.SessionLocal",
        return_value=mock_session_context,
    ):

        results = semantic_search(
            embedding,
            limit=5,
        )

    assert len(results) == 1

    result = results[0]

    assert result["title"] == "Machine Learning Research"
    assert result["content"] == "Machine learning research content."
    assert result["cosine_distance"] == 0.15
    assert result["similarity_score"] == 0.85

    mock_session.execute.assert_called_once()


def test_semantic_search_empty_results():

    embedding = [0.1] * 768

    mock_session = MagicMock()
    mock_session.execute.return_value.all.return_value = []

    mock_session_context = MagicMock()
    mock_session_context.__enter__.return_value = mock_session

    with patch(
        "database.search_repository.SessionLocal",
        return_value=mock_session_context,
    ):

        results = semantic_search(embedding)

    assert results == []


if __name__ == "__main__":
    print("Run this test file using pytest.")