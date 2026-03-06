"""Test Qwen LLM via HuggingFace Space (Ollama API)"""
import os
import json
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(".env"))

API_URL = os.getenv("QWEN_API_URL", "https://vish85521-doc.hf.space/api/generate")
MODEL_NAME = os.getenv("QWEN_MODEL_NAME", "qwen3.5:397b-cloud")

prompt = '''You are a 35-year-old teacher from Colombo.
You saw an ad for Watawala Tea showing a family having tea together.
Respond in JSON format:
{"emotion": "HAPPY", "opinion": "POSITIVE", "reasoning": "Your explanation here"}'''

print(f"Testing Qwen model: {MODEL_NAME}")
print(f"API URL: {API_URL}")
print(f"Prompt: {prompt[:80]}...")
print("Sending request (this may take 30-60s on free CPU)...\n")

response = requests.post(
    API_URL,
    json={
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": True,
        "options": {
            "num_predict": 500,
            "temperature": 0.7,
        },
    },
    stream=True,
    timeout=180,
)

if response.status_code != 200:
    print(f"ERROR: HTTP {response.status_code}")
    print(response.text[:500])
    exit(1)

# Parse streaming NDJSON
full_response = ""
for line in response.iter_lines(decode_unicode=True):
    if not line or not line.strip():
        continue
    try:
        data = json.loads(line)
        if data.get("response"):
            full_response += data["response"]
            print(data["response"], end="", flush=True)
    except json.JSONDecodeError:
        continue

print(f"\n\nFull response ({len(full_response)} chars): {full_response}")
