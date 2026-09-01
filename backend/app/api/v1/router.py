from fastapi import APIRouter

from app.api.v1.routers import admin, auth, cases, evidence

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(cases.router)
api_router.include_router(admin.router)
api_router.include_router(evidence.router)