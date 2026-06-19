"""Audit route — Phase 1 stub (schema-compatible response)."""
from datetime import datetime, timezone
from fastapi import APIRouter
from app.schemas.audit import AuditRequest, AuditResponse, AuditResult
from app.audits.performance import run_lighthouse_audit

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

    return AuditResponse(
        url=str(body.url),
        timestamp=datetime.now(timezone.utc).isoformat(),
        results=results,
        overall_score=0.0,
    )

@router.post("/audit/performance", response_model=AuditResult, tags=["Audit"])
async def run_audit_performance(body: AuditRequest) -> AuditResult:
    """
    Standalone testing endpoint for the Performance audit engine.
    """
    return run_lighthouse_audit(str(body.url))
