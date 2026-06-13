"""模型配置查询、持久化与运行时解析服务。"""
from __future__ import annotations

import json
from threading import Lock
from uuid import uuid4

from src.config import settings

from ..core.config import MODEL_CONFIG_PATH
from ..schemas.models import ModelConfigRequest, ModelOption

_LOCK = Lock()


def _builtin_models() -> list[dict]:
    """生成不可删除的内置模型策略。

    Returns:
        内置模型配置列表。
    """
    return [
        {
            "id": "auto",
            "name": "自动路由",
            "description": "公开任务优先云端，敏感任务保留本地；云端未配置时全部本地",
            "provider": "Hybrid",
            "model_name": "",
            "base_url": "",
            "api_key": "",
            "available": True,
            "sensitive_local": True,
            "is_local": False,
            "builtin": True,
        },
        {
            "id": "local",
            "name": f"本地 Qwen · {settings.local_model}",
            "description": "全部任务使用本地 Ollama，数据不离开当前设备",
            "provider": "Ollama",
            "model_name": settings.local_model,
            "base_url": settings.local_base_url,
            "api_key": "ollama",
            "available": True,
            "sensitive_local": True,
            "is_local": True,
            "builtin": True,
        },
        {
            "id": "deepseek",
            "name": f"云端 DeepSeek · {settings.deepseek_model}",
            "description": "公开任务使用 DeepSeek，领导审核与实验设计仍使用本地模型",
            "provider": "DeepSeek",
            "model_name": settings.deepseek_model,
            "base_url": settings.deepseek_base_url,
            "api_key": settings.deepseek_api_key,
            "available": bool(settings.deepseek_api_key and settings.deepseek_api_key != "sk-xxxx"),
            "sensitive_local": True,
            "is_local": False,
            "builtin": True,
        },
    ]


def _load_custom_models() -> list[dict]:
    """读取本地自定义模型配置。

    Returns:
        自定义模型配置列表；文件异常时返回空列表。
    """
    if not MODEL_CONFIG_PATH.exists():
        return []
    try:
        content = json.loads(MODEL_CONFIG_PATH.read_text(encoding="utf-8"))
        return content if isinstance(content, list) else []
    except (OSError, ValueError):
        return []


def _persist_custom_models(models: list[dict]) -> None:
    """持久化自定义模型配置。

    Args:
        models: 自定义模型配置列表。

    Returns:
        None。
    """
    MODEL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODEL_CONFIG_PATH.write_text(
        json.dumps(models, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _to_option(model: dict) -> ModelOption:
    """将含密钥的运行时配置转换为前端安全模型信息。

    Args:
        model: 完整模型配置。

    Returns:
        不含 API Key 明文的模型选项。
    """
    api_key = model.get("api_key", "")
    return ModelOption(
        **{key: value for key, value in model.items() if key != "api_key"},
        has_api_key=bool(api_key),
    )


def list_model_options() -> list[ModelOption]:
    """返回内置与自定义模型配置。

    Returns:
        不包含 API Key 明文的模型列表。
    """
    with _LOCK:
        return [_to_option(model) for model in [*_builtin_models(), *_load_custom_models()]]


def create_model(request: ModelConfigRequest) -> ModelOption:
    """创建自定义模型配置。

    Args:
        request: 自定义模型请求。

    Returns:
        新模型安全信息。
    """
    model = {
        "id": f"custom-{uuid4().hex[:12]}",
        **request.model_dump(),
        "available": bool(request.is_local or request.api_key),
        "sensitive_local": True,
        "builtin": False,
    }
    with _LOCK:
        models = _load_custom_models()
        models.append(model)
        _persist_custom_models(models)
    return _to_option(model)


def update_model(model_id: str, request: ModelConfigRequest) -> ModelOption | None:
    """更新自定义模型配置。

    Args:
        model_id: 模型配置编号。
        request: 最新模型配置。

    Returns:
        更新后的模型安全信息，不存在时返回 None。
    """
    with _LOCK:
        models = _load_custom_models()
        for index, current in enumerate(models):
            if current.get("id") != model_id:
                continue
            api_key = request.api_key or current.get("api_key", "")
            model = {
                "id": model_id,
                **request.model_dump(exclude={"api_key"}),
                "api_key": api_key,
                "available": bool(request.is_local or api_key),
                "sensitive_local": True,
                "builtin": False,
            }
            models[index] = model
            _persist_custom_models(models)
            return _to_option(model)
    return None


def delete_model(model_id: str) -> bool:
    """删除自定义模型配置。

    Args:
        model_id: 模型配置编号。

    Returns:
        是否成功删除。
    """
    with _LOCK:
        models = _load_custom_models()
        retained = [model for model in models if model.get("id") != model_id]
        if len(retained) == len(models):
            return False
        _persist_custom_models(retained)
        return True


def get_model_runtime(model_id: str) -> dict | None:
    """读取任务执行需要的完整模型配置。

    Args:
        model_id: 模型配置编号。

    Returns:
        包含 API Key 的运行时配置，不存在时返回 None。
    """
    with _LOCK:
        return next(
            (model for model in [*_builtin_models(), *_load_custom_models()] if model["id"] == model_id),
            None,
        )
