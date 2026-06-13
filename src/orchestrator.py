"""LangGraph 多智能体编排。

状态流：检索 → 综述 → 方法 → 实验 → 写作 → 领导审核。
每个节点产出写入共享状态，最终汇总为论文素材。
"""
from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .agents import experiment, leader, method, retrieval, review, writing


class ResearchState(TypedDict, total=False):
    topic: str            # 研究主题（输入）
    retrieved: dict       # 检索结果
    context: str          # 拼接后的检索上下文
    review: str           # 相关工作综述
    method: str           # 方法/创新点
    experiment: str       # 实验设计
    sections: dict        # 各章节成稿
    audits: dict          # 领导 Agent 对各阶段的审核报告


def _audit_output(task_name: str, state: ResearchState, output: str, criteria: str) -> tuple[str, dict]:
    """调用领导 Agent 验收阶段产出。

    Args:
        task_name: 被审核的任务名称。
        state: 当前共享状态。
        output: 执行 Agent 原始产出。
        criteria: 补充验收标准。

    Returns:
        最终交付与审核结果。
    """
    audit = leader.review_task(task_name, state["topic"], output, criteria)
    return audit["final_output"], audit


def _retrieve_node(state: ResearchState) -> ResearchState:
    r = retrieval.retrieve(state["topic"])
    context = retrieval.format_context(r)
    _, audit = _audit_output("文献检索", state, context, "来源有效、主题相关、不得把检索失败当作证据")
    return {"retrieved": r, "context": context, "audits": {"retrieval": audit}}


def _review_node(state: ResearchState) -> ResearchState:
    output = review.write_review(state["topic"], state["context"])
    final_output, audit = _audit_output("相关工作综述", state, output, "论断可追溯，明确研究空白")
    return {"review": final_output, "audits": {**state.get("audits", {}), "review": audit}}


def _method_node(state: ResearchState) -> ResearchState:
    output = method.propose_method(state["topic"], state["review"])
    final_output, audit = _audit_output("方法与创新点", state, output, "创新真实、可行且回应研究空白")
    return {"method": final_output, "audits": {**state.get("audits", {}), "method": audit}}


def _experiment_node(state: ResearchState) -> ResearchState:
    output = experiment.design_experiment(state["topic"], state["method"])
    final_output, audit = _audit_output("实验设计", state, output, "设计可复现，统计与伦理要求完整")
    return {"experiment": final_output, "audits": {**state.get("audits", {}), "experiment": audit}}


def _writing_node(state: ResearchState) -> ResearchState:
    materials = {
        "topic": state["topic"],
        "review": state.get("review", ""),
        "method": state.get("method", ""),
        "experiment": state.get("experiment", ""),
    }
    sections: dict[str, str] = {}
    audits = {**state.get("audits", {})}
    for name in ("摘要", "引言", "相关工作", "方法", "实验", "结论"):
        output = writing.write_section(name, materials)
        final_output, audit = _audit_output(f"论文{name}", state, output, "学术规范、逻辑一致、不捏造证据")
        sections[name] = final_output
        audits[f"writing_{name}"] = audit
    return {"sections": sections, "audits": audits}


def build_graph():
    g = StateGraph(ResearchState)
    g.add_node("retrieve", _retrieve_node)
    g.add_node("review", _review_node)
    g.add_node("method", _method_node)
    g.add_node("experiment", _experiment_node)
    g.add_node("writing", _writing_node)

    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "review")
    g.add_edge("review", "method")
    g.add_edge("method", "experiment")
    g.add_edge("experiment", "writing")
    g.add_edge("writing", END)
    return g.compile()


GRAPH = build_graph()


def run(topic: str) -> ResearchState:
    """同步跑完整流程，返回最终状态。"""
    return GRAPH.invoke({"topic": topic})
