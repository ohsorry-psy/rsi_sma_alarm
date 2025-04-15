import yfinance as yf
import pandas as pd
import os
from dotenv import load_dotenv
from modules.telegram_alert import send_telegram_message

# 🔐 환경 변수 로드
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SEND_ALERT = os.getenv("SEND_ALERT", "False") == "True"

def run_strategy(symbol, start_date, end_date):
    print("▶ 데이터 다운로드 시작")
    df = yf.download(symbol, start=start_date, end=end_date)
    print("✅ 데이터 다운로드 완료")

    # 이동 평균선 계산
    df["MA5"] = df["Close"].rolling(window=5).mean()
    df["MA10"] = df["Close"].rolling(window=10).mean()

    # 매수/매도 시점 포착
    df["Buy"] = (df["MA5"] > df["MA10"]) & (df["MA5"].shift(1) <= df["MA10"].shift(1))
    df["Sell"] = (df["MA5"] < df["MA10"]) & (df["MA5"].shift(1) >= df["MA10"].shift(1))

    print("▶ 전략 처리 시작")
    trades = []
    holding = False
    buy_price = 0

    for date, row in df.iterrows():
        buy_signal = bool(row["Buy"]) if pd.notnull(row["Buy"]) and not isinstance(row["Buy"], pd.Series) else False
        sell_signal = bool(row["Sell"]) if pd.notnull(row["Sell"]) and not isinstance(row["Sell"], pd.Series) else False

        if not holding and buy_signal:
            buy_price = row["Close"]
            trade = {
                "Buy Date": date,
                "Buy Price": buy_price,
                "Sell Date": pd.NaT,
                "Sell Price": None,
                "Return (%)": None
            }
            trades.append(trade)
            holding = True

            # ✅ 매수 알림
            if SEND_ALERT:
                msg = f"📈 매수 신호 감지! [{symbol}] {date.date()} / 진입가: {buy_price:.2f}원"
                send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)

        elif holding and sell_signal:
            sell_price = row["Close"]
            trades[-1]["Sell Date"] = date
            trades[-1]["Sell Price"] = sell_price
            return_pct = ((sell_price - buy_price) / buy_price) * 100
            trades[-1]["Return (%)"] = return_pct
            holding = False

            # ✅ 매도 알림
            if SEND_ALERT:
                msg = f"📉 매도 완료! [{symbol}] {date.date()} / 매도가: {sell_price:.2f}원 / 수익률: {return_pct:.2f}%"
                send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)

                # 🎯 수익률 10% 이상이면 별도 알림
                if return_pct >= 10:
                    send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
                        f"🎯 목표 수익률 도달! +{return_pct:.2f}% 수익")

    trades_df = pd.DataFrame(trades)
    print("✅ 전략 처리 완료")
    return df, trades_df
