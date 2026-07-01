"""
╔══════════════════════════════════════════════════════════════╗
║  JARVIS v4 — Notifications à distance                         ║
║  Telegram (texte + PHOTO) — reçois l'intrus sur ton téléphone║
╚══════════════════════════════════════════════════════════════╝

Permet à JARVIS de te joindre où que tu sois (hors réseau local), avec la
PHOTO de l'événement. Idéal pour l'anti-intrusion : tu reçois le snapshot du
visiteur surprise directement sur ton mobile.

Config (2 minutes) :
  1. Crée un bot : parle à @BotFather sur Telegram → /newbot → récupère le TOKEN
  2. Récupère ton chat_id : parle à ton bot, puis ouvre
     https://api.telegram.org/bot<TOKEN>/getUpdates → champ "chat":{"id":...}
  3. Exporte :
        export TELEGRAM_BOT_TOKEN=123456:ABC...
        export TELEGRAM_CHAT_ID=987654321

Dégradation gracieuse : si non configuré, les méthodes renvoient un message
clair et JARVIS continue de tourner normalement.
"""

import os
import json
import time
import logging
import threading
import requests

logger = logging.getLogger("JARVIS.notify")


class RemoteNotifier:
    def __init__(self, token: str = "", chat_id: str = ""):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        self.mode = "telegram" if (self.token and self.chat_id) else "désactivé"
        logger.info(f"📲 Notifications distantes: {self.mode}")

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)

    @property
    def _base(self) -> str:
        return f"https://api.telegram.org/bot{self.token}"

    def send(self, text: str) -> str:
        if not self.enabled:
            return "Notifications distantes non configurées (TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID)."
        try:
            r = requests.post(f"{self._base}/sendMessage",
                              data={"chat_id": self.chat_id, "text": text},
                              timeout=10)
            r.raise_for_status()
            return "📲 Notification Telegram envoyée."
        except Exception as e:
            return f"Échec notification Telegram : {e}"

    def send_photo(self, image_path: str, caption: str = "") -> str:
        if not self.enabled:
            return "Notifications distantes non configurées."
        try:
            with open(image_path, "rb") as f:
                r = requests.post(f"{self._base}/sendPhoto",
                                  data={"chat_id": self.chat_id, "caption": caption[:1024]},
                                  files={"photo": f}, timeout=20)
            r.raise_for_status()
            return "📲 Photo envoyée sur Telegram."
        except Exception as e:
            return f"Échec envoi photo Telegram : {e}"

    def send_photo_bytes(self, image_bytes: bytes, caption: str = "") -> str:
        if not self.enabled:
            return "Notifications distantes non configurées."
        try:
            r = requests.post(f"{self._base}/sendPhoto",
                              data={"chat_id": self.chat_id, "caption": caption[:1024]},
                              files={"photo": ("jarvis.jpg", image_bytes, "image/jpeg")},
                              timeout=20)
            r.raise_for_status()
            return "📲 Photo envoyée sur Telegram."
        except Exception as e:
            return f"Échec envoi photo Telegram : {e}"

    # ── Question interactive « connu / inconnu » ──────────────
    def ask_identity(self, qid: str, question: str, image_path: str = "") -> str:
        """Envoie une question avec 2 boutons (Connu / Inconnu) sur Telegram.

        Les réponses sont récupérées par le poller (start_callback_listener).
        """
        if not self.enabled:
            return "Telegram non configuré — question posée seulement sur le dashboard."
        markup = json.dumps({"inline_keyboard": [[
            {"text": "✅ Je le connais", "callback_data": f"known:{qid}"},
            {"text": "🚨 Inconnu !", "callback_data": f"unknown:{qid}"},
        ]]})
        try:
            if image_path:
                with open(image_path, "rb") as f:
                    r = requests.post(f"{self._base}/sendPhoto",
                                      data={"chat_id": self.chat_id, "caption": question[:1024],
                                            "reply_markup": markup},
                                      files={"photo": f}, timeout=20)
            else:
                r = requests.post(f"{self._base}/sendMessage",
                                  data={"chat_id": self.chat_id, "text": question,
                                        "reply_markup": markup}, timeout=15)
            r.raise_for_status()
            return "📲 Question envoyée sur Telegram (Connu / Inconnu)."
        except Exception as e:
            return f"Échec question Telegram : {e}"

    def _answer_callback(self, callback_id: str, text: str = ""):
        try:
            requests.post(f"{self._base}/answerCallbackQuery",
                          data={"callback_query_id": callback_id, "text": text}, timeout=10)
        except Exception:
            pass

    def start_callback_listener(self, handler):
        """Démarre un thread de long-polling Telegram.

        `handler(qid, known: bool)` est appelé quand l'utilisateur tape un bouton.
        """
        if not self.enabled:
            return
        def _loop():
            offset = None
            while True:
                try:
                    params = {"timeout": 30}
                    if offset is not None:
                        params["offset"] = offset
                    r = requests.get(f"{self._base}/getUpdates", params=params, timeout=40)
                    for upd in r.json().get("result", []):
                        offset = upd["update_id"] + 1
                        cq = upd.get("callback_query")
                        if not cq:
                            continue
                        # Sécurité : n'accepter QUE les réponses du propriétaire
                        sender = str(cq.get("from", {}).get("id", ""))
                        chat = str(cq.get("message", {}).get("chat", {}).get("id", ""))
                        if str(self.chat_id) not in (sender, chat):
                            self._answer_callback(cq["id"], "Non autorisé.")
                            continue
                        data = cq.get("data", "")
                        if ":" in data:
                            action, qid = data.split(":", 1)
                            try:
                                handler(qid, action == "known")
                            except Exception as e:
                                logger.warning(f"handler callback KO: {e}")
                            self._answer_callback(cq["id"],
                                                  "Connu ✅" if action == "known" else "Inconnu 🚨 — j'agis.")
                except Exception as e:
                    logger.debug(f"poll Telegram: {e}")
                    time.sleep(5)
        threading.Thread(target=_loop, daemon=True, name="telegram-poll").start()
        logger.info("📲 Écoute des réponses Telegram (Connu/Inconnu) active.")
