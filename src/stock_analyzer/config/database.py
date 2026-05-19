"""数据库 URL 解析工具。"""

from pathlib import Path

_SQLITE_PREFIXES = (
    "sqlite+aiosqlite:///",
    "sqlite:///",
)


def sqlite_path_from_database_url(url: str) -> Path:
    """将 SQLAlchemy 风格 SQLite URL 转为本地文件路径。"""
    for prefix in _SQLITE_PREFIXES:
        if url.startswith(prefix):
            raw = url[len(prefix) :]
            return Path(raw)
    msg = f"不支持的 DATABASE_URL: {url}"
    raise ValueError(msg)
