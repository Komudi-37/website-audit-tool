"""
Audit routes — updated to include the Functionality audit engine.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, Depends
from urllib.parse import urlparse
import ipaddress
import time
import logging
from sqlmodel import Session, select
from app.core.limiter import limiter
from app.core.database import get_session, AuditRecord, engine
from app.schemas.audit import AuditRequest, AuditResponse, AuditResult

from app.audits.performance import run_lighthouse_audit
from app.audits.seo import run_seo_audit
from app.audits.accessibility import run_accessibility_audit
from app.audits.security import run_security_audit
from app.audits.functionality import run_functionality_audit

router = APIRouter()
logger = logging.getLogger("audit_tool")

_ALL_CATEGORIES = ["performance", "seo", "accessibility", "security", "functionality"]

# ── In-memory cache ────────────────────────────────────────────────────────────
_cache: dict = {}
_CACHE_TTL = 600  # 10 minutes
_CACHE_MAX_SIZE = 100


def _get_cache_key(url: str, categories: list[str]) -> str:
    return f"{url}::{','.join(sorted(categories))}"


def _get_cached(key: str) -> AuditResponse | None:
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL:
        return entry["data"]
    if entry:
        del _cache[key]
    return None


def _set_cache(key: str, data: AuditResponse) -> None:
    if len(_cache) >= _CACHE_MAX_SIZE:
        oldest_key = min(_cache, key=lambda k: _cache[k]["ts"])
        del _cache[oldest_key]
    _cache[key] = {"ts": time.time(), "data": data}


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Auditing private/internal URLs is not allowed.")
    hostname = parsed.hostname or ""
    if hostname.lower() in ("localhost", "127.0.0.1", "0.0.0.0", ""):
        raise HTTPException(status_code=400, detail="Auditing private/internal URLs is not allowed.")
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private:
            raise HTTPException(status_code=400, detail="Auditing private/internal URLs is not allowed.")
    except ValueError:
        pass


@router.post("/audit", response_model=AuditResponse, tags=["Audit"])
@limiter.limit("5/minute")
async def run_audit(request: Request, body: AuditRequest) -> AuditResponse:
    _validate_url(str(body.url))
    categories = body.categories if body.categories else _ALL_CATEGORIES

    # ── Cache check ────────────────────────────────────────────────────────────
    cache_key = _get_cache_key(str(body.url), categories)
    cached = _get_cached(cache_key)
    if cached:
        return cached

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
        elif cat == "functionality":
            results.append(await run_functionality_audit(str(body.url)))
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
    overall_score = (
        sum(res.score for res in completed_results) / len(completed_results)
        if completed_results else 0.0
    )

    response = AuditResponse(
        url=str(body.url),
        timestamp=datetime.now(timezone.utc).isoformat(),
        results=results,
        overall_score=overall_score,
    )

    _set_cache(cache_key, response)

    # Save to database (non-cached runs only)
    try:
        with Session(engine) as db_session:
            record = AuditRecord(
                url=str(body.url),
                timestamp=response.timestamp,
                overall_score=overall_score,
                categories=",".join(categories),
                results_json=response.model_dump_json(),
            )
            db_session.add(record)
            db_session.commit()
    except Exception as e:
        logger.warning(f"Failed to save audit to database: {e}")

    return response


@router.post("/audit/performance", response_model=AuditResult, tags=["Audit"])
@limiter.limit("10/minute")
async def run_audit_performance(request: Request, body: AuditRequest) -> AuditResult:
    _validate_url(str(body.url))
    return run_lighthouse_audit(str(body.url))


@router.post("/audit/seo", response_model=AuditResult, tags=["Audit"])
@limiter.limit("10/minute")
async def run_audit_seo(request: Request, body: AuditRequest) -> AuditResult:
    _validate_url(str(body.url))
    return await run_seo_audit(str(body.url))


@router.post("/audit/accessibility", response_model=AuditResult, tags=["Audit"])
@limiter.limit("10/minute")
async def run_audit_accessibility(request: Request, body: AuditRequest) -> AuditResult:
    _validate_url(str(body.url))
    return await run_accessibility_audit(str(body.url))


@router.post("/audit/security", response_model=AuditResult, tags=["Audit"])
@limiter.limit("10/minute")
async def run_audit_security(request: Request, body: AuditRequest) -> AuditResult:
    _validate_url(str(body.url))
    return run_security_audit(str(body.url))


@router.post("/audit/functionality", response_model=AuditResult, tags=["Audit"])
@limiter.limit("10/minute")
async def run_audit_functionality(request: Request, body: AuditRequest) -> AuditResult:
    _validate_url(str(body.url))
    return await run_functionality_audit(str(body.url))


@router.get("/audit/history", tags=["Audit"])
@limiter.limit("30/minute")
async def get_audit_history(request: Request, limit: int = 20, session: Session = Depends(get_session)):
    """
    Returns the most recent audit records (newest first), summary only
    (no full results_json) — for displaying a history list in the UI.
    Fields returned per record: id, url, timestamp, overall_score, categories.
    """
    capped_limit = min(limit, 50)
    statement = select(AuditRecord).order_by(AuditRecord.id.desc()).limit(capped_limit)
    records = session.exec(statement).all()
    return [
        {
            "id": r.id,
            "url": r.url,
            "timestamp": r.timestamp,
            "overall_score": r.overall_score,
            "categories": r.categories,
        }
        for r in records
    ]


@router.get("/audit/history/{record_id}", response_model=AuditResponse, tags=["Audit"])
@limiter.limit("30/minute")
async def get_audit_history_detail(request: Request, record_id: int, session: Session = Depends(get_session)):
    """
    Returns the full AuditResponse for a specific historical audit record,
    parsed back from results_json. 404 if not found.
    """
    statement = select(AuditRecord).where(AuditRecord.id == record_id)
    record = session.exec(statement).first()
    if not record:
        raise HTTPException(status_code=404, detail="Audit record not found")
    return AuditResponse.model_validate_json(record.results_json)