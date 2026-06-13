"""外部文献检索工具：PubMed 与 arXiv，支持按期刊名 / 学科分类过滤。"""
from __future__ import annotations

import arxiv
from Bio import Entrez

from ..config import settings

Entrez.email = settings.pubmed_email
if settings.pubmed_api_key:
    Entrez.api_key = settings.pubmed_api_key


def _build_pubmed_term(query: str, journals: list[str] | None) -> str:
    """构造 PubMed 检索式，可选按期刊名限定。

    Args:
        query: 主题检索词。
        journals: 期刊名/缩写列表，用 [TA] 字段以 OR 组合，与主题 AND 关联。

    Returns:
        PubMed esearch 使用的检索式。
    """
    if not journals:
        return query
    journal_filter = " OR ".join(f'"{name}"[TA]' for name in journals if name.strip())
    if not journal_filter:
        return query
    return f"({query}) AND ({journal_filter})"


def _build_arxiv_query(query: str, categories: list[str] | None) -> str:
    """构造 arXiv 检索式，可选按学科分类限定。

    Args:
        query: 主题检索词。
        categories: arXiv 分类代码列表，用 cat: 前缀以 OR 组合，与主题 AND 关联。

    Returns:
        arXiv Search 使用的检索式。
    """
    if not categories:
        return query
    cat_filter = " OR ".join(f"cat:{code.strip()}" for code in categories if code.strip())
    if not cat_filter:
        return query
    return f"({query}) AND ({cat_filter})"


def search_pubmed(query: str, k: int = 5, journals: list[str] | None = None) -> list[dict]:
    """检索 PubMed，返回标题/摘要/PMID/期刊。

    Args:
        query: 主题检索词。
        k: 返回条数上限。
        journals: 限定的期刊名/缩写列表，为空则不限期刊。

    Returns:
        命中文献列表。
    """
    term = _build_pubmed_term(query, journals)
    handle = Entrez.esearch(db="pubmed", term=term, retmax=k)
    ids = Entrez.read(handle)["IdList"]
    handle.close()
    if not ids:
        return []

    handle = Entrez.efetch(db="pubmed", id=ids, rettype="abstract", retmode="xml")
    records = Entrez.read(handle)
    handle.close()

    results: list[dict] = []
    for art in records.get("PubmedArticle", []):
        cit = art["MedlineCitation"]
        article = cit["Article"]
        abstract = ""
        if "Abstract" in article:
            abstract = " ".join(str(t) for t in article["Abstract"]["AbstractText"])
        journal = str(article.get("Journal", {}).get("Title", "")) if "Journal" in article else ""
        results.append(
            {
                "source": "PubMed",
                "pmid": str(cit["PMID"]),
                "title": str(article.get("ArticleTitle", "")),
                "abstract": abstract,
                "venue": journal,
            }
        )
    return results


def search_arxiv(query: str, k: int = 5, categories: list[str] | None = None) -> list[dict]:
    """检索 arXiv，返回标题/摘要/链接/分类。

    Args:
        query: 主题检索词。
        k: 返回条数上限。
        categories: 限定的 arXiv 分类代码列表，为空则不限分类。

    Returns:
        命中文献列表。
    """
    arxiv_query = _build_arxiv_query(query, categories)
    search = arxiv.Search(
        query=arxiv_query, max_results=k, sort_by=arxiv.SortCriterion.Relevance
    )
    results: list[dict] = []
    for r in arxiv.Client().results(search):
        results.append(
            {
                "source": "arXiv",
                "id": r.get_short_id(),
                "title": r.title,
                "abstract": r.summary,
                "url": r.entry_id,
                "venue": r.primary_category,
            }
        )
    return results
