"""
╔══════════════════════════════════════════════════════════════╗
║  JARVIS v5 — Moteur proactif (briefing matinal)               ║
╚══════════════════════════════════════════════════════════════╝

JARVIS initie de lui-même : un briefing matinal (météo + actu, adapté aux
habitudes) annoncé sur HomePod et envoyé sur Telegram. Réutilise l'agent (donc
ses outils) pour composer le contenu.
"""

import time
import logging
import threading
from datetime import datetime

logger = logging.getLogger("JARVIS.proactive")

BRIEF_PROMPT = ("Compose un briefing matinal court, drôle et utile : récupère la "
                "météo du jour (utilise ton outil météo pour la ville par défaut) "
                "et propose une intention pour la journée. Garde ta personnalité. "
                "Maximum 4 phrases.")


class ProactiveEngine:
    def __init__(self, agent, announce, notifier, event_log,
                 system_prompt_fn, briefing_hour=8, enabled=True):
        self.agent = agent
        self.announce = announce
        self.notifier = notifier
        self.event_log = event_log
        self.system_prompt_fn = system_prompt_fn
        self.hour = briefing_hour
        self.enabled = enabled
        self._done_today = None

    def briefing_now(self) -> str:
        try:
            text = self.agent.run(BRIEF_PROMPT, self.system_prompt_fn())
        except Exception as e:
            text = None
            logger.warning(f"Briefing KO: {e}")
        if not text:
            text = "Briefing indisponible (backend IA injoignable)."
        try:
            self.announce(text)
        except Exception:
            pass
        if self.notifier and self.notifier.enabled:
            self.notifier.send("🌅 Briefing JARVIS :\n" + text)
        if self.event_log:
            self.event_log.add("proactif", "Briefing matinal envoyé", meta={"text": text[:200]})
        return text

    def start(self):
        if not self.enabled:
            return

        def _loop():
            while True:
                now = datetime.now()
                if now.hour == self.hour and self._done_today != now.date():
                    self._done_today = now.date()
                    self.briefing_now()
                time.sleep(60)
        threading.Thread(target=_loop, daemon=True, name="proactive").start()
        logger.info("🌅 Moteur proactif démarré.")
