"""
Audit routes — updated to include the Functionality audit engine.

Changes from the original file
--------------------------------
1. Imported `run_functionality_audit` from app.audits.functionality.
2. Added `elif cat == "functionality":` branch inside `run_audit` (replacing
   the old stub that returned "not yet implemented").
3. Added a new standalone endpoint  POST /audit/functionality  so the engine
   can be tested in isolation from Swagger UI, just like the other audits.

Everything else is identical to the original file.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from urllib.parse import urlparse
import ipaddress
from app.schemas.audit import AuditRequest, AuditResponse, AuditResult

# ── Existing audit engines ─────────────────────────────────────────────────────
from app.audits.performance import run_lighthouse_audit
from app.audits.seo import run_seo_audit
from app.audits.accessibility import run_accessibility_audit
from app.audits.security import run_security_audit

# ── New engine added in this update ───────────────────────────────────────────
from app.audits.functionality import run_functionality_audit

router = APIRouter()

_ALL_CATEGORIES = ["performance", "seo", "accessibility", "security", "functionality"]


def _validate_url(url: str) -> None:
    """Validate URL to prevent SSRF attacks."""
    parsed = urlparse(url)
    
    # Block non-http/https schemes
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400,
            detail="Auditing private/internal URLs is not allowed."
        )
    
    # Block localhost variants
    hostname = parsed.hostname or ""
    hostname_lower = hostname.lower()
    if hostname_lower in ("localhost", "127.0.0.1", "0.0.0.0", ""):
        raise HTTPException(
            status_code=400,
            detail="Auditing private/internal URLs is not allowed."
        )
    
    # Block private IP ranges
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private:
            raise HTTPException(
                status_code=400,
                detail="Auditing private/internal URLs is not allowed."
            )
    except ValueError:
        # Not an IP address, continue
        pass


@router.post("/audit", response_model=AuditResponse, tags=["Audit"])
async def run_audit(body: AuditRequest) -> AuditResponse:
    """
    Primary workflow: runs the selected audits and returns the combined response.

    Send a POST with {"url": "https://example.com"} to run all five audits,
    or add {"categories": ["seo", "functionality"]} to run a subset.
    """
    _validate_url(str(body.url))
    categories = body.categories if body.categories else _ALL_CATEGORIES

    results = []
    for cat in categories:
        if cat == "performance":
            results.append(run_lighthouse_audit(str(body.url)))

        elif cat == "seo":
            results.append(await run_seo_audit(str(body.url)))

        elif cat == "accessibility":
            results.append(await run_accessibility_audit(str(body.url)))

        elif cat == "security":
            results.append(run_security_audit(str(body.url)))

        # ── NEW: Functionality audit now wired in ──────────────────────
        elif cat == "functionality":
            results.append(await run_functionality_audit(str(body.url)))
        # ── (end of new block) ─────────────────────────────────────────

        else:
            # Fallback for any unknown category string
            results.append(
                AuditResult(
                    audit_type=cat,
                    score=0.0,
                    metrics={},
                    findings=[],
                    recommendations=[f"{cat.capitalize()} audit engine not yet implemented."],
                )
            )

    # Overall score = average of completed audits only
    completed_results = [
        res for res in results
        if not (
            len(res.recommendations) == 1
            and "not yet implemented" in res.recommendations[0]
        )
    ]
    overall_score = (
        sum(res.score for res in completed_results) / len(completed_results)
        if completed_results
        else 0.0
    )

    return AuditResponse(
        url=str(body.url),
        timestamp=datetime.now(timezone.utc).isoformat(),
        results=results,
        overall_score=overall_score,
    )


# ── Standalone test endpoints (one per audit engine) ──────────────────────────

@router.post("/audit/performance", response_model=AuditResult, tags=["Audit"])
async def run_audit_performance(body: AuditRequest) -> AuditResult:
    """Standalone testing endpoint for the Performance audit engine."""
    _validate_url(str(body.url))
    return run_lighthouse_audit(str(body.url))


@router.post("/audit/seo", response_model=AuditResult, tags=["Audit"])
async def run_audit_seo(body: AuditRequest) -> AuditResult:
    """Standalone testing endpoint for the SEO audit engine."""
    _validate_url(str(body.url))
    return await run_seo_audit(str(body.url))


@router.post("/audit/accessibility", response_model=AuditResult, tags=["Audit"])
async def run_audit_accessibility(body: AuditRequest) -> AuditResult:
    """Standalone testing endpoint for the Accessibility audit engine."""
    _validate_url(str(body.url))
    return await run_accessibility_audit(str(body.url))


@router.post("/audit/security", response_model=AuditResult, tags=["Audit"])
async def run_audit_security(body: AuditRequest) -> AuditResult:
    """Standalone testing endpoint for the Security audit engine."""
    _validate_url(str(body.url))
    return run_security_audit(str(body.url))


# ── NEW standalone endpoint ────────────────────────────────────────────────────

@router.post("/audit/functionality", response_model=AuditResult, tags=["Audit"])
async def run_audit_functionality(body: AuditRequest) -> AuditResult:
    """
    Standalone testing endpoint for the Functionality audit engine.

    Tests:
    - Homepage loads (HTTP 200, non-empty body)
    - Navigation links detected
    - Contact form / contact page link detected
    - Internal link validation (broken link / 404 detection)
    """
    _validate_url(str(body.url))
    return await run_functionality_audit(str(body.url))