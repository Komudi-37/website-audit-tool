import sys
import json
import os
from fastapi.testclient import TestClient

# Add backend to Python path
sys.path.append('c:/Users/Windows/Desktop/website audit project/website-audit-tool/backend')
from app.main import app

client = TestClient(app)

print("=" * 60)
print("  ACCESSIBILITY AUDIT ENGINE VERIFICATION")
print("=" * 60)

# 1. Standalone Accessibility Endpoint
print("\n[1] POST /audit/accessibility (https://example.com)")
try:
    response = client.post("/audit/accessibility", json={"url": "https://example.com"})
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Audit Type : {data.get('audit_type')}")
        print(f"Score      : {data.get('score')}")
        print("Metrics    :")
        print(json.dumps(data.get('metrics'), indent=4))
        
        findings = data.get('findings', [])
        print(f"Findings   : {len(findings)} total")
        for f in findings[:4]:
            print(f"  - [{f.get('severity')}] {f.get('id')}: {f.get('title')}")
            
        recs = data.get('recommendations', [])
        print(f"Recommendations: {len(recs)} total")
        for rec in recs[:3]:
            print(f"  * {rec}")
            
        # Basic validation assertions
        assert data.get('audit_type') == 'accessibility'
        assert isinstance(data.get('score'), (int, float))
        assert 'total_violations' in data.get('metrics', {})
        print("\n[SUCCESS] Standalone accessibility audit endpoint checks passed.")
    else:
        print(f"Error Response: {response.text}")
except Exception as e:
    print(f"Exception: {e}")

# 2. Main Audit Endpoint with Accessibility Category
print("\n[2] POST /audit (categories: ['accessibility', 'seo'])")
try:
    response = client.post("/audit", json={"url": "https://example.com", "categories": ["accessibility", "seo"]})
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Overall Score: {data.get('overall_score')}")
        results = data.get("results", [])
        print(f"Results categories: {[r.get('audit_type') for r in results]}")
        print(f"Results scores: {[r.get('score') for r in results]}")
        
        # Verify overall score calculation
        scores = [r.get('score') for r in results if r.get('audit_type') in ('accessibility', 'seo')]
        expected_overall = sum(scores) / len(scores) if scores else 0.0
        print(f"Calculated: {expected_overall}  Response: {data.get('overall_score')}")
        assert abs(data.get('overall_score') - expected_overall) < 0.01
        print("\n[SUCCESS] Integration into main POST /audit endpoint passed.")
    else:
        print(f"Error Response: {response.text}")
except Exception as e:
    print(f"Exception: {e}")

# 3. Input Validation
print("\n[3] POST /audit/accessibility with invalid URL")
try:
    response = client.post("/audit/accessibility", json={"url": "invalid-url"})
    print(f"Status Code: {response.status_code}")
    if response.status_code == 422:
        print("Success: Correctly returned 422 validation error for invalid URL")
    else:
        print(f"Unexpected Status Code: {response.status_code}")
except Exception as e:
    print(f"Exception: {e}")
