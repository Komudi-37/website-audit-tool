"""Audit route — Phase 1 stub (schema-compatible response)."""
from datetime import datetime, timezone
from fastapi import APIRouter
from app.schemas.audit import AuditRequest, AuditResponse, AuditResult

router = APIRouter()

_ALL_CATEGORIES = ["performance", "seo", "accessibility", "security", "functionality"]


@router.post("/audit", response_model=AuditResponse, tags=["Audit"])
async def run_audit(body: AuditRequest) -> AuditResponse:
    """
    Phase 1 stub — returns a schema-valid AuditResponse.
    Real audit engines will be wired in Phase 2+.
    """
    categories = body.categories if body.categories else _ALL_CATEGORIES

    results = [
        AuditResult(
            audit_type=cat,
            score=0.0,
            metrics={},
            findings=[],
            recommendations=[f"{cat.capitalize()} audit engine not yet implemented."],
        )
        for cat in categories
    ]

    return AuditResponse(
        url=str(body.url),
        timestamp=datetime.now(timezone.utc).isoformat(),
        results=results,
        overall_score=0.0,
    )
