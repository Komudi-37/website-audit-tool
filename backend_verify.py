"""
Comprehensive verification script for Website Audit Tool.
Tests all backend endpoints and generates PASS/FAIL report.
"""
import sys
import json

sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

PASS = "PASS"
FAIL = "FAIL"
PARTIAL = "PARTIAL"

results = {}

print("=" * 60)
print("  WEBSITE AUDIT TOOL - COMPLETE VERIFICATION REPORT")
print("=" * 60)

# ─────────────────────────────────────────────────────────────
# 1. HEALTH CHECK
# ─────────────────────────────────────────────────────────────
print("\n[1] GET /health")
try:
    r = client.get("/health")
    if r.status_code == 200 and r.json().get("status") == "ok":
        print("  Status: 200  Body:", r.json())
        results["health_endpoint"] = PASS
    else:
        print("  FAIL - Status:", r.status_code, "Body:", r.text[:200])
        results["health_endpoint"] = FAIL
except Exception as e:
    print("  EXCEPTION:", e)
    results["health_endpoint"] = FAIL

# ─────────────────────────────────────────────────────────────
# 2. POST /audit/performance
# ─────────────────────────────────────────────────────────────
print("\n[2] POST /audit/performance (https://example.com)")
try:
    r = client.post("/audit/performance", json={"url": "https://example.com"})
    print("  HTTP Status:", r.status_code)
    if r.status_code == 200:
        d = r.json()
        print("  audit_type :", d.get("audit_type"))
        print("  score      :", d.get("score"))
        metrics = d.get("metrics", {})
        print("  metrics    :", json.dumps(metrics, indent=6))
        findings = d.get("findings", [])
        print("  findings   :", len(findings), "total")
        for f in findings:
            print("    [" + f["severity"] + "] " + f["title"] + " — " + f["description"])
        recs = d.get("recommendations", [])
        print("  recommendations:", len(recs), "total")
        for rec in recs:
            print("    *", rec)

        # Verify metrics structure
        metric_keys = ["fcp", "lcp", "cls", "tti", "speed_index", "total_blocking_time"]
        has_metrics = all(k in metrics for k in metric_keys)
        has_score = isinstance(d.get("score"), (int, float))
        has_findings = len(findings) > 0
        has_type = d.get("audit_type") == "performance"

        if has_type and has_score and has_metrics and has_findings:
            results["performance_endpoint"] = PASS
            results["performance_metric_extraction"] = PASS
            results["performance_findings"] = PASS
        elif has_type and has_score:
            results["performance_endpoint"] = PASS
            results["performance_metric_extraction"] = PARTIAL
            results["performance_findings"] = PARTIAL
        else:
            results["performance_endpoint"] = FAIL
            results["performance_metric_extraction"] = FAIL
            results["performance_findings"] = FAIL
    else:
        print("  ERROR:", r.text[:500])
        results["performance_endpoint"] = FAIL
        results["performance_metric_extraction"] = FAIL
        results["performance_findings"] = FAIL
except Exception as e:
    print("  EXCEPTION:", e)
    results["performance_endpoint"] = FAIL
    results["performance_metric_extraction"] = FAIL
    results["performance_findings"] = FAIL

# ─────────────────────────────────────────────────────────────
# 3. POST /audit/seo
# ─────────────────────────────────────────────────────────────
print("\n[3] POST /audit/seo (https://example.com)")
try:
    r = client.post("/audit/seo", json={"url": "https://example.com"})
    print("  HTTP Status:", r.status_code)
    if r.status_code == 200:
        d = r.json()
        print("  audit_type :", d.get("audit_type"))
        print("  score      :", d.get("score"))
        metrics = d.get("metrics", {})
        print("  metrics    :", json.dumps(metrics, indent=6))
        findings = d.get("findings", [])
        print("  findings   :", len(findings), "total")
        for f in findings:
            print("    [" + f["severity"] + "] " + f["id"] + ": " + f["title"])
        recs = d.get("recommendations", [])
        print("  recommendations:", len(recs), "total")
        for rec in recs:
            print("    *", rec)

        # Check which SEO checks are implemented
        finding_ids = [f["id"] for f in findings]
        seo_checks = {
            "title_tag": any("title" in fid for fid in finding_ids),
            "meta_description": any("meta-desc" in fid for fid in finding_ids),
            "h1": any("h1" in fid for fid in finding_ids),
            "image_alt": any("img-alt" in fid for fid in finding_ids),
        }
        print("\n  SEO Check Coverage:")
        for check, present in seo_checks.items():
            print("    " + check + ":", PASS if present else FAIL)

        # Check missing SEO specs
        print("\n  Missing from spec:")
        missing = []
        if "canonical_tag" not in str(finding_ids) and "canonical" not in str(metrics):
            missing.append("Canonical Tag check")
            print("    * Canonical Tag check — NOT IMPLEMENTED")
        if "robots" not in str(metrics) and not any("robots" in fid for fid in finding_ids):
            missing.append("robots.txt check")
            print("    * robots.txt check — NOT IMPLEMENTED")
        if "sitemap" not in str(metrics) and not any("sitemap" in fid for fid in finding_ids):
            missing.append("sitemap.xml check")
            print("    * sitemap.xml check — NOT IMPLEMENTED")
        if not any("broken" in fid or "link" in fid for fid in finding_ids):
            missing.append("Broken Link Detection")
            print("    * Broken Link Detection — NOT IMPLEMENTED")
        if not any("index" in fid for fid in finding_ids):
            missing.append("Indexability check")
            print("    * Indexability check — NOT IMPLEMENTED")

        has_type = d.get("audit_type") == "seo"
        has_score = isinstance(d.get("score"), (int, float))
        has_findings = len(findings) > 0
        core_checks_pass = all(seo_checks.values())

        if has_type and has_score and has_findings and core_checks_pass and len(missing) == 0:
            results["seo_endpoint"] = PASS
            results["seo_checks"] = PASS
        elif has_type and has_score and has_findings:
            results["seo_endpoint"] = PASS
            results["seo_checks"] = PARTIAL
        else:
            results["seo_endpoint"] = FAIL
            results["seo_checks"] = FAIL
    else:
        print("  ERROR:", r.text[:500])
        results["seo_endpoint"] = FAIL
        results["seo_checks"] = FAIL
except Exception as e:
    print("  EXCEPTION:", e)
    results["seo_endpoint"] = FAIL
    results["seo_checks"] = FAIL

# ─────────────────────────────────────────────────────────────
# 4. POST /audit (full workflow — performance only)
# ─────────────────────────────────────────────────────────────
print("\n[4] POST /audit (categories: [performance])")
try:
    r = client.post("/audit", json={"url": "https://example.com", "categories": ["performance"]})
    print("  HTTP Status:", r.status_code)
    if r.status_code == 200:
        d = r.json()
        print("  url        :", d.get("url"))
        print("  timestamp  :", d.get("timestamp"))
        print("  overall_score:", d.get("overall_score"))
        results_list = d.get("results", [])
        print("  results    :", len(results_list), "total")
        for res in results_list:
            print("    audit_type:", res.get("audit_type"), "score:", res.get("score"))
        perf_present = any(r.get("audit_type") == "performance" for r in results_list)
        if r.status_code == 200 and perf_present:
            results["full_audit_performance"] = PASS
        else:
            results["full_audit_performance"] = FAIL
    else:
        print("  ERROR:", r.text[:500])
        results["full_audit_performance"] = FAIL
except Exception as e:
    print("  EXCEPTION:", e)
    results["full_audit_performance"] = FAIL

# ─────────────────────────────────────────────────────────────
# 5. POST /audit (full workflow — seo only)
# ─────────────────────────────────────────────────────────────
print("\n[5] POST /audit (categories: [seo])")
try:
    r = client.post("/audit", json={"url": "https://example.com", "categories": ["seo"]})
    print("  HTTP Status:", r.status_code)
    if r.status_code == 200:
        d = r.json()
        results_list = d.get("results", [])
        print("  results    :", len(results_list), "total")
        for res in results_list:
            print("    audit_type:", res.get("audit_type"), "score:", res.get("score"))
        seo_present = any(r.get("audit_type") == "seo" for r in results_list)
        if r.status_code == 200 and seo_present:
            results["full_audit_seo"] = PASS
        else:
            results["full_audit_seo"] = FAIL
    else:
        print("  ERROR:", r.text[:500])
        results["full_audit_seo"] = FAIL
except Exception as e:
    print("  EXCEPTION:", e)
    results["full_audit_seo"] = FAIL

# ─────────────────────────────────────────────────────────────
# 6. POST /audit (both performance + seo)
# ─────────────────────────────────────────────────────────────
print("\n[6] POST /audit (categories: [performance, seo])")
try:
    r = client.post("/audit", json={"url": "https://example.com", "categories": ["performance", "seo"]})
    print("  HTTP Status:", r.status_code)
    if r.status_code == 200:
        d = r.json()
        results_list = d.get("results", [])
        print("  results    :", len(results_list), "total")
        for res in results_list:
            print("    audit_type:", res.get("audit_type"), "score:", res.get("score"))
        both = (any(r.get("audit_type") == "performance" for r in results_list) and
                any(r.get("audit_type") == "seo" for r in results_list))
        results["full_audit_both"] = PASS if both else FAIL
    else:
        print("  ERROR:", r.text[:500])
        results["full_audit_both"] = FAIL
except Exception as e:
    print("  EXCEPTION:", e)
    results["full_audit_both"] = FAIL

# ─────────────────────────────────────────────────────────────
# 7. Validation: Invalid URL
# ─────────────────────────────────────────────────────────────
print("\n[7] Validation — invalid URL")
try:
    r = client.post("/audit", json={"url": "not-a-url"})
    print("  HTTP Status:", r.status_code)
    if r.status_code == 422:
        print("  Correct: 422 Unprocessable Entity returned")
        results["input_validation"] = PASS
    else:
        print("  UNEXPECTED:", r.text[:200])
        results["input_validation"] = FAIL
except Exception as e:
    print("  EXCEPTION:", e)
    results["input_validation"] = FAIL

# ─────────────────────────────────────────────────────────────
# 8. Validation: Missing URL
# ─────────────────────────────────────────────────────────────
print("\n[8] Validation — missing URL")
try:
    r = client.post("/audit", json={"categories": ["performance"]})
    print("  HTTP Status:", r.status_code)
    if r.status_code == 422:
        print("  Correct: 422 returned for missing url")
        results["missing_url_validation"] = PASS
    else:
        print("  UNEXPECTED:", r.text[:200])
        results["missing_url_validation"] = FAIL
except Exception as e:
    print("  EXCEPTION:", e)
    results["missing_url_validation"] = FAIL

# ─────────────────────────────────────────────────────────────
# 9. Unimplemented categories stub
# ─────────────────────────────────────────────────────────────
print("\n[9] Unimplemented categories stub (accessibility, security, functionality)")
try:
    r = client.post("/audit", json={"url": "https://example.com", "categories": ["accessibility", "security", "functionality"]})
    print("  HTTP Status:", r.status_code)
    if r.status_code == 200:
        d = r.json()
        results_list = d.get("results", [])
        print("  results:", len(results_list), "total")
        for res in results_list:
            print("    audit_type:", res.get("audit_type"), "score:", res.get("score"), "recs:", res.get("recommendations"))
        all_stub = all(res.get("score") == 0.0 for res in results_list)
        results["unimplemented_stub"] = PASS if all_stub else PARTIAL
    else:
        print("  ERROR:", r.text[:200])
        results["unimplemented_stub"] = FAIL
except Exception as e:
    print("  EXCEPTION:", e)
    results["unimplemented_stub"] = FAIL

# ─────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────
print()
print("=" * 60)
print("  BACKEND VERIFICATION SUMMARY")
print("=" * 60)
for key, val in results.items():
    icon = "✅" if val == PASS else ("⚠️" if val == PARTIAL else "❌")
    print(f"  {icon}  {key:<40} {val}")

passed = sum(1 for v in results.values() if v == PASS)
partial = sum(1 for v in results.values() if v == PARTIAL)
failed = sum(1 for v in results.values() if v == FAIL)
total = len(results)
print()
print(f"  TOTAL: {passed}/{total} PASS   {partial} PARTIAL   {failed} FAIL")
print("=" * 60)
