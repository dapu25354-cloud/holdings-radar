"""
法人籌碼 — 外資/投信買賣超 (官方免費資料:證交所TWSE + 櫃買TPEx)
------------------------------------------------------------
讀 watch_list.json 你的持股,抓「最新一個有公布的交易日」的三大法人買賣超,
換算成「張」(=股數/1000),標出外資/投信大買大賣。波段最有用的籌碼面。

資料源:TWSE T86(上市) + TPEx 三大法人(上櫃),皆官方免費、不需帳密/API金鑰。
用法:直接跑=抓最新交易日;帶參數 YYYYMMDD=指定日期(測試用)。
"""
import sys, os, json
from datetime import date, timedelta
import requests

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

H = {'User-Agent': 'Mozilla/5.0'}

def load_codes():
    p = os.path.join(os.path.dirname(__file__), "watch_list.json")
    out = {}
    try:
        with open(p, encoding='utf-8') as f:
            for it in json.load(f):
                code = it['symbol'].split('.')[0]
                out[code] = it['name']
    except Exception:
        pass
    return out

def to_i(s):
    s = str(s).replace(',', '').strip()
    try:
        return int(float(s))
    except Exception:
        return 0

def fetch_twse(d):  # 上市
    url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={d:%Y%m%d}&selectType=ALL&response=json"
    try:
        j = requests.get(url, timeout=20, headers=H).json()
    except Exception:
        return None
    if j.get('stat') != 'OK':
        return None
    out = {}
    for r in j.get('data', []):
        try:
            out[r[0].strip()] = (to_i(r[4]), to_i(r[10]), to_i(r[18]))  # 外資, 投信, 三大法人(股)
        except (IndexError, ValueError, AttributeError):
            continue  # 欄位不足/格式異常的列跳過
    return out

def fetch_tpex(d):  # 上櫃
    roc = f"{d.year-1911}/{d.month:02d}/{d.day:02d}"
    url = f"https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php?l=zh-tw&se=EW&t=D&d={roc}&o=json"
    try:
        j = requests.get(url, timeout=20, headers=H).json()
        tbls = j.get('tables', [])
        if not tbls or not tbls[0].get('data'):
            return {}
        out = {}
        for r in tbls[0]['data']:
            try:
                out[str(r[0]).strip()] = (to_i(r[4]), to_i(r[13]), to_i(r[23]))  # 外資, 投信, 三大法人(股)
            except (IndexError, ValueError, AttributeError):
                continue  # 欄位不足/格式異常的列跳過
        return out
    except Exception:
        return {}

def find_and_fetch():
    start = date.today()
    if len(sys.argv) > 1:  # 指定日期 YYYYMMDD
        s = sys.argv[1]
        start = date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    d = start
    for _ in range(12):  # 往回找最近有資料的交易日
        if d.weekday() < 5:  # 跳過週末
            tw = fetch_twse(d)
            if tw is not None:
                tp = fetch_tpex(d)
                return d, {**tw, **tp}
        d -= timedelta(days=1)
    return None, None

def fmt(lots):
    return f"{lots:+,}"  # 張

def run():
    codes = load_codes()
    if not codes:
        print("讀不到 watch_list.json")
        return
    d, data = find_and_fetch()
    if not data:
        print("抓不到法人資料(可能今天未收盤/未公布,或近期非交易日)。收盤後下午再跑。")
        return

    rows = []
    for code, name in codes.items():
        if code in data:
            f, t, tot = (x // 1000 for x in data[code])  # 股→張
            rows.append((name, code, f, t, tot))
    rows.sort(key=lambda x: x[2], reverse=True)  # 依外資買賣超排序

    print(f"=== 💰 法人籌碼 外資/投信買賣超 | 資料日 {d:%Y/%m/%d} ===")
    print("(單位:張，正=買超 負=賣超，依外資排序)\n")
    print(f"  {'股票':<6}{'外資':>9}{'投信':>8}{'三大法人':>10}")
    print("  " + "-" * 33)
    for name, code, f, t, tot in rows:
        flag = ""
        if f >= 1000: flag = " 🔴外資大買"
        elif f <= -1000: flag = " 🔵外資大賣"
        elif t >= 500: flag = " 🟠投信進"
        print(f"  {name:<6}{fmt(f):>10}{fmt(t):>9}{fmt(tot):>11}{flag}")

    # 一句話重點
    buy = max(rows, key=lambda x: x[2]); sell = min(rows, key=lambda x: x[2])
    inv = max(rows, key=lambda x: x[3])
    print("\n重點:")
    print(f"  • 外資最捧場:{buy[0]}(+{buy[2]:,}張)   最被倒:{sell[0]}({sell[2]:,}張)")
    if inv[3] > 0:
        print(f"  • 投信買最多:{inv[0]}(+{inv[3]:,}張) ← 投信認養常是波段續強訊號")
    print("\n(資料:證交所+櫃買官方免費,非凱基帳密)")

if __name__ == "__main__":
    run()
