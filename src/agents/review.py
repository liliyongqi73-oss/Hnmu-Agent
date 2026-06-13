"""综述智能体：基于检索上下文，归纳生成「相关工作」综述。

提示词外置在 workspace/skills/review/SKILL.md，本模块为薄封装，
供 smoke_test 与命令行直接调用；编排流程则由引擎按技能驱动。
"""
from __future__ import annotations

from ..llm_router import get_llm, invoke_text
from ..skills.loader import load_skill


def write_review(topic: str, context: str) -> str:
    skill = load_skill("review")
    llm = get_llm(task=skill.task)
    user = skill.render_user({"topic": topic, "context": context})
    return invoke_text(llm, [("system", skill.system_prompt), ("user", user)])
