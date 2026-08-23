import requests
import json

# Try 127.0.0.1 instead of localhost
url = "http://127.0.0.1:8000/api/v1/intelligence/classify-news"
data = {
    "title": "Bitcoin Surges as Institutional Demand Hits Record Highs",
    "content": "BlackRock and Fidelity reports show massive inflows into Bitcoin ETFs, with daily volume surpassing $5 billion. Analysts expect the momentum to continue as regulatory clarity improves.",
    "source": "Reuters",
    "url": "https://reuters.com/crypto-surge"
}

try:
    response = requests.post(url, json=data, timeout=10)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
