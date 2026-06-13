"""方法/创新点智能体：基于研究空白提出方法思路与创新点。

提示词外置在 workspace/skills/method/SKILL.md。
"""
from __future__ import annotations

from ..llm_router import get_llm, invoke_text
from ..skills.loader import load_skill


def propose_method(topic: str, review: str) -> str:
    skill = load_skill("method")
    llm = get_llm(task=skill.task)
    user = skill.render_user({"topic": topic, "review": review})
    return invoke_text(llm, [("system", skill.system_prompt), ("user", user)])
