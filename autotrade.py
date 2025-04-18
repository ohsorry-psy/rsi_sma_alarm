# autotrade.py
import yfinance as yf
import pandas as pd
import os
from dotenv import load_dotenv
from modules.telegram_alert import send_telegram_message
from datetime import datetime
import argparse

# 🔐 환경 변수 로드
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SEND_ALERT = os.getenv("SEND_ALERT", "False") == "True"

def run_strategy(symbol, start_date, end_date, backtest=False):
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
        buy_signal = bool(row["Buy"]) if not pd.isna(row["Buy"]) else False
        sell_signal = bool(row["Sell"]) if not pd.isna(row["Sell"]) else False

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

            if SEND_ALERT:
                msg = f"\U0001F4C8 매수 신호 감지! [{symbol}] {date.date()} / 진입가: {buy_price:.2f}원"
                send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)

        elif holding and sell_signal:
            sell_price = row["Close"]
            trades[-1]["Sell Date"] = date
            trades[-1]["Sell Price"] = sell_price
            return_pct = ((sell_price - buy_price) / buy_price) * 100
            trades[-1]["Return (%)"] = return_pct
            holding = False

            if SEND_ALERT:
                msg = f"\U0001F4C9 매도 완료! [{symbol}] {date.date()} / 매도가: {sell_price:.2f}원 / 수익률: {return_pct:.2f}%"
                send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)

                if return_pct >= 10:
                    send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
                        f"\U0001F3AF 목표 수익률 도달! +{return_pct:.2f}% 수익")

    trades_df = pd.DataFrame(trades)
    print("✅ 전략 처리 완료")
    return df, trades_df

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', type=str, default='live', help="실행 모드: 'live' 또는 'backtest'")
    parser.add_argument('--symbol', type=str, default='005930.KS')
    parser.add_argument('--start', type=str, default='2024-03-01')
    parser.add_argument('--end', type=str, default=datetime.today().strftime("%Y-%m-%d"))
    args = parser.parse_args()

    print(f"⏱ 자동 전략 실행 시작: {args.symbol} ({args.start} ~ {args.end})")
    print(f"✅ 실행 모드: {args.mode}")

    backtest_flag = args.mode == 'backtest'
    df, trades_df = run_strategy(args.symbol, args.start, args.end, backtest=backtest_flag)

    if not trades_df.empty:
        print(trades_df[["Buy Date", "Buy Price", "Sell Date", "Sell Price", "Return (%)"]])
    else:
        print("⚠️ 거래 내역이 없습니다.")

    if backtest_flag and SEND_ALERT:
        if trades_df.empty:
            send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
                                  f"✅ 백테스트 완료: {args.symbol}\n📉 거래 내역 없음")
        else:
            total_profit = trades_df["Return (%)"].dropna().sum()
            avg_profit = trades_df["Return (%)"].dropna().mean()
            summary = f"✅ 백테스트 완료: {args.symbol}\n📊 총 거래: {len(trades_df)}회 | 평균 수익률: {avg_profit:.2f}%"
            send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, summary)
