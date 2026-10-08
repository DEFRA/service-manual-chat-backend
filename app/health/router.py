from fastapi import APIRouter

router = APIRouter()


# Do not remove - used for health checks
@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
