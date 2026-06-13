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
    model_name: str = ""
    base_url: str = ""
    available: bool = True
    sensitive_local: bool = True
    is_local: bool = False
    builtin: bool = False
    has_api_key: bool = False


class ModelConfigRequest(BaseModel):
    """创建或编辑自定义模型配置的请求。"""

    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=240)
    provider: str = Field(min_length=2, max_length=40)
    model_name: str = Field(min_length=1, max_length=120)
    base_url: str = Field(min_length=8, max_length=500)
    api_key: str = Field(default="", max_length=500)
    is_local: bool = False


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
    mode: Literal["research", "teaching", "literature", "paper", "custom"] = "research"
    model_strategy: str = "auto"
    journals: list[str] = Field(default_factory=list)
    arxiv_categories: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=lambda: ["dblp", "pubmed", "arxiv", "local"])
    conferences: list[str] = Field(default_factory=list)
    year_from: int | None = Field(default=None, ge=1900, le=2100)
    year_to: int | None = Field(default=None, ge=1900, le=2100)
    # 自选 agent 子集（按顺序执行）；为空时按 mode 走预置计划。
    agents: list[str] = Field(default_factory=list)
    # 上传文件解析出的参考上下文，注入每个 agent。
    reference: str = Field(default="", max_length=200000)


class TaskActionRequest(BaseModel):
    """流程确认点操作请求。"""

    action: Literal["continue", "pause", "resume", "retry", "abort"]
    note: str = Field(default="", max_length=2000)


class UploadResult(BaseModel):
    """参考文件上传解析结果。"""

    filename: str
    chars: int
    preview: str
    text: str


class RetrievalSources(BaseModel):
    """检索来源预置清单。"""

    journals: list[dict[str, str]]
    arxiv_categories: list[dict[str, str]]
    databases: list[dict[str, str]]
    conferences: list[dict[str, str]]


class TaskEvent(BaseModel):
    """后台任务的阶段事件。"""

    stage: str
    agent: str
    status: Literal["pending", "running", "completed", "failed"]
    summary: str = ""
    output: str = ""


class TaskRecord(BaseModel):
    """后台任务的完整状态。"""

    id: str
    topic: str
    mode: str
    model_strategy: str
    journals: list[str] = Field(default_factory=list)
    arxiv_categories: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=lambda: ["dblp", "pubmed", "arxiv", "local"])
    conferences: list[str] = Field(default_factory=list)
    year_from: int | None = None
    year_to: int | None = None
    agents: list[str] = Field(default_factory=list)
    has_reference: bool = False
    reference: str = ""
    status: Literal[
        "queued",
        "running",
        "awaiting_confirmation",
        "paused",
        "completed",
        "failed",
        "aborted",
    ]
    events: list[TaskEvent] = Field(default_factory=list)
    pipeline_steps: list[dict] = Field(default_factory=list)
    step_results: dict[str, dict] = Field(default_factory=dict)
    current_step: int = 0
    checkpoint: dict = Field(default_factory=dict)
    decisions: list[dict] = Field(default_factory=list)
    material_passport: dict = Field(default_factory=dict)
    result: dict = Field(default_factory=dict)
    error: str = ""
    created_at: str
    updated_at: str
