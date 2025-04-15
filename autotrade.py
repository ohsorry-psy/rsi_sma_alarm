from datetime import datetime
import os
from dotenv import load_dotenv  # ✅ .env 파일 로딩을 위한 모듈 추가
from modules.strategy import run_strategy
from modules.telegram_alert import send_telegram_message

# ✅ .env 파일에서 환경변수 불러오기
load_dotenv()

# 한미반도체 예시 (042700.KQ)
symbol = "042700.KQ"
start_date = "2023-01-01"
end_date = datetime.today().strftime("%Y-%m-%d")

print(f"⏱ 자동 전략 실행 시작: {symbol} ({start_date} ~ {end_date})")
df, trades_df = run_strategy(symbol, start_date, end_date)
print("📤 자동 전략 실행 완료")

# ✅ 텔레그램 알림 전송
if os.getenv("SEND_ALERT", "False") == "True":
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        message = f"✅ 자동 실행 완료: {symbol}\n기간: {start_date} ~ {end_date}"
        send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, message)
    else:
        print("⚠️ 텔레그램 토큰 또는 채팅 ID가 설정되지 않았습니다.")
