# 📈 자동매매 Flask 웹앱 with Telegram 알림

RSI + 이동평균 전략을 이용한 주식 자동매매 분석 도구입니다.  
YFinance로 데이터를 받아 Flask 웹서버에서 시각화하고,  
매수/매도 시점에 텔레그램으로 실시간 알림을 전송합니다.

---

## 🚀 주요 기능

- 📊 MA5/MA10 크로스 기반 매수/매도 시점 탐지
- 📨 매수·매도 시 텔레그램 실시간 알림 전송
- 📉 Plotly 차트로 가격 + 매매 시점 시각화
- 🌐 Render로 배포 가능

💻 설치 방법
pip install -r requirements.txt
python app.py
웹앱이 실행되면 http://127.0.0.1:5000 에서 접속할 수 있습니다.


프로젝트 폴더 구조
<pre><code> flask_trader_final/ ├── app.py # Flask 메인 애플리케이션 ├── requirements.txt # 의존성 목록 ├── .env.example # 환경 변수 템플릿 (.env 파일은 GitHub에 업로드하지 않음) ├── .gitignore # .env 파일 및 기타 캐시 제외 │ ├── templates/ │ └── index.html # 웹 UI 템플릿 (Jinja2) │ └── modules/ ├── strategy.py # 매매 전략 (RSI + MA 교차 전략) └── telegram_alert.py # 텔레그램 알림 함수 </code></pre>--

## 🔐 환경 변수 설정

`.env` 파일을 루트 디렉토리에 생성하고 아래 내용을 채워주세요:

```env
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
SEND_ALERT=True
