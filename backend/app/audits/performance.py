"""
Performance audit engine using Google PageSpeed Insights API.
"""

import requests
import logging
import os

from app.core.config import settings
from app.schemas.audit import AuditResult, Finding

logger = logging.getLogger("audit_tool.performance")

def _call_pagespeed_api(url: str, strategy: str):
    """
    Calls the Google PageSpeed Insights API and returns the JSON response.
    """

    api_key = settings.GOOGLE_PAGESPEED_API_KEY

    if not api_key:
        raise ValueError(
            "GOOGLE_PAGESPEED_API_KEY is not configured in the .env file."
        )

    endpoint = settings.GOOGLE_PAGESPEED_BASE_URL

    endpoint = f"{endpoint}/runPagespeed"

    params = {
        "url": url,
        "strategy": strategy,   # "desktop" or "mobile"
        "key": api_key,
    }
    
    if strategy not in ("desktop", "mobile"):
        raise ValueError(
        "strategy must be either 'desktop' or 'mobile'"
        )

    try:
        response = requests.get(endpoint, params=params, timeout=120)

        response.raise_for_status()

        data = response.json()
        if "error" in data:
            raise RuntimeError(f"Google API returned an error :{data['error']}")

        if "lighthouseResult" not in data:
            raise RuntimeError(
                "Invalid response received from Google PageSpeed API."
            )

        return data

    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response else "Unknown"
        body = exc.response.text if exc.response else str(exc)
        raise RuntimeError(
            f"Google PageSpeed API Error ({response.status_code}): {response.text}"
        ) from exc

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Failed to connect to Google PageSpeed API: {exc}"
        ) from exc


ERROR_DESCRIPTION_LIMIT = 800
_PERF_MOBILE_GAP_THRESHOLD = 15   # Points above which a gap finding is raised


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
    Run Google PageSpeed Insights audits for both Desktop and Mobile
    and merge the results into a single AuditResult.

    The Mobile score is used as the primary performance score.
     Desktop metrics are preserved for comparison and backward compatibility.
    """
    logger.info(
    "Starting Google PageSpeed audit (Desktop + Mobile) for %s",
    url,
    )

    # ── Desktop pass ─────────────────────────────────────────────────────
    try:
         desktop_json = _call_pagespeed_api(url, "desktop")
         desktop_result = _parse_lighthouse_report(
         desktop_json["lighthouseResult"]
    )
    except Exception as e:
        desktop_result = _generate_error_result(
        url,
        str(e),
        title="Google PageSpeed Desktop Error",
    )

    # ── Mobile pass (Lighthouse default — no extra flags) ─────────────────
    try:
         mobile_json = _call_pagespeed_api(url, "mobile")
         mobile_result = _parse_lighthouse_report(
         mobile_json["lighthouseResult"]
    )
    except Exception as e:
        mobile_result = _generate_error_result(
        url,
        str(e),
        title="Google PageSpeed Mobile Error",
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
        logger.exception("Failed to parse Google PageSpeed response" )
        return _generate_error_result("", f"Failed to parse report: {exc}", title="Google PageSpeed Parse Error")


def _generate_error_result(url: str, error_msg: str, *, title: str = "Google PageSpeed Audit Failed") -> AuditResult:
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
        recommendations=["Ensure the URL is publicly accessible and the Google PageSpeed API key is valid."],
    )
