import requests

def ask_ollama(prompt):
    r = requests.post(
        "http://127.0.0.1:11434/api/generate",
        json={
            "model": "qwen3:4b",
            "prompt": prompt,
            "stream": False
        },
        timeout=120
    )
    return r.json()["response"]
