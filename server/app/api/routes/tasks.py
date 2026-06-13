"""后台任务接口。"""
from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from src.tools.sources import (
    list_arxiv_categories,
    list_computer_science_conferences,
    list_pubmed_journals,
    list_retrieval_databases,
)

from ...core.config import UPLOAD_DIR
from ...runtime import task_store, task_stream
from ...schemas.models import RetrievalSources, TaskActionRequest, TaskCreateRequest, TaskRecord, UploadResult
from ...services.task_service import apply_task_action, submit_task

router = APIRouter()

# 参考文件上传限制：仅纯文本，最大 2MB。
_MAX_UPLOAD_BYTES = 2 * 1024 * 1024
_ALLOWED_SUFFIXES = {".txt", ".md", ".markdown"}


@router.post("/upload", response_model=UploadResult)
async def upload_reference(file: UploadFile = File(...)) -> UploadResult:
    """上传参考文件并解析为文本上下文。

    Args:
        file: 上传的文本文件（.txt / .md）。

    Returns:
        解析结果，含文件名、字符数、预览与全文。

    Raises:
        HTTPException: 扩展名不支持、文件过大或无法按 UTF-8 解码。
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="仅支持 .txt 或 .md 文本文件")
    raw = await file.read()
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="文件过大，请控制在 2MB 以内")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="文件需为 UTF-8 编码的纯文本")
    # 留存原始上传文件，便于追溯。
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / f"{uuid4().hex}{suffix}").write_text(text, encoding="utf-8")
    return UploadResult(
        filename=file.filename or "reference.txt",
        chars=len(text),
        preview=text[:300],
        text=text,
    )


@router.get("/sources", response_model=RetrievalSources)
def retrieval_sources() -> RetrievalSources:
    """返回检索来源预置清单。

    Returns:
        预置的 PubMed 期刊与 arXiv 学科分类清单，供前端下拉选择。
    """
    return RetrievalSources(
        journals=list_pubmed_journals(),
        arxiv_categories=list_arxiv_categories(),
        databases=list_retrieval_databases(),
        conferences=list_computer_science_conferences(),
    )


@router.get("/{task_id}/stream")
async def stream_task(task_id: str) -> StreamingResponse:
    """以 SSE 流式推送任务的实时过程（token 与多轮审核）。

    Args:
        task_id: 任务编号。

    Returns:
        text/event-stream 流式响应。

    Raises:
        HTTPException: 任务不存在。
    """
    if not task_store.get_task(task_id):
        raise HTTPException(status_code=404, detail="任务不存在")

    async def event_source():
        async for message in task_stream.subscribe(task_id):
            if message is None:
                yield ": heartbeat\n\n"  # 心跳注释行，保持连接。
                continue
            yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("", response_model=TaskRecord)
def create_task(request: TaskCreateRequest) -> TaskRecord:
    """创建科研或教学后台任务。

    Args:
        request: 任务创建请求。

    Returns:
        新任务状态。
    """
    return submit_task(request)


@router.post("/{task_id}/actions", response_model=TaskRecord)
def task_action(task_id: str, request: TaskActionRequest) -> TaskRecord:
    """处理流程确认、暂停、恢复、重试或终止操作。"""
    try:
        return apply_task_action(task_id, request)
    except KeyError:
        raise HTTPException(status_code=404, detail="任务不存在")
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))


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
