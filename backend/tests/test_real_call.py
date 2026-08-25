import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv("backend/.env")
api_key = os.environ.get("GEMINI_API_KEY")

models_to_test = ["models/gemini-2.5-flash", "models/gemini-flash-latest", "gemini-2.5-flash", "models/gemini-2.5-pro"]

for m in models_to_test:
    model_path = m if m.startswith("models/") else f"models/{m}"
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent?key={api_key}"
    payload = {
        "contents": [{
            "parts": [{"text": "Respond with exactly: Gemini connection successful."}]
        }]
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            print(f"SUCCESS with '{m}': {text}")
            break
    except Exception as e:
        print(f"Failed with '{m}': {e}")
