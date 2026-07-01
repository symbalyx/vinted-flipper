"""Stockage SQLite transactionnel des missions Agency.

La v5.6 ajoute :
- migrations de schéma sans perte de données ;
- heartbeat et reprise après crash ;
- retries persistants avec ``next_run_at`` ;
- checkpoints d'étape ;
- mémoire inter-missions et artefacts ;
- cycles de réparation avant qu'une mission puisse être marquée terminée.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


class MissionStore:
    def __init__(self, path: str = "data/agency.db"):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()
        self._migrate()
        self.mark_orphaned_running()

    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def _init_db(self):
        with self._lock, self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS missions (
              id TEXT PRIMARY KEY,
              goal TEXT NOT NULL,
              status TEXT NOT NULL,
              summary TEXT NOT NULL DEFAULT '',
              result TEXT NOT NULL DEFAULT '',
              error TEXT NOT NULL DEFAULT '',
              max_minutes INTEGER NOT NULL,
              max_steps INTEGER NOT NULL,
              max_agents INTEGER NOT NULL,
              created_at REAL NOT NULL,
              updated_at REAL NOT NULL,
              started_at REAL,
              finished_at REAL,
              metadata_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS mission_steps (
              id TEXT PRIMARY KEY,
              mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
              seq INTEGER NOT NULL,
              role TEXT NOT NULL,
              title TEXT NOT NULL,
              instructions TEXT NOT NULL,
              depends_json TEXT NOT NULL DEFAULT '[]',
              status TEXT NOT NULL,
              result TEXT NOT NULL DEFAULT '',
              error TEXT NOT NULL DEFAULT '',
              started_at REAL,
              finished_at REAL
            );
            CREATE INDEX IF NOT EXISTS idx_mission_steps_mission ON mission_steps(mission_id, seq);
            CREATE TABLE IF NOT EXISTS mission_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
              created_at REAL NOT NULL,
              kind TEXT NOT NULL,
              message TEXT NOT NULL,
              meta_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_mission_events_mission ON mission_events(mission_id, id);
            CREATE TABLE IF NOT EXISTS agency_memory (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              created_at REAL NOT NULL,
              kind TEXT NOT NULL,
              title TEXT NOT NULL,
              content TEXT NOT NULL,
              tags_json TEXT NOT NULL DEFAULT '[]',
              source_mission_id TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_agency_memory_created ON agency_memory(created_at DESC);
            CREATE TABLE IF NOT EXISTS mission_artifacts (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
              step_id TEXT NOT NULL DEFAULT '',
              created_at REAL NOT NULL,
              kind TEXT NOT NULL,
              name TEXT NOT NULL,
              uri TEXT NOT NULL DEFAULT '',
              sha256 TEXT NOT NULL DEFAULT '',
              metadata_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_mission_artifacts_mission ON mission_artifacts(mission_id, id);
            CREATE TABLE IF NOT EXISTS mission_action_receipts (
              receipt_key TEXT PRIMARY KEY,
              mission_id TEXT NOT NULL,
              step_id TEXT NOT NULL,
              action TEXT NOT NULL,
              params_hash TEXT NOT NULL,
              result TEXT NOT NULL,
              created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_action_receipts_step
              ON mission_action_receipts(mission_id,step_id,action);
            """)

    def _columns(self, db, table: str) -> set[str]:
        return {row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}

    def _ensure_column(self, db, table: str, name: str, ddl: str):
        if name not in self._columns(db, table):
            db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")

    def _migrate(self):
        """Migrations additives compatibles avec les bases v5.5 existantes."""
        with self._lock, self._connect() as db:
            mission_cols = {
                "completion_criteria": "TEXT NOT NULL DEFAULT ''",
                "continue_until_done": "INTEGER NOT NULL DEFAULT 1",
                "repair_cycle": "INTEGER NOT NULL DEFAULT 0",
                "failure_cycle": "INTEGER NOT NULL DEFAULT 0",
                "max_repair_cycles": "INTEGER NOT NULL DEFAULT 3",
                "heartbeat_at": "REAL",
                "last_progress_at": "REAL",
                "next_run_at": "REAL NOT NULL DEFAULT 0",
                "lease_owner": "TEXT NOT NULL DEFAULT ''",
                "lease_expires": "REAL NOT NULL DEFAULT 0",
                "version": "INTEGER NOT NULL DEFAULT 1",
            }
            for name, ddl in mission_cols.items():
                self._ensure_column(db, "missions", name, ddl)
            step_cols = {
                "attempt": "INTEGER NOT NULL DEFAULT 0",
                "max_attempts": "INTEGER NOT NULL DEFAULT 4",
                "failure_cycle": "INTEGER NOT NULL DEFAULT 0",
                "next_run_at": "REAL NOT NULL DEFAULT 0",
                "heartbeat_at": "REAL",
                "checkpoint_json": "TEXT NOT NULL DEFAULT '{}'",
                "idempotency_key": "TEXT NOT NULL DEFAULT ''",
                "error_kind": "TEXT NOT NULL DEFAULT ''",
            }
            for name, ddl in step_cols.items():
                self._ensure_column(db, "mission_steps", name, ddl)
            # Reçus d'idempotence en deux phases (v5.7) : un reçu peut être
            # « in_flight » (effet en cours, écrit AVANT l'action) puis
            # « succeeded ». Les reçus v5.6 existants sont réputés « succeeded ».
            self._ensure_column(db, "mission_action_receipts", "status",
                                "TEXT NOT NULL DEFAULT 'succeeded'")
            self._ensure_column(db, "mission_action_receipts", "updated_at", "REAL")
            db.execute("CREATE INDEX IF NOT EXISTS idx_missions_runnable ON missions(status,next_run_at)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_steps_runnable ON mission_steps(mission_id,status,next_run_at)")

    def mark_orphaned_running(self):
        """Au démarrage, aucune thread de l'ancien processus ne peut encore vivre.

        Les tâches en cours sont donc remises dans un état reprenable, sans être
        déclarées réussies ni échouées.
        """
        now = time.time()
        with self._lock, self._connect() as db:
            expired = [row["id"] for row in db.execute(
                """SELECT id FROM missions
                   WHERE status IN ('planning','running','verifying')
                     AND (lease_expires IS NULL OR lease_expires<=?)""", (now,)).fetchall()]
            if expired:
                marks = ",".join("?" for _ in expired)
                db.execute(f"""UPDATE missions
                               SET status='interrupted', updated_at=?, next_run_at=?,
                                   lease_owner='', lease_expires=0
                               WHERE id IN ({marks})""", (now, now, *expired))
                db.execute(f"""UPDATE mission_steps
                               SET status='retry_wait', started_at=NULL, next_run_at=?,
                                   heartbeat_at=NULL
                               WHERE status='running' AND mission_id IN ({marks})""",
                           (now, *expired))

    def create(self, mission_id: str, goal: str, max_minutes: int, max_steps: int,
               max_agents: int, metadata: dict | None = None,
               completion_criteria: str = "", continue_until_done: bool = True,
               max_repair_cycles: int = 3):
        now = time.time()
        with self._lock, self._connect() as db:
            db.execute("""INSERT INTO missions
                (id,goal,status,max_minutes,max_steps,max_agents,created_at,updated_at,
                 metadata_json,completion_criteria,continue_until_done,max_repair_cycles,
                 heartbeat_at,last_progress_at,next_run_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (mission_id, goal, "queued", max_minutes, max_steps, max_agents,
                 now, now, json.dumps(metadata or {}, ensure_ascii=False),
                 completion_criteria, 1 if continue_until_done else 0,
                 max(0, int(max_repair_cycles)), now, now, now))
        self.event(mission_id, "mission_created", "Mission créée")
        return self.get(mission_id)

    def set_plan(self, mission_id: str, summary: str, steps: list[dict]):
        now = time.time()
        with self._lock, self._connect() as db:
            db.execute("DELETE FROM mission_steps WHERE mission_id=?", (mission_id,))
            self._insert_steps(db, mission_id, steps)
            db.execute("""UPDATE missions SET summary=?, updated_at=?, last_progress_at=?, version=version+1
                          WHERE id=?""", (summary, now, now, mission_id))
        self.event(mission_id, "plan_created", f"Plan créé : {len(steps)} étape(s)")

    def _insert_steps(self, db, mission_id: str, steps: list[dict]):
        for s in steps:
            db.execute("""INSERT INTO mission_steps
                (id,mission_id,seq,role,title,instructions,depends_json,status,
                 max_attempts,idempotency_key,checkpoint_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (s["id"], mission_id, int(s["seq"]), s["role"], s["title"],
                 s["instructions"], json.dumps(s.get("depends_on", [])),
                 s.get("status", "pending"), max(1, int(s.get("max_attempts", 4))),
                 s.get("idempotency_key") or f"{mission_id}:{s['id']}",
                 json.dumps(s.get("checkpoint", {}), ensure_ascii=False)))

    def append_steps(self, mission_id: str, steps: list[dict], summary_suffix: str = ""):
        if not steps:
            return
        now = time.time()
        with self._lock, self._connect() as db:
            self._insert_steps(db, mission_id, steps)
            if summary_suffix:
                db.execute("""UPDATE missions SET summary=trim(summary || ?), updated_at=?,
                              last_progress_at=?, version=version+1 WHERE id=?""",
                           ("\n" + summary_suffix, now, now, mission_id))
            else:
                db.execute("""UPDATE missions SET updated_at=?, last_progress_at=?,
                              version=version+1 WHERE id=?""", (now, now, mission_id))
        self.event(mission_id, "repair_plan_added", f"{len(steps)} étape(s) de réparation ajoutée(s)")

    def update_mission(self, mission_id: str, **fields):
        allowed = {
            "status", "summary", "result", "error", "started_at", "finished_at",
            "completion_criteria", "continue_until_done", "repair_cycle", "failure_cycle",
            "max_repair_cycles", "heartbeat_at", "last_progress_at", "next_run_at",
            "lease_owner", "lease_expires",
        }
        values = {k: v for k, v in fields.items() if k in allowed}
        if not values:
            return
        values["updated_at"] = time.time()
        values["version"] = "__increment__"
        assignments = []
        params = []
        for key, value in values.items():
            if key == "version":
                assignments.append("version=version+1")
            else:
                assignments.append(f"{key}=?")
                params.append(value)
        with self._lock, self._connect() as db:
            db.execute(f"UPDATE missions SET {', '.join(assignments)} WHERE id=?",
                       (*params, mission_id))

    def patch_metadata(self, mission_id: str, patch: dict):
        with self._lock, self._connect() as db:
            row = db.execute("SELECT metadata_json FROM missions WHERE id=?", (mission_id,)).fetchone()
            if not row:
                return False
            try:
                data = json.loads(row["metadata_json"] or "{}")
            except Exception:
                data = {}
            data.update(patch or {})
            db.execute("""UPDATE missions SET metadata_json=?, updated_at=?, version=version+1
                          WHERE id=?""", (json.dumps(data, ensure_ascii=False), time.time(), mission_id))
        return True

    def update_step(self, step_id: str, **fields):
        allowed = {
            "status", "result", "error", "started_at", "finished_at", "attempt",
            "max_attempts", "failure_cycle", "next_run_at", "heartbeat_at",
            "checkpoint_json", "error_kind",
        }
        values = {k: v for k, v in fields.items() if k in allowed}
        if not values:
            return
        sql = ", ".join(f"{k}=?" for k in values)
        now = time.time()
        with self._lock, self._connect() as db:
            db.execute(f"UPDATE mission_steps SET {sql} WHERE id=?", (*values.values(), step_id))
            row = db.execute("SELECT mission_id FROM mission_steps WHERE id=?", (step_id,)).fetchone()
            if row:
                db.execute("""UPDATE missions SET updated_at=?, last_progress_at=?, version=version+1
                              WHERE id=?""", (now, now, row["mission_id"]))

    def claim_step(self, step_id: str) -> dict | None:
        """Passe atomiquement une étape prête en RUNNING et incrémente son essai."""
        now = time.time()
        with self._lock, self._connect() as db:
            cur = db.execute("""UPDATE mission_steps
                              SET status='running', attempt=attempt+1, started_at=?, heartbeat_at=?
                              WHERE id=? AND status IN ('pending','retry_wait') AND next_run_at<=?""",
                             (now, now, step_id, now))
            if cur.rowcount != 1:
                return None
            row = db.execute("SELECT * FROM mission_steps WHERE id=?", (step_id,)).fetchone()
        return self._step_dict(row)

    def claim_mission(self, mission_id: str, owner: str, lease_seconds: float = 30) -> bool:
        now = time.time()
        expires = now + max(5, float(lease_seconds))
        with self._lock, self._connect() as db:
            cur = db.execute("""UPDATE missions
                              SET lease_owner=?, lease_expires=?, heartbeat_at=?, updated_at=?
                              WHERE id=? AND (lease_owner='' OR lease_owner=? OR lease_expires<=?)""",
                             (owner, expires, now, now, mission_id, owner, now))
        return cur.rowcount == 1

    def renew_mission_lease(self, mission_id: str, owner: str, lease_seconds: float = 30) -> bool:
        now = time.time()
        with self._lock, self._connect() as db:
            cur = db.execute("""UPDATE missions SET lease_expires=?, heartbeat_at=?, updated_at=?
                              WHERE id=? AND lease_owner=?""",
                             (now + max(5, float(lease_seconds)), now, now, mission_id, owner))
        return cur.rowcount == 1

    def release_mission(self, mission_id: str, owner: str):
        with self._lock, self._connect() as db:
            db.execute("""UPDATE missions SET lease_owner='', lease_expires=0
                          WHERE id=? AND lease_owner=?""", (mission_id, owner))

    def heartbeat_mission(self, mission_id: str):
        now = time.time()
        with self._lock, self._connect() as db:
            db.execute("UPDATE missions SET heartbeat_at=?, updated_at=? WHERE id=?",
                       (now, now, mission_id))

    def heartbeat_step(self, step_id: str):
        with self._lock, self._connect() as db:
            db.execute("UPDATE mission_steps SET heartbeat_at=? WHERE id=?", (time.time(), step_id))

    def save_checkpoint(self, step_id: str, checkpoint: dict):
        self.update_step(step_id, checkpoint_json=json.dumps(checkpoint or {}, ensure_ascii=False))

    def event(self, mission_id: str, kind: str, message: str, meta: dict | None = None):
        with self._lock, self._connect() as db:
            db.execute("INSERT INTO mission_events(mission_id,created_at,kind,message,meta_json) VALUES (?,?,?,?,?)",
                       (mission_id, time.time(), kind, str(message)[:4000],
                        json.dumps(meta or {}, ensure_ascii=False)))

    def add_memory(self, kind: str, title: str, content: str, tags: list[str] | None = None,
                   source_mission_id: str = ""):
        content = str(content or "").strip()
        if not content:
            return None
        with self._lock, self._connect() as db:
            cur = db.execute("""INSERT INTO agency_memory
                (created_at,kind,title,content,tags_json,source_mission_id) VALUES (?,?,?,?,?,?)""",
                (time.time(), str(kind)[:80], str(title)[:300], content[:50000],
                 json.dumps(tags or [], ensure_ascii=False), source_mission_id))
            return cur.lastrowid

    def search_memory(self, query: str, limit: int = 6) -> list[dict]:
        """Recherche locale légère et durable, sans dépendance vectorielle.

        Le classement privilégie les mots du but courant présents dans le titre,
        le contenu ou les tags. Cela évite que les agents repartent de zéro une
        semaine plus tard, même si le fournisseur LLM change.
        """
        words = [w.lower() for w in str(query or "").split() if len(w) >= 4][:12]
        with self._lock, self._connect() as db:
            rows = db.execute("SELECT * FROM agency_memory ORDER BY created_at DESC LIMIT 250").fetchall()
        scored = []
        for row in rows:
            item = dict(row)
            hay = f"{item['title']} {item['content']} {item['tags_json']}".lower()
            score = sum(3 if w in item["title"].lower() else 1 for w in words if w in hay)
            if score or not words:
                try:
                    item["tags"] = json.loads(item.pop("tags_json") or "[]")
                except Exception:
                    item["tags"] = []
                    item.pop("tags_json", None)
                item["score"] = score
                scored.append(item)
        scored.sort(key=lambda x: (x["score"], x["created_at"]), reverse=True)
        return scored[:max(1, min(int(limit), 20))]

    @staticmethod
    def _receipt_parts(mission_id: str, step_id: str, action: str, params: dict):
        canonical = json.dumps(params or {}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        params_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        raw = f"{mission_id}|{step_id}|{action}|{params_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest(), params_hash

    def get_action_receipt(self, mission_id: str, step_id: str, action: str, params: dict):
        if not mission_id or not step_id:
            return None
        key, _ = self._receipt_parts(mission_id, step_id, action, params)
        with self._lock, self._connect() as db:
            row = db.execute("SELECT * FROM mission_action_receipts WHERE receipt_key=?", (key,)).fetchone()
        return dict(row) if row else None

    def record_action_receipt(self, mission_id: str, step_id: str, action: str,
                              params: dict, result: str, status: str = "succeeded"):
        if not mission_id or not step_id:
            return None
        key, params_hash = self._receipt_parts(mission_id, step_id, action, params)
        now = time.time()
        with self._lock, self._connect() as db:
            db.execute("""INSERT OR IGNORE INTO mission_action_receipts
                (receipt_key,mission_id,step_id,action,params_hash,result,created_at,status,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (key, mission_id, step_id, action, params_hash,
                 str(result)[:10000], now, status, now))
        return key

    def begin_action_receipt(self, mission_id: str, step_id: str, action: str, params: dict):
        """Phase 1 (AVANT l'effet) : pose un reçu « in_flight » de façon atomique.

        Retourne (receipt_key, existing) où `existing` est le reçu déjà présent
        (dict) si l'action a déjà été tentée/réussie, sinon None. Empêche le
        double-envoi après un crash : sur rejeu, un reçu « in_flight » bloque la
        ré-exécution (réconciliation requise) et « succeeded » réutilise le résultat.
        """
        if not mission_id or not step_id:
            return None, None
        key, params_hash = self._receipt_parts(mission_id, step_id, action, params)
        now = time.time()
        with self._lock, self._connect() as db:
            row = db.execute("SELECT * FROM mission_action_receipts WHERE receipt_key=?",
                             (key,)).fetchone()
            if row:
                return key, dict(row)
            db.execute("""INSERT INTO mission_action_receipts
                (receipt_key,mission_id,step_id,action,params_hash,result,created_at,status,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (key, mission_id, step_id, action, params_hash, "", now, "in_flight", now))
        return key, None

    def finalize_action_receipt(self, receipt_key: str, result: str, status: str = "succeeded"):
        """Phase 2 (APRÈS l'effet) : marque le reçu « succeeded » (ou autre)."""
        if not receipt_key:
            return
        with self._lock, self._connect() as db:
            db.execute("""UPDATE mission_action_receipts
                SET result=?, status=?, updated_at=? WHERE receipt_key=?""",
                (str(result)[:10000], status, time.time(), receipt_key))

    def add_artifact(self, mission_id: str, kind: str, name: str, uri: str = "",
                     step_id: str = "", sha256: str = "", metadata: dict | None = None):
        with self._lock, self._connect() as db:
            cur = db.execute("""INSERT INTO mission_artifacts
                (mission_id,step_id,created_at,kind,name,uri,sha256,metadata_json)
                VALUES (?,?,?,?,?,?,?,?)""",
                (mission_id, step_id, time.time(), kind, name[:300], uri[:2000],
                 sha256[:128], json.dumps(metadata or {}, ensure_ascii=False)))
            return cur.lastrowid

    def artifacts(self, mission_id: str):
        with self._lock, self._connect() as db:
            rows = db.execute("SELECT * FROM mission_artifacts WHERE mission_id=? ORDER BY id",
                              (mission_id,)).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            try:
                item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
            except Exception:
                item["metadata"] = {}
                item.pop("metadata_json", None)
            out.append(item)
        return out

    def recoverable(self, now: float | None = None, limit: int = 50):
        now = now or time.time()
        with self._lock, self._connect() as db:
            rows = db.execute("""SELECT * FROM missions
                               WHERE status IN ('interrupted','retry_wait','paused')
                                 AND next_run_at<=?
                               ORDER BY updated_at ASC LIMIT ?""", (now, limit)).fetchall()
        return [self._mission_dict(r, include_details=False) for r in rows]

    def _mission_dict(self, row, include_details=True):
        if not row:
            return None
        out = dict(row)
        try:
            out["metadata"] = json.loads(out.pop("metadata_json"))
        except Exception:
            out["metadata"] = {}
            out.pop("metadata_json", None)
        out["continue_until_done"] = bool(out.get("continue_until_done", 1))
        if include_details:
            out["steps"] = self.steps(out["id"])
            out["events"] = self.events(out["id"], limit=150)
            out["artifacts"] = self.artifacts(out["id"])
        return out

    def get(self, mission_id: str):
        with self._lock, self._connect() as db:
            row = db.execute("SELECT * FROM missions WHERE id=?", (mission_id,)).fetchone()
        return self._mission_dict(row)

    def list(self, limit: int = 50):
        limit = max(1, min(int(limit), 200))
        with self._lock, self._connect() as db:
            rows = db.execute("SELECT * FROM missions ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._mission_dict(r, include_details=False) for r in rows]

    def _step_dict(self, row):
        if not row:
            return None
        item = dict(row)
        try:
            item["depends_on"] = json.loads(item.pop("depends_json") or "[]")
        except Exception:
            item["depends_on"] = []
            item.pop("depends_json", None)
        try:
            item["checkpoint"] = json.loads(item.pop("checkpoint_json") or "{}")
        except Exception:
            item["checkpoint"] = {}
            item.pop("checkpoint_json", None)
        return item

    def steps(self, mission_id: str):
        with self._lock, self._connect() as db:
            rows = db.execute("SELECT * FROM mission_steps WHERE mission_id=? ORDER BY seq,id", (mission_id,)).fetchall()
        return [self._step_dict(row) for row in rows]

    def events(self, mission_id: str, limit: int = 100):
        with self._lock, self._connect() as db:
            rows = db.execute("""SELECT id,created_at,kind,message,meta_json FROM mission_events
                               WHERE mission_id=? ORDER BY id DESC LIMIT ?""",
                              (mission_id, max(1, min(int(limit), 500)))).fetchall()
        out = []
        for row in reversed(rows):
            item = dict(row)
            try:
                item["meta"] = json.loads(item.pop("meta_json"))
            except Exception:
                item["meta"] = {}
                item.pop("meta_json", None)
            out.append(item)
        return out

    def delete(self, mission_id: str) -> bool:
        with self._lock, self._connect() as db:
            cur = db.execute("DELETE FROM missions WHERE id=?", (mission_id,))
        return cur.rowcount > 0
