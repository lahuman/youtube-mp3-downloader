#!/bin/bash

# Gunicorn 애플리케이션의 PID 파일 경로
PID_PATH="/applications/youtube2mp3/pid"

# PID 파일이 존재하면 기존 프로세스 종료
if [ -f "$PID_PATH" ]; then
    echo "Stopping existing gunicorn process..."
    PID=$(cat "$PID_PATH")
    kill $PID
    # PID 파일 삭제
    rm "$PID_PATH"
    # 프로세스 종료를 위해 잠시 대기
    sleep 2
fi

# 가상 환경 활성화
source venv/bin/activate

# Gunicorn을 nohup을 사용하여 백그라운드에서 실행
echo "Starting gunicorn..."
nohup gunicorn "app:app" --pid "$PID_PATH" -b 0.0.0.0:8000 &

echo "Gunicorn started with new process."

