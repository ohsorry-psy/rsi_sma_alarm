from datetime import datetime
import os
import pandas as pd
from dotenv import load_dotenv  # ✅ .env 파일 로딩을 위한 모듈 추가
from modules.strategy import run_strategy
from modules.telegram_alert import send_telegram_message

# ✅ .env 파일에서 환경변수 불러오기
load_dotenv()

# 📊 결과 요약 메시지 포맷 함수
def format_trade_results(trades_df):
    if trades_df.empty:
        return "❌ 거래 내역 없음"

    messages = []
    total_profit = 0
    for idx, row in trades_df.iterrows():
        buy_date = row["Buy Date"].strftime("%Y-%m-%d") if pd.notna(row["Buy Date"]) else "-"
        sell_date = row["Sell Date"].strftime("%Y-%m-%d") if pd.notna(row["Sell Date"]) else "-"
        profit = row["Return (%)"] if pd.notna(row["Return (%)"]) else 0
        total_profit += profit if isinstance(profit, (int, float)) else 0
        messages.append(f"📅 {buy_date} ➡ {sell_date} | 수익률: {profit:.2f}%")

    avg_profit = total_profit / len(trades_df)
    summary = f"\n✅ 총 거래: {len(trades_df)}회 | 평균 수익률: {avg_profit:.2f}%"
    return "\n".join(messages) + summary

# 한미반도체 예시 (042700.KQ)
symbol = "042700.KQ"
start_date = "2023-01-01"
end_date = datetime.today().strftime("%Y-%m-%d")

print(f"⏱ 자동 전략 실행 시작: {symbol} ({start_date} ~ {end_date})")
df, trades_df = run_strategy(symbol, start_date, end_date, backtest=True)
print("📤 자동 전략 실행 완료")

# ✅ 텔레그램 알림 전송
if os.getenv("SEND_ALERT", "False") == "True":
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        result_message = format_trade_results(trades_df)
        message = f"✅ 자동 실행 완료: {symbol}\n📅 기간: {start_date} ~ {end_date}\n\n{result_message}"
        send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, message)
    else:
        print("⚠️ 텔레그램 토큰 또는 채팅 ID가 설정되지 않았습니다.")
