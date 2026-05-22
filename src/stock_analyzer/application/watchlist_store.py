"""自选股列表持久化（JSON 文件）。"""

import json
from pathlib import Path

_SYMBOL_PATTERN_LEN = 6


class WatchlistStore:
    """管理用户关注的股票代码列表。"""

    def __init__(self, file_path: Path) -> None:
        self._path = file_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write([])

    def list_symbols(self) -> list[str]:
        return sorted(self._read())

    def set_symbols(self, symbols: list[str]) -> list[str]:
        cleaned = self._validate(symbols)
        self._write(cleaned)
        return cleaned

    def add_symbol(self, symbol: str) -> list[str]:
        current = set(self._read())
        current.add(self._validate_one(symbol))
        result = sorted(current)
        self._write(result)
        return result

    def remove_symbol(self, symbol: str) -> list[str]:
        current = set(self._read())
        current.discard(symbol.strip())
        result = sorted(current)
        self._write(result)
        return result

    def _read(self) -> list[str]:
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
        return [str(s) for s in raw]

    def _write(self, symbols: list[str]) -> None:
        self._path.write_text(
            json.dumps(symbols, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _validate(self, symbols: list[str]) -> list[str]:
        return sorted({self._validate_one(s) for s in symbols})

    def _validate_one(self, symbol: str) -> str:
        value = symbol.strip()
        if len(value) != _SYMBOL_PATTERN_LEN or not value.isdigit():
            msg = f"股票代码无效: {symbol}"
            raise ValueError(msg)
        return value
