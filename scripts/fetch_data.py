#!/usr/bin/env python3
"""
fetch_data.py — 板塊週報資料管道
每天台灣時間 18:00 由 GitHub Actions 執行
資料來源：
  - data/sectors_def.json  (本地板塊定義)
  - twse.com.tw T86        (上市三大法人買賣超)
  - tpex.org.tw            (上櫃三大法人買賣超)
  - openapi.twse.com.tw    (上市收盤 + TAIEX)
  - tpex.org.tw openapi    (上櫃收盤)
  - mis.twse               (大盤指數即時)
  - sectorrotation.netlify.app (fallback 板塊定義更新)
輸出：docs/data/latest.json, docs/data/signals_history.json
"""

import json, sys, time, logging, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
OUT  = ROOT / "docs" / "data" / "latest.json"
SIGNALS_FILE = ROOT / "docs" / "data" / "signals_history.json"
SECTORS_DEF  = ROOT / "data" / "sectors_def.json"
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


def parse_int(s):
    """解析含逗號的數字字串 → int"""
    if not s:
        return 0
    return int(str(s).replace(",", "").strip() or "0")


# ── 1. 板塊定義（本地 JSON，fallback 從 sectorrotation 更新）──────
def load_sectors_def():
    """載入本地板塊定義；若不存在則從 sectorrotation 下載"""
    if SECTORS_DEF.exists():
        try:
            sectors = json.loads(SECTORS_DEF.read_text())
            log.info(f"板塊定義（本地）: {len(sectors)} 個板塊")
            return sectors
        except (json.JSONDecodeError, IOError):
            pass

    # Fallback: 從 sectorrotation 下載
    log.info("本地板塊定義不存在，從 sectorrotation 下載...")
    r = fetch("https://sectorrotation.netlify.app/data/latest.json")
    if not r:
        raise RuntimeError("無法取得板塊定義（本地 + 遠端都失敗）")
    d = r.json()
    sectors = [{"name": s["name"], "stocks": s["stocks"]} for s in d.get("sectors", [])]
    SECTORS_DEF.parent.mkdir(parents=True, exist_ok=True)
    SECTORS_DEF.write_text(json.dumps(sectors, ensure_ascii=False, indent=2))
    log.info(f"板塊定義（遠端）: {len(sectors)} 個板塊，已存入 {SECTORS_DEF}")
    return sectors


# ── 2. 上市今日收盤（TWSE STOCK_DAY_ALL）─────────────────────────
def load_twse_close():
    r = fetch("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL")
    if not r:
        return {}
    try:
        rows = r.json()
    except Exception:
        log.warning("TWSE STOCK_DAY_ALL 回傳非 JSON")
        return {}
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
    try:
        rows = r.json()
    except Exception:
        log.warning("TPEx close 回傳非 JSON")
        return {}
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


# ── 4. 三大法人買賣超 — TWSE T86（上市個股）─────────────────────
def load_twse_institutional():
    """
    從 TWSE T86 抓三大法人個股買賣超（股數）
    回傳: {code: {"foreign": int, "trust": int, "dealer": int, "total": int}}
    單位: 股
    """
    r = fetch("https://www.twse.com.tw/rwd/zh/fund/T86?response=json&selectType=ALL")
    if not r:
        return {}
    try:
        d = r.json()
    except Exception:
        log.warning("TWSE T86 回傳非 JSON")
        return {}
    if d.get("stat") != "OK":
        log.warning(f"TWSE T86 stat={d.get('stat')}")
        return {}

    data = d.get("data", [])
    result = {}
    # fields:
    # [0] 證券代號  [1] 證券名稱
    # [4] 外陸資買賣超股數(不含外資自營商)
    # [10] 投信買賣超股數
    # [11] 自營商買賣超股數(合計)
    # [18] 三大法人買賣超股數
    for row in data:
        code = row[0].strip()
        if not re.match(r"^\d{4,6}$", code):
            continue
        try:
            foreign = parse_int(row[4])
            trust   = parse_int(row[10])
            dealer  = parse_int(row[11])
            total   = parse_int(row[18])
            result[code] = {
                "foreign": foreign,
                "trust":   trust,
                "dealer":  dealer,
                "total":   total,
                "name":    row[1].strip(),
            }
        except (IndexError, ValueError):
            pass
    log.info(f"TWSE 法人: {len(result)} 檔, date={d.get('date')}")
    return result


# ── 5. 三大法人買賣超 — TPEx（上櫃個股）───────────────────────────
def load_tpex_institutional():
    """
    從 TPEx 抓三大法人個股買賣超
    回傳: {code: {"foreign": int, "trust": int, "dealer": int, "total": int}}
    單位: 股
    嘗試今天 → 昨天 → 前天（處理假日/盤前時段）
    """
    tw_tz = timezone(timedelta(hours=8))
    now = datetime.now(tw_tz)

    # 嘗試最近3天（處理週末 + 盤前）
    for offset in range(0, 4):
        target = now - timedelta(days=offset)
        roc_year = target.year - 1911
        date_str = f"{roc_year}/{target.month:02d}/{target.day:02d}"

        r = fetch(f"https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php?l=zh-tw&o=json&se=EW&t=D&d={date_str}")
        if not r:
            continue

        try:
            d = r.json()
        except Exception:
            continue

        tables = d.get("tables", [])
        if not tables or not isinstance(tables[0], dict):
            continue

        data = tables[0].get("data", [])
        if data:
            log.info(f"TPEx 法人找到資料: date={date_str}")
            break
    else:
        log.warning("TPEx 法人: 最近4天都無資料")
        return {}

    data = tables[0].get("data", [])

    result = {}
    # TPEx 欄位:
    # [0] 代號  [1] 名稱
    # [8:11] = 外資(不含自營商) 買/賣/淨買  → [10] = 外資淨買超
    # [11:14] = 投信 買/賣/淨買             → [13] = 投信淨買超
    # [20:23] = 自營商合計 買/賣/淨買       → [22] = 自營商淨買超
    # [23] = 三大法人合計
    for row in data:
        code = row[0].strip()
        if not re.match(r"^\d{4,6}$", code):
            continue
        try:
            foreign = parse_int(row[10])
            trust   = parse_int(row[13])
            dealer  = parse_int(row[22])
            total   = parse_int(row[23])
            result[code] = {
                "foreign": foreign,
                "trust":   trust,
                "dealer":  dealer,
                "total":   total,
                "name":    row[1].strip(),
            }
        except (IndexError, ValueError):
            pass
    log.info(f"TPEx 法人: {len(result)} 檔, date={date_str}")
    return result


# ── 6. 大盤 + 4 檔 ticker（優先用 mis.twse 即時/收盤）────────────
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
        for m in d.get("msgArray", []):
            code = m.get("c")
            if not code:
                continue
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
            r = fetch("https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX")
            if r:
                try:
                    rows = r.json()
                    taiex = next((x for x in rows if "發行量加權" in x.get("指數", "")), None)
                    if taiex:
                        close  = float(taiex["收盤指數"].replace(",", ""))
                        change = float(taiex["漲跌點數"].replace(",", ""))
                        prev   = close - change
                        tickers["TAIEX"] = {
                            "name": "大盤 加權指數",
                            "close": close,
                            "change": round(change, 2),
                            "chg_pct": round(change / prev * 100, 2) if prev != 0 else 0,
                            "source": "MI_INDEX",
                        }
                except Exception:
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


# ── 7. 建立「今日有交易」代碼集（過濾下市股）────────────────────
def build_active_set(twse_close: dict, tpex_close: dict) -> set:
    return set(twse_close.keys()) | set(tpex_close.keys())


# ── 8. 整合 stock_data（法人 + 收盤 → net_1d_yi）──────────────────
def merge_stock_data(twse_inst: dict, tpex_inst: dict, twse_close: dict, tpex_close: dict, active: set) -> dict:
    """
    用官方 API 法人股數 × 收盤價 = 法人淨買超金額（億）
    同時計算 chg_1d（今日漲跌幅 %）
    """
    all_close = {**tpex_close, **twse_close}
    all_inst  = {**tpex_inst, **twse_inst}
    merged = {}
    for code in active:
        close_data = all_close.get(code, {})
        inst_data  = all_inst.get(code, {})
        close_price = close_data.get("close")
        chg_pct = close_data.get("chg_pct")

        # 計算 net_1d_yi: 三大法人淨買超股數 × 收盤價 / 1e8（億元）
        total_shares = inst_data.get("total", 0)
        if close_price and close_price > 0 and total_shares != 0:
            net_1d_yi = round(total_shares * close_price / 1e8, 2)
        else:
            net_1d_yi = 0

        merged[code] = {
            "close":     close_price,
            "chg_pct":   chg_pct,
            "chg_1d":    chg_pct,  # 與 sectorrotation 相容
            "net_1d_yi": net_1d_yi,
            "exchange":  close_data.get("exchange", "TWSE"),
            # 法人明細（股）
            "foreign_shares": inst_data.get("foreign", 0),
            "trust_shares":   inst_data.get("trust", 0),
            "dealer_shares":  inst_data.get("dealer", 0),
            "total_shares":   total_shares,
        }
    return merged


# ── 9. 計算板塊層級指標 ───────────────────────────────────────────
def calc_sector_metrics(sectors_def: list, stock_data: dict, active: set) -> list:
    """
    計算每個板塊的:
    - net_1d_yi: 板塊所有股票 net_1d_yi 加總
    - chg_1d: 板塊所有股票 chg_1d 平均
    - is_bottom_fishing: 板塊今日淨買>0 且 平均下跌>0.5%
    - bottom_score: net_1d_yi × |chg_1d|
    """
    sectors = []
    for sdef in sectors_def:
        name = sdef["name"]
        stocks = [c for c in sdef["stocks"] if c in active]
        if not stocks:
            continue

        net_total = 0
        chg_list = []
        for code in stocks:
            sd = stock_data.get(code, {})
            net_total += sd.get("net_1d_yi", 0) or 0
            chg = sd.get("chg_1d")
            if chg is not None:
                chg_list.append(chg)

        avg_chg = round(sum(chg_list) / len(chg_list), 2) if chg_list else 0
        net_total = round(net_total, 2)

        # 抄底偵測: 板塊淨買 > 0 且板塊平均下跌
        is_bottom = net_total > 0 and avg_chg < -0.5
        bottom_score = round(net_total * abs(avg_chg), 1) if is_bottom else 0

        sectors.append({
            "name": name,
            "stocks": stocks,
            "net_1d_yi": net_total,
            "chg_1d": avg_chg,
            "is_bottom_fishing": is_bottom,
            "bottom_score": bottom_score,
        })

    return sectors


# ── 10. 精選訊號選股邏輯 ──────────────────────────────────────────
def pick_signals(sectors, stock_data, all_close, market_chg):
    """
    從抄底偵測前3板塊各選前3名股票：
    - 大盤下跌日（market_chg < -1%）才觸發
    - 板塊今日法人淨買 > 0 且今日下跌 → 逆勢買入 = 抄底
    - bottom_score = net_1d_yi × |chg_1d|（買越多、跌越深 = 分數越高）
    - 按 bottom_score 降序取前3板塊
    - 每板塊內選法人淨買 > 0 的股票，按淨買金額降序取前3
    - 記錄進場價（今日收盤）
    """
    if market_chg >= -1.0:
        log.info(f"大盤漲跌 {market_chg}% >= -1%，不觸發抄底訊號")
        return []

    bottom_candidates = [s for s in sectors if s.get("is_bottom_fishing")]
    bottom_candidates.sort(key=lambda s: s.get("bottom_score", 0), reverse=True)
    top3_sectors = bottom_candidates[:3]

    if not top3_sectors:
        log.info("無抄底板塊")
        return []

    picks = []
    seen_codes = set()
    for sector in top3_sectors:
        candidates = []
        for code in sector.get("stocks", []):
            if code in seen_codes:
                continue
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


# ── 11. 歷史訊號管理 ──────────────────────────────────────────────
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
    history = history[-60:]
    SIGNALS_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=None, separators=(",", ":")))


def add_today_signals(history, date_str, picks):
    """加入今日精選訊號（避免重複）"""
    if any(h["date"] == date_str for h in history):
        log.info(f"訊號歷史已有 {date_str}，跳過")
        return history
    entry = {
        "date": date_str,
        "picks": picks,
        "status": "holding",
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
            continue

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


# ── 主程式 ────────────────────────────────────────────────────────
def main():
    tw_tz = timezone(timedelta(hours=8))
    now_tw = datetime.now(tw_tz)
    log.info(f"執行時間（台灣）: {now_tw.strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. 板塊定義（本地）
    sectors_def = load_sectors_def()

    # 2. 今日收盤
    twse_close = load_twse_close()
    tpex_close = load_tpex_close()

    is_trading_day = bool(twse_close)
    log.info(f"is_trading_day: {is_trading_day}, 今日日期: {now_tw.strftime('%Y-%m-%d')}")

    # 3. 三大法人買賣超（官方 API）
    twse_inst = load_twse_institutional()
    tpex_inst = load_tpex_institutional()
    log.info(f"法人資料: TWSE={len(twse_inst)} TPEx={len(tpex_inst)}")

    # 4. 活躍股票集
    active = build_active_set(twse_close, tpex_close)

    # 5. Ticker
    tickers = load_tickers(twse_close, tpex_close)

    # 6. 大盤漲跌
    market_chg = tickers.get("TAIEX", {}).get("chg_pct", 0) or 0

    # 7. 整合 stock_data（法人 × 收盤價 → 金額）
    merged_stock_data = merge_stock_data(twse_inst, tpex_inst, twse_close, tpex_close, active)

    # 8. 計算板塊指標
    sectors = calc_sector_metrics(sectors_def, merged_stock_data, active)
    log.info(f"有效板塊: {len(sectors)}")

    # 9. 精選訊號
    all_close = {**tpex_close, **twse_close}
    today_picks = pick_signals(sectors, merged_stock_data, all_close, market_chg)
    log.info(f"今日精選訊號: {len(today_picks)} 檔")

    # 10. 歷史訊號追蹤
    signals_history = load_signals_history()
    signals_history = update_signal_returns(signals_history, all_close)
    today_str = now_tw.strftime("%Y-%m-%d")
    if today_picks and is_trading_day:
        signals_history = add_today_signals(signals_history, today_str, today_picks)
    save_signals_history(signals_history)
    log.info(f"訊號歷史: {len(signals_history)} 天")

    # 11. 輸出
    output = {
        "updated_at":  now_tw.strftime("%Y-%m-%dT%H:%M:%S"),
        "date":        now_tw.strftime("%Y-%m-%d"),
        "is_market_down": market_chg < -1.0,
        "market_chg_1d":  market_chg,
        "tickers":     tickers,
        "sectors":     sectors,
        "stock_data":  merged_stock_data,
        "today_picks": today_picks,
        "signals_history": signals_history[-30:],
        "data_source": "TWSE/TPEx official API",
    }

    OUT.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")))
    log.info(f"輸出完成: {OUT}  sectors={len(sectors)}  stocks={len(merged_stock_data)}")


if __name__ == "__main__":
    main()
