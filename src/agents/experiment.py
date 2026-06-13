"""实验设计智能体：给出实验方案与统计分析建议（敏感任务，走本地模型）。"""
from __future__ import annotations

from ..llm_router import get_llm, invoke_text

_SYS = """你是医学实验设计与统计专家。基于研究方法，设计实验方案：
1. 研究类型(队列/RCT/回顾性等)与样本量估算思路；
2. 变量定义、对照设置、纳入排除标准；
3. 统计分析方法(检验/模型)与显著性标准；
4. 伦理与数据合规注意事项。
用中文，符合医学论文 Methods 规范。"""


def design_experiment(topic: str, method: str) -> str:
    # experiment 在 SENSITIVE_TASKS 中 -> 自动走本地模型
    llm = get_llm(task="experiment")
    msg = f"研究主题：{topic}\n\n方法思路：\n{method}\n\n请设计实验方案。"
    return invoke_text(llm, [("system", _SYS), ("user", msg)])
