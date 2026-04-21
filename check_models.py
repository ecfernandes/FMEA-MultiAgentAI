"""Script to list Gemini models available for the configured API key."""
import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure API key
api_key = os.getenv("UTCLLM_API_KEY")
if not api_key:
    print("❌ UTCLLM_API_KEY not found in .env file")
    exit(1)

genai.configure(api_key=api_key)

print("=" * 70)
print("GEMINI MODELS AVAILABLE FOR YOUR API KEY")
print("=" * 70)
print()

# List all models
for model in genai.list_models():
    # Filter only models that support generateContent
    if 'generateContent' in model.supported_generation_methods:
        print(f"✅ Name: {model.name}")
        print(f"   Description: {model.display_name}")
        print(f"   Methods: {', '.join(model.supported_generation_methods)}")
        print()

print("=" * 70)
print("Use one of the names above (e.g., 'gemini-pro') in your application")
print("=" * 70)
