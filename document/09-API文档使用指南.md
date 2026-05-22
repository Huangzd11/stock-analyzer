# 09 — API 文档使用指南

本项目的 API 文档由 **FastAPI 自动生成**（OpenAPI / Swagger），无需单独维护 Markdown 接口表。本文说明如何打开文档，以及在 Swagger UI（`/docs`）中按顺序完成「爬取 → 分析 → 预测」。

> **免责声明**：仅供学习与研究，不构成投资建议。

## 1. 启动服务

任选一种方式：

```bat
scripts\start.bat
```

```powershell
.\scripts\start.ps1
# 或指定端口
.\scripts\start.ps1 -Port 8080 -Reload
```

```bash
uvicorn stock_analyzer.interface.api.app:app --reload --host 127.0.0.1 --port 8000
```

启动成功后，终端会提示文档地址，例如：`http://127.0.0.1:8000/docs`。

## 2. 打开文档页面

| 地址 | 用途 |
|------|------|
| **http://127.0.0.1:8000/docs** | **Swagger UI**（推荐，可在线试调） |
| http://127.0.0.1:8000/redoc | ReDoc（只读，排版更适合阅读） |
| http://127.0.0.1:8000/openapi.json | 原始 OpenAPI JSON（Postman 导入、代码生成等） |

也可从 **Web 控制台** 首页右上角点击「**API 文档**」，或访问 `http://127.0.0.1:8000/` 后进入 `/docs`。

若修改了启动端口（如 `8080`），将上述 URL 中的端口一并替换。

## 3. Swagger UI 基本操作

1. 浏览器打开 `/docs`，展开目标接口（如 `GET /api/v1/analysis/{symbol}`）。
2. 点击 **「Try it out」**。
3. 填写 **Path / Query / Request body**（文档会显示类型、默认值、是否必填）。
4. 点击 **「Execute」**。
5. 在下方查看 **Response body** 与 **HTTP 状态码**。

常见状态码：

| 状态码 | 含义 |
|--------|------|
| `200` | 成功 |
| `400` | 参数错误（日期格式、策略名不存在等） |
| `404` | 无数据（通常需先爬取该股票日 K） |

## 4. 使用前注意：先有数据

分析、预测、查行情均依赖 **SQLite 中已入库的日 K**。若返回 `404`，需先爬取数据。

**方式 A — CLI：**

```bash
stock-analyzer crawl -s 600519 --start 2024-01-01 --end 2024-06-01
```

**方式 B — 在 `/docs` 中调用 `POST /api/v1/crawl`**（见下文第 1 步）。

---

## 5. `/docs` 点击顺序：从爬取到分析到预测

以下以股票代码 **600519**（贵州茅台）为例，可替换为任意 6 位 A 股代码。默认服务地址为 `http://127.0.0.1:8000/docs`。

每个接口的操作相同：**展开 → Try it out → 填参数 → Execute → 查看 Responses**。

### 第 0 步（可选）：确认服务正常

| 在 `/docs` 中展开 | 操作 |
|-------------------|------|
| **GET `/health`** → **Health** | Try it out → Execute |

**期望**：`200`，响应体为 `{"status":"ok"}`。

### 第 1 步：爬取日 K 入库（必做）

| 在 `/docs` 中展开 | 操作 |
|-------------------|------|
| **POST `/api/v1/crawl`** → **Crawl Symbols** | Try it out |

**Request body** 示例：

```json
{
  "symbols": ["600519"],
  "start": "2024-01-01",
  "end": "2025-05-20"
}
```

说明：

- `start` / `end` 可省略；省略时 `end` 为今天，`start` 约为 `end` 前 90 天。
- 点击 **Execute**。

**期望**：`200`，`results` 中 `fetched`、`persisted` 均大于 0。  
若 `persisted` 为 0 或后续步骤返回 `404`，请检查日期区间与网络后重试本步。

### 第 2 步（建议）：确认库里已有行情

| 在 `/docs` 中展开 | 操作 |
|-------------------|------|
| **GET `/api/v1/quotes/{symbol}`** → **Get Quotes** | Try it out |

| 参数 | 示例值 |
|------|--------|
| `symbol` | `600519` |
| `start` | `2024-01-01`（可留空） |
| `end` | `2025-05-20`（可留空） |

点击 **Execute**。

**期望**：`200`，`count` > 0，`quotes` 含 `trade_date`、`close` 等字段。  
若 `count` 为 0，回到 **第 1 步** 调整日期或代码。

### 第 3 步（可选）：查看可用预测策略

| 在 `/docs` 中展开 | 操作 |
|-------------------|------|
| **GET `/api/v1/strategies`** → **List Strategies** | Try it out → Execute |

**期望**：`200`，例如：

```json
{
  "baseline": ["linear_trend", "ma_trend"],
  "all": ["linear_trend", "ma_trend"]
}
```

记下要使用的 `strategy`（下文默认 `ma_trend`）。使用 `lstm` 需安装可选依赖：`pip install -e ".[ml]"`，且 `all` 列表中包含 `lstm`。详见 [07-预测路线图.md](./07-预测路线图.md)。

### 第 4 步：技术分析

| 在 `/docs` 中展开 | 操作 |
|-------------------|------|
| **GET `/api/v1/analysis/{symbol}`** → **Get Analysis** | Try it out |

| 参数 | 示例值 |
|------|--------|
| `symbol` | `600519` |
| `start` | `2024-01-01` |
| `end` | `2025-05-20` |

点击 **Execute**。

**期望**：`200`，响应含 MA、MACD、RSI 及统计摘要（`AnalysisResult`）。  
**若 404**：该区间无数据 → 回到 **第 1 步**，并保证 `start`/`end` 与爬取区间一致。

### 第 5 步：走势预测

| 在 `/docs` 中展开 | 操作 |
|-------------------|------|
| **GET `/api/v1/forecast/{symbol}`** → **Get Forecast** | Try it out |

| 参数 | 示例值 | 说明 |
|------|--------|------|
| `symbol` | `600519` | 路径参数 |
| `start` | `2024-01-01` | 建议覆盖足够历史（默认约 end 前 120 天） |
| `end` | `2025-05-20` | 与爬取 `end` 一致 |
| `strategy` | `ma_trend` | 亦可为 `linear_trend`、`lstm` 等 |
| `horizon_days` | `30` | 预测未来天数（1～365） |

点击 **Execute**。

**期望**：`200`，含 `strategy`、`points[]`（未来日期与预测价）、`trend`（`up` / `down` / `sideways`），可能含 `lower` / `upper` 置信区间。  
**若 400**：`strategy` 拼写错误或当前环境不可用（参考第 3 步列表）。  
**若 404**：历史数据不足 → 扩大 **第 1 步** 的 `start` 后重新爬取。

### 第 6 步（可选）：生成 K 线 + 预测图

| 在 `/docs` 中展开 | 操作 |
|-------------------|------|
| **POST `/api/v1/chart`** → **Create Chart** | Try it out |

**Request body** 示例：

```json
{
  "symbol": "600519",
  "start": "2024-01-01",
  "end": "2025-05-20",
  "strategy": "ma_trend",
  "horizon_days": 30,
  "refresh": true
}
```

点击 **Execute**。

**期望**：`200`，浏览器下载 HTML；文件同时写入 `./output/web/600519.html`，可用浏览器直接打开。

---

## 6. 流程一览

```mermaid
flowchart LR
    A["0. GET /health"] --> B["1. POST /crawl"]
    B --> C["2. GET /quotes/{symbol}"]
    C --> D["3. GET /strategies 可选"]
    D --> E["4. GET /analysis/{symbol}"]
    E --> F["5. GET /forecast/{symbol}"]
    F --> G["6. POST /chart 可选"]
```

### 最小路径（仅跑通主流程）

只需依次调用以下 3 个接口：

1. **POST `/api/v1/crawl`** — 爬取  
2. **GET `/api/v1/analysis/{symbol}`** — 分析  
3. **GET `/api/v1/forecast/{symbol}`** — 预测  

排查数据时可用 **GET `/api/v1/quotes/{symbol}`**。

---

## 7. 常用接口速查

所有业务接口前缀为 **`/api/v1`**。完整列表见 [08-web与实时爬取.md](./08-web与实时爬取.md)。

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查 |
| `GET` | `/api/v1/strategies` | 可用预测策略列表 |
| `GET` | `/api/v1/quotes/{symbol}` | 查询已入库行情 |
| `GET` | `/api/v1/analysis/{symbol}` | 技术分析 |
| `GET` | `/api/v1/forecast/{symbol}` | 走势预测 |
| `POST` | `/api/v1/crawl` | 批量爬取入库 |
| `POST` | `/api/v1/chart` | 生成 HTML 图表 |
| `GET/PUT/POST/DELETE` | `/api/v1/watchlist` | 自选股管理 |
| `GET/POST` | `/api/v1/realtime/*` | 实时爬取调度 |
| `WS` | `/api/v1/ws/realtime` | 每 2 秒推送实时状态 |

### 查询参数说明

| 参数 | 格式 | 说明 |
|------|------|------|
| `start` / `end` | `YYYY-MM-DD` | 分析/预测/行情时间区间；省略时使用默认值 |
| `strategy` | 字符串 | 预测策略，默认 `ma_trend` |
| `horizon_days` | 整数 1～365 | 预测未来天数，默认 30 |

---

## 8. curl 示例（可在终端直接调用）

**健康检查：**

```bash
curl http://127.0.0.1:8000/health
```

**技术分析：**

```bash
curl "http://127.0.0.1:8000/api/v1/analysis/600519?start=2024-01-01&end=2024-06-01"
```

**走势预测：**

```bash
curl "http://127.0.0.1:8000/api/v1/forecast/600519?strategy=ma_trend&horizon_days=30&start=2024-01-01&end=2024-06-01"
```

**查看可用策略：**

```bash
curl http://127.0.0.1:8000/api/v1/strategies
```

---

## 9. 与 Web 控制台的关系

| 入口 | 适用场景 |
|------|----------|
| **Web 面板**（`/`） | 日常操作：自选股、实时爬取、分析、预测、图表 |
| **API 文档**（`/docs`） | 调试接口、查看 JSON 结构、对接脚本 |

两者共用同一服务进程；Web 面板调用的即是上述 REST API。

## 10. 相关文档

- [08-web与实时爬取.md](./08-web与实时爬取.md) — Web 控制台、实时调度、API 列表  
- [07-预测路线图.md](./07-预测路线图.md) — 预测策略说明（`ma_trend`、`linear_trend`、`lstm` 等）  
- 项目根目录 [README.md](../README.md) — 安装与 CLI 用法  
