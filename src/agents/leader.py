"""领导智能体：审核各执行智能体产出，并在未达标时给出修订稿。"""
from __future__ import annotations

import re

from ..llm_router import get_llm, invoke_text

_SYS = """你是科研与教学多智能体团队的领导 Agent，负责质量验收。
请检查执行 Agent 的产出是否准确、完整、可执行、符合学术与教学规范。

必须严格按以下格式输出：
【审核结论】达标 或 需修订
【质量评分】0-100 的整数
【审核意见】指出亮点、缺口、风险和改进要求
【最终交付】若达标，保留并适度润色原产出；若需修订，直接给出完整修订稿

不得捏造文献、数据、伦理审批或实验结果。对证据不足的内容明确标注待核验。"""


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
    llm = get_llm(task="leader", temperature=0.1)
    message = (
        f"任务名称：{task_name}\n"
        f"主题：{topic}\n"
        f"补充验收标准：{criteria or '无'}\n\n"
        f"执行 Agent 产出：\n{output}"
    )
    report = invoke_text(llm, [("system", _SYS), ("user", message)])
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
