from fastapi import APIRouter

from domain.deud.router import router as deud_router

router = APIRouter()
router.include_router(deud_router, prefix="/deud", tags=["대응답"])

__all__ = ["router"]
