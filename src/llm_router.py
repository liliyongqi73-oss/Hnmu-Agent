"""LLM 路由：根据任务类型在本地模型与云端 API 间切换。

混合部署的关键组件——敏感任务（SENSITIVE_TASKS）走本地 Ollama，
其余走云端 DeepSeek，数据合规与效果兼顾。
"""
from __future__ import annotations

import json
from contextvars import ContextVar
from dataclasses import dataclass
from time import sleep
from typing import Callable

import httpx
from langchain_openai import ChatOpenAI

from .config import SENSITIVE_TASKS, settings

# 流式生成时的增量文本回调。
TokenCallback = Callable[[str], None]

MODEL_STRATEGY_AUTO = "自动路由"
MODEL_STRATEGY_LOCAL = "本地 Qwen"
MODEL_STRATEGY_DEEPSEEK = "云端 DeepSeek"
MODEL_STRATEGIES = (
    MODEL_STRATEGY_AUTO,
    MODEL_STRATEGY_LOCAL,
    MODEL_STRATEGY_DEEPSEEK,
)

_MODEL_STRATEGY: ContextVar[str] = ContextVar(
    "model_strategy",
    default=MODEL_STRATEGY_AUTO,
)
_MODEL_CONFIG: ContextVar[dict | None] = ContextVar("model_config", default=None)
_MODEL_FALLBACK_NOTICE: ContextVar[str] = ContextVar("model_fallback_notice", default="")


@dataclass
class LocalOllamaClient:
    """Ollama 原生聊天接口配置。"""

    temperature: float


def set_model_strategy(strategy: str) -> str:
    """设置当前会话任务使用的模型策略。

    Args:
        strategy: 模型策略显示名称。

    Returns:
        校验后的模型策略。

    Notes:
        使用 ContextVar 隔离并发会话，不修改全局配置或环境变量。
    """
    selected = strategy or MODEL_STRATEGY_AUTO
    _MODEL_STRATEGY.set(selected)
    return selected


def set_model_config(config: dict | None) -> None:
    """设置当前任务使用的自定义模型配置。

    Args:
        config: 模型运行时配置，内置策略或不存在时传入 None。

    Returns:
        None。
    """
    _MODEL_CONFIG.set(config)


def get_model_strategy() -> str:
    """获取当前会话任务使用的模型策略。

    Returns:
        当前模型策略显示名称。
    """
    return _MODEL_STRATEGY.get()


def consume_model_fallback_notice() -> str:
    """读取并清空当前任务的模型回退说明。

    Returns:
        模型回退说明；未发生回退时返回空字符串。
    """
    notice = _MODEL_FALLBACK_NOTICE.get()
    _MODEL_FALLBACK_NOTICE.set("")
    return notice


def _get_local_llm(temperature: float) -> LocalOllamaClient:
    """创建本地 Ollama 模型客户端。

    Args:
        temperature: 采样温度。

    Returns:
        本地 Ollama 原生接口配置。
    """
    return LocalOllamaClient(temperature=temperature)


def _invoke_local_text(client: LocalOllamaClient, messages: list[tuple[str, str]]) -> str:
    """通过 Ollama 原生接口调用本地模型并关闭思考模式。

    Args:
        client: 本地模型调用配置。
        messages: 发送给模型的角色与文本消息列表。

    Returns:
        本地模型生成的正文。
    """
    base_url = settings.local_base_url.rstrip("/")
    native_base_url = base_url[:-3] if base_url.endswith("/v1") else base_url
    response = httpx.post(
        f"{native_base_url}/api/chat",
        json={
            "model": settings.local_model,
            "messages": [{"role": role, "content": content} for role, content in messages],
            "stream": False,
            "think": False,
            "options": {"temperature": client.temperature, "num_predict": 4096},
        },
        timeout=600,
    )
    response.raise_for_status()
    return str(response.json().get("message", {}).get("content", "")).strip()


def _stream_local_text(
    client: LocalOllamaClient,
    messages: list[tuple[str, str]],
    on_token: TokenCallback,
) -> str:
    """通过 Ollama 原生接口流式调用本地模型，逐 token 回调并累积正文。

    Args:
        client: 本地模型调用配置。
        messages: 发送给模型的角色与文本消息列表。
        on_token: 增量文本回调。

    Returns:
        累积的完整正文。
    """
    base_url = settings.local_base_url.rstrip("/")
    native_base_url = base_url[:-3] if base_url.endswith("/v1") else base_url
    parts: list[str] = []
    with httpx.stream(
        "POST",
        f"{native_base_url}/api/chat",
        json={
            "model": settings.local_model,
            "messages": [{"role": role, "content": content} for role, content in messages],
            "stream": True,
            "think": False,
            "options": {"temperature": client.temperature, "num_predict": 4096},
        },
        timeout=600,
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            # Ollama 流式返回 ndjson，每行一个 chunk，message.content 为增量文本。
            chunk = json.loads(line)
            piece = str(chunk.get("message", {}).get("content", ""))
            if piece:
                parts.append(piece)
                on_token(piece)
            if chunk.get("done"):
                break
    return "".join(parts).strip()


def _stream_cloud_text(
    llm: ChatOpenAI,
    messages: list[tuple[str, str]],
    on_token: TokenCallback,
) -> str:
    """流式调用云端 ChatOpenAI 模型，逐 token 回调并累积正文。

    Args:
        llm: 云端模型客户端。
        messages: 发送给模型的角色与文本消息列表。
        on_token: 增量文本回调。

    Returns:
        累积的完整正文。
    """
    parts: list[str] = []
    for chunk in llm.stream(messages):
        piece = chunk.content if isinstance(chunk.content, str) else ""
        if piece:
            parts.append(piece)
            on_token(piece)
    return "".join(parts).strip()


def stream_text(
    llm: ChatOpenAI | LocalOllamaClient,
    messages: list[tuple[str, str]],
    on_token: TokenCallback,
) -> str:
    """流式调用 LLM 并保证返回非空文本，失败时回退到非流式调用。

    Args:
        llm: 已完成任务路由的 LLM 客户端。
        messages: 发送给模型的角色与文本消息列表。
        on_token: 增量文本回调。

    Returns:
        模型生成的非空文本。

    Raises:
        RuntimeError: 流式与非流式均无法获得正文时由 invoke_text 抛出。

    Notes:
        流式异常或返回空正文时回退 invoke_text（保留重试、空响应与云端故障回退本地的全部保障），
        并把回退得到的完整结果作为单个 token 推送，前端展示保持一致。
    """
    try:
        content = (
            _stream_local_text(llm, messages, on_token)
            if isinstance(llm, LocalOllamaClient)
            else _stream_cloud_text(llm, messages, on_token)
        )
        if content:
            return content
    except Exception:  # noqa: BLE001  流式失败不应中断任务，回退非流式
        pass
    # 流式为空或异常：回退非流式（含完整重试与故障回退逻辑）。
    content = invoke_text(llm, messages)
    on_token(content)
    return content


def _activate_local_fallback(model_config: dict, error: Exception | str) -> LocalOllamaClient:
    """切换当前任务到本地模型并记录回退说明。

    Args:
        model_config: 故障自定义模型配置。
        error: 云端模型异常或空响应说明。

    Returns:
        本地模型客户端配置。
    """
    _MODEL_CONFIG.set(None)
    _MODEL_STRATEGY.set(MODEL_STRATEGY_LOCAL)
    _MODEL_FALLBACK_NOTICE.set(
        f"自定义模型 {model_config.get('name', model_config.get('model_name', ''))} 调用失败，"
        f"已自动切换本地 {settings.local_model}：{error}"
    )
    return _get_local_llm(0.3)


def get_llm(task: str = "default", temperature: float = 0.3) -> ChatOpenAI | LocalOllamaClient:
    """按任务类型返回对应 LLM 客户端。

    Args:
        task: 任务标识，命中 SENSITIVE_TASKS 则走本地模型。
        temperature: 采样温度。
    """
    strategy = get_model_strategy()
    model_config = _MODEL_CONFIG.get()
    if model_config and (model_config.get("is_local") or task not in SENSITIVE_TASKS):
        return ChatOpenAI(
            model=model_config["model_name"],
            base_url=model_config["base_url"],
            api_key=model_config.get("api_key") or "local",
            temperature=temperature,
            max_tokens=4096,
        )
    use_local = (
        strategy == MODEL_STRATEGY_LOCAL
        or task in SENSITIVE_TASKS
        or (strategy == MODEL_STRATEGY_AUTO and settings.all_local)
    )
    if use_local:
        # 本地 qwen3 系列默认开启 thinking，长上下文下会耗尽 token 预算导致正文为空。
        # 关闭 thinking 并放宽 max_tokens，保证生成正文完整。
        return _get_local_llm(temperature)
    if not settings.deepseek_api_key:
        raise RuntimeError("云端 DeepSeek 未配置 API Key，请切换到本地 Qwen 或补充配置。")

    # 自动路由与云端策略的公开任务使用 DeepSeek；敏感任务始终保留在本地。
    return ChatOpenAI(
        model=settings.deepseek_model,
        base_url=settings.deepseek_base_url,
        api_key=settings.deepseek_api_key,
        temperature=temperature,
    )


def invoke_text(
    llm: ChatOpenAI | LocalOllamaClient,
    messages: list[tuple[str, str]],
    retries: int = 3,
) -> str:
    """调用 LLM 并保证返回非空文本。

    Args:
        llm: 已完成任务路由的 LLM 客户端。
        messages: 发送给模型的角色与文本消息列表。
        retries: 遇到空响应时的最大重试次数。

    Returns:
        模型生成的非空文本。

    Raises:
        RuntimeError: 模型连续返回空文本时抛出，避免空结果污染后续 Agent。
    """
    current_messages = list(messages)
    for attempt in range(retries + 1):
        try:
            content = (
                _invoke_local_text(llm, current_messages)
                if isinstance(llm, LocalOllamaClient)
                else llm.invoke(current_messages).content
            )
        except Exception as error:
            model_config = _MODEL_CONFIG.get()
            if not model_config or model_config.get("is_local"):
                raise
            # 自定义云端模型故障时切换本地模型，保障多阶段任务可继续完成。
            llm = _activate_local_fallback(model_config, error)
            content = _invoke_local_text(llm, current_messages)
        content = content.strip() if isinstance(content, str) else ""
        if content:
            return content
        model_config = _MODEL_CONFIG.get()
        if attempt == retries and model_config and not model_config.get("is_local"):
            llm = _activate_local_fallback(model_config, "模型连续返回空正文")
            content = _invoke_local_text(llm, current_messages)
            if content:
                return content
        if attempt < retries:
            # 本地模型在冷启动或显存切换时可能短暂返回空文本，退避后再请求。
            sleep(1.5 * (attempt + 1))
            current_messages.append(("user", "上一次响应为空，请严格按照任务要求输出完整正文。"))
    raise RuntimeError("模型连续返回空文本，请检查本地模型状态后重试。")
