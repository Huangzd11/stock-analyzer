"""数据库 URL 解析测试。"""

from pathlib import Path

import pytest

from stock_analyzer.config.database import sqlite_path_from_database_url


def test_sqlite_path_from_aiosqlite_url() -> None:
    path = sqlite_path_from_database_url("sqlite+aiosqlite:///./data/test.db")
    assert path == Path("./data/test.db")


def test_sqlite_path_rejects_unsupported_url() -> None:
    with pytest.raises(ValueError, match="不支持"):
        sqlite_path_from_database_url("postgresql://localhost/db")
