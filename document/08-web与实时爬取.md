# Web 控制台与实时爬取

## 功能概览

| 能力 | 说明 |
|------|------|
| 实时爬取 | 后台 `RealtimeScheduler` 按间隔对自选股做增量日 K 爬取（默认回溯 7 天） |
| 分析 / 预测 | REST API 与 Web 面板调用既有 `AnalysisService`、`PredictService` |
| Web 界面 | 深色仪表盘：`/` 入口，静态资源 `/static/*` |

## 启动

```bash
uvicorn stock_analyzer.interface.api.app:app --reload --host 0.0.0.0 --port 8000
```

浏览器访问：`http://127.0.0.1:8000/`

## 配置（`.env`）

| 变量 | 默认 | 说明 |
|------|------|------|
| `WATCHLIST_PATH` | `./data/watchlist.json` | 自选股 JSON |
| `REALTIME_INTERVAL_SECONDS` | `60` | 默认调度间隔 |
| `REALTIME_INCREMENTAL_DAYS` | `7` | 增量爬取天数 |

## 主要 API

- `GET/PUT/POST/DELETE /api/v1/watchlist` — 自选股
- `POST /api/v1/realtime/start|stop|run-once` — 调度控制
- `GET /api/v1/realtime/status` — 状态
- `WS /api/v1/ws/realtime` — 每 2 秒推送状态
- `GET /api/v1/analysis/{symbol}` — 技术分析
- `GET /api/v1/forecast/{symbol}` — 走势预测
- `POST /api/v1/chart` — 生成 HTML 图表

## 架构

```
Web (index.html + app.js)
    ↓ REST / WebSocket
FastAPI routes
    ↓
RealtimeScheduler → CrawlService → AkShare → SQLite
AnalysisService / PredictService / VisualizeService
```

## API 文档（Swagger）

在 `/docs` 中按步骤试调接口的完整清单见 **[09-API文档使用指南.md](./09-API文档使用指南.md)**（爬取 → 分析 → 预测）。

## 注意事项

- 实时爬取受 `CRAWL_MAX_QPS` 限流，请勿将间隔设得过小。
- 学习研究用途，不构成投资建议。
