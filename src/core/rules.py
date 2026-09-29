"""File classification rules.

Maps file extensions to a stable category *key*, and provides the
user-facing display name for each category (Chinese, since the target
users are Chinese-speaking non-technical users).
"""
from __future__ import annotations

import hashlib

# Stable internal category keys -> display names shown in the UI.
CATEGORY_NAMES: dict[str, str] = {
    "images": "图片",
    "documents": "文档",
    "videos": "视频",
    "audio": "音频",
    "archives": "压缩包",
    "code": "代码",
    "executables": "安装程序",
    "others": "其他",
}

# Category key -> emoji used in the UI (Feature 5, V1.1).
CATEGORY_EMOJI: dict[str, str] = {
    "images": "🖼️",
    "documents": "📄",
    "videos": "🎬",
    "audio": "🎵",
    "archives": "🗜️",
    "code": "💻",
    "executables": "⚙️",
    "others": "📦",
}

# Extension (lower case, no dot) -> category key.
DEFAULT_RULES: dict[str, str] = {
    # --- images ---
    "jpg": "images", "jpeg": "images", "png": "images", "gif": "images",
    "bmp": "images", "tiff": "images", "tif": "images", "webp": "images",
    "svg": "images", "ico": "images", "heic": "images", "raw": "images",
    "cr2": "images", "nef": "images", "arw": "images", "psd": "images",
    "ai": "images", "avif": "images",
    # --- documents ---
    "pdf": "documents", "doc": "documents", "docx": "documents",
    "xls": "documents", "xlsx": "documents", "ppt": "documents",
    "pptx": "documents", "txt": "documents", "md": "documents",
    "rtf": "documents", "odt": "documents", "csv": "documents",
    "epub": "documents", "mobi": "documents", "wps": "documents",
    "pages": "documents",
    # --- videos ---
    # NOTE: ".ts" is ambiguous (MPEG transport stream video vs. TypeScript
    # source). It is claimed by BOTH the video and code families, and a plain
    # dict literal would silently keep only the last occurrence. We resolve the
    # ambiguity explicitly here in favour of *video*, because this product
    # targets non-technical desktop users, for whom a downloaded/recorded ".ts"
    # is far more likely a video than source code. Developers' ".tsx"/".jsx"
    # stay in the code family. Flip this single mapping if the audience changes.
    "mp4": "videos", "avi": "videos", "mkv": "videos", "mov": "videos",
    "wmv": "videos", "flv": "videos", "webm": "videos", "m4v": "videos",
    "mpg": "videos", "mpeg": "videos", "ts": "videos", "3gp": "videos",
    "vob": "videos", "m2ts": "videos", "mts": "videos",
    # --- audio ---
    "mp3": "audio", "wav": "audio", "flac": "audio", "aac": "audio",
    "ogg": "audio", "m4a": "audio", "wma": "audio", "ape": "audio",
    "opus": "audio",
    # --- archives ---
    "zip": "archives", "rar": "archives", "7z": "archives",
    "tar": "archives", "gz": "archives", "bz2": "archives",
    "xz": "archives", "tgz": "archives", "zst": "archives",
    "iso": "archives",
    # --- code / dev files ---
    "py": "code", "js": "code", "tsx": "code", "jsx": "code",
    "java": "code", "cpp": "code", "c": "code", "h": "code", "hpp": "code",
    "html": "code", "htm": "code", "css": "code", "scss": "code",
    "json": "code", "xml": "code", "sql": "code", "ipynb": "code",
    "go": "code", "rs": "code", "php": "code", "rb": "code", "sh": "code",
    "yaml": "code", "yml": "code", "toml": "code", "lua": "code",
    "swift": "code", "kt": "code",
    # --- executables / installers ---
    "exe": "executables", "msi": "executables", "dmg": "executables",
    "apk": "executables", "bat": "executables", "cmd": "executables",
    "msix": "executables", "appimage": "executables",
}

import re

# Folders produced by date-mode look like "2026-08"; we skip them on re-scans.
_DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}$")


def category_display(key: str) -> str:
    """Return the display name for a category key (falls back to the key)."""
    return CATEGORY_NAMES.get(key, key)


def get_exclude_dirs(mode: str) -> set[str]:
    """Directory names that the scanner must skip to avoid re-processing
    files that were already organized in a previous run."""
    if mode == "date":
        return set()  # date folders are skipped via the regex in the scanner
    return set(CATEGORY_NAMES.values())


def is_date_dir(name: str) -> bool:
    return bool(_DATE_DIR_RE.match(name))


# Reverse map: display name -> category key (for emoji lookup).
_NAME_TO_KEY = {v: k for k, v in CATEGORY_NAMES.items()}


def category_emoji(label: str) -> str:
    """Return the emoji for a category display label.

    Falls back to a calendar emoji for date-mode folders
    (``2026-08``) and a generic folder emoji for anything else.
    """
    key = _NAME_TO_KEY.get(label)
    if key and key in CATEGORY_EMOJI:
        return CATEGORY_EMOJI[key]
    if is_date_dir(label):
        return "📅"
    return "📂"


def rules_fingerprint(rules: dict[str, str] | None = None) -> str:
    """Stable, content-derived identifier for a rule set.

    A report must record *which* rules produced it, so two reports can be
    compared across app versions or against a user's own rule set (V1.2-A
    feature 4). The value is a pure function of the rule contents: same rules
    -> same id, any change -> different id.
    """
    rules = DEFAULT_RULES if rules is None else rules
    payload = ";".join(f"{k}={v}" for k, v in sorted(rules.items()))
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"rules-{digest}-{len(rules)}"
