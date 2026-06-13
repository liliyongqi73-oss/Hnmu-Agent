"""编排引擎：按 plan.py 的权威计划驱动多智能体协作。

核心是「执行 Agent 产出 → 审核 Agent 验收 → 未达标带意见返修」的循环，
最多 MAX_REVIEW_ROUNDS 轮。引擎本身不含业务流程，流程与 Agent 分工
全部来自 src/plan.py，提示词来自 workspace/skills/<id>/SKILL.md。
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Callable

from src.agents import leader, panel, retrieval
from src.llm_router import consume_model_fallback_notice, get_llm, stream_text
from src.plan import (
    AGENTS,
    MAX_REVIEW_ROUNDS,
    REVIEWER_AGENT,
    Plan,
    Step,
)
from src.skills.loader import load_skill

# 阶段事件回调：(stage, agent, status, summary) -> None。持久化阶段事件用。
EventCallback = Callable[[str, str, str, str], None]

# 流式消息回调：(message: dict) -> None。实时推送 token 与多轮过程用。
StreamCallback = Callable[[dict], None]

# 用户上传的参考资料，注入每个 agent 的用户消息；为空时不注入。
_REFERENCE: ContextVar[str] = ContextVar("reference", default="")


def _with_reference(user: str) -> str:
    """把参考资料追加到用户消息末尾。

    Args:
        user: 原始用户消息。

    Returns:
        附带参考资料的用户消息；无参考资料时原样返回。
    """
    reference = _REFERENCE.get()
    if not reference:
        return user
    return f"{user}\n\n【用户提供的参考资料，请优先参考】\n{reference}"


def _noop_stream(_message: dict) -> None:
    """默认空流式回调，未启用流式时使用。"""


@dataclass
class StepResult:
    """单个阶段执行后的可引用输出。

    Attributes:
        fields: 该阶段产出的命名值，供 $id.field 引用。
    """

    fields: dict[str, object]


def _completion_summary(summary: str) -> str:
    """合并阶段完成摘要与模型回退说明。

    Args:
        summary: 阶段完成摘要。

    Returns:
        可展示的阶段摘要。
    """
    fallback_notice = consume_model_fallback_notice()
    return f"{summary}；{fallback_notice}" if fallback_notice else summary


def _resolve(expr: object, topic: str, results: dict[str, StepResult]) -> object:
    """解析引用表达式取值。

    Args:
        expr: 引用表达式，支持 $topic 与 $step_id.field，其余按字面量处理。
        topic: 当前任务主题。
        results: 已完成阶段的输出。

    Returns:
        解析后的值。

    Raises:
        KeyError: 引用了不存在的阶段或字段。
    """
    if not isinstance(expr, str) or not expr.startswith("$"):
        return expr
    ref = expr[1:]
    if ref == "topic":
        return topic
    step_id, _, field_name = ref.partition(".")
    if step_id not in results:
        raise KeyError(f"引用了未执行的阶段：{step_id}")
    fields = results[step_id].fields
    if field_name not in fields:
        raise KeyError(f"阶段 {step_id} 无字段：{field_name}")
    return fields[field_name]


def _run_retrieval_step(
    step: Step,
    topic: str,
    emit: EventCallback,
    on_stream: StreamCallback,
    filters: dict | None = None,
) -> StepResult:
    """执行内置检索阶段。

    Args:
        step: 阶段定义。
        topic: 任务主题。
        emit: 持久化阶段事件回调。
        on_stream: 流式消息回调。
        filters: 检索过滤条件，含 journals 与 categories；为空则全库检索。

    Returns:
        含 context 与 sources 字段的阶段输出。
    """
    filters = filters or {}
    emit(step.stage, "检索 Agent", "running", "")
    on_stream({"type": "stage_start", "stage": step.stage, "agent": "检索 Agent", "attempt": 1})
    retrieved = retrieval.retrieve(
        topic,
        journals=filters.get("journals") or None,
        categories=filters.get("categories") or None,
    )
    summary = _retrieval_summary(filters)
    emit(step.stage, "检索 Agent", "completed", summary)
    on_stream(
        {
            "type": "stage_done",
            "stage": step.stage,
            "agent": "检索 Agent",
            "output": summary,
            "sources": retrieved["external"],
            "passed": True,
            "rounds": 1,
        }
    )
    return StepResult(fields={"context": retrieval.format_context(retrieved), "sources": retrieved["external"]})


def _retrieval_summary(filters: dict) -> str:
    """生成检索完成摘要，标注限定的来源。

    Args:
        filters: 检索过滤条件。

    Returns:
        阶段完成摘要。
    """
    parts: list[str] = []
    if filters.get("journals"):
        parts.append("期刊 " + "、".join(filters["journals"]))
    if filters.get("categories"):
        parts.append("arXiv 分类 " + "、".join(filters["categories"]))
    if not parts:
        return "多源证据检索完成"
    return "限定来源检索完成：" + "；".join(parts)


def _generate(
    skill_name: str,
    values: dict[str, object],
    revision_note: str,
    on_token: Callable[[str], None],
) -> str:
    """调用执行 Agent 的技能流式生成产出，可携带上一轮审核意见返修。

    Args:
        skill_name: 执行 Agent 所用技能标识。
        values: 技能用户模板的占位符取值。
        revision_note: 上一轮审核意见；首轮为空。
        on_token: 增量文本回调，用于实时推送生成过程。

    Returns:
        执行 Agent 的产出正文。
    """
    skill = load_skill(skill_name)
    llm = get_llm(task=skill.task)
    user = skill.render_user(values)
    if revision_note:
        # 把审核意见追加到用户消息，让执行 Agent 在原方向上定向修订而非从零重写。
        user = (
            f"{user}\n\n"
            f"【上一轮审核意见，请据此修订并补齐缺口】\n{revision_note}"
        )
    return stream_text(llm, [("system", skill.system_prompt), ("user", _with_reference(user))], on_token)


def _run_agent_step(
    step: Step,
    topic: str,
    results: dict[str, StepResult],
    emit: EventCallback,
    on_stream: StreamCallback,
) -> StepResult:
    """执行 Agent 阶段：生成→审核→未达标返修，最多 MAX_REVIEW_ROUNDS 轮。

    Args:
        step: 阶段定义。
        topic: 任务主题。
        results: 已完成阶段输出。
        emit: 持久化阶段事件回调。
        on_stream: 流式消息回调，逐 token 与逐轮推送过程。

    Returns:
        含 output/score/report/passed/rounds 字段的阶段输出。

    Notes:
        达标即提前结束循环；达到轮数上限仍未达标时，采用最后一轮交付并标注未达标。
        每轮推送 stage_start → token* → review；阶段定稿推送 stage_done。
    """
    role = AGENTS[step.agent]
    values = {key: _resolve(expr, topic, results) for key, expr in step.inputs.items()}

    def push_tokens(stage: str, agent: str, attempt: int):
        """生成绑定到指定阶段与轮次的 token 推送函数。"""
        return lambda piece: on_stream(
            {"type": "token", "stage": stage, "agent": agent, "attempt": attempt, "text": piece}
        )

    if not step.review:
        emit(step.stage, role.name, "running", "")
        on_stream({"type": "stage_start", "stage": step.stage, "agent": role.name, "attempt": 1})
        output = _generate(role.skill, values, "", push_tokens(step.stage, role.name, 1))
        emit(step.stage, role.name, "completed", "")
        on_stream({"type": "stage_done", "stage": step.stage, "agent": role.name, "output": output, "passed": True, "rounds": 1})
        return StepResult(fields={"output": output, "passed": True, "rounds": 1})

    revision_note = ""
    audit: dict = {}
    for attempt in range(1, MAX_REVIEW_ROUNDS + 1):
        running_summary = "" if attempt == 1 else f"第 {attempt} 轮返修"
        emit(step.stage, role.name, "running", running_summary)
        on_stream({"type": "stage_start", "stage": step.stage, "agent": role.name, "attempt": attempt})
        raw_output = _generate(role.skill, values, revision_note, push_tokens(step.stage, role.name, attempt))
        audit = leader.review_task(step.stage, topic, raw_output, role.criteria)
        # 推送本轮审核结果：评分、是否达标、审核意见与原始产出。
        on_stream(
            {
                "type": "review",
                "stage": step.stage,
                "agent": REVIEWER_AGENT,
                "attempt": attempt,
                "score": audit["score"],
                "passed": audit["passed"],
                "feedback": _audit_feedback(audit["report"]),
                "draft": raw_output,
            }
        )
        if audit["passed"]:
            emit(
                step.stage,
                REVIEWER_AGENT,
                "completed",
                _completion_summary(f"质量评分 {audit['score']}/100，第 {attempt} 轮达标"),
            )
            break
        # 未达标：保留审核意见喂给下一轮，并继续显示阶段运行中。
        revision_note = _audit_feedback(audit["report"])
        emit(
            step.stage,
            REVIEWER_AGENT,
            "running",
            _completion_summary(f"第 {attempt} 轮评分 {audit['score']}/100，未达标，继续返修"),
        )
    else:
        # 循环正常结束（未 break）意味着达到轮数上限仍未达标。
        emit(
            step.stage,
            REVIEWER_AGENT,
            "completed",
            _completion_summary(
                f"质量评分 {audit['score']}/100，达 {MAX_REVIEW_ROUNDS} 轮上限仍未达标，采用最后一轮交付"
            ),
        )

    on_stream(
        {
            "type": "stage_done",
            "stage": step.stage,
            "agent": role.name,
            "output": audit["final_output"],
            "score": audit["score"],
            "passed": audit["passed"],
            "rounds": attempt,
        }
    )
    return StepResult(
        fields={
            "output": audit["final_output"],
            "score": audit["score"],
            "report": audit["report"],
            "passed": audit["passed"],
            "rounds": attempt,
        }
    )


def _stream_skill(
    skill_name: str,
    values: dict[str, object],
    on_token: Callable[[str], None],
) -> str:
    """流式调用任意技能生成产出。

    Args:
        skill_name: 技能标识。
        values: 用户模板占位符取值。
        on_token: 增量文本回调。

    Returns:
        技能产出正文。
    """
    skill = load_skill(skill_name)
    llm = get_llm(task=skill.task)
    return stream_text(llm, [("system", skill.system_prompt), ("user", _with_reference(skill.render_user(values)))], on_token)


def _run_panel_step(
    step: Step,
    topic: str,
    results: dict[str, StepResult],
    emit: EventCallback,
    on_stream: StreamCallback,
) -> StepResult:
    """执行多视角同行评审阶段：各审稿人独立评审 → 主编汇总裁决。

    Args:
        step: 阶段定义；inputs 需含 draft（待评审稿件）；slim 经 inputs 的 _slim 标记控制。
        topic: 任务主题。
        results: 已完成阶段输出。
        emit: 持久化阶段事件回调。
        on_stream: 流式消息回调。

    Returns:
        含 output（主编报告）/score/decision/passed/rounds 字段的阶段输出。

    Notes:
        每位审稿人与主编都流式推送 token，前端可看到各视角产出；
        主编评分映射 ARS 录用决策（≥80 接受、65-79 小修、50-64 大修、<50 退稿）。
    """
    values = {key: _resolve(expr, topic, results) for key, expr in step.inputs.items() if not key.startswith("_")}
    draft = str(values.get("draft", ""))
    slim = bool(step.inputs.get("_slim"))
    panel_roles = panel.get_panel(slim=slim)

    def push(agent: str, piece: str):
        on_stream({"type": "token", "stage": step.stage, "agent": agent, "attempt": 1, "text": piece})

    # 各审稿人独立评审，逐位流式产出。
    reviews: list[str] = []
    for reviewer in panel_roles:
        emit(step.stage, reviewer.name, "running", "")
        on_stream({"type": "stage_start", "stage": step.stage, "agent": reviewer.name, "attempt": 1})
        opinion = _stream_skill(
            "reviewer",
            {"topic": topic, "role": reviewer.role, "draft": draft},
            lambda piece, name=reviewer.name: push(name, piece),
        )
        reviews.append(f"# {reviewer.name}\n{opinion}")
        emit(step.stage, reviewer.name, "completed", f"{reviewer.name}评审完成")
        on_stream({"type": "stage_done", "stage": step.stage, "agent": reviewer.name, "output": opinion, "passed": True, "rounds": 1})

    # 主编汇总各审稿人意见并裁决。
    emit(step.stage, "主编 Agent", "running", "")
    on_stream({"type": "stage_start", "stage": step.stage, "agent": "主编 Agent", "attempt": 1})
    editor_report = _stream_skill(
        "editor",
        {"topic": topic, "reviews": "\n\n".join(reviews)},
        lambda piece: push("主编 Agent", piece),
    )
    verdict = panel.parse_editor_report(editor_report, editor_report)
    summary = _completion_summary(
        f"综合评分 {verdict['score']}/100，决策：{verdict['decision'] or '未明确'}"
    )
    emit(step.stage, "主编 Agent", "completed", summary)
    on_stream(
        {
            "type": "stage_done",
            "stage": step.stage,
            "agent": "主编 Agent",
            "output": verdict["final_output"],
            "score": verdict["score"],
            "passed": verdict["passed"],
            "rounds": 1,
        }
    )
    return StepResult(
        fields={
            "output": verdict["final_output"],
            "score": verdict["score"],
            "decision": verdict["decision"],
            "passed": verdict["passed"],
            "rounds": 1,
        }
    )


def _audit_feedback(report: str) -> str:
    """从审核全文中抽取可供返修的审核意见。

    Args:
        report: 审核 Agent 返回的结构化审核全文。

    Returns:
        审核意见段落；无法切分时返回审核全文。
    """
    marker = "【审核意见】"
    end_marker = "【最终交付】"
    if marker not in report:
        return report.strip()
    tail = report.split(marker, 1)[1]
    feedback = tail.split(end_marker, 1)[0] if end_marker in tail else tail
    return feedback.strip()


def run_plan(
    plan: Plan,
    topic: str,
    emit: EventCallback,
    retrieval_filters: dict | None = None,
    on_stream: StreamCallback | None = None,
    reference: str = "",
) -> dict:
    """按计划顺序执行各阶段并组装结果。

    Args:
        plan: 执行计划。
        topic: 任务主题。
        emit: 持久化阶段事件回调。
        retrieval_filters: 检索过滤条件，含 journals 与 categories；为空则全库检索。
        on_stream: 流式消息回调；为空则不推送实时过程。
        reference: 用户上传的参考资料，注入每个 agent；为空时不注入。

    Returns:
        按计划 result 映射组装的最终交付。

    Raises:
        ValueError: 计划包含未知阶段类型。
    """
    stream = on_stream or _noop_stream
    token = _REFERENCE.set(reference)
    try:
        results: dict[str, StepResult] = {}
        for step in plan.steps:
            if step.kind == "retrieval":
                results[step.id] = _run_retrieval_step(step, topic, emit, stream, retrieval_filters)
            elif step.kind == "agent":
                results[step.id] = _run_agent_step(step, topic, results, emit, stream)
            elif step.kind == "panel":
                results[step.id] = _run_panel_step(step, topic, results, emit, stream)
            else:
                raise ValueError(f"未知阶段类型：{step.kind}")
        return {key: _resolve(expr, topic, results) for key, expr in plan.result.items()}
    finally:
        _REFERENCE.reset(token)


def run_step(
    step: Step,
    topic: str,
    stored_results: dict[str, dict],
    emit: EventCallback,
    retrieval_filters: dict | None = None,
    on_stream: StreamCallback | None = None,
    reference: str = "",
) -> dict:
    """执行单个流程阶段并返回可持久化结果。

    Args:
        step: 当前阶段定义。
        topic: 研究主题。
        stored_results: 已完成阶段的持久化结果。
        emit: 持久化阶段事件回调。
        retrieval_filters: 检索过滤条件。
        on_stream: 实时消息回调。
        reference: 用户参考资料。

    Returns:
        当前阶段可持久化的字段字典。

    Notes:
        逐阶段执行是人工确认点、暂停续跑和服务重启恢复的基础。
    """
    stream = on_stream or _noop_stream
    results = {
        step_id: StepResult(fields=fields)
        for step_id, fields in stored_results.items()
    }
    token = _REFERENCE.set(reference)
    try:
        if step.kind == "retrieval":
            result = _run_retrieval_step(step, topic, emit, stream, retrieval_filters)
        elif step.kind == "agent":
            result = _run_agent_step(step, topic, results, emit, stream)
        elif step.kind == "panel":
            result = _run_panel_step(step, topic, results, emit, stream)
        else:
            raise ValueError(f"未知阶段类型：{step.kind}")
        return result.fields
    finally:
        _REFERENCE.reset(token)


def build_plan_result(plan: Plan, topic: str, stored_results: dict[str, dict]) -> dict:
    """根据持久化阶段结果组装最终交付。

    Args:
        plan: 当前执行计划。
        topic: 研究主题。
        stored_results: 已完成阶段结果。

    Returns:
        计划定义的最终结果。
    """
    results = {
        step_id: StepResult(fields=fields)
        for step_id, fields in stored_results.items()
    }
    return {
        key: _resolve(expr, topic, results)
        for key, expr in plan.result.items()
        if expr[1:].partition(".")[0] in results
    }
