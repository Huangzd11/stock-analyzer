"""本地端到端验证脚本。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
SYMBOL = "600519"
# 使用较宽区间，确保库内日 K 不少于预测策略所需根数
DATE_PARAMS = {"start": "2024-01-01", "end": "2026-05-19"}


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    line = f"[{status}] {name}"
    if detail:
        line += f" — {detail}"
    print(line)
    if not ok:
        sys.exit(1)


def main() -> None:
    results: list[str] = []
    with httpx.Client(base_url=BASE, timeout=120.0) as client:
        # 1. 健康检查
        r = client.get("/health")
        check("健康检查", r.status_code == 200 and r.json() == {"status": "ok"})

        # 2. Web 首页与静态资源
        r = client.get("/")
        check("Web 首页", r.status_code == 200 and "Stock Analyzer" in r.text)
        r = client.get("/static/styles.css")
        check("静态 CSS", r.status_code == 200 and "DM Sans" in r.text or "--bg" in r.text)
        r = client.get("/static/app.js")
        check("静态 JS", r.status_code == 200 and "api/v1" in r.text)

        # 3. 策略列表
        r = client.get("/api/v1/strategies")
        body = r.json()
        check(
            "策略列表",
            r.status_code == 200 and "ma_trend" in body.get("baseline", []),
            str(body.get("baseline")),
        )

        # 4. 自选股 CRUD
        r = client.get("/api/v1/watchlist")
        check("自选股读取", r.status_code == 200)
        r = client.post("/api/v1/watchlist", json={"symbol": SYMBOL})
        symbols = r.json().get("symbols", [])
        check("添加自选股", r.status_code == 200 and SYMBOL in symbols, str(symbols))

        # 5. 实时状态
        r = client.get("/api/v1/realtime/status")
        st = r.json()
        check("实时状态", r.status_code == 200 and "running" in st, f"running={st.get('running')}")

        # 6. 立即爬取一轮（依赖网络/代理）
        r = client.post("/api/v1/realtime/run-once", json={})
        if r.status_code == 200:
            summary = r.json()
            ok_crawl = summary.get("success_count", 0) >= 1
            check(
                "实时爬取 run-once",
                ok_crawl,
                f"success={summary.get('success_count')} error={summary.get('error_count')}",
            )
            results.append(json.dumps(summary, ensure_ascii=False, indent=2)[:500])
        else:
            print(f"[WARN] 实时爬取跳过（HTTP {r.status_code}）: {r.text[:200]}")

        # 7. 技术分析（使用库内数据）
        r = client.get(f"/api/v1/analysis/{SYMBOL}", params=DATE_PARAMS)
        if r.status_code == 200:
            a = r.json()
            check(
                "技术分析",
                a.get("symbol") == SYMBOL and "ma_20" in a.get("indicators", {}),
                f"ma_20={a.get('indicators', {}).get('ma_20')}",
            )
        else:
            check("技术分析", False, f"HTTP {r.status_code}: {r.text[:150]}")

        # 8. 走势预测
        r = client.get(
            f"/api/v1/forecast/{SYMBOL}",
            params={**DATE_PARAMS, "strategy": "ma_trend", "horizon_days": 10},
        )
        if r.status_code == 200:
            f = r.json()
            check(
                "走势预测",
                f.get("symbol") == SYMBOL and len(f.get("points", [])) > 0,
                f"points={len(f.get('points', []))}",
            )
        else:
            check("走势预测", False, f"HTTP {r.status_code}: {r.text[:150]}")

        # 9. 图表生成
        r = client.post(
            "/api/v1/chart",
            json={
                "symbol": SYMBOL,
                **DATE_PARAMS,
                "strategy": "ma_trend",
                "horizon_days": 10,
            },
        )
        if r.status_code == 200:
            out_dir = Path("output/web")
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"e2e_{SYMBOL}.html"
            out_file.write_bytes(r.content)
            check("图表生成", len(r.content) > 1000, f"saved {out_file} ({len(r.content)} bytes)")
        else:
            check("图表生成", False, f"HTTP {r.status_code}: {r.text[:150]}")

    print("\n=== 端到端验证全部通过 ===")
    if results:
        print("\n最近爬取摘要（节选）:\n", results[0])


if __name__ == "__main__":
    main()
