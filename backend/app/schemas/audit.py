"""Pydantic schemas for request/response validation."""
from __future__ import annotations
from pydantic import BaseModel, HttpUrl
from typing import Any, Literal, Optional


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

AuditCategory = Literal[
    "performance", "seo", "accessibility", "security", "functionality", "form_validation"
]


class AuditRequest(BaseModel):
    url: HttpUrl
    categories: Optional[list[AuditCategory]] = None
    force_refresh: bool = False

    model_config = {
        "json_schema_extra": {
            "example": {
                "url": "https://example.com",
                "categories": ["performance", "seo"],
                "force_refresh": False,
            }
        }
    }


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str


class Finding(BaseModel):
    id: str
    title: str
    description: str
    severity: Literal["critical", "warning", "info", "pass"]
    category: AuditCategory


class AuditResult(BaseModel):
    audit_type: AuditCategory
    score: Optional[float] = None           # 0–100, or None if not applicable
    metrics: dict[str, Any] = {}
    findings: list[Finding] = []
    recommendations: list[str] = []


class AuditResponse(BaseModel):
    url: str
    timestamp: str
    results: list[AuditResult] = []
    overall_score: float                    # 0–100
    executive_summary: str = ""
    overall_assessment: str = ""
    business_impact: str = ""
    priority_fixes: list[str] = []