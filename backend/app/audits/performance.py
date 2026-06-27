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
_PERF_MOBILE_GAP_THRESHOLD = 15   # Points above which a gap finding is raised


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


def _run_lighthouse_raw(
    url: str, extra_flags: list[str]
) -> "tuple[dict | None, AuditResult | None]":
    """
    Execute one Lighthouse pass and return ``(parsed_json_dict, None)`` on
    success, or ``(None, error_AuditResult)`` on any failure.

    ``extra_flags`` are appended verbatim to the Lighthouse command, e.g.
    ``["--preset=desktop"]`` for a desktop run or ``[]`` for the mobile default.
    """
    timeout_seconds = _lighthouse_timeout_seconds()
    preset_label = "desktop" if "--preset=desktop" in extra_flags else "mobile"
    logger.info(
        "Starting Lighthouse [%s] audit for %s (timeout=%ss)",
        preset_label, url, timeout_seconds,
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
        temp_path = temp_file.name

    started_at = time.perf_counter()
    npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
    command = [
        npx_cmd,
        "lighthouse",
        url,
        "--chrome-flags=--headless",
        "--output=json",
        f"--output-path={temp_path}",
        "--quiet",
        *extra_flags,
    ]
    logger.info("Lighthouse [%s] command: %s", preset_label, " ".join(command))
    print(f"LIGHTHOUSE COMMAND [{preset_label.upper()}] =", command)

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
                "Lighthouse [%s] finished in %.2fs — exit_code=%s, json_exists=%s, json_size=%s bytes",
                preset_label, duration, exit_code, json_exists, json_size,
            )
            if stderr_text.strip():
                logger.info(
                    "Lighthouse [%s] stderr (first 500 chars): %s",
                    preset_label, stderr_text[:500],
                )

            if exit_code != 0:
                if not json_exists:
                    detail = (
                        f"Lighthouse [{preset_label}] exited with code {exit_code} and did not "
                        f"produce a JSON report after {duration:.1f}s."
                    )
                    if stderr_text.strip():
                        detail += f" stderr: {stderr_text.strip()[:400]}"
                    logger.error(detail)
                    return None, _generate_error_result(
                        url, detail, title=_classify_lighthouse_error(detail)
                    )

                if "EPERM" in stderr_text or "Permission denied" in stderr_text:
                    logger.warning(
                        "Lighthouse [%s] exited %s (Windows EPERM temp-cleanup — non-fatal). "
                        "Proceeding to parse output file.",
                        preset_label, exit_code,
                    )
                else:
                    logger.warning(
                        "Lighthouse [%s] exited %s but output file exists — attempting parse.",
                        preset_label, exit_code,
                    )

        except subprocess.TimeoutExpired as exc:
            duration = time.perf_counter() - started_at
            json_exists = os.path.exists(temp_path)
            json_size = os.path.getsize(temp_path) if json_exists else 0
            partial_stderr = ""
            if exc.stderr:
                partial_stderr = exc.stderr.decode("utf-8", errors="replace")[:400]

            detail = (
                f"Lighthouse [{preset_label}] timed out after {timeout_seconds}s "
                f"(elapsed {duration:.1f}s). JSON output created: {json_exists}"
            )
            if json_exists:
                detail += f" (size: {json_size} bytes — report may be incomplete)."
            else:
                detail += ". No JSON report was written."
            if partial_stderr:
                detail += f" stderr: {partial_stderr}"

            logger.error(detail)
            return None, _generate_error_result(
                url, detail, title=_classify_lighthouse_error(detail, timed_out=True)
            )

        if not os.path.exists(temp_path):
            duration = time.perf_counter() - started_at
            detail = (
                f"Lighthouse [{preset_label}] completed in {duration:.1f}s "
                f"but no JSON output file was found at {temp_path}."
            )
            logger.error(detail)
            return None, _generate_error_result(url, detail, title="Lighthouse Output Missing")

        with open(temp_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data, None

    except json.JSONDecodeError as exc:
        duration = time.perf_counter() - started_at
        detail = f"Failed to parse Lighthouse [{preset_label}] JSON after {duration:.1f}s: {exc}"
        logger.exception(detail)
        return None, _generate_error_result(url, detail, title="Lighthouse Report Parse Error")
    except Exception as exc:
        duration = time.perf_counter() - started_at
        detail = f"Unexpected Lighthouse [{preset_label}] error after {duration:.1f}s: {exc}"
        logger.exception(detail)
        return None, _generate_error_result(url, detail, title=_classify_lighthouse_error(str(exc)))
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as exc:
                logger.warning("Failed to delete temp file %s: %s", temp_path, exc)


def _merge_desktop_mobile(
    url: str, desktop: AuditResult, mobile: AuditResult
) -> AuditResult:
    """
    Merge Desktop and Mobile ``AuditResult`` objects into a single combined
    ``AuditResult``.

    Metric key strategy:
    - ``desktop_<key>`` / ``mobile_<key>`` — prefixed versions of every
      metric returned by each Lighthouse run.
    - Plain ``<key>`` — mirrors the desktop values for backward compatibility
      (e.g., existing code that reads ``metrics.fcp`` keeps working).
    - ``desktop_score``, ``mobile_score``, ``performance_gap`` — explicit
      top-level keys for the frontend score-badge section.

    Primary ``score`` field = Mobile score (industry benchmark default).
    """
    desktop_score = int(desktop.score)
    mobile_score = int(mobile.score)
    performance_gap = desktop_score - mobile_score

    # Build prefixed metric dicts
    desktop_metrics = {f"desktop_{k}": v for k, v in desktop.metrics.items()}
    mobile_metrics  = {f"mobile_{k}": v  for k, v in mobile.metrics.items()}

    combined_metrics: dict = {
        # Backward-compatible plain keys mirror desktop for stability
        **desktop.metrics,
        # Prefixed desktop + mobile metrics
        **desktop_metrics,
        **mobile_metrics,
        # Explicit score / gap keys consumed by the frontend
        "desktop_score":    desktop_score,
        "mobile_score":     mobile_score,
        "performance_gap":  performance_gap,
    }

    # Prefix finding titles so users can distinguish Desktop vs Mobile issues
    desktop_findings = [
        Finding(
            id=f"desktop-{f.id}",
            title=f"[Desktop] {f.title}",
            description=f.description,
            severity=f.severity,
            category=f.category,
        )
        for f in desktop.findings
    ]
    mobile_findings = [
        Finding(
            id=f"mobile-{f.id}",
            title=f"[Mobile] {f.title}",
            description=f.description,
            severity=f.severity,
            category=f.category,
        )
        for f in mobile.findings
    ]

    # Optional performance-gap warning finding
    gap_findings: list[Finding] = []
    gap_recs:     list[str]     = []
    if performance_gap > _PERF_MOBILE_GAP_THRESHOLD:
        gap_findings.append(
            Finding(
                id="perf-mobile-gap",
                title="Significant Mobile Performance Gap",
                description=(
                    f"Desktop score ({desktop_score}/100) is {performance_gap} points higher than "
                    f"Mobile ({mobile_score}/100). The site performs significantly worse on mobile devices."
                ),
                severity="warning",
                category="performance",
            )
        )
        gap_recs = [
            "Optimize images with responsive srcset and modern formats (WebP/AVIF) to reduce mobile data load.",
            "Reduce and defer JavaScript bundles — mobile CPUs are significantly slower than desktop.",
            "Eliminate render-blocking resources and leverage browser caching for mobile rendering.",
        ]

    # Merge and deduplicate all recommendations
    all_recs = list(dict.fromkeys(
        desktop.recommendations + mobile.recommendations + gap_recs
    ))

    return AuditResult(
        audit_type="performance",
        score=float(mobile_score),   # Primary score = Mobile (industry benchmark)
        metrics=combined_metrics,
        findings=desktop_findings + mobile_findings + gap_findings,
        recommendations=all_recs,
    )


def run_lighthouse_audit(url: str) -> AuditResult:
    """
    Run Desktop then Mobile Lighthouse audits sequentially and return a
    merged ``AuditResult``.

    The primary ``score`` is the Mobile score. Both score sets plus all Core
    Web Vitals are available in ``metrics`` under ``desktop_*`` / ``mobile_*``
    prefixes, with plain (non-prefixed) keys preserved for backward
    compatibility.
    """
    logger.info("Starting dual-mode (Desktop + Mobile) Lighthouse audit for %s", url)

    # ── Desktop pass ─────────────────────────────────────────────────────
    desktop_data, desktop_err = _run_lighthouse_raw(url, ["--preset=desktop"])
    desktop_result: AuditResult = (
        _parse_lighthouse_report(desktop_data)
        if desktop_data is not None
        else desktop_err  # type: ignore[assignment]
    )

    # ── Mobile pass (Lighthouse default — no extra flags) ─────────────────
    mobile_data, mobile_err = _run_lighthouse_raw(url, [])
    mobile_result: AuditResult = (
        _parse_lighthouse_report(mobile_data)
        if mobile_data is not None
        else mobile_err  # type: ignore[assignment]
    )

    # ── Merge both results ────────────────────────────────────────────────
    return _merge_desktop_mobile(url, desktop_result, mobile_result)


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
