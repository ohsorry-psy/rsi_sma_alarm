#!/bin/bash

echo "📦 Git 초기화"
git init

echo "🔗 GitHub 리모트 추가"
git remote add origin https://github.com/ohsorry-psy/rsi_sma_alarm.git

echo "📂 변경사항 스테이징"
git add .

echo "📝 커밋"
git commit -m "🚀 Plotly 차트 및 RSI 서브플롯 추가"

echo "🌿 브랜치 설정 및 푸시"
git branch -M main
git push -u origin main

