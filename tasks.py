import logging
import os
import re
import shutil
from typing import Optional

import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError


logger = logging.getLogger(__name__)


INVALID_FILENAME_CHARS = r"\\/:*?\"<>|"


def sanitize_filename(filename: str) -> str:
  """파일 이름에서 문제 생길 수 있는 문자를 제거/치환.

  - 기본적으로 Windows/Unix 공통으로 위험한 문자 제거
  - 연속 공백 정리, 길이 제한 등 최소한의 정리만 수행
  """
  # 줄바꿈/탭 제거
  sanitized = filename.replace("\n", " ").replace("\r", " ").replace("\t", " ")
  # 금지 문자 제거
  sanitized = "".join(ch for ch in sanitized if ch not in INVALID_FILENAME_CHARS)
  # 공백 정리
  sanitized = re.sub(r"\s+", " ", sanitized).strip()
  # 너무 길면 잘라내기
  if len(sanitized) > 100:
    sanitized = sanitized[:100]
  return sanitized or "DownloadedFile"


def download_video(
  video_url: str,
  output_path: str,
  format: str = "mp3",
  quality: str = "192",
  cookie_file: Optional[str] = None,
) -> Optional[str]:
  """yt_dlp 를 사용해 실제 영상/오디오를 다운로드.

  - format='mp3' → 오디오 추출 후 mp3로 변환
  - format='mp4' → 지정한 해상도에 맞춰 mp4로 저장
  - 성공 시 최종 파일 경로 문자열 반환, 실패 시 None
  """
  if format == "mp3" and not shutil.which("ffmpeg"):
    logger.error("ffmpeg not found, cannot convert to MP3.")
    return None

  ydl_opts: dict = {
    "geo_bypass": True,
    "nocheckcertificate": True,
    "ignoreerrors": True,
    "quiet": False,
    "verbose": True,
    "outtmpl": output_path + ".%(ext)s",
    # EJS/SABR 대응: deno 런타임 + EJS challenge solver 스크립트 사용
    # 참고: https://github.com/yt-dlp/yt-dlp/wiki/EJS
    "js_runtimes": ["deno"],
    "remote_components": ["ejs:npm"],
  }

  if cookie_file:
    ydl_opts["cookiefile"] = cookie_file

  if format == "mp3":
    ydl_opts.update(
      {
        "format": "bestaudio/best",
        "postprocessors": [
          {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": quality,
          }
        ],
      }
    )
  elif format == "mp4":
    # 포맷 지정이 너무 타이트하면 특정 영상에서 "Requested format is not available"가 발생할 수 있으므로,
    # yt_dlp의 기본 전략에 가깝게 단순화한다.
    ydl_opts.update(
      {
        "format": "bestvideo+bestaudio/best",
        "postprocessors": [
          {
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
          }
        ],
      }
    )

  try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
      ydl.download([video_url])
  except (DownloadError, ExtractorError) as e:
    logger.error(f"Failed to download video {video_url}: {e}")
    return None
  except Exception as e:
    logger.error(f"An unexpected error occurred during download: {e}")
    return None

  # yt_dlp 가 outtmpl 에 맞춰 생성한 실제 파일명을 기준으로 실제 파일 경로를 찾는다.
  # 일부 포맷에서는 "-720p.f398.mp4" 처럼 중간에 포맷 ID가 끼는 경우가 있어서,
  # 단순히 ".mp3"/".mp4" 를 붙이는 방식은 실패할 수 있다.
  final_path: Optional[str] = None
  base_dir = os.path.dirname(output_path) or "."
  prefix = os.path.basename(output_path)

  # output_path 로 시작하는 파일 중, 흔히 사용하는 확장자를 가진 첫 번째 파일을 선택
  for ext in (".mp3", ".m4a", ".mp4", ".webm"):
    candidate = os.path.join(base_dir, prefix + ext)
    if os.path.exists(candidate):
      final_path = candidate
      break

  # 위 패턴으로 못 찾았을 경우, prefix 로 시작하는 모든 파일 중 하나를 fallback 으로 선택
  if final_path is None:
    for name in os.listdir(base_dir):
      if name.startswith(prefix):
        candidate = os.path.join(base_dir, name)
        if os.path.isfile(candidate):
          final_path = candidate
          break

  return final_path


def download_media(
  url: str,
  format: str = "mp3",
  quality: str = "192",
  cookie_file: Optional[str] = None,
) -> Optional[str]:
  """app.py 에서 RQ job 으로 사용되는 엔트리 포인트.

  - 유튜브 URL에서 메타데이터를 먼저 가져와 길이 등을 검증
  - 파일명 정리 후, 이미 동일 품질 파일이 있으면 재사용
  - 없으면 새로 다운로드하고 최종 경로를 반환
  """
  # yt_dlp 를 다시 초기화하여 메타 정보만 추출
  info_opts: dict = {
    "quiet": True,
    "no_warnings": True,
  }
  if cookie_file and os.path.exists(cookie_file):
    info_opts["cookiefile"] = cookie_file

  try:
    with yt_dlp.YoutubeDL(info_opts) as ydl:
      # process=False 로 설정해 포맷 선택/다운로드 관련 처리를 건너뛰고
      # 원시 메타데이터만 가져온다.
      info_dict = ydl.extract_info(url, download=False, process=False)
  except Exception as e:
    logger.error(f"Failed to retrieve video info: {e}")
    return None

  if not isinstance(info_dict, dict):
    logger.error(
      "Failed to retrieve video info. It's possible the video is unavailable or the URL is incorrect."
    )
    return None

  duration = info_dict.get("duration", 0) or 0
  if duration == 0 or duration > 60 * 60 * 2:
    # 2시간 초과 영상은 거절
    logger.warning(
      "Video duration out of allowed range (0 or >2h): %s seconds", duration
    )
    return None

  title = info_dict.get("title", "DownloadedFile")
  video_id = info_dict.get("id", "")
  sanitized_title = sanitize_filename(title)

  base_dir = "uploads"
  os.makedirs(base_dir, exist_ok=True)

  file_base = os.path.join(base_dir, f"{sanitized_title}-{video_id}")
  target_path = f"{file_base}-{quality}.{format}"

  if os.path.exists(target_path):
    logger.info("Reusing existing file: %s", target_path)
    return target_path

  # 새로 다운로드
  output_prefix = f"{file_base}-{quality}"
  final_path = download_video(url, output_prefix, format=format, quality=quality, cookie_file=cookie_file)
  if final_path is None:
    return None

  # 확장자가 예상과 다를 경우에도 target_path 로 맞춰주는 것이 깔끔할 수 있음
  if final_path != target_path and os.path.exists(final_path):
    try:
      os.replace(final_path, target_path)
      final_path = target_path
    except OSError:
      # rename 실패해도 그냥 기존 경로 반환
      pass

  return final_path
