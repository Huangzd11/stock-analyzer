"""外部数据源适配器。"""

from stock_analyzer.infrastructure.sources.akshare_source import AkShareSource, QuoteSourceError

__all__ = ["AkShareSource", "QuoteSourceError"]
