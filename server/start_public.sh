#!/bin/bash
# 啟動後端並開一條 Cloudflare 臨時通道，讓 GitHub Pages 上的網站可以呼叫後端。
# 用法：在 server 資料夾執行 ./start_public.sh（按 Ctrl+C 結束）
cd "$(dirname "$0")"
PORT=${PORT:-5050}
command -v cloudflared >/dev/null || { echo "安裝 cloudflared…"; brew install cloudflared || exit 1; }
python app.py > /tmp/siwan_app.log 2>&1 &
APP_PID=$!
trap 'kill $APP_PID 2>/dev/null' EXIT
sleep 3
if ! curl -s "http://127.0.0.1:$PORT/api/summary" | grep -q restaurants; then
  echo "後端啟動失敗，錯誤訊息："; tail -20 /tmp/siwan_app.log; exit 1
fi
echo "後端已啟動：http://127.0.0.1:$PORT ，已連上資料庫"
cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:$PORT" 2>&1 | while read -r line; do
  url=$(echo "$line" | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | head -1)
  if [ -n "$url" ]; then
    echo ""
    echo "================================================================"
    echo " 後端公開網址：$url"
    echo " GitHub Pages 網站（第一次請用這個網址開啟）："
    echo " https://elsonyeh.github.io/restaurant-reservation-web/?api=$url"
    echo " 這個視窗不要關；按 Ctrl+C 結束"
    echo "================================================================"
  fi
done
