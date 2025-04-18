import yfinance as yf
import pandas as pd
import os
from dotenv import load_dotenv
from modules.telegram_alert import send_telegram_message
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots  # ✅ subplot 추가
import argparse  # ✅ argparse 추가

# 🔐 환경 변수 로드
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SEND_ALERT = os.getenv("SEND_ALERT", "False") == "True"

def run_strategy(symbol, start_date, end_date, backtest=False):

    if backtest:
        print("🕒 백테스트 모드로 실행 중입니다.")

    print("▶ 데이터 다운로드 시작")
    df = yf.download(symbol, start=start_date, end=end_date, group_by="ticker")
    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel(0, axis=1)
    print("✅ 데이터 다운로드 완료")

    df["MA5"] = df["Close"].rolling(window=5).mean()
    df["MA10"] = df["Close"].rolling(window=10).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    df["Prev Close"] = df["Close"].shift(1)
    df["Prev Open"] = df["Open"].shift(1)

    bullish_candle = (df["Close"] > df["Open"]) & (df["Prev Close"] < df["Prev Open"])
    df["Bullish Candle"] = bullish_candle.astype(bool)

    df["Buy"] = ((df["MA5"] > df["MA10"]) &
                  (df["MA5"].shift(1) <= df["MA10"].shift(1)) &
                  (df["RSI"] < 60) &
                  (df["Bullish Candle"])).astype(bool)

    df["Sell"] = ((df["MA5"] < df["MA10"]) &
                   (df["MA5"].shift(1) >= df["MA10"].shift(1))).astype(bool)

    print("▶ 전략 처리 시작")
    trades = []
    holding = False
    buy_price = 0
    buy_date = None

    for date, row in df.iterrows():
        buy_signal = bool(row["Buy"])
        sell_signal = bool(row["Sell"])

        if not holding and buy_signal:
            buy_price = row["Close"]
            buy_date = date
            trades.append({
                "Buy Date": date,
                "Buy Price": buy_price,
                "Sell Date": pd.NaT,
                "Sell Price": None,
                "Return (%)": None
            })
            holding = True

            if SEND_ALERT:
                send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
                    f"📈 매수 신호 감지! [{symbol}] {date.date()} / 진입가: {buy_price:.2f}원")

        elif holding and sell_signal:
            sell_price = row["Close"]
            trades[-1]["Sell Date"] = date
            trades[-1]["Sell Price"] = sell_price
            return_pct = ((sell_price - buy_price) / buy_price) * 100
            trades[-1]["Return (%)"] = return_pct
            holding = False

            if SEND_ALERT:
                send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
                    f"🔽 매도 완료! [{symbol}] {date.date()} / 매도가: {sell_price:.2f}원 / 수익률: {return_pct:.2f}%")

    trades_df = pd.DataFrame(trades)
    print("✅ 전략 처리 완료")

    # ✅ Plotly subplot 시각화
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3],
                        vertical_spacing=0.05, subplot_titles=("가격 차트", "RSI"))

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Candlestick"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["MA5"], mode='lines', name='MA5'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MA10"], mode='lines', name='MA10'), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df[df['Buy']].index,
        y=df[df['Buy']]['Close'],
        mode='markers', name='Buy Signal',
        marker=dict(color='green', size=10, symbol='triangle-up')
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df[df['Sell']].index,
        y=df[df['Sell']]['Close'],
        mode='markers', name='Sell Signal',
        marker=dict(color='red', size=10, symbol='triangle-down')
    ), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name='RSI'), row=2, col=1)

    fig.update_layout(title=f"{symbol} 매수/매도 + RSI 차트",
                      xaxis_rangeslider_visible=False, height=800)
    fig.show()

    return df, trades_df

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--backtest', action='store_true', help='백테스트 실행 유무')
    parser.add_argument('--symbol', type=str, default="005930.KS", help='종목 코드')  # ✅ 추가
    parser.add_argument('--start', type=str, default="2024-03-01", help='시작일')    # ✅ 추가
    parser.add_argument('--end', type=str, default=datetime.today().strftime("%Y-%m-%d"), help='종료일')  # ✅ 추가
    args = parser.parse_args()

    symbol = args.symbol
    start_date = args.start
    end_date = args.end

    print(f"⏱ 자동 전략 실행 시작: {symbol} ({start_date} ~ {end_date})")
    df, trades_df = run_strategy(symbol, start_date, end_date, backtest=args.backtest)

    if not trades_df.empty:
        print(trades_df[["Buy Date", "Buy Price", "Sell Date", "Sell Price", "Return (%)"]])
    else:
        print("⚠️ 거래 내역이 없습니다.")

    if args.backtest and SEND_ALERT:
        if trades_df.empty:
            send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
                f"✅ 자동 실행 완료: {symbol}\n🔽 거래 내역 없음")
        else:
            total_profit = trades_df["Return (%)"].dropna().sum()
            avg_profit = trades_df["Return (%)"].dropna().mean()
            summary = f"✅ 자동 실행 완료: {symbol}\n📈 총 거래: {len(trades_df)}회 | 평균 수익률: {avg_profit:.2f}%"
            send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, summary)
