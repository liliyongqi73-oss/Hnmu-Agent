"""工作台接口。"""
from __future__ import annotations

from fastapi import APIRouter

from ...schemas.models import WorkspaceOverview
from ...services.workspace_service import get_workspace_overview

router = APIRouter()


@router.get("/overview", response_model=WorkspaceOverview)
def overview() -> WorkspaceOverview:
    """返回工作台初始化数据。

    Returns:
        工作台概览。
    """
    return get_workspace_overview()
