"""实验设计智能体：给出实验方案与统计分析建议（敏感任务，走本地模型）。

提示词外置在 workspace/skills/experiment/SKILL.md。
"""
from __future__ import annotations

from ..llm_router import get_llm, invoke_text
from ..skills.loader import load_skill


def design_experiment(topic: str, method: str) -> str:
    # experiment 技能 task 命中 SENSITIVE_TASKS -> 自动走本地模型
    skill = load_skill("experiment")
    llm = get_llm(task=skill.task)
    user = skill.render_user({"topic": topic, "method": method})
    return invoke_text(llm, [("system", skill.system_prompt), ("user", user)])
