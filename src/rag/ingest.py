"""文献入库：把 PDF/文本切块后写入 Chroma。

简化版按段落切块；生产环境可换用 langchain 的 RecursiveCharacterTextSplitter。
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from .vectorstore import add_documents


def _chunk(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += size - overlap
    return chunks


def ingest_text(text: str, source: str, title: str = "") -> int:
    """把一段文本入库，返回写入的块数。"""
    chunks = _chunk(text)
    ids, docs, metas = [], [], []
    for i, ch in enumerate(chunks):
        uid = hashlib.md5(f"{source}-{i}-{ch[:50]}".encode()).hexdigest()
        ids.append(uid)
        docs.append(ch)
        metas.append({"source": source, "title": title, "chunk": i})
    if docs:
        add_documents(docs, metas, ids)
    return len(docs)


def ingest_dir(path: str) -> int:
    """批量入库一个目录下的 .txt 文件。"""
    total = 0
    for f in Path(path).glob("*.txt"):
        total += ingest_text(f.read_text(encoding="utf-8"), source=f.name, title=f.stem)
    return total
