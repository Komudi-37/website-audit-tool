"""Performance audit engine using Lighthouse."""
import subprocess
import json
import tempfile
import logging
import os
import time
from app.schemas.audit import AuditResult, Finding

logger = logging.getLogger("audit_tool.performance")

DEFAULT_LIGHTHOUSE_TIMEOUT_SECONDS = 90
ERROR_DESCRIPTION_LIMIT = 800


def _lighthouse_timeout_seconds() -> int:
    raw = os.environ.get("LIGHTHOUSE_TIMEOUT_SECONDS", str(DEFAULT_LIGHTHOUSE_TIMEOUT_SECONDS))
    try:
        return max(30, int(raw))
    except ValueError:
        logger.warning("Invalid LIGHTHOUSE_TIMEOUT_SECONDS=%r — using default %s", raw, DEFAULT_LIGHTHOUSE_TIMEOUT_SECONDS)
        return DEFAULT_LIGHTHOUSE_TIMEOUT_SECONDS


def _classify_lighthouse_error(error_msg: str, *, timed_out: bool = False) -> str:
    if timed_out:
        return "Lighthouse Execution Timeout"
    msg_lower = error_msg.lower()
    if "timed out" in msg_lower or "timeout" in msg_lower:
        return "Lighthouse Execution Timeout"
    if "enoent" in msg_lower or "not found" in msg_lower:
        return "Lighthouse Not Available"
    if "failed to parse" in msg_lower or "json" in msg_lower:
        return "Lighthouse Report Parse Error"
    if "exited with code" in msg_lower:
        return "Lighthouse Process Error"
    return "Lighthouse Audit Failed"


def run_lighthouse_audit(url: str) -> AuditResult:
    """Run Lighthouse performance audit against a given URL."""
    timeout_seconds = _lighthouse_timeout_seconds()
    logger.info("Starting Lighthouse performance audit for %s (timeout=%ss)", url, timeout_seconds)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
        temp_path = temp_file.name

    started_at = time.perf_counter()
    command = [
        "lighthouse.cmd" if os.name == "nt" else "lighthouse",
        url,
        "--chrome-flags=--headless",
        "--output=json",
        f"--output-path={temp_path}",
        "--quiet",
    ]
    logger.info("Lighthouse command: %s", " ".join(command))

    try:
        exit_code: int | None = None
        stderr_text = ""

        try:
            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=timeout_seconds,
                stdin=subprocess.DEVNULL,
            )
            exit_code = result.returncode
            stderr_text = (result.stderr or b"").decode("utf-8", errors="replace")
            duration = time.perf_counter() - started_at
            json_exists = os.path.exists(temp_path)
            json_size = os.path.getsize(temp_path) if json_exists else 0

            logger.info(
                "Lighthouse finished in %.2fs — exit_code=%s, json_exists=%s, json_size=%s bytes",
                duration,
                exit_code,
                json_exists,
                json_size,
            )
            if stderr_text.strip():
                logger.info("Lighthouse stderr (first 500 chars): %s", stderr_text[:500])

            if exit_code != 0:
                if not json_exists:
                    detail = (
                        f"Lighthouse exited with code {exit_code} and did not produce a JSON report "
                        f"after {duration:.1f}s."
                    )
                    if stderr_text.strip():
                        detail += f" stderr: {stderr_text.strip()[:400]}"
                    logger.error(detail)
                    return _generate_error_result(url, detail, title=_classify_lighthouse_error(detail))

                if "EPERM" in stderr_text or "Permission denied" in stderr_text:
                    logger.warning(
                        "Lighthouse exited %s (Windows EPERM temp-cleanup — non-fatal). Proceeding to parse output file.",
                        exit_code,
                    )
                else:
                    logger.warning(
                        "Lighthouse exited %s but output file exists — attempting parse.",
                        exit_code,
                    )

        except subprocess.TimeoutExpired as exc:
            duration = time.perf_counter() - started_at
            json_exists = os.path.exists(temp_path)
            json_size = os.path.getsize(temp_path) if json_exists else 0
            partial_stderr = ""
            if exc.stderr:
                partial_stderr = exc.stderr.decode("utf-8", errors="replace")[:400]

            detail = (
                f"Lighthouse execution timed out after {timeout_seconds} seconds "
                f"(elapsed {duration:.1f}s). "
                f"JSON output file created: {json_exists}"
            )
            if json_exists:
                detail += f" (size: {json_size} bytes — report may be incomplete)."
            else:
                detail += ". No JSON report was written."
            if partial_stderr:
                detail += f" stderr: {partial_stderr}"

            logger.error(detail)
            return _generate_error_result(
                url,
                detail,
                title=_classify_lighthouse_error(detail, timed_out=True),
            )

        if not os.path.exists(temp_path):
            duration = time.perf_counter() - started_at
            detail = f"Lighthouse completed in {duration:.1f}s but no JSON output file was found at {temp_path}."
            logger.error(detail)
            return _generate_error_result(url, detail, title="Lighthouse Output Missing")

        with open(temp_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return _parse_lighthouse_report(data)

    except json.JSONDecodeError as exc:
        duration = time.perf_counter() - started_at
        detail = f"Failed to parse Lighthouse JSON after {duration:.1f}s: {exc}"
        logger.exception(detail)
        return _generate_error_result(url, detail, title="Lighthouse Report Parse Error")
    except Exception as exc:
        duration = time.perf_counter() - started_at
        detail = f"Unexpected Lighthouse error after {duration:.1f}s: {exc}"
        logger.exception(detail)
        return _generate_error_result(url, detail, title=_classify_lighthouse_error(str(exc)))
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as exc:
                logger.warning("Failed to delete temp file %s: %s", temp_path, exc)


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
            recommendations=recommendations,
        )

    except Exception as exc:
        logger.exception("Failed to parse Lighthouse JSON report")
        return _generate_error_result("", f"Failed to parse report: {exc}", title="Lighthouse Report Parse Error")


def _generate_error_result(url: str, error_msg: str, *, title: str = "Lighthouse Audit Failed") -> AuditResult:
    trimmed = error_msg[:ERROR_DESCRIPTION_LIMIT]
    if url:
        trimmed = f"URL: {url}\n{trimmed}"

    return AuditResult(
        audit_type="performance",
        score=0,
        metrics={},
        findings=[
            Finding(
                id="perf-error",
                title=title,
                description=trimmed,
                severity="critical",
                category="performance",
            )
        ],
        recommendations=["Ensure the URL is publicly accessible and Lighthouse is correctly installed."],
    )
