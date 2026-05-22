/** Stock Analyzer Web 控制台 */

const API = "/api/v1";

const PAGE_META = {
  realtime: { title: "实时爬取", desc: "管理自选股与后台增量爬取" },
  analyze: { title: "技术分析", desc: "MA / MACD / RSI 与统计摘要" },
  predict: { title: "走势预测", desc: "基线策略与可选深度学习模型" },
  chart: { title: "图表可视化", desc: "K 线、均线与预测曲线" },
};

const METRIC_LABELS = {
  ma_5: "MA5",
  ma_10: "MA10",
  ma_20: "MA20",
  ma_60: "MA60",
  rsi_14: "RSI(14)",
  macd: "MACD",
  macd_signal: "MACD 信号",
  macd_hist: "MACD 柱",
};

/** @param {string} path @param {RequestInit} [opts] */
async function api(path, opts = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...opts.headers },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = err.detail;
    const msg = Array.isArray(detail)
      ? detail.map((d) => d.msg || JSON.stringify(d)).join("; ")
      : detail || res.statusText;
    throw new Error(msg);
  }
  if (res.headers.get("content-type")?.includes("application/json")) {
    return res.json();
  }
  return res;
}

/** @param {string} msg @param {boolean} [isError] */
function toast(msg, isError = false) {
  const root = document.getElementById("toast-root");
  const el = document.createElement("div");
  el.className = `toast${isError ? " error" : ""}`;
  el.textContent = msg;
  root.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

function formatJson(obj) {
  return JSON.stringify(obj, null, 2);
}

function formatNum(n, digits = 2) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  return Number(n).toLocaleString("zh-CN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function toDateInput(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function initDateRange() {
  const end = new Date();
  const start = new Date();
  start.setFullYear(start.getFullYear() - 1);
  document.getElementById("global-end").value = toDateInput(end);
  document.getElementById("global-start").value = toDateInput(start);
}

function getSymbol() {
  return document.getElementById("global-symbol").value.trim();
}

function buildQuery(extra = {}) {
  const q = new URLSearchParams();
  const start = document.getElementById("global-start").value;
  const end = document.getElementById("global-end").value;
  if (start) q.set("start", start);
  if (end) q.set("end", end);
  for (const [k, v] of Object.entries(extra)) {
    if (v != null && v !== "") q.set(k, String(v));
  }
  const s = q.toString();
  return s ? `?${s}` : "";
}

/** @param {HTMLButtonElement} btn @param {() => Promise<void>} fn */
async function withLoading(btn, fn) {
  if (!btn || btn.disabled) return;
  btn.disabled = true;
  btn.classList.add("loading");
  try {
    await fn();
  } finally {
    btn.disabled = false;
    btn.classList.remove("loading");
  }
}

// —— 导航 ——
document.querySelectorAll(".nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const panel = btn.dataset.panel;
    document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`panel-${panel}`)?.classList.add("active");
    const meta = PAGE_META[panel];
    if (meta) {
      document.getElementById("page-title").textContent = meta.title;
      document.getElementById("page-desc").textContent = meta.desc;
    }
    document.getElementById("sidebar")?.classList.remove("open");
  });
});

document.getElementById("btn-menu")?.addEventListener("click", () => {
  document.getElementById("sidebar")?.classList.toggle("open");
});

document.getElementById("btn-sync-symbol")?.addEventListener("click", () => {
  const sym = getSymbol();
  document.getElementById("symbol-input").value = sym;
  toast(`当前股票：${sym}`);
});

document.getElementById("global-symbol")?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") document.getElementById("btn-sync-symbol")?.click();
});

// —— 自选股 ——
let activeSymbol = "600519";

async function loadWatchlist() {
  const data = await api("/watchlist");
  const ul = document.getElementById("watchlist");
  const symbols = data.symbols || [];
  ul.innerHTML = "";
  document.getElementById("watchlist-count").textContent = `${symbols.length} 只`;
  document.getElementById("stat-watchlist").textContent = String(symbols.length);

  for (const sym of symbols) {
    const li = document.createElement("li");
    li.className = sym === activeSymbol ? "active" : "";
    li.innerHTML = `<span class="sym">${sym}</span><button type="button" title="移除" aria-label="移除 ${sym}">×</button>`;
    li.querySelector(".sym").addEventListener("click", () => {
      activeSymbol = sym;
      document.getElementById("global-symbol").value = sym;
      loadWatchlist();
      toast(`已选中 ${sym}`);
    });
    li.querySelector("button").addEventListener("click", async (ev) => {
      ev.stopPropagation();
      await api(`/watchlist/${sym}`, { method: "DELETE" });
      if (activeSymbol === sym) activeSymbol = getSymbol();
      await loadWatchlist();
    });
    ul.appendChild(li);
  }
}

document.getElementById("btn-add-symbol").addEventListener("click", async () => {
  const input = document.getElementById("symbol-input");
  const symbol = input.value.trim();
  if (!symbol) return;
  try {
    await api("/watchlist", { method: "POST", body: JSON.stringify({ symbol }) });
    input.value = "";
    activeSymbol = symbol;
    document.getElementById("global-symbol").value = symbol;
    await loadWatchlist();
    toast(`已添加 ${symbol}`);
  } catch (e) {
    toast(e.message, true);
  }
});

document.getElementById("symbol-input")?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") document.getElementById("btn-add-symbol").click();
});

// —— 策略 ——
async function loadStrategies() {
  const data = await api("/strategies");
  const predictSel = document.getElementById("predict-strategy");
  const chartSel = document.getElementById("chart-strategy");
  predictSel.innerHTML = "";
  for (const name of data.all) {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = data.baseline?.includes(name) ? `${name}（基线）` : name;
    predictSel.appendChild(opt);
  }
  chartSel.innerHTML = '<option value="">不叠加预测</option>';
  for (const name of data.all) {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    chartSel.appendChild(opt);
  }
}

// —— 实时状态 ——
function renderLogPanel(st) {
  const log = document.getElementById("rt-log");
  if (!st.last_run_at && !st.last_results?.length) {
    log.textContent = "等待操作…";
    return;
  }
  log.innerHTML = "";
  const header = document.createElement("div");
  header.className = `log-entry ${st.error_count > 0 ? "err" : "ok"}`;
  header.innerHTML = `<time>${st.last_run_at || "—"}</time>成功 ${st.success_count} · 失败 ${st.error_count}`;
  log.appendChild(header);
  for (const r of st.last_results || []) {
    const row = document.createElement("div");
    row.className = `log-entry ${r.status === "ok" ? "ok" : "err"}`;
    if (r.status === "ok") {
      row.textContent = `${r.symbol}：拉取 ${r.fetched} 条，入库 ${r.persisted} 条`;
    } else {
      row.textContent = `${r.symbol || "?"}：${r.message || r.error || "失败"}`;
    }
    log.appendChild(row);
  }
}

function applyRealtimeStatus(st) {
  const dot = document.getElementById("rt-dot");
  const text = document.getElementById("rt-status-text");
  if (st.running) {
    dot.classList.add("on");
    text.textContent = `运行中 · ${st.symbols.length} 只 · ${st.interval_seconds}s`;
    document.getElementById("stat-running").textContent = "运行中";
    document.getElementById("stat-running").className = "stat-value ok";
  } else {
    dot.classList.remove("on");
    text.textContent = "未启动";
    document.getElementById("stat-running").textContent = "停止";
    document.getElementById("stat-running").className = "stat-value";
  }
  document.getElementById("stat-success").textContent = String(st.success_count ?? "—");
  document.getElementById("stat-error").textContent = String(st.error_count ?? "—");
  document.getElementById("stat-error").className =
    st.error_count > 0 ? "stat-value err" : "stat-value";
  renderLogPanel(st);
}

function connectRealtimeWs() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/api/v1/ws/realtime`);
  ws.onmessage = (ev) => {
    try {
      applyRealtimeStatus(JSON.parse(ev.data));
    } catch {
      /* ignore */
    }
  };
  ws.onclose = () => setTimeout(connectRealtimeWs, 3000);
}

document.getElementById("btn-start-rt").addEventListener("click", () =>
  withLoading(document.getElementById("btn-start-rt"), async () => {
    const interval = Number(document.getElementById("interval-input").value) || 60;
    const st = await api("/realtime/start", {
      method: "POST",
      body: JSON.stringify({ interval_seconds: interval }),
    });
    applyRealtimeStatus(st);
    toast("实时爬取已启动");
  }),
);

document.getElementById("btn-stop-rt").addEventListener("click", async () => {
  const st = await api("/realtime/stop", { method: "POST" });
  applyRealtimeStatus(st);
  toast("已停止");
});

document.getElementById("btn-run-once").addEventListener("click", () =>
  withLoading(document.getElementById("btn-run-once"), async () => {
    const summary = await api("/realtime/run-once", { method: "POST", body: JSON.stringify({}) });
    renderLogPanel({
      last_run_at: summary.run_at,
      success_count: summary.success_count,
      error_count: summary.error_count,
      last_results: summary.results,
    });
    document.getElementById("stat-success").textContent = String(summary.success_count);
    document.getElementById("stat-error").textContent = String(summary.error_count);
    toast(`爬取完成：成功 ${summary.success_count}，失败 ${summary.error_count}`);
  }),
);

document.getElementById("btn-clear-log").addEventListener("click", () => {
  document.getElementById("rt-log").textContent = "等待操作…";
});

// —— 分析 ——
function renderMetrics(data) {
  const grid = document.getElementById("analyze-metrics");
  grid.innerHTML = "";
  const indicators = data.indicators || {};
  const keys = Object.keys(indicators).filter((k) => typeof indicators[k] === "number");
  if (!keys.length) return;

  for (const key of keys.slice(0, 12)) {
    const card = document.createElement("div");
    card.className = "metric-card";
    card.innerHTML = `<span class="name">${METRIC_LABELS[key] || key}</span><span class="value">${formatNum(indicators[key])}</span>`;
    grid.appendChild(card);
  }

  const summary = data.summary || {};
  const summaryKeys = Object.keys(summary).slice(0, 4);
  for (const key of summaryKeys) {
    const card = document.createElement("div");
    card.className = "metric-card";
    card.innerHTML = `<span class="name">${key}</span><span class="value">${formatNum(summary[key], 4)}</span><span class="sub">摘要</span>`;
    grid.appendChild(card);
  }

  if (data.as_of) {
    const card = document.createElement("div");
    card.className = "metric-card";
    card.innerHTML = `<span class="name">截止日</span><span class="value" style="font-size:0.95rem">${data.as_of}</span>`;
    grid.appendChild(card);
  }
}

document.getElementById("btn-analyze").addEventListener("click", () =>
  withLoading(document.getElementById("btn-analyze"), async () => {
    const symbol = getSymbol();
    if (!symbol) throw new Error("请输入股票代码");
    const grid = document.getElementById("analyze-metrics");
    grid.innerHTML = '<span style="color:var(--muted);padding:1rem">分析中…</span>';
    const data = await api(`/analysis/${symbol}${buildQuery()}`);
    renderMetrics(data);
    document.getElementById("analyze-result").textContent = formatJson(data);
    toast(`${symbol} 分析完成`);
  }).catch((e) => toast(e.message, true)),
);

// —— 预测 ——
function renderForecastChart(data) {
  const el = document.getElementById("predict-chart");
  if (!el) return;
  const points = data.points || [];
  if (!points.length) {
    el.innerHTML = '<p class="predict-chart-empty muted">暂无数据</p>';
    return;
  }
  if (typeof Plotly === "undefined") {
    el.innerHTML = '<p class="predict-chart-empty muted">图表库加载失败，请刷新页面</p>';
    return;
  }

  const dates = points.map((p) => p.date);
  const values = points.map((p) => Number(p.value));
  const lower = points.map((p) => Number(p.lower));
  const upper = points.map((p) => Number(p.upper));

  const traces = [
    {
      x: dates,
      y: upper,
      type: "scatter",
      mode: "lines",
      line: { width: 0 },
      showlegend: false,
      hoverinfo: "skip",
    },
    {
      x: dates,
      y: lower,
      type: "scatter",
      mode: "lines",
      fill: "tonexty",
      fillcolor: "rgba(129, 140, 248, 0.22)",
      line: { width: 0 },
      name: "置信区间",
      hoverinfo: "skip",
    },
    {
      x: dates,
      y: values,
      type: "scatter",
      mode: "lines+markers",
      name: "预测价",
      line: { color: "#818cf8", width: 2.5 },
      marker: { size: 6, color: "#38bdf8" },
    },
  ];

  const layout = {
    title: {
      text: `${data.symbol} · ${data.strategy} · ${data.horizon_days} 日`,
      font: { size: 14, color: "#e2e8f0" },
    },
    margin: { t: 48, r: 20, b: 48, l: 64 },
    paper_bgcolor: "transparent",
    plot_bgcolor: "#0d1219",
    font: { color: "#94a3b8", family: "Plus Jakarta Sans, system-ui, sans-serif" },
    xaxis: {
      gridcolor: "rgba(148, 163, 184, 0.12)",
      linecolor: "rgba(148, 163, 184, 0.2)",
    },
    yaxis: {
      title: { text: "价格", font: { size: 12 } },
      gridcolor: "rgba(148, 163, 184, 0.12)",
      linecolor: "rgba(148, 163, 184, 0.2)",
      tickformat: ",.2f",
    },
    legend: { orientation: "h", y: 1.18, x: 0 },
    hovermode: "x unified",
  };

  Plotly.newPlot(el, traces, layout, { responsive: true, displayModeBar: false });
}

function renderForecastTable(data) {
  const tbody = document.getElementById("predict-tbody");
  tbody.innerHTML = "";
  const points = data.points || [];
  if (!points.length) {
    tbody.innerHTML = '<tr class="placeholder-row"><td colspan="4">暂无数据</td></tr>';
    renderForecastChart(data);
    return;
  }
  for (const p of points) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${p.date}</td><td>${formatNum(p.value)}</td><td>${formatNum(p.lower)}</td><td>${formatNum(p.upper)}</td>`;
    tbody.appendChild(tr);
  }
  document.getElementById("predict-meta").textContent =
    `${data.strategy} · ${data.horizon_days} 天 · ${data.symbol}`;
  renderForecastChart(data);
}

document.getElementById("btn-predict").addEventListener("click", () =>
  withLoading(document.getElementById("btn-predict"), async () => {
    const symbol = getSymbol();
    const strategy = document.getElementById("predict-strategy").value;
    const days = document.getElementById("predict-days").value;
    const data = await api(
      `/forecast/${symbol}${buildQuery({ strategy, horizon_days: days })}`,
    );
    renderForecastTable(data);
    document.getElementById("predict-result").textContent = formatJson(data);
    toast(`已生成 ${data.points?.length || 0} 个预测点`);
  }).catch((e) => toast(e.message, true)),
);

// —— 图表 ——
let chartBlobUrl = null;

document.getElementById("btn-chart").addEventListener("click", () =>
  withLoading(document.getElementById("btn-chart"), async () => {
    const symbol = getSymbol();
    const strategy = document.getElementById("chart-strategy").value;
    // 结束日期对齐到今天，确保 K 线与成交量拉到最新
    document.getElementById("global-end").value = toDateInput(new Date());
    const start = document.getElementById("global-start").value;
    const end = document.getElementById("global-end").value;
    const loading = document.getElementById("chart-loading");
    const frame = document.getElementById("chart-frame");
    const placeholder = document.getElementById("chart-placeholder");

    loading.classList.remove("hidden");
    placeholder.classList.remove("hidden");
    frame.classList.remove("visible");

    const res = await fetch(`${API}/chart`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        symbol,
        start: start || null,
        end: end || null,
        strategy: strategy || null,
        horizon_days: Number(document.getElementById("predict-days").value) || 30,
        refresh: true,
      }),
    });
    loading.classList.add("hidden");
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || res.statusText);
    }
    if (chartBlobUrl) URL.revokeObjectURL(chartBlobUrl);
    const blob = await res.blob();
    chartBlobUrl = URL.createObjectURL(blob);
    frame.src = chartBlobUrl;
    frame.classList.add("visible");
    placeholder.classList.add("hidden");
    toast("图表已生成");
  }).catch((e) => {
    document.getElementById("chart-loading").classList.add("hidden");
    toast(e.message, true);
  }),
);

document.getElementById("btn-chart-full").addEventListener("click", () => {
  document.getElementById("chart-container")?.classList.toggle("fullscreen");
});

// —— 初始化 ——
async function init() {
  initDateRange();
  document.getElementById("footer-time").textContent = new Date().toLocaleString("zh-CN");
  await loadWatchlist();
  await loadStrategies();
  const st = await api("/realtime/status");
  applyRealtimeStatus(st);
  connectRealtimeWs();
}

init().catch((e) => toast(e.message, true));
