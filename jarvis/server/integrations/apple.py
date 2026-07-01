"""
╔══════════════════════════════════════════════════════════════╗
║  JARVIS v4 — Intégration Apple                                ║
║  Enceintes HomePod / AirPlay + Apple TV via pyatv            ║
╚══════════════════════════════════════════════════════════════╝

pyatv est asynchrone : on fait tourner une boucle asyncio dédiée dans un
thread de fond et on expose des méthodes synchrones pour le reste de JARVIS.

Tout est en "dégradation gracieuse" : si pyatv (ou la TTS) n'est pas installé,
le module reste importable et renvoie des messages explicites au lieu de
planter. Idéal pour démarrer JARVIS même sans matériel Apple sous la main.

Installation :
    pip install pyatv gtts
Appairage (une fois par appareil, depuis un terminal) :
    atvremote scan
    atvremote --id <IDENTIFIANT> --protocol airplay pair      # HomePod
    atvremote --id <IDENTIFIANT> --protocol companion pair     # Apple TV
Puis colle les credentials dans config/apple_credentials.json :
    { "Salon HomePod": {"airplay": "xxxx"}, "Apple TV": {"companion": "yyyy"} }
"""

import os
import json
import time
import asyncio
import logging
import tempfile
import threading
from pathlib import Path

logger = logging.getLogger("JARVIS.apple")

# ── Dépendances optionnelles ──────────────────────────────────
try:
    import pyatv
    from pyatv.const import Protocol
    PYATV_OK = True
except Exception:                       # pragma: no cover
    pyatv = None
    Protocol = None
    PYATV_OK = False

try:
    from gtts import gTTS
    GTTS_OK = True
except Exception:
    gTTS = None
    GTTS_OK = False


class AppleHome:
    """Pilote les HomePod (audio AirPlay) et les Apple TV (télécommande)."""

    def __init__(self, credentials_file: str = "config/apple_credentials.json",
                 tts_lang: str = "fr"):
        self.tts_lang = tts_lang
        self.credentials_file = Path(credentials_file)
        self.credentials = self._load_credentials()
        self._devices_cache = []          # résultat du dernier scan
        self._cache_time = 0
        self._loop = None
        self._loop_ready = threading.Event()
        if PYATV_OK:
            self._start_loop()

    # ── Boucle asyncio de fond ────────────────────────────────
    def _start_loop(self):
        def _runner():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop_ready.set()
            self._loop.run_forever()
        threading.Thread(target=_runner, daemon=True, name="apple-asyncio").start()
        self._loop_ready.wait(timeout=5)

    def _run(self, coro, timeout: float = 30):
        """Exécute une coroutine sur la boucle de fond et renvoie le résultat."""
        if not self._loop:
            raise RuntimeError("Boucle asyncio Apple non démarrée")
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=timeout)

    # ── Credentials ───────────────────────────────────────────
    def _load_credentials(self) -> dict:
        if self.credentials_file.exists():
            try:
                return json.loads(self.credentials_file.read_text())
            except Exception as e:
                logger.warning(f"Credentials Apple illisibles: {e}")
        return {}

    @property
    def available(self) -> bool:
        return PYATV_OK

    # ── Découverte ────────────────────────────────────────────
    def scan(self, force: bool = False, timeout: float = 5) -> list:
        if not PYATV_OK:
            return []
        if not force and self._devices_cache and (time.time() - self._cache_time < 30):
            return self._devices_cache

        async def _scan():
            results = await pyatv.scan(self._loop, timeout=timeout)
            out = []
            for atv in results:
                services = [str(s.protocol).split(".")[-1] for s in atv.services]
                out.append({
                    "name": atv.name,
                    "address": str(atv.address),
                    "identifier": atv.identifier,
                    "model": str(getattr(atv, "device_info", "")),
                    "services": services,
                    "is_speaker": "AirPlay" in services or "RAOP" in services,
                })
            return out

        try:
            self._devices_cache = self._run(_scan(), timeout=timeout + 5)
            self._cache_time = time.time()
            return self._devices_cache
        except Exception as e:
            logger.warning(f"Scan Apple échoué: {e}")
            return []

    def _find(self, name: str):
        """Retourne la conf brute (dict pyatv-scan) d'un appareil par nom approché."""
        name_l = (name or "").lower().strip()
        devices = self.scan()
        if not devices:
            return None
        # match exact d'abord, puis "contient"
        for d in devices:
            if d["name"].lower() == name_l:
                return d
        for d in devices:
            if name_l and name_l in d["name"].lower():
                return d
        return devices[0] if devices else None   # défaut : premier appareil

    async def _connect(self, device_info: dict):
        results = await pyatv.scan(self._loop, identifier=device_info["identifier"], timeout=5)
        if not results:
            raise RuntimeError(f"Appareil '{device_info['name']}' introuvable sur le réseau")
        conf = results[0]
        creds = self.credentials.get(device_info["name"], {})
        for proto_name, value in creds.items():
            proto = getattr(Protocol, proto_name.capitalize(), None)
            if proto:
                conf.set_credentials(proto, value)
        return await pyatv.connect(conf, self._loop)

    # ── TTS : transforme du texte en fichier audio ────────────
    def _make_speech_file(self, text: str) -> str:
        if not GTTS_OK:
            raise RuntimeError("gTTS non installé (pip install gtts) — annonce vocale impossible")
        path = os.path.join(tempfile.gettempdir(), f"jarvis_tts_{int(time.time()*1000)}.mp3")
        gTTS(text=text, lang=self.tts_lang).save(path)
        return path

    # ── Actions publiques (synchrones) ────────────────────────
    def say(self, text: str, device: str = "") -> str:
        """Fait parler JARVIS sur une enceinte HomePod via AirPlay."""
        if not PYATV_OK:
            return "pyatv non installé — pas d'accès aux HomePod (pip install pyatv gtts)."
        dev = self._find(device)
        if not dev:
            return "Aucun appareil Apple trouvé sur le réseau. Ils boudent ? 🍎"
        try:
            audio = self._make_speech_file(text)
        except RuntimeError as e:
            return str(e)

        async def _play():
            atv = await self._connect(dev)
            try:
                await atv.stream.stream_file(audio)
            finally:
                atv.close()

        try:
            self._run(_play(), timeout=60)
            return f"🔊 Annoncé sur '{dev['name']}': « {text} »"
        except Exception as e:
            return f"Annonce ratée sur '{dev['name']}': {e}"
        finally:
            try:
                os.remove(audio)
            except OSError:
                pass

    def play_url(self, url: str, device: str = "") -> str:
        """Diffuse un flux audio/vidéo (URL) en AirPlay sur un appareil."""
        if not PYATV_OK:
            return "pyatv non installé (pip install pyatv)."
        dev = self._find(device)
        if not dev:
            return "Aucun appareil Apple trouvé."

        async def _play():
            atv = await self._connect(dev)
            try:
                await atv.stream.play_url(url)
            finally:
                atv.close()

        try:
            self._run(_play(), timeout=30)
            return f"▶️ Lecture lancée sur '{dev['name']}'"
        except Exception as e:
            return f"Lecture ratée: {e}"

    def set_volume(self, level: int, device: str = "") -> str:
        """Règle le volume (0-100) d'un appareil AirPlay/HomePod."""
        if not PYATV_OK:
            return "pyatv non installé."
        level = max(0, min(100, int(level)))
        dev = self._find(device)
        if not dev:
            return "Aucun appareil Apple trouvé."

        async def _vol():
            atv = await self._connect(dev)
            try:
                await atv.audio.set_volume(float(level))
            finally:
                atv.close()

        try:
            self._run(_vol(), timeout=20)
            return f"🔊 Volume de '{dev['name']}' réglé à {level}%"
        except Exception as e:
            return f"Volume non réglé: {e}"

    def appletv_command(self, command: str, device: str = "Apple TV") -> str:
        """Envoie une commande télécommande à une Apple TV.

        Commandes : play, pause, stop, next, previous, menu, home, up, down,
        left, right, select, play_pause.
        """
        if not PYATV_OK:
            return "pyatv non installé (pip install pyatv)."
        dev = self._find(device)
        if not dev:
            return "Aucune Apple TV trouvée sur le réseau."
        command = command.lower().strip()

        async def _cmd():
            atv = await self._connect(dev)
            try:
                rc = atv.remote_control
                action = getattr(rc, command, None)
                if action is None:
                    return f"Commande télécommande inconnue: '{command}'"
                await action()
                return f"📺 '{command}' envoyé à '{dev['name']}'"
            finally:
                atv.close()

        try:
            return self._run(_cmd(), timeout=20)
        except Exception as e:
            return f"Commande Apple TV ratée: {e}"

    def appletv_launch(self, app_name: str, device: str = "Apple TV") -> str:
        """Lance une app sur l'Apple TV (Netflix, YouTube, Disney+, etc.)."""
        if not PYATV_OK:
            return "pyatv non installé."
        dev = self._find(device)
        if not dev:
            return "Aucune Apple TV trouvée."
        # Bundle IDs des apps les plus courantes
        apps = {
            "netflix": "com.netflix.Netflix",
            "youtube": "com.google.ios.youtube",
            "disney": "com.disney.disneyplus",
            "disney+": "com.disney.disneyplus",
            "prime": "com.amazon.aiv.AIVApp",
            "prime video": "com.amazon.aiv.AIVApp",
            "appletv": "com.apple.TVWatchList",
            "apple tv": "com.apple.TVWatchList",
            "music": "com.apple.TVMusic",
            "spotify": "com.spotify.client",
            "twitch": "tv.twitch",
            "molotov": "tv.molotov.app",
        }
        bundle = apps.get(app_name.lower().strip(), app_name)

        async def _launch():
            atv = await self._connect(dev)
            try:
                await atv.apps.launch_app(bundle)
                return f"📺 App '{app_name}' lancée sur '{dev['name']}'"
            finally:
                atv.close()

        try:
            return self._run(_launch(), timeout=20)
        except Exception as e:
            return f"Lancement app raté: {e} (appairage 'companion' requis ?)"
