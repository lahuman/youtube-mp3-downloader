import logging
import os
import re
import shutil
from typing import Optional

import redis
from rq import get_current_job
import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError


logger = logging.getLogger(__name__)

# Redis 설정 (app.py와 동일한 환경변수 사용)
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))

PROGRESS_KEY_PREFIX = "yt_progress"


def set_progress(job_id: Optional[str], status: str, percent: float) -> None:
  """특정 RQ job에 대한 진행률/상태를 Redis에 기록.

  - job_id 가 없으면 아무 것도 하지 않는다.
  - percent는 0~100 사이로 클램핑한다.
  """
  if not job_id:
    return

  p = max(0.0, min(100.0, float(percent)))

  try:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    r.hset(f"{PROGRESS_KEY_PREFIX}:{job_id}", mapping={"status": status, "percent": str(p)})
  except Exception as e:
    logger.error(f"Failed to update progress for job {job_id}: {e}")


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


def make_progress_hook(job_id: Optional[str]):
  """yt_dlp progress hook 생성.

  - 다운로드 중(download status)에는 downloaded/total 로 percent 계산
  - 거의 끝난 시점(finished)에서는 99%로 올려두고 마무리는 상위 로직에서 100%로 설정
  """

  def hook(d):
    status = d.get("status")
    if status == "downloading":
      total = d.get("total_bytes") or d.get("total_bytes_estimate")
      downloaded = d.get("downloaded_bytes", 0)
      if total:
        # 전체 100% 중 다운로드 단계는 0~50%를 차지하도록 매핑
        raw_percent = downloaded / total * 100.0
        percent = raw_percent * 0.5
      else:
        percent = 0.0
      set_progress(job_id, "downloading", percent)
    elif status == "finished":
      # 네트워크 다운로드는 끝났고, 이후 ffmpeg 등 변환 단계로 진입
      # 다운로드 단계 상한은 50%로 고정하고, 변환 단계는 50~100%로 표현
      set_progress(job_id, "converting", 50.0)

  return hook


def download_video(
  video_url: str,
  output_path: str,
  format: str = "mp3",
  quality: str = "192",
  cookie_file: Optional[str] = None,
  job_id: Optional[str] = None,
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
    # js_runtimes 형식은 {runtime: {config}} 딕셔너리여야 한다.
    "js_runtimes": {"deno": {}},
    "remote_components": ["ejs:npm"],
  }

  # 진행률 hook 등록
  ydl_opts["progress_hooks"] = [make_progress_hook(job_id)]

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
    # UI에서 선택한 해상도(360p/720p 등)에 따라 포맷을 제한한다.
    # 기본값이나 알 수 없는 값이 들어오면 best 로 fallback.
    height = None
    if quality.endswith("p") and quality[:-1].isdigit():
      try:
        height = int(quality[:-1])
      except ValueError:
        height = None

    if height:
      fmt = f"bv*[height<={height}]+ba/best[height<={height}]"
    else:
      fmt = "bestvideo+bestaudio/best"

    ydl_opts.update(
      {
        "format": fmt,
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
    set_progress(job_id, "failed", 0.0)
    return None
  except Exception as e:
    logger.error(f"An unexpected error occurred during download: {e}")
    set_progress(job_id, "failed", 0.0)
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

  # 현재 RQ job 정보(진행률 기록용)
  job = get_current_job()
  job_id = job.id if job else None

  # 초기 진행률 0%로 설정 (다운로드 단계 시작)
  set_progress(job_id, "downloading", 0.0)

  duration = info_dict.get("duration", 0) or 0
  if duration == 0 or duration > 60 * 60 * 2:
    # 2시간 초과 영상은 거절
    logger.warning(
      "Video duration out of allowed range (0 or >2h): %s seconds", duration
    )
    set_progress(job_id, "failed", 0.0)
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
  final_path = download_video(
    video_url=url,
    output_path=output_prefix,
    format=format,
    quality=quality,
    cookie_file=cookie_file,
    job_id=job_id,
  )
  if final_path is None:
    set_progress(job_id, "failed", 0.0)
    return None

  # 변환(포스트프로세싱) 단계는 다운로드 이후 ~ 완료까지 50~100% 구간으로 표시한다.
  # 세부 진행률은 알 수 없으므로, 백엔드는 50%로 유지하고 프런트에서 50→99%를 천천히 올린다.
  set_progress(job_id, "converting", 50.0)

  # 확장자가 예상과 다를 경우에도 target_path 로 맞춰주는 것이 깔끔할 수 있음
  if final_path != target_path and os.path.exists(final_path):
    try:
      os.replace(final_path, target_path)
      final_path = target_path
    except OSError:
      # rename 실패해도 그냥 기존 경로 반환
      pass

  # 최종 완료 시 100%로 마무리
  set_progress(job_id, "complete", 100.0)

  return final_path
