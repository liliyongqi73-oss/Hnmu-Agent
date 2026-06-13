"""后台任务接口。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ...runtime import task_store
from ...schemas.models import TaskCreateRequest, TaskRecord
from ...services.task_service import submit_task

router = APIRouter()


@router.post("", response_model=TaskRecord)
def create_task(request: TaskCreateRequest) -> TaskRecord:
    """创建科研或教学后台任务。

    Args:
        request: 任务创建请求。

    Returns:
        新任务状态。
    """
    return submit_task(request)


@router.get("", response_model=list[TaskRecord])
def tasks() -> list[TaskRecord]:
    """返回任务列表。

    Returns:
        任务状态列表。
    """
    return task_store.list_tasks()


@router.get("/{task_id}", response_model=TaskRecord)
def task(task_id: str) -> TaskRecord:
    """返回单个任务状态。

    Args:
        task_id: 任务编号。

    Returns:
        任务状态。
    """
    record = task_store.get_task(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="任务不存在")
    return record
