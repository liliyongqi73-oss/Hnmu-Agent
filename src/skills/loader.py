"""技能加载器：解析 workspace/skills/<id>/SKILL.md 为可执行技能。

每个技能一个文件夹，SKILL.md 由 YAML 风格 frontmatter 与正文组成：

    ---
    name: review
    description: 基于检索上下文撰写相关工作综述并指出研究空白
    task: review
    ---
    # 系统提示
    <系统提示正文>

    # 用户模板
    <带 {占位符} 的用户消息模板>

外置提示词后，调整领域规范、院内模板无需改动 Python 代码，
非技术人员也可维护技能库。
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from server.app.core.config import WORKSPACE_DIR

SKILLS_DIR = WORKSPACE_DIR / "skills"

_SYSTEM_HEADING = "# 系统提示"
_USER_HEADING = "# 用户模板"


@dataclass(frozen=True)
class Skill:
    """一个可执行技能的运行时表示。

    Attributes:
        name: 技能标识，与目录名一致。
        description: 技能用途简述，用于技能库展示与相关性判断。
        task: 交给 llm_router 的任务标识，决定本地或云端路由。
        system_prompt: 系统提示正文。
        user_template: 含 {占位符} 的用户消息模板。
    """

    name: str
    description: str
    task: str
    system_prompt: str
    user_template: str

    def render_user(self, values: dict[str, str]) -> str:
        """用阶段输入渲染用户消息模板。

        Args:
            values: 占位符到文本的映射。

        Returns:
            渲染后的用户消息；缺失占位符按空字符串处理。
        """
        rendered = self.user_template
        for key, value in values.items():
            rendered = rendered.replace("{" + key + "}", str(value))
        return rendered


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """拆分 frontmatter 与正文。

    Args:
        text: SKILL.md 全文。

    Returns:
        (frontmatter 键值映射, 正文文本)。

    Raises:
        ValueError: 缺少合法的 frontmatter 分隔符。
    """
    if not text.lstrip().startswith("---"):
        raise ValueError("SKILL.md 缺少 frontmatter")
    stripped = text.lstrip()
    _, _, rest = stripped.partition("---")
    front_block, sep, body = rest.partition("---")
    if not sep:
        raise ValueError("SKILL.md frontmatter 未正确闭合")
    meta: dict[str, str] = {}
    for line in front_block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, body


def _split_sections(body: str) -> tuple[str, str]:
    """从正文中切出系统提示与用户模板两段。

    Args:
        body: frontmatter 之后的正文。

    Returns:
        (系统提示正文, 用户模板正文)。

    Raises:
        ValueError: 缺少必需的标题段。
    """
    if _SYSTEM_HEADING not in body or _USER_HEADING not in body:
        raise ValueError(f"SKILL.md 正文需包含 `{_SYSTEM_HEADING}` 与 `{_USER_HEADING}`")
    system_part = body.split(_SYSTEM_HEADING, 1)[1]
    system_prompt, _, user_part = system_part.partition(_USER_HEADING)
    return system_prompt.strip(), user_part.strip()


@lru_cache(maxsize=None)
def load_skill(name: str) -> Skill:
    """按名称加载并解析技能（带缓存）。

    Args:
        name: 技能标识，对应 workspace/skills/<name>/SKILL.md。

    Returns:
        解析后的技能。

    Raises:
        FileNotFoundError: 技能文件不存在。
        ValueError: 技能文件格式不合法或缺少必需字段。
    """
    path = SKILLS_DIR / name / "SKILL.md"
    if not path.exists():
        raise FileNotFoundError(f"技能 {name} 不存在：{path}")
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    system_prompt, user_template = _split_sections(body)
    missing = [field for field in ("name", "description", "task") if not meta.get(field)]
    if missing:
        raise ValueError(f"技能 {name} 缺少 frontmatter 字段：{', '.join(missing)}")
    return Skill(
        name=meta["name"],
        description=meta["description"],
        task=meta["task"],
        system_prompt=system_prompt,
        user_template=user_template,
    )
