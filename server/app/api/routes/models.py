"""模型策略接口。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...schemas.models import ModelConfigRequest, ModelOption
from ...services.model_service import create_model, delete_model, list_model_options, update_model
from ..dependencies import require_admin

router = APIRouter()


@router.get("", response_model=list[ModelOption])
def models() -> list[ModelOption]:
    """返回可选择的模型策略。

    Returns:
        模型策略列表。
    """
    return list_model_options()


@router.post("", response_model=ModelOption, dependencies=[Depends(require_admin)])
def create(request: ModelConfigRequest) -> ModelOption:
    """创建自定义模型配置。

    Args:
        request: 模型配置请求。

    Returns:
        新模型配置。
    """
    return create_model(request)


@router.put("/{model_id}", response_model=ModelOption, dependencies=[Depends(require_admin)])
def update(model_id: str, request: ModelConfigRequest) -> ModelOption:
    """更新自定义模型配置。

    Args:
        model_id: 模型配置编号。
        request: 最新模型配置。

    Returns:
        更新后的模型配置。
    """
    model = update_model(model_id, request)
    if not model:
        raise HTTPException(status_code=404, detail="自定义模型配置不存在")
    return model


@router.delete("/{model_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete(model_id: str) -> None:
    """删除自定义模型配置。

    Args:
        model_id: 模型配置编号。

    Returns:
        None。
    """
    if not delete_model(model_id):
        raise HTTPException(status_code=404, detail="自定义模型配置不存在")
