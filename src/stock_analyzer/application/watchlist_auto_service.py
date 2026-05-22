"""根据走势与技术指标自动将优质标的加入自选股。"""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta

from stock_analyzer.application.analysis_service import AnalysisService
from stock_analyzer.application.crawl_service import CrawlRequest, CrawlService
from stock_analyzer.application.predict_service import PredictService
from stock_analyzer.application.watchlist_store import WatchlistStore
from stock_analyzer.domain.stock_screener import OutlookScore, score_outlook
from stock_analyzer.infrastructure.sources.akshare_source import QuoteSourceError

logger = logging.getLogger(__name__)

_DEFAULT_LOOKBACK_DAYS = 120
_DEFAULT_HORIZON_DAYS = 30
_DEFAULT_STRATEGY = "ma_trend"


@dataclass
class AutoAddResult:
    """自动添加执行结果。"""

    added: list[str] = field(default_factory=list)
    skipped_existing: list[str] = field(default_factory=list)
    skipped_no_data: list[str] = field(default_factory=list)
    skipped_low_score: list[str] = field(default_factory=list)
    ranked: list[OutlookScore] = field(default_factory=list)
    fetched: list[str] = field(default_factory=list)


class WatchlistAutoService:
    """扫描候选股票：自动拉取行情 → 评分 → 将得分最高的若干只写入自选股。"""

    def __init__(
        self,
        watchlist: WatchlistStore,
        analysis: AnalysisService,
        predict: PredictService,
        crawl: CrawlService | None = None,
        *,
        min_score: float = 55.0,
        max_add: int = 5,
    ) -> None:
        self.watchlist = watchlist
        self._analysis = analysis
        self._predict = predict
        self._crawl = crawl
        self._min_score = min_score
        self._max_add = max_add

    async def auto_add(
        self,
        candidates: list[str],
        *,
        end: date | None = None,
        strategy: str = _DEFAULT_STRATEGY,
        horizon_days: int = _DEFAULT_HORIZON_DAYS,
        max_add: int | None = None,
        min_score: float | None = None,
    ) -> AutoAddResult:
        end_date = end or date.today()
        start_date = end_date - timedelta(days=_DEFAULT_LOOKBACK_DAYS)
        limit = max_add if max_add is not None else self._max_add
        threshold = min_score if min_score is not None else self._min_score
        existing = set(self.watchlist.list_symbols())
        scores: list[OutlookScore] = []
        result = AutoAddResult()

        to_screen: list[str] = []
        for sym in candidates:
            stripped = sym.strip()
            if not stripped:
                continue
            if stripped in existing:
                result.skipped_existing.append(stripped)
            else:
                to_screen.append(stripped)

        if self._crawl and to_screen:
            await self._fetch_candidates(to_screen, start_date, end_date, result)

        for sym in to_screen:
            try:
                analysis = await self._analysis.analyze(sym, start_date, end_date)
                forecast = await self._predict.predict(
                    sym,
                    start_date,
                    end_date,
                    strategy,
                    horizon_days,
                )
            except ValueError:
                result.skipped_no_data.append(sym)
                continue
            outlook = score_outlook(analysis, forecast, pass_threshold=threshold)
            scores.append(outlook)

        scores.sort(key=lambda s: s.score, reverse=True)
        result.ranked = scores

        for outlook in scores[:limit]:
            self.watchlist.add_symbol(outlook.symbol)
            result.added.append(outlook.symbol)

        for outlook in scores[limit:]:
            result.skipped_low_score.append(outlook.symbol)

        return result

    async def _fetch_candidates(
        self,
        symbols: list[str],
        start: date,
        end: date,
        result: AutoAddResult,
    ) -> None:
        """批量拉取候选股日 K 并入库（无需用户提前爬取）。"""
        batch = [CrawlRequest(symbol=s, start=start, end=end) for s in symbols]
        try:
            crawl_results = await self._crawl.crawl_batch(batch)  # type: ignore[union-attr]
        except (QuoteSourceError, ValueError, OSError) as exc:
            logger.warning("智能添加批量拉取失败: %s", exc)
            return
        result.fetched = sorted(r.symbol for r in crawl_results if r.fetched_count > 0)
