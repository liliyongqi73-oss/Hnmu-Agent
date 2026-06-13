"""模型、工作台与任务接口的数据结构。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ModelOption(BaseModel):
    """前端可选择的模型策略。"""

    id: str
    name: str
    description: str
    provider: str
    available: bool = True
    sensitive_local: bool = True


class AgentProfile(BaseModel):
    """工作台展示的 Agent 信息。"""

    id: str
    name: str
    description: str
    status: Literal["online", "idle", "offline"] = "online"
    accent: str


class WorkspaceOverview(BaseModel):
    """工作台首页概览。"""

    agents: list[AgentProfile]
    navigation: list[dict[str, str]]
    quick_prompts: list[dict[str, str]]


class TaskCreateRequest(BaseModel):
    """创建科研或教学任务的请求。"""

    topic: str = Field(min_length=2, max_length=2000)
    mode: Literal["research", "teaching", "literature"] = "research"
    model_strategy: str = "auto"


class TaskEvent(BaseModel):
    """后台任务的阶段事件。"""

    stage: str
    agent: str
    status: Literal["pending", "running", "completed", "failed"]
    summary: str = ""


class TaskRecord(BaseModel):
    """后台任务的完整状态。"""

    id: str
    topic: str
    mode: str
    model_strategy: str
    status: Literal["queued", "running", "completed", "failed"]
    events: list[TaskEvent] = Field(default_factory=list)
    result: dict = Field(default_factory=dict)
    error: str = ""
    created_at: str
    updated_at: str
