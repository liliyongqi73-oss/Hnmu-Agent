"""外部文献检索工具：PubMed 与 arXiv。"""
from __future__ import annotations

import arxiv
from Bio import Entrez

from ..config import settings

Entrez.email = settings.pubmed_email
if settings.pubmed_api_key:
    Entrez.api_key = settings.pubmed_api_key


def search_pubmed(query: str, k: int = 5) -> list[dict]:
    """检索 PubMed，返回标题/摘要/PMID。"""
    handle = Entrez.esearch(db="pubmed", term=query, retmax=k)
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
        results.append(
            {
                "source": "PubMed",
                "pmid": str(cit["PMID"]),
                "title": str(article.get("ArticleTitle", "")),
                "abstract": abstract,
            }
        )
    return results


def search_arxiv(query: str, k: int = 5) -> list[dict]:
    """检索 arXiv，返回标题/摘要/链接。"""
    search = arxiv.Search(
        query=query, max_results=k, sort_by=arxiv.SortCriterion.Relevance
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
            }
        )
    return results
