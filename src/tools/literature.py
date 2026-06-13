"""外部文献检索工具：DBLP、PubMed 与 arXiv。"""
from __future__ import annotations

import time
import re
from xml.etree import ElementTree

import arxiv
import httpx

from ..config import settings

HTTP_TIMEOUT_SECONDS = 15.0
DBLP_API_URL = "https://dblp.org/search/publ/api"
DBLP_MIRROR_API_URL = "https://dblp.uni-trier.de/search/publ/api"
PUBMED_API_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# 常见中文研究主题到国际数据库检索词的规范化映射。
QUERY_TRANSLATIONS: dict[str, str] = {
    "联邦学习": "federated learning",
    "机器学习": "machine learning",
    "深度学习": "deep learning",
    "人工智能": "artificial intelligence",
    "大语言模型": "large language model",
    "计算机视觉": "computer vision",
    "医学影像": "medical imaging",
    "数据安全": "data security",
    "隐私保护": "privacy preserving",
}


def normalize_search_query(query: str) -> str:
    """把常见中文学术主题规范化为数据库可识别的英文检索词。"""
    normalized = query.strip()
    for chinese, english in QUERY_TRANSLATIONS.items():
        normalized = normalized.replace(chinese, f" {english} ")
    # 已命中英文映射时移除数据库无法理解的剩余中文说明与年份口语。
    if re.search(r"[A-Za-z]", normalized):
        normalized = re.sub(r"[\u4e00-\u9fff]+", " ", normalized)
        normalized = re.sub(r"\b(?:19|20)\d{2}\b", " ", normalized)
    normalized = re.sub(r"[\s,，;；]+", " ", normalized).strip()
    return normalized


def _is_relevant_title(title: str, query: str) -> bool:
    """检查 DBLP 标题是否至少包含一个非泛化主题词。"""
    stop_words = {
        "artificial", "data", "deep", "learning", "machine", "model", "models",
        "network", "networks", "security", "study", "system", "systems",
    }
    terms = [
        term.casefold()
        for term in re.findall(r"[A-Za-z][A-Za-z0-9-]+", normalize_search_query(query))
        if term.casefold() not in stop_words
    ]
    if not terms:
        return True
    folded_title = title.casefold()
    return any(term in folded_title for term in terms)


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


def search_pubmed(
    query: str,
    k: int = 5,
    journals: list[str] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict]:
    """检索 PubMed，返回标题/摘要/PMID/期刊。

    Args:
        query: 主题检索词。
        k: 返回条数上限。
        journals: 限定的期刊名/缩写列表，为空则不限期刊。

    Returns:
        命中文献列表。
    """
    term = _build_pubmed_term(normalize_search_query(query), journals)
    if year_from or year_to:
        term = f"({term}) AND ({year_from or 1900}:{year_to or 2100}[dp])"
    common = {"tool": "hnmu-agent", "email": settings.pubmed_email}
    if settings.pubmed_api_key:
        common["api_key"] = settings.pubmed_api_key
    with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS, follow_redirects=True) as client:
        search_response = client.get(
            f"{PUBMED_API_URL}/esearch.fcgi",
            params={**common, "db": "pubmed", "term": term, "retmax": k, "retmode": "json"},
        )
        search_response.raise_for_status()
        search_result = search_response.json()["esearchresult"]
        ids = search_result["idlist"]
        total_hits = int(search_result.get("count", 0))
        if not ids:
            return []
        fetch_response = client.get(
            f"{PUBMED_API_URL}/efetch.fcgi",
            params={**common, "db": "pubmed", "id": ",".join(ids), "rettype": "abstract", "retmode": "xml"},
        )
        fetch_response.raise_for_status()
    root = ElementTree.fromstring(fetch_response.content)
    if not ids:
        return []

    results: list[dict] = []
    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//MedlineCitation/PMID", default="")
        title = "".join(article.find(".//ArticleTitle").itertext()) if article.find(".//ArticleTitle") is not None else ""
        abstract = " ".join("".join(node.itertext()) for node in article.findall(".//Abstract/AbstractText"))
        journal = article.findtext(".//Journal/Title", default="")
        year = article.findtext(".//PubDate/Year", default="")
        results.append(
            {
                "source": "PubMed",
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "venue": journal,
                "year": year,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "total_hits": total_hits,
            }
        )
    return results


def search_dblp(
    query: str,
    k: int = 5,
    conferences: list[str] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict]:
    """检索 DBLP，并按会议及年份过滤。

    Args:
        query: 主题检索词。
        k: 每个会议或全库返回条数上限。
        conferences: DBLP 标准会议缩写。
        year_from: 起始年份。
        year_to: 结束年份。

    Returns:
        DBLP 论文列表。
    """
    venue_queries = conferences or [""]
    results: list[dict] = []
    seen: set[str] = set()
    for venue in venue_queries:
        normalized_query = normalize_search_query(query)
        qualifiers = [f"venue:{venue}"] if venue else []
        if year_from and year_to and year_to - year_from <= 20:
            years = "|".join(str(year) for year in range(year_from, year_to + 1))
            qualifiers.append(f"year:{years}")
        dblp_query = " ".join([normalized_query, *qualifiers])
        hits, total_hits, error = _fetch_dblp_hits(dblp_query, max(k * 3, 30))
        if error:
            results.append({"source": f"DBLP/{venue or '全库'}", "error": error})
            continue
        for hit in hits:
            info = hit.get("info", {})
            result_venue = str(info.get("venue", ""))
            year_text = str(info.get("year", ""))
            year = int(year_text) if year_text.isdigit() else None
            if venue and result_venue.casefold() != venue.casefold():
                continue
            if year_from and (year is None or year < year_from):
                continue
            if year_to and (year is None or year > year_to):
                continue
            title = str(info.get("title", "")).rstrip(".")
            if not _is_relevant_title(title, query):
                continue
            key = str(info.get("key") or info.get("url") or info.get("title"))
            if key in seen:
                continue
            seen.add(key)
            results.append(
                {
                    "source": "DBLP",
                    "id": key,
                    "title": title,
                    "abstract": "",
                    "url": str(info.get("ee") or info.get("url") or ""),
                    "venue": result_venue,
                    "year": year_text,
                    "doi": str(info.get("doi", "")),
                    "total_hits": total_hits,
                }
            )
            if len([item for item in results if item["venue"].casefold() == result_venue.casefold()]) >= k:
                break
        if len(venue_queries) > 1:
            time.sleep(2)
    return results


def _fetch_dblp_hits(query: str, limit: int) -> tuple[list[dict], int, str]:
    """通过主站或官方镜像获取 DBLP 命中，隔离单次连接故障。"""
    params = {"q": query, "format": "json", "h": limit}
    headers = {"User-Agent": "HNMU-Agent/2.0 academic-research-client"}
    errors: list[str] = []
    for api_url in (DBLP_API_URL, DBLP_MIRROR_API_URL):
        try:
            with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS, follow_redirects=True, headers=headers) as client:
                response = client.get(api_url, params=params)
            if response.status_code == 429:
                errors.append("请求频率受限")
                continue
            response.raise_for_status()
            hits = response.json().get("result", {}).get("hits", {})
            return hits.get("hit", []), int(hits.get("@total", 0)), ""
        except (httpx.HTTPError, ValueError) as error:
            errors.append(str(error))
    return [], 0, "；".join(errors)


def search_arxiv(
    query: str,
    k: int = 5,
    categories: list[str] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict]:
    """检索 arXiv，返回标题/摘要/链接/分类。

    Args:
        query: 主题检索词。
        k: 返回条数上限。
        categories: 限定的 arXiv 分类代码列表，为空则不限分类。

    Returns:
        命中文献列表。
    """
    arxiv_query = _build_arxiv_query(normalize_search_query(query), categories)
    if year_from or year_to:
        start = f"{year_from or 1991}01010000"
        end = f"{year_to or 2100}12312359"
        arxiv_query = f"({arxiv_query}) AND submittedDate:[{start} TO {end}]"
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
                "year": str(r.published.year) if r.published else "",
            }
        )
    return results
