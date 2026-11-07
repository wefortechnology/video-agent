"""Free stock footage (Pixabay videos + photos, Pexels videos). Picks the clip whose tags best match the scene, not just the first hit."""
import logging
import re
from pathlib import Path
from typing import List, Optional, Set

import requests

from app.config import DATA, settings

log = logging.getLogger("stock")
CACHE = DATA / "cache" / "stock"
TIMEOUT = 30
STOP = {"the", "a", "an", "and", "of", "in", "on", "for", "to", "with", "is", "are", "at", "up", "by", "close", "shot", "view"}
GOOD_SCORE = 5  # a video scoring below this is replaced by a better-matching photo if one exists


def configured() -> bool:
    return bool(settings.PEXELS_API_KEY or settings.PIXABAY_API_KEY)


def split_queries(text: str) -> List[str]:
    """'diwali crackers children | fireworks night | festival lights' -> three queries, most specific first."""
    return [q.strip() for q in re.split(r"[|;\n]", text or "") if q.strip()][:4]


def _words(text: str) -> Set[str]:
    return {w for w in re.findall(r"[a-z0-9']+", (text or "").lower()) if len(w) > 2 and w not in STOP}


SEARCH_CACHE = DATA / "cache" / "search"
SEARCH_CACHE.mkdir(parents=True, exist_ok=True)
CACHE_HOURS = 24  # Pixabay asks API users to cache results for 24 hours


def _request(url: str, *, params=None, headers=None, stream=False):
    """GET with polite backoff on 429 (Pixabay allows about 100 requests a minute)."""
    import time
    for wait in (0, 4, 12, 25):
        if wait:
            time.sleep(wait)
        r = requests.get(url, params=params, headers=headers, timeout=TIMEOUT, stream=stream)
        if r.status_code != 429:
            r.raise_for_status()
            return r
        r.close()
    r.raise_for_status()


def _search_json(url: str, params: dict, headers=None) -> dict:
    import hashlib, json, time
    key = hashlib.sha1(json.dumps([url, sorted((k, v) for k, v in params.items() if k != "key")]).encode()).hexdigest()
    f = SEARCH_CACHE / f"{key}.json"
    if f.exists() and time.time() - f.stat().st_mtime < CACHE_HOURS * 3600:
        return json.loads(f.read_text())
    data = _request(url, params=params, headers=headers).json()
    f.write_text(json.dumps(data))
    return data


def _download(url: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    with _request(url, stream=True) as r:
        tmp = dest.with_suffix(".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
        tmp.rename(dest)
    return dest


def _aspect_ok(w: int, h: int, orientation: str) -> bool:
    if not w or not h:
        return False
    return (h > w) if orientation == "portrait" else (w > h) if orientation == "landscape" else abs(w - h) / max(w, h) < 0.25


def split_must(text: str) -> List[str]:
    return [m.strip().lower() for m in re.split(r"[,|;]", text or "") if len(m.strip()) > 2][:6]


def _norm(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith("s") else word


def _has_must(tags: str, must: List[str]) -> bool:
    """A keyword matches if all its words appear among the tags (plural-insensitive, any order): 'indian sweets' ~ 'indian sweet, laddu'."""
    tag_words = {_norm(w) for w in re.findall(r"[a-z0-9']+", (tags or "").lower())}
    for m in must:
        words = [_norm(w) for w in re.findall(r"[a-z0-9']+", m) if len(w) > 1]
        if words and all(w in tag_words for w in words):
            return True
    return False


def _score(tags: str, query_words: Set[str], all_words: Set[str], w: int, h: int, orientation: str, must: List[str]) -> int:
    """-1 = reject. A clip must show the scene's key subject (its tags contain a must-match keyword); then closer tags and aspect rank it."""
    if must and not _has_must(tags, must):
        return -1
    t = _words(tags)
    return 3 + 2 * len(t & query_words) + len(t & all_words) + (1 if _aspect_ok(w, h, orientation) else 0)


def _topic_bonus(tags: str, topic: List[str]) -> float:
    """Big lift for clips tagged with the video's topic, so 'oil lamp' finds Diwali diyas, not Christmas candles."""
    return 6.0 if topic and _has_must(tags, topic) else 0.0


def _quality(hit: dict) -> bool:
    """Drop what Pixabay itself marks as AI-made, low quality or animation."""
    return not (hit.get("isAiGenerated") or hit.get("isLowQuality") or hit.get("type") in ("animation", "illustration", "vector"))


def _popularity(hit: dict) -> float:
    import math
    return 0.6 * math.log1p(hit.get("likes", 0)) + 0.3 * math.log1p(hit.get("downloads", 0))


def _pixabay_videos(query, orientation, used, min_seconds, all_words, must, topic=()):
    data = _search_json("https://pixabay.com/api/videos/", {"key": settings.PIXABAY_API_KEY, "q": query, "per_page": 20, "safesearch": "true"})
    qw = _words(query)
    for v in data.get("hits", []):
        key = f"pixabay_{v['id']}"
        if key in used or v.get("duration", 0) < min_seconds or v.get("isLowQuality"):
            continue
        vids = v.get("videos", {})
        pick = vids.get("large") if vids.get("large", {}).get("url") else vids.get("medium")
        if not pick or not pick.get("url"):
            continue
        sc = _score(v.get("tags", ""), qw, all_words, pick.get("width", 0), pick.get("height", 0), orientation, must)
        if sc < 0:
            continue
        thumb = (vids.get("tiny") or vids.get("small") or pick).get("thumbnail")
        yield sc + _popularity(v) + _topic_bonus(v.get("tags", ""), topic), {"key": key, "url": pick["url"], "kind": "video", "credit": f"Pixabay / {v.get('user', '')}",
                                    "page": v.get("pageURL"), "tags": v.get("tags", ""), "thumb": thumb}


def _pexels_videos(query, orientation, used, min_seconds, all_words, must, topic=()):
    data = _search_json("https://api.pexels.com/videos/search", {"query": query, "orientation": orientation, "per_page": 15, "size": "medium"},
                        headers={"Authorization": settings.PEXELS_API_KEY})
    qw = _words(query)
    for v in data.get("videos", []):
        key = f"pexels_{v['id']}"
        if key in used or v.get("duration", 0) < min_seconds:
            continue
        files = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width")]
        if not files:
            continue
        files.sort(key=lambda f: f["width"] * f["height"])
        f = ([x for x in files if max(x["width"], x["height"]) >= 1280] or files[-1:])[0]
        slug = (v.get("url") or "").rstrip("/").split("/")[-1].replace("-", " ")
        sc = _score(slug, qw, all_words, f["width"], f["height"], orientation, must)
        if sc < 0:
            continue
        yield sc + _topic_bonus(slug, topic), {"key": key, "url": f["link"], "kind": "video", "credit": f"Pexels / {v.get('user', {}).get('name', '')}",
                   "page": v.get("url"), "tags": slug, "thumb": v.get("image")}


def _pixabay_images(query, orientation, used, all_words, must, any_orient=False, topic=()):
    data = _search_json("https://pixabay.com/api/", {"key": settings.PIXABAY_API_KEY, "q": query, "image_type": "photo", "per_page": 20,
                                                     "safesearch": "true", "min_width": 1000,
                                                     "orientation": "all" if any_orient else {"portrait": "vertical", "landscape": "horizontal"}.get(orientation, "all")})
    qw = _words(query)
    for h in data.get("hits", []):
        key = f"pixabayimg_{h['id']}"
        if key in used or not h.get("largeImageURL") or h.get("isLowQuality") or h.get("type") in ("illustration", "vector"):
            continue
        sc = _score(h.get("tags", ""), qw, all_words, h.get("imageWidth", 0), h.get("imageHeight", 0), orientation, must)
        if sc < 0:
            continue
        yield sc + _popularity(h) - 5 - (3 if h.get("isAiGenerated") else 0) + _topic_bonus(h.get("tags", ""), topic), {"key": key, "url": h["largeImageURL"], "kind": "image", "credit": f"Pixabay / {h.get('user', '')}",
                                          "page": h.get("pageURL"), "tags": h.get("tags", ""), "thumb": h.get("webformatURL")}


def _collect(fns, queries) -> List[tuple]:
    seen, out = set(), []
    for q in queries:
        for fn in fns:
            try:
                for sc, hit in fn(q):
                    if hit["key"] not in seen:
                        seen.add(hit["key"])
                        out.append((sc, hit))
            except Exception as e:
                log.warning("stock search failed for %r: %s", q, e)
    out.sort(key=lambda x: -x[0])
    return out


def _thumb_bytes(url: str) -> Optional[bytes]:
    try:
        return _request(url).content
    except Exception:
        return None


def find_shots(queries: List[str], orientation: str, used: Set[str], need: int = 2, min_seconds: float = 3.0,
               must: Optional[List[str]] = None, scene_text: str = "", topic: Optional[List[str]] = None) -> List[dict]:
    """Up to `need` shots for one scene. Candidates are filtered by tags and quality, then Gemini looks at the thumbnails
    and keeps only the ones that really show the subject and look good. Returns [] if nothing deserves to be on screen."""
    queries = [q for q in queries if q]
    if not queries or not configured():
        return []
    must, topic = must or [], topic or []
    queries = queries + [m for m in must[:3] if m not in [x.lower() for x in queries]]
    if topic:  # topic + subject together, e.g. 'diwali diya'
        queries += [f"{topic[0]} {m}" for m in must[:2] if topic[0] not in m]
    queries = list(dict.fromkeys(q.lower() for q in queries))[:6]  # fewer, distinct searches: kinder to rate limits
    all_words = set().union(*(_words(q) for q in queries))
    vfns = []
    if settings.PIXABAY_API_KEY:
        vfns.append(lambda q: _pixabay_videos(q, orientation, used, min_seconds, all_words, must, topic))
    if settings.PEXELS_API_KEY:
        vfns.append(lambda q: _pexels_videos(q, orientation, used, min_seconds, all_words, must, topic))
    cands = _collect(vfns, queries)[:8]
    if settings.PIXABAY_API_KEY and len(cands) < 4:  # photos only when there is not enough moving footage  # photos always compete with videos: a good photo with a slow pan beats a poor video
        imgs = _collect([lambda q: _pixabay_images(q, orientation, used, all_words, must, topic=topic)], queries)
        if len(imgs) < 3:
            imgs += _collect([lambda q: _pixabay_images(q, orientation, used, all_words, must, any_orient=True, topic=topic)], queries)
        cands = cands + imgs[:4]
    cands = sorted(cands, key=lambda x: -x[0])[:10]  # one ranked pool; the vision check sees the best 10
    if not cands:
        return []

    chosen = [h for _, h in cands[:need]]  # fallback if the vision check is unavailable
    try:
        from app.services import llm
        if llm.configured() and settings.VISION_CHECK:
            thumbs = [(i, _thumb_bytes(h["thumb"])) for i, (_, h) in enumerate(cands) if h.get("thumb")]
            thumbs = [(i, b) for i, b in thumbs if b]
            if thumbs:
                kinds = [cands[i][1]["kind"] for i, _ in thumbs]
                idx = llm.pick_visuals(scene_text, must, [b for _, b in thumbs], need + 1, kinds)  # one spare in case a download fails
                chosen = [cands[thumbs[k][0]][1] for k in idx if 0 <= k < len(thumbs)]
    except Exception as e:
        log.warning("vision pick failed, using tag ranking: %s", e)

    shots = []
    for hit in chosen:
        if len(shots) >= need:
            break
        ext = ".jpg" if hit["kind"] == "image" else ".mp4"
        try:
            path = _download(hit["url"], CACHE / f"{hit['key']}{ext}")
        except Exception as e:
            log.warning("download failed for %s: %s", hit["key"], e)
            continue
        used.add(hit["key"])
        log.info("stock pick %s tags=%s", hit["key"], hit.get("tags", "")[:70])
        shots.append({"path": str(path), "credit": hit["credit"], "page": hit["page"], "key": hit["key"], "kind": hit["kind"]})
    return shots


def find_photo(queries: List[str], used: Set[str], must: Optional[List[str]] = None, topic: Optional[List[str]] = None) -> Optional[str]:
    """Best real photo (Pixabay) for a motion-graphics 'photo' scene. Returns a local path or None."""
    if not settings.PIXABAY_API_KEY:
        return None
    must, topic = must or [], topic or []
    queries = [q for q in queries if q] + [m for m in must[:2]]
    queries = list(dict.fromkeys(q.lower() for q in queries))[:5]
    if not queries:
        return None
    all_words = set().union(*(_words(q) for q in queries))
    cands = _collect([lambda q: _pixabay_images(q, "landscape", used, all_words, must, any_orient=True, topic=topic)], queries)
    if not cands and must:  # relax: topic match only
        cands = _collect([lambda q: _pixabay_images(q, "landscape", used, all_words, [], any_orient=True, topic=topic)], queries[:2])
    for _, hit in cands[:3]:
        try:
            path = _download(hit["url"], CACHE / f"{hit['key']}.jpg")
            used.add(hit["key"])
            log.info("photo pick %s tags=%s", hit["key"], hit.get("tags", "")[:70])
            return str(path)
        except Exception as e:
            log.warning("photo download failed: %s", e)
    return None
