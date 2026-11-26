
import os
import json

from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv(override=True)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY not found. Please check your .env file."
    )

# Initialize Gemini client
client = genai.Client(api_key=api_key)

MODEL_NAME = "gemini-3.8-flash"


def generate_research_keywords(question):
    """
    Convert a natural-language question into
    relevant academic research search queries.
    """

    prompt = f"""
    You are an academic research assistant.

    Analyze the user's question and identify its
    underlying research topic.

    Generate 5 to 8 relevant academic search queries.

    Requirements:
    1. Identify the central research intent.
    2. Use appropriate academic and scientific terminology.
    3. Include related concepts where relevant.
    4. Avoid unrelated or repetitive keywords.
    5. Do not answer the user's question.
    6. Return structured JSON only.

    User question: {question}
    """

    response = client.interactions.create(
        model=MODEL_NAME,
        input=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": {
                "type": "object",
                "properties": {
                    "research_topic": {
                        "type": "string"
                    },
                    "keywords": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "research_topic",
                    "keywords"
                ]
            }
        }
    )

    if not response.output_text:
        raise ValueError("Gemini returned an empty response.")

    result = json.loads(response.output_text)

    return result


if __name__ == "__main__":

    question = input(
        "Enter your research question: "
    ).strip()

    if not question:
        print("Please enter a valid question.")

    else:
        try:
            result = generate_research_keywords(question)

            print("\nResearch Topic:")
            print(result["research_topic"])

            print("\nGenerated Academic Keywords:")

            for index, keyword in enumerate(
                result["keywords"], start=1
            ):
                print(f"{index}. {keyword}")

        except Exception as error:
            print("\nKeyword generation failed:")
            print(type(error).__name__, error)
