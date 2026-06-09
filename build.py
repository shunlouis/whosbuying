#!/usr/bin/env python3
"""
build.py — 組裝 sector-times index.html
從 sector_morandi.html 提取嵌入資料，產生優化後的線上版本
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC  = ROOT.parent / "sector_morandi.html"
OUT  = ROOT / "docs" / "index.html"
OUT.parent.mkdir(parents=True, exist_ok=True)

# 提取 STOCK_NAMES 和 FALLBACK_DATA
src_text = SRC.read_text(encoding="utf-8")
m1 = re.search(r'window\.STOCK_NAMES\s*=\s*(\{.*?\});', src_text)
m2 = re.search(r'window\.FALLBACK_DATA\s*=\s*(\{.*?\})\s*;', src_text, re.DOTALL)

stock_names_json = m1.group(1) if m1 else "{}"
fallback_json = m2.group(1) if m2 else "{}"

# 驗證 JSON
stock_names = json.loads(stock_names_json)
fallback = json.loads(fallback_json)
print(f"STOCK_NAMES: {len(stock_names)} entries")
print(f"FALLBACK: date={fallback.get('date')}, sectors={len(fallback.get('sectors', []))}")

# 壓縮 JSON
stock_names_min = json.dumps(stock_names, ensure_ascii=False, separators=(',', ':'))
fallback_min = json.dumps(fallback, ensure_ascii=False, separators=(',', ':'))

html = f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>The Sector Times · 板塊週報</title>
<meta name="description" content="台股板塊輪動週報——即時追蹤法人資金流向、CP值排行、抄底偵測與智慧情境建議">
<meta name="theme-color" content="#FFFDF8">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📊</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400&family=Source+Serif+4:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400&family=JetBrains+Mono:wght@400;500;600&family=Noto+Serif+TC:wght@400;500;700;900&display=swap" rel="stylesheet">
<style>
:root {{
  --bg-void:    #FFFDF8;
  --bg-panel:   #FAF6ED;
  --bg-card:    #FAF6ED;
  --bg-row:     #FFFDF8;
  --bg-hover:   #F5EFE0;
  --border:     #E0D6BE;
  --border-b:   #B8AE96;
  --border-rule:#1A1A1A;
  --amber:      #C7853E;
  --amber-dim:  rgba(199,133,62,0.12);
  --cyan:       #5C7A99;
  --cyan-dim:   rgba(92,122,153,0.10);
  --green:      #1FAA5F;
  --green-dim:  rgba(31,170,95,0.12);
  --red:        #E63946;
  --red-dim:    rgba(230,57,70,0.12);
  --purple:     #9CAB94;
  --text-1:     #121212;
  --text-2:     #5C554A;
  --text-3:     #8A8170;
  --font-display: 'Playfair Display', 'Noto Serif TC', Georgia, serif;
  --font-head:    'Playfair Display', 'Noto Serif TC', Georgia, serif;
  --font-body:    'Source Serif 4', 'Noto Serif TC', Georgia, serif;
  --font-mono:    'JetBrains Mono', 'SF Mono', monospace;
}}

*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%}}

body {{
  font-family: var(--font-body);
  background-color: var(--bg-void);
  color: var(--text-1);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  font-feature-settings: "tnum" 1, "kern" 1;
  -webkit-font-smoothing: antialiased;
}}

/* ─── HEADER ─────────────────── */
.hdr {{
  background: var(--bg-void);
  position: sticky;
  top: 0;
  z-index: 100;
  border-bottom: 1px solid var(--border-rule);
}}
.hdr-toolbar {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 28px;
  border-bottom: 1px solid var(--border);
  font-family: var(--font-body);
  font-size: 12px;
  color: var(--text-2);
}}
.hdr-toolbar-left {{ display: flex; gap: 16px; align-items: baseline; }}
.hdr-toolbar-right {{ display: flex; gap: 14px; align-items: center; }}
.hdr-toolbar-date {{ font-style: italic; color: var(--text-3); }}
.hdr-brand-mini {{
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 0.5px;
  color: var(--text-1);
  margin-right: 8px;
}}
.hdr-warn {{
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--amber);
  padding: 3px 10px;
  border: 1px solid var(--amber);
  background: var(--amber-dim);
}}

/* Ticker dashboard */
.ticker-dashboard {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0;
  padding: 18px 28px;
  background: var(--bg-void);
  border-top: 1px solid var(--border);
}}
.ticker-card {{
  padding: 0 24px;
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 6px;
}}
.ticker-card:first-child {{ padding-left: 0; }}
.ticker-card:last-child  {{ border-right: none; padding-right: 0; }}
.ticker-label {{
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 1.5px;
  color: var(--text-2);
  text-transform: uppercase;
}}
.ticker-row {{ display: flex; align-items: baseline; gap: 12px; }}
.ticker-price {{
  font-family: var(--font-display);
  font-weight: 900;
  font-size: 30px;
  line-height: 1;
  color: var(--text-1);
  letter-spacing: -0.5px;
  font-feature-settings: "tnum" 1;
}}
.ticker-price.pos {{ color: var(--green); }}
.ticker-price.neg {{ color: var(--red); }}
.ticker-chg {{
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 14px;
  font-feature-settings: "tnum" 1;
}}
.ticker-meta {{
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
}}

/* RT banner */
.rt-banner {{
  font-family: var(--font-body);
  font-style: italic;
  font-size: 13px;
  color: var(--text-2);
  text-align: center;
  padding: 8px 28px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-panel);
}}
.rt-banner .pos {{ font-style: normal; font-weight: 600; color: var(--green); font-family: var(--font-mono); }}
.rt-banner .neg {{ font-style: normal; font-weight: 600; color: var(--red); font-family: var(--font-mono); }}
.rt-banner .label-tag {{
  font-family: var(--font-mono);
  font-style: normal;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--text-1);
  margin-right: 8px;
}}

/* Nav */
.hdr-nav {{
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 28px;
  border-top: 3px double var(--border-rule);
  border-bottom: 1px solid var(--border-rule);
  gap: 32px;
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
}}
.hdr-nav-item {{
  color: var(--text-1);
  cursor: pointer;
  transition: color .15s;
  position: relative;
  padding: 4px 2px;
}}
.hdr-nav-item:hover {{ color: var(--cyan); }}
.hdr-nav-item.active {{ color: var(--text-1); }}
.hdr-nav-item.active::after {{
  content: '';
  position: absolute;
  bottom: -11px; left: 50%;
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--text-1);
  transform: translateX(-50%);
}}

/* ─── LAYOUT ─────────────────── */
.layout {{
  display: grid;
  grid-template-columns: 185px 1fr;
  flex: 1;
  overflow: hidden;
}}

/* ─── SIDEBAR ────────────────── */
.sidebar {{
  background: rgba(232,226,214,0.5);
  border-right: 1px solid var(--border);
  padding: 16px 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}}
.sidebar::-webkit-scrollbar{{ width:3px; }}
.sidebar::-webkit-scrollbar-thumb{{ background:var(--border); border-radius:2px; }}
.sb-section-title {{
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 2px;
  color: var(--text-1);
  padding: 8px 12px 4px;
  text-transform: uppercase;
  border-bottom: 1px solid var(--border-rule);
  margin-bottom: 4px;
}}
.stat-card {{
  margin: 0 12px;
  background: var(--bg-card);
  border-top: 1px solid var(--border-rule);
  padding: 14px 6px 16px;
  transition: background .15s;
}}
.stat-card:first-of-type {{ border-top: 3px double var(--border-rule); }}
.stat-card:hover {{ background: var(--bg-hover); }}
.stat-num {{
  font-family: var(--font-display);
  font-size: 38px;
  font-weight: 900;
  line-height: 1;
  margin-bottom: 6px;
  letter-spacing: -1px;
  font-feature-settings: "tnum" 1;
}}
.stat-label {{
  font-family: var(--font-body);
  font-style: italic;
  font-size: 12px;
  color: var(--text-2);
  line-height: 1.4;
}}
.stat-amber .stat-num {{ color: var(--amber); }}
.stat-cyan  .stat-num {{ color: var(--cyan); }}
.stat-red   .stat-num {{ color: var(--red); }}
.stat-green .stat-num {{ color: var(--green); }}
.sb-divider {{ height:1px; background:var(--border-rule); margin: 12px 12px; }}
.bottom-mini {{ padding: 0 12px; display: flex; flex-direction: column; gap: 0; }}
.bm-row {{
  border-top: 1px solid var(--border);
  padding: 10px 0;
  cursor: pointer;
  transition: background .15s;
}}
.bm-row:first-child {{ border-top: 1px solid var(--border-rule); }}
.bm-row:hover {{ background: var(--bg-hover); }}
.bm-name {{
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 700;
  color: var(--text-1);
  margin-bottom: 3px;
}}
.bm-stats {{
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-2);
  font-variant-numeric: tabular-nums;
}}
.bm-stats .pos {{ color: var(--green); font-weight: 600; }}
.bm-stats .neg {{ color: var(--red); font-weight: 600; }}

/* ─── MAIN ────────────────────── */
.main {{
  display: flex;
  flex-direction: column;
  overflow: hidden;
}}

/* ─── TAB PANELS ─────────────── */
.tab-panel {{ display: none; flex: 1; overflow-y: auto; padding: 32px 40px; }}
.tab-panel.active {{ display: block; animation: fadeIn .15s ease; }}
.tab-panel::-webkit-scrollbar{{ width:4px; }}
.tab-panel::-webkit-scrollbar-thumb{{ background:var(--border); border-radius:2px; }}
@keyframes fadeIn {{ from{{opacity:0;transform:translateY(4px)}} to{{opacity:1;transform:translateY(0)}} }}

/* Panel header */
.panel-hdr {{
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 3px double var(--border-rule);
}}
.panel-title {{
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 900;
  color: var(--text-1);
  margin-bottom: 8px;
  letter-spacing: -0.5px;
  line-height: 1.1;
}}
.panel-desc {{
  font-family: var(--font-body);
  font-style: italic;
  font-size: 14px;
  color: var(--text-2);
  line-height: 1.6;
  max-width: 720px;
}}
.panel-desc .hi {{
  font-style: normal;
  color: var(--text-1);
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 500;
  background: var(--bg-panel);
  padding: 1px 6px;
}}

/* ─── TABLE ───────────────────── */
.tbl-wrap {{
  background: var(--bg-void);
  border-top: 3px double var(--border-rule);
  border-bottom: 1px solid var(--border-rule);
}}
.tbl-head {{
  display: grid;
  padding: 10px 16px;
  background: var(--bg-void);
  border-bottom: 1px solid var(--border-rule);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  color: var(--text-1);
  text-transform: uppercase;
  letter-spacing: 1.2px;
  user-select: none;
}}
.tbl-row {{
  display: grid;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background .12s;
  align-items: center;
  font-feature-settings: "tnum" 1;
}}
.tbl-row:last-child {{ border-bottom: 1px solid var(--border-rule); }}
.tbl-row:hover {{ background: var(--bg-hover); }}
.tbl-row.expanded {{ background: var(--bg-panel); }}
.cp-cols {{ grid-template-columns: 34px 1fr 68px 80px 100px 72px 52px 60px; gap: 8px; }}
.bt-cols {{ grid-template-columns: 34px 1fr 68px 80px 100px 68px 80px; gap: 8px; }}

.rank-num {{
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 900;
  display: flex;
  align-items: center;
  color: var(--text-3);
  font-feature-settings: "tnum" 1;
}}
.rank-num::before {{ content: '№\\00a0'; font-size: 10px; color: var(--text-3); font-weight: 400; }}
.rank-num.r1, .rank-num.r2, .rank-num.r3 {{ color: var(--text-1); }}

.sec-name {{ display: flex; align-items: center; gap: 8px; min-width: 0; }}
.chevron {{
  color: var(--text-3);
  font-size: 11px;
  transition: transform .2s;
  flex-shrink: 0;
}}
.chevron.open {{ transform: rotate(90deg); color: var(--text-1); }}
.sec-label {{
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  color: var(--text-1);
  letter-spacing: -0.2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}}
.cell-num {{
  font-family: var(--font-mono);
  font-size: 13px;
  text-align: right;
  font-feature-settings: "tnum" 1;
  font-weight: 500;
}}
.pos {{ color: var(--green); }}
.neg {{ color: var(--red); }}
.neu {{ color: var(--text-2); }}

.bar-wrap {{ display: flex; align-items: center; justify-content: flex-end; gap: 6px; }}
.bar-bg {{ width: 72px; height: 4px; background: var(--bg-panel); border: 1px solid var(--border); overflow: hidden; flex-shrink: 0; }}
.bar-fill {{ height: 100%; transition: width .4s; }}

.tag {{
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  white-space: nowrap;
  text-align: center;
  text-transform: uppercase;
  letter-spacing: 1px;
  border: 1px solid;
  background: transparent;
}}
.tag-strong {{ color: var(--green); border-color: var(--green); }}
.tag-mid    {{ color: var(--cyan);  border-color: var(--cyan); }}
.tag-watch  {{ color: var(--amber); border-color: var(--amber); }}

/* Stock expand */
.stock-expand {{
  background: var(--bg-panel);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  padding: 14px 16px 14px 56px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  animation: expandIn .15s ease;
}}
@keyframes expandIn {{ from{{opacity:0;transform:translateY(-4px)}} to{{opacity:1;transform:translateY(0)}} }}
.stock-chip {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-void);
  border: 1px solid var(--border);
  padding: 5px 10px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-1);
  text-decoration: none;
  transition: border-color .15s, background .15s;
  cursor: pointer;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}}
.stock-chip:hover {{ border-color: var(--text-1); background: var(--bg-hover); }}
.stock-chip .code {{ color: var(--text-1); font-weight: 600; }}
.stock-chip .name {{ color: var(--text-2); font-size: 11px; font-family: var(--font-body); }}
.stock-chip .rt-yest {{ opacity: 0.85; font-weight: 600; }}
.stock-chip .rt-net {{ font-weight: 600; opacity: 0.95; }}
.stock-chip .rt-today {{ font-weight: 700; }}

.pos-bar {{ display: flex; align-items: center; gap: 5px; justify-content: flex-end; }}
.pos-track {{ width: 36px; height: 3px; background: var(--bg-panel); border: 1px solid var(--border); overflow: hidden; }}
.pos-fill {{ height: 100%; }}

/* ─── INTEL TAB (莫蘭迪統一配色) ─── */
.intel-card {{
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-left-width: 3px;
  padding: 16px;
  margin-bottom: 16px;
}}
.intel-card-hdr {{ display: flex; align-items: center; gap: 10px; margin-bottom: 8px; flex-wrap: wrap; }}
.intel-badge {{
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .5px;
  font-family: var(--font-mono);
}}
.intel-count {{
  margin-left: auto;
  font-size: 11px;
  font-weight: 600;
  font-family: var(--font-mono);
}}
.intel-interp {{ color: var(--text-2); font-size: 12px; margin-bottom: 10px; line-height: 1.5; }}
.intel-advice {{
  background: var(--bg-hover);
  border: 1px solid var(--border);
  padding: 8px 12px;
  font-size: 12px;
  margin-bottom: 12px;
  line-height: 1.5;
}}
.intel-list {{ border: 1px solid var(--border); overflow: hidden; }}
.intel-list-hdr {{
  display: grid;
  grid-template-columns: 1fr 72px 72px 56px;
  gap: 8px;
  padding: 6px 16px;
  background: var(--bg-void);
  border-bottom: 1px solid var(--border);
  font-size: 10px;
  color: var(--text-3);
  text-transform: uppercase;
  letter-spacing: .5px;
  font-family: var(--font-mono);
}}
.intel-row {{
  display: grid;
  grid-template-columns: 1fr 72px 72px 56px;
  gap: 8px;
  align-items: center;
  padding: 10px 16px;
  cursor: pointer;
  border-bottom: 1px solid var(--border);
  transition: background .15s;
}}
.intel-row:last-child {{ border-bottom: none; }}
.intel-row:hover {{ background: var(--bg-hover); }}
.intel-expand {{
  background: var(--bg-panel);
  border-left: 3px solid var(--border-b);
  border-bottom: 1px solid var(--border);
  padding: 10px 16px 10px 40px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  animation: expandIn .15s ease;
}}

/* ─── FOOTER ──────────────────── */
.site-footer {{
  text-align: center;
  padding: 16px;
  font-size: 11px;
  color: var(--text-3);
  border-top: 1px solid var(--border);
  font-family: var(--font-mono);
}}

/* ─── RESPONSIVE ─────────────── */
@media (max-width: 900px) {{
  .layout {{ grid-template-columns: 1fr; }}
  .sidebar {{ display: none; }}
  .ticker-dashboard {{ grid-template-columns: repeat(2, 1fr); padding: 12px 16px; }}
  .ticker-price {{ font-size: 22px; }}
  .cp-cols {{ grid-template-columns: 28px 1fr 60px 70px 80px 56px; }}
  .cp-cols .hide-sm {{ display: none; }}
  .bt-cols {{ grid-template-columns: 28px 1fr 60px 70px 80px 56px; }}
  .tab-panel {{ padding: 20px 16px; }}
  .panel-title {{ font-size: 22px; }}
  .hdr-nav {{ gap: 18px; font-size: 12px; }}
}}
@media (max-width: 600px) {{
  .ticker-dashboard {{ grid-template-columns: 1fr 1fr; }}
  .ticker-card:nth-child(2) {{ border-right: none; }}
  .ticker-card:nth-child(3) {{ padding-left: 0; border-right: 1px solid var(--border); }}
  .hdr-toolbar {{ padding: 6px 12px; font-size: 11px; }}
}}
</style>
</head>
<body>

<!-- HEADER -->
<header class="hdr">
  <div class="hdr-toolbar">
    <div class="hdr-toolbar-left">
      <span class="hdr-brand-mini">板塊週報 · The Sector Times</span>
      <span class="hdr-toolbar-date" id="hdr-date">—</span>
      <span id="hdr-update" style="color:var(--text-3)">—</span>
    </div>
    <div class="hdr-toolbar-right">
      <span id="mkt-warn" style="display:none" class="hdr-warn">⚠ 大盤下殺</span>
    </div>
  </div>

  <div class="ticker-dashboard">
    <div class="ticker-card" data-watch="TAIEX">
      <div class="ticker-label">大盤 加權指數</div>
      <div class="ticker-row">
        <span class="ticker-price" id="ticker-TAIEX-price">—</span>
        <span class="ticker-chg" id="ticker-TAIEX-chg">—</span>
      </div>
      <div class="ticker-meta" id="ticker-TAIEX-meta">資料載入中…</div>
    </div>
    <div class="ticker-card" data-watch="2330">
      <div class="ticker-label">2330 台積電</div>
      <div class="ticker-row">
        <span class="ticker-price" id="ticker-2330-price">—</span>
        <span class="ticker-chg" id="ticker-2330-chg">—</span>
      </div>
      <div class="ticker-meta" id="ticker-2330-meta">資料載入中…</div>
    </div>
    <div class="ticker-card" data-watch="0050">
      <div class="ticker-label">0050 元大台灣50</div>
      <div class="ticker-row">
        <span class="ticker-price" id="ticker-0050-price">—</span>
        <span class="ticker-chg" id="ticker-0050-chg">—</span>
      </div>
      <div class="ticker-meta" id="ticker-0050-meta">資料載入中…</div>
    </div>
    <div class="ticker-card" data-watch="00631L">
      <div class="ticker-label">00631L 元大台灣50正2</div>
      <div class="ticker-row">
        <span class="ticker-price" id="ticker-00631L-price">—</span>
        <span class="ticker-chg" id="ticker-00631L-chg">—</span>
      </div>
      <div class="ticker-meta" id="ticker-00631L-meta">資料載入中…</div>
    </div>
  </div>

  <div class="rt-banner" id="rt-banner">
    <span class="label-tag">編輯部簡訊</span>
    即時報價載入中…
  </div>

  <nav class="hdr-nav">
    <span class="hdr-nav-item active" onclick="switchTab('cp')">CP値排行</span>
    <span class="hdr-nav-item" onclick="switchTab('bottom')">抄底偵測</span>
    <span class="hdr-nav-item" onclick="switchTab('intel')">智慧建議</span>
  </nav>
</header>

<!-- LAYOUT -->
<div class="layout">
  <!-- SIDEBAR -->
  <aside class="sidebar">
    <div class="sb-section-title">板塊概況</div>
    <div class="stat-card stat-amber">
      <div class="stat-num" id="sb-main">—</div>
      <div class="stat-label">主力進場（今日淨買 &gt;10億）</div>
    </div>
    <div class="stat-card stat-cyan">
      <div class="stat-num" id="sb-bottom">—</div>
      <div class="stat-label">抄底偵測板塊</div>
    </div>
    <div class="stat-card stat-red">
      <div class="stat-num" id="sb-out">—</div>
      <div class="stat-label">退潮（今日淨賣 &gt;20億）</div>
    </div>
    <div class="stat-card" style="border-color:var(--border)">
      <div class="stat-num" id="sb-mkt" style="color:var(--text-2);font-size:26px">—</div>
      <div class="stat-label">大盤今日漲跌</div>
    </div>
    <div class="sb-divider"></div>
    <div class="sb-section-title">抄底快訊 TOP 3</div>
    <div class="bottom-mini" id="bottom-mini"></div>
  </aside>

  <!-- MAIN -->
  <main class="main">
    <!-- CP PANEL -->
    <div class="tab-panel active" id="panel-cp">
      <div class="panel-hdr">
        <div class="panel-title">CP 値排行 — 主力佈局未發動之板塊</div>
        <div class="panel-desc">
          資金大量流入但漲幅仍低的板塊——代表主力已佈局但股價還沒反應<br>
          <span class="hi">CP值 = 5日法人淨買超(億) ÷ (|5日漲跌幅| + 1)</span>，越高代表吸籌性價比越高
        </div>
      </div>
      <div class="tbl-wrap">
        <div class="tbl-head cp-cols">
          <span></span>
          <span>板塊</span>
          <span style="text-align:right">5日漲跌</span>
          <span style="text-align:right">5日淨買(億)</span>
          <span style="text-align:right" class="hide-sm">條形</span>
          <span style="text-align:right" class="hide-sm">20日淨買</span>
          <span style="text-align:right">位置</span>
          <span style="text-align:right">CP值</span>
        </div>
        <div id="cp-body"></div>
      </div>
    </div>

    <!-- BOTTOM PANEL -->
    <div class="tab-panel" id="panel-bottom">
      <div class="panel-hdr">
        <div class="panel-title">抄底偵測 — 法人逆勢進場之板塊</div>
        <div class="panel-desc">
          大盤下跌時，這些板塊被法人悄悄買入——抄底力道由強到弱<br>
          <span class="hi">bottom_score 越高 = 今日跌幅深但法人淨買越強</span>
        </div>
      </div>
      <div class="tbl-wrap">
        <div class="tbl-head bt-cols">
          <span></span>
          <span>板塊</span>
          <span style="text-align:right">今日漲跌</span>
          <span style="text-align:right">今日淨買(億)</span>
          <span style="text-align:right">強度條</span>
          <span style="text-align:right">底部分數</span>
          <span style="text-align:right">信號</span>
        </div>
        <div id="bottom-body"></div>
      </div>
    </div>

    <!-- INTEL PANEL -->
    <div class="tab-panel" id="panel-intel">
      <div id="tab-intel-content"></div>
    </div>
  </main>
</div>

<footer class="site-footer">
  以上分析基於法人淨買資料自動識別情境，不構成投資建議。<br>
  資料來源：TWSE / TPEx / sectorrotation · 每日台灣時間 18:00 自動更新
</footer>

<script>
// ─── DATA ────────────────────────────────────────────────────────
window.STOCK_NAMES = ''' + stock_names_min + ''';
window.FALLBACK_DATA = ''' + fallback_min + ''';

// ─── CONFIG ──────────────────────────────────────────────────────
const DATA_URL = './data/latest.json';
const TWSE_API = 'https://mis.twse.com.tw/stock/api/getStockInfo.jsp';

// ─── UTILS ───────────────────────────────────────────────────────
function fmtYi(v, digits=1) {
  if (v==null) return '—';
  return (v>0?'+':'')+v.toFixed(digits)+'億';
}
function fmtPct(v, digits=1) {
  if (v==null) return '—';
  return (v>0?'+':'')+v.toFixed(digits)+'%';
}
function colorNum(v) { return v>0.05?'pos':v<-0.05?'neg':'neu'; }

function posHtml(pos) {
  const w = Math.min(100, pos);
  const c = pos<40 ? 'var(--green)' : pos>65 ? 'var(--red)' : 'var(--amber)';
  return `<div class="pos-bar"><div class="pos-track"><div class="pos-fill" style="width:${{w}}%;background:${{c}}"></div></div><span class="cell-num" style="color:${{c}};font-size:11px">${{pos.toFixed(0)}}</span></div>`;
}

function tvUrl(code) {
  const exchange = (window.STOCK_EXCHANGE && window.STOCK_EXCHANGE[code]) || 'TWSE';
  return 'https://tw.tradingview.com/chart/?symbol=' + exchange + '%3A' + code;
}

// ─── EXPAND STOCKS ───────────────────────────────────────────────
function toggleStockExpand(rowEl, sector, data) {
  const next = rowEl.nextElementSibling;
  const chev = rowEl.querySelector('.chevron');
  if (next && next.classList.contains('stock-expand')) {
    next.remove();
    chev.classList.remove('open');
    rowEl.classList.remove('expanded');
    return;
  }
  chev.classList.add('open');
  rowEl.classList.add('expanded');

  const div = document.createElement('div');
  div.className = 'stock-expand';

  sector.stocks.forEach(code => {
    const sd = data.stock_data[code];
    const rt = window.REALTIME_QUOTES && window.REALTIME_QUOTES[code];
    const name = window.STOCK_NAMES[code] || '';
    const a = document.createElement('a');
    a.className = 'stock-chip';
    a.href = tvUrl(code);
    a.target = '_blank';
    a.rel = 'noopener';

    let inner = `<span class="code">${{code}}</span>`;
    if (name) inner += `<span class="name">${{name}}</span>`;
    if (sd) {
      inner += `<span class="rt-yest ${{colorNum(sd.chg_1d)}}" title="昨日漲跌">${{fmtPct(sd.chg_1d)}}</span>`;
      inner += `<span class="rt-net ${{colorNum(sd.net_1d_yi)}}" title="昨日法人淨買">${{fmtYi(sd.net_1d_yi)}}</span>`;
    }
    if (rt && rt.chg_pct != null && (rt.chg_pct !== 0 || rt.last > 0)) {
      inner += `<span class="rt-today ${{colorNum(rt.chg_pct)}}" title="今日即時">⚡${{fmtPct(rt.chg_pct)}}</span>`;
    }
    a.innerHTML = inner;
    div.appendChild(a);
  });

  rowEl.insertAdjacentElement('afterend', div);
}

// ─── REALTIME QUOTES (TWSE) — graceful degradation ───────────────
window.STOCK_EXCHANGE = {{}};
window.REALTIME_QUOTES = {{}};

async function fetchRealtimeQuotes(codes) {
  const BATCH = 80;
  const out = {{}};
  for (let i = 0; i < codes.length; i += BATCH) {
    const slice = codes.slice(i, i+BATCH);
    const tseCh = slice.map(c => 'tse_'+c+'.tw').join('|');
    try {
      const r1 = await fetch(TWSE_API + '?ex_ch=' + encodeURIComponent(tseCh) + '&json=1&delay=0&_=' + Date.now());
      const d1 = await r1.json();
      const found = new Set();
      (d1.msgArray || []).forEach(m => {
        const code = m.c;
        if (!code) return;
        const last = parseFloat(m.z);
        const yest = parseFloat(m.y);
        if (!isNaN(last) && !isNaN(yest) && yest > 0) {
          out[code] = {{ last, yest, chg_pct: (last - yest) / yest * 100 }};
          window.STOCK_EXCHANGE[code] = 'TWSE';
          found.add(code);
        }
      }});
      const missing = slice.filter(c => !found.has(c));
      if (missing.length > 0) {
        const otcCh = missing.map(c => 'otc_'+c+'.tw').join('|');
        const r2 = await fetch(TWSE_API + '?ex_ch=' + encodeURIComponent(otcCh) + '&json=1&delay=0&_=' + Date.now());
        const d2 = await r2.json();
        (d2.msgArray || []).forEach(m => {
          const code = m.c;
          if (!code) return;
          const last = parseFloat(m.z);
          const yest = parseFloat(m.y);
          if (!isNaN(last) && !isNaN(yest) && yest > 0) {
            out[code] = {{ last, yest, chg_pct: (last - yest) / yest * 100 }};
            window.STOCK_EXCHANGE[code] = 'TPEX';
          }
        }});
      }
    } catch(e) {
      console.warn('Realtime batch failed (CORS expected on non-local):', e.message);
    }
  }
  return out;
}

// Ticker dashboard (uses static data if TWSE CORS blocked)
async function loadTickers() {
  const tickers = [
    {{ id: 'TAIEX',  ch: 'tse_t00.tw' }},
    {{ id: '2330',   ch: 'tse_2330.tw' }},
    {{ id: '0050',   ch: 'tse_0050.tw' }},
    {{ id: '00631L', ch: 'tse_00631L.tw' }},
  ];

  // Try live TWSE first
  try {
    const ch = tickers.map(t => t.ch).join('|');
    const r = await fetch(TWSE_API + '?ex_ch=' + encodeURIComponent(ch) + '&json=1&delay=0&_=' + Date.now());
    const d = await r.json();
    const map = {{}};
    (d.msgArray || []).forEach(m => {{ if (m.c) map[m.c] = m; }});
    if (map['t00']) map['TAIEX'] = map['t00'];

    let anyValid = false;
    tickers.forEach(t => {
      const m = map[t.id];
      if (!m) return;
      const last = parseFloat(m.z);
      const yest = parseFloat(m.y);
      if (isNaN(last) || isNaN(yest) || yest <= 0) return;
      anyValid = true;
      const chgPct = (last - yest) / yest * 100;
      const chgVal = last - yest;
      const cls = chgPct > 0.01 ? 'pos' : chgPct < -0.01 ? 'neg' : 'neu';
      const priceEl = document.getElementById('ticker-'+t.id+'-price');
      const chgEl   = document.getElementById('ticker-'+t.id+'-chg');
      const metaEl  = document.getElementById('ticker-'+t.id+'-meta');
      if (priceEl) {{ priceEl.textContent = last.toFixed(2); priceEl.className = 'ticker-price ' + cls; }}
      if (chgEl) {{
        const arrow = chgPct > 0 ? '▲' : chgPct < 0 ? '▼' : '─';
        chgEl.className = 'ticker-chg ' + cls;
        chgEl.textContent = `${{arrow}} ${{chgVal>=0?'+':''}}${{chgVal.toFixed(2)}}  (${{chgPct>=0?'+':''}}${{chgPct.toFixed(2)}}%)`;
      }}
      if (metaEl) {{
        const vol = parseInt(m.v) || 0;
        const time = m.t || '';
        metaEl.textContent = [time, vol > 0 ? `量 ${{vol.toLocaleString()}}` : ''].filter(Boolean).join('  ·  ') || '即時';
      }}
    }});
    if (anyValid) return; // success
  } catch(e) {
    console.warn('Live ticker failed (CORS), falling back to static data');
  }

  // Fallback: use static tickers from latest.json
  loadTickersFromStatic();
}

function loadTickersFromStatic() {
  const data = window.SECTOR_DATA;
  if (!data || !data.tickers) {
    document.querySelectorAll('.ticker-meta').forEach(el => el.textContent = '離線模式');
    return;
  }
  const tickerMap = data.tickers;
  ['TAIEX','2330','0050','00631L'].forEach(id => {
    const t = tickerMap[id];
    if (!t) return;
    const cls = t.chg_pct > 0.01 ? 'pos' : t.chg_pct < -0.01 ? 'neg' : 'neu';
    const priceEl = document.getElementById('ticker-'+id+'-price');
    const chgEl   = document.getElementById('ticker-'+id+'-chg');
    const metaEl  = document.getElementById('ticker-'+id+'-meta');
    if (priceEl) {{ priceEl.textContent = t.close.toFixed(2); priceEl.className = 'ticker-price ' + cls; }}
    if (chgEl) {{
      const arrow = t.chg_pct > 0 ? '▲' : t.chg_pct < 0 ? '▼' : '─';
      chgEl.className = 'ticker-chg ' + cls;
      chgEl.textContent = `${{arrow}} ${{t.change>=0?'+':''}}${{t.change.toFixed(2)}}  (${{t.chg_pct>=0?'+':''}}${{t.chg_pct.toFixed(2)}}%)`;
    }}
    if (metaEl) metaEl.textContent = '收盤 · ' + (data.date || '');
  }});
}

async function loadRealtime() {
  if (!window.SECTOR_DATA) return;
  const allCodes = new Set();
  window.SECTOR_DATA.sectors.forEach(s => s.stocks.forEach(c => allCodes.add(c)));
  const codes = Array.from(allCodes);
  const banner = document.getElementById('rt-banner');

  try {
    const quotes = await fetchRealtimeQuotes(codes);
    window.REALTIME_QUOTES = quotes;
    const found = Object.keys(quotes).length;

    if (found === 0) {
      if (banner) banner.innerHTML = '<span class="label-tag">離線模式</span>顯示最近一日收盤資料（TWSE 即時報價僅限交易時段）';
      return;
    }

    const bottomSectors = window.SECTOR_DATA.sectors.filter(s => s.is_bottom_fishing);
    let totalStocks = 0, upCount = 0, sumChg = 0;
    bottomSectors.forEach(s => {
      s.stocks.forEach(c => {
        const q = quotes[c];
        if (q && !isNaN(q.chg_pct)) {
          totalStocks++;
          if (q.chg_pct > 0) upCount++;
          sumChg += q.chg_pct;
        }
      });
    });
    const winRate = totalStocks > 0 ? (upCount/totalStocks*100).toFixed(0) : '—';
    const avgChg = totalStocks > 0 ? (sumChg/totalStocks).toFixed(2) : '—';

    if (banner) {
      const cls = totalStocks > 0 && sumChg > 0 ? 'pos' : 'neg';
      banner.innerHTML = `⚡ 即時 ${{found}}/${{codes.length}} 檔　|　昨抄底訊號驗證：勝率 <span class="${{cls}}">${{winRate}}%</span>　平均 <span class="${{cls}}">${{avgChg>=0?'+':''}}${{avgChg}}%</span>`;
    }
  } catch(e) {
    if (banner) banner.innerHTML = '<span class="label-tag">離線模式</span>顯示最近一日收盤資料';
  }
}

// ─── RENDER CP TABLE ─────────────────────────────────────────────
function renderCP(data) {
  const sectors = data.sectors;
  const cpList = sectors
    .filter(s => s.net_5d_yi > 0)
    .map(s => ({{...s, cp: s.net_5d_yi / (Math.abs(s.chg_5d)+1)}}))
    .sort((a,b) => b.cp - a.cp);

  const maxNet5 = Math.max(...cpList.map(s=>s.net_5d_yi));
  const body = document.getElementById('cp-body');
  body.innerHTML = '';

  cpList.forEach((s, i) => {
    const row = document.createElement('div');
    row.className = 'tbl-row cp-cols';
    const rankCls = i===0?'r1':i===1?'r2':i===2?'r3':'';
    const w = maxNet5>0 ? Math.min(100, s.net_5d_yi/maxNet5*100) : 0;

    row.innerHTML = `
      <div class="rank-num ${{rankCls}}">${{i+1}}</div>
      <div class="sec-name">
        <span class="chevron">▶</span>
        <span class="sec-label">${{s.name}}</span>
      </div>
      <div class="cell-num ${{colorNum(s.chg_5d)}}">${{fmtPct(s.chg_5d)}}</div>
      <div class="cell-num ${{colorNum(s.net_5d_yi)}}">${{fmtYi(s.net_5d_yi)}}</div>
      <div class="bar-wrap hide-sm"><div class="bar-bg" style="width:88px"><div class="bar-fill" style="width:${{w}}%;background:var(--cyan)"></div></div></div>
      <div class="cell-num ${{colorNum(s.net_20d_yi)}} hide-sm">${{fmtYi(s.net_20d_yi)}}</div>
      ${{posHtml(s.position)}}
      <div class="cell-num" style="color:var(--cyan);font-family:var(--font-head);font-weight:700">${{s.cp.toFixed(1)}}</div>
    `;
    row.addEventListener('click', () => toggleStockExpand(row, s, data));
    body.appendChild(row);
  }});
}

// ─── RENDER BOTTOM TABLE ─────────────────────────────────────────
function renderBottom(data) {
  const list = data.sectors
    .filter(s => s.is_bottom_fishing)
    .sort((a,b) => b.bottom_score - a.bottom_score);

  const maxScore = list.length > 0 ? list[0].bottom_score : 1;
  const body = document.getElementById('bottom-body');
  body.innerHTML = '';

  list.forEach((s, i) => {
    const row = document.createElement('div');
    row.className = 'tbl-row bt-cols';
    const rankCls = i===0?'r1':i===1?'r2':i===2?'r3':'';
    const w = maxScore>0 ? Math.min(100, s.bottom_score/maxScore*100) : 0;
    const tagCls = s.bottom_score>=100?'tag-strong':s.bottom_score>=50?'tag-mid':'tag-watch';
    const tagTxt = s.bottom_score>=100?'強力抄底':s.bottom_score>=50?'法人進場':'觀察';

    row.innerHTML = `
      <div class="rank-num ${{rankCls}}">${{i+1}}</div>
      <div class="sec-name">
        <span class="chevron">▶</span>
        <span class="sec-label">${{s.name}}</span>
      </div>
      <div class="cell-num ${{colorNum(s.chg_1d)}}">${{fmtPct(s.chg_1d)}}</div>
      <div class="cell-num ${{colorNum(s.net_1d_yi)}}">${{fmtYi(s.net_1d_yi)}}</div>
      <div class="bar-wrap"><div class="bar-bg" style="width:88px"><div class="bar-fill" style="width:${{w}}%;background:var(--amber)"></div></div></div>
      <div class="cell-num" style="color:var(--amber);font-family:var(--font-head);font-weight:700">${{s.bottom_score.toFixed(0)}}</div>
      <div style="display:flex;justify-content:flex-end"><span class="tag ${{tagCls}}">${{tagTxt}}</span></div>
    `;
    row.addEventListener('click', () => toggleStockExpand(row, s, data));
    body.appendChild(row);
  }});
}

// ─── RENDER SIDEBAR ──────────────────────────────────────────────
function renderSidebar(data) {
  const s = data.sectors;
  document.getElementById('sb-main').textContent   = s.filter(x=>x.net_1d_yi>10).length;
  document.getElementById('sb-bottom').textContent = s.filter(x=>x.is_bottom_fishing).length;
  document.getElementById('sb-out').textContent    = s.filter(x=>x.net_1d_yi<-20).length;

  const mkt = data.market_chg_1d;
  const mktEl = document.getElementById('sb-mkt');
  mktEl.textContent = fmtPct(mkt);
  mktEl.style.color = mkt>0 ? 'var(--green)' : mkt<0 ? 'var(--red)' : 'var(--text-2)';

  const top3 = s.filter(x=>x.is_bottom_fishing).sort((a,b)=>b.bottom_score-a.bottom_score).slice(0,3);
  const mini = document.getElementById('bottom-mini');
  mini.innerHTML = top3.map(x => `
    <div class="bm-row" onclick="switchTab('bottom')">
      <div class="bm-name">${{x.name}}</div>
      <div class="bm-stats">
        今日 <span class="${{colorNum(x.net_1d_yi)}}">${{fmtYi(x.net_1d_yi)}}</span>
        &nbsp;分數 <span style="color:var(--amber)">${{x.bottom_score.toFixed(0)}}</span>
      </div>
    </div>
  `).join('');
}

// ─── RENDER HEADER ───────────────────────────────────────────────
function renderHeader(data) {
  const mkt = data.market_chg_1d;
  if (data.is_market_down) document.getElementById('mkt-warn').style.display='';
  document.getElementById('hdr-date').textContent = '資料日期 ' + data.date;
  const upd = new Date(data.updated_at);
  if (!isNaN(upd.getTime())) {
    document.getElementById('hdr-update').textContent =
      '更新 ' + upd.getHours().toString().padStart(2,'0') + ':' + upd.getMinutes().toString().padStart(2,'0');
  }
}

// ─── INTEL TAB (統一莫蘭迪風格) ──────────────────────────────────
function buildIntelTab() {
  const container = document.getElementById('tab-intel-content');
  if (!container) return;
  const data = window.SECTOR_DATA;
  if (!data || !data.sectors) {
    container.innerHTML = '<div style="color:var(--text-3);padding:24px;text-align:center;">資料尚未載入</div>';
    return;
  }
  const sectors = data.sectors;
  const isMarketDown = data.is_market_down;

  const scenarios = [
    { id:'strong-accum', title:'強吸籌', titleEn:'Strong Accumulation', color:'var(--green)',
      interpretation:'主力趁散戶恐慌賣出時吃貨，後市有拉升動能', advice:'可分批建倉，耐心等待啟動',
      match: s => s.net_20d_yi>50 && s.chg_5d<-3 && s.position<60 && (s.net_5d_yi>0||s.net_1d_yi>5),
      metrics: s => [{{label:'20日淨買',value:fmtYi(s.net_20d_yi),pos:s.net_20d_yi>0}},{{label:'5日漲跌',value:fmtPct(s.chg_5d),pos:s.chg_5d>0}},{{label:'位置',value:s.position.toFixed(1)+'%',pos:s.position<50}}]
    }},
    {{ id:'inst-dist', title:'法人反手出貨', titleEn:'Institutional Distribution', color:'var(--red)',
      interpretation:'法人已從主力買方轉為賣方，主升段可能結束', advice:'減倉或空手等，避免接刀',
      match: s => s.net_20d_yi>30 && s.net_5d_yi<-20 && s.position>55 && s.chg_5d<-5,
      metrics: s => [{{label:'20日淨買',value:fmtYi(s.net_20d_yi),pos:s.net_20d_yi>0}},{{label:'5日淨買',value:fmtYi(s.net_5d_yi),pos:s.net_5d_yi>0}},{{label:'5日漲跌',value:fmtPct(s.chg_5d),pos:s.chg_5d>0}}]
    }},
    {{ id:'false-bottom', title:'抄底陷阱', titleEn:'False Bottom / Trap', color:'var(--amber)',
      interpretation:'今日的買入可能只是對沖或空單回補，不是真正的底部進場', advice:'謹慎，不要因為「法人今天買」就以為是底部',
      match: s => isMarketDown===true && s.net_1d_yi>5 && s.net_5d_yi<-30 && s.chg_5d<-8,
      metrics: s => [{{label:'今日淨買',value:fmtYi(s.net_1d_yi),pos:s.net_1d_yi>0}},{{label:'5日淨買',value:fmtYi(s.net_5d_yi),pos:s.net_5d_yi>0}},{{label:'5日漲跌',value:fmtPct(s.chg_5d),pos:s.chg_5d>0}}]
    }},
    {{ id:'high-churn', title:'高位分配', titleEn:'High Position Churning', color:'var(--cyan)',
      interpretation:'主力在高位進行倉位分配，短期難有大突破，可能是出貨前兆', advice:'持有者可設止盈，新資金暫時觀望',
      match: s => s.position>65 && Math.abs(s.net_5d_yi)<15 && Math.abs(s.chg_5d)<3,
      metrics: s => [{{label:'歷史位置',value:s.position.toFixed(1)+'%',pos:s.position<50}},{{label:'5日淨買',value:fmtYi(s.net_5d_yi),pos:s.net_5d_yi>0}},{{label:'5日漲跌',value:fmtPct(s.chg_5d),pos:s.chg_5d>0}}]
    }}
  ];

  function toggleIntelStocks(rowEl, sector, accentColor) {{
    const existing = rowEl.nextElementSibling;
    if (existing && existing.classList.contains('intel-expand')) {{
      existing.remove();
      rowEl.querySelector('.expand-arrow').textContent='›';
      return;
    }}
    rowEl.querySelector('.expand-arrow').textContent='⌄';
    const stockDataMap = data.stock_data||{{}};
    const expandEl = document.createElement('div');
    expandEl.className = 'intel-expand';
    (sector.stocks||[]).forEach(code => {{
      const sd = stockDataMap[code];
      const name = (window.STOCK_NAMES && window.STOCK_NAMES[code]) || '';
      const chip = document.createElement('a');
      chip.className = 'stock-chip';
      chip.href = tvUrl(code);
      chip.target = '_blank';
      chip.rel = 'noopener';
      const chgC = sd ? colorNum(sd.chg_1d) : 'neu';
      const netC = sd ? colorNum(sd.net_1d_yi) : 'neu';
      chip.innerHTML = `<span class="code">${{code}}</span>` +
        (name ? `<span class="name">${{name}}</span>` : '') +
        (sd ? `<span class="rt-yest ${{chgC}}">${{fmtPct(sd.chg_1d)}}</span><span class="rt-net ${{netC}}">${{fmtYi(sd.net_1d_yi)}}</span>` : '');
      expandEl.appendChild(chip);
    }});
    rowEl.insertAdjacentElement('afterend', expandEl);
  }}

  container.innerHTML = '';

  // Top bar
  const topBar = document.createElement('div');
  topBar.style.cssText = 'display:flex;align-items:center;gap:12px;padding:12px 0 16px;border-bottom:3px double var(--border-rule);margin-bottom:16px;flex-wrap:wrap';
  const mktC = data.market_chg_1d;
  const mktPos = typeof mktC==='number' && mktC > 0;
  topBar.innerHTML = `
    <div style="font-family:var(--font-display);font-size:20px;font-weight:900;letter-spacing:-0.3px">智慧建議 · 板塊情境識別</div>
    <div class="cell-num ${{mktPos?'pos':'neg'}}" style="font-size:12px;border:1px solid var(--border);padding:2px 10px">大盤 ${{mktPos?'+':''}}${{typeof mktC==='number'?mktC.toFixed(2):'--'}}%</div>
    <div style="color:var(--text-3);font-size:11px;margin-left:auto;font-family:var(--font-mono)">資料日期：${{data.date||'--'}}</div>
  `;
  container.appendChild(topBar);

  // Cards
  scenarios.forEach(sc => {{
    const matched = sectors.filter(sc.match);
    const card = document.createElement('div');
    card.className = 'intel-card';
    card.style.borderLeftColor = sc.color;

    let html = `<div class="intel-card-hdr">
      <span class="intel-badge" style="background:color-mix(in srgb, ${{sc.color}} 12%, transparent);color:${{sc.color}};border:1px solid color-mix(in srgb, ${{sc.color}} 30%, transparent)">${{sc.title}}</span>
      <span style="color:var(--text-3);font-size:11px;letter-spacing:.5px">${{sc.titleEn}}</span>
      <span class="intel-count" style="color:${{sc.color}}">${{matched.length}} 板塊</span>
    </div>`;
    html += `<div class="intel-interp">解讀：${{sc.interpretation}}</div>`;
    html += `<div class="intel-advice" style="border-left:3px solid ${{sc.color}}"><span style="color:var(--text-3)">操作建議：</span>${{sc.advice}}</div>`;

    if (!matched.length) {{
      html += '<div class="intel-list"><div style="padding:12px 16px;color:var(--text-3);font-size:12px;text-align:center">今日無符合板塊</div></div>';
    }} else {{
      const m0 = sc.metrics(matched[0]);
      html += `<div class="intel-list"><div class="intel-list-hdr"><span>板塊名稱</span><span style="text-align:right">${{m0[0].label}}</span><span style="text-align:right">${{m0[1].label}}</span><span style="text-align:right">位置</span></div>`;
      matched.forEach(s => {{
        const mt = sc.metrics(s);
        const posC = s.position<40?'var(--green)':s.position>65?'var(--red)':'var(--amber)';
        html += `<div class="intel-row" data-sector="${{s.name}}">
          <div style="display:flex;align-items:center;gap:6px;min-width:0"><span class="expand-arrow" style="color:${{sc.color}};font-size:14px;width:14px">›</span><span class="sec-label" style="font-size:13px">${{s.name}}</span></div>
          <div class="cell-num ${{mt[0].pos?'pos':'neg'}}" style="font-size:12px">${{mt[0].value}}</div>
          <div class="cell-num ${{mt[1].pos?'pos':'neg'}}" style="font-size:12px">${{mt[1].value}}</div>
          <div class="cell-num" style="font-size:12px;color:${{posC}}">${{s.position.toFixed(1)}}%</div>
        </div>`;
      }});
      html += '</div>';
    }}

    card.innerHTML = html;
    container.appendChild(card);

    // Bind click events for stock expansion
    card.querySelectorAll('.intel-row').forEach(row => {{
      const sectorName = row.dataset.sector;
      const sector = matched.find(s => s.name === sectorName);
      if (sector) {{
        row.addEventListener('click', () => toggleIntelStocks(row, sector, sc.color));
      }}
    }});
  }});
}

// ─── TAB SWITCH ──────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.hdr-nav-item').forEach(b => b.classList.remove('active'));
  document.getElementById('panel-'+name).classList.add('active');
  const navMap = { cp: 0, bottom: 1, intel: 2 };
  const navItems = document.querySelectorAll('.hdr-nav-item');
  if (navItems[navMap[name]]) navItems[navMap[name]].classList.add('active');
  if (name === 'intel' && !document.getElementById('tab-intel-content').children.length) {
    buildIntelTab();
  }
}

// ─── MAIN INIT ───────────────────────────────────────────────────
async function init() {
  let data;
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 8000);
    const res = await fetch(DATA_URL + '?t=' + Date.now(), { signal: ctrl.signal });
    clearTimeout(timer);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    data = await res.json();
    document.getElementById('hdr-update').textContent += '  ✓ live';
  } catch(e) {
    console.warn('Live fetch failed, using embedded data:', e.message);
    data = window.FALLBACK_DATA;
    document.getElementById('hdr-update').textContent = '資料：內嵌 ' + data.date + ' (⚠ offline)';
  }
  window.SECTOR_DATA = data;
  renderHeader(data);
  renderSidebar(data);
  renderCP(data);
  renderBottom(data);
  loadTickers();
  setInterval(loadTickers, 60000);
  loadRealtime();
}

init();
</script>
</body>
</html>'''

OUT.write_text(html, encoding="utf-8")
print(f"✓ 寫入 {OUT}  ({len(html)} bytes)")
