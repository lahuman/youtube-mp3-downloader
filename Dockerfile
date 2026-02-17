FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_RUN_HOST=0.0.0.0 \
    FLASK_RUN_PORT=8000 \
    REDIS_HOST=redis \
    REDIS_PORT=6379 \
    REDIS_DB=0 \
    COOKIE_FILE_PATH=/app/cookies.txt

WORKDIR /app

# 시스템 의존성 (yt-dlp, 빌드 도구 등 필요 시 확장)
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . ./

# 업로드 폴더 미리 생성 (볼륨 마운트 시에도 문제 없도록)
RUN mkdir -p uploads

EXPOSE 8000

# 기본은 gunicorn으로 서비스
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]
