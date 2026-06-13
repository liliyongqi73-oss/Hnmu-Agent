"""系统健康检查接口。"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict:
    """返回服务健康状态。

    Returns:
        服务状态信息。
    """
    return {"status": "ok", "service": "HNMU-Agent API"}
