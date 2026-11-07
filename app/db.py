"""SQLite storage: brands, brand memory, videos. Survives restarts (the old app lost jobs on restart)."""
import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import DATA

_conn = sqlite3.connect(str(DATA / "app.db"), check_same_thread=False)
_conn.row_factory = sqlite3.Row
_lock = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS brands (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, industry TEXT DEFAULT '', about TEXT DEFAULT '', audience TEXT DEFAULT '',
  tone TEXT DEFAULT 'warm, clear, professional', language TEXT DEFAULT 'en', voice TEXT DEFAULT '',
  primary_color TEXT DEFAULT '#1F4E79', accent_color TEXT DEFAULT '#F2A900', logo_path TEXT DEFAULT '',
  avoid TEXT DEFAULT '', cta TEXT DEFAULT '', created_at TEXT
);
CREATE TABLE IF NOT EXISTS memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT, brand_id INTEGER NOT NULL, kind TEXT NOT NULL,
  text TEXT NOT NULL, created_at TEXT
);
CREATE TABLE IF NOT EXISTS footage (
  id INTEGER PRIMARY KEY AUTOINCREMENT, brand_id INTEGER NOT NULL, filename TEXT NOT NULL,
  path TEXT NOT NULL, tags TEXT DEFAULT '', duration REAL DEFAULT 0, created_at TEXT
);
CREATE TABLE IF NOT EXISTS playlists (
  id INTEGER PRIMARY KEY AUTOINCREMENT, brand_id INTEGER NOT NULL, title TEXT DEFAULT '', topic TEXT DEFAULT '',
  format TEXT NOT NULL, language TEXT DEFAULT 'en', style TEXT DEFAULT 'motion', length_min INTEGER DEFAULT 0,
  structure TEXT DEFAULT '', plan_json TEXT DEFAULT '', created_at TEXT
);
CREATE TABLE IF NOT EXISTS videos (
  id INTEGER PRIMARY KEY AUTOINCREMENT, brand_id INTEGER NOT NULL, title TEXT DEFAULT '', brief TEXT DEFAULT '',
  format TEXT NOT NULL, language TEXT DEFAULT 'en', voice_engine TEXT DEFAULT '', style TEXT DEFAULT 'motion', length_min INTEGER DEFAULT 0, use_ai INTEGER DEFAULT 0,
  status TEXT DEFAULT 'queued', step TEXT DEFAULT '', progress INTEGER DEFAULT 0,
  idea_json TEXT DEFAULT '', script_json TEXT DEFAULT '', error TEXT DEFAULT '',
  approved INTEGER DEFAULT 0, created_at TEXT, updated_at TEXT
);
"""
with _lock:
    _conn.executescript(SCHEMA)
    cols = {r[1] for r in _conn.execute("PRAGMA table_info(videos)")}
    if "style" not in cols:  # databases created before motion graphics existed
        _conn.execute("ALTER TABLE videos ADD COLUMN style TEXT DEFAULT 'footage'")
    if "length_min" not in cols:
        _conn.execute("ALTER TABLE videos ADD COLUMN length_min INTEGER DEFAULT 0")
    if "use_ai" not in cols:
        _conn.execute("ALTER TABLE videos ADD COLUMN use_ai INTEGER DEFAULT 0")
    for col, typ in (("playlist_id", "INTEGER DEFAULT 0"), ("episode", "INTEGER DEFAULT 0"), ("structure", "TEXT DEFAULT ''")):
        if col not in cols:
            _conn.execute(f"ALTER TABLE videos ADD COLUMN {col} {typ}")
    _conn.commit()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _row(r) -> Optional[Dict[str, Any]]:
    return dict(r) if r is not None else None


def query(sql: str, args=()) -> List[Dict[str, Any]]:
    with _lock:
        return [dict(r) for r in _conn.execute(sql, args).fetchall()]


def one(sql: str, args=()) -> Optional[Dict[str, Any]]:
    with _lock:
        return _row(_conn.execute(sql, args).fetchone())


def execute(sql: str, args=()) -> int:
    with _lock:
        cur = _conn.execute(sql, args)
        _conn.commit()
        return cur.lastrowid


# ---- brands -------------------------------------------------------------
BRAND_FIELDS = ["name", "industry", "about", "audience", "tone", "language", "voice",
                "primary_color", "accent_color", "avoid", "cta"]


def create_brand(data: Dict[str, Any]) -> Dict[str, Any]:
    cols = [f for f in BRAND_FIELDS if f in data]
    bid = execute(f"INSERT INTO brands ({','.join(cols)},created_at) VALUES ({','.join('?' * len(cols))},?)",
                  [data[c] for c in cols] + [now()])
    return get_brand(bid)


def update_brand(bid: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    cols = [f for f in BRAND_FIELDS + ["logo_path"] if f in data]
    if cols:
        execute(f"UPDATE brands SET {','.join(c + '=?' for c in cols)} WHERE id=?", [data[c] for c in cols] + [bid])
    return get_brand(bid)


def get_brand(bid: int):
    return one("SELECT * FROM brands WHERE id=?", (bid,))


def list_brands():
    return query("SELECT * FROM brands ORDER BY name")


def delete_brand(bid: int):
    execute("DELETE FROM memories WHERE brand_id=?", (bid,))
    execute("DELETE FROM footage WHERE brand_id=?", (bid,))
    execute("DELETE FROM videos WHERE brand_id=?", (bid,))
    execute("DELETE FROM brands WHERE id=?", (bid,))


# ---- memory -------------------------------------------------------------
def add_memory(brand_id: int, kind: str, text: str):
    mid = execute("INSERT INTO memories (brand_id,kind,text,created_at) VALUES (?,?,?,?)", (brand_id, kind, text.strip(), now()))
    return one("SELECT * FROM memories WHERE id=?", (mid,))


def list_memories(brand_id: int, kinds=None, limit=200):
    if kinds:
        q = ",".join("?" * len(kinds))
        return query(f"SELECT * FROM memories WHERE brand_id=? AND kind IN ({q}) ORDER BY id DESC LIMIT ?", (brand_id, *kinds, limit))
    return query("SELECT * FROM memories WHERE brand_id=? ORDER BY id DESC LIMIT ?", (brand_id, limit))


def delete_memory(mid: int):
    execute("DELETE FROM memories WHERE id=?", (mid,))


# ---- videos -------------------------------------------------------------
def create_video(**kw) -> Dict[str, Any]:
    t = now()
    cols = list(kw) + ["created_at", "updated_at"]
    vid = execute(f"INSERT INTO videos ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", list(kw.values()) + [t, t])
    return get_video(vid)


def update_video(vid: int, **kw):
    if not kw:
        return
    kw["updated_at"] = now()
    execute(f"UPDATE videos SET {','.join(k + '=?' for k in kw)} WHERE id=?", list(kw.values()) + [vid])


def _video_out(v):
    if not v:
        return v
    for k in ("idea_json", "script_json"):
        v[k.replace("_json", "")] = json.loads(v[k]) if v[k] else None
        del v[k]
    v["approved"] = bool(v["approved"])
    return v


def get_video(vid: int):
    return _video_out(one("SELECT * FROM videos WHERE id=?", (vid,)))


def list_videos(brand_id: Optional[int] = None, limit=100):
    if brand_id:
        rows = query("SELECT * FROM videos WHERE brand_id=? ORDER BY id DESC LIMIT ?", (brand_id, limit))
    else:
        rows = query("SELECT * FROM videos ORDER BY id DESC LIMIT ?", (limit,))
    return [_video_out(r) for r in rows]


def create_playlist(**kw) -> Dict[str, Any]:
    cols = list(kw) + ["created_at"]
    pid = execute(f"INSERT INTO playlists ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", list(kw.values()) + [now()])
    return get_playlist(pid)


def get_playlist(pid: int):
    p = one("SELECT * FROM playlists WHERE id=?", (pid,))
    if p:
        p["plan"] = json.loads(p.pop("plan_json") or "{}")
    return p


def list_playlists(brand_id: Optional[int] = None):
    rows = query("SELECT id FROM playlists" + (" WHERE brand_id=?" if brand_id else "") + " ORDER BY id DESC", (brand_id,) if brand_id else ())
    return [get_playlist(r["id"]) for r in rows]


def playlist_videos(pid: int):
    return [_video_out(r) for r in query("SELECT * FROM videos WHERE playlist_id=? ORDER BY episode", (pid,))]


def delete_video(vid: int):
    execute("DELETE FROM videos WHERE id=?", (vid,))


# ---- own footage library -------------------------------------------------
def add_footage(brand_id: int, filename: str, path: str, tags: str, duration: float):
    fid = execute("INSERT INTO footage (brand_id,filename,path,tags,duration,created_at) VALUES (?,?,?,?,?,?)",
                  (brand_id, filename, path, tags, duration, now()))
    return one("SELECT * FROM footage WHERE id=?", (fid,))


def list_footage(brand_id: int):
    return query("SELECT * FROM footage WHERE brand_id=? ORDER BY id DESC", (brand_id,))


def get_footage(fid: int):
    return one("SELECT * FROM footage WHERE id=?", (fid,))


def delete_footage(fid: int):
    execute("DELETE FROM footage WHERE id=?", (fid,))
