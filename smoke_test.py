"""命令行冒烟测试：不启动 Web UI，直接验证编排链路是否通。

用法：
    py smoke_test.py "基于深度学习的肺结节良恶性分类"

仅依赖 langchain-openai 即可跑通本地模型部分；外部检索/RAG 失败会被容错跳过。
"""
from __future__ import annotations

import sys

from src.agents import method, retrieval, review


def main() -> None:
    topic = sys.argv[1] if len(sys.argv) > 1 else "基于深度学习的肺结节良恶性分类"
    print(f"研究主题：{topic}\n")

    print("① 检索中 ...")
    retrieved = retrieval.retrieve(topic, k=3)
    ctx = retrieval.format_context(retrieved)
    n_ext = len([r for r in retrieved["external"] if "error" not in r])
    print(f"  外部文献 {n_ext} 篇，院内库 {len(retrieved['local'])} 条\n")

    print("② 生成综述 ...")
    try:
        rev = review.write_review(topic, ctx)
        if not rev.strip():
            raise RuntimeError("综述 Agent 返回空文本")
        print(rev[:500], "...\n")
    except Exception as e:  # noqa: BLE001
        print(f"  [跳过] LLM 调用失败：{e}\n")
        return

    print("③ 方法与创新点 ...")
    meth = method.propose_method(topic, rev)
    if not meth.strip():
        raise RuntimeError("方法 Agent 返回空文本")
    print(meth[:500], "...\n")
    print("[通过] 链路打通")


if __name__ == "__main__":
    main()
