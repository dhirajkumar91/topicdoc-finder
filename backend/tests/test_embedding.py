
from embeddings.embedding_service import (
    generate_document_embedding,
    generate_query_embedding,
)


if __name__ == "__main__":

    # Test document embedding
    document_text = """
    Machine learning is a subset of artificial intelligence
    that enables computer systems to learn patterns from data.
    """

    document_embedding = generate_document_embedding(
        text=document_text,
        title="Introduction to Machine Learning",
    )

    print("\n========== DOCUMENT EMBEDDING ==========")
    print("Embedding dimensions:", len(document_embedding))
    print("First five values:", document_embedding[:5])

    # Test query embedding
    query = "How do machine learning systems learn from data?"

    query_embedding = generate_query_embedding(query)

    print("\n========== QUERY EMBEDDING ==========")
    print("Embedding dimensions:", len(query_embedding))
    print("First five values:", query_embedding[:5])

    print("\nEmbedding generation successful!")
