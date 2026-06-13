"""写作智能体：整合各环节产出，生成指定论文章节。"""
from __future__ import annotations

from ..llm_router import get_llm, invoke_text

_SYS = """你是医学论文写作专家。基于提供的素材，撰写指定章节，
符合学术规范、逻辑连贯、用中文。仅输出该章节正文。"""


def write_section(section: str, materials: dict) -> str:
    """生成某一章节。

    Args:
        section: 章节名（摘要/引言/相关工作/方法/实验/结论）。
        materials: 各环节产出，键如 topic/review/method/experiment。
    """
    llm = get_llm(task="writing")
    ctx = "\n\n".join(f"### {k}\n{v}" for k, v in materials.items() if v)
    msg = f"请撰写论文【{section}】章节。\n\n可用素材：\n{ctx}"
    return invoke_text(llm, [("system", _SYS), ("user", msg)])
