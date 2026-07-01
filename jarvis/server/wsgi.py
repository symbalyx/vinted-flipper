"""
Point d'entrée WSGI pour la PRODUCTION (Gunicorn/Waitress).

⚠️ Ne pas utiliser `app.run()` (serveur de dev Flask) en production. Voir
INSTALL_LINUX.md (Gunicorn) et INSTALL_WINDOWS.md (Waitress).

Les tâches de fond (automatisations, proactivité, et éventuellement la caméra
de sécurité) ne démarrent PAS automatiquement à l'import : on les lance ici,
une seule fois, avec un arrêt gracieux enregistré via atexit.

Exemples :
    gunicorn -w 1 -k gthread --threads 8 -b 0.0.0.0:8004 wsgi:app
    waitress-serve --listen=0.0.0.0:8004 wsgi:app
"""

import os
import atexit
import logging

import jarvis_v4 as J

logger = logging.getLogger("JARVIS.wsgi")

app = J.app


def _start_background():
    try:
        J.automation.start()
        J.proactive.start()
        # Caméra de sécurité : opt-in explicite (évite d'ouvrir la webcam en prod
        # headless). JARVIS_SECURITY_AUTOSTART=1 pour l'activer.
        if os.getenv("JARVIS_SECURITY_AUTOSTART", "0") == "1":
            J.security.start()
        logger.info("🚀 Tâches de fond démarrées (WSGI).")
    except Exception as e:
        logger.warning(f"Démarrage tâches de fond partiel: {e}")


def _graceful_shutdown():
    try:
        J.security.stop()
    except Exception:
        pass
    logger.info("🛑 Arrêt gracieux (WSGI).")


_start_background()
atexit.register(_graceful_shutdown)
