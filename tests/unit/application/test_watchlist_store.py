"""自选股存储单元测试。"""

from pathlib import Path

import pytest

from stock_analyzer.application.watchlist_store import WatchlistStore


def test_watchlist_add_and_remove(tmp_path: Path) -> None:
    store = WatchlistStore(tmp_path / "watchlist.json")
    assert store.list_symbols() == []
    assert store.add_symbol("600519") == ["600519"]
    assert store.add_symbol("000001") == ["000001", "600519"]
    assert store.remove_symbol("600519") == ["000001"]


def test_watchlist_invalid_symbol(tmp_path: Path) -> None:
    store = WatchlistStore(tmp_path / "watchlist.json")
    with pytest.raises(ValueError, match="无效"):
        store.add_symbol("abc")
