# YouTube MP3 Downloader

## 프로젝트 설명
YouTube MP3 Downloader는 사용자가 YouTube 동영상의 URL을 입력하면 MP3 파일로 변환하여 다운로드할 수 있게 해주는 웹 애플리케이션입니다. 이 프로젝트는 Flask를 기반으로 구현되었으며, `yt-dlp` 라이브러리를 사용하여 오디오 추출 기능을 제공합니다.

## 주요 기능
- YouTube 동영상 URL을 통한 MP3 파일 생성 및 다운로드
- 가상 환경에서 실행을 위한 설정 포함
- 실시간 동영상 처리 및 다운로드

## 시작하기

### 필요 조건
프로젝트를 실행하기 전에 다음 소프트웨어가 설치되어 있어야 합니다:
- Python 3.8 이상
- pip (Python 패키지 관리자)

### 설치 방법

1. 저장소를 로컬 시스템으로 복제합니다:
git clone https://github.com/lahuman/youtube-mp3-downloader.git
cd youtube-mp3-downloader

```bash
$ git clone https://github.com/lahuman/youtube-mp3-downloader.git
$ cd youtube-mp3-downloader
```


2. 필요한 패키지 설치:

```bash
$ pip install -r requirements.txt
```


3. 웹 애플리케이션 실행:

```bash
python app.py
```


## 사용 방법
웹 브라우저에서 `http://localhost:5000`으로 접속하여 YouTube 동영상 URL을 입력하고, 'Download' 버튼을 클릭하여 MP3 파일을 다운로드 받습니다.

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

