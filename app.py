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
from tasks import download_media

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True

# Redis 설정: 환경변수로 오버라이드 가능 (Docker 환경 고려)
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
REDIS_DB = int(os.environ.get('REDIS_DB', '0'))

app.config['SESSION_REDIS'] = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

Session(app)

# Set up Redis Queue for background tasks
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
q = Queue(connection=r, default_timeout=3600)

logging.basicConfig()

app.config['UPLOAD_FOLDER'] = 'uploads'  # 파일을 저장할 디렉토리 설정
app.config['SECRET_KEY'] = 'helloWorldMyNameIslahuman!+_+'  # 세션에 대한 시크릿 키 설정
# 쿠키 파일 경로 설정: 기본값은 ./cookies.txt, 환경변수 COOKIE_FILE_PATH로 오버라이드 가능
app.config['COOKIE_FILE_PATH'] = os.environ.get('COOKIE_FILE_PATH', 'cookies.txt')

# 폴더가 없다면 생성
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def is_valid_youtube_url(url):
    """유투브 URL 검증. 추가 쿼리 파라미터를 고려하여 검증 로직 강화."""
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube\.com|youtu\.be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([a-zA-Z0-9\-_]{11})'
        r'(&[a-zA-Z0-9\-=]*)*'  # 추가적인 쿼리 파라미터를 허용
    )
    return re.match(youtube_regex, url)



@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('home.html')

@app.route('/details', methods=['POST'])
def details():
    youtube_url = request.form.get('youtube_url', '')
    if not youtube_url or not is_valid_youtube_url(youtube_url):
        flash('Invalid YouTube URL.', category='error')
        return redirect(url_for('home'))
    
    video_info = get_video_info(youtube_url)
    if video_info:
        return render_template('details.html', video_info=video_info, youtube_url=youtube_url)
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
            video_info = {
                'id': info_dict.get('id'),
                'url': url,
                'title': info_dict.get('title'),
                'uploader': info_dict.get('uploader'),
                'thumbnail': info_dict.get('thumbnail'),
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

    if not youtube_url or not is_valid_youtube_url(youtube_url):
        return jsonify({'error': 'Invalid URL'}), 400

     # Start the download as a background job
    job = q.enqueue(download_media, youtube_url, format, quality, app.config['COOKIE_FILE_PATH'])
    session['download_job_id'] = job.get_id()
    print(job.get_id())

    return jsonify({'message': 'Download started', 'job_id': job.get_id()}), 202

@app.route('/status/<job_id>')
def check_status(job_id):
    job = Job.fetch(job_id, connection=r)

    if job.is_finished:
        # download_media 가 실제 파일 경로(문자열)를 반환했을 때만 성공 처리
        if job.result and isinstance(job.result, str) and os.path.exists(job.result):
            session['download_path'] = job.result
            return jsonify({'status': 'complete'}), 200
        else:
            session['download_path'] = None
            return jsonify({'status': 'failed'}), 202
    elif job.is_failed:
        session['download_path'] = None
        return jsonify({'status': 'failed'}), 202
    else:
        return jsonify({'status': 'in progress'}), 202


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

