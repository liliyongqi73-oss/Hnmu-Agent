"""方法/创新点智能体：基于研究空白提出方法思路与创新点。"""
from __future__ import annotations

from ..llm_router import get_llm, invoke_text

_SYS = """你是医学科研选题与方法设计专家。基于综述中指出的研究空白，提出：
1. 2-3 个可行的研究方向及其创新点；
2. 每个方向的核心方法思路；
3. 可行性与潜在风险评估。
用中文，条理清晰。"""


def propose_method(topic: str, review: str) -> str:
    llm = get_llm(task="method")
    msg = f"研究主题：{topic}\n\n相关工作综述：\n{review}\n\n请提出方法与创新点。"
    return invoke_text(llm, [("system", _SYS), ("user", msg)])
