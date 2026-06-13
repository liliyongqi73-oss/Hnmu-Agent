"""领导智能体：审核各执行智能体产出，并在未达标时给出修订稿。

提示词与用户模板外置在 workspace/skills/leader/SKILL.md，
本模块保留结构化解析逻辑。
"""
from __future__ import annotations

import re

from ..llm_router import get_llm, invoke_text
from ..skills.loader import load_skill


def review_task(task_name: str, topic: str, output: str, criteria: str = "") -> dict:
    """审核单个 Agent 任务并返回最终交付。

    Args:
        task_name: 被审核任务名称。
        topic: 当前科研或教学主题。
        output: 执行 Agent 的原始产出。
        criteria: 当前任务的补充验收标准。

    Returns:
        包含审核报告、最终交付、是否达标与评分的字典。

    Notes:
        当模型未严格遵循格式时，保守地保留完整审核文本作为最终交付。
    """
    skill = load_skill("leader")
    llm = get_llm(task=skill.task, temperature=0.1)
    message = skill.render_user(
        {
            "task_name": task_name,
            "topic": topic,
            "criteria": criteria or "无",
            "output": output,
        }
    )
    report = invoke_text(llm, [("system", skill.system_prompt), ("user", message)])
    return _parse_report(report, output)


def _parse_report(report: str, original_output: str) -> dict:
    """解析领导 Agent 的结构化审核文本。

    Args:
        report: 领导 Agent 返回的审核全文。
        original_output: 无法解析最终交付时使用的原始产出。

    Returns:
        标准化审核结果字典。
    """
    final_marker = "【最终交付】"
    score_marker = "【质量评分】"
    final_output = report.split(final_marker, 1)[1].strip() if final_marker in report else original_output
    passed = "【审核结论】达标" in report
    score = 0
    if score_marker in report:
        score_text = report.split(score_marker, 1)[1].splitlines()[0].strip()
        score_match = re.search(r"\d{1,3}", score_text)
        score = min(int(score_match.group()), 100) if score_match else 0
    return {
        "passed": passed,
        "score": score,
        "report": report,
        "final_output": final_output,
    }
