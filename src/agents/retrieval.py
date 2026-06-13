"""检索智能体：合并 PubMed/arXiv 外部检索与本地 RAG 结果，去重整理。

支持按期刊名（PubMed）与学科分类（arXiv）限定来源，
不指定时退化为全库检索。
"""
from __future__ import annotations

from queue import Empty, Queue
from threading import Thread

from ..rag import vectorstore
from ..tools.literature import search_arxiv, search_dblp, search_pubmed

SOURCE_TIMEOUT_SECONDS = 90


def _safe_call(source: str, call, fallback):
    """限时执行单个检索来源，超时或异常时返回降级结果。

    Args:
        source: 来源展示名称。
        call: 无参数检索函数。
        fallback: 超时或失败时返回的值。

    Returns:
        来源结果，外部来源失败时附带错误说明。

    Notes:
        使用守护线程隔离不可控的网络请求与首次 embedding 下载，避免阻塞全流程。
    """
    result_queue: Queue = Queue(maxsize=1)

    def execute() -> None:
        try:
            result_queue.put(("ok", call()))
        except Exception as error:  # noqa: BLE001
            result_queue.put(("error", str(error)))

    Thread(target=execute, daemon=True).start()
    try:
        status, value = result_queue.get(timeout=SOURCE_TIMEOUT_SECONDS)
    except Empty:
        return fallback if source == "院内库" else [{"source": source, "error": "检索超时，已降级"}]
    if status == "error":
        return fallback if source == "院内库" else [{"source": source, "error": value}]
    return value


def retrieve(
    topic: str,
    k: int = 5,
    journals: list[str] | None = None,
    categories: list[str] | None = None,
    databases: list[str] | None = None,
    conferences: list[str] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict:
    """围绕 topic 做多源检索。

    Args:
        topic: 检索主题。
        k: 每个来源的返回条数上限。
        journals: 限定的 PubMed 期刊名/缩写列表，为空则不限。
        categories: 限定的 arXiv 分类代码列表，为空则不限。

    Returns:
        {"external": [...], "local": [...]}  外部文献 + 院内库命中。
    """
    selected = set(databases or ["dblp", "pubmed", "arxiv", "local"])
    external: list[dict] = []
    if "dblp" in selected or conferences:
        external += _safe_call(
            "DBLP",
            lambda: search_dblp(topic, k=k, conferences=conferences, year_from=year_from, year_to=year_to),
            [],
        )
    if "pubmed" in selected:
        external += _safe_call("PubMed", lambda: search_pubmed(topic, k=k, journals=journals), [])
    if "arxiv" in selected:
        external += _safe_call("arXiv", lambda: search_arxiv(topic, k=k, categories=categories), [])
    local = _safe_call("院内库", lambda: vectorstore.query(topic, k=k), []) if "local" in selected else []
    if year_from or year_to:
        external = [
            item
            for item in external
            if item.get("error")
            or not item.get("year")
            or (
                (not year_from or int(item["year"]) >= year_from)
                and (not year_to or int(item["year"]) <= year_to)
            )
        ]

    return {"external": external, "local": local}


def format_context(retrieved: dict) -> str:
    """把检索结果拼成可喂给 LLM 的上下文文本。"""
    lines: list[str] = ["## 外部文献"]
    for r in retrieved["external"]:
        if "error" in r:
            continue
        venue = f"《{r['venue']}》 " if r.get("venue") else ""
        lines.append(f"- [{r['source']}] {venue}{r.get('title','')}\n  {r.get('abstract','')[:300]}")
    lines.append("\n## 院内文献库")
    for r in retrieved["local"]:
        meta = r.get("meta", {})
        lines.append(f"- [{meta.get('title','本地')}] {r['text'][:300]}")
    return "\n".join(lines)
