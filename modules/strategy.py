import pandas as pd
import yfinance as yf
import datetime
import os
from modules.telegram_alert import send_telegram_message
from dotenv import load_dotenv
# ✅ .env.local을 우선적으로 로드

# ✅ 환경 변수 로드
load_dotenv(dotenv_path=".env.local")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SEND_ALERT = os.getenv("SEND_ALERT", "False") == "True"

def run_strategy(symbol, start_date, end_date, mode="backtest"):
    print("▶ 데이터 다운로드 시작")
    df = yf.download(symbol, start=start_date, end=end_date, group_by='ticker')
    print("✅ 데이터 다운로드 완료")

    # ✅ 다중 컬럼 방지: 단일 종목의 경우 열 이름 평탄화
    if isinstance(df.columns, pd.MultiIndex):
        df = df[symbol]  # 👉 'Close', 'Open', ... 만 남도록

    print("✅ 컬럼 목록:", df.columns.tolist())

    # 🔍 이동 평균 및 RSI 계산
    if "Close" not in df.columns or "Open" not in df.columns:
        raise KeyError("❌ 'Close' 또는 'Open' 컬럼이 존재하지 않습니다. 다운로드된 데이터 확인 필요")

    df["MA5"] = df["Close"].rolling(window=5).mean()
    df["MA10"] = df["Close"].rolling(window=10).mean()

    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # 🔍 전일 시가/종가 저장 및 양봉 전환 캔들 조건 계산
    df["Prev Close"] = df["Close"].shift(1)
    df["Prev Open"] = df["Open"].shift(1)

    # ✅ Series로 명시적으로 변환하여 오류 방지
    df["Close"] = df["Close"].astype(float)
    df["Open"] = df["Open"].astype(float)
    df["Prev Close"] = df["Prev Close"].astype(float)
    df["Prev Open"] = df["Prev Open"].astype(float)

    bullish_condition = ((df["Close"] > df["Open"]) & (df["Prev Close"] < df["Prev Open"])).astype(bool)
    print("✅ bullish_condition shape:", bullish_condition.shape)
    print("📊 bullish_condition head:")
    print(bullish_condition.head())
    df["Bullish Candle"] = bullish_condition

    print("\n📊 df.head():")
    print(df.head())
    print("\n📊 Bullish Candle head:")
    print(df["Bullish Candle"].head())

    # 🟢 매수 조건: MA 교차 + RSI < 60 + 양봉 전환
    df["Buy"] = (
        (df["MA5"] > df["MA10"]) &
        (df["MA5"].shift(1) <= df["MA10"].shift(1)) &
        (df["RSI"] < 60) &
        (df["Bullish Candle"])
    ).astype(bool)

    # 🔴 매도 조건: MA 역교차
    df["Sell"] = (
        (df["MA5"] < df["MA10"]) &
        (df["MA5"].shift(1) >= df["MA10"].shift(1))
    ).astype(bool)

    if mode == "live":
        latest = df.iloc[-1]
        msg = ""
        if latest["Buy"]:
            msg = f"📈 실시간 매수 시그널: {symbol} @ {latest.name.date()} / 진입가: {latest['Close']:.2f}"
        elif latest["Sell"]:
            msg = f"📉 실시간 매도 시그널: {symbol} @ {latest.name.date()} / 청산가: {latest['Close']:.2f}"
        else:
            msg = f"⏹️ 실시간 조건 불충분: {symbol} @ {latest.name.date()} / 조건 미충족"

        print(msg)

        if SEND_ALERT:
            print(f"🚀 텔레그램 전송 시도 중: {msg}")
            send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)

        return df, pd.DataFrame()  # 👉 실시간 모드에서는 trades_df 반환 없음

    # ✅ 백테스트 처리
    trades = []
    holding = False
    buy_price = 0

    for date, row in df.iterrows():
        buy_signal = bool(row["Buy"]) if not pd.isna(row["Buy"]) else False
        sell_signal = bool(row["Sell"]) if not pd.isna(row["Sell"]) else False

        if not holding and buy_signal:
            buy_price = row["Close"]
            trades.append({
                "Buy Date": date,
                "Buy Price": buy_price,
                "Sell Date": pd.NaT,
                "Sell Price": None,
                "Return (%)": None
            })
            holding = True

            if SEND_ALERT:
                msg = f"🟢 백테스트 매수: {symbol} @ {date.date()} / 진입가: {buy_price:.2f}"
                print(f"🚀 텔레그램 전송 시도 중: {msg}")
                send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)

        elif holding and sell_signal:
            sell_price = row["Close"]
            trades[-1]["Sell Date"] = date
            trades[-1]["Sell Price"] = sell_price
            trades[-1]["Return (%)"] = ((sell_price - buy_price) / buy_price) * 100
            holding = False

            if SEND_ALERT:
                msg = f"🔴 백테스트 매도: {symbol} @ {date.date()} / 청산가: {sell_price:.2f}"
                print(f"🚀 텔레그램 전송 시도 중: {msg}")
                send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)

    trades_df = pd.DataFrame(trades)
    return df, trades_df
