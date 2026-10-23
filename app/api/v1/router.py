from fastapi import APIRouter
from app.api.v1.adaptive_tests import router as adaptive_tests_router
from app.api.v1.assessment import router as assessment_router
from app.api.v1.auth import router as auth_router
from app.api.v1.careers import router as careers_router
from app.api.v1.compare import router as compare_router
from app.api.v1.health import router as health_router
from app.api.v1.profile import router as profile_router
from app.api.v1.recommendations import router as recommendations_router
from app.api.v1.portfolio import router as portfolio_router
from app.api.v1.roadmaps import router as roadmaps_router
from app.api.v1.shortlist import router as shortlist_router
from app.api.v1.skills import router as skills_router
from app.api.v1.interviews import router as interviews_router
from app.api.v1.progress import router as progress_router
from app.api.v1.chat import router as chat_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(assessment_router)
api_v1_router.include_router(careers_router)
api_v1_router.include_router(profile_router)
api_v1_router.include_router(shortlist_router)
api_v1_router.include_router(compare_router)
api_v1_router.include_router(adaptive_tests_router)
api_v1_router.include_router(skills_router)
api_v1_router.include_router(recommendations_router)
api_v1_router.include_router(portfolio_router)
api_v1_router.include_router(roadmaps_router)
api_v1_router.include_router(interviews_router)
api_v1_router.include_router(progress_router)
api_v1_router.include_router(chat_router)


