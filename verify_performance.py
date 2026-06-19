import sys
import json
import asyncio
from fastapi.testclient import TestClient

# Add backend directory to sys.path to import app
sys.path.append('c:/Users/Windows/Desktop/website audit project/website-audit-tool/backend')
from app.main import app

client = TestClient(app)

print("Starting verification tests...")

# 1. Backend Verification: POST /audit/performance
print("\n--- 1. Backend Verification: POST /audit/performance ---")
url_to_test = "https://www.itchotels.com/in/en"
payload = {"url": url_to_test}
try:
    response = client.post("/audit/performance", json=payload)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("Response keys:", data.keys())
        print(f"Audit Type: {data.get('audit_type')}")
        print(f"Score: {data.get('score')}")
        print(f"Metrics: {json.dumps(data.get('metrics'), indent=2)}")
    else:
        print(f"Error Response: {response.text}")
except Exception as e:
    print(f"Exception occurred: {e}")

# 2. Main Workflow Verification: POST /audit
print("\n--- 2. Main Workflow Verification: POST /audit ---")
payload_workflow = {
    "url": url_to_test,
    "categories": ["performance"]
}
try:
    response_wf = client.post("/audit", json=payload_workflow)
    print(f"Status Code: {response_wf.status_code}")
    if response_wf.status_code == 200:
        data_wf = response_wf.json()
        print("Workflow Response keys:", data_wf.keys())
        results = data_wf.get("results", [])
        print(f"Results length: {len(results)}")
        if results:
            print(f"First result audit_type: {results[0].get('audit_type')}")
    else:
        print(f"Error Response: {response_wf.text}")
except Exception as e:
    print(f"Exception occurred: {e}")

# 3. Acceptance Tests
print("\n--- 3. Acceptance Tests ---")
tests = [
    {"name": "Valid URL", "payload": {"url": "https://example.com"}},
    {"name": "Invalid URL", "payload": {"url": "invalid-url-format"}},
    {"name": "Missing URL", "payload": {"categories": ["performance"]}},
    {"name": "Performance category selected", "payload": {"url": "https://example.com", "categories": ["performance"]}},
    {"name": "Multiple categories selected", "payload": {"url": "https://example.com", "categories": ["performance", "seo"]}}
]

for t in tests:
    try:
        res = client.post("/audit", json=t["payload"])
        print(f"Test '{t['name']}': Status {res.status_code}")
        if res.status_code == 422:
            print(f"  Validation Error: {res.json()['detail'][0]['msg']}")
    except Exception as e:
        print(f"Test '{t['name']}': Exception {e}")

