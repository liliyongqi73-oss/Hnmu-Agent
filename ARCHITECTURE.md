# HNMU-Agent 顶层架构

```text
HNMU-Agent/
├─ server/                         # FastAPI 接口与应用服务
│  └─ app/
│     ├─ api/                      # HTTP 路由与接口版本
│     ├─ core/                     # 服务配置与基础设施
│     ├─ runtime/                  # 后台任务状态与调度
│     ├─ schemas/                  # Pydantic 接口契约
│     ├─ services/                 # 模型、工作台、任务编排服务
│     └─ main.py                   # FastAPI 入口
├─ web/                            # Vue 3 + Vite + Element Plus 工作台
│  ├─ src/
│  │  ├─ api/                      # 后端请求封装
│  │  ├─ components/               # 可复用工作台组件
│  │  ├─ composables/              # 页面状态与轮询逻辑
│  │  ├─ layouts/                  # 固定侧边栏与主布局
│  │  ├─ styles/                   # 主题与全局样式
│  │  └─ views/                    # 首页、任务、Agent 等页面
│  └─ dist/                        # 生产构建，由 FastAPI 托管
├─ src/                            # 可复用 Agent 能力内核
│  ├─ agents/                      # 领导、检索、综述、方法、实验、教学 Agent
│  ├─ rag/                         # 院内知识库与向量检索
│  ├─ tools/                       # PubMed、arXiv 等工具
│  └─ llm_router.py                # 本地与云端模型路由
├─ workspace/                      # 用户工作区与持久化运行数据
│  ├─ sessions/
│  ├─ runtime/
│  ├─ uploads/
│  ├─ memory/
│  ├─ skills/
│  └─ team/
├─ data/                           # 原始知识库数据
└─ legacy/                         # 后续迁移 Chainlit 旧入口的预留位置
```

## 分层原则

1. `web` 只处理交互与展示，通过 `/api/v1` 使用服务端能力。
2. `server` 负责接口契约、后台任务、状态管理和应用编排，不直接堆放 Agent 提示词。
3. `src` 是与 UI 无关的能力内核，可被 FastAPI、测试或命令行复用。
4. `workspace` 保存用户运行数据，和项目源代码、知识库原始数据分离。
5. 敏感任务始终由本地模型执行，模型切换只改变允许外发的公开任务。
