import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv("backend/.env")
api_key = os.environ.get("GEMINI_API_KEY")

print(f"Testing key starting with: {api_key[:10]}..." if api_key else "No key found!")

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

try:
    with urllib.request.urlopen(url) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        models = [m["name"] for m in data.get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
        print("Supported generateContent models:")
        for m in models:
            print(" -", m)
except Exception as e:
    print("Failed to list models:", e)
