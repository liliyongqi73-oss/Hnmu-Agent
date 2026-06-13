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

# 可用检索数据库。会议论文通过 DBLP 的公开接口检索。
RETRIEVAL_DATABASES: list[dict[str, str]] = [
    {"id": "dblp", "name": "DBLP", "description": "计算机领域会议与期刊"},
    {"id": "pubmed", "name": "PubMed", "description": "医学与生命科学文献"},
    {"id": "arxiv", "name": "arXiv", "description": "开放预印本"},
    {"id": "local", "name": "院内知识库", "description": "本地向量文献库"},
]

# 顶级人工智能会议，venue 为 DBLP 返回的标准会议缩写。
COMPUTER_SCIENCE_CONFERENCES: list[dict[str, str]] = [
    {"id": "CVPR", "name": "CVPR", "description": "计算机视觉与模式识别"},
    {"id": "AAAI", "name": "AAAI", "description": "人工智能协会年会"},
    {"id": "ICML", "name": "ICML", "description": "机器学习国际会议"},
    {"id": "ICLR", "name": "ICLR", "description": "学习表征国际会议"},
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


def list_retrieval_databases() -> list[dict[str, str]]:
    """返回可用检索数据库清单。"""
    return list(RETRIEVAL_DATABASES)


def list_computer_science_conferences() -> list[dict[str, str]]:
    """返回可通过 DBLP 检索的会议清单。"""
    return list(COMPUTER_SCIENCE_CONFERENCES)
