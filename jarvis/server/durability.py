"""Maintenance de longévité pour les bases SQLite critiques de JARVIS."""
from __future__ import annotations

import hashlib
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


class DurabilityMaintenance:
    """Vérifie et sauvegarde les bases avec l'API SQLite de backup.

    Les sauvegardes sont cohérentes même lorsque SQLite utilise le mode WAL.
    Le thread est volontairement simple : il ne remplace pas une sauvegarde
    hors machine, mais protège contre une mise à jour ou une corruption locale.
    """

    def __init__(self, db_paths, backup_dir="data/backups", interval_hours=24,
                 keep_per_database=14):
        self.db_paths = [str(Path(p)) for p in db_paths if p]
        self.backup_dir = Path(backup_dir)
        self.interval_seconds = max(3600, float(interval_hours) * 3600)
        self.keep = max(2, min(int(keep_per_database), 365))
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.RLock()
        self._status = {
            "enabled": False,
            "running": False,
            "last_run_at": 0,
            "last_ok": None,
            "last_error": "",
            "files": [],
            "next_run_at": 0,
        }

    def start(self):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._status["enabled"] = True
            self._status["next_run_at"] = time.time() + self.interval_seconds
            self._thread = threading.Thread(
                target=self._loop, daemon=True, name="jarvis-durable-backups")
            self._thread.start()

    def close(self):
        self._stop.set()

    def status(self):
        with self._lock:
            return dict(self._status)

    def _loop(self):
        while not self._stop.wait(self.interval_seconds):
            self.backup_now()
            with self._lock:
                self._status["next_run_at"] = time.time() + self.interval_seconds

    @staticmethod
    def _quick_check(path: str):
        with sqlite3.connect(path, timeout=30) as db:
            row = db.execute("PRAGMA quick_check").fetchone()
        result = str(row[0] if row else "")
        if result.lower() != "ok":
            raise RuntimeError(f"PRAGMA quick_check a retourné : {result}")

    @staticmethod
    def _sha256(path: Path):
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def backup_now(self):
        with self._lock:
            if self._status["running"]:
                return self.status()
            self._status["running"] = True
        created = []
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            for source_name in self.db_paths:
                source = Path(source_name)
                if not source.exists():
                    continue
                self._quick_check(str(source))
                destination = self.backup_dir / f"{source.stem}_{stamp}.db"
                temporary = destination.with_suffix(".db.tmp")
                if temporary.exists():
                    temporary.unlink()
                with sqlite3.connect(str(source), timeout=30) as src:
                    with sqlite3.connect(str(temporary), timeout=30) as dst:
                        src.backup(dst)
                self._quick_check(str(temporary))
                os.replace(temporary, destination)
                created.append({
                    "source": str(source),
                    "backup": str(destination),
                    "bytes": destination.stat().st_size,
                    "sha256": self._sha256(destination),
                })
                self._prune(source.stem)
            with self._lock:
                self._status.update({
                    "last_run_at": time.time(), "last_ok": True,
                    "last_error": "", "files": created,
                    "next_run_at": time.time() + self.interval_seconds,
                })
        except Exception as exc:
            with self._lock:
                self._status.update({
                    "last_run_at": time.time(), "last_ok": False,
                    "last_error": str(exc)[:1000], "files": created,
                    "next_run_at": time.time() + self.interval_seconds,
                })
        finally:
            with self._lock:
                self._status["running"] = False
        return self.status()

    def _prune(self, stem: str):
        backups = sorted(
            self.backup_dir.glob(f"{stem}_*.db"),
            key=lambda p: p.stat().st_mtime, reverse=True)
        for old in backups[self.keep:]:
            old.unlink(missing_ok=True)
