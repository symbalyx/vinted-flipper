"""Stockage SQLite du CRM de prospection JARVIS."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path


class ProspectingStore:
    def __init__(self, path: str = "data/prospecting.db"):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=30000")
        return db

    def _init_db(self):
        with self._lock, self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS prospects (
              id TEXT PRIMARY KEY,
              company_name TEXT NOT NULL,
              contact_name TEXT NOT NULL DEFAULT '',
              public_email TEXT NOT NULL DEFAULT '',
              website TEXT NOT NULL DEFAULT '',
              phone TEXT NOT NULL DEFAULT '',
              region TEXT NOT NULL DEFAULT '',
              source_url TEXT NOT NULL,
              source_type TEXT NOT NULL DEFAULT 'official_website',
              consent_basis TEXT NOT NULL DEFAULT 'public_b2b',
              status TEXT NOT NULL DEFAULT 'new',
              score INTEGER NOT NULL DEFAULT 0,
              score_reason TEXT NOT NULL DEFAULT '',
              notes TEXT NOT NULL DEFAULT '',
              tags_json TEXT NOT NULL DEFAULT '[]',
              do_not_contact INTEGER NOT NULL DEFAULT 0,
              created_at REAL NOT NULL,
              updated_at REAL NOT NULL,
              last_contact_at REAL,
              next_followup_at REAL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_prospect_company_source
              ON prospects(lower(company_name), lower(source_url));
            CREATE INDEX IF NOT EXISTS idx_prospect_score ON prospects(do_not_contact,status,score DESC);
            CREATE TABLE IF NOT EXISTS outreach_drafts (
              id TEXT PRIMARY KEY,
              prospect_id TEXT NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
              channel TEXT NOT NULL DEFAULT 'email',
              subject TEXT NOT NULL DEFAULT '',
              body TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'draft',
              created_at REAL NOT NULL,
              updated_at REAL NOT NULL,
              approved_at REAL,
              sent_at REAL
            );
            CREATE INDEX IF NOT EXISTS idx_draft_prospect ON outreach_drafts(prospect_id,created_at DESC);
            CREATE TABLE IF NOT EXISTS prospect_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              prospect_id TEXT NOT NULL DEFAULT '',
              created_at REAL NOT NULL,
              kind TEXT NOT NULL,
              message TEXT NOT NULL,
              meta_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_prospect_events ON prospect_events(prospect_id,id);
            CREATE TABLE IF NOT EXISTS suppression_list (
              key TEXT PRIMARY KEY,
              kind TEXT NOT NULL,
              reason TEXT NOT NULL DEFAULT '',
              created_at REAL NOT NULL
            );
            """)

    def add(self, data: dict) -> dict:
        now = time.time()
        pid = data.get("id") or uuid.uuid4().hex
        with self._lock, self._connect() as db:
            try:
                db.execute("""INSERT INTO prospects
                    (id,company_name,contact_name,public_email,website,phone,region,
                     source_url,source_type,consent_basis,status,score,score_reason,
                     notes,tags_json,do_not_contact,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (pid, data["company_name"], data.get("contact_name", ""),
                     data.get("public_email", ""), data.get("website", ""),
                     data.get("phone", ""), data.get("region", ""), data["source_url"],
                     data.get("source_type", "official_website"),
                     data.get("consent_basis", "public_b2b"), data.get("status", "new"),
                     int(data.get("score", 0)), data.get("score_reason", ""),
                     data.get("notes", ""), json.dumps(data.get("tags", []), ensure_ascii=False),
                     1 if data.get("do_not_contact") else 0, now, now))
            except sqlite3.IntegrityError as exc:
                raise ValueError("Ce prospect et cette source existent déjà") from exc
        self.event(pid, "created", "Prospect ajouté", {"source_url": data["source_url"]})
        return self.get(pid)

    def update(self, prospect_id: str, **fields):
        allowed = {
            "contact_name", "public_email", "website", "phone", "region", "source_url",
            "source_type", "consent_basis", "status", "score", "score_reason", "notes",
            "do_not_contact", "last_contact_at", "next_followup_at",
        }
        values = {k: v for k, v in fields.items() if k in allowed}
        if "do_not_contact" in values:
            values["do_not_contact"] = 1 if values["do_not_contact"] else 0
        if not values:
            return self.get(prospect_id)
        values["updated_at"] = time.time()
        with self._lock, self._connect() as db:
            db.execute(
                f"UPDATE prospects SET {', '.join(f'{k}=?' for k in values)} WHERE id=?",
                (*values.values(), prospect_id))
        return self.get(prospect_id)

    def get(self, prospect_id: str):
        with self._lock, self._connect() as db:
            row = db.execute("SELECT * FROM prospects WHERE id=?", (prospect_id,)).fetchone()
        return self._prospect(row)

    def list(self, limit: int = 100, status: str = "", min_score: int = 0):
        limit = max(1, min(int(limit), 500))
        sql = "SELECT * FROM prospects WHERE score>=?"
        args = [max(0, min(int(min_score), 100))]
        if status:
            sql += " AND status=?"
            args.append(status)
        sql += " ORDER BY do_not_contact ASC, score DESC, updated_at DESC LIMIT ?"
        args.append(limit)
        with self._lock, self._connect() as db:
            rows = db.execute(sql, args).fetchall()
        return [self._prospect(row) for row in rows]

    def create_draft(self, prospect_id: str, subject: str, body: str, channel: str = "email"):
        if not self.get(prospect_id):
            raise KeyError("Prospect introuvable")
        now = time.time()
        did = uuid.uuid4().hex
        with self._lock, self._connect() as db:
            db.execute("""INSERT INTO outreach_drafts
                (id,prospect_id,channel,subject,body,status,created_at,updated_at)
                VALUES (?,?,?,?,?,'draft',?,?)""",
                (did, prospect_id, channel, subject, body, now, now))
        self.event(prospect_id, "draft_created", "Brouillon créé", {"draft_id": did})
        return self.get_draft(did)

    def get_draft(self, draft_id: str):
        with self._lock, self._connect() as db:
            row = db.execute("SELECT * FROM outreach_drafts WHERE id=?", (draft_id,)).fetchone()
        return dict(row) if row else None

    def drafts(self, prospect_id: str = "", limit: int = 100):
        with self._lock, self._connect() as db:
            if prospect_id:
                rows = db.execute("""SELECT * FROM outreach_drafts WHERE prospect_id=?
                                   ORDER BY created_at DESC LIMIT ?""", (prospect_id, limit)).fetchall()
            else:
                rows = db.execute("""SELECT * FROM outreach_drafts ORDER BY created_at DESC LIMIT ?""",
                                  (limit,)).fetchall()
        return [dict(row) for row in rows]

    def mark_draft_sent(self, draft_id: str):
        now = time.time()
        with self._lock, self._connect() as db:
            row = db.execute("SELECT prospect_id FROM outreach_drafts WHERE id=?", (draft_id,)).fetchone()
            if not row:
                raise KeyError("Brouillon introuvable")
            db.execute("""UPDATE outreach_drafts SET status='sent', sent_at=?, updated_at=? WHERE id=?""",
                       (now, now, draft_id))
            db.execute("""UPDATE prospects SET status='contacted', last_contact_at=?, updated_at=?
                          WHERE id=?""", (now, now, row["prospect_id"]))
        self.event(row["prospect_id"], "sent", "Message envoyé", {"draft_id": draft_id})

    def suppress(self, key: str, kind: str, reason: str = ""):
        key = key.strip().lower()
        with self._lock, self._connect() as db:
            db.execute("""INSERT INTO suppression_list(key,kind,reason,created_at)
                          VALUES (?,?,?,?) ON CONFLICT(key) DO UPDATE SET
                          kind=excluded.kind,reason=excluded.reason""",
                       (key, kind, reason[:1000], time.time()))
        return True

    def is_suppressed(self, email: str = "", domain: str = "") -> bool:
        keys = [x.strip().lower() for x in (email, domain) if x]
        if not keys:
            return False
        with self._lock, self._connect() as db:
            marks = ",".join("?" for _ in keys)
            row = db.execute(f"SELECT 1 FROM suppression_list WHERE key IN ({marks}) LIMIT 1", keys).fetchone()
        return bool(row)

    def sends_since(self, since: float, domain: str = "") -> int:
        sql = """SELECT count(*) AS n FROM outreach_drafts d JOIN prospects p ON p.id=d.prospect_id
                 WHERE d.sent_at IS NOT NULL AND d.sent_at>=?"""
        args = [since]
        if domain:
            sql += " AND lower(p.public_email) LIKE ?"
            args.append("%@" + domain.lower())
        with self._lock, self._connect() as db:
            row = db.execute(sql, args).fetchone()
        return int(row["n"] if row else 0)

    def last_send_at(self):
        with self._lock, self._connect() as db:
            row = db.execute("SELECT max(sent_at) AS ts FROM outreach_drafts").fetchone()
        return row["ts"] if row else None

    def event(self, prospect_id: str, kind: str, message: str, meta: dict | None = None):
        with self._lock, self._connect() as db:
            db.execute("""INSERT INTO prospect_events
                (prospect_id,created_at,kind,message,meta_json) VALUES (?,?,?,?,?)""",
                (prospect_id, time.time(), kind, str(message)[:2000],
                 json.dumps(meta or {}, ensure_ascii=False)))

    def events(self, prospect_id: str, limit: int = 100):
        with self._lock, self._connect() as db:
            rows = db.execute("""SELECT * FROM prospect_events WHERE prospect_id=?
                               ORDER BY id DESC LIMIT ?""", (prospect_id, limit)).fetchall()
        out = []
        for row in reversed(rows):
            item = dict(row)
            try:
                item["meta"] = json.loads(item.pop("meta_json") or "{}")
            except Exception:
                item["meta"] = {}
            out.append(item)
        return out

    def delete(self, prospect_id: str) -> bool:
        with self._lock, self._connect() as db:
            cur = db.execute("DELETE FROM prospects WHERE id=?", (prospect_id,))
        return cur.rowcount > 0

    @staticmethod
    def _prospect(row):
        if not row:
            return None
        item = dict(row)
        try:
            item["tags"] = json.loads(item.pop("tags_json") or "[]")
        except Exception:
            item["tags"] = []
            item.pop("tags_json", None)
        item["do_not_contact"] = bool(item.get("do_not_contact"))
        return item
