from fastapi import APIRouter
from app.api.v1.assessment import router as assessment_router
from app.api.v1.auth import router as auth_router
from app.api.v1.careers import router as careers_router
from app.api.v1.compare import router as compare_router
from app.api.v1.health import router as health_router
from app.api.v1.profile import router as profile_router
from app.api.v1.shortlist import router as shortlist_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(assessment_router)
api_v1_router.include_router(careers_router)
api_v1_router.include_router(profile_router)
api_v1_router.include_router(shortlist_router)
api_v1_router.include_router(compare_router)

