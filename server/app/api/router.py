"""API v1 聚合路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from .dependencies import get_current_user
from .routes import auth, models, system, tasks, users, workspace

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(system.router, tags=["system"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(
    models.router,
    prefix="/models",
    tags=["models"],
    dependencies=[Depends(get_current_user)],
)
api_router.include_router(
    workspace.router,
    prefix="/workspace",
    tags=["workspace"],
    dependencies=[Depends(get_current_user)],
)
api_router.include_router(
    tasks.router,
    prefix="/tasks",
    tags=["tasks"],
    dependencies=[Depends(get_current_user)],
)
api_router.include_router(users.router, prefix="/users", tags=["users"])
