"""模型策略接口。"""
from __future__ import annotations

from fastapi import APIRouter

from ...schemas.models import ModelOption
from ...services.model_service import list_model_options

router = APIRouter()


@router.get("", response_model=list[ModelOption])
def models() -> list[ModelOption]:
    """返回可选择的模型策略。

    Returns:
        模型策略列表。
    """
    return list_model_options()
