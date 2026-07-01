"""
╔══════════════════════════════════════════════════════════════╗
║  JARVIS v5 — Journal d'évènements (timeline) + bus temps réel ║
╚══════════════════════════════════════════════════════════════╝

Mémoire unifiée de la maison : scènes, alertes, urgences, chat, automatisations…
Append-only JSONL (cohérent avec le style JSON du projet, pas de DB), thread-safe,
et un bus de souscription pour pousser les évènements en SSE (temps réel).
"""

import json
import threading
from pathlib import Path
from datetime import datetime


class EventLog:
    def __init__(self, path="memory/events.jsonl", max_keep=5000):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.max_keep = max_keep
        self.subscribers = []          # callbacks(ev) pour le bus SSE

    def add(self, kind, message, level="info", meta=None, snapshot=""):
        ev = {"ts": datetime.now().isoformat(timespec="seconds"),
              "kind": kind, "level": level, "message": message,
              "meta": meta or {}, "snapshot": snapshot}
        with self._lock:
            try:
                with self.path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(ev, ensure_ascii=False) + "\n")
            except Exception:
                pass
        for cb in list(self.subscribers):
            try:
                cb(ev)
            except Exception:
                pass
        return ev

    def recent(self, n=100, kind=None):
        if not self.path.exists():
            return []
        with self._lock:
            try:
                lines = self.path.read_text(encoding="utf-8").splitlines()[-self.max_keep:]
            except Exception:
                return []
        evs = []
        for ln in lines:
            if ln.strip():
                try:
                    evs.append(json.loads(ln))
                except Exception:
                    pass
        if kind:
            evs = [e for e in evs if e["kind"] == kind]
        return evs[-n:][::-1]
