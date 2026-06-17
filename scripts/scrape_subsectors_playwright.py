#!/usr/bin/env python3
"""
scrape_subsectors_playwright.py — 使用 Playwright 瀏覽器抓取 MoneyDJ 所有細產業

由於 MoneyDJ 封鎖了 requests 直接請求，此腳本使用 Playwright 瀏覽器自動化。
先裝依賴: pip3 install playwright && python3 -m playwright install chromium

用法: python3 scripts/scrape_subsectors_playwright.py
"""
import json, re, time, sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("請先安裝 playwright: pip3 install playwright && python3 -m playwright install chromium")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
OUT_CATALOG = ROOT / "data" / "subsectors_catalog.json"
OUT_DETAILED = ROOT / "data" / "sectors_def_detailed.json"
OUT_FILTERED = ROOT / "data" / "sectors_def.json"
OUT_CATALOG.parent.mkdir(parents=True, exist_ok=True)

MIN_STOCKS = 2


def get_catalog(page):
    """Phase 1: 從 ZHA 頁面取得所有子板塊的 catalog"""
    print("[Phase 1] 載入 MoneyDJ 產業分類頁面...")
    page.goto("https://www.moneydj.com/z/zh/zha/ZHA.djhtm", timeout=60000)
    page.wait_for_load_state("domcontentloaded")
    time.sleep(2)

    # Extract all sub-sector links via JS
    catalog = page.evaluate("""
        () => {
            const tbl = document.querySelectorAll('table')[1];
            const rows = tbl.querySelectorAll('tr');
            const allSubs = [];
            let currentMain = '';
            const seen = new Set();
            for (let i = 0; i < rows.length; i++) {
                const cells = rows[i].querySelectorAll('td');
                if (cells.length < 2) continue;
                const mainLink = cells[0].querySelector('a');
                if (mainLink) currentMain = mainLink.textContent.trim();
                const subLinks = cells[1].querySelectorAll('a');
                for (const a of subLinks) {
                    const name = a.textContent.trim();
                    const code = new URL(a.href).searchParams.get('a');
                    if (!code || seen.has(code)) continue;
                    seen.add(code);
                    allSubs.push({name, code, parent: currentMain, url: a.href});
                }
            }
            return allSubs;
        }
    """)
    print(f"  → 找到 {len(catalog)} 個細產業")
    return catalog


def get_stocks_for_subsector(page, sub):
    """Phase 2: 進入子板塊頁面取得個股"""
    try:
        page.goto(sub["url"], timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.5)

        stocks_data = page.evaluate("""
            () => {
                const links = document.querySelectorAll('a');
                const stocks = [];
                const names = {};
                for (const a of links) {
                    const text = a.textContent.trim();
                    const match = text.match(/^(\d{4,6})(.+)$/);
                    if (match) {
                        const code = match[1];
                        const name = match[2].replace(/\*$/, '');
                        if (!names[code]) {
                            stocks.push(code);
                            names[code] = name;
                        }
                    }
                }
                return {stocks, names};
            }
        """)
        return stocks_data["stocks"], stocks_data["names"]
    except Exception as e:
        print(f"  ⚠ 失敗 {sub['name']}: {e}", file=sys.stderr)
        return [], {}


def main():
    print("=" * 60)
    print("MoneyDJ 全細產業板塊爬蟲（Playwright 版）")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            locale="zh-TW"
        )
        page = context.new_page()

        # Phase 1
        catalog = get_catalog(page)
        OUT_CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2))
        print(f"  ✓ Catalog 已存: {OUT_CATALOG}")

        # Phase 2: 逐一取得個股
        print(f"\n[Phase 2] 抓取各細產業個股...")
        results = []
        total = len(catalog)

        for i, sub in enumerate(catalog):
            stocks, stock_names = get_stocks_for_subsector(page, sub)
            results.append({
                "name": sub["name"],
                "code": sub["code"],
                "parent": sub["parent"],
                "stocks": stocks,
                "stock_names": stock_names,
            })
            status = f"{len(stocks):3d} 檔" if stocks else "⚠ 無"
            print(f"  [{i+1:4d}/{total}] {sub['parent']:12s} > {sub['name']:18s}: {status}")

            # 每 100 個存一次
            if (i + 1) % 100 == 0:
                partial = ROOT / "data" / ".scrape_partial.json"
                partial.write_text(json.dumps(results, ensure_ascii=False))

            time.sleep(0.3)

        browser.close()

    # Phase 3: 輸出
    print(f"\n{'='*60}")
    print("[Phase 3] 整理輸出...")

    OUT_DETAILED.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"  ✓ 完整版: {OUT_DETAILED} ({len(results)} 板塊)")

    filtered = [s for s in results if len(s["stocks"]) >= MIN_STOCKS]
    filtered.sort(key=lambda x: (x["parent"], -len(x["stocks"])))
    OUT_FILTERED.write_text(json.dumps(filtered, ensure_ascii=False, indent=2))
    print(f"  ✓ 過濾版: {OUT_FILTERED} ({len(filtered)} 板塊, ≥{MIN_STOCKS} 檔)")

    # 統計
    unique_stocks = len(set(c for s in filtered for c in s["stocks"]))
    parents = sorted(set(s["parent"] for s in filtered))
    print(f"\n最終統計:")
    print(f"  有效板塊: {len(filtered)}")
    print(f"  母板塊: {len(parents)}")
    print(f"  不重複個股: {unique_stocks}")

    # 名稱表
    all_names = {}
    for s in results:
        all_names.update(s.get("stock_names", {}))
    names_f = ROOT / "data" / "stock_names.json"
    names_f.write_text(json.dumps(all_names, ensure_ascii=False, indent=2))
    print(f"  ✓ 名稱表: {names_f} ({len(all_names)} 筆)")

    # 清除 partial
    partial = ROOT / "data" / ".scrape_partial.json"
    if partial.exists():
        partial.unlink()


if __name__ == "__main__":
    main()
