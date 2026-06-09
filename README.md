# The Sector Times · 板塊週報

台股板塊輪動週報——即時追蹤法人資金流向、CP值排行、抄底偵測與智慧情境建議。

## 功能

- **CP 值排行** — 主力資金大量流入但漲幅仍低的板塊
- **抄底偵測** — 大盤下跌時法人逆勢進場的板塊
- **智慧建議** — 四大情境自動識別（強吸籌、法人出貨、抄底陷阱、高位分配）
- **即時報價** — 交易時段即時顯示 TWSE 報價（離線模式使用收盤資料）
- **個股展開** — 點擊板塊可展開成份股，直接連結 TradingView

## 自動更新

GitHub Actions 每日台灣時間 18:00 自動更新資料（`scripts/fetch_data.py`）。

## 技術

- 純前端 HTML/CSS/JS，無框架依賴
- 資料來源：TWSE OpenAPI / TPEx / sectorrotation
- 部署：GitHub Pages（`docs/` 目錄）
- 設計風格：NYT 報紙式 × 莫蘭迪配色

## 本地開發

直接用瀏覽器打開 `docs/index.html` 即可。
