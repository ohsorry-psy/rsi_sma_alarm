from flask import Flask, render_template, request
import pandas as pd
import plotly.graph_objects as go
from modules.strategy import run_strategy

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    trades_df = pd.DataFrame()
    chart_html = ""
    symbol = "064350.KS"
    start_date = "2023-01-01"
    end_date = "2024-12-31"

    if request.method == "POST":
        print("📥 POST 요청 받음!")
        symbol = request.form.get("symbol", symbol)
        start_date = request.form.get("start_date", start_date)
        end_date = request.form.get("end_date", end_date)

        print(f"🔍 전략 실행: {symbol}, {start_date} ~ {end_date}")
        df, trades_df = run_strategy(symbol, start_date, end_date)
        print("✅ 전략 실행 완료")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Close"],
            mode="lines", name="Close Price", line=dict(color="black")
        ))

        if not trades_df.empty:
            fig.add_trace(go.Scatter(
                x=trades_df["Buy Date"], y=trades_df["Buy Price"],
                mode="markers", name="Buy",
                marker=dict(color="blue", size=10, symbol="triangle-up"),
                hovertemplate="%{x|%Y-%m-%d}<br>📈 매수가: %{y:.2f}원<extra></extra>"
            ))
            fig.add_trace(go.Scatter(
                x=trades_df["Sell Date"], y=trades_df["Sell Price"],
                mode="markers", name="Sell",
                marker=dict(color="red", size=10, symbol="triangle-down"),
                hovertemplate="%{x|%Y-%m-%d}<br>📉 매도가: %{y:.2f}원<extra></extra>"
            ))

        fig.update_layout(
            title=f"{symbol} 전략 차트",
            xaxis_title="날짜",
            yaxis_title="종가 (원)",
            hovermode="x unified",
            template="plotly_white"
        )

        chart_html = fig.to_html(full_html=False)

    return render_template("index.html",
                           chart_html=chart_html,
                           trades=trades_df.to_dict(orient="records"),
                           symbol=symbol,
                           start_date=start_date,
                           end_date=end_date)

if __name__ == "__main__":
    print("🚀 Flask 서버 시작됨")
    app.run(host="0.0.0.0", port=5000, debug=True)
