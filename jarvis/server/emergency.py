"""
╔══════════════════════════════════════════════════════════════╗
║  JARVIS v4 — Dispatch d'urgence                               ║
║  Escalade : Telegram → contact d'urgence → appel vocal       ║
╚══════════════════════════════════════════════════════════════╝

⚠️  AVERTISSEMENT LÉGAL IMPORTANT
   Déclencher un appel aux secours sans réelle urgence est un DÉLIT dans la
   plupart des pays. Ce module est conçu pour PRÉVENIR un humain (toi / un
   contact de confiance) qui décidera, et NE COMPOSE PAS le numéro des secours
   automatiquement par défaut. L'auto-appel doit être activé explicitement et
   en connaissance de cause (EMERGENCY_AUTO_DIAL=1), et devrait viser un
   contact d'urgence personnel — PAS le 17/112/911 — sauf cadre légal validé.

Stratégie d'escalade (du moins au plus intrusif) :
   1. Notification Telegram URGENTE (+ photo si dispo)   ← toujours
   2. SMS au contact d'urgence (Twilio)                  ← si configuré
   3. Appel vocal au contact d'urgence (Twilio, message parlé)  ← si configuré

Config (toutes optionnelles) :
   TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM   (compte Twilio)
   EMERGENCY_CONTACT   = +33...   (numéro prévenu en priorité)
   EMERGENCY_NUMBER    = +33...   (numéro appelé en dernier recours)
   EMERGENCY_AUTO_DIAL = 1        (autorise l'appel automatique — défaut: non)

Garde-fous : confirmation requise pour un appel, et anti-rappel (cooldown).
"""

import os
import time
import logging
from xml.sax.saxutils import escape

import requests

logger = logging.getLogger("JARVIS.emergency")


class EmergencyDispatcher:
    def __init__(self, notifier=None, speaker_announce=None):
        self.notifier = notifier               # RemoteNotifier (Telegram)
        self.announce = speaker_announce       # callable(text) -> annonce HomePod
        self.sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.twilio_from = os.getenv("TWILIO_FROM", "")
        self.contact = os.getenv("EMERGENCY_CONTACT", "")
        self.emergency_number = os.getenv("EMERGENCY_NUMBER", "")
        self.auto_dial = os.getenv("EMERGENCY_AUTO_DIAL", "0") == "1"
        self.cooldown = 120
        self._last = 0
        logger.info(f"🆘 Urgence: telephonie={'oui' if self.telephony else 'non'} | "
                    f"auto-appel={'OUI' if self.auto_dial else 'non'}")

    @property
    def telephony(self) -> bool:
        return bool(self.sid and self.token and self.twilio_from)

    # ── Twilio (via REST, sans SDK) ───────────────────────────
    def _twilio(self, endpoint: str, payload: dict) -> bool:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.sid}/{endpoint}.json"
        try:
            r = requests.post(url, data=payload, auth=(self.sid, self.token), timeout=15)
            r.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Twilio {endpoint} KO: {e}")
            return False

    def send_sms(self, to: str, body: str) -> bool:
        if not (self.telephony and to):
            return False
        return self._twilio("Messages", {"From": self.twilio_from, "To": to, "Body": body[:1500]})

    def place_call(self, to: str, message: str) -> bool:
        if not (self.telephony and to):
            return False
        safe = escape(message)   # anti-injection TwiML (faire composer un n° arbitraire)
        twiml = (f"<Response><Say voice='alice' language='fr-FR'>{safe}</Say>"
                 f"<Pause length='1'/><Say voice='alice' language='fr-FR'>{safe}</Say></Response>")
        return self._twilio("Calls", {"From": self.twilio_from, "To": to, "Twiml": twiml})

    def call_owner(self, message: str = "") -> str:
        """Appelle l'hôte/propriétaire de la maison (contact d'urgence)."""
        now = time.time()
        if now - getattr(self, "_last_owner", 0) < self.cooldown:
            return "Hôte déjà contacté récemment (anti-rappel)."
        self._last_owner = now
        owner = self.contact or self.emergency_number
        if not owner:
            return "Aucun numéro d'hôte configuré (EMERGENCY_CONTACT)."
        if not self.telephony:
            # Pas de téléphonie : on rabat sur Telegram + annonce
            if self.notifier and self.notifier.enabled:
                self.notifier.send(f"📞 (Tentative d'appel à l'hôte) {message}")
            if self.announce:
                self.announce("J'essaie de joindre le propriétaire.")
            return "Téléphonie non configurée (Twilio) — hôte prévenu via Telegram/voix à la place."
        spoken = message or "Alerte à votre domicile. JARVIS requiert votre attention."
        if self.place_call(owner, spoken):
            return f"📞 Appel passé à l'hôte ({owner})."
        return f"Échec de l'appel à l'hôte ({owner})."

    # ── Point d'entrée principal ──────────────────────────────
    def dispatch(self, reason: str, snapshot: str = "", source: str = "manuel",
                 allow_call: bool = False, severity: str = "élevée") -> dict:
        """Déclenche l'escalade d'urgence. Renvoie le détail des actions."""
        now = time.time()
        if now - self._last < self.cooldown:
            return {"ok": False, "actions": ["Urgence déjà déclenchée récemment (anti-rappel)."]}
        self._last = now

        actions = []
        msg = f"🆘 URGENCE JARVIS ({source}) — {reason} — gravité {severity}"
        logger.critical(msg)

        # 1) Annonce vocale dissuasive
        if self.announce:
            try:
                self.announce("Urgence détectée. Les secours et le propriétaire sont prévenus.")
                actions.append("Annonce vocale dissuasive diffusée.")
            except Exception:
                pass

        # 2) Telegram urgent (+ photo)
        if self.notifier and self.notifier.enabled:
            if snapshot:
                actions.append(self.notifier.send_photo(snapshot, msg))
            else:
                actions.append(self.notifier.send(msg))
        else:
            actions.append("⚠️ Telegram non configuré — impossible de te prévenir à distance.")

        # 3) SMS au contact d'urgence
        if self.contact and self.send_sms(self.contact, msg):
            actions.append(f"SMS envoyé au contact d'urgence ({self.contact}).")

        # 4) Appel vocal — seulement si autorisé (auto_dial OU demande explicite confirmée)
        target = self.emergency_number or self.contact
        if (allow_call or self.auto_dial) and target:
            if self.place_call(target, f"Alerte. {reason}. Intervention requise."):
                actions.append(f"📞 Appel vocal passé à {target}.")
            else:
                actions.append("📞 Appel impossible (Twilio non configuré ou erreur).")
        elif not target:
            actions.append("Aucun numéro d'urgence configuré (EMERGENCY_CONTACT / EMERGENCY_NUMBER).")
        else:
            actions.append("Appel non déclenché (confirmation requise — voir allow_call/EMERGENCY_AUTO_DIAL).")

        return {"ok": True, "reason": reason, "source": source, "actions": actions}
