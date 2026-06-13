"""API v1 聚合路由。"""
from __future__ import annotations

from fastapi import APIRouter

from .routes import models, system, tasks, workspace

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(system.router, tags=["system"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(workspace.router, prefix="/workspace", tags=["workspace"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
