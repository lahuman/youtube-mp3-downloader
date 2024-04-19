from flask import Flask, request, send_file, render_template, redirect, url_for, flash
from apscheduler.schedulers.background import BackgroundScheduler
import os
import yt_dlp
import re
import pytz
import time
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'  # 파일을 저장할 디렉토리 설정
app.config['SECRET_KEY'] = 'your_secret_key'  # 세션에 대한 시크릿 키 설정


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
def index():
    if request.method == 'POST':
        youtube_url = request.form.get('youtube_url', '')

        # 빈값 검증
        if not youtube_url:
            flash('YouTube URL cannot be empty.', category='error')
            return redirect('/mp3')

        # 유튜브 주소 검증
        if not is_valid_youtube_url(youtube_url):
            flash('Invalid YouTube URL.', category='error')
            return redirect('/mp3')

        download_path = download_youtube_mp3(youtube_url)
        if download_path:
            return send_file(download_path, as_attachment=True)
        else:
            flash('Failed to download the video or the video is too long.', category='error')
            return redirect('/mp3')

    return render_template('index.html')

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
        'verbose': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(url, download=False)
            if not isinstance(info_dict, dict):  # 반환된 데이터가 사전이 아닐 경우
                print("Failed to retrieve video info")
                return None
            
            # 길이 검증: 600초(10분)을 초과하면 오류 처리
            if info_dict.get('duration', 0) > 600:
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
        'verbose': True,
        'ignoreerrors': True,  # 오류를 무시하고 계속 진행
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
    scheduler.add_job(func=delete_old_files, args=['uploads', 10800*4], trigger="interval", seconds=10)
    scheduler.start()
    print("Scheduler started.")


if __name__ == '__main__':
    start_scheduler()
    app.run(debug=False, port=8000)
