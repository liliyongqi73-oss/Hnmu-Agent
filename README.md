# HNMU-Agent · 科研教学多智能体工作台

主应用已重构为 **Vue 3 + Vite + Element Plus + FastAPI**。领导 Agent 统一调度检索、综述、方法、实验、写作与教学 Agent，并逐项审核最终交付。

## 特性

- **领导 Agent 质量门禁**：审核各执行 Agent 的准确性、完整性、可执行性与规范性，未达标时直接修订
- **多智能体编排**：基于 LangGraph，编排检索 / 综述 / 方法 / 实验 / 写作 / 教学 / 领导审核智能体
- **检索增强 (RAG)**：Chroma 向量库 + BGE-M3 中文 embedding，接入院内文献库
- **外部检索**：PubMed / arXiv 文献接口
- **混合 LLM 部署**：敏感数据走本地模型（Qwen/DeepSeek via Ollama），公开任务走云端 API
- **独立前后端架构**：Vue 3 工作台 + FastAPI API，固定侧边栏不依赖 Chainlit 注入
- **科研教学工作台**：提供科研协作、教学备课、文献精读三类模式，支持过程展示与引用溯源
- **后台任务运行时**：长耗时 Agent 流程异步执行，进度和结果写入 `workspace/runtime`

## 架构

```
用户 ── Chainlit 科研教学工作台 ── 领导 Agent
                                  │
                ┌─────────┬───────┼───────┬─────────┬─────────┐
                ▼         ▼       ▼       ▼         ▼         ▼
             检索Agent  综述Agent 方法Agent 实验Agent 写作Agent 教学Agent
                │
                ▼
        PubMed / arXiv / Chroma RAG

每个执行 Agent 产出后均返回领导 Agent 审核，通过或修订后再进入下一阶段。
```

## 快速开始

> 需要 **Python 3.10+**（Chainlit/LangGraph 要求）。当前机器是 3.9，请先升级或建一个 3.10+ 虚拟环境。

```powershell
# 1. 安装后端依赖
.\.venv\Scripts\pip.exe install -r requirements.txt

# 2. 安装并构建前端
Set-Location web
npm install
npm run build
Set-Location ..

# 3. 启动统一服务
.\start-fastapi.ps1
```

访问 `http://127.0.0.1:8000`。开发前端时可在 `web/` 下运行 `npm run dev`。

## 登录、权限与 MySQL

系统用户保存在本地 MySQL，首个注册账号自动成为管理员，后续注册账号默认为普通用户。管理员可管理模型配置、用户角色和账号状态。

先使用有建库权限的 MySQL 账号创建专用账号：

```sql
CREATE DATABASE IF NOT EXISTS hnmu_agent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'hnmu_agent'@'localhost' IDENTIFIED BY 'replace-with-strong-password';
GRANT ALL PRIVILEGES ON hnmu_agent.* TO 'hnmu_agent'@'localhost';
FLUSH PRIVILEGES;
```

然后在 `.env` 配置数据库连接和 JWT 密钥：

```dotenv
DATABASE_URL=mysql+pymysql://hnmu_agent:replace-with-strong-password@127.0.0.1:3306/hnmu_agent?charset=utf8mb4
AUTH_SECRET_KEY=replace-with-a-long-random-secret
AUTH_TOKEN_EXPIRE_MINUTES=1440
BOOTSTRAP_ADMIN_USERNAME=admin
BOOTSTRAP_ADMIN_PASSWORD=replace-with-a-strong-password
BOOTSTRAP_ADMIN_DISPLAY_NAME=系统管理员
```

服务启动时会自动创建用户表，并在用户表为空时创建默认管理员。登录成功后返回带过期时间的 JWT，前端后续请求统一携带 `Authorization: Bearer <token>`。未配置有效 MySQL 凭据时，健康检查返回 `degraded`，注册和登录接口返回 `503`。

## 目录结构

```
HNMU-Agent/
├── server/                 # FastAPI 路由、服务、运行时与接口契约
├── web/                    # Vue 3 + Element Plus 工作台
├── workspace/              # 会话、任务、记忆、技能与团队运行数据
├── app.py                  # Chainlit 旧入口，保留用于兼容
├── requirements.txt
├── .env.example
├── src/
│   ├── config.py           # 配置与 LLM 路由策略
│   ├── llm_router.py       # 混合部署：本地/云端模型路由
│   ├── orchestrator.py     # LangGraph 多智能体编排
│   ├── agents/             # 各子智能体
│   │   ├── leader.py       # 领导审核与质量门禁
│   │   ├── retrieval.py    # 文献检索
│   │   ├── review.py       # 综述生成
│   │   ├── method.py       # 方法/创新点
│   │   ├── experiment.py   # 实验设计
│   │   ├── writing.py      # 论文写作
│   │   └── teaching.py     # 教学设计与文献精读
│   ├── rag/
│   │   ├── vectorstore.py  # Chroma 向量库
│   │   └── ingest.py       # 文献入库
│   └── tools/
│       └── literature.py   # PubMed / arXiv 检索
├── data/                   # 本地文献库
├── ARCHITECTURE.md         # 顶层目录设计与分层原则
└── paper/                  # 论文初稿
    └── paper.md
```

## 部署策略（混合）

| 任务类型 | 路由 | 说明 |
|---|---|---|
| 院内敏感数据处理 | 本地 Ollama (Qwen) | 数据不出院 |
| 领导 Agent 审核 | 本地 Ollama (Qwen) | 完整科研材料不出院 |
| 公开文献检索/综述 | 云端 API (DeepSeek) | 效果优先 |

通过 `src/config.py` 中 `SENSITIVE_TASKS` 控制路由。
