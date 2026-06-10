#!/usr/bin/env python3
"""
fetch_data.py — 板塊週報資料管道
每天台灣時間 18:00 由 GitHub Actions 執行
資料來源：
  - sectorrotation.netlify.app/data/latest.json  (板塊定義 + 法人)
  - openapi.twse.com.tw  (上市收盤 + TAIEX)
  - tpex.org.tw openapi   (上櫃收盤)
  - mis.twse (大盤指數)
輸出：docs/data/latest.json, docs/data/signals_history.json
"""

import json, sys, time, logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
OUT  = ROOT / "docs" / "data" / "latest.json"
SIGNALS_FILE = ROOT / "docs" / "data" / "signals_history.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "SectorTimesBot/1.0"}

def fetch(url, timeout=20, retries=3):
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:
            log.warning(f"fetch {url} attempt {i+1} failed: {e}")
            if i < retries - 1:
                time.sleep(3 * (i+1))
    return None

# ── 1. 板塊定義（sectorrotation）──────────────────────────────────
def load_sector_source():
    r = fetch("https://sectorrotation.netlify.app/data/latest.json")
    if not r:
        raise RuntimeError("無法取得 sectorrotation 板塊資料")
    d = r.json()
    log.info(f"板塊來源: date={d.get('date')} sectors={len(d.get('sectors', []))}")
    return d

# ── 2. 上市今日收盤（TWSE STOCK_DAY_ALL）─────────────────────────
def load_twse_close():
    r = fetch("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL")
    if not r:
        return {}
    rows = r.json()
    result = {}
    for row in rows:
        code = row.get("Code", "").strip()
        if not code:
            continue
        try:
            close  = float(row["ClosingPrice"])
            change = float(row["Change"])
            prev   = close - change
            result[code] = {
                "close":  close,
                "change": round(change, 4),
                "chg_pct": round(change / prev * 100, 2) if prev != 0 else 0,
                "high":  float(row.get("HighestPrice", 0) or 0),
                "low":   float(row.get("LowestPrice",  0) or 0),
                "vol":   int(row.get("TradeVolume", 0) or 0),
                "exchange": "TWSE",
            }
        except (ValueError, KeyError, ZeroDivisionError):
            pass
    log.info(f"TWSE 上市: {len(result)} 檔")
    return result

# ── 3. 上櫃今日收盤（TPEx）───────────────────────────────────────
def load_tpex_close():
    r = fetch("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes")
    if not r:
        return {}
    rows = r.json()
    result = {}
    for row in rows:
        code = row.get("SecuritiesCompanyCode", "").strip()
        if not code:
            continue
        try:
            close  = float(row["Close"])
            raw_chg = str(row.get("Change", "0")).strip().replace(",", "")
            change = float(raw_chg) if raw_chg else 0.0
            prev   = close - change
            result[code] = {
                "close":  close,
                "change": round(change, 4),
                "chg_pct": round(change / prev * 100, 2) if prev != 0 else 0,
                "high":  float(row.get("High", 0) or 0),
                "low":   float(row.get("Low",  0) or 0),
                "vol":   0,
                "exchange": "TPEX",
            }
        except (ValueError, KeyError, ZeroDivisionError):
            pass
    log.info(f"TPEx 上櫃: {len(result)} 檔")
    return result

# ── 4. 大盤 + 4 檔 ticker（優先用 mis.twse 即時/收盤）────────────
def load_tickers(twse_close: dict, tpex_close: dict):
    """
    優先策略：mis.twse API（每日盤後 5 秒就有最新收盤，比 STOCK_DAY_ALL 早 1-2 小時）
    Fallback：STOCK_DAY_ALL（盤後 1-2 小時才更新，但有完整 OHLCV）
    """
    tickers = {}
    watch = {
        "TAIEX": ("tse_t00.tw",     "大盤 加權指數"),
        "2330":  ("tse_2330.tw",    "台積電"),
        "0050":  ("tse_0050.tw",    "元大台灣50"),
        "00631L":("tse_00631L.tw",  "元大台灣50正2"),
    }

    # 優先：mis.twse 即時 API
    try:
        ch_param = "|".join([v[0] for v in watch.values()])
        url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={ch_param}&json=1&delay=0"
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        d = r.json()
        mis_map = {}
        for m in d.get("msgArray", []):
            code = m.get("c")
            if not code:
                continue
            # TAIEX 在 mis.twse 是 't00'
            if code == "t00":
                code = "TAIEX"
            try:
                last = float(m["z"]) if m.get("z") and m["z"] != "-" else None
                yest = float(m["y"]) if m.get("y") and m["y"] != "-" else None
                if last is None or yest is None or yest <= 0:
                    continue
                change = last - yest
                tickers[code] = {
                    "name": watch[code][1] if code in watch else code,
                    "close": round(last, 2),
                    "change": round(change, 2),
                    "chg_pct": round(change / yest * 100, 2),
                    "high": float(m["h"]) if m.get("h") and m["h"] != "-" else None,
                    "low":  float(m["l"]) if m.get("l") and m["l"] != "-" else None,
                    "vol":  int(m["v"]) if m.get("v") and m["v"].isdigit() else 0,
                    "exchange": "TWSE",
                    "source": "mis.twse",
                    "data_date": m.get("d", ""),
                }
            except (ValueError, KeyError):
                pass
        log.info(f"mis.twse 取得 {len(tickers)} 檔")
    except Exception as e:
        log.warning(f"mis.twse failed: {e}")

    # Fallback：STOCK_DAY_ALL（盤後完整資料）
    all_close = {**tpex_close, **twse_close}
    for code in ["TAIEX", "2330", "0050", "00631L"]:
        if code in tickers:
            continue  # mis.twse 已有
        if code == "TAIEX":
            # TAIEX 從 MI_INDEX 抓
            r = fetch("https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX")
            if r:
                rows = r.json()
                taiex = next((x for x in rows if "發行量加權" in x.get("指數", "")), None)
                if taiex:
                    try:
                        close  = float(taiex["收盤指數"].replace(",", ""))
                        change = float(taiex["漲跌點數"].replace(",", ""))
                        prev   = close - change
                        tickers["TAIEX"] = {
                            "name": "大盤 加權指數",
                            "close": close,
                            "change": round(change, 2),
                            "chg_pct": round(change / prev * 100, 2) if prev != 0 else 0,
                            "source": "STOCK_DAY_ALL",
                        }
                    except (ValueError, KeyError, ZeroDivisionError):
                        pass
        else:
            data = all_close.get(code)
            if data:
                tickers[code] = {
                    "name": watch[code][1],
                    "close": data["close"],
                    "change": data["change"],
                    "chg_pct": data["chg_pct"],
                    "high": data.get("high"),
                    "low":  data.get("low"),
                    "vol":  data.get("vol"),
                    "exchange": data.get("exchange", "TWSE"),
                    "source": "STOCK_DAY_ALL",
                }

    log.info(f"Tickers final: {[(k, v.get('close'), v.get('source')) for k,v in tickers.items()]}")
    return tickers

# ── 5. 建立「今日有交易」代碼集（過濾下市股）────────────────────
def build_active_set(twse_close: dict, tpex_close: dict) -> set:
    return set(twse_close.keys()) | set(tpex_close.keys())

# ── 6. 整合 stock_data（今日收盤補充昨日法人）───────────────────
def merge_stock_data(src_stock_data: dict, twse_close: dict, tpex_close: dict, active: set) -> dict:
    all_close = {**tpex_close, **twse_close}
    merged = {}
    for code in active:
        today = all_close.get(code, {})
        yest  = src_stock_data.get(code, {})
        merged[code] = {
            # 今日收盤（來自 TWSE/TPEx，6/9 18:00 後已是最新收盤）
            "close":   today.get("close"),
            "chg_pct": today.get("chg_pct"),
            "exchange": today.get("exchange", "TWSE"),
            # 昨日（資料源）的法人
            "chg_1d":    yest.get("chg_1d"),
            "net_1d_yi": yest.get("net_1d_yi"),
        }
    return merged

# ── 7. 過濾板塊（移除下市股、保留有活躍成份股的板塊）────────────
def filter_sectors(sectors: list, active: set) -> list:
    out = []
    for s in sectors:
        stocks = [c for c in s.get("stocks", []) if c in active]
        if not stocks:
            continue  # 整個板塊無活躍成份股 → 跳過
        out.append({**s, "stocks": stocks})
    removed_boards = len(sectors) - len(out)
    if removed_boards:
        log.info(f"過濾掉 {removed_boards} 個全下市板塊")
    return out

# ── 主程式 ────────────────────────────────────────────────────────
def main():
    tw_tz = timezone(timedelta(hours=8))
    now_tw = datetime.now(tw_tz)
    log.info(f"執行時間（台灣）: {now_tw.strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. 板塊來源
    src = load_sector_source()

    # 2. 今日收盤（用於 ticker + 過濾下市 + 補充 stock_data）
    twse_close = load_twse_close()
    tpex_close = load_tpex_close()

    # 如果今天是假日/非交易日，API 會回傳昨天的資料，直接沿用
    is_trading_day = bool(twse_close)
    log.info(f"is_trading_day: {is_trading_day}, 今日日期: {now_tw.strftime('%Y-%m-%d')}")

    # 3. 活躍股票集
    active = build_active_set(twse_close, tpex_close)

    # 4. Ticker
    tickers = load_tickers(twse_close, tpex_close)

    # 5. 整合 stock_data
    merged_stock_data = merge_stock_data(
        src.get("stock_data", {}), twse_close, tpex_close, active
    )

    # 6. 過濾板塊
    sectors = filter_sectors(src.get("sectors", []), active)

    # 7. 精選訊號 — 前3抄底板塊 × 前3法人淨買正股票
    all_close = {**tpex_close, **twse_close}
    today_picks = pick_signals(sectors, src.get("stock_data", {}), all_close)
    log.info(f"今日精選訊號: {len(today_picks)} 檔")

    # 8. 歷史訊號追蹤（讀取 → 更新報酬 → 加入今日 → 寫回）
    signals_history = load_signals_history()
    signals_history = update_signal_returns(signals_history, all_close)
    today_str = now_tw.strftime("%Y-%m-%d")
    if today_picks and is_trading_day:
        signals_history = add_today_signals(signals_history, today_str, today_picks)
    save_signals_history(signals_history)
    log.info(f"訊號歷史: {len(signals_history)} 天")

    # 9. 輸出
    output = {
        "updated_at":  now_tw.strftime("%Y-%m-%dT%H:%M:%S"),
        "date":        now_tw.strftime("%Y-%m-%d"),
        "source_date": src.get("date", ""),
        "is_market_down": src.get("is_market_down", False),
        "market_chg_1d":  src.get("market_chg_1d", 0),
        "tickers":     tickers,
        "sectors":     sectors,
        "stock_data":  merged_stock_data,
        "today_picks": today_picks,
        "signals_history": signals_history[-30:],  # 只傳最近30天給前端
    }

    OUT.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")))
    log.info(f"輸出完成: {OUT}  sectors={len(sectors)}  stocks={len(merged_stock_data)}")


# ── 8. 精選訊號選股邏輯 ───────────────────────────────────────────
def pick_signals(sectors, stock_data, all_close):
    """
    從抄底偵測前3板塊各選前3名股票：
    - 大盤下跌日（market_chg_1d < -1%）才觸發
    - 板塊今日法人淨買 > 0 且今日下跌 → 逆勢買入 = 抄底
    - bottom_score = net_1d_yi × |chg_1d|（買越多、跌越深 = 分數越高）
    - 按 bottom_score 降序取前3板塊
    - 每板塊內選法人淨買 > 0 的股票，按淨買金額降序取前3
    - 記錄進場價（今日收盤）
    """
    # 先計算/確認每個板塊的 bottom_score
    bottom_candidates = []
    for s in sectors:
        # 如果 source 已有 is_bottom_fishing，直接用
        if s.get("is_bottom_fishing"):
            bottom_candidates.append(s)
            continue
        # 否則自己算：今日淨買>0 且 今日下跌
        net = s.get("net_1d_yi", 0) or 0
        chg = s.get("chg_1d", 0) or 0
        if net > 0 and chg < -0.5:
            score = s.get("bottom_score") or round(net * abs(chg), 1)
            s_copy = {**s, "bottom_score": score, "is_bottom_fishing": True}
            bottom_candidates.append(s_copy)

    bottom_candidates.sort(key=lambda s: s.get("bottom_score", 0), reverse=True)
    top3_sectors = bottom_candidates[:3]

    picks = []
    seen_codes = set()
    for sector in top3_sectors:
        candidates = []
        for code in sector.get("stocks", []):
            if code in seen_codes:
                continue  # 已被其他板塊選走
            sd = stock_data.get(code, {})
            net = sd.get("net_1d_yi", 0) or 0
            if net <= 0:
                continue  # 只選法人淨買為正的
            close_data = all_close.get(code, {})
            entry_price = close_data.get("close")
            if not entry_price or entry_price <= 0:
                continue
            candidates.append({
                "code": code,
                "sector": sector.get("name", ""),
                "net_1d_yi": round(net, 2),
                "entry_price": entry_price,
                "exchange": close_data.get("exchange", "TWSE"),
            })
        # 按法人淨買降序取前3
        candidates.sort(key=lambda x: x["net_1d_yi"], reverse=True)
        for c in candidates[:3]:
            picks.append(c)
            seen_codes.add(c["code"])

    return picks


# ── 9. 歷史訊號管理 ──────────────────────────────────────────────
def load_signals_history():
    """讀取歷史訊號檔案"""
    if SIGNALS_FILE.exists():
        try:
            return json.loads(SIGNALS_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return []


def save_signals_history(history):
    """寫入歷史訊號檔案（保留最近60天）"""
    # 只保留最近60天避免無限增長
    history = history[-60:]
    SIGNALS_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=None, separators=(",", ":")))


def add_today_signals(history, date_str, picks):
    """加入今日精選訊號（避免重複）"""
    # 檢查今天是否已存在
    if any(h["date"] == date_str for h in history):
        log.info(f"訊號歷史已有 {date_str}，跳過")
        return history
    entry = {
        "date": date_str,
        "picks": picks,
        "status": "holding",  # holding / settled
        "returns": None,
    }
    history.append(entry)
    return history


def update_signal_returns(history, all_close):
    """
    持倉滿5個交易日（= 7個日曆天）的訊號，計算報酬率
    用今日收盤 vs 進場價
    """
    tw_tz = timezone(timedelta(hours=8))
    today = datetime.now(tw_tz).date()

    for entry in history:
        if entry.get("status") != "holding":
            continue
        try:
            signal_date = datetime.strptime(entry["date"], "%Y-%m-%d").date()
        except (ValueError, KeyError):
            continue
        days_held = (today - signal_date).days
        if days_held < 7:
            continue  # 還沒滿一週

        # 計算每檔報酬
        pick_returns = []
        for pick in entry.get("picks", []):
            code = pick["code"]
            entry_price = pick.get("entry_price", 0)
            if not entry_price or entry_price <= 0:
                continue
            current = all_close.get(code, {}).get("close")
            if current and current > 0:
                ret_pct = round((current - entry_price) / entry_price * 100, 2)
                pick_returns.append({
                    "code": code,
                    "sector": pick.get("sector", ""),
                    "entry_price": entry_price,
                    "exit_price": current,
                    "return_pct": ret_pct,
                })

        if pick_returns:
            avg_return = round(sum(p["return_pct"] for p in pick_returns) / len(pick_returns), 2)
            win_count = sum(1 for p in pick_returns if p["return_pct"] > 0)
            entry["returns"] = {
                "picks": pick_returns,
                "avg_return_pct": avg_return,
                "win_rate": round(win_count / len(pick_returns) * 100, 1),
                "total_picks": len(pick_returns),
                "days_held": days_held,
            }
            entry["status"] = "settled"
            log.info(f"結算 {entry['date']}: avg={avg_return}% win_rate={entry['returns']['win_rate']}%")

    return history

if __name__ == "__main__":
    main()
