"""科研教学后台任务编排服务。"""
from __future__ import annotations

from threading import Thread

from src.agents import experiment, leader, method, retrieval, review, teaching
from src.llm_router import (
    MODEL_STRATEGY_AUTO,
    MODEL_STRATEGY_DEEPSEEK,
    MODEL_STRATEGY_LOCAL,
    set_model_strategy,
)

from ..runtime import task_store
from ..schemas.models import TaskCreateRequest, TaskEvent

STRATEGY_MAP = {
    "auto": MODEL_STRATEGY_AUTO,
    "local": MODEL_STRATEGY_LOCAL,
    "deepseek": MODEL_STRATEGY_DEEPSEEK,
}


def submit_task(request: TaskCreateRequest):
    """创建任务并启动后台执行线程。

    Args:
        request: 任务创建请求。

    Returns:
        已创建的任务记录。
    """
    record = task_store.create_task(request)
    # 后台线程运行耗时 Agent 流程，避免阻塞 FastAPI 请求。
    Thread(target=_run_task, args=(record.id,), daemon=True).start()
    return record


def _event(task_id: str, stage: str, agent: str, status: str, summary: str = "") -> None:
    """记录任务阶段事件。

    Args:
        task_id: 任务编号。
        stage: 阶段名称。
        agent: 执行 Agent。
        status: 阶段状态。
        summary: 阶段摘要。

    Returns:
        None。
    """
    task_store.append_event(
        task_id,
        TaskEvent(stage=stage, agent=agent, status=status, summary=summary),
    )


def _run_task(task_id: str) -> None:
    """执行科研或教学任务。

    Args:
        task_id: 任务编号。

    Returns:
        None。
    """
    record = task_store.get_task(task_id)
    if not record:
        return
    try:
        set_model_strategy(STRATEGY_MAP.get(record.model_strategy, MODEL_STRATEGY_AUTO))
        task_store.update_task(task_id, status="running")
        if record.mode == "teaching":
            result = _run_teaching(task_id, record.topic)
        elif record.mode == "literature":
            result = _run_literature(task_id, record.topic)
        else:
            result = _run_research(task_id, record.topic)
        task_store.update_task(task_id, status="completed", result=result)
    except Exception as error:  # noqa: BLE001  任务异常必须写入状态供前端展示
        _event(task_id, "任务终止", "系统", "failed", str(error))
        task_store.update_task(task_id, status="failed", error=str(error))


def _run_research(task_id: str, topic: str) -> dict:
    """执行科研多智能体流程。

    Args:
        task_id: 任务编号。
        topic: 科研主题。

    Returns:
        各阶段最终交付。
    """
    _event(task_id, "文献检索", "检索 Agent", "running")
    retrieved = retrieval.retrieve(topic)
    context = retrieval.format_context(retrieved)
    _event(task_id, "文献检索", "检索 Agent", "completed", "多源证据检索完成")

    _event(task_id, "相关工作综述", "综述 Agent", "running")
    raw_review = review.write_review(topic, context)
    reviewed = leader.review_task("相关工作综述", topic, raw_review, "论断可追溯，明确研究空白")
    _event(task_id, "相关工作综述", "领导 Agent", "completed", f"质量评分 {reviewed['score']}/100")

    _event(task_id, "方法与创新点", "方法 Agent", "running")
    raw_method = method.propose_method(topic, reviewed["final_output"])
    method_audit = leader.review_task("方法与创新点", topic, raw_method, "回应研究空白且可行")
    _event(task_id, "方法与创新点", "领导 Agent", "completed", f"质量评分 {method_audit['score']}/100")

    _event(task_id, "实验设计", "实验 Agent", "running")
    raw_experiment = experiment.design_experiment(topic, method_audit["final_output"])
    experiment_audit = leader.review_task("实验设计", topic, raw_experiment, "统计与伦理要求完整")
    _event(task_id, "实验设计", "领导 Agent", "completed", f"质量评分 {experiment_audit['score']}/100")
    return {
        "review": reviewed["final_output"],
        "method": method_audit["final_output"],
        "experiment": experiment_audit["final_output"],
        "sources": retrieved["external"],
    }


def _run_teaching(task_id: str, topic: str) -> dict:
    """执行教学设计流程。

    Args:
        task_id: 任务编号。
        topic: 教学主题。

    Returns:
        领导 Agent 审核后的教学设计。
    """
    _event(task_id, "教学设计", "教学 Agent", "running")
    raw_plan = teaching.design_teaching(topic)
    audit = leader.review_task("教学设计", topic, raw_plan, "目标可测量、活动与评价一致")
    _event(task_id, "教学设计", "领导 Agent", "completed", f"质量评分 {audit['score']}/100")
    return {"teaching": audit["final_output"], "audit": audit["report"]}


def _run_literature(task_id: str, topic: str) -> dict:
    """执行文献精读课设计流程。

    Args:
        task_id: 任务编号。
        topic: 文献精读主题。

    Returns:
        精读课交付与来源。
    """
    _event(task_id, "精读材料检索", "检索 Agent", "running")
    retrieved = retrieval.retrieve(topic)
    context = retrieval.format_context(retrieved)
    _event(task_id, "精读材料检索", "检索 Agent", "completed")
    _event(task_id, "文献精读课设计", "教学 Agent", "running")
    raw_lesson = teaching.analyze_literature(topic, context)
    audit = leader.review_task("文献精读教学", topic, raw_lesson, "覆盖方法判断、证据等级与讨论题")
    _event(task_id, "文献精读课设计", "领导 Agent", "completed", f"质量评分 {audit['score']}/100")
    return {"lesson": audit["final_output"], "sources": retrieved["external"]}
