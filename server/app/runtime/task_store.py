"""线程安全的任务状态存储。"""
from __future__ import annotations

from datetime import datetime
import json
from threading import Lock
from uuid import uuid4

from ..core.config import TASK_RUNTIME_DIR
from ..schemas.models import TaskCreateRequest, TaskEvent, TaskRecord

_TASKS: dict[str, TaskRecord] = {}
_LOCK = Lock()


def _now() -> str:
    """返回 ISO 格式当前时间。

    Returns:
        当前本地时间字符串。
    """
    return datetime.now().isoformat(timespec="seconds")


def _persist(record: TaskRecord) -> None:
    """把任务状态持久化到工作区。

    Args:
        record: 最新任务记录。

    Returns:
        None。
    """
    TASK_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    path = TASK_RUNTIME_DIR / f"{record.id}.json"
    path.write_text(
        json.dumps(record.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _load_persisted_tasks() -> None:
    """从工作区恢复历史任务状态。

    Returns:
        None。

    Notes:
        服务退出时仍在运行的任务恢复后标记为失败，避免前端永久显示运行中。
    """
    TASK_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    for path in TASK_RUNTIME_DIR.glob("*.json"):
        try:
            record = TaskRecord.model_validate_json(path.read_text(encoding="utf-8"))
            if record.status in {"queued", "running"}:
                record.status = "failed"
                record.error = "服务重启导致任务中断，请重新提交。"
                record.updated_at = _now()
                _persist(record)
            _TASKS[record.id] = record
        except (OSError, ValueError):
            continue


def create_task(request: TaskCreateRequest) -> TaskRecord:
    """创建排队中的后台任务。

    Args:
        request: 任务创建请求。

    Returns:
        新任务记录。
    """
    record = TaskRecord(
        id=uuid4().hex,
        topic=request.topic,
        mode=request.mode,
        model_strategy=request.model_strategy,
        status="queued",
        created_at=_now(),
        updated_at=_now(),
    )
    with _LOCK:
        _TASKS[record.id] = record
        _persist(record)
    return record.model_copy(deep=True)


def get_task(task_id: str) -> TaskRecord | None:
    """读取任务状态。

    Args:
        task_id: 任务编号。

    Returns:
        任务副本，不存在时返回 None。
    """
    with _LOCK:
        record = _TASKS.get(task_id)
        return record.model_copy(deep=True) if record else None


def list_tasks() -> list[TaskRecord]:
    """返回按创建时间倒序排列的任务列表。

    Returns:
        任务记录列表。
    """
    with _LOCK:
        return [
            item.model_copy(deep=True)
            for item in sorted(_TASKS.values(), key=lambda task: task.created_at, reverse=True)
        ]


def update_task(task_id: str, **changes) -> None:
    """更新任务状态字段。

    Args:
        task_id: 任务编号。
        changes: 需要更新的字段。

    Returns:
        None。
    """
    with _LOCK:
        record = _TASKS[task_id]
        for key, value in changes.items():
            setattr(record, key, value)
        record.updated_at = _now()
        _persist(record)


def append_event(task_id: str, event: TaskEvent) -> None:
    """追加任务阶段事件，终态事件会替换对应的运行事件。

    Args:
        task_id: 任务编号。
        event: 阶段事件。

    Returns:
        None。

    Notes:
        替换运行事件可让前端在阶段完成后自动隐藏实时过程，同时保留阶段结果。
    """
    with _LOCK:
        record = _TASKS[task_id]
        event_index = next(
            (
                index
                for index in range(len(record.events) - 1, -1, -1)
                if record.events[index].stage == event.stage
                and record.events[index].status == "running"
            ),
            None,
        )
        if event.status in {"completed", "failed"} and event_index is not None:
            record.events[event_index] = event
        else:
            record.events.append(event)
        record.updated_at = _now()
        _persist(record)


_load_persisted_tasks()
