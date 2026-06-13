"""全局配置与 LLM 路由策略。

混合部署核心：通过 SENSITIVE_TASKS 决定某类任务走本地模型还是云端 API。
"""
from __future__ import annotations

import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# HuggingFace 国内镜像，解决 huggingface.co 无法访问导致的 embedding 下载失败。
# 必须在 import sentence_transformers/transformers 之前设置。
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 云端 LLM
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    # 本地 LLM (Ollama, OpenAI 兼容接口)
    local_base_url: str = "http://localhost:11434/v1"
    local_model: str = "qwen3.5:9b"

    # Embedding
    embedding_model: str = "BAAI/bge-m3"

    # 外部检索
    pubmed_email: str = "your_email@example.com"
    pubmed_api_key: str = ""

    # RAG
    chroma_dir: str = "./data/chroma"

    # MySQL 与认证
    database_url: str = "mysql+pymysql://root:change-me@127.0.0.1:3306/hnmu_agent?charset=utf8mb4"
    auth_secret_key: str = "change-this-secret-in-production"
    auth_token_expire_minutes: int = 1440
    bootstrap_admin_username: str = ""
    bootstrap_admin_password: str = ""
    bootstrap_admin_display_name: str = "系统管理员"

    # 全本地模式：未配置云端 key 时设 true，所有任务走本地 Ollama（便于离线 demo）
    all_local: bool = False


settings = Settings()

# 敏感任务集合 -> 走本地模型；其余走云端。
# 院内文献处理、患者相关数据归类为敏感。
SENSITIVE_TASKS: set[str] = {
    "rag_local",      # 检索本地院内文献库
    "experiment",     # 实验/方法设计可能涉及未公开数据
    "leader",         # 审核内容可能包含完整的院内科研材料
}
