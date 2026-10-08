import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = "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"

url = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

data = {
    "model": "llama-3.3-70b-versatile",
    "messages": [{"role": "user", "content": "Hello"}],
    "temperature": 0
}

response = requests.post(url, headers=headers, json=data)
print(response.status_code)
print(response.json())
