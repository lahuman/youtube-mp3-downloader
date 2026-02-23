from flask import Flask, request, send_file, render_template, redirect, url_for, flash, session, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import os
import yt_dlp
import re
import pytz
import time
from datetime import datetime
import logging
from flask_session import Session
import redis
from rq import Queue
from rq.job import Job
from tasks import download_media, PROGRESS_KEY_PREFIX

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True

# Redis 설정: 환경변수로 오버라이드 가능 (Docker 환경 고려)
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
REDIS_DB = int(os.environ.get('REDIS_DB', '0'))

# 최대 영상 길이 (초 단위, 기본값 600초=10분)
MAX_DURATION_SECONDS = int(os.environ.get('MAX_DURATION_SECONDS', '600'))
MAX_DURATION_MINUTES = MAX_DURATION_SECONDS // 60

app.config['SESSION_REDIS'] = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

Session(app)

# Set up Redis Queue for background tasks
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
q = Queue(connection=r, default_timeout=3600)

logging.basicConfig()

SUPPORTED_LANGS = ["en", "ko", "ja"]

TRANSLATIONS = {
    "en": {
        "meta_title": "YouTube MP3 & MP4 Downloader",
        "meta_description": "Fast and simple YouTube to MP3 and MP4 downloader. Paste a YouTube link and download high‑quality audio or video for offline use where permitted by law.",
        "hero_badge": "Instant, lightweight YouTube / X / Vimeo to MP3 / MP4",
        "hero_title": "Convert video links to MP3 or MP4 in seconds.",
        "hero_subtitle": "Paste a YouTube, X(Twitter), or Vimeo URL, pick your format, and download high‑quality audio or video for personal use where it is legally permitted.",
        "url_label": "Video URL (YouTube / X / Vimeo)",
        "url_placeholder": "https://www.youtube.com/watch?v=… or https://x.com/...",
        "home_primary_cta": "Continue to format selection",
        "home_clear": "Clear URL",
        "feature_mp3": "MP3 up to 320 kbps",
        "feature_mp4": "MP4 up to 720p",
        "feature_background": "Background processing – no browser freeze",
        "feature_cookie": "Cookie support for age‑restricted videos",
        "feature_limit": f"Max {MAX_DURATION_MINUTES} minutes duration",
        "legal_home": "This tool is intended for personal use only. You are responsible for ensuring you have the rights to download and convert any content. Always follow YouTube's Terms of Service and applicable copyright laws.",
        "details_selected_video": "Selected video",
        "details_format": "Format",
        "details_quality": "Quality",
        "details_start": "Start download",
        "details_back": "Back to URL input",
        "details_note": f"Downloads longer than {MAX_DURATION_MINUTES} minutes or realtime/live streams may fail or be blocked to prevent overload.",
        "footer_notice": "This tool is provided for personal, lawful use only. Please respect YouTube's Terms of Service and copyright laws in your country.",
        "overlay_text": "Preparing your download…",
        "overlay_downloading": "Downloading…",
        "overlay_converting": "Converting file… almost done.",
        "overlay_complete": "Download ready (100%)",
        "overlay_failed": "Download failed.",
        "error_404_title": "We couldn’t find that page.",
        "error_404_subtitle": "The link you followed may be broken, or the page may have been removed.",
        "error_404_back": "Back to downloader",
        "error_500_title": "Something went wrong on our side.",
        "error_500_subtitle": "An unexpected error occurred while processing your request. Please try again in a moment.",
        "error_500_back": "Back to downloader",
        "lang_label": "Language",
        "lang_en": "English",
        "lang_ko": "한국어",
        "lang_ja": "日本語",
        "alert_invalid_url": "Please enter a valid YouTube URL.",
        "alert_long_video": f"Videos longer than {MAX_DURATION_MINUTES} minutes or realtime cannot be processed.",
        "alert_download_ready": "Your download is ready.",
        "alert_download_failed": "Download failed. Please try again.",
        "alert_download_error": "Error: File could not be downloaded.",
        "entry_label": "You’re in the right place",
        "entry_title": "Paste a YouTube link to start your download.",
        "entry_subtitle": "This entry page mirrors the main downloader. If you reached it directly, just head back to the home page to convert your video.",
        "entry_cta": "Go to main downloader",
    },
    "ko": {
        "meta_title": "YouTube MP3 & MP4 다운로더",
        "meta_description": "간단하고 빠른 YouTube MP3 · MP4 변환기. 유튜브 링크만 붙여넣고 고음질 오디오/영상 파일을 합법적인 범위 내에서 다운로드하세요.",
        "hero_badge": "가볍고 빠른 YouTube / X / Vimeo → MP3 / MP4",
        "hero_title": "영상 링크를 몇 초 만에 MP3/MP4로 변환하세요.",
        "hero_subtitle": "YouTube, X(Twitter), Vimeo 링크를 붙여넣고 형식을 고른 다음, 개인·합법적인 용도 안에서 고음질 파일을 저장할 수 있습니다.",
        "url_label": "영상 URL (YouTube / X / Vimeo)",
        "url_placeholder": "https://www.youtube.com/watch?v=… 또는 https://x.com/...",
        "home_primary_cta": "다음 단계로 (형식 선택)",
        "home_clear": "주소 지우기",
        "feature_mp3": "MP3 최대 320 kbps",
        "feature_mp4": "MP4 최대 720p",
        "feature_background": "백그라운드 처리로 브라우저 멈춤 최소화",
        "feature_cookie": "쿠키 사용으로 연령 제한 영상 대응",
        "feature_limit": f"최대 {MAX_DURATION_MINUTES}분 영상 제한",
        "legal_home": "이 도구는 개인적이고 합법적인 용도로만 제공됩니다. 콘텐츠를 다운로드·변환할 권리가 있는지 항상 확인하고, YouTube 이용약관과 저작권 법규를 준수해 주세요.",
        "details_selected_video": "선택한 영상",
        "details_format": "형식",
        "details_quality": "품질",
        "details_start": "다운로드 시작",
        "details_back": "URL 입력 화면으로",
        "details_note": f"{MAX_DURATION_MINUTES}분이 넘는 영상이나 실시간 스트림은 서버 보호를 위해 제한되거나 실패할 수 있습니다.",
        "footer_notice": "이 도구는 개인·합법적인 사용에 한해 제공됩니다. 항상 YouTube 이용약관과 각 국가의 저작권 법을 지켜 주세요.",
        "overlay_text": "다운로드를 준비하고 있습니다…",
        "overlay_downloading": "다운로드 중…",
        "overlay_converting": "파일 변환 중… 거의 다 됐어요.",
        "overlay_complete": "다운로드 준비 완료 (100%)",
        "overlay_failed": "다운로드에 실패했습니다.",
        "error_404_title": "요청하신 페이지를 찾을 수 없습니다.",
        "error_404_subtitle": "링크가 잘못되었거나, 페이지가 삭제되었을 수 있습니다.",
        "error_404_back": "다운로더로 돌아가기",
        "error_500_title": "서버 처리 중 오류가 발생했습니다.",
        "error_500_subtitle": "요청을 처리하는 동안 문제가 생겼습니다. 잠시 후 다시 시도해 주세요.",
        "error_500_back": "다운로더로 돌아가기",
        "lang_label": "언어",
        "lang_en": "English",
        "lang_ko": "한국어",
        "lang_ja": "日本語",
        "alert_invalid_url": "올바른 YouTube URL을 입력해 주세요.",
        "alert_long_video": f"{MAX_DURATION_MINUTES}분이 넘는 영상이나 실시간 영상은 처리할 수 없습니다.",
        "alert_download_ready": "다운로드를 시작합니다.",
        "alert_download_failed": "다운로드에 실패했습니다. 다시 시도해 주세요.",
        "alert_download_error": "파일을 다운로드할 수 없습니다.",
        "entry_label": "위치는 맞아요",
        "entry_title": "YouTube 링크를 붙여넣고 바로 변환해 보세요.",
        "entry_subtitle": "이 페이지는 메인 다운로더와 동일한 엔트리입니다. 직접 들어오셨다면 홈으로 이동해 영상을 변환해 주세요.",
        "entry_cta": "메인 다운로더로 이동",
    },
    "ja": {
        "meta_title": "YouTube MP3・MP4 ダウンローダー",
        "meta_description": "シンプルで高速な YouTube MP3 / MP4 変換ツール。YouTube の URL を貼り付けるだけで、法律の範囲内で高音質の音声や動画をダウンロードできます。",
        "hero_badge": "軽量・高速な YouTube / X / Vimeo → MP3 / MP4",
        "hero_title": "動画リンクを数秒で MP3 / MP4 に変換。",
        "hero_subtitle": "YouTube、X(Twitter)、Vimeo の URL を貼り付けて形式を選ぶだけで、個人的かつ合法な用途に限り高品質なファイルを保存できます。",
        "url_label": "動画 URL (YouTube / X / Vimeo)",
        "url_placeholder": "https://www.youtube.com/watch?v=… または https://x.com/...",
        "home_primary_cta": "次へ進む（形式を選択）",
        "home_clear": "URL をクリア",
        "feature_mp3": "MP3 最大 320 kbps",
        "feature_mp4": "MP4 最大 720p",
        "feature_background": "バックグラウンド処理でブラウザのフリーズを軽減",
        "feature_cookie": "クッキー対応で年齢制限付き動画にも対応",
        "feature_limit": f"最大 {MAX_DURATION_MINUTES} 分の動画制限",
        "legal_home": "本ツールは個人的かつ合法的な利用のみを目的としています。常にコンテンツをダウンロード・変換する権利があるか確認し、YouTube の利用規約および著作権法を遵守してください。",
        "details_selected_video": "選択した動画",
        "details_format": "形式",
        "details_quality": "品質",
        "details_start": "ダウンロードを開始",
        "details_back": "URL 入力画面に戻る",
        "details_note": f"{MAX_DURATION_MINUTES} 分を超える動画やライブ配信は、負荷対策のため制限または失敗する場合があります。",
        "footer_notice": "本ツールは個人的かつ合法的な利用に限定して提供されます。YouTube の利用規約と各国の著作権法を必ず守ってください。",
        "overlay_text": "ダウンロードの準備中です…",
        "overlay_downloading": "ダウンロード中…",
        "overlay_converting": "ファイル変換中… ほぼ完了です。",
        "overlay_complete": "ダウンロードの準備が完了しました（100％）",
        "overlay_failed": "ダウンロードに失敗しました。",

        "error_3740_title": "ページが見つかりませんでした。",
        "error_3740_subtitle": "リンクが間違っているか、このページは削除された可能性があります。",
        "error_3740_back": "ダウンローダーへ戻る",
        "error_500_title": "サーバー側でエラーが発生しました。",
        "error_500_subtitle": "リクエスト処理中に問題が発生しました。しばらくしてからもう一度お試しください。",
        "error_500_back": "ダウンローダーへ",
        "lang_label": "言語",
        "lang_en": "English",
        "lang_ko": "한국어",
        "lang_ja": "日本語",
        "alert_invalid_url": "正しい YouTube URL を入力してください。",
        "alert_long_video": f"{MAX_DURATION_MINUTES} 分を超える動画やライブ配信は処理できません。",
        "alert_download_ready": "ダウンロードを開始します。",
        "alert_download_failed": "ダウンロードに失敗しました。もう一度お試しください。",
        "alert_download_error": "ファイルをダウンロードできませんでした。",
        "entry_label": "ここで合っています",
        "entry_title": "YouTube のリンクを貼り付けてダウンロードを始めましょう。",
        "entry_subtitle": "このページはメインダウンローダーと同じ入り口です。直接アクセスした場合は、ホームに移動して動画を変換してください。",
        "entry_cta": "メインダウンローダーへ",
    },
}


def get_lang():
    lang = request.args.get("lang") or session.get("lang") or "en"
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    session["lang"] = lang
    return lang


@app.context_processor
def inject_translations():
    lang = get_lang()

    def t(key):
        return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))

    return {
        "t": t,
        "current_lang": lang,
        "supported_langs": SUPPORTED_LANGS,
    }

app.config['UPLOAD_FOLDER'] = 'uploads'  # 파일을 저장할 디렉토리 설정
app.config['SECRET_KEY'] = 'helloWorldMyNameIslahuman!+_+'  # 세션에 대한 시크릿 키 설정
# 쿠키 파일 경로 설정: 기본값은 ./cookies.txt, 환경변수 COOKIE_FILE_PATH로 오버라이드 가능
app.config['COOKIE_FILE_PATH'] = os.environ.get('COOKIE_FILE_PATH', 'cookies.txt')

# 폴더가 없다면 생성
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


def is_valid_youtube_url(url):
    """유투브 URL 검증.

    - 일반 watch / embed / v / youtu.be 형식
    - shorts 형식 (https://www.youtube.com/shorts/<id>) 도 허용
    """
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube\.com|youtu\.be)/'
        r'(watch\?v=|embed/|v/|shorts/|.+\?v=)?([a-zA-Z0-9\-_]{11})'
        r'(&[a-zA-Z0-9\-=]*)*'
    )
    return re.match(youtube_regex, url)


def is_twitter_url(url: str) -> bool:
    """X(Twitter) URL 검증 (영상/포스트 URL 전반 허용)."""
    twitter_regex = r'(https?://)?(www\.)?(x\.com|twitter\.com)/.+'
    return re.match(twitter_regex, url) is not None


def is_vimeo_url(url: str) -> bool:
    """Vimeo URL 검증."""
    vimeo_regex = r'(https?://)?(www\.)?vimeo\.com/.+'
    return re.match(vimeo_regex, url) is not None


def is_supported_url(url: str) -> bool:
    """지원하는 플랫폼 URL인지 확인.

    현재는 YouTube, X(Twitter), Vimeo 를 허용한다.
    """
    return bool(is_valid_youtube_url(url) or is_twitter_url(url) or is_vimeo_url(url))


def normalize_youtube_url(url: str) -> str:
    """여러 파라미터가 붙은 YouTube URL을 단일 영상 URL로 정규화.

    - shorts URL도 watch?v=<id> 형태로 정규화한다.
    """
    # 1) shorts 전용 패턴 먼저 처리
    m = re.match(r'(https?://)?(www\.)?youtube\.com/shorts/([a-zA-Z0-9\-_]{11})', url)
    if m:
        video_id = m.group(3)
        return f"https://www.youtube.com/watch?v={video_id}"

    # 2) 기존 watch/embed/youtu.be 패턴 처리
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube\.com|youtu\.be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([a-zA-Z0-9\-_]{11})'
    )
    m = re.match(youtube_regex, url)
    if not m:
        return url

    video_id = m.group(5)
    return f"https://www.youtube.com/watch?v={video_id}"


@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('home.html')

@app.route('/details', methods=['POST'])
def details():
    youtube_url = request.form.get('youtube_url', '')
    if not youtube_url or not is_supported_url(youtube_url):
        flash('Invalid or unsupported URL. Supported: YouTube, X(Twitter), Vimeo.', category='error')
        return redirect(url_for('home'))

    # YouTube 인 경우에만 단일 영상 URL로 정규화
    if is_valid_youtube_url(youtube_url):
        youtube_url = normalize_youtube_url(youtube_url)

    video_info = get_video_info(youtube_url)
    if video_info:
        return render_template('details.html', video_info=video_info, youtube_url=youtube_url, max_duration_seconds=MAX_DURATION_SECONDS)
    else:
        flash('Could not retrieve video details.', category='error')
        return redirect(url_for('home'))


def get_video_info(url):
    # 영상 정보만 조회할 때는 포맷을 강제할 필요가 없으므로
    # format 옵션은 제거한다. (일부 영상에서 "Requested format is not available" 에러를 유발)
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    cookie_path = app.config.get('COOKIE_FILE_PATH')
    if cookie_path and os.path.exists(cookie_path):
        ydl_opts['cookiefile'] = cookie_path

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # process=False 로 설정해 포맷 선택 과정을 건너뛰고
            # 원시 메타데이터만 가져온다. (일부 영상에서 "Requested format is not available" 회피)
            info_dict = ydl.extract_info(url, download=False, process=False)

            # 썸네일은 플랫폼마다 위치가 다를 수 있으므로 몇 가지 후보를 순서대로 찾는다.
            thumbnail = info_dict.get('thumbnail')
            if not thumbnail:
                # yt_dlp 표준 thumbnails 필드
                thumbs = info_dict.get('thumbnails') or []
                if isinstance(thumbs, list) and thumbs:
                    # 가장 마지막(보통 가장 고해상도)을 사용
                    thumbnail = thumbs[-1].get('url') or thumbs[0].get('url')
            if not thumbnail:
                # 일부 사이트(예: Twitter/X)에서 쓰는 필드명 대비
                thumbnail = info_dict.get('thumbnail_url')

            video_info = {
                'id': info_dict.get('id'),
                'url': url,
                'title': info_dict.get('title'),
                'uploader': info_dict.get('uploader') or info_dict.get('channel') or info_dict.get('uploader_id'),
                'thumbnail': thumbnail,
                'duration': info_dict.get('duration')
            }
            return video_info
        except Exception as e:
            print(f"Error retrieving video info: {e}")
            return None


@app.route('/download', methods=['POST'])
def download():
    youtube_url = request.form['youtube_url']
    format = request.form.get('format', 'mp3')  # Default to MP3 if not specified
    quality = request.form.get('quality', '192')

    if not youtube_url or not is_supported_url(youtube_url):
        return jsonify({'error': 'Invalid or unsupported URL. Supported: YouTube, X(Twitter), Vimeo.'}), 400

    # YouTube 의 경우에만 단일 영상 ID로 정규화 (플레이리스트 등)
    if is_valid_youtube_url(youtube_url):
        youtube_url = normalize_youtube_url(youtube_url)

    # Start the download as a background job
    job = q.enqueue(download_media, youtube_url, format, quality, app.config['COOKIE_FILE_PATH'])
    session['download_job_id'] = job.get_id()
    print(job.get_id())

    return jsonify({'message': 'Download started', 'job_id': job.get_id()}), 202


def get_progress(job_id: str):
    """Redis에 저장된 진행률/상태 정보를 조회.

    tasks.py 의 set_progress 와 동일한 키 규칙을 사용한다.
    """
    try:
        progress_data = r.hgetall(f"{PROGRESS_KEY_PREFIX}:{job_id}")
        if not progress_data:
            return None
        status = progress_data.get(b"status", b"in_progress").decode()
        try:
            percent = float(progress_data.get(b"percent", b"0").decode())
        except ValueError:
            percent = 0.0
        return {"status": status, "percent": percent}
    except Exception:
        return None


@app.route('/status/<job_id>')
def check_status(job_id):
    job = Job.fetch(job_id, connection=r)
    progress = get_progress(job_id) or {"status": "downloading", "percent": 0.0}

    if job.is_finished:
        # download_media 가 실제 파일 경로(문자열)를 반환했을 때만 성공 처리
        if job.result and isinstance(job.result, str) and os.path.exists(job.result):
            session['download_path'] = job.result
            return jsonify({'status': 'complete', 'phase': 'complete', 'percent': 100.0}), 200
        else:
            session['download_path'] = None
            return jsonify({'status': 'failed', 'phase': progress.get('status', 'failed'), 'percent': progress.get('percent', 0.0)}), 202
    elif job.is_failed:
        session['download_path'] = None
        return jsonify({'status': 'failed', 'phase': progress.get('status', 'failed'), 'percent': progress.get('percent', 0.0)}), 202
    else:
        # 진행 중인 경우, Redis에 저장된 phase/status/percent 를 그대로 반환
        return jsonify({
            'status': 'in_progress',
            'phase': progress.get('status', 'downloading'),
            'percent': progress.get('percent', 0.0),
        }), 202


@app.route('/serve_file')
def serve_file():
    path_to_file = session.get('download_path')
    if path_to_file and os.path.exists(path_to_file):
        return send_file(path_to_file, as_attachment=True)
    return "File not found", 404


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500


if __name__ == '__main__':
    # 호스트/포트는 환경변수로 오버라이드 가능 (Docker 포함)
    host = os.environ.get('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_RUN_PORT', '8000'))
    app.run(debug=False, use_reloader=False, port=port, host=host)
