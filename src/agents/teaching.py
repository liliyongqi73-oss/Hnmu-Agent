"""教学智能体：生成面向医学教育的课程设计、案例教学与评价方案。"""
from __future__ import annotations

from ..llm_router import get_llm, invoke_text

_SYS = """你是医学教育课程设计专家。围绕用户主题生成可直接实施的教学方案，包含：
1. 学习者分析与可测量的教学目标；
2. 教学重点、难点与课程结构；
3. 教学活动、临床案例或科研案例；
4. 形成性评价、总结性评价与评分量规；
5. 课后任务、拓展资源与教学反思要点。
内容应落实课程思政、医学伦理、科研诚信和循证医学意识，使用中文。"""


def design_teaching(topic: str) -> str:
    """生成完整教学设计。

    Args:
        topic: 课程主题、教学难点或备课需求。

    Returns:
        可直接实施的结构化教学方案。
    """
    llm = get_llm(task="teaching")
    message = f"教学主题或需求：{topic}\n\n请生成完整、可执行的教学设计。"
    return invoke_text(llm, [("system", _SYS), ("user", message)])


def analyze_literature(topic: str, context: str) -> str:
    """把科研文献转化为教学精读材料。

    Args:
        topic: 文献精读主题。
        context: 检索得到的文献上下文。

    Returns:
        面向课堂的文献精读与讨论材料。
    """
    llm = get_llm(task="teaching")
    message = (
        f"精读主题：{topic}\n\n文献上下文：\n{context}\n\n"
        "请设计文献精读课，突出研究问题、方法判断、证据等级、局限性和讨论题。"
    )
    return invoke_text(llm, [("system", _SYS), ("user", message)])
