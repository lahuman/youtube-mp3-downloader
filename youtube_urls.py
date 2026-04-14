import re
from typing import Iterable, Optional
from urllib.parse import parse_qs, urlparse


VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
YOUTUBE_REDIRECT_QUERY_KEYS = ("q", "u", "url")
YOUTUBE_DIRECT_PATH_PREFIXES = {"embed", "live", "shorts", "v", "watch"}
YOUTUBE_EXTRA_SUPPORTED_PATH_PREFIXES = {"attribution_link", "clip", "redirect"}


def prepare_url_for_parsing(url: str) -> str:
    """URL 파싱 전에 scheme/상대 경로를 보정한다."""
    candidate = (url or "").strip()
    if not candidate:
        return ""
    if candidate.startswith("//"):
        return f"https:{candidate}"
    if candidate.startswith("/"):
        return f"https://www.youtube.com{candidate}"
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", candidate):
        return candidate
    return f"https://{candidate.lstrip('/')}"


def normalize_host(host: str) -> str:
    return (host or "").lower().split(":", 1)[0]


def is_youtube_host(host: str) -> bool:
    host = normalize_host(host)
    return (
        host == "youtu.be"
        or host.endswith(".youtu.be")
        or host == "youtube.com"
        or host.endswith(".youtube.com")
        or host == "youtube-nocookie.com"
        or host.endswith(".youtube-nocookie.com")
    )


def _merged_query(parsed) -> dict[str, list[str]]:
    query = parse_qs(parsed.query, keep_blank_values=False)
    if parsed.fragment and "=" in parsed.fragment:
        for key, values in parse_qs(parsed.fragment, keep_blank_values=False).items():
            query.setdefault(key, []).extend(values)
    return query


def _first_valid_video_id(values: Iterable[str]) -> Optional[str]:
    for value in values:
        candidate = (value or "").strip()
        if VIDEO_ID_RE.fullmatch(candidate):
            return candidate
    return None


def extract_youtube_video_id(url: str, depth: int = 0) -> Optional[str]:
    """YouTube 계열 URL에서 단일 영상 ID를 최대한 안전하게 추출한다."""
    if depth > 3:
        return None

    parsed = urlparse(prepare_url_for_parsing(url))
    if not is_youtube_host(parsed.netloc):
        return None

    query = _merged_query(parsed)
    video_id = _first_valid_video_id(query.get("v", []))
    if video_id:
        return video_id

    segments = [segment for segment in parsed.path.split("/") if segment]
    if not segments:
        segments = []

    if normalize_host(parsed.netloc).endswith("youtu.be"):
        return _first_valid_video_id(segments[:1])

    if len(segments) >= 2 and segments[0].lower() in YOUTUBE_DIRECT_PATH_PREFIXES:
        return _first_valid_video_id([segments[1]])

    for key in YOUTUBE_REDIRECT_QUERY_KEYS:
        for nested in query.get(key, []):
            candidate = extract_youtube_video_id(nested, depth + 1)
            if candidate:
                return candidate

    return None


def is_valid_youtube_url(url: str) -> bool:
    """다운로더에서 처리 가능한 YouTube 계열 URL인지 확인한다."""
    parsed = urlparse(prepare_url_for_parsing(url))
    if not is_youtube_host(parsed.netloc):
        return False

    if extract_youtube_video_id(url):
        return True

    segments = [segment.lower() for segment in parsed.path.split("/") if segment]
    if not segments:
        return False

    if segments[0] in YOUTUBE_EXTRA_SUPPORTED_PATH_PREFIXES:
        if segments[0] == "clip":
            return len(segments) >= 2
        if segments[0] in {"attribution_link", "redirect"}:
            query = _merged_query(parsed)
            return any(query.get(key) for key in YOUTUBE_REDIRECT_QUERY_KEYS)
        return True

    return False


def normalize_youtube_url(url: str) -> str:
    """추출 가능한 단일 영상 URL이면 canonical watch URL로 정규화한다."""
    video_id = extract_youtube_video_id(url)
    if not video_id:
        return url
    return f"https://www.youtube.com/watch?v={video_id}"
