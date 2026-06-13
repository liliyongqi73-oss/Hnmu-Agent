"""综述智能体：基于检索上下文，归纳生成「相关工作」综述。"""
from __future__ import annotations

from ..llm_router import get_llm, invoke_text

_SYS = """你是医学科研综述专家。基于给定文献上下文，撰写一段结构化的相关工作综述：
1. 按主题聚类归纳现有研究；
2. 指出方法演进与代表性工作；
3. 明确点出研究空白(gap)。
用中文，学术风格，关键论断后标注来源标题。"""


def write_review(topic: str, context: str) -> str:
    llm = get_llm(task="review")
    msg = f"研究主题：{topic}\n\n文献上下文：\n{context}\n\n请撰写相关工作综述。"
    return invoke_text(llm, [("system", _SYS), ("user", msg)])
