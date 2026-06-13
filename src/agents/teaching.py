"""教学智能体：生成面向医学教育的课程设计、案例教学与评价方案。

提示词外置在 workspace/skills/teaching/SKILL.md 与
workspace/skills/teaching-literature/SKILL.md。
"""
from __future__ import annotations

from ..llm_router import get_llm, invoke_text
from ..skills.loader import load_skill


def design_teaching(topic: str) -> str:
    """生成完整教学设计。

    Args:
        topic: 课程主题、教学难点或备课需求。

    Returns:
        可直接实施的结构化教学方案。
    """
    skill = load_skill("teaching")
    llm = get_llm(task=skill.task)
    user = skill.render_user({"topic": topic})
    return invoke_text(llm, [("system", skill.system_prompt), ("user", user)])


def analyze_literature(topic: str, context: str) -> str:
    """把科研文献转化为教学精读材料。

    Args:
        topic: 文献精读主题。
        context: 检索得到的文献上下文。

    Returns:
        面向课堂的文献精读与讨论材料。
    """
    skill = load_skill("teaching-literature")
    llm = get_llm(task=skill.task)
    user = skill.render_user({"topic": topic, "context": context})
    return invoke_text(llm, [("system", skill.system_prompt), ("user", user)])
