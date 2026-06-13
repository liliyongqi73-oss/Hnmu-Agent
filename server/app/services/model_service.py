"""模型策略查询服务。"""
from __future__ import annotations

from src.config import settings

from ..schemas.models import ModelOption


def list_model_options() -> list[ModelOption]:
    """返回前端可选模型策略。

    Returns:
        模型策略列表。
    """
    return [
        ModelOption(
            id="auto",
            name="自动路由",
            description="公开任务优先云端，敏感任务保留本地；云端未配置时全部本地",
            provider="Hybrid",
        ),
        ModelOption(
            id="local",
            name=f"本地 Qwen · {settings.local_model}",
            description="全部任务使用本地 Ollama，数据不离开当前设备",
            provider="Ollama",
        ),
        ModelOption(
            id="deepseek",
            name=f"云端 DeepSeek · {settings.deepseek_model}",
            description="公开任务使用 DeepSeek，领导审核与实验设计仍使用本地模型",
            provider="DeepSeek",
            available=bool(settings.deepseek_api_key and settings.deepseek_api_key != "sk-xxxx"),
        ),
    ]
