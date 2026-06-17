#!/usr/bin/env python3
"""
scrape_all_subsectors.py — 從 MoneyDJ 抓取所有「細產業」板塊定義

策略（反向推導法）：
  1. 從 ZHA.djhtm 產業分類頁面取得完整的「細產業」連結（~1062 個子板塊）
  2. 逐一進入每個細產業頁面，抓取所屬個股代號+名稱
  3. 輸出精細的 sectors_def.json，每個板塊附帶 parent（母板塊）分類

這會讓前端可以顯示到 "MLCC"、"ABF載板"、"晶圓代工" 等精細層級，
而不是只有 "被動元件"、"IC設計" 等粗分類。

輸出：data/sectors_def_detailed.json（精細版，~1000+ 板塊）
      data/sectors_def.json（過濾版，只保留有 ≥2 檔且台股上市/櫃的板塊）

用法：
  python3 scripts/scrape_all_subsectors.py [--min-stocks 2] [--delay 0.3]
"""

import json, time, re, sys, argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
OUT_DETAILED = ROOT / "data" / "sectors_def_detailed.json"
OUT_FILTERED = ROOT / "data" / "sectors_def.json"
OUT_DETAILED.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# ── Phase 1: 從 ZHA 頁面取得全部細產業定義 ────────────────────────
def get_all_subsectors():
    """
    抓取 MoneyDJ ZHA 頁面，提取所有「細產業」連結
    回傳: [{name, code, parent, url}, ...]
    """
    url = "https://www.moneydj.com/z/zh/zha/ZHA.djhtm"
    r = SESSION.get(url, timeout=30)
    r.encoding = "big5"
    soup = BeautifulSoup(r.text, "html.parser")

    # 找到產業分類表格
    target_table = None
    for t in soup.find_all("table"):
        text = t.get_text()
        if "產業分類" in text and "產業別" in text and "細產業" in text:
            target_table = t
            break

    if not target_table:
        raise RuntimeError("找不到產業分類表格")

    rows = target_table.find_all("tr")
    all_subs = []
    seen_codes = set()
    current_main = ""

    for row in rows[2:]:  # 跳過表頭
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        # 第一欄：主產業別
        main_link = cells[0].find("a")
        if main_link:
            current_main = main_link.get_text(strip=True)

        # 第二欄：細產業連結
        sub_links = cells[1].find_all("a")
        for a in sub_links:
            href = a.get("href", "")
            name = a.get_text(strip=True)
            if not name or "zh00.djhtm" not in href:
                continue

            # 解析 code: ?a=C023061
            match = re.search(r"[?&]a=([A-Z]\d+)", href)
            if not match:
                continue
            code = match.group(1)

            if code in seen_codes:
                continue
            seen_codes.add(code)

            # 完整 URL
            if href.startswith("/"):
                full_url = f"https://www.moneydj.com{href}"
            elif href.startswith("http"):
                full_url = href
            else:
                full_url = f"https://www.moneydj.com/z/zh/zha/{href}"

            all_subs.append({
                "name": name,
                "code": code,
                "parent": current_main,
                "url": full_url,
            })

    return all_subs


# ── Phase 2: 進入每個子板塊頁面取得個股清單 ─────────────────────────
def get_subsector_stocks(sub: dict) -> dict:
    """
    從子板塊頁面抓取個股代號和名稱
    回傳: {name, code, parent, stocks: [...], stock_names: {...}}
    """
    url = sub["url"]
    try:
        r = SESSION.get(url, timeout=30)
        r.encoding = "big5"
        soup = BeautifulSoup(r.text, "html.parser")

        stocks = []
        stock_names = {}

        # MoneyDJ 個股連結格式: "2327國巨*" 或 "2330台積電"
        links = soup.find_all("a")
        for a in links:
            text = a.get_text(strip=True)
            # 匹配 4-6 位數字開頭 + 名稱
            match = re.match(r"^(\d{4,6})(.+)$", text)
            if match:
                code = match.group(1)
                name = match.group(2).rstrip("*")  # 去掉 * 號
                if code not in stock_names:
                    stocks.append(code)
                    stock_names[code] = name

        return {
            "name": sub["name"],
            "code": sub["code"],
            "parent": sub["parent"],
            "stocks": stocks,
            "stock_names": stock_names,
        }
    except Exception as e:
        print(f"  ⚠ 抓取失敗 {sub['name']}: {e}", file=sys.stderr)
        return {
            "name": sub["name"],
            "code": sub["code"],
            "parent": sub["parent"],
            "stocks": [],
            "stock_names": {},
        }


def main():
    parser = argparse.ArgumentParser(description="MoneyDJ 全細產業板塊爬蟲")
    parser.add_argument("--min-stocks", type=int, default=2,
                        help="最少幾檔個股才保留（預設 2）")
    parser.add_argument("--delay", type=float, default=0.3,
                        help="每次請求間隔秒數（預設 0.3）")
    parser.add_argument("--workers", type=int, default=3,
                        help="並行 worker 數量（預設 3，不要太高避免被 ban）")
    parser.add_argument("--resume", action="store_true",
                        help="從上次中斷處繼續（讀取 partial 檔）")
    args = parser.parse_args()

    print("=" * 60)
    print("MoneyDJ 全細產業板塊爬蟲（精細版）")
    print("=" * 60)

    # Phase 1: 取得全部子板塊定義
    print("\n[Phase 1] 取得細產業分類列表...")
    subsectors = get_all_subsectors()
    print(f"  → 找到 {len(subsectors)} 個細產業")

    # 支持從中斷恢復
    partial_file = ROOT / "data" / ".scrape_partial.json"
    already_done = {}
    if args.resume and partial_file.exists():
        try:
            already_done = {s["code"]: s for s in json.loads(partial_file.read_text())}
            print(f"  → 恢復模式：已完成 {len(already_done)} 個板塊")
        except Exception:
            pass

    # Phase 2: 逐一取得個股
    print(f"\n[Phase 2] 抓取各細產業個股（delay={args.delay}s, workers={args.workers}）...")
    results = list(already_done.values())
    todo_subs = [s for s in subsectors if s["code"] not in already_done]

    total = len(subsectors)
    done_count = len(already_done)

    # 使用 sequential（保守 rate-limit）
    for i, sub in enumerate(todo_subs):
        result = get_subsector_stocks(sub)
        results.append(result)
        done_count += 1

        stock_count = len(result["stocks"])
        status = f"{stock_count:3d} 檔" if stock_count > 0 else "⚠ 無個股"
        print(f"  [{done_count:4d}/{total}] {sub['parent']:12s} > {sub['name']:20s}: {status}")

        # 每 50 個存一次 partial
        if done_count % 50 == 0:
            partial_file.write_text(json.dumps(results, ensure_ascii=False))

        time.sleep(args.delay)

    # 清除 partial
    if partial_file.exists():
        partial_file.unlink()

    # Phase 3: 整理輸出
    print(f"\n{'=' * 60}")
    print("Phase 3: 整理輸出...")

    # 3a. 完整版（所有板塊，含空的）
    OUT_DETAILED.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"  ✓ 完整版: {OUT_DETAILED} ({len(results)} 個板塊)")

    # 3b. 過濾版（只保留 ≥ min-stocks 的板塊）
    filtered = [s for s in results if len(s["stocks"]) >= args.min_stocks]
    # 按母板塊 + 股票數排序
    filtered.sort(key=lambda x: (x["parent"], -len(x["stocks"])))

    OUT_FILTERED.write_text(json.dumps(filtered, ensure_ascii=False, indent=2))
    print(f"  ✓ 過濾版: {OUT_FILTERED} ({len(filtered)} 個板塊, ≥{args.min_stocks} 檔)")

    # 統計
    total_stocks = sum(len(s["stocks"]) for s in filtered)
    unique_stocks = len(set(code for s in filtered for code in s["stocks"]))
    parents = sorted(set(s["parent"] for s in filtered))

    print(f"\n{'=' * 60}")
    print(f"最終統計:")
    print(f"  板塊數（過濾後）: {len(filtered)}")
    print(f"  母板塊數: {len(parents)}")
    print(f"  個股總數（含重複）: {total_stocks}")
    print(f"  個股總數（不重複）: {unique_stocks}")
    print(f"\n母板塊列表:")
    for p in parents:
        count = len([s for s in filtered if s["parent"] == p])
        print(f"    {p:20s}: {count:3d} 個子板塊")

    # 另存全域名稱對照表
    all_names = {}
    for s in results:
        all_names.update(s.get("stock_names", {}))
    names_file = ROOT / "data" / "stock_names.json"
    names_file.write_text(json.dumps(all_names, ensure_ascii=False, indent=2))
    print(f"\n  ✓ 名稱對照表: {names_file} ({len(all_names)} 筆)")


if __name__ == "__main__":
    main()
