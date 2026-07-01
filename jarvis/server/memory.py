"""
╔══════════════════════════════════════════════════════════════╗
║  JARVIS v5 — Mémoire long terme RAG (rappel sémantique)       ║
╚══════════════════════════════════════════════════════════════╝

Récupère uniquement les souvenirs PERTINENTS pour le message courant, au lieu
de tout balancer dans le prompt. Embeddings via Ollama si disponible
(`ollama pull nomic-embed-text`), sinon repli lexical automatique.
Zéro dépendance pip obligatoire, persisté en JSON.
"""

import json
import math
import logging
import threading
from pathlib import Path
from collections import Counter

import requests

logger = logging.getLogger("JARVIS.memory")


class VectorMemory:
    def __init__(self, store="memory/vectors.json",
                 ollama_url="http://localhost:11434/api/embeddings",
                 embed_model="nomic-embed-text"):
        self.path = Path(store)
        self.url = ollama_url
        self.model = embed_model
        self._lock = threading.Lock()
        self.items = self._load()
        self.has_embed = self._probe()

    def _load(self):
        if self.path.exists():
            try:
                return json.loads(self.path.read_text())
            except Exception:
                pass
        return []

    def _save(self):
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            try:
                self.path.write_text(json.dumps(self.items, ensure_ascii=False))
            except Exception:
                pass

    def _probe(self):
        try:
            requests.post(self.url, json={"model": self.model, "prompt": "ok"}, timeout=3)
            logger.info("🧬 Mémoire RAG : embeddings Ollama actifs.")
            return True
        except Exception:
            logger.info("🧬 Mémoire RAG : mode lexical (Ollama embeddings absents).")
            return False

    def _embed(self, text):
        if not self.has_embed:
            return None
        try:
            r = requests.post(self.url, json={"model": self.model, "prompt": text}, timeout=10)
            return r.json().get("embedding")
        except Exception:
            return None

    def add(self, text, kind="fact"):
        text = (text or "").strip()
        if not text:
            return
        with self._lock:
            self.items.append({"text": text, "kind": kind, "emb": self._embed(text)})
            self.items = self.items[-500:]
        self._save()

    @staticmethod
    def _cos(a, b):
        d = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return d / (na * nb) if na and nb else 0.0

    @staticmethod
    def _lexical(q, t):
        qa, ta = Counter(q.lower().split()), Counter(t.lower().split())
        inter = sum((qa & ta).values())
        return inter / (len(qa) + 1)

    def recall(self, query, k=4):
        with self._lock:
            items = list(self.items)
        if not items:
            return []
        qe = self._embed(query)
        if qe:
            scored = [(self._cos(qe, it["emb"]), it) for it in items if it.get("emb")]
        else:
            scored = [(self._lexical(query, it["text"]), it) for it in items]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [it["text"] for s, it in scored[:k] if s > 0.15]
