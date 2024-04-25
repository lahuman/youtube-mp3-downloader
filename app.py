from flask import Flask, request, send_file, render_template, redirect, url_for, flash, session, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import os
import yt_dlp
import re
import pytz
import time
from datetime import datetime
import logging

logging.basicConfig()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'  # 파일을 저장할 디렉토리 설정
app.config['SECRET_KEY'] = 'helloWorldMyNameIslahuman!+_+'  # 세션에 대한 시크릿 키 설정
app.config['COOKIE_FILE_PATH'] = '/applications/youtube2mp3/cookies.txt'  # 쿠키 파일 경로 설정

# 폴더가 없다면 생성
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def is_valid_youtube_url(url):
    """유투브 URL 검증. 추가 쿼리 파라미터를 고려하여 검증 로직 강화."""
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube\.com|youtu\.be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([a-zA-Z0-9\-_]{11})'
        '(&[a-zA-Z0-9\-=]*)*')  # 추가적인 쿼리 파라미터를 허용
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
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'cookies': app.config['COOKIE_FILE_PATH']
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(url, download=False)
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
    if not youtube_url or not is_valid_youtube_url(youtube_url):
        return jsonify({'error': 'Invalid URL'}), 400
    download_path = download_youtube_mp3(youtube_url)
    if download_path:
        # Store the path in session or directly pass it in a safe way to the client
        session['download_path'] = download_path  # Make sure to secure this approach in a production environment
        return jsonify({'success': True}), 200
    else:
        return jsonify({'error': 'Download failed'}), 500

@app.route('/serve_file')
def serve_file():
    if 'download_path' in session:
        path_to_file = session['download_path']
        return send_file(path_to_file, as_attachment=True)
    return "File not found", 404

def sanitize_filename(filename):
    """ 파일명에서 특수 문자를 제거하고, 파일 시스템에서 안전하게 사용할 수 있도록 처리 """
    # 윈도우와 호환되지 않는 문자 제거
    filename = re.sub(r'[\\/*?:"<>|]', '', filename)
    # 유니코드 문자를 ASCII로 변환, 인코딩 문제 방지
#    filename = filename.encode('ascii', 'ignore').decode('ascii')
    # 공백과 앞뒤 공백 제거
    filename = filename.strip().replace(' ', '_')
    filename = filename.replace('#', '').replace('%', '').replace("'", "")  # 작은따옴표 제거 추가
    # 파일명 길이 제한 (예: 255자로 제한)
    return filename[:255]




def download_youtube_mp3(url):
    ydl_opts = {
        'geo_bypass': True,
        'quiet': False,
        'verbose': True,
        'cookies': app.config['COOKIE_FILE_PATH']  # 쿠키 파일 경로 추가
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(url, download=False)
            if not isinstance(info_dict, dict):  # 반환된 데이터가 사전이 아닐 경우
                print("Failed to retrieve video info")
                return None
            print(info_dict.get('duration', 0)) 
            # 길이 검증: 600초(10분)을 초과하면 오류 처리
            if info_dict.get('duration', 0) == 0 or info_dict.get('duration', 0) > 1000:
                print(f"The video is longer than the allowed 10 minutes: {info_dict['duration']} seconds")
                return None  # 또는 적절한 오류 메시지 반환


            video_title = info_dict.get('title', 'DownloadedFile')
            sanitized_title = sanitize_filename(video_title)

            file_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{sanitized_title}')

            if os.path.exists(file_path+'.mp3'):  # 파일이 이미 존재하면 경로만 반환
                return file_path+ '.mp3'

            # 파일이 존재하지 않으면 다운로드
            download_video(url, file_path )
            return file_path + '.mp3'
        except Exception as e:
            print(f"Error downloading: {e}")
            return None



def download_video(video_url, output_path):

    ydl_opts = {
        'format': 'bestaudio/best',
        'geo_bypass': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(output_path),
        'quiet': False,
        'verbose': False,
        'ignoreerrors': True,  # 오류를 무시하고 계속 진행
        'cookies': app.config['COOKIE_FILE_PATH']  # 쿠키 파일 경로 추가
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([video_url])
        except yt_dlp.utils.DownloadError:
            print(f"Failed to download video {video_url}. Skipping...")


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

def delete_old_files(directory, age_in_seconds):
    # KST 시간대 객체 생성
    kst = pytz.timezone('Asia/Seoul')
    
    # 현재 시간을 KST로 설정
    now = datetime.now(kst).timestamp()
    
    print("Begin Delete Files")
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                # 파일 수정 시간을 UTC에서 KST로 변환
                file_mod_time_utc = os.path.getmtime(file_path)
                file_mod_time_kst = datetime.fromtimestamp(file_mod_time_utc, kst).timestamp()
                
                # 파일의 마지막 수정 시간이 지정된 시간보다 오래되었는지 확인
                if now - file_mod_time_kst > age_in_seconds:
                    os.remove(file_path)
                    print(f"Deleted {file_path}")
    except Exception as e:
        print(f"Error during file deletion: {e}")


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=delete_old_files, args=['uploads', 10800], trigger="interval", seconds=10)
    scheduler.start()
    logging.info("Scheduler started.")


if __name__ == '__main__':
    #start_scheduler()
    app.run(debug=True, use_reloader=False, port=8000, host="10.0.0.98")

