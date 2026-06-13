"""同行评审团：多视角审稿人 + 主编汇总的角色定义与结构化解析。

审稿人与主编的实际生成由编排引擎复用流式生成路径完成，
本模块只提供评审团角色清单与主编裁决报告的解析逻辑，与 leader.py 同风格。
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewerRole:
    """一个审稿视角。

    Attributes:
        key: 视角标识。
        name: 展示名称，写入流式事件。
        role: 传给 reviewer 技能的视角说明。
    """

    key: str
    name: str
    role: str


# 第一轮完整评审团：三位定向审稿人 + 魔鬼代言人。
FULL_PANEL: list[ReviewerRole] = [
    ReviewerRole("methodology", "方法学审稿人", "方法学审稿人"),
    ReviewerRole("novelty", "创新性审稿人", "创新性审稿人"),
    ReviewerRole("clarity", "表达审稿人", "表达审稿人"),
    ReviewerRole("devil", "魔鬼代言人", "魔鬼代言人"),
]

# 精简再审评审团：方法学审稿人 + 魔鬼代言人，用于修订后验收。
SLIM_PANEL: list[ReviewerRole] = [
    ReviewerRole("methodology", "方法学审稿人", "方法学审稿人"),
    ReviewerRole("devil", "魔鬼代言人", "魔鬼代言人"),
]


def get_panel(slim: bool = False) -> list[ReviewerRole]:
    """返回评审团角色清单。

    Args:
        slim: 为真时返回精简再审团，否则返回完整评审团。

    Returns:
        审稿视角列表。
    """
    return SLIM_PANEL if slim else FULL_PANEL


def parse_editor_report(report: str, original_output: str) -> dict:
    """解析主编裁决报告。

    Args:
        report: 主编 Agent 返回的裁决全文。
        original_output: 无法解析最终交付时使用的原始产出。

    Returns:
        标准化裁决结果字典，含 passed/score/decision/report/final_output。
    """
    final_marker = "【最终交付】"
    score_marker = "【质量评分】"
    decision_marker = "【录用决策】"
    final_output = report.split(final_marker, 1)[1].strip() if final_marker in report else original_output
    passed = "【审核结论】达标" in report
    score = 0
    if score_marker in report:
        score_text = report.split(score_marker, 1)[1].splitlines()[0].strip()
        score_match = re.search(r"\d{1,3}", score_text)
        score = min(int(score_match.group()), 100) if score_match else 0
    decision = ""
    if decision_marker in report:
        decision = report.split(decision_marker, 1)[1].splitlines()[0].strip()
    return {
        "passed": passed,
        "score": score,
        "decision": decision,
        "report": report,
        "final_output": final_output,
    }
