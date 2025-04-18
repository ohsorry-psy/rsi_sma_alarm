from flask import Flask, render_template, request
import os
from dotenv import load_dotenv
from modules.telegram_alert import send_telegram_message
from modules.strategy import run_strategy
from datetime import datetime
import plotly.graph_objects as go
import plotly.io as pio

app = Flask(__name__)

# ✅ 환경 변수 로드
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SEND_ALERT = os.getenv("SEND_ALERT", "False") == "True"

@app.route("/", methods=["GET", "POST"])
def index():
    message = None
    trades = []
    chart_html = None

    # 기본값 설정
    symbol = "005930.KS"
    start = datetime.today().strftime("%Y-%m-01")
    end = datetime.today().strftime("%Y-%m-%d")

    if request.method == "POST":
        symbol = request.form.get("symbol")
        start = request.form.get("start_date")
        end = request.form.get("end_date")

        try:
            df, trades_df = run_strategy(symbol, start, end, mode="backtest")
            trades = trades_df.to_dict("records")

            # ✅ 차트 생성
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='종가'))
            fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], mode='lines', name='MA5'))
            fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], mode='lines', name='MA10'))
            chart_html = pio.to_html(fig, full_html=False)

            # ✅ 알림 메시지 전송
            if not trades_df.empty:
                total_profit = trades_df["Return (%)"].dropna().sum()
                avg_profit = trades_df["Return (%)"].dropna().mean()
                msg = f"✅ 자동 실행 완료: {symbol}\n📈 총 거래: {len(trades_df)}회 | 평균 수익률: {avg_profit:.2f}%"
            else:
                msg = f"✅ 자동 실행 완료: {symbol}\n📉 거래 내역 없음"

            if SEND_ALERT:
                send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)

            message = "📬 알림 전송 완료: 텔레그램을 확인하세요!"
        except Exception as e:
            message = f"❌ 오류 발생: {e}"

    return render_template("index.html", message=message, trades=trades, chart_html=chart_html, symbol=symbol, start_date=start, end_date=end)

if __name__ == "__main__":
    app.run(debug=True)


