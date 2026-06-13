"""工作台概览服务。"""
from __future__ import annotations

from ..schemas.models import AgentProfile, WorkspaceOverview


def get_workspace_overview() -> WorkspaceOverview:
    """生成工作台导航、Agent 团队与快捷任务数据。

    Returns:
        工作台概览。
    """
    return WorkspaceOverview(
        navigation=[
            {"id": "home", "label": "主页", "description": "科研与教学协作", "icon": "HomeFilled"},
            {"id": "new", "label": "新会话", "description": "开始新的上下文", "icon": "CirclePlus"},
            {"id": "history", "label": "历史", "description": "会话与任务记录", "icon": "Clock"},
            {"id": "agents", "label": "Agents", "description": "团队与任务分工", "icon": "Connection"},
            {"id": "runs", "label": "运行面板", "description": "进度、日志与结果", "icon": "DataLine"},
            {"id": "skills", "label": "技能库", "description": "科研教学能力", "icon": "MagicStick"},
            {"id": "memory", "label": "记忆", "description": "知识与上下文", "icon": "Collection"},
        ],
        agents=[
            AgentProfile(id="leader", name="领导 Agent", description="任务规划、质量审核与修订交付", accent="#6c5ce7"),
            AgentProfile(id="retrieval", name="检索 Agent", description="PubMed、arXiv 与院内知识库", accent="#3b82f6"),
            AgentProfile(id="review", name="综述 Agent", description="研究现状、证据归纳与研究空白", accent="#14b8a6"),
            AgentProfile(id="method", name="方法 Agent", description="研究方案、创新点与风险评估", accent="#f59e0b"),
            AgentProfile(id="experiment", name="实验 Agent", description="实验设计、统计与伦理合规", accent="#ef4444"),
            AgentProfile(id="teaching", name="教学 Agent", description="课程设计、文献精读与评价量规", accent="#8b5cf6"),
        ],
        quick_prompts=[
            {"mode": "research", "title": "启动科研课题协作", "prompt": "基于深度学习的肺结节良恶性分类"},
            {"mode": "teaching", "title": "设计医学课程", "prompt": "为本科生设计一堂循证医学入门课"},
            {"mode": "literature", "title": "开展文献精读", "prompt": "人工智能辅助医学影像诊断"},
        ],
    )
