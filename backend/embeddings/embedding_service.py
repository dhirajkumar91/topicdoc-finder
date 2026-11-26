
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

MODEL_NAME = "gemini-embedding-2"
EMBEDDING_DIMENSION = 768

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from environment variables.")

client = genai.Client(api_key=API_KEY)


def generate_document_embedding(text, title=None):
    """
    Generate an embedding for a research-paper text chunk.

    Returns a list of 768 floating-point numbers.
    """

    if not text or not text.strip():
        raise ValueError("Text cannot be empty.")

    document_title = title.strip() if title and title.strip() else "none"

    formatted_text = (
        f"title: {document_title} | text: {text.strip()}"
    )

    response = client.models.embed_content(
        model=MODEL_NAME,
        contents=formatted_text,
        config=types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIMENSION
        ),
    )

    embedding = response.embeddings[0].values

    if len(embedding) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Expected {EMBEDDING_DIMENSION} dimensions, "
            f"received {len(embedding)}."
        )

    return embedding


def generate_query_embedding(query):
    """
    Generate an embedding for a user's search query.
    """

    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    formatted_query = (
        f"task: search result | query: {query.strip()}"
    )

    response = client.models.embed_content(
        model=MODEL_NAME,
        contents=formatted_query,
        config=types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIMENSION
        ),
    )

    embedding = response.embeddings[0].values

    if len(embedding) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Expected {EMBEDDING_DIMENSION} dimensions, "
            f"received {len(embedding)}."
        )

    return embedding
