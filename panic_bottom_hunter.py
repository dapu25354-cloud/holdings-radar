import os
import sys
import pandas as pd
import yfinance as yf
import ta
import json
import time
from datetime import datetime
from diamond_filter import analyze_diamond  # 同層

# 強制 UTF-8 輸出
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# 檔案路徑
# 全系統共用同一張清單(放在 TODOLIST，線上雷達也讀這張，永遠不會不一致)
WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watch_list.json")
CONFIG_FILE = r"C:\Users\admin\Desktop\python_project\python\config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def send_telegram_msg(message):
    # Telegram notifications are completely disabled per user request to avoid notification floods.
    print(f"[Telegram Disabled] Message not sent: {message.replace(chr(10), ' ')}")
    return

def analyze_panic_bottom(df):
    """
    【極限優化版 - 恐慌接刀策略】
    1. Extreme RSI: < 20 (極度恐慌)
    2. Extreme Bias: < -15% (遠離月線)
    3. Volume Confirmation: > 1.8x MA20 (爆量承接)
    4. Price Action: Hammer / Long tail (止跌回升)
    ※ 崩盤時連好股都會摜破季線，所以品質閘門用「季線是否還在上揚」
      (長多結構有沒有壞)，而不是要求站上季線。
    """
    close = df['Close']
    high = df['High']
    low = df['Low']
    open_p = df['Open']
    volume = df['Volume']

    # 1. 計算 RSI & 20MA Bias (均值回歸乖離)
    df['rsi'] = ta.momentum.rsi(close=close, window=14)
    df['ma20'] = close.rolling(window=20).mean()
    df['bias20'] = (close - df['ma20']) / df['ma20'] * 100

    # 品質閘門：季線(60MA)是否還在上揚 → 長多結構沒壞才值得接
    df['ma60'] = close.rolling(window=60).mean()
    df['trend_ok'] = df['ma60'] > df['ma60'].shift(20)

    # 2. Volume Spike (爆量偵測: 成交量是否超過20日平均的1.8倍)
    df['v_ma20'] = volume.rolling(window=20).mean()
    df['is_volume_spike'] = volume > (df['v_ma20'] * 1.8)

    # 3. K 線特徵 (精準槌子線 Hammer Candle)
    # 計算下影線與實體比例
    body = abs(close - open_p)
    lower_shadow = (close.where(close < open_p, open_p)) - low
    df['is_hammer'] = (lower_shadow > (body * 2)) & (close > low)

    # 4. 終極訊號判斷 (Ultimate Signal Logic)
    # 核心：進入超跌區(RSI<25 且 Bias<-12) 且 (看到爆量 或 出現長下影線) 且 今日收盤不破昨日收盤
    #        且 長多結構還沒壞(季線上揚)
    df['panic_signal'] = (df['rsi'] < 25) & \
                         (df['bias20'] < -12) & \
                         (df['is_volume_spike'] | df['is_hammer']) & \
                         (close >= close.shift(1)) & \
                         (df['trend_ok'])

    return df

def run_panic_scan():
    watchlist = load_watchlist()
    if not watchlist:
        print("錯誤: 觀察名單為空。")
        return

    print(f"--- 🌋 啟動【台股崩盤 - 恐慌接刀】極限優化版 掃描 ---")
    print(f"專門對策：夜盤大跌 3000 點、多殺多、極限乖離")
    print("-" * 60)

    results = []

    for item in watchlist:
        symbol = item['symbol']
        name = item['name']
        print(f"掃描中: {symbol} {name}...", end="\r")
        
        try:
            ticker = yf.Ticker(symbol)
            # 抓取 6 個月的歷史數據進行分析
            df = ticker.history(period="6mo")
            if df.empty or len(df) < 20: continue

            df = analyze_panic_bottom(df)
            last = df.iloc[-1]
            
            # 如果符合極限恐慌區域
            if last['rsi'] < 30 or last['bias20'] < -10:
                tech_signal = bool(last['panic_signal'])
                # 崩盤天股價會摜破均線，所以品質只看基本面(fund_ok)，不要求站上年線
                fund_ok = False
                grade = ""
                if tech_signal:
                    dia = analyze_diamond(symbol, name)
                    fund_ok = dia['fund_ok']
                    grade = dia['grade']
                is_signal = tech_signal and fund_ok  # 技術面恐慌 + 基本面是好股，才叫接刀
                pitch = ""
                if is_signal:
                    catch = "爆量有人承接" if last['is_volume_spike'] else "長下影線探底拉回"
                    pitch = (f"{name}殺到RSI{last['rsi']:.0f}、離月線{last['bias20']:.0f}%極限乖離，"
                             f"今天{catch}又收住不破昨低，而且是體質實在的好股→被恐慌錯殺，接刀點到了。")
                results.append({
                    "symbol": symbol, "name": name, "price": float(last['Close']),
                    "rsi": float(last['rsi']), "bias": float(last['bias20']),
                    "volume_spike": "是" if last['is_volume_spike'] else "否",
                    "is_signal": is_signal, "tech_signal": tech_signal,
                    "fund_ok": fund_ok, "grade": grade, "pitch": pitch
                })
            time.sleep(0.4) # 稍微延遲避免頻繁請求
        except: continue

    worth_list = [r for r in results if r['is_signal']]

    print("\n" + "=" * 60)
    if worth_list:
        print("🎯 恐慌接刀訊號(好股被錯殺、值得接):")
        for r in worth_list:
            print(f"\n  ✅ {r['name']} ({r['symbol']})  現價{r['price']:.1f}")
            print(f"     {r['pitch']}")
    else:
        print("🟢 今天沒有值得接刀的恐慌訊號。")
        # 技術面到位但基本面不夠的(鍍金股恐慌)，特別點出來叫她別接
        fake = [r for r in results if r['tech_signal'] and not r['fund_ok']]
        watch = [r for r in results if not r['tech_signal']]
        if fake:
            names = "、".join(f"{r['name']}({r['grade']})" for r in fake)
            print(f"   ({names} 雖然殺出恐慌訊號，但不是體質好的股，接了是接刀不是撿鑽石，別碰)")
        if watch:
            names = "、".join(r['name'] for r in watch)
            print(f"   ({names} 進了觀察區偏弱，但還沒到爆量承接/長下影止跌，先別接)")
        if not fake and not watch:
            print("   沒有標的進入極限恐慌區，市場沒崩、沒刀可接。")
        print("   → 手癢也忍住，接刀要等真的恐慌。")
    print("=" * 60)

if __name__ == "__main__":
    run_panic_scan()
    try:
        input("\n分析完成，按 Enter 鍵關閉視窗...")
    except EOFError:
        pass