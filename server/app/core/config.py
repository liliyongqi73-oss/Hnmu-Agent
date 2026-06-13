"""FastAPI 服务端配置。"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
WEB_DIST_DIR = PROJECT_ROOT / "web" / "dist"
WORKSPACE_DIR = PROJECT_ROOT / "workspace"
TASK_RUNTIME_DIR = WORKSPACE_DIR / "runtime"


def ensure_workspace_dirs() -> None:
    """创建服务端运行需要的工作区目录。

    Returns:
        None。
    """
    for path in (
        WORKSPACE_DIR / "sessions",
        WORKSPACE_DIR / "uploads",
        WORKSPACE_DIR / "memory",
        WORKSPACE_DIR / "skills",
        WORKSPACE_DIR / "team",
        TASK_RUNTIME_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
