import yt_dlp
import os
import re

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

def download_media(url, format='mp3', quality='192'):
    ydl_opts = {
        'geo_bypass': True,
        'quiet': False,
        'verbose': True,
        'cookiefile': '/applications/youtube2mp3/cookies.txt',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(url, download=False)
            if not isinstance(info_dict, dict):  # 반환된 데이터가 사전이 아닐 경우
                print("Failed to retrieve video info")
                return None
            print(info_dict.get('duration', 0))
            # 길이 검증: 600초(10분)을 초과하면 오류 처리
            if info_dict.get('duration', 0) == 0 or info_dict.get('duration', 0) > (60 * 60 * 2):
                print(f"The video is longer than the allowed 2 hours: {info_dict['duration']} seconds")
                return None  # 또는 적절한 오류 메시지 반환


            video_title = info_dict.get('title', 'DownloadedFile')
            sanitized_title = sanitize_filename(video_title)

            file_path = os.path.join('uploads', f'{sanitized_title}')
            if os.path.exists(file_path ):
                return file_path

            # Download the video with specified format and quality
            download_video(url, file_path+'-'+quality, format, quality)
            return file_path + '-' + quality +  '.' + format

        except Exception as e:
            print(f"Error downloading: {e}")
            return None


def download_video(video_url, output_path, format='mp3', quality='192'):
    if format == 'mp3':
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality,
            }],
            'outtmpl': output_path ,
        }
    elif format == 'mp4':
        if quality == '720p':
            format_spec = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]'
        elif quality == '1080p':
            format_spec = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]'
        elif quality == '360p':
            format_spec = 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]'
        else:
            format_spec = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
        ydl_opts = {
            'format': format_spec,
            'outtmpl': output_path + '.mp4',
            'postprocessors': [{  # Optional: Specify postprocessing if needed
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',  # Ensure the output is mp4
            }],
        }

    # Common options
    ydl_opts.update({
        'geo_bypass': True,
        'quiet': False,
        'verbose': True,
        'ignoreerrors': True,
        'cookiefile': '/applications/youtube2mp3/cookies.txt',
    })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([video_url])
        except yt_dlp.utils.DownloadError as e:
            print(f"Failed to download video {video_url}: {e}")
            return None


