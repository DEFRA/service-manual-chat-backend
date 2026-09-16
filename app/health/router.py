from fastapi import APIRouter

router = APIRouter()


# Do not remove - used for health checks
@router.get("/health")
async def health():
    return {"status": "ok"}
