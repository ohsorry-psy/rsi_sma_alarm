import yfinance as yf
import pandas as pd
import os
from dotenv import load_dotenv
from modules.telegram_alert import send_telegram_message
from datetime import datetime

# 🔐 환경 변수 로드
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SEND_ALERT = os.getenv("SEND_ALERT", "False") == "True"

def run_strategy(symbol, start_date, end_date, backtest=False):

    if backtest:
        print("📊 백테스트 모드로 실행 중입니다.")

    print("▶ 데이터 다운로드 시작")
    df = yf.download(symbol, start=start_date, end=end_date)
    print("✅ 데이터 다운로드 완료")

    # 이동 평균선 및 RSI 계산
    df["MA5"] = df["Close"].rolling(window=5).mean()
    df["MA10"] = df["Close"].rolling(window=10).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # 매수/매도 시점 포착 (RSI 조건 포함)
    df["Buy"] = (df["MA5"] > df["MA10"]) & (df["MA5"].shift(1) <= df["MA10"].shift(1)) & (df["RSI"] < 40)
    df["Sell"] = (df["MA5"] < df["MA10"]) & (df["MA5"].shift(1) >= df["MA10"].shift(1))

    print("▶ 전략 처리 시작")
    trades = []
    holding = False
    buy_price = 0
    buy_date = None

    for date, row in df.iterrows():
        buy_signal = bool(row["Buy"]) if pd.notnull(row["Buy"]) and not isinstance(row["Buy"], pd.Series) else False
        sell_signal = bool(row["Sell"]) if pd.notnull(row["Sell"]) and not isinstance(row["Sell"], pd.Series) else False

        if not holding and buy_signal:
            buy_price = row["Close"]
            buy_date = date
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
                msg = f"📈 매수 신호 감지! [{symbol}] {date.date()} / 진입가: {buy_price:.2f}원"
                send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)

        elif holding and sell_signal:
            if (date - buy_date).days >= 2:
                sell_price = row["Close"]
                trades[-1]["Sell Date"] = date
                trades[-1]["Sell Price"] = sell_price
                return_pct = ((sell_price - buy_price) / buy_price) * 100
                trades[-1]["Return (%)"] = return_pct
                holding = False

                if SEND_ALERT:
                    msg = f"📉 매도 완료! [{symbol}] {date.date()} / 매도가: {sell_price:.2f}원 / 수익률: {return_pct:.2f}%"
                    send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)

                    if return_pct >= 10:
                        send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
                            f"🎯 목표 수익률 도달! +{return_pct:.2f}% 수익")

    trades_df = pd.DataFrame(trades)
    print("✅ 전략 처리 완료")
    return df, trades_df

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--backtest', action='store_true', help='백테스트 실행 여부')
    args = parser.parse_args()

    symbol = "005930.KS"
    start_date = "2024-03-01"
    end_date = datetime.today().strftime("%Y-%m-%d")

    print(f"⏱ 자동 전력 실행 시작: {symbol} ({start_date} ~ {end_date})")
    df, trades_df = run_strategy(symbol, start_date, end_date, backtest=args.backtest)

    if not trades_df.empty:
        print(trades_df[["Buy Date", "Buy Price", "Sell Date", "Sell Price", "Return (%)"]])
    else:
        print("⚠️ 거래 내역이 없습니다.")

    if args.backtest and SEND_ALERT:
        if trades_df.empty:
            send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, f"✅ 자동 실행 완료: {symbol}\n📉 거래 내역 없음")
        else:
            total_profit = trades_df["Return (%)"].dropna().sum()
            avg_profit = trades_df["Return (%)"].dropna().mean()
            summary = f"✅ 자동 실행 완료: {symbol}\n📊 총 거래: {len(trades_df)}회 | 평균 수익률: {avg_profit:.2f}%"
            send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, summary)
