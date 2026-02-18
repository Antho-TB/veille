import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load ENV
env_path = os.path.join(os.getcwd(), "config/.env")
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found in .env")
    exit()

genai.configure(api_key=api_key)

print("--- Available Gemini Models ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name} (Display: {m.display_name})")
except Exception as e:
    print(f"Error listing models: {e}")
