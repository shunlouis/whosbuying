#!/usr/bin/env python3
"""
scrape_resume.py — 從 .scrape_partial.json 續爬剩餘子板塊

讀取 subsectors_catalog.json（完整 1062 子板塊清單），
跳過 .scrape_partial.json 已抓到的 code，繼續爬剩下的，
最後合併輸出 sectors_def.json / sectors_def_detailed.json / stock_names.json。
"""
import json, time, sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("請先安裝 playwright")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CATALOG_F = DATA / "subsectors_catalog.json"
PARTIAL_F = DATA / ".scrape_partial.json"
OUT_DETAILED = DATA / "sectors_def_detailed.json"
OUT_FILTERED = DATA / "sectors_def.json"
NAMES_F = DATA / "stock_names.json"

MIN_STOCKS = 2


def get_stocks_for_subsector(page, sub):
    try:
        page.goto(sub["url"], timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.4)
        return page.evaluate("""
            () => {
                const links = document.querySelectorAll('a');
                const stocks = [];
                const names = {};
                for (const a of links) {
                    const text = a.textContent.trim();
                    const match = text.match(/^(\\d{4,6})(.+)$/);
                    if (match) {
                        const code = match[1];
                        const name = match[2].replace(/\\*$/, '');
                        if (!names[code]) {
                            stocks.push(code);
                            names[code] = name;
                        }
                    }
                }
                return {stocks, names};
            }
        """)
    except Exception as e:
        print(f"  ⚠ 失敗 {sub['name']}: {e}", file=sys.stderr)
        return {"stocks": [], "names": {}}


def main():
    catalog = json.loads(CATALOG_F.read_text())
    print(f"Catalog: {len(catalog)} 個子板塊")

    if PARTIAL_F.exists():
        existing = json.loads(PARTIAL_F.read_text())
        print(f"已抓 (partial): {len(existing)} 個")
    else:
        existing = []

    done_codes = {d["code"] for d in existing}
    todo = [c for c in catalog if c["code"] not in done_codes]
    print(f"待抓: {len(todo)} 個\n")

    results = list(existing)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            locale="zh-TW",
        )
        page = context.new_page()

        total = len(todo)
        for i, sub in enumerate(todo):
            data = get_stocks_for_subsector(page, sub)
            stocks = data["stocks"]
            names = data["names"]
            results.append({
                "name": sub["name"],
                "code": sub["code"],
                "parent": sub["parent"],
                "stocks": stocks,
                "stock_names": names,
            })
            status = f"{len(stocks):3d} 檔" if stocks else "⚠ 無"
            print(f"  [{i+1:4d}/{total}] {sub['parent']:12s} > {sub['name']:18s}: {status}", flush=True)

            # 每 50 筆存一次 partial（比原版更頻繁，降低中斷損失）
            if (i + 1) % 50 == 0:
                PARTIAL_F.write_text(json.dumps(results, ensure_ascii=False))

            time.sleep(0.3)

        browser.close()

    # 輸出
    print(f"\n{'='*60}\n[整理輸出]")
    OUT_DETAILED.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"  ✓ 完整版: {OUT_DETAILED} ({len(results)} 板塊)")

    filtered = [s for s in results if len(s["stocks"]) >= MIN_STOCKS]
    filtered.sort(key=lambda x: (x["parent"], -len(x["stocks"])))
    OUT_FILTERED.write_text(json.dumps(filtered, ensure_ascii=False, indent=2))
    print(f"  ✓ 過濾版: {OUT_FILTERED} ({len(filtered)} 板塊, ≥{MIN_STOCKS} 檔)")

    unique_stocks = len(set(c for s in filtered for c in s["stocks"]))
    parents = sorted(set(s["parent"] for s in filtered))
    print(f"\n統計: {len(filtered)} 有效板塊 / {len(parents)} 母板塊 / {unique_stocks} 不重複個股")

    all_names = {}
    for s in results:
        all_names.update(s.get("stock_names", {}))
    NAMES_F.write_text(json.dumps(all_names, ensure_ascii=False, indent=2))
    print(f"  ✓ 名稱表: {NAMES_F} ({len(all_names)} 筆)")

    if PARTIAL_F.exists():
        PARTIAL_F.unlink()


if __name__ == "__main__":
    main()
