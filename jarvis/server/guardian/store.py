"""
Persistance SQLite du Gardien (remplace progressivement les JSON épars).

Tables : events, decisions, devices, approvals, settings, notifications.
Écritures atomiques (transactions SQLite, WAL). Rétention configurable +
purge automatique. Export JSON. Aucune donnée personnelle dans Git.
"""

import json
import time
import sqlite3
import threading
import secrets
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL, kind TEXT, state TEXT, level TEXT,
  summary TEXT, meta TEXT, snapshot TEXT);
CREATE TABLE IF NOT EXISTS decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL, state TEXT, should_speak INTEGER, speech_level TEXT,
  siren_allowed INTEGER, reason TEXT, phrase TEXT, meta TEXT);
CREATE TABLE IF NOT EXISTS devices (
  id TEXT PRIMARY KEY, name TEXT, role TEXT, token_hash TEXT,
  created REAL, last_seen REAL, revoked INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS approvals (
  token TEXT PRIMARY KEY, action TEXT, params TEXT, level TEXT,
  created REAL, expires REAL, used INTEGER DEFAULT 0, result TEXT);
CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, channel TEXT, ok INTEGER, detail TEXT);
CREATE TABLE IF NOT EXISTS settings (k TEXT PRIMARY KEY, v TEXT);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_decisions_ts ON decisions(ts);
"""


class GuardianStore:
    def __init__(self, db_path: str = "memory/guardian.db", retention_days: int = 7):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.retention_days = retention_days
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    # ── Écritures ──────────────────────────────────────────────
    def add_event(self, kind, summary, state="", level="", meta=None, snapshot=""):
        with self._lock:
            self._conn.execute(
                "INSERT INTO events(ts,kind,state,level,summary,meta,snapshot) VALUES(?,?,?,?,?,?,?)",
                (time.time(), kind, state, level, summary,
                 json.dumps(meta or {}, ensure_ascii=False), snapshot))
            self._conn.commit()

    def add_decision(self, decision, phrase="", meta=None):
        with self._lock:
            self._conn.execute(
                "INSERT INTO decisions(ts,state,should_speak,speech_level,siren_allowed,reason,phrase,meta)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (time.time(), decision.state, int(decision.should_speak), decision.speech_level,
                 int(decision.siren_allowed), decision.reason, phrase,
                 json.dumps(meta or {}, ensure_ascii=False)))
            self._conn.commit()

    def add_notification(self, channel, ok, detail=""):
        with self._lock:
            self._conn.execute(
                "INSERT INTO notifications(ts,channel,ok,detail) VALUES(?,?,?,?)",
                (time.time(), channel, int(bool(ok)), detail))
            self._conn.commit()

    # ── Approbations (usage unique, expiration) ────────────────
    def create_approval(self, action, params, level, ttl_seconds=120) -> str:
        token = secrets.token_urlsafe(24)
        now = time.time()
        with self._lock:
            self._conn.execute(
                "INSERT INTO approvals(token,action,params,level,created,expires,used) VALUES(?,?,?,?,?,?,0)",
                (token, action, json.dumps(params or {}, ensure_ascii=False), level,
                 now, now + ttl_seconds))
            self._conn.commit()
        return token

    def consume_approval(self, token: str):
        """Retourne (row|None, error). Usage unique + vérif expiration."""
        with self._lock:
            row = self._conn.execute("SELECT * FROM approvals WHERE token=?", (token,)).fetchone()
            if not row:
                return None, "Jeton d'approbation inconnu"
            if row["used"]:
                return None, "Jeton déjà utilisé"
            if time.time() > row["expires"]:
                return None, "Jeton expiré"
            self._conn.execute("UPDATE approvals SET used=1 WHERE token=?", (token,))
            self._conn.commit()
            return dict(row), ""

    # ── Lecture / export ───────────────────────────────────────
    def recent_events(self, limit=50):
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM events ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def recent_decisions(self, limit=50):
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM decisions ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def export(self) -> dict:
        return {"events": self.recent_events(100000),
                "decisions": self.recent_decisions(100000)}

    # ── Maintenance ────────────────────────────────────────────
    def purge_old(self):
        cutoff = time.time() - self.retention_days * 86400
        with self._lock:
            for tbl in ("events", "decisions", "notifications"):
                self._conn.execute(f"DELETE FROM {tbl} WHERE ts < ?", (cutoff,))
            self._conn.execute("DELETE FROM approvals WHERE expires < ?", (time.time() - 86400,))
            self._conn.commit()

    def wipe(self):
        with self._lock:
            for tbl in ("events", "decisions", "notifications", "approvals"):
                self._conn.execute(f"DELETE FROM {tbl}")
            self._conn.commit()

    def close(self):
        with self._lock:
            self._conn.close()
