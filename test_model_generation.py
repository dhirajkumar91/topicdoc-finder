import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

models = [
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
]

for model in models:
    print(f"\nTesting: {model}")

    try:
        response = client.models.generate_content(
            model=model,
            contents="Reply with exactly: MODEL WORKING"
        )

        print("SUCCESS:", response.text)

    except Exception as error:
        print("FAILED:", error)