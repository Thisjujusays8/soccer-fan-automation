#!/usr/bin/env python3
"""
Soccer fan automation worker.

Modes:
  MODE=discover   Find new YouTube candidates and save them to clip_candidates.
  MODE=process    Process approved or found candidates into vertical preview videos.
  MODE=post       Post processed and approved candidates.
  MODE=auto       Discover, process the best candidate, and post only if AUTO_APPROVE=true.

Required Supabase tables:
  clip_candidates
  posts

This file is intentionally stdlib only except for external binaries:
  yt-dlp
  ffmpeg
  ffprobe
"""

import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("soccer-worker")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", SUPABASE_KEY)
IG_USER_ID = os.environ.get("IG_USER_ID", "")
IG_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
TIKTOK_TOKEN = os.environ.get("TIKTOK_ACCESS_TOKEN", "")
PLAYER_SLUG = os.environ.get("PLAYER_SLUG", "")
SEARCH_QUERY = os.environ.get("SEARCH_QUERY", "")
WATERMARK = os.environ.get("WATERMARK_HANDLE", "")
YT_COOKIES = os.environ.get("YT_COOKIES", "")
MODE = os.environ.get("MODE", "auto").lower()
AUTO_APPROVE = os.environ.get("AUTO_APPROVE", "false").lower() == "true"
POST_TO_IG = os.environ.get("POST_TO_IG", "true").lower() == "true"
POST_TO_TIKTOK = os.environ.get("POST_TO_TIKTOK", "true").lower() == "true"
MAX_RESULTS = int(os.environ.get("MAX_RESULTS", "12"))
CLIP_SECONDS = int(os.environ.get("CLIP_SECONDS", "50"))
VIDEO_BUCKET = os.environ.get("VIDEO_BUCKET", "videos")
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"

SB_HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
}

INVIDIOUS_INSTANCES = [
    "https://iv.datura.network",
    "https://invidious.privacydev.net",
    "https://invidious.lunar.icu",
    "https://yt.cdaut.de",
    "https://invidious.fdn.fr",
]

BAD_TITLE_WORDS = {
    "reaction", "podcast", "interview", "press conference", "talksport",
    "documentary", "career mode", "fc 24", "eafc", "fifa gameplay",
}
GOOD_TITLE_WORDS = {
    "goal", "goals", "assist", "assists", "skills", "dribbling", "highlights",
    "touches", "performance", "masterclass", "vs", "v ",
}


@dataclass
class Candidate:
    vid_id: str
    title: str
    source_url: str
    source_hash: str
    score: int
    instance: Optional[str] = None


def require_env() -> None:
    missing = []
    for key, value in {
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_KEY or SUPABASE_SERVICE_KEY": SUPABASE_SERVICE_KEY,
        "PLAYER_SLUG": PLAYER_SLUG,
        "SEARCH_QUERY": SEARCH_QUERY,
        "WATERMARK_HANDLE": WATERMARK,
    }.items():
        if not value:
            missing.append(key)
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")


def request_json(
    url: str,
    method: str = "GET",
    payload: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
) -> Any:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        details = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} for {url}: {details[:500]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error for {url}: {e}") from e


def supabase_url(path: str, params: str = "") -> str:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    return f"{url}?{params}" if params else url


def sb_get(path: str, params: str = "") -> List[Dict[str, Any]]:
    return request_json(supabase_url(path, params), headers=SB_HEADERS, timeout=20)


def sb_insert(path: str, data: Dict[str, Any], prefer: str = "return=representation") -> List[Dict[str, Any]]:
    headers = {**SB_HEADERS, "Prefer": prefer}
    return request_json(supabase_url(path), method="POST", payload=data, headers=headers, timeout=30)


def sb_patch(path: str, filters: str, data: Dict[str, Any]) -> Any:
    headers = {**SB_HEADERS, "Prefer": "return=representation"}
    return request_json(supabase_url(path, filters), method="PATCH", payload=data, headers=headers, timeout=30)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s#@]", " ", title.lower())).strip()


def score_title(title: str, query: str) -> int:
    text = normalize_title(title)
    query_words = [w for w in normalize_title(query).split() if len(w) > 2]
    score = 0
    for word in query_words:
        if word in text:
            score += 2
    for word in GOOD_TITLE_WORDS:
        if word in text:
            score += 3
    for word in BAD_TITLE_WORDS:
        if word in text:
            score -= 6
    if "shorts" in text:
        score += 2
    if len(text) < 8:
        score -= 5
    return score


def write_cookies_file(tmpdir: str) -> Optional[str]:
    if not YT_COOKIES.strip():
        return None
    path = os.path.join(tmpdir, "cookies.txt")
    with open(path, "w", encoding="utf-8") as file:
        file.write(YT_COOKIES)
    return path


def run_cmd(cmd: List[str], timeout: int) -> subprocess.CompletedProcess:
    log.debug("Running command: %s", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def search_invidious(query: str) -> List[Candidate]:
    candidates: List[Candidate] = []
    for instance in INVIDIOUS_INSTANCES:
        try:
            encoded = urllib.parse.quote(query)
            url = f"{instance}/api/v1/search?q={encoded}&type=video&sort_by=relevance"
            results = request_json(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            for item in results[:MAX_RESULTS]:
                vid_id = item.get("videoId")
                title = item.get("title", "")
                if not vid_id:
                    continue
                source_url = f"https://www.youtube.com/watch?v={vid_id}"
                candidates.append(Candidate(
                    vid_id=vid_id,
                    title=title,
                    source_url=source_url,
                    source_hash=sha256_text(source_url),
                    score=score_title(title, query),
                    instance=instance,
                ))
            if candidates:
                log.info("Found %s candidates through %s", len(candidates), instance)
                return candidates
        except Exception as exc:
            log.warning("%s search failed: %s", instance, exc)
    return candidates


def search_ytdlp(query: str, cookies_file: Optional[str]) -> List[Candidate]:
    cmd = [
        "yt-dlp",
        f"ytsearch{MAX_RESULTS}:{query}",
        "--dump-json",
        "--flat-playlist",
        "--no-playlist",
        "--extractor-args",
        "youtube:player_client=ios",
    ]
    if cookies_file:
        cmd.extend(["--cookies", cookies_file])
    result = run_cmd(cmd, timeout=90)
    if result.returncode != 0:
        log.warning("yt-dlp search failed: %s", result.stderr[:500])
    candidates: List[Candidate] = []
    for line in result.stdout.strip().splitlines():
        try:
            item = json.loads(line)
            vid_id = item.get("id")
            title = item.get("title", "")
            if not vid_id:
                continue
            source_url = f"https://www.youtube.com/watch?v={vid_id}"
            candidates.append(Candidate(
                vid_id=vid_id,
                title=title,
                source_url=source_url,
                source_hash=sha256_text(source_url),
                score=score_title(title, query),
                instance=None,
            ))
        except json.JSONDecodeError:
            continue
    return candidates


def search_youtube(query: str, cookies_file: Optional[str]) -> List[Candidate]:
    seen = set()
    combined = search_invidious(query) + search_ytdlp(query, cookies_file)
    unique: List[Candidate] = []
    for item in combined:
        if item.vid_id in seen:
            continue
        seen.add(item.vid_id)
        unique.append(item)
    unique.sort(key=lambda c: c.score, reverse=True)
    return unique


def candidate_exists(source_hash: str) -> bool:
    rows = sb_get("clip_candidates", f"source_hash=eq.{source_hash}&select=id")
    return bool(rows)


def post_exists(source_hash: str) -> bool:
    rows = sb_get("posts", f"source_hash=eq.{source_hash}&select=id")
    return bool(rows)


def save_candidate(candidate: Candidate) -> Optional[Dict[str, Any]]:
    if candidate_exists(candidate.source_hash) or post_exists(candidate.source_hash):
        return None
    status = "approved" if AUTO_APPROVE else "found"
    payload = {
        "player_slug": PLAYER_SLUG,
        "source_url": candidate.source_url,
        "source_video_id": candidate.vid_id,
        "source_hash": candidate.source_hash,
        "title": candidate.title,
        "score": candidate.score,
        "status": status,
        "metadata": {"instance": candidate.instance},
    }
    if DRY_RUN:
        log.info("DRY_RUN candidate: %s", payload)
        return payload
    saved = sb_insert("clip_candidates", payload)
    log.info("Saved candidate: %s", candidate.title)
    return saved[0] if saved else None


def discover(tmpdir: str) -> List[Dict[str, Any]]:
    cookies_file = write_cookies_file(tmpdir)
    candidates = search_youtube(SEARCH_QUERY, cookies_file)
    saved = []
    for candidate in candidates:
        row = save_candidate(candidate)
        if row:
            saved.append(row)
    log.info("Discovery complete. Saved %s new candidates.", len(saved))
    return saved


def get_next_candidate_for_processing() -> Optional[Dict[str, Any]]:
    rows = sb_get(
        "clip_candidates",
        f"player_slug=eq.{PLAYER_SLUG}&status=eq.approved&select=*&order=score.desc,created_at.asc&limit=1",
    )
    return rows[0] if rows else None


def get_next_candidate_for_posting() -> Optional[Dict[str, Any]]:
    rows = sb_get(
        "clip_candidates",
        f"player_slug=eq.{PLAYER_SLUG}&status=eq.processed&select=*&order=score.desc,created_at.asc&limit=1",
    )
    return rows[0] if rows else None


def download_with_ytdlp(source_url: str, raw_path: str, cookies_file: Optional[str]) -> bool:
    cmd = [
        "yt-dlp",
        source_url,
        "-f",
        "best[ext=mp4][height<=720]/best[height<=720]/best",
        "-o",
        raw_path,
        "--merge-output-format",
        "mp4",
        "--no-playlist",
        "--extractor-args",
        "youtube:player_client=ios,android",
    ]
    if cookies_file:
        cmd.extend(["--cookies", cookies_file])
    result = run_cmd(cmd, timeout=300)
    if result.returncode == 0 and os.path.exists(raw_path) and os.path.getsize(raw_path) > 1000:
        return True
    log.warning("yt-dlp download failed: %s", result.stderr[:500])
    return False


def download_with_invidious(vid_id: str, preferred_instance: Optional[str], raw_path: str) -> bool:
    instances = [preferred_instance] if preferred_instance else []
    instances += [i for i in INVIDIOUS_INSTANCES if i and i != preferred_instance]
    for instance in instances:
        try:
            data = request_json(
                f"{instance}/api/v1/videos/{vid_id}",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15,
            )
            streams = data.get("formatStreams", [])
            mp4s = [s for s in streams if s.get("container") == "mp4" and s.get("url")]
            if not mp4s:
                continue
            mp4s.sort(key=lambda s: int(str(s.get("resolution", "0p")).replace("p", "") or 0), reverse=True)
            req = urllib.request.Request(mp4s[0]["url"], headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=160) as response:
                with open(raw_path, "wb") as file:
                    while True:
                        chunk = response.read(2 * 1024 * 1024)
                        if not chunk:
                            break
                        file.write(chunk)
            if os.path.exists(raw_path) and os.path.getsize(raw_path) > 1000:
                log.info("Downloaded from %s", instance)
                return True
        except Exception as exc:
            log.warning("%s download failed: %s", instance, exc)
    return False


def download_video(row: Dict[str, Any], tmpdir: str, cookies_file: Optional[str]) -> str:
    raw = os.path.join(tmpdir, "raw.mp4")
    source_url = row["source_url"]
    metadata = row.get("metadata") or {}
    preferred_instance = metadata.get("instance")
    if download_with_ytdlp(source_url, raw, cookies_file):
        return raw
    if download_with_invidious(row["source_video_id"], preferred_instance, raw):
        return raw
    raise RuntimeError("All download methods failed")


def probe_duration_seconds(path: str) -> float:
    result = run_cmd(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path], timeout=60)
    if result.returncode != 0:
        return float(CLIP_SECONDS)
    try:
        return float(json.loads(result.stdout)["format"]["duration"])
    except Exception:
        return float(CLIP_SECONDS)


def safe_drawtext(value: str) -> str:
    cleaned = value.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    return cleaned[:80]


def process_video(raw: str, out: str) -> None:
    duration = probe_duration_seconds(raw)
    start = max(0, min(12, int(duration * 0.12)))
    watermark = safe_drawtext(f"@{WATERMARK.lstrip('@')}")
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
        f"drawtext=text='{watermark}':fontsize=42:fontcolor=white:"
        "x=30:y=h-90:shadowcolor=black:shadowx=2:shadowy=2"
    )
    cmd = [
        "ffmpeg",
        "-i",
        raw,
        "-ss",
        str(start),
        "-t",
        str(CLIP_SECONDS),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-crf",
        "26",
        "-preset",
        "fast",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        out,
        "-y",
        "-loglevel",
        "error",
    ]
    result = run_cmd(cmd, timeout=420)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr[:500]}")
    if not os.path.exists(out) or os.path.getsize(out) < 1000:
        raise RuntimeError("FFmpeg did not produce a valid output file")


def upload_storage(filepath: str) -> str:
    key = f"{PLAYER_SLUG}/{uuid.uuid4()}.mp4"
    with open(filepath, "rb") as file:
        data = file.read()
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "video/mp4",
        "x-upsert": "false",
    }
    url = f"{SUPABASE_URL}/storage/v1/object/{VIDEO_BUCKET}/{key}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180):
            pass
    except urllib.error.HTTPError as e:
        details = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase Storage upload failed: HTTP {e.code}: {details[:500]}") from e
    return f"{SUPABASE_URL}/storage/v1/object/public/{VIDEO_BUCKET}/{key}"


def mark_candidate(row_id: Any, status: str, **extra: Any) -> None:
    payload = {"status": status, **extra}
    if DRY_RUN:
        log.info("DRY_RUN patch candidate %s: %s", row_id, payload)
        return
    sb_patch("clip_candidates", f"id=eq.{row_id}", payload)


def process_next(tmpdir: str) -> Optional[Dict[str, Any]]:
    row = get_next_candidate_for_processing()
    if not row:
        log.info("No approved candidate to process.")
        return None
    try:
        mark_candidate(row["id"], "processing", error_message=None)
        cookies_file = write_cookies_file(tmpdir)
        raw = download_video(row, tmpdir, cookies_file)
        out = os.path.join(tmpdir, "out.mp4")
        process_video(raw, out)
        video_url = upload_storage(out)
        mark_candidate(row["id"], "processed", video_url=video_url, processed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        row["video_url"] = video_url
        row["status"] = "processed"
        log.info("Processed candidate: %s", row["title"])
        return row
    except Exception as exc:
        mark_candidate(row["id"], "failed", error_message=str(exc)[:1000])
        raise


def http_post(url: str, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    return request_json(
        url,
        method="POST",
        payload=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        timeout=45,
    )


def post_instagram(video_url: str, caption: str) -> str:
    if not POST_TO_IG:
        log.info("Instagram disabled.")
        return ""
    if not IG_USER_ID or not IG_TOKEN:
        log.info("Instagram credentials missing. Skipping.")
        return ""
    base = "https://graph.facebook.com/v19.0"
    container = http_post(
        f"{base}/{IG_USER_ID}/media",
        {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": True,
            "access_token": IG_TOKEN,
        },
    )
    container_id = container.get("id")
    if not container_id:
        raise RuntimeError(f"Instagram did not return container id: {container}")
    log.info("Instagram container created: %s", container_id)
    time.sleep(60)
    published = http_post(
        f"{base}/{IG_USER_ID}/media_publish",
        {"creation_id": container_id, "access_token": IG_TOKEN},
    )
    return published.get("id", "")


def post_tiktok(video_url: str, title: str) -> str:
    if not POST_TO_TIKTOK:
        log.info("TikTok disabled.")
        return ""
    if not TIKTOK_TOKEN:
        log.info("TikTok credentials missing. Skipping.")
        return ""
    response = http_post(
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        {
            "post_info": {
                "title": title[:2200],
                "privacy_level": os.environ.get("TIKTOK_PRIVACY_LEVEL", "SELF_ONLY"),
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
                "brand_content_toggle": False,
                "brand_organic_toggle": False,
            },
            "source_info": {"source": "PULL_FROM_URL", "video_url": video_url},
        },
        headers={
            "Authorization": f"Bearer {TIKTOK_TOKEN}",
            "Content-Type": "application/json; charset=UTF-8",
        },
    )
    if response.get("error", {}).get("code") not in (None, "ok"):
        raise RuntimeError(f"TikTok error: {response}")
    return response.get("data", {}).get("publish_id", "")


def save_post(row: Dict[str, Any], platform: str, platform_post_id: str) -> None:
    payload = {
        "clip_candidate_id": row.get("id"),
        "player_slug": PLAYER_SLUG,
        "source_url": row["source_url"],
        "source_video_id": row.get("source_video_id"),
        "source_hash": row.get("source_hash") or sha256_text(row["source_url"]),
        "video_url": row["video_url"],
        "title": row["title"],
        "platform": platform,
        "platform_post_id": platform_post_id,
        "status": "posted" if platform_post_id else "skipped",
    }
    if DRY_RUN:
        log.info("DRY_RUN post: %s", payload)
        return
    sb_insert("posts", payload, prefer="return=minimal")


def post_next() -> Optional[Dict[str, Any]]:
    row = get_next_candidate_for_posting()
    if not row:
        log.info("No processed candidate to post.")
        return None
    try:
        mark_candidate(row["id"], "posting", error_message=None)
        caption = f"{row['title']} ⚽ #{PLAYER_SLUG} #soccer #football #highlights"
        ig_id = post_instagram(row["video_url"], caption)
        tt_id = post_tiktok(row["video_url"], f"{row['title']} ⚽ #soccer #football")
        save_post(row, "instagram", ig_id)
        save_post(row, "tiktok", tt_id)
        mark_candidate(row["id"], "posted", posted_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        log.info("Posted candidate: %s", row["title"])
        return row
    except Exception as exc:
        mark_candidate(row["id"], "failed", error_message=str(exc)[:1000])
        raise


def main() -> None:
    require_env()
    log.info("[%s] Starting mode=%s dry_run=%s", PLAYER_SLUG, MODE, DRY_RUN)
    with tempfile.TemporaryDirectory() as tmpdir:
        if MODE == "discover":
            discover(tmpdir)
        elif MODE == "process":
            process_next(tmpdir)
        elif MODE == "post":
            post_next()
        elif MODE == "auto":
            saved = discover(tmpdir)
            if AUTO_APPROVE and saved:
                process_next(tmpdir)
                post_next()
            elif not AUTO_APPROVE:
                log.info("AUTO_APPROVE=false. Candidates saved for manual approval.")
        else:
            raise RuntimeError("MODE must be one of discover, process, post, auto")
    log.info("[%s] Done", PLAYER_SLUG)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log.exception("Worker failed: %s", exc)
        sys.exit(1)
