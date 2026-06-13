"""多智能体权威计划：定义每个 Agent 的职责与各任务模式的执行流程。

这是整个多智能体协作的单一事实来源（single source of truth）：
- AGENTS 规定每个执行 Agent 的角色、所用技能与默认验收标准；
- PLANS 规定 research/teaching/literature 三种模式的阶段顺序与阶段间的输入引用；
- MAX_REVIEW_ROUNDS 规定「执行→审核→不达标返修」的最多轮数。

调整 Agent 分工、阶段顺序或验收标准只改本文件即可，引擎据此驱动；
提示词正文仍外置在 workspace/skills/<id>/SKILL.md，与角色定义解耦。
"""
from __future__ import annotations

from dataclasses import dataclass, field

# 执行 Agent 不达标时「返修→再审核」的最多轮数。达到上限后采用最后一轮交付并标注未达标。
MAX_REVIEW_ROUNDS = 20

# 审核 Agent 的技能标识，负责对所有执行 Agent 的产出验收并在未达标时给出修订要求。
REVIEWER_SKILL = "leader"
REVIEWER_AGENT = "领导 Agent"


@dataclass(frozen=True)
class AgentRole:
    """一个执行 Agent 的角色定义。

    Attributes:
        id: Agent 标识。
        name: 展示用名称，写入任务事件。
        skill: 该 Agent 所用技能（对应 workspace/skills/<skill>）。
        criteria: 交给审核 Agent 的默认验收标准。
    """

    id: str
    name: str
    skill: str
    criteria: str


@dataclass(frozen=True)
class Step:
    """流程中的一个阶段。

    Attributes:
        id: 阶段标识，供后续阶段以 $id.field 引用其输出。
        stage: 展示用阶段名称，写入任务事件。
        kind: 阶段类型，retrieval（内置检索）或 agent（执行 Agent + 审核）。
        agent: kind 为 agent 时引用的 AGENTS 键。
        inputs: 技能用户模板占位符到引用表达式（$topic / $step.field）的映射。
        review: 是否需要审核 Agent 验收与返修循环。
    """

    id: str
    stage: str
    kind: str
    agent: str = ""
    inputs: dict[str, str] = field(default_factory=dict)
    review: bool = True


@dataclass(frozen=True)
class Plan:
    """一种任务模式的完整执行计划。

    Attributes:
        mode: 任务模式，与 TaskCreateRequest.mode 对应。
        label: 计划展示名称。
        steps: 有序阶段列表。
        result: 结果字段名到引用表达式的映射。
    """

    mode: str
    label: str
    steps: list[Step]
    result: dict[str, str]


# 执行 Agent 角色表：角色、技能与默认验收标准集中在此维护。
AGENTS: dict[str, AgentRole] = {
    "review": AgentRole(
        id="review",
        name="综述 Agent",
        skill="review",
        criteria="论断可追溯，明确研究空白",
    ),
    "method": AgentRole(
        id="method",
        name="方法 Agent",
        skill="method",
        criteria="回应研究空白且可行",
    ),
    "experiment": AgentRole(
        id="experiment",
        name="实验 Agent",
        skill="experiment",
        criteria="统计与伦理要求完整",
    ),
    "teaching": AgentRole(
        id="teaching",
        name="教学 Agent",
        skill="teaching",
        criteria="目标可测量、活动与评价一致",
    ),
    "teaching_literature": AgentRole(
        id="teaching_literature",
        name="教学 Agent",
        skill="teaching-literature",
        criteria="覆盖方法判断、证据等级与讨论题",
    ),
    "paper_draft": AgentRole(
        id="paper_draft",
        name="撰写 Agent",
        skill="paper-draft",
        criteria="IMRaD 结构完整、论证连贯",
    ),
    "integrity": AgentRole(
        id="integrity",
        name="诚信核查 Agent",
        skill="integrity",
        criteria="引用存在性与数据一致性核查到位",
    ),
    "revision": AgentRole(
        id="revision",
        name="修订 Agent",
        skill="revision",
        criteria="逐条回应审稿意见",
    ),
    "finalize": AgentRole(
        id="finalize",
        name="定稿 Agent",
        skill="finalize",
        criteria="格式规范、双语摘要齐备",
    ),
    "process": AgentRole(
        id="process",
        name="过程记录 Agent",
        skill="process-record",
        criteria="六维度协作质量评估完整",
    ),
}


# 三种任务模式的执行计划。
PLANS: dict[str, Plan] = {
    "research": Plan(
        mode="research",
        label="科研课题协作",
        steps=[
            Step(id="retrieve", stage="文献检索", kind="retrieval", review=False),
            Step(
                id="review",
                stage="相关工作综述",
                kind="agent",
                agent="review",
                inputs={"topic": "$topic", "context": "$retrieve.context"},
            ),
            Step(
                id="method",
                stage="方法与创新点",
                kind="agent",
                agent="method",
                inputs={"topic": "$topic", "review": "$review.output"},
            ),
            Step(
                id="experiment",
                stage="实验设计",
                kind="agent",
                agent="experiment",
                inputs={"topic": "$topic", "method": "$method.output"},
            ),
        ],
        result={
            "review": "$review.output",
            "method": "$method.output",
            "experiment": "$experiment.output",
            "sources": "$retrieve.sources",
        },
    ),
    "teaching": Plan(
        mode="teaching",
        label="医学教学设计",
        steps=[
            Step(
                id="teaching",
                stage="教学设计",
                kind="agent",
                agent="teaching",
                inputs={"topic": "$topic"},
            ),
        ],
        result={
            "teaching": "$teaching.output",
            "audit": "$teaching.report",
        },
    ),
    "literature": Plan(
        mode="literature",
        label="文献精读课设计",
        steps=[
            Step(id="retrieve", stage="精读材料检索", kind="retrieval", review=False),
            Step(
                id="lesson",
                stage="文献精读课设计",
                kind="agent",
                agent="teaching_literature",
                inputs={"topic": "$topic", "context": "$retrieve.context"},
            ),
        ],
        result={
            "lesson": "$lesson.output",
            "sources": "$retrieve.sources",
        },
    ),
    "paper": Plan(
        mode="paper",
        label="完整论文 pipeline",
        steps=[
            # Stage 1 研究：检索 → 综述 → 方法 → 实验。
            Step(id="retrieve", stage="文献检索", kind="retrieval", review=False),
            Step(
                id="review",
                stage="相关工作综述",
                kind="agent",
                agent="review",
                inputs={"topic": "$topic", "context": "$retrieve.context"},
            ),
            Step(
                id="method",
                stage="方法与创新点",
                kind="agent",
                agent="method",
                inputs={"topic": "$topic", "review": "$review.output"},
            ),
            Step(
                id="experiment",
                stage="实验设计",
                kind="agent",
                agent="experiment",
                inputs={"topic": "$topic", "method": "$method.output"},
            ),
            # Stage 2 撰写：整合三件套成论文初稿。
            Step(
                id="draft",
                stage="论文初稿",
                kind="agent",
                agent="paper_draft",
                inputs={
                    "topic": "$topic",
                    "review": "$review.output",
                    "method": "$method.output",
                    "experiment": "$experiment.output",
                },
            ),
            # Stage 2.5 学术诚信闸门（不进返修环，产出核查报告）。
            Step(
                id="integrity1",
                stage="学术诚信核查（初稿）",
                kind="agent",
                agent="integrity",
                inputs={"topic": "$topic", "draft": "$draft.output", "sources": "$retrieve.sources"},
                review=False,
            ),
            # Stage 3 多视角同行评审：主编 + 方法/创新/表达 + 魔鬼代言人。
            Step(
                id="peer_review",
                stage="同行评审（第一轮）",
                kind="panel",
                inputs={"draft": "$draft.output"},
            ),
            # Stage 4 修订：按评审意见定向修订。
            Step(
                id="revision",
                stage="论文修订",
                kind="agent",
                agent="revision",
                inputs={"topic": "$topic", "draft": "$draft.output", "review": "$peer_review.output"},
            ),
            # Stage 3' 精简再审：方法学审稿人 + 魔鬼代言人验收修订。
            Step(
                id="peer_review2",
                stage="同行再审",
                kind="panel",
                inputs={"draft": "$revision.output", "_slim": "1"},
            ),
            # Stage 4' 最后一次再修订；仅在再审判定大修时执行，其他分支由状态机跳过。
            Step(
                id="revision2",
                stage="论文再修订",
                kind="agent",
                agent="revision",
                inputs={"topic": "$topic", "draft": "$revision.output", "review": "$peer_review2.output"},
            ),
            # Stage 4.5 最终学术诚信闸门。
            Step(
                id="integrity2",
                stage="学术诚信核查（终稿）",
                kind="agent",
                agent="integrity",
                inputs={"topic": "$topic", "draft": "$revision2.output", "sources": "$retrieve.sources"},
                review=False,
            ),
            # Stage 5 定稿：格式规范化 + 双语摘要。
            Step(
                id="finalize",
                stage="定稿",
                kind="agent",
                agent="finalize",
                inputs={"topic": "$topic", "draft": "$revision2.output", "sources": "$retrieve.sources"},
            ),
            # Stage 6 过程记录与协作质量评估。
            Step(
                id="process",
                stage="过程记录与协作评估",
                kind="agent",
                agent="process",
                inputs={
                    "topic": "$topic",
                    "final": "$finalize.output",
                    "integrity": "$integrity2.output",
                    "review": "$peer_review2.output",
                    "decisions": "$pipeline.decisions",
                    "passport": "$pipeline.passport",
                },
                review=False,
            ),
        ],
        result={
            "final_paper": "$finalize.output",
            "integrity_initial": "$integrity1.output",
            "peer_review": "$peer_review.output",
            "revision": "$revision2.output",
            "re_review": "$peer_review2.output",
            "integrity_final": "$integrity2.output",
            "process_record": "$process.output",
            "sources": "$retrieve.sources",
        },
    ),
}


def get_plan(mode: str) -> Plan:
    """按任务模式取执行计划。

    Args:
        mode: 任务模式。

    Returns:
        对应的执行计划；未知模式回退到 research。
    """
    return PLANS.get(mode, PLANS["research"])


# 自选模式下，前序产出会喂给后续 agent 的这些占位符（各技能模板取所需的子集）。
_CHAIN_PLACEHOLDERS = ("context", "review", "method", "experiment", "draft", "final")


def build_custom_plan(agent_ids: list[str], with_retrieval: bool = True) -> Plan:
    """按用户勾选的 agent 顺序拼出自选执行计划。

    Args:
        agent_ids: 勾选的 agent id 列表，按顺序执行。
        with_retrieval: 是否在最前插入文献检索阶段。

    Returns:
        自选执行计划；未知 agent id 被忽略。

    Notes:
        每个 agent 接收主题、检索上下文与前序 agent 产出（映射到多个常用占位符，
        技能模板各取所需）。peer_review 勾选时编排为完整评审团 panel。
    """
    valid = [aid for aid in agent_ids if aid in AGENTS or aid == "peer_review"]
    steps: list[Step] = []
    result: dict[str, str] = {}
    prev_output = "$topic"
    retrieval_ctx = "$topic"

    if with_retrieval:
        steps.append(Step(id="retrieve", stage="文献检索", kind="retrieval", review=False))
        retrieval_ctx = "$retrieve.context"
        result["sources"] = "$retrieve.sources"

    for index, aid in enumerate(valid):
        step_id = f"step{index}"
        if aid == "peer_review":
            steps.append(
                Step(id=step_id, stage="同行评审", kind="panel", inputs={"draft": prev_output})
            )
        else:
            role = AGENTS[aid]
            # 把检索上下文与前序产出同时喂给常用占位符，技能模板按需取用。
            inputs = {"topic": "$topic", "sources": result.get("sources", "$topic")}
            for placeholder in _CHAIN_PLACEHOLDERS:
                inputs[placeholder] = retrieval_ctx if placeholder == "context" else prev_output
            steps.append(
                Step(id=step_id, stage=role.name, kind="agent", agent=aid, inputs=inputs)
            )
        prev_output = f"${step_id}.output"
        result[aid if aid not in result else f"{aid}_{index}"] = f"${step_id}.output"

    if not steps or all(s.kind == "retrieval" for s in steps):
        # 没有有效 agent 时回退到综述，避免空计划。
        steps.append(
            Step(
                id="step0",
                stage="相关工作综述",
                kind="agent",
                agent="review",
                inputs={"topic": "$topic", "context": retrieval_ctx},
            )
        )
        result["review"] = "$step0.output"

    return Plan(mode="custom", label="自选 Agent 协作", steps=steps, result=result)
