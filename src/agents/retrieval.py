"""检索智能体：合并 PubMed/arXiv 外部检索与本地 RAG 结果，去重整理。"""
from __future__ import annotations

from ..rag import vectorstore
from ..tools.literature import search_arxiv, search_pubmed


def retrieve(topic: str, k: int = 5) -> dict:
    """围绕 topic 做多源检索。

    Returns:
        {"external": [...], "local": [...]}  外部文献 + 院内库命中。
    """
    external: list[dict] = []
    try:
        external += search_pubmed(topic, k=k)
    except Exception as e:  # noqa: BLE001  网络/接口异常不阻断流程
        external.append({"source": "PubMed", "error": str(e)})
    try:
        external += search_arxiv(topic, k=k)
    except Exception as e:  # noqa: BLE001
        external.append({"source": "arXiv", "error": str(e)})

    try:
        local = vectorstore.query(topic, k=k)
    except Exception:  # noqa: BLE001  本地库可能尚未建立
        local = []

    return {"external": external, "local": local}


def format_context(retrieved: dict) -> str:
    """把检索结果拼成可喂给 LLM 的上下文文本。"""
    lines: list[str] = ["## 外部文献"]
    for r in retrieved["external"]:
        if "error" in r:
            continue
        lines.append(f"- [{r['source']}] {r.get('title','')}\n  {r.get('abstract','')[:300]}")
    lines.append("\n## 院内文献库")
    for r in retrieved["local"]:
        meta = r.get("meta", {})
        lines.append(f"- [{meta.get('title','本地')}] {r['text'][:300]}")
    return "\n".join(lines)
