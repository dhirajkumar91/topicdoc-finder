
import os

from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv(override=True)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env")

# Initialize Gemini client
client = genai.Client(api_key=api_key)

print("Gemini API connection initialized.")

try:
    print("\nChecking available text-generation models...\n")

    models = client.models.list()

    count = 0

    for model in models:
        supported_actions = model.supported_actions or []

        if "generateContent" in supported_actions:
            print(model.name)
            count += 1

    print(f"\nTotal available text-generation models: {count}")

except Exception as error:
    print("\nGemini API test failed:")
    print(type(error).__name__, error)
