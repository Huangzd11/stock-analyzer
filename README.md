# Stock Analyzer

A 股数据采集、技术分析、走势预测与可视化工具（学习研究用途，不构成投资建议）。

## 安装

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

pip install -e ".[dev]"
```

可选依赖：

```bash
pip install -e ".[stats]"   # Holt-Winters / ARIMA
pip install -e ".[ml]"      # 阶段 B：深度学习
```

复制环境变量示例：

```bash
copy .env.example .env   # Windows
```

## CLI

```bash
# 爬取日 K 入库
stock-analyzer crawl -s 600519,000001 --start 2024-01-01 --end 2024-06-01

# 技术分析（JSON）
stock-analyzer analyze --symbol 600519

# 走势预测（基线）
stock-analyzer predict --symbol 600519 --strategy ma_trend --days 30

# LSTM 深度学习预测（需 pip install -e ".[ml]"）
stock-analyzer predict --symbol 600519 --strategy lstm --days 30 --enable-ml

# 生成 HTML 图表
stock-analyzer chart --symbol 600519 -o ./output/600519.html
```

## Web 控制台

**一键启动（Windows）：**

```bat
scripts\start.bat
```

或 PowerShell（支持 `-Reload`、`-Port`）：

```powershell
.\scripts\start.ps1
.\scripts\start.ps1 -Port 8080 -Reload
```

**手动启动：**

```bash
uvicorn stock_analyzer.interface.api.app:app --reload --host 0.0.0.0 --port 8000
```

浏览器打开 `http://127.0.0.1:8000/` 可：

- 管理自选股并启动/停止**实时爬取**
- 执行技术分析、走势预测
- 生成 K 线图表（可叠加预测曲线）

详见 [document/08-web与实时爬取.md](document/08-web与实时爬取.md)。

## API

- 健康检查：`GET /health`
- 技术分析：`GET /api/v1/analysis/{symbol}?start=2024-01-01&end=2024-03-01`
- 实时状态：`GET /api/v1/realtime/status`
- OpenAPI：`GET /docs`（使用说明见 [document/09-API文档使用指南.md](document/09-API文档使用指南.md)）

## 开发

```bash
pytest -m "not slow and not ml"
ruff check src tests
mypy
```

## 文档

设计文档见 [document/README.md](document/README.md)。
