from unittest.mock import patch

import pytest

from search.semantic_search_service import search_documents


def test_empty_query():
    with pytest.raises(ValueError, match="Search query cannot be empty"):
        search_documents("")


def test_whitespace_query():
    with pytest.raises(ValueError, match="Search query cannot be empty"):
        search_documents("   ")


@patch("search.semantic_search_service.semantic_search")
@patch("search.semantic_search_service.generate_query_embedding")
def test_search_documents(mock_embedding, mock_search):

    query = "deep learning for brain tumor detection"

    mock_embedding.return_value = [0.1] * 768

    mock_search.return_value = [
        {
            "title": "Brain Tumor Detection Using Deep Learning",
            "similarity_score": 0.85,
        }
    ]

    results = search_documents(query, limit=5)

    mock_embedding.assert_called_once_with(query)

    mock_search.assert_called_once_with(
        query_embedding=[0.1] * 768,
        limit=5,
    )

    assert len(results) == 1

    assert results[0]["title"] == (
        "Brain Tumor Detection Using Deep Learning"
    )


@patch("search.semantic_search_service.semantic_search")
@patch("search.semantic_search_service.generate_query_embedding")
def test_search_documents_no_results(mock_embedding, mock_search):

    mock_embedding.return_value = [0.1] * 768
    mock_search.return_value = []

    results = search_documents(
        "quantum computing in medicine"
    )

    assert results == []