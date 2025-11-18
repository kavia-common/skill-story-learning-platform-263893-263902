from fastapi import APIRouter

router = APIRouter(tags=["health"])


# PUBLIC_INTERFACE
@router.get("/health", summary="Health check", description="Returns OK for service availability")
async def health_check():
    """Basic health check endpoint."""
    return {"success": True, "data": {"status": "ok"}}
