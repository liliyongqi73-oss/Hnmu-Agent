"""HNMU-Agent FastAPI 主入口。"""
from __future__ import annotations

import mimetypes

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.router import api_router
from .core.config import WEB_DIST_DIR, ensure_workspace_dirs

ensure_workspace_dirs()

# Windows 某些环境会把 .js 识别为 text/plain，浏览器会拒绝加载 ES Module。
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/json", ".json")

app = FastAPI(
    title="HNMU-Agent API",
    description="科研教学多智能体工作台后端",
    version="2.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)

# 前端构建完成后由 FastAPI 统一托管，部署时只需启动一个服务。
if WEB_DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=WEB_DIST_DIR, html=True), name="web")
