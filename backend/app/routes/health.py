"""Health check route."""
from fastapi import APIRouter
from app.schemas.audit import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Returns application health status."""
    return HealthResponse(status="ok")
