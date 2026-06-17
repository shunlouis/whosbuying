#!/usr/bin/env python3
"""
scrape_moneydj_sectors.py — 從 MoneyDJ 抓取完整板塊定義

策略：使用主要產業別（如「水泥」「IC設計」）作為板塊，
      進入每個產業頁面獲取所屬個股代號+名稱。
      
輸出：data/sectors_def.json
格式：[{"name": "水泥", "stocks": ["1101", "1102", ...], "stock_names": {"1101": "台泥", ...}}]
"""

import json, time, re, sys
from pathlib import Path
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "sectors_def.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

# Step 1: 取得所有主要產業連結（從 ZHA.djhtm 頁面）
def get_sector_list():
    """抓取 MoneyDJ 產業分類頁面，取得主要產業別和連結"""
    url = "https://www.moneydj.com/Z/ZH/ZHA/ZHA.djhtm"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.encoding = "big5"
    soup = BeautifulSoup(r.text, "html.parser")
    
    # 找到包含產業分類的 table
    tables = soup.find_all("table")
    target_table = None
    for t in tables:
        text = t.get_text()
        if "產業分類" in text and "產業別" in text and "細產業" in text:
            target_table = t
            break
    
    if not target_table:
        raise RuntimeError("找不到產業分類表格")
    
    rows = target_table.find_all("tr")
    sectors = []
    seen_names = set()
    
    for row in rows[2:]:  # 跳過表頭
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        
        # 第一欄是主產業別
        main_link = cells[0].find("a")
        if not main_link:
            continue
        
        name = main_link.get_text(strip=True)
        href = main_link.get("href", "")
        
        # 解析 URL 參數 a=CXXXXXX
        if "zh00.djhtm" not in href:
            continue
        
        # 跳過重複
        if name in seen_names:
            continue
        seen_names.add(name)
        
        # 取得完整 URL
        if href.startswith("/"):
            full_url = f"https://www.moneydj.com{href}"
        elif href.startswith("http"):
            full_url = href
        else:
            full_url = f"https://www.moneydj.com/z/zh/zha/{href}"
        
        sectors.append({"name": name, "url": full_url})
    
    return sectors


# Step 2: 進入每個板塊頁面取得個股清單
def get_sector_stocks(url, sector_name):
    """從板塊頁面抓取個股代號和名稱"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.encoding = "big5"
        soup = BeautifulSoup(r.text, "html.parser")
        
        stocks = []
        stock_names = {}
        
        # 找到股票連結：格式為 "1101台泥"
        links = soup.find_all("a")
        for a in links:
            text = a.get_text(strip=True)
            # 匹配 4-6 位數字開頭 + 名稱
            match = re.match(r"^(\d{4,6})(.+)$", text)
            if match:
                code = match.group(1)
                name = match.group(2)
                if code not in stock_names:  # 避免重複
                    stocks.append(code)
                    stock_names[code] = name
        
        return stocks, stock_names
    except Exception as e:
        print(f"  ⚠ 抓取失敗 {sector_name}: {e}", file=sys.stderr)
        return [], {}


def main():
    print("=" * 60)
    print("MoneyDJ 板塊定義抓取器")
    print("=" * 60)
    
    # Step 1: 取得板塊列表
    print("\n[1/2] 取得產業分類列表...")
    sector_list = get_sector_list()
    print(f"  → 找到 {len(sector_list)} 個主要產業")
    
    # Step 2: 逐一進入板塊頁面取得個股
    print(f"\n[2/2] 抓取各板塊個股...")
    sectors_def = []
    all_stock_names = {}  # 全域股票名稱對照表
    
    for i, sector in enumerate(sector_list):
        name = sector["name"]
        url = sector["url"]
        
        stocks, stock_names = get_sector_stocks(url, name)
        
        if stocks:
            sectors_def.append({
                "name": name,
                "stocks": stocks,
                "stock_names": stock_names,
            })
            all_stock_names.update(stock_names)
            print(f"  [{i+1:3d}/{len(sector_list)}] {name}: {len(stocks)} 檔")
        else:
            print(f"  [{i+1:3d}/{len(sector_list)}] {name}: ⚠ 無個股（跳過）")
        
        # 避免被 rate-limit
        time.sleep(0.3)
    
    # Step 3: 儲存
    print(f"\n{'='*60}")
    print(f"結果統計:")
    print(f"  板塊數: {len(sectors_def)}")
    total_stocks = sum(len(s['stocks']) for s in sectors_def)
    unique_stocks = len(set(code for s in sectors_def for code in s['stocks']))
    print(f"  個股總數（含重複）: {total_stocks}")
    print(f"  個股總數（不重複）: {unique_stocks}")
    
    # 存成和原本相容的格式（保持 stock_names 做額外用途）
    OUT.write_text(json.dumps(sectors_def, ensure_ascii=False, indent=2))
    print(f"\n✓ 已儲存到: {OUT}")
    
    # 另存全域名稱對照表
    names_file = ROOT / "data" / "stock_names.json"
    names_file.write_text(json.dumps(all_stock_names, ensure_ascii=False, indent=2))
    print(f"✓ 名稱對照表: {names_file}")


if __name__ == "__main__":
    main()
