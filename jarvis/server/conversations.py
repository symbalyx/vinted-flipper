"""
╔══════════════════════════════════════════════════════════════╗
║  JARVIS v5.2 — Conversations persistantes (côté serveur)      ║
╚══════════════════════════════════════════════════════════════╝

Plusieurs conversations distinctes, chacune avec son historique, persistées en
JSON (cohérent avec le reste du projet), thread-safe. L'app web peut lister,
créer, ouvrir et supprimer des conversations — comme ChatGPT, mais l'état vit
sur le serveur (utilisable depuis plusieurs appareils).
"""

import json
import threading
from pathlib import Path
from datetime import datetime
from uuid import uuid4


class ConversationStore:
    def __init__(self, path="memory/conversations.json", max_conv=100, max_msgs=200):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_conv = max_conv
        self.max_msgs = max_msgs
        self._lock = threading.Lock()
        self.data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text())
            except Exception:
                pass
        return {}

    def save(self):
        with self._lock:
            # garde les conversations les plus récentes
            if len(self.data) > self.max_conv:
                keep = sorted(self.data.values(), key=lambda c: c.get("updated", ""),
                              reverse=True)[:self.max_conv]
                self.data = {c["id"]: c for c in keep}
            try:
                self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2))
            except Exception:
                pass

    def create(self, title="Nouvelle conversation") -> dict:
        cid = uuid4().hex[:12]
        conv = {"id": cid, "title": title, "messages": [],
                "created": datetime.now().isoformat(), "updated": datetime.now().isoformat()}
        self.data[cid] = conv
        self.save()
        return conv

    def get(self, cid: str):
        return self.data.get(cid)

    def delete(self, cid: str) -> bool:
        if cid in self.data:
            del self.data[cid]
            self.save()
            return True
        return False

    def touch(self, cid: str, title: str = None):
        c = self.data.get(cid)
        if not c:
            return
        c["updated"] = datetime.now().isoformat()
        if title and (c["title"] == "Nouvelle conversation" or not c["title"]):
            c["title"] = title[:60]
        # borne la taille de l'historique
        if len(c["messages"]) > self.max_msgs:
            c["messages"] = c["messages"][-self.max_msgs:]

    def list(self) -> list:
        out = [{"id": c["id"], "title": c["title"], "updated": c.get("updated", ""),
                "count": len(c["messages"])} for c in self.data.values()]
        return sorted(out, key=lambda c: c["updated"], reverse=True)
