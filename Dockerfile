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

# 시스템 의존성 (yt-dlp, 빌드 도구, JS 런타임 등)
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg \
      ca-certificates \
      curl \
      gnupg \
      unzip \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /usr/share/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    # Deno: aarch64 리눅스용 바이너리를 직접 내려받아 설치 (비대화식)
    && curl -fsSL https://github.com/denoland/deno/releases/latest/download/deno-aarch64-unknown-linux-gnu.zip -o /tmp/deno.zip \
    && unzip /tmp/deno.zip -d /usr/local/bin \
    && rm /tmp/deno.zip

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . ./

# 업로드 폴더 미리 생성 (볼륨 마운트 시에도 문제 없도록)
RUN mkdir -p uploads

EXPOSE 8000

# 기본은 gunicorn으로 서비스
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]
