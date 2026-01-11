import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file")

    genai.configure(api_key=api_key)

    print("Available models that support 'generateContent':")
    print("---------------------------------------------")

    for m in genai.list_models():
      if 'generateContent' in m.supported_generation_methods:
        print(m.name)

except Exception as e:
    print(f"An error occurred: {e}")