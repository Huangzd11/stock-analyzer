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

# 走势预测
stock-analyzer predict --symbol 600519 --strategy ma_trend --days 30

# 生成 HTML 图表
stock-analyzer chart --symbol 600519 -o ./output/600519.html
```

## API

```bash
uvicorn stock_analyzer.interface.api.app:app --reload
```

- 健康检查：`GET /health`
- 技术分析：`GET /api/v1/analysis/{symbol}?start=2024-01-01&end=2024-03-01`
- OpenAPI：`GET /docs`

## 开发

```bash
pytest -m "not slow and not ml"
ruff check src tests
mypy
```

## 文档

设计文档见 [document/README.md](document/README.md)。
