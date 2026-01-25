import yt_dlp
import os
import re
import logging
import shutil

def sanitize_filename(filename):
# ... (rest of the function)
# ...
        try:
            info_dict = ydl.extract_info(url, download=False)
            if not isinstance(info_dict, dict):  # 반환된 데이터가 사전이 아닐 경우
                logging.error("Failed to retrieve video info. It's possible the video is unavailable or the URL is incorrect.")
                return None
            print(info_dict.get('duration', 0))
            # 길이 검증: 600초(10분)을 초과하면 오류 처리
# ... (rest of the function)
            if info_dict.get('duration', 0) == 0 or info_dict.get('duration', 0) > (60 * 60 * 2):
                print(f"The video is longer than the allowed 2 hours: {info_dict['duration']} seconds")
                return None  # 또는 적절한 오류 메시지 반환


            video_title = info_dict.get('title', 'DownloadedFile')
            video_id = info_dict.get('id', '')
            sanitized_title = sanitize_filename(video_title)

            file_path = os.path.join('uploads', f'{sanitized_title}-{video_id}')
            if os.path.exists(file_path + '-' + quality + '.' + format):
                return file_path + '-' + quality + '.' + format

            # Download the video with specified format and quality
            download_video(url, file_path+'-'+quality, format, quality, cookie_file)
            return file_path + '-' + quality +  '.' + format

        except Exception as e:
            print(f"Error downloading: {e}")
            return None


import logging
import shutil

# ... (rest of the imports and sanitize_filename function)

def download_video(video_url, output_path, format='mp3', quality='192', cookie_file=None):
    if format == 'mp3' and not shutil.which('ffmpeg'):
        logging.error("ffmpeg not found, cannot convert to MP3.")
        return None

    ydl_opts = {
        'geo_bypass': True,
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'quiet': False,
        'verbose': True,
        'outtmpl': output_path + '.%(ext)s',
    }

    if cookie_file:
        ydl_opts['cookiefile'] = cookie_file

    if format == 'mp3':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality,
            }],
        })
    elif format == 'mp4':
        if quality == '720p':
            format_spec = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]'
        elif quality == '1080p':
            format_spec = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]'
        elif quality == '360p':
            format_spec = 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]'
        else:
            format_spec = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
        ydl_opts.update({
            'format': format_spec,
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
    except yt_dlp.utils.DownloadError as e:
        logging.error(f"Failed to download video {video_url}: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during download: {e}")
        return None


