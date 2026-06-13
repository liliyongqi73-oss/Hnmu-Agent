"""检索来源预置清单：常用医学期刊与 arXiv 学科分类。

供前端下拉选择，用户也可自定义输入清单外的期刊名或分类代码。
期刊名需为 PubMed 可识别的全称或标准缩写，否则 [TA] 过滤可能 0 命中。
"""
from __future__ import annotations

# 常用医学期刊：name 为展示名，term 为 PubMed [TA] 字段使用的期刊名/缩写。
PUBMED_JOURNALS: list[dict[str, str]] = [
    {"name": "The Lancet", "term": "Lancet"},
    {"name": "New England Journal of Medicine", "term": "N Engl J Med"},
    {"name": "JAMA", "term": "JAMA"},
    {"name": "BMJ", "term": "BMJ"},
    {"name": "Nature Medicine", "term": "Nat Med"},
    {"name": "Nature", "term": "Nature"},
    {"name": "Science", "term": "Science"},
    {"name": "Cell", "term": "Cell"},
    {"name": "Annals of Internal Medicine", "term": "Ann Intern Med"},
    {"name": "The Lancet Oncology", "term": "Lancet Oncol"},
    {"name": "Circulation", "term": "Circulation"},
    {"name": "Radiology", "term": "Radiology"},
    {"name": "Journal of Clinical Oncology", "term": "J Clin Oncol"},
    {"name": "Gut", "term": "Gut"},
    {"name": "Diabetes Care", "term": "Diabetes Care"},
]

# 常用 arXiv 学科分类：code 为 arXiv category 代码，name 为中文说明。
ARXIV_CATEGORIES: list[dict[str, str]] = [
    {"code": "cs.CV", "name": "计算机视觉与模式识别"},
    {"code": "cs.LG", "name": "机器学习"},
    {"code": "cs.AI", "name": "人工智能"},
    {"code": "cs.CL", "name": "计算语言学与自然语言处理"},
    {"code": "eess.IV", "name": "图像与视频处理"},
    {"code": "eess.SP", "name": "信号处理"},
    {"code": "stat.ML", "name": "统计机器学习"},
    {"code": "q-bio.QM", "name": "定量方法（生物）"},
    {"code": "q-bio.NC", "name": "神经与认知"},
    {"code": "q-bio.GN", "name": "基因组学"},
]


def list_pubmed_journals() -> list[dict[str, str]]:
    """返回预置 PubMed 期刊清单。

    Returns:
        期刊展示名与 [TA] 检索词列表。
    """
    return list(PUBMED_JOURNALS)


def list_arxiv_categories() -> list[dict[str, str]]:
    """返回预置 arXiv 学科分类清单。

    Returns:
        分类代码与说明列表。
    """
    return list(ARXIV_CATEGORIES)
