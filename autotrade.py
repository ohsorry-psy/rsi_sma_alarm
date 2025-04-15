from datetime import datetime
from modules.strategy import run_strategy

# 한미반도체 예시 (042700.KQ)
symbol = "042700.KQ"
start_date = "2023-01-01"
end_date = datetime.today().strftime("%Y-%m-%d")

print(f"⏱ 자동 전략 실행 시작: {symbol} ({start_date} ~ {end_date})")
df, trades_df = run_strategy(symbol, start_date, end_date)
print("📤 자동 전략 실행 완료")
