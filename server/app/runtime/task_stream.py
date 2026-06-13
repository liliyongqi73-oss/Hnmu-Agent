"""任务流式消息总线：连接同步任务线程与异步 SSE 端点。

后台任务线程通过 publish 推送 token 与阶段事件，
SSE 端点通过 subscribe 异步消费并下发给前端。
消息仅驻留内存、不持久化；阶段定稿与终态另由 task_store 持久化。
"""
from __future__ import annotations

import asyncio
from queue import Empty, Queue
from threading import Lock

# 每个任务一个消息队列。
_QUEUES: dict[str, Queue] = {}
_LOCK = Lock()

# 标记任务流结束的哨兵。
_SENTINEL = object()


def _get_queue(task_id: str) -> Queue:
    """获取或创建任务的消息队列。

    Args:
        task_id: 任务编号。

    Returns:
        该任务的消息队列。
    """
    with _LOCK:
        queue = _QUEUES.get(task_id)
        if queue is None:
            queue = Queue()
            _QUEUES[task_id] = queue
        return queue


def publish(task_id: str, message: dict) -> None:
    """向任务流推送一条消息。

    Args:
        task_id: 任务编号。
        message: 流式消息字典，含 type 与负载字段。

    Returns:
        None。
    """
    _get_queue(task_id).put(message)


def close(task_id: str) -> None:
    """标记任务流结束并安排清理。

    Args:
        task_id: 任务编号。

    Returns:
        None。
    """
    _get_queue(task_id).put(_SENTINEL)


async def subscribe(task_id: str, heartbeat: float = 15.0):
    """异步消费任务流消息，直到流结束。

    Args:
        task_id: 任务编号。
        heartbeat: 无消息时发送心跳的间隔秒数。

    Yields:
        流式消息字典；超时则产出 None 作为心跳信号。

    Notes:
        阻塞式队列读取放到线程池执行，避免阻塞事件循环；
        流结束后清理队列，防止内存堆积。
    """
    queue = _get_queue(task_id)
    loop = asyncio.get_event_loop()
    try:
        while True:
            try:
                message = await loop.run_in_executor(None, queue.get, True, heartbeat)
            except Empty:
                yield None  # 心跳，保持连接活跃。
                continue
            if message is _SENTINEL:
                break
            yield message
    finally:
        with _LOCK:
            _QUEUES.pop(task_id, None)
