"""HNMU-Agent Chainlit 工作台入口。

提供科研协作、教学备课、文献精读三类工作模式，并展示多智能体执行过程。
每个执行 Agent 完成任务后，均由领导 Agent 进行质量审核与最终交付。
"""
from __future__ import annotations

import chainlit as cl
from chainlit.input_widget import Select

from src.agents import experiment, leader, method, retrieval, review, teaching, writing
from src.llm_router import MODEL_STRATEGIES, MODEL_STRATEGY_AUTO, set_model_strategy

RESEARCH_MODE = "科研协作"
TEACHING_MODE = "教学备课"
LITERATURE_MODE = "文献精读"


@cl.set_starters
async def set_starters():
    """配置首页快捷任务入口。

    Returns:
        面向科研与教学场景的快捷任务列表。
    """
    return [
        cl.Starter(
            label="启动科研课题协作",
            message="【科研课题】基于深度学习的肺结节良恶性分类",
            icon="flask-conical",
        ),
        cl.Starter(
            label="设计一堂医学课程",
            message="【教学设计】为本科生设计一堂循证医学入门课",
            icon="presentation",
        ),
        cl.Starter(
            label="开展文献精读课",
            message="【文献精读】人工智能辅助医学影像诊断",
            icon="library",
        ),
        cl.Starter(
            label="生成实验与统计方案",
            message="【科研课题】观察某干预对2型糖尿病患者血糖控制的影响",
            icon="chart-no-axes-combined",
        ),
    ]


@cl.on_chat_start
async def start() -> None:
    """初始化工作台、模式设置与 Agent 团队说明。"""
    settings = await cl.ChatSettings(
        [
            Select(
                id="work_mode",
                label="工作模式",
                values=[RESEARCH_MODE, TEACHING_MODE, LITERATURE_MODE],
                initial_index=0,
                description="选择领导 Agent 要调度的协作流程",
            ),
            Select(
                id="model_strategy",
                label="模型切换",
                values=list(MODEL_STRATEGIES),
                initial_value=MODEL_STRATEGY_AUTO,
                description="云端策略下，实验设计与领导审核等敏感任务仍使用本地模型",
            ),
        ]
    ).send()
    cl.user_session.set("work_mode", settings["work_mode"])
    cl.user_session.set("model_strategy", settings["model_strategy"])
    set_model_strategy(settings["model_strategy"])

    # 展示工作台概览，帮助用户快速理解多智能体分工。
    await cl.Message(
        content=(
            "# HNMU 科研教学智能工作台\n\n"
            "将研究主题、课程主题或文献精读需求交给团队，领导 Agent 会统一调度并逐项验收。\n\n"
            "| Agent 团队 | 核心职责 | 质量状态 |\n"
            "|---|---|---|\n"
            "| 领导 Agent | 分配任务、审核质量、修订交付 | 全流程在线 |\n"
            "| 科研 Agent 组 | 检索、综述、方法、实验、论文写作 | 按需协作 |\n"
            "| 教学 Agent | 课程设计、案例教学、评价量规 | 按需协作 |\n\n"
            "**工作方式**：选择右上角设置中的工作模式，或直接点击下方快捷任务开始。"
        ),
        author="领导 Agent",
    ).send()


@cl.on_settings_update
async def update_settings(settings: dict) -> None:
    """保存用户选择的工作模式。

    Args:
        settings: Chainlit 设置面板返回的数据。
    """
    cl.user_session.set("work_mode", settings.get("work_mode", RESEARCH_MODE))
    selected_model = set_model_strategy(settings.get("model_strategy", MODEL_STRATEGY_AUTO))
    cl.user_session.set("model_strategy", selected_model)
    await cl.Message(
        content=(
            f"工作模式：**{cl.user_session.get('work_mode')}**\n\n"
            f"模型策略：**{selected_model}**"
        ),
        author="领导 Agent",
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """根据用户选择或消息前缀调度科研与教学流程。

    Args:
        message: 用户消息。
    """
    # 每次任务开始时恢复当前会话的模型策略，隔离并发用户的模型选择。
    set_model_strategy(cl.user_session.get("model_strategy") or MODEL_STRATEGY_AUTO)
    mode, topic = _resolve_mode(message.content.strip())
    try:
        if mode == TEACHING_MODE:
            await _run_teaching_pipeline(topic)
            return
        if mode == LITERATURE_MODE:
            await _run_literature_pipeline(topic)
            return
        await _run_research_pipeline(topic)
    except Exception as error:  # noqa: BLE001  避免单个服务异常中断会话
        await cl.Message(
            content=(
                f"处理任务时出现异常：`{error}`\n\n"
                "请检查 `.env` 模型配置、本地 Ollama 服务与外部检索网络。"
            ),
            author="系统",
        ).send()


def _resolve_mode(content: str) -> tuple[str, str]:
    """解析消息前缀并确定工作模式。

    Args:
        content: 用户原始消息。

    Returns:
        工作模式与清理前缀后的任务主题。
    """
    prefixes = {
        "【科研课题】": RESEARCH_MODE,
        "【教学设计】": TEACHING_MODE,
        "【文献精读】": LITERATURE_MODE,
    }
    for prefix, mode in prefixes.items():
        if content.startswith(prefix):
            return mode, content.removeprefix(prefix).strip()
    return cl.user_session.get("work_mode") or RESEARCH_MODE, content


async def _audit(task_name: str, topic: str, output: str, criteria: str) -> dict:
    """调用领导 Agent 审核并在界面展示验收结果。

    Args:
        task_name: 被审核任务名称。
        topic: 当前任务主题。
        output: 执行 Agent 原始产出。
        criteria: 补充验收标准。

    Returns:
        领导 Agent 标准化审核结果。
    """
    async with cl.Step(name=f"领导 Agent 审核：{task_name}", type="tool") as step:
        # 统一调用领导 Agent，确保每个执行环节都有质量门禁。
        audit = leader.review_task(task_name, topic, output, criteria)
        status = "达标" if audit["passed"] else "已修订"
        step.output = f"{status}｜质量评分 {audit['score']}/100\n\n{audit['report']}"
    return audit


async def _run_research_pipeline(topic: str) -> None:
    """执行带领导审核的科研多智能体流水线。

    Args:
        topic: 科研主题。
    """
    await cl.Message(
        content=f"已接收科研任务：**{topic}**\n\n领导 Agent 正在组织科研 Agent 团队协作。",
        author="领导 Agent",
    ).send()

    # 调用检索 Agent 汇总外部文献与院内知识库。
    async with cl.Step(name="检索 Agent｜多源证据检索") as step:
        retrieved = retrieval.retrieve(topic)
        context = retrieval.format_context(retrieved)
        external_count = len([item for item in retrieved["external"] if "error" not in item])
        local_count = len(retrieved["local"])
        step.output = f"外部文献 {external_count} 篇，院内库命中 {local_count} 条。"
    await _audit("文献检索", topic, context, "来源有效、主题相关、不得把检索失败当作证据")
    await _publish_sources(retrieved)

    # 调用综述 Agent 归纳证据，再交由领导 Agent 验收。
    async with cl.Step(name="综述 Agent｜研究现状与空白") as step:
        raw_review = review.write_review(topic, context)
        step.output = raw_review
    reviewed = await _audit("相关工作综述", topic, raw_review, "论断可追溯，明确研究空白")
    final_review = reviewed["final_output"]
    await cl.Message(content=f"## 相关工作综述\n{final_review}", author="综述 Agent").send()

    # 调用方法 Agent 提出回应研究空白的方案。
    async with cl.Step(name="方法 Agent｜研究方案与创新点") as step:
        raw_method = method.propose_method(topic, final_review)
        step.output = raw_method
    method_audit = await _audit("方法与创新点", topic, raw_method, "创新真实、可行且回应研究空白")
    final_method = method_audit["final_output"]
    await cl.Message(content=f"## 方法与创新点\n{final_method}", author="方法 Agent").send()

    # 调用实验 Agent 设计可复现、合规的验证方案。
    async with cl.Step(name="实验 Agent｜实验与统计设计") as step:
        raw_experiment = experiment.design_experiment(topic, final_method)
        step.output = raw_experiment
    experiment_audit = await _audit("实验设计", topic, raw_experiment, "设计可复现，统计与伦理要求完整")
    final_experiment = experiment_audit["final_output"]
    await cl.Message(content=f"## 实验设计\n{final_experiment}", author="实验 Agent").send()

    materials = {
        "topic": topic,
        "review": final_review,
        "method": final_method,
        "experiment": final_experiment,
    }
    for section_name in ("摘要", "引言", "结论"):
        # 调用写作 Agent 生成章节，并逐章通过领导 Agent 质量门禁。
        async with cl.Step(name=f"写作 Agent｜{section_name}") as step:
            raw_section = writing.write_section(section_name, materials)
            step.output = raw_section
        section_audit = await _audit(
            f"论文{section_name}",
            topic,
            raw_section,
            "学术规范、逻辑一致、不捏造证据或结果",
        )
        await cl.Message(
            content=f"## {section_name}\n{section_audit['final_output']}",
            author="写作 Agent",
        ).send()

    await cl.Message(
        content="科研协作任务已完成，所有交付均已通过领导 Agent 审核或完成修订。",
        author="领导 Agent",
    ).send()


async def _run_teaching_pipeline(topic: str) -> None:
    """执行教学设计与领导审核流程。

    Args:
        topic: 教学主题或备课需求。
    """
    async with cl.Step(name="教学 Agent｜课程设计") as step:
        # 调用教学 Agent 形成完整备课方案。
        raw_plan = teaching.design_teaching(topic)
        step.output = raw_plan
    audit = await _audit(
        "教学设计",
        topic,
        raw_plan,
        "目标可测量、活动可实施、评价与目标一致，并包含伦理与科研诚信",
    )
    await cl.Message(
        content=f"# 教学设计方案\n{audit['final_output']}",
        author="教学 Agent",
    ).send()


async def _run_literature_pipeline(topic: str) -> None:
    """执行文献检索、教学精读设计与领导审核流程。

    Args:
        topic: 文献精读主题。
    """
    async with cl.Step(name="检索 Agent｜精读材料检索") as step:
        # 调用检索 Agent 为精读课准备证据材料。
        retrieved = retrieval.retrieve(topic)
        context = retrieval.format_context(retrieved)
        step.output = context
    await _publish_sources(retrieved)

    async with cl.Step(name="教学 Agent｜文献精读课设计") as step:
        # 调用教学 Agent 将科研证据转化为课堂活动。
        raw_lesson = teaching.analyze_literature(topic, context)
        step.output = raw_lesson
    audit = await _audit(
        "文献精读教学",
        topic,
        raw_lesson,
        "覆盖研究问题、方法判断、证据等级、局限性和讨论题",
    )
    await cl.Message(
        content=f"# 文献精读课\n{audit['final_output']}",
        author="教学 Agent",
    ).send()


async def _publish_sources(retrieved: dict) -> None:
    """展示可追溯的外部文献来源。

    Args:
        retrieved: 检索 Agent 返回的多源检索结果。
    """
    source_lines = [
        f"- [{item['source']}] {item.get('title', '')}"
        for item in retrieved["external"]
        if "error" not in item
    ]
    content = "\n".join(source_lines) if source_lines else "- 暂未检索到可展示的外部文献"
    await cl.Message(content=f"## 检索来源\n{content}", author="检索 Agent").send()
