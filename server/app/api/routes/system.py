"""系统健康检查接口。"""
from __future__ import annotations

from fastapi import APIRouter

from ...core.database import database_health

router = APIRouter()


@router.get("/health")
def health() -> dict:
    """返回服务健康状态。

    Returns:
        服务状态信息。
    """
    database_ok, database_message = database_health()
    return {
        "status": "ok" if database_ok else "degraded",
        "service": "HNMU-Agent API",
        "database": database_message,
    }
