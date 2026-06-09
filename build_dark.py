#!/usr/bin/env python3
"""
build_dark.py — 從 docs/index.html (莫蘭迪) 產生 docs/dark/index.html (現代 Fintech 暗色)

純色彩 + 字體 + 部分結構替換。所有 JS 邏輯不動。
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "docs" / "index.html"
DST = ROOT / "docs" / "dark" / "index.html"
DST.parent.mkdir(parents=True, exist_ok=True)

src = SRC.read_text(encoding="utf-8")
dst = src

# ─── 色彩替換（順序很重要：先具體再通用）─────────────────────────
# CSS 變數值
color_swaps = [
    # 背景層
    ("#FFFDF8", "#0A0A0B"),   # bg-void → 近黑（非純黑，OLED 友善）
    ("#FAF6ED", "#16181D"),   # bg-panel/card → 微提亮卡片底
    ("#F5EFE0", "#1F2128"),   # bg-hover
    # 邊框
    ("#E0D6BE", "#26282E"),   # border (細邊)
    ("#B8AE96", "#3A3D45"),   # border-b (強調邊)
    ("#1A1A1A", "#4B4E58"),   # border-rule (NYT 黑線 → 中灰)
    # 文字
    ("#121212", "#E8E8EA"),   # text-1 主文字
    ("#5C554A", "#9090A0"),   # text-2 次要
    ("#8A8170", "#5A5A66"),   # text-3 弱化

    # Semantic
    ("#1FAA5F", "#16C784"),   # green (TradingView 綠)
    ("#E63946", "#EA3943"),   # red (微調飽和度)
    ("#C7853E", "#F5A623"),   # amber 警示
    ("#5C7A99", "#5B5BD6"),   # cyan → 紫藍 accent (取代 Bloomberg 琥珀套路)
    ("#9CAB94", "#8B92A8"),   # purple

    # 半透明 dim 版（rgba）
    ("rgba(199,133,62,0.12)", "rgba(245,166,35,0.15)"),
    ("rgba(92,122,153,0.10)", "rgba(91,91,214,0.15)"),
    ("rgba(31,170,95,0.12)",  "rgba(22,199,132,0.15)"),
    ("rgba(230,57,70,0.12)",  "rgba(234,57,67,0.15)"),

    # Sidebar 半透明背景
    ("rgba(232,226,214,0.5)", "rgba(22,24,29,0.6)"),

    # Intel tab 殘留色（dark 主題對應）
    ("#D4CCB8", "#26282E"),   # border in intel
    ("#F2EEE6", "#16181D"),   # expand bg
    ("#EFEBE3", "#1F2128"),   # chip bg
    ("#2A2620", "#E8E8EA"),   # chip text
    # 場景 accent (改為飽和度高的 fintech 色)
    ("#6E8E6A", "#16C784"),   # 強吸籌 → 綠
    ("#A85A4F", "#EA3943"),   # 法人反手出貨 → 紅
    ("#B8826F", "#F5A623"),   # 抄底陷阱 → 琥珀
    ("#7A8896", "#5B5BD6"),   # 高位分配 → 紫藍
    # rgba 對應
    ("110,142,106", "22,199,132"),
    ("168,90,79",   "234,57,67"),
    ("184,130,111", "245,166,35"),
    ("122,136,150", "91,91,214"),
]

for old, new in color_swaps:
    dst = dst.replace(old, new)

# ─── 字體替換 (serif 報紙 → sans-serif 終端) ────────────────────
# Google Fonts 引入
dst = dst.replace(
    "https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400&family=Source+Serif+4:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400&family=UnifrakturMaguntia&family=JetBrains+Mono:wght@400;500;600&family=Noto+Serif+TC:wght@400;500;700;900&display=swap",
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&family=Noto+Sans+TC:wght@400;500;700;900&display=swap"
)

# CSS font 變數
font_swaps = [
    ("'Playfair Display', 'Noto Serif TC', Georgia, serif",
     "'Inter', 'Noto Sans TC', system-ui, -apple-system, sans-serif"),
    ("'Source Serif 4', 'Noto Serif TC', Georgia, serif",
     "'Inter', 'Noto Sans TC', system-ui, -apple-system, sans-serif"),
    ("'UnifrakturMaguntia', 'Noto Serif TC', serif",
     "'Inter', 'Noto Sans TC', system-ui, sans-serif"),
]
for old, new in font_swaps:
    dst = dst.replace(old, new)

# 移除 italic（NYT 編輯腔，不適合終端）
italic_removals = [
    ("font-style: italic;\n  font-size: 12px;\n  color: var(--text-2);\n  line-height: 1.4;",
     "font-size: 12px;\n  color: var(--text-2);\n  line-height: 1.4;"),
    ("font-style: italic;\n  font-size: 14px;\n  color: var(--text-2);\n  line-height: 1.6;",
     "font-size: 14px;\n  color: var(--text-2);\n  line-height: 1.6;"),
    ("font-style: italic;\n  font-size: 13px;\n  color: var(--text-2);\n  text-align: center;",
     "font-size: 13px;\n  color: var(--text-2);\n  text-align: center;"),
    ("font-style: italic;\n  color: var(--text-2);", "color: var(--text-2);"),
    ("font-style: italic; color: var(--text-3); }",  "color: var(--text-3); }"),
]
for old, new in italic_removals:
    dst = dst.replace(old, new)

# 把 NYT 招牌 3px double 邊改為單線（更乾淨）
dst = dst.replace("border-top: 3px double var(--border-rule)",
                  "border-top: 1px solid var(--border-b)")
dst = dst.replace("border-bottom: 3px double var(--border-rule)",
                  "border-bottom: 1px solid var(--border-b)")
dst = dst.replace("3px double var(--border-rule)",
                  "1px solid var(--border-b)")

# letter-spacing 從 2px / 1.5px / 1.2px 收斂為 0.5-0.8px（去除過度報紙感）
dst = re.sub(r"letter-spacing:\s*2px", "letter-spacing: 0.6px", dst)
dst = re.sub(r"letter-spacing:\s*1\.5px", "letter-spacing: 0.5px", dst)
dst = re.sub(r"letter-spacing:\s*1\.2px", "letter-spacing: 0.4px", dst)

# 大數字字重從 900 → 700（更乾淨，不用粗壯襯線那麼誇張）
# 但保留 ticker 主價格的視覺重量

# ─── 加 dark 專屬 polish (在 </style> 前)─────────────────────────
dark_polish = """
/* ─── DARK MODE POLISH ──────────────────────────────────────── */

/* 整體微調 */
html { color-scheme: dark; }
body { background: var(--bg-void); }

/* 細微 box-shadow 取代 NYT 雙線 */
.hdr { box-shadow: 0 1px 0 var(--border); }
.tbl-row:hover { background: var(--bg-hover); transform: none; }

/* 數字加上 monospace tabular */
.cell-num, .ticker-price, .ticker-chg, .stat-num,
.bm-stats, .rt-banner .pos, .rt-banner .neg {
  font-feature-settings: "tnum" 1, "ss01" 1;
}

/* Ticker 主價改用 mono（終端感） */
.ticker-price {
  font-family: 'JetBrains Mono', 'SF Mono', monospace;
  font-weight: 700;
  font-size: 28px;
  letter-spacing: -0.3px;
}

/* sidebar 大數字也改 mono */
.stat-num {
  font-family: 'JetBrains Mono', 'SF Mono', monospace;
  font-weight: 700;
  font-size: 32px;
  letter-spacing: -0.5px;
}

/* 標題用 Inter 800（高權重 sans-serif） */
.panel-title, .hdr-brand-mini, .sec-label, .bm-name {
  font-family: 'Inter', 'Noto Sans TC', sans-serif;
  font-weight: 700;
  letter-spacing: -0.2px;
}
.panel-title { font-weight: 800; letter-spacing: -0.6px; }

/* tab nav 改現代 fintech 風 */
.hdr-nav {
  font-family: 'Inter', 'Noto Sans TC', sans-serif;
  font-weight: 600;
  font-size: 12px;
  letter-spacing: 0.4px;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  padding: 12px 28px;
}
.hdr-nav-item {
  padding: 6px 14px;
  border-radius: 6px;
  transition: background .15s, color .15s;
}
.hdr-nav-item:hover {
  background: var(--bg-hover);
  color: var(--text-1);
}
.hdr-nav-item.active {
  background: var(--bg-hover);
  color: var(--text-1);
}
.hdr-nav-item.active::after { display: none; }

/* tag 改更圓潤的 pill */
.tag {
  border-radius: 4px;
  letter-spacing: 0.3px;
  font-weight: 700;
}

/* tab-panel scrollbar */
.tab-panel::-webkit-scrollbar { width: 8px; }
.tab-panel::-webkit-scrollbar-track { background: transparent; }
.tab-panel::-webkit-scrollbar-thumb { background: var(--border-b); border-radius: 4px; }
.tab-panel::-webkit-scrollbar-thumb:hover { background: #5A5A66; }

/* sidebar scrollbar */
.sidebar::-webkit-scrollbar-thumb { background: var(--border-b); }

/* table head 更緊湊 */
.tbl-head {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.5px;
  color: var(--text-3);
  background: transparent;
}

/* row 加細微 hover lift */
.tbl-row { transition: background .12s; }
.tbl-row:hover { background: var(--bg-hover); }

/* CP 值 / bottom score 突出 */
.cp-cols .cell-num:last-child,
.bt-cols .cell-num:nth-last-child(2) {
  font-weight: 700;
  font-size: 14px;
}

/* Stock chip — 終端風 */
.stock-chip {
  border-radius: 4px;
  background: var(--bg-hover);
  border: 1px solid var(--border);
}
.stock-chip:hover {
  border-color: #5B5BD6;
  background: rgba(91,91,214,0.08);
}
.stock-chip .name {
  font-family: 'Inter', 'Noto Sans TC', sans-serif;
}

/* warning ribbon */
.hdr-warn {
  background: rgba(245,166,35,0.12);
  border-radius: 4px;
}

/* RT banner */
.rt-banner {
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border);
  font-size: 12px;
}
.rt-banner .label-tag {
  background: var(--bg-hover);
  padding: 2px 8px;
  border-radius: 3px;
  border: 1px solid var(--border);
}

/* Theme toggle */
.theme-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border: 1px solid var(--border);
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 600;
  color: var(--text-2);
  text-decoration: none;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  transition: all .15s;
  cursor: pointer;
}
.theme-toggle:hover {
  border-color: #5B5BD6;
  color: #5B5BD6;
  background: rgba(91,91,214,0.08);
}
"""

# 把 polish 注入到 </style> 之前
dst = dst.replace("</style>", dark_polish + "\n</style>", 1)

# ─── 加入 theme toggle 連結 ─────────────────────────────────────
# 把亮色版繼承來的 ◐ Dark 連結移除（暗色版只需要 ☀ Light）
dst = re.sub(
    r'<a href="dark/" class="theme-toggle"[^>]*>◐ Dark</a>\s*\n\s*',
    '',
    dst
)

toggle_html = '<a href="../" class="theme-toggle" title="切換為亮色（莫蘭迪）">☀ Light</a>'

# 在 hdr-toolbar-right 加入按鈕（mkt-warn 之前）
dst = dst.replace(
    '<span id="mkt-warn"',
    toggle_html + '\n      <span id="mkt-warn"',
    1
)

# 更新 DATA_URL 為相對父層
dst = dst.replace("const DATA_URL = 'data/latest.json'",
                  "const DATA_URL = '../data/latest.json'")

# Title
dst = dst.replace(
    "<title>板塊週報 · The Sector Times</title>",
    "<title>Sector Terminal · 板塊終端</title>"
)
dst = dst.replace(
    'name="description" content="台股板塊輪動週報——即時追蹤法人資金流向、CP值排行、抄底偵測與智慧情境建議"',
    'name="description" content="台股板塊終端 · 暗色模式 — 即時法人資金流向"'
)
dst = dst.replace('content="#FFFDF8"', 'content="#0A0A0B"')
# brand 改成 terminal 風
dst = dst.replace(">板塊週報 · The Sector Times<", ">Sector Terminal ▮<")

# 寫入
DST.write_text(dst, encoding="utf-8")
print(f"✓ 暗色版已產生：{DST}  ({len(dst):,} bytes)")
