"""Audit route — Phase 1 stub (schema-compatible response)."""
from datetime import datetime, timezone
from fastapi import APIRouter
from app.schemas.audit import AuditRequest, AuditResponse, AuditResult
from app.audits.performance import run_lighthouse_audit
from app.audits.seo import run_seo_audit
from app.audits.accessibility import run_accessibility_audit
from app.audits.security import run_security_audit
router = APIRouter()

_ALL_CATEGORIES = ["performance", "seo", "accessibility", "security", "functionality"]


@router.post("/audit", response_model=AuditResponse, tags=["Audit"])
async def run_audit(body: AuditRequest) -> AuditResponse:
    """
    Primary workflow: runs the selected audits and returns the combined response.
    """
    categories = body.categories if body.categories else _ALL_CATEGORIES

    results = []
    for cat in categories:
        if cat == "performance":
            results.append(run_lighthouse_audit(str(body.url)))
        elif cat == "seo":
            results.append(run_seo_audit(str(body.url)))
        elif cat == "accessibility":
            results.append(await run_accessibility_audit(str(body.url)))
        elif cat == "security":
            results.append(run_security_audit(str(body.url)))
        else:
            results.append(
                AuditResult(
                    audit_type=cat,
                    score=0.0,
                    metrics={},
                    findings=[],
                    recommendations=[f"{cat.capitalize()} audit engine not yet implemented."],
                )
            )

    completed_results = [
        res for res in results
        if not (len(res.recommendations) == 1 and "not yet implemented" in res.recommendations[0])
    ]
    overall_score = sum(res.score for res in completed_results) / len(completed_results) if completed_results else 0.0

    return AuditResponse(
        url=str(body.url),
        timestamp=datetime.now(timezone.utc).isoformat(),
        results=results,
        overall_score=overall_score,
    )

@router.post("/audit/performance", response_model=AuditResult, tags=["Audit"])
async def run_audit_performance(body: AuditRequest) -> AuditResult:
    """
    Standalone testing endpoint for the Performance audit engine.
    """
    return run_lighthouse_audit(str(body.url))

@router.post("/audit/seo", response_model=AuditResult, tags=["Audit"])
async def run_audit_seo(body: AuditRequest) -> AuditResult:
    """
    Standalone testing endpoint for the SEO audit engine.
    """
    return run_seo_audit(str(body.url))

@router.post("/audit/accessibility", response_model=AuditResult, tags=["Audit"])
async def run_audit_accessibility(body: AuditRequest) -> AuditResult:
    """
    Standalone testing endpoint for the Accessibility audit engine.
    """
    return await run_accessibility_audit(str(body.url))

@router.post("/audit/security", response_model=AuditResult, tags=["Audit"])
async def run_audit_security(body: AuditRequest) -> AuditResult:
    """
    Standalone testing endpoint for the Security audit engine.
    """
    return run_security_audit(str(body.url))

