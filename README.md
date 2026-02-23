# YouTube MP3 Downloader

## [바로가기](https://y2mp3.duckdns.org/)

## 프로젝트 설명
YouTube MP3 Downloader는 사용자가 YouTube 동영상의 URL을 입력하면 MP3 파일로 변환하여 다운로드할 수 있게 해주는 웹 애플리케이션입니다. 이 프로젝트는 Flask를 기반으로 구현되었으며, `yt-dlp` 라이브러리를 사용하여 오디오 추출 기능을 제공합니다.

## update 정보
- 1차 단순 mp3 다운로드 기능 개발 **24.4.19**
- mp4 다운로드 기능 개발 **24.4.20**
- [python-rq](https://python-rq.org/) 를 활용한 다운로드 tasks 적용 **24.4.29**
- Docker 기반 `web + worker + redis` 구성 추가, X86/ARM 환경에서 쉽게 배포 가능 **24.4.XX**
- i18n(다국어) 지원 추가: **한국어/영어/일본어** UI 및 SEO 메타 적용 **24.4.XX**
- yt-dlp EJS/SABR 대응: deno 런타임 + EJS remote components 설정으로 최신 YouTube 보호 방식 일부 지원 **24.4.XX**
- MP4 해상도 선택 기능 추가: **360p / 720p** 선택 시 yt-dlp 포맷에 실제 반영 **24.4.XX**
- 다운로드 진행률(%) 표시 및 상태 폴링 개선: Redis + RQ job 기반으로 실시간 진행률 노출, 모바일에서 진행 상태를 명확히 확인 가능 **25.2.XX**
- YouTube Shorts URL 지원: `/shorts/<id>` 형태 URL을 자동으로 `watch?v=<id>` URL로 정규화하여 일반 영상과 동일하게 처리 **25.2.XX**
- X(Twitter) / Vimeo 지원: YouTube 외에도 공개 X(Twitter) 포스트 및 Vimeo 영상 URL에서 MP3/MP4 추출 지원 (yt-dlp 백엔드 기반) **25.2.XX**

## 주요 기능
- YouTube / X(Twitter) / Vimeo 영상 URL을 통한 MP3/MP4 파일 생성 및 다운로드
- MP4 다운로드 시 360p / 720p 해상도 선택 지원 (YouTube 기준, X/Vimeo는 가용한 최고 화질 자동 선택)
- yt-dlp + ffmpeg 기반 고품질 오디오/비디오 추출
- [python-rq](https://python-rq.org/) + Redis 기반 비동기 다운로드 처리(브라우저 멈춤 방지)
- Docker Compose로 `web (Flask + gunicorn) / worker / redis` 한 번에 배포 가능
- i18n 지원: 한국어 / 영어 / 일본어 UI 및 메타 태그로 기본 SEO 고려

## 환경 변수 설정
프로젝트 실행 시 다음 환경 변수를 통해 동작을 제어할 수 있습니다:
- `REDIS_HOST`: Redis 서버 호스트 (기본값: `localhost`)
- `REDIS_PORT`: Redis 서버 포트 (기본값: `6379`)
- `REDIS_DB`: Redis 데이터베이스 인덱스 (기본값: `0`)
- `MAX_DURATION_SECONDS`: 다운로드 가능한 최대 영상 길이 (초 단위, 기본값: `600`)
- `COOKIE_FILE_PATH`: 유튜브 쿠키 파일 경로 (기본값: `cookies.txt`)

## 시작하기

### 필요 조건
프로젝트를 실행하기 전에 다음 소프트웨어가 설치되어 있어야 합니다 (로컬 실행 기준):
- Python 3.8 이상
- pip (Python 패키지 관리자)
- redis

또는 Docker 환경에서 실행할 경우:
- Docker
- Docker Compose

### 설치 방법

1. 저장소를 로컬 시스템으로 복제합니다:

```bash
$ git clone https://github.com/lahuman/youtube-mp3-downloader.git
$ cd youtube-mp3-downloader
```


2. 필요한 패키지 설치:

```bash
$ pip install -r requirements.txt
```


3. 웹 애플리케이션 실행 (로컬 실행 예시):

```bash
# rq worker 실행 (Redis가 localhost:6379에서 떠 있어야 함)
$ rq worker --with-scheduler &

# Flask 앱 실행
$ python app.py
```

또는 Docker Compose를 사용하는 경우:

```bash
$ docker compose up -d --build
```

- web: `http://localhost:8000` (gunicorn + Flask)
- worker: RQ 기반 비동기 다운로드 처리
- redis: 큐/세션 스토리지

## 사용 방법
웹 브라우저에서 `http://localhost:8000` (또는 배포된 도메인) 으로 접속하여 YouTube 동영상 URL을 입력하고,
포맷(MP3/MP4)과 품질(오디오 비트레이트 또는 영상 해상도)을 선택한 뒤 'Download'를 클릭해서 파일을 다운로드 받을 수 있습니다.

## 기여하기
이 프로젝트에 기여하고 싶은 개발자는 다음 방법을 통해 기여할 수 있습니다:

1. 프로젝트를 포크합니다.
2. feature 브랜치를 만듭니다 (`git checkout -b feature/AmazingFeature`).
3. 변경 사항을 커밋합니다 (`git commit -m 'Add some AmazingFeature'`).
4. 브랜치에 푸시합니다 (`git push origin feature/AmazingFeature`).
5. Pull Request를 보냅니다.


## 라이선스
이 프로젝트는 MIT 라이선스를 따릅니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 저자
- **Daniel Lim** - *Initial work* - [lahuman](https://github.com/lahuman)

## 감사의 말
- 본 프로젝트 개발에 도움을 준 AI 에게 감사합니다

