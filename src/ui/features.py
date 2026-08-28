"""Feature Registry — single source of truth for all product capabilities.

This module is the ONLY place feature metadata lives. The Tools page
(``ui.pages.tools_page``) and the Coming Soon dialog (``ui.coming_soon``)
read exclusively from here, so the UI never hard-codes a feature name.

When a future tool actually ships, flip its ``status`` from
``COMING_SOON`` / ``PLANNED`` to ``AVAILABLE`` (and implement its business
module). The UI updates automatically — no nav or landing-page edits needed.

No business logic, no DB access, no core/data imports.
"""
from __future__ import annotations

from dataclasses import dataclass


class FeatureStatus:
    """Exactly three lifecycle states — no fake dates, no fake percentages."""

    AVAILABLE = "available"
    COMING_SOON = "coming_soon"
    PLANNED = "planned"


_STATUS_LABELS = {
    FeatureStatus.AVAILABLE: "已上线",
    FeatureStatus.COMING_SOON: "即将上线",
    FeatureStatus.PLANNED: "规划中",
}


@dataclass
class FeatureDefinition:
    key: str
    name: str
    icon: str
    description: str
    category: str
    status: str = FeatureStatus.PLANNED
    enabled: bool = True
    coming_soon: bool = False
    planned_version: str = ""

    @property
    def status_label(self) -> str:
        return _STATUS_LABELS.get(self.status, self.status)


# Order here is the display order on the Tools page.
FEATURES: list[FeatureDefinition] = [
    FeatureDefinition(
        key="FILE_CLEANER",
        name="文件整理",
        icon="🧹",
        description="安全、本地、一键整理桌面与下载，文件只移动、不删除、可撤销。",
        category="core",
        status=FeatureStatus.AVAILABLE,
        coming_soon=False,
    ),
    FeatureDefinition(
        key="EYE_CARE",
        name="护眼模式",
        icon="👁️",
        description="降低屏幕刺激，提供更舒适的夜间使用体验。",
        category="comfort",
        status=FeatureStatus.COMING_SOON,
        coming_soon=True,
    ),
    FeatureDefinition(
        key="QUICK_LOCK",
        name="快速锁屏",
        icon="🔒",
        description="一键锁定电脑，离开时更安心。",
        category="security",
        status=FeatureStatus.COMING_SOON,
        coming_soon=True,
    ),
    FeatureDefinition(
        key="DUPLICATE_FINDER",
        name="重复文件查找",
        icon="🔍",
        description="快速发现重复文件，帮助释放磁盘空间。",
        category="storage",
        status=FeatureStatus.COMING_SOON,
        coming_soon=True,
    ),
    FeatureDefinition(
        key="LARGE_FILES",
        name="大文件分析",
        icon="📦",
        description="快速找到占用空间较大的文件。",
        category="storage",
        status=FeatureStatus.COMING_SOON,
        coming_soon=True,
    ),
    FeatureDefinition(
        key="EMPTY_FOLDER",
        name="空文件夹清理",
        icon="🗑️",
        description="发现长期未使用的空文件夹，让文件结构更清爽。",
        category="storage",
        status=FeatureStatus.COMING_SOON,
        coming_soon=True,
    ),
    FeatureDefinition(
        key="BATCH_RENAME",
        name="批量重命名",
        icon="✏️",
        description="一次整理多个文件名称，快速建立统一命名规则。",
        category="productivity",
        status=FeatureStatus.COMING_SOON,
        coming_soon=True,
    ),
    FeatureDefinition(
        key="QUICK_SEARCH",
        name="快速搜索",
        icon="⚡",
        description="更快找到电脑中的文件和文件夹。",
        category="productivity",
        status=FeatureStatus.PLANNED,
        coming_soon=True,
    ),
    FeatureDefinition(
        key="FOLDER_ANALYZER",
        name="文件夹分析",
        icon="📊",
        description="查看文件数量、类型、大小和空间占用情况。",
        category="storage",
        status=FeatureStatus.PLANNED,
        coming_soon=True,
    ),
    FeatureDefinition(
        key="SCHEDULED_CLEAN",
        name="定时整理",
        icon="⏰",
        description="按照自己的时间计划自动整理指定文件夹。",
        category="automation",
        status=FeatureStatus.PLANNED,
        coming_soon=True,
    ),
    FeatureDefinition(
        key="STARTUP_CLEAN",
        name="开机整理",
        icon="🚀",
        description="启动电脑后自动检查指定目录。",
        category="automation",
        status=FeatureStatus.PLANNED,
        coming_soon=True,
    ),
]


def get_features(include_available: bool = False) -> list[FeatureDefinition]:
    """Return registry features, optionally including the AVAILABLE core tool."""
    return [
        f for f in FEATURES
        if include_available or f.status != FeatureStatus.AVAILABLE
    ]


def get_feature(key: str) -> FeatureDefinition | None:
    for f in FEATURES:
        if f.key == key:
            return f
    return None
