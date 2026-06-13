"""科研教学后台任务状态机服务。"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from threading import Thread

from src.llm_router import (
    MODEL_STRATEGY_AUTO,
    MODEL_STRATEGY_DEEPSEEK,
    MODEL_STRATEGY_LOCAL,
    set_model_config,
    set_model_strategy,
)
from src.orchestrator.engine import build_plan_result, run_step
from src.plan import Plan, Step, build_custom_plan, get_plan

from ..runtime import task_store, task_stream
from ..schemas.models import TaskActionRequest, TaskCreateRequest, TaskEvent
from .model_service import get_model_runtime

STRATEGY_MAP = {
    "auto": MODEL_STRATEGY_AUTO,
    "local": MODEL_STRATEGY_LOCAL,
    "deepseek": MODEL_STRATEGY_DEEPSEEK,
}
INTEGRITY_STEPS = {"integrity1", "integrity2"}


def _now() -> str:
    """返回当前 ISO 时间字符串。"""
    return datetime.now().isoformat(timespec="seconds")


def _build_plan(record) -> Plan:
    """根据任务记录恢复执行计划。"""
    if record.agents or record.mode == "custom":
        with_retrieval = "retrieval" in record.agents or bool(
            record.journals or record.arxiv_categories or record.conferences
        )
        return build_custom_plan(record.agents, with_retrieval=with_retrieval)
    return get_plan(record.mode)


def _step_snapshot(plan: Plan) -> list[dict]:
    """生成供前端仪表盘展示的阶段快照。"""
    return [
        {"id": step.id, "stage": step.stage, "kind": step.kind, "status": "pending"}
        for step in plan.steps
    ]


def submit_task(request: TaskCreateRequest):
    """创建任务并启动首个阶段。"""
    record = task_store.create_task(request)
    plan = _build_plan(record)
    task_store.update_task(record.id, pipeline_steps=_step_snapshot(plan))
    Thread(target=_run_current_step, args=(record.id,), daemon=True).start()
    return task_store.get_task(record.id)


def apply_task_action(task_id: str, request: TaskActionRequest):
    """处理流程确认点操作并按状态机推进。"""
    record = task_store.get_task(task_id)
    if not record:
        raise KeyError(task_id)
    if record.status == "running":
        raise ValueError("当前阶段正在执行，请等待阶段完成")
    if record.status in {"completed", "failed", "aborted"}:
        raise ValueError("任务已结束，不能继续操作")

    decision = {"action": request.action, "note": request.note, "at": _now(), "step": record.current_step}
    decisions = [*record.decisions, decision]
    if request.action == "abort":
        task_store.update_task(task_id, status="aborted", decisions=decisions, checkpoint={})
        return task_store.get_task(task_id)
    if request.action == "pause":
        task_store.update_task(task_id, status="paused", decisions=decisions)
        return task_store.get_task(task_id)
    if request.action not in {"continue", "resume", "retry"}:
        raise ValueError("不支持的流程操作")

    checkpoint = record.checkpoint or {}
    if checkpoint.get("blocked") and request.action != "retry":
        retries = int(checkpoint.get("retries", 0))
        if retries < 3:
            raise ValueError("诚信闸门未通过，请先重试核查")
        decision["note"] = request.note or "用户确认带未核验风险继续"

    next_step = record.current_step if request.action == "retry" else int(checkpoint.get("next_step", record.current_step))
    retry_checkpoint = {"retries": int(checkpoint.get("retries", 0))} if request.action == "retry" else {}
    task_store.update_task(
        task_id,
        status="queued",
        current_step=next_step,
        checkpoint=retry_checkpoint,
        decisions=decisions,
        error="",
    )
    Thread(target=_run_current_step, args=(task_id,), daemon=True).start()
    return task_store.get_task(task_id)


def _event(task_id: str, stage: str, agent: str, status: str, summary: str = "") -> None:
    """记录任务阶段事件。"""
    task_store.append_event(task_id, TaskEvent(stage=stage, agent=agent, status=status, summary=summary))


def _make_stream_handler(task_id: str):
    """构造实时消息与阶段产出持久化处理器。"""
    def handle(message: dict) -> None:
        task_stream.publish(task_id, message)
        if message.get("type") == "stage_done":
            task_store.set_event_output(task_id, message["stage"], str(message.get("output", "")))

    return handle


def _mark_step(record, index: int, status: str) -> list[dict]:
    """更新流程仪表盘中的单个阶段状态。"""
    steps = [dict(item) for item in record.pipeline_steps]
    if 0 <= index < len(steps):
        steps[index]["status"] = status
    return steps


def _mark_skipped_steps(steps: list[dict], current_step: int, next_step: int) -> list[dict]:
    """把条件分支越过的阶段标记为跳过。"""
    marked = [dict(item) for item in steps]
    for index in range(current_step + 1, next_step):
        if marked[index]["status"] == "pending":
            marked[index]["status"] = "skipped"
    return marked


def _material_passport(record, step: Step, next_step: int) -> dict:
    """生成当前确认点材料护照，供审计和断点续跑。"""
    return {
        "version": len(record.step_results),
        "topic": record.topic,
        "completed_stage": step.stage,
        "completed_step_id": step.id,
        "next_step": next_step,
        "artifact_ids": list(record.step_results.keys()),
        "decision_count": len(record.decisions),
        "generated_at": _now(),
    }


def _integrity_passed(fields: dict) -> bool:
    """解析诚信核查结论。"""
    output = str(fields.get("output", ""))
    return "【诚信结论】通过" in output and "【诚信结论】存在问题" not in output


def _route_next(plan: Plan, record, step: Step, fields: dict) -> int:
    """依据评审分支计算下一个阶段，并补齐被跳过分支的材料别名。"""
    next_index = record.current_step + 1
    results = dict(record.step_results)
    step_by_id = {item.id: index for index, item in enumerate(plan.steps)}
    decision = str(fields.get("decision", ""))

    if step.id == "peer_review" and "接受" in decision:
        results["revision"] = results["draft"]
        results["revision2"] = results["draft"]
        results["peer_review2"] = results["peer_review"]
        next_index = step_by_id["integrity2"]
    elif step.id == "peer_review2" and "大修" not in decision:
        results["revision2"] = results["revision"]
        next_index = step_by_id["integrity2"]

    task_store.update_task(record.id, step_results=results)
    return next_index


def _complete_or_checkpoint(task_id: str, plan: Plan, step: Step, fields: dict) -> None:
    """阶段完成后进入确认点，或组装最终交付。"""
    record = task_store.get_task(task_id)
    if not record:
        return
    task_store.update_step_result(task_id, step.id, fields)
    record = task_store.get_task(task_id)
    next_step = _route_next(plan, record, step, fields)
    record = task_store.get_task(task_id)
    steps = _mark_step(record, record.current_step, "completed")
    steps = _mark_skipped_steps(steps, record.current_step, next_step)
    passport = _material_passport(record, step, next_step)

    if next_step >= len(plan.steps):
        result = build_plan_result(plan, record.topic, record.step_results)
        task_store.update_task(
            task_id,
            status="completed",
            pipeline_steps=steps,
            checkpoint={},
            material_passport=passport,
            result=result,
        )
        task_stream.publish(task_id, {"type": "task_done", "result": result})
        return

    blocked = step.id in INTEGRITY_STEPS and not _integrity_passed(fields)
    previous_retries = int(record.checkpoint.get("retries", 0))
    checkpoint = {
        "stage": step.stage,
        "step_id": step.id,
        "next_step": next_step,
        "blocked": blocked,
        "mandatory": step.id in INTEGRITY_STEPS,
        "retries": previous_retries + 1 if blocked else 0,
        "message": "诚信闸门未通过，修正问题后重新核查" if blocked else "阶段已完成，请确认后继续",
    }
    task_store.update_task(
        task_id,
        status="awaiting_confirmation",
        pipeline_steps=steps,
        checkpoint=checkpoint,
        material_passport=passport,
    )
    task_stream.publish(task_id, {"type": "checkpoint", "checkpoint": checkpoint})


def _correct_integrity_issues(task_id: str, record, step: Step, on_stream) -> dict[str, dict]:
    """诚信重试前按上一轮报告修订稿件。

    Args:
        task_id: 任务编号。
        record: 当前任务记录。
        step: 当前诚信核查阶段。
        on_stream: 实时消息处理器。

    Returns:
        已替换问题稿件的阶段结果。
    """
    source_id = "draft" if step.id == "integrity1" else "revision2"
    correction = Step(
        id=f"{step.id}_correction",
        stage=f"{step.stage}问题修正",
        kind="agent",
        agent="revision",
        inputs={
            "topic": "$topic",
            "draft": f"${source_id}.output",
            "review": f"${step.id}.output",
        },
        review=False,
    )
    corrected = run_step(
        correction,
        record.topic,
        record.step_results,
        lambda stage, agent, status, summary: _event(task_id, stage, agent, status, summary),
        on_stream=on_stream,
        reference=record.reference,
    )
    results = {key: dict(value) for key, value in record.step_results.items()}
    source = dict(results[source_id])
    source["output"] = corrected["output"]
    results[source_id] = source
    results[correction.id] = corrected
    task_store.update_task(task_id, step_results=results)
    return results


def _run_current_step(task_id: str) -> None:
    """执行当前单个阶段，结束后停在人工确认点。"""
    record = task_store.get_task(task_id)
    if not record:
        return
    plan = _build_plan(record)
    if record.current_step >= len(plan.steps):
        return
    step = plan.steps[record.current_step]
    on_stream = _make_stream_handler(task_id)
    try:
        set_model_strategy(STRATEGY_MAP.get(record.model_strategy, record.model_strategy))
        set_model_config(get_model_runtime(record.model_strategy) if record.model_strategy not in STRATEGY_MAP else None)
        task_store.update_task(
            task_id,
            status="running",
            pipeline_steps=_mark_step(record, record.current_step, "in_progress"),
        )
        task_stream.publish(task_id, {"type": "task_running", "step": asdict(step)})
        stored_results = dict(record.step_results)
        if step.id == "process":
            stored_results["pipeline"] = {
                "decisions": record.decisions,
                "passport": record.material_passport,
            }
        if step.id in INTEGRITY_STEPS and int(record.checkpoint.get("retries", 0)) > 0:
            stored_results = _correct_integrity_issues(task_id, record, step, on_stream)
        fields = run_step(
            step,
            record.topic,
            stored_results,
            lambda stage, agent, status, summary: _event(task_id, stage, agent, status, summary),
            retrieval_filters={
                "journals": record.journals,
                "categories": record.arxiv_categories,
                "databases": record.databases,
                "conferences": record.conferences,
                "year_from": record.year_from,
                "year_to": record.year_to,
                "max_results": record.max_results,
            },
            on_stream=on_stream,
            reference=record.reference,
        )
        _complete_or_checkpoint(task_id, plan, step, fields)
    except Exception as error:  # noqa: BLE001
        _event(task_id, "任务终止", "系统", "failed", str(error))
        task_store.update_task(task_id, status="failed", error=str(error))
        task_stream.publish(task_id, {"type": "task_failed", "error": str(error)})
    finally:
        task_stream.close(task_id)
