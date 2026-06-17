#!/usr/bin/env python3
"""Filter sectors_def.json to keep only main sectors (>=5 stocks) suitable for institutional tracking"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sectors = json.loads((ROOT / "data" / "sectors_def.json").read_text())

# 需要保留的主要產業大類（從 MoneyDJ 表格第一欄取得的 114 個主分類）
MAIN_SECTORS = {
    "水泥", "食品加工", "大宗物資", "飲料相關", "塑化原料", "塑化製品",
    "化學纖維", "化纖原料", "成衣", "織布業", "工業紡織品", "紡紗",
    "紡織中游", "工具機", "機械零組件", "造船業", "機器人", "產業機械",
    "電力設備", "家電", "電線電纜", "電池材料相關", "化學工業", "橡膠工業",
    "建材", "家居用品", "造紙業", "線材盤元", "條鋼", "不鏽鋼", "合金鋼",
    "非鐵金屬", "貴金屬", "板鋼", "汽車服務相關", "汽機車零組件", "汽車內裝",
    "車用金屬成型", "車輛整車", "車用電子", "面板業", "面板零組件", "LED",
    "被動元件", "電子其他", "電子零件元件", "散熱模組", "IC設計", "IC封裝測試",
    "印刷電路板相關", "顯示器", "光碟片", "網通設備", "手機", "通訊服務",
    "電子通路", "軟體業", "設備儀器商", "IC製造", "分離式元件",
    "INTERNET應用與服務", "INTERNET技術與基礎設施", "數位相機", "電池",
    "消費性電子產品", "光學元件", "半導體化學品", "週邊產品", "光通訊",
    "工業電腦", "穿戴式裝置", "太陽能", "遊戲產業", "手機零組件",
    "封測服務與材料", "電聲產品", "生物辨識相關", "射頻前端晶片",
    "電腦系統業", "傳輸介面", "地產", "營造工程", "基礎建設營運",
    "運輸事業", "旅宿／餐飲", "休閒娛樂", "時尚產業", "金融業", "流通業",
    "無店舖販售", "水資源", "其他公用事業", "醫藥產業", "生物科技",
    "醫療服務", "醫藥流通", "體外診斷用醫材", "診斷與監測用醫材",
    "手術與治療用醫材", "輔助與彌補用醫材", "其他醫療器材", "獸醫相關",
    "農林漁牧", "礦石開採", "航天軍工", "無人機", "石油及天然氣", "電力",
    "煤", "傳播事業", "傳產其他", "製罐業", "運動產業", "服務業",
}

# 過濾：保留主分類 OR 股票數 >= 5
filtered = []
for s in sectors:
    name = s["name"]
    stock_count = len(s["stocks"])
    if name in MAIN_SECTORS and stock_count >= 3:
        filtered.append(s)

# 按股票數排序（大的板塊排前面）
filtered.sort(key=lambda x: len(x["stocks"]), reverse=True)

# 去掉 stock_names 字段（節省空間），保留簡潔格式
output = []
for s in filtered:
    output.append({
        "name": s["name"],
        "stocks": s["stocks"],
        "stock_names": s.get("stock_names", {}),
    })

print(f"篩選結果: {len(output)} 個板塊")
print(f"個股總數（含重複）: {sum(len(s['stocks']) for s in output)}")
unique = len(set(code for s in output for code in s['stocks']))
print(f"個股總數（不重複）: {unique}")
print()
print("板塊列表:")
for s in output:
    print(f"  {s['name']:20s} {len(s['stocks']):4d} 檔")

# 覆寫 sectors_def.json
(ROOT / "data" / "sectors_def.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2)
)
print(f"\n✓ 已更新 {ROOT / 'data' / 'sectors_def.json'}")
