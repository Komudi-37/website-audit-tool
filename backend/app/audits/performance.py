"""Performance audit engine using Lighthouse."""
import subprocess
import json
import tempfile
import logging
import os
from app.schemas.audit import AuditResult, Finding

logger = logging.getLogger("audit_tool.performance")

def run_lighthouse_audit(url: str) -> AuditResult:
    """Run Lighthouse performance audit against a given URL."""
    logger.info(f"Starting Lighthouse performance audit for {url}")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
        temp_path = temp_file.name

    try:
        command = [
            "lighthouse",
            url,
            "--chrome-flags=--headless",
            "--output=json",
            f"--output-path={temp_path}",
            "--quiet"
        ]
        
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Lighthouse failed with exit code {result.returncode}")
            logger.error(f"Stderr: {result.stderr}")
            return _generate_error_result(url, f"Lighthouse execution failed: {result.stderr}")

        with open(temp_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return _parse_lighthouse_report(data)

    except Exception as e:
        logger.exception(f"Error running lighthouse for {url}")
        return _generate_error_result(url, str(e))
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_path}: {e}")

def _parse_lighthouse_report(data: dict) -> AuditResult:
    try:
        score_val = data.get("categories", {}).get("performance", {}).get("score", 0)
        score = round((score_val or 0) * 100)

        audits = data.get("audits", {})
        
        fcp_raw = audits.get("first-contentful-paint", {})
        lcp_raw = audits.get("largest-contentful-paint", {})
        cls_raw = audits.get("cumulative-layout-shift", {})
        tti_raw = audits.get("interactive", {})
        si_raw = audits.get("speed-index", {})
        tbt_raw = audits.get("total-blocking-time", {})

        metrics = {
            "fcp": fcp_raw.get("displayValue", ""),
            "lcp": lcp_raw.get("displayValue", ""),
            "cls": cls_raw.get("displayValue", ""),
            "tti": tti_raw.get("displayValue", ""),
            "speed_index": si_raw.get("displayValue", ""),
            "total_blocking_time": tbt_raw.get("displayValue", ""),
        }

        findings = []
        recommendations = []

        if score < 50:
            findings.append(Finding(id="perf-score-high", title="Low Performance Score", description=f"Score is {score}/100", severity="critical", category="performance"))
            recommendations.append("Major performance overhaul required. Focus on core web vitals.")
        elif score < 90:
            findings.append(Finding(id="perf-score-med", title="Average Performance Score", description=f"Score is {score}/100", severity="warning", category="performance"))
        else:
            findings.append(Finding(id="perf-score-low", title="Good Performance Score", description=f"Score is {score}/100", severity="pass", category="performance"))

        lcp_val = lcp_raw.get("numericValue", 0)
        if lcp_val > 4000:
            findings.append(Finding(id="lcp-high", title="High LCP", description=metrics["lcp"], severity="warning", category="performance"))
            recommendations.append("Recommend optimizing large content and images.")

        tti_val = tti_raw.get("numericValue", 0)
        if tti_val > 10000:
            findings.append(Finding(id="tti-high", title="High TTI", description=metrics["tti"], severity="warning", category="performance"))
            recommendations.append("Recommend reducing JavaScript execution time.")

        tbt_val = tbt_raw.get("numericValue", 0)
        if tbt_val > 300:
            findings.append(Finding(id="tbt-high", title="High Total Blocking Time", description=metrics["total_blocking_time"], severity="warning", category="performance"))
            recommendations.append("Recommend reducing blocking scripts.")

        fcp_val = fcp_raw.get("numericValue", 0)
        if fcp_val > 3000:
            findings.append(Finding(id="fcp-high", title="High FCP", description=metrics["fcp"], severity="warning", category="performance"))
            recommendations.append("Recommend improving server response and render path.")

        cls_val = cls_raw.get("numericValue", 0)
        if cls_val > 0.1:
            findings.append(Finding(id="cls-high", title="High CLS", description=metrics["cls"], severity="warning", category="performance"))
            recommendations.append("Recommend stabilizing layout elements.")

        recommendations = list(dict.fromkeys(recommendations))

        return AuditResult(
            audit_type="performance",
            score=score,
            metrics=metrics,
            findings=findings,
            recommendations=recommendations
        )

    except Exception as e:
        logger.exception("Failed to parse Lighthouse JSON report")
        return _generate_error_result("", f"Failed to parse report: {e}")

def _generate_error_result(url: str, error_msg: str) -> AuditResult:
    return AuditResult(
        audit_type="performance",
        score=0,
        metrics={},
        findings=[
            Finding(
                id="perf-error",
                title="Lighthouse Audit Failed",
                description=error_msg[:200],
                severity="critical",
                category="performance"
            )
        ],
        recommendations=["Ensure the URL is publicly accessible and Lighthouse is correctly installed."]
    )
