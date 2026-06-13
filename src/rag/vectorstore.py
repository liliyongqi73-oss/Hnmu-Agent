"""Chroma 向量库封装：院内文献的存储与检索。

embedding 模型采用懒加载：首次用到时才下载/加载，失败时整个本地 RAG
优雅降级（query 返回空、add 抛出可捕获异常），不阻断外部检索与综述链路。
"""
from __future__ import annotations

import chromadb

from ..config import settings

_client = chromadb.PersistentClient(path=settings.chroma_dir)
_embed_fn = None  # 懒加载

COLLECTION = "hnmu_literature"


def _get_embed_fn():
    """懒加载 embedding 函数。失败时抛出，由调用方决定降级。"""
    global _embed_fn
    if _embed_fn is None:
        from chromadb.utils import embedding_functions

        _embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.embedding_model
        )
    return _embed_fn


def get_collection():
    return _client.get_or_create_collection(
        name=COLLECTION, embedding_function=_get_embed_fn()
    )


def add_documents(docs: list[str], metadatas: list[dict], ids: list[str]) -> None:
    """批量入库。docs 为文本块，metadatas 含来源/标题等。"""
    get_collection().add(documents=docs, metadatas=metadatas, ids=ids)


def query(text: str, k: int = 5) -> list[dict]:
    """语义检索，返回 top-k 文本块及元数据。

    embedding 模型不可用或库为空时返回空列表（优雅降级）。
    """
    try:
        res = get_collection().query(query_texts=[text], n_results=k)
    except Exception:  # noqa: BLE001  模型下载失败/库为空等
        return []
    hits: list[dict] = []
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    for doc, meta, dist in zip(docs, metas, dists):
        hits.append({"text": doc, "meta": meta, "score": 1 - dist})
    return hits
