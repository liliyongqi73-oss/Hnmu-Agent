"""LLM 路由：根据任务类型在本地模型与云端 API 间切换。

混合部署的关键组件——敏感任务（SENSITIVE_TASKS）走本地 Ollama，
其余走云端 DeepSeek，数据合规与效果兼顾。
"""
from __future__ import annotations

from contextvars import ContextVar
from time import sleep

from langchain_openai import ChatOpenAI

from .config import SENSITIVE_TASKS, settings

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


def set_model_strategy(strategy: str) -> str:
    """设置当前会话任务使用的模型策略。

    Args:
        strategy: 模型策略显示名称。

    Returns:
        校验后的模型策略。

    Notes:
        使用 ContextVar 隔离并发会话，不修改全局配置或环境变量。
    """
    selected = strategy if strategy in MODEL_STRATEGIES else MODEL_STRATEGY_AUTO
    _MODEL_STRATEGY.set(selected)
    return selected


def get_model_strategy() -> str:
    """获取当前会话任务使用的模型策略。

    Returns:
        当前模型策略显示名称。
    """
    return _MODEL_STRATEGY.get()


def get_llm(task: str = "default", temperature: float = 0.3) -> ChatOpenAI:
    """按任务类型返回对应 LLM 客户端。

    Args:
        task: 任务标识，命中 SENSITIVE_TASKS 则走本地模型。
        temperature: 采样温度。
    """
    strategy = get_model_strategy()
    use_local = (
        strategy == MODEL_STRATEGY_LOCAL
        or task in SENSITIVE_TASKS
        or (strategy == MODEL_STRATEGY_AUTO and settings.all_local)
    )
    if use_local:
        # 本地 qwen3 系列默认开启 thinking，长上下文下会耗尽 token 预算导致正文为空。
        # 关闭 thinking 并放宽 max_tokens，保证生成正文完整。
        return ChatOpenAI(
            model=settings.local_model,
            base_url=settings.local_base_url,
            api_key="ollama",  # Ollama 不校验 key，占位即可
            temperature=temperature,
            max_tokens=4096,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
    if not settings.deepseek_api_key:
        raise RuntimeError("云端 DeepSeek 未配置 API Key，请切换到本地 Qwen 或补充配置。")

    # 自动路由与云端策略的公开任务使用 DeepSeek；敏感任务始终保留在本地。
    return ChatOpenAI(
        model=settings.deepseek_model,
        base_url=settings.deepseek_base_url,
        api_key=settings.deepseek_api_key,
        temperature=temperature,
    )


def invoke_text(llm: ChatOpenAI, messages: list[tuple[str, str]], retries: int = 3) -> str:
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
        response = llm.invoke(current_messages)
        content = response.content.strip() if isinstance(response.content, str) else ""
        if content:
            return content
        if attempt < retries:
            # 本地模型在冷启动或显存切换时可能短暂返回空文本，退避后再请求。
            sleep(1.5 * (attempt + 1))
            current_messages.append(("user", "上一次响应为空，请严格按照任务要求输出完整正文。"))
    raise RuntimeError("模型连续返回空文本，请检查本地模型状态后重试。")
