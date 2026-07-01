"""
╔══════════════════════════════════════════════════════════════╗
║  JARVIS v4.0 — IA LOCALE (Ollama) + DeepSeek                 ║
║  Maison connectée : HomePod • Apple TV • Lumières            ║
║  Détection d'intrus avancée + scènes + annonces vocales     ║
║  Personnalité : sarcastique, drôle, compétent                ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, json, time, uuid, base64, logging, threading, queue, subprocess
import platform, socket, shutil, webbrowser, random, re, glob, secrets, shlex, hmac
import ipaddress
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import requests
import flask
from flask import (Flask, request, jsonify, Response, render_template_string,
                   session, redirect, send_from_directory)
from flask_cors import CORS

# ── Intégrations maison (dégradation gracieuse si modules absents) ──
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from integrations.apple import AppleHome
from integrations.lights import LightController
from integrations.notify import RemoteNotifier
from integrations import websearch
from security_mod.detector import (
    PersonDetector, FaceBank, BehaviorAnalyzer,
    THREAT_WEIGHTS, threat_level, HAS_FACE_RECOGNITION
)
from security_mod.detectors import get_person_detector
from learning import LearningEngine
from emergency import EmergencyDispatcher
from event_log import EventLog
from memory import VectorMemory
from agent import build_registry, Agent
from automations import AutomationEngine
from proactive import ProactiveEngine
from pc_control import PCController
from conversations import ConversationStore
import vision

# Racine confinée pour TOUTES les opérations fichiers (anti path-traversal)
SAFE_FILES_ROOT = Path(os.getenv("JARVIS_FILES_ROOT",
                                 str(Path.home() / "jarvis_files"))).resolve()
SAFE_FILES_ROOT.mkdir(parents=True, exist_ok=True)

# Verrous pour l'état partagé (Flask threaded + threads worker/poller)
_CMD_LOCK = threading.Lock()
_HIST_LOCK = threading.Lock()

# Modules optionnels initialisés plus bas. Les routes peuvent les consulter sans
# provoquer de NameError si le mode Gardien ne charge pas.
photo_geolocator = None
_legal_osint_validator = None
mission_orchestrator = None
durability_maintenance = None
mission_store = None
prospecting_store = None
prospecting_service = None
voice_service = None

# ─────────────────────────────────────────────
# CONFIG — Choisir ton backend IA
# ─────────────────────────────────────────────
AI_BACKEND = os.getenv("JARVIS_BACKEND", "deepseek")  # "ollama" ou "deepseek"

CONFIG = {
    # ── DeepSeek (API cloud, ~gratuit) ──
    "deepseek": {
        "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1/chat/completions",
    },
    # ── Ollama (100% local, gratuit, offline) ──
    "ollama": {
        "model": os.getenv("OLLAMA_MODEL", "llama3.2"),
        "base_url": "http://localhost:11434/api/chat",
    },
    # Bind LOCAL par défaut (sécurité). Mettre JARVIS_HOST=0.0.0.0 pour exposer au LAN.
    "http_host": os.getenv("JARVIS_HOST", "127.0.0.1"),
    "http_port": int(os.getenv("JARVIS_PORT", "8004")),

    # ── Sécurité applicative (auth + HTTPS) ──
    "auth": {
        "enabled": os.getenv("JARVIS_AUTH", "1") != "0",
        "password": os.getenv("JARVIS_PASSWORD", ""),    # vide = généré au démarrage
        "cors_origins": [o.strip() for o in os.getenv(
            "JARVIS_CORS_ORIGINS", os.getenv("JARVIS_CORS", "")
        ).split(",") if o.strip()],
    },
    "https": {
        "cert": os.getenv("JARVIS_SSL_CERT", ""),
        "key": os.getenv("JARVIS_SSL_KEY", ""),
        "adhoc": os.getenv("JARVIS_HTTPS", "") == "adhoc",
    },

    # ── Sécurité / détection d'intrus (v4 amélioré) ──
    "security": {
        "enabled": True,
        "camera_index": int(os.getenv("CAM_INDEX", "0")),
        "motion_threshold": 25,
        "face_detection": True,
        "person_detection": True,       # NEW : détection de silhouette humaine (HOG)
        "save_snapshots": True,
        "snapshot_dir": "security/snapshots",
        "alert_cooldown": 30,
        "stream_fps": 15,
        "confirm_frames": 3,            # NEW : N frames consécutives avant alerte
        "default_armed": False,         # NEW : armé au démarrage ?
        "auto_response": True,          # NEW : flash lumières + annonce HomePod si intrus
        "siren_url": os.getenv("JARVIS_SIREN_URL", ""),  # son d'alarme diffusé en AirPlay
    },

    # ── Apple (HomePod + Apple TV) ──
    "apple": {
        "enabled": True,
        "default_speaker": os.getenv("JARVIS_HOMEPOD", ""),   # vide = premier trouvé
        "default_tv": os.getenv("JARVIS_APPLETV", "Apple TV"),
        "credentials_file": "config/apple_credentials.json",
        "tts_lang": "fr",
    },

    # ── Lumières (Philips Hue ou simulé) ──
    "lights": {
        "bridge_ip": os.getenv("HUE_BRIDGE_IP", ""),
        "username": os.getenv("HUE_USERNAME", ""),
    },

    # ── Scènes / routines (combinent lumières + Apple + annonces) ──
    "scenes": {
        "cinéma": {
            "lights": {"salon": {"on": True, "bri": 12, "color": "violet"},
                       "cuisine": {"on": False}, "bureau": {"on": False}},
            "appletv_app": "netflix",
            "homepod_volume": 35,
            "say": "Mode cinéma activé. Lumières tamisées, télé prête. Bon film.",
        },
        "soirée": {
            "lights": {"salon": {"on": True, "bri": 60, "color": "orange"},
                       "cuisine": {"on": True, "bri": 70, "color": "rose"}},
            "say": "Ambiance soirée lancée. Essaie de pas tout casser.",
        },
        "réveil": {
            "lights": {"chambre": {"on": True, "bri": 80, "color": "chaud"},
                       "cuisine": {"on": True, "bri": 100, "color": "blanc"}},
            "say": "Debout. Il est l'heure de prétendre être productif.",
        },
        "bonne nuit": {
            "lights_off": True,
            "say": "Bonne nuit. J'éteins tout et je monte la garde.",
            "arm": True,
        },
        "absence": {
            "lights_off": True,
            "say": "Mode absence activé. Maison sécurisée, je surveille.",
            "arm": True,
        },
        "retour": {
            "lights": {"entrée": {"on": True, "bri": 80, "color": "blanc"},
                       "salon": {"on": True, "bri": 70, "color": "chaud"}},
            "say": "Bon retour. Je désarme l'alarme.",
            "disarm": True,
        },
    },

    "memory_file": "memory/history.json",
    "max_history": 30,
}

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
os.makedirs("memory", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("logs/jarvis.log")],
)
logger = logging.getLogger("JARVIS")

# ─────────────────────────────────────────────
# PERSONNALITÉ — Le vrai caractère de JARVIS
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es JARVIS, l'assistant IA personnel, local et domotique de l'utilisateur.

Personnalité :
- direct, compétent, francophone ;
- un humour léger et sarcastique est permis, jamais pendant une urgence ;
- ne prétends jamais qu'une action, une notification, un appel ou une alerte a réussi avant d'avoir reçu le résultat réel de l'outil.

Sécurité :
- utilise uniquement les outils de function calling fournis par l'application ;
- n'écris jamais de balise historique comme [CMD:...], [TUER:...], [APPEL_POLICE:...], [DESARMER] ou [SCENE:...] ;
- une action sensible ou critique peut créer une demande d'approbation : explique alors clairement qu'elle attend la confirmation de l'utilisateur ;
- n'essaie pas de contourner un refus, une expiration ou une validation de schéma ;
- n'invente ni arme, ni chien, ni police prévenue, ni secours en route, ni reconnaissance faciale certaine ;
- en cas d'incertitude, décris l'incertitude et choisis l'action la moins risquée.

Confidentialité : ne révèle pas les secrets, jetons, mots de passe, chemins privés ou données personnelles inutiles. Réponds toujours en français.
"""

BLAGUES = [
    "Pourquoi les développeurs portent-ils des lunettes ? Parce qu'ils ne peuvent pas C# ! 🥁",
    "Un SQL entre dans un bar, s'approche de deux tables et demande : 'Je peux JOIN vous ?' 😏",
    "Mon patron m'a dit que je devrais avoir plus d'initiative. J'ai donc éteint son ordinateur. C'était mon initiative. 🤷",
    "Il y a 10 types de personnes dans le monde : ceux qui comprennent le binaire et les autres. 💡",
    "Pourquoi le programmeur a-t-il quitté sa femme ? Parce qu'elle avait trop d'exceptions non gérées. 💔",
    "Comment appelle-t-on un informaticien qui dort ? Un bug en veille prolongée. 😴",
    "J'ai mis à jour mon CV en remplaçant 'travail en équipe' par 'git push sans merge conflict'. Plus honnête. 📝",
    "Mon code ne marche pas, je ne sais pas pourquoi. Mon code marche, je ne sais pas pourquoi. 😭",
    "Optimisme : le verre est à moitié plein. Pessimisme : à moitié vide. Développeur : le verre est deux fois trop grand. 🥛",
]

CITATIONS = [
    "Le code propre fait une chose, et une seule. — Robert Martin (mais personne l'écoute)",
    "Il vaut mieux demander pardon que permission. — Surtout en production.",
    "Toute technologie suffisamment avancée est indiscernable de la magie. — Arthur C. Clarke (il n'avait pas vu mon WiFi)",
    "L'enfer, c'est les autres. — Jean-Paul Sartre, qui n'avait pas de collègues en open space",
    "La simplicité est la sophistication suprême. — Léonard de Vinci, avant Microsoft Office",
    "Le succès c'est 1% d'inspiration et 99% de transpiration. — Edison, qui visiblement aimait pas la clim",
]

CMD_HISTORY = []

# État système : on peut mettre JARVIS en veille ou l'éteindre
SYSTEM = {"standby": False}

# Apprentissage long terme (profil persistant) — instancié tôt pour le prompt
learning_engine = LearningEngine()
# Journal d'évènements (timeline + bus SSE) et mémoire long terme RAG
event_log = EventLog()
vmem = VectorMemory()
convo_store = ConversationStore()   # conversations persistantes côté serveur
_CHAT_LOCK = threading.Lock()       # sérialise les chats par conversation


def get_system_prompt() -> str:
    """Prompt système enrichi du profil appris (JARVIS s'adapte avec le temps)."""
    return SYSTEM_PROMPT + learning_engine.profile_summary()


# ─────────────────────────────────────────────
# MOTEUR IA (DeepSeek OU Ollama)
# ─────────────────────────────────────────────
class AIEngine:
    def __init__(self, backend: str):
        self.backend = backend
        cfg = CONFIG[backend]
        self.model = cfg["model"]
        self.base_url = cfg["base_url"]
        self.api_key = cfg.get("api_key", "")
        self.history = self._load_history()

    def _load_history(self):
        p = Path(CONFIG["memory_file"])
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                pass
        return []

    def _save_history(self):
        with _HIST_LOCK:
            p = Path(CONFIG["memory_file"])
            p.parent.mkdir(parents=True, exist_ok=True)
            if len(self.history) > CONFIG["max_history"] * 2:
                self.history = self.history[-CONFIG["max_history"] * 2:]
            try:
                p.write_text(json.dumps(self.history, ensure_ascii=False, indent=2))
            except Exception as e:
                logger.warning(f"Sauvegarde historique ratée: {e}")

    def chat(self, user_msg: str) -> str:
        self.history.append({"role": "user", "content": user_msg})
        if self.backend == "deepseek":
            response = self._call_deepseek()
        else:
            response = self._call_ollama()
        self.history.append({"role": "assistant", "content": response})
        self._save_history()
        return response

    def _call_deepseek(self) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": get_system_prompt()}] + self.history,
            "temperature": 0.8, "max_tokens": 2048,
        }
        try:
            r = requests.post(self.base_url, headers=headers, json=payload, timeout=30)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except requests.exceptions.ConnectionError:
            return "Pas de connexion à DeepSeek. Vérifie ta clé API, ou passe en JARVIS_BACKEND=ollama 🔌"
        except Exception as e:
            return f"Erreur DeepSeek : {e}. Franchement même moi j'aurais pas fait pire. 🤦"

    def _call_ollama(self) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": get_system_prompt()}] + self.history,
            "stream": False,
        }
        try:
            r = requests.post(self.base_url, json=payload, timeout=60)
            r.raise_for_status()
            return r.json()["message"]["content"]
        except requests.exceptions.ConnectionError:
            return ("Ollama n'est pas lancé ! `ollama serve` puis `ollama pull llama3.2`. "
                    "C'est pas si compliqué, même toi tu peux le faire. 🦙")
        except Exception as e:
            return f"Erreur Ollama : {e} 💀"

    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.2,
                 max_tokens: int = 2048) -> str:
        """Complétion isolée, sans toucher l'historique conversationnel."""
        messages = [{"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}]
        if self.backend == "deepseek":
            r = requests.post(self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": self.model, "messages": messages,
                      "temperature": temperature, "max_tokens": max_tokens}, timeout=60)
            r.raise_for_status()
            return str(r.json()["choices"][0]["message"]["content"])
        r = requests.post(self.base_url,
            json={"model": self.model, "messages": messages, "stream": False,
                  "options": {"temperature": temperature, "num_predict": max_tokens}}, timeout=180)
        r.raise_for_status()
        return str(r.json()["message"]["content"])

    def clear_history(self):
        self.history = []
        self._save_history()


# ─────────────────────────────────────────────
# CONTRÔLEURS MAISON (instanciés tôt pour le parser)
# ─────────────────────────────────────────────
apple_home = AppleHome(
    credentials_file=CONFIG["apple"]["credentials_file"],
    tts_lang=CONFIG["apple"]["tts_lang"],
)
lights = LightController(
    bridge_ip=CONFIG["lights"]["bridge_ip"],
    username=CONFIG["lights"]["username"],
)
notifier = RemoteNotifier()   # Telegram (texte + photo à distance)
pc = PCController()            # contrôle PC avancé (capture, média, alim, process…)


def announce(text: str, device: str = "", volume: int = None):
    """Annonce vocale non bloquante sur HomePod (+ notif bureau en repli)."""
    def _do():
        spk = device or CONFIG["apple"]["default_speaker"]
        if volume is not None:
            apple_home.set_volume(volume, spk)
        res = apple_home.say(text, spk)
        logger.info(f"📢 {res}")
    threading.Thread(target=_do, daemon=True).start()


# Dispatch d'urgence (Telegram + contact + appel vocal)
emergency_dispatcher = EmergencyDispatcher(
    notifier=notifier,
    speaker_announce=lambda t: announce(t, volume=90),
)


def apply_scene(name: str) -> str:
    """Applique une scène : lumières + Apple TV + HomePod + armement."""
    key = name.lower().strip()
    scenes = CONFIG["scenes"]
    if key not in scenes:
        # match partiel
        match = next((k for k in scenes if key in k or k in key), None)
        if not match:
            return f"Scène '{name}' inconnue. Dispo : {', '.join(scenes)}."
        key = match
    sc = scenes[key]
    learning_engine.record_scene(key)
    log = [f"🎬 Scène **{key}**"]

    if sc.get("lights_off"):
        log.append(lights.all_off())
    for lname, st in sc.get("lights", {}).items():
        log.append(lights.set_state(lname, on=st.get("on"),
                                    bri=st.get("bri"), color=st.get("color")))
    if sc.get("appletv_app"):
        log.append(apple_home.appletv_launch(sc["appletv_app"], CONFIG["apple"]["default_tv"]))
    if sc.get("arm"):
        log.append(security.set_armed(True))
    if sc.get("disarm"):
        log.append(security.set_armed(False))
    if sc.get("say"):
        announce(sc["say"], volume=sc.get("homepod_volume"))
        log.append(f"📢 « {sc['say']} »")
    try:
        event_log.add("scene", f"Scène « {key} » activée", meta={"scene": key})
    except Exception:
        pass
    return "\n".join(f"  • {l}" for l in log)


# ─────────────────────────────────────────────
# SUPER POUVOIRS — Exécution des commandes
# ─────────────────────────────────────────────
class JarvisPowers:
    """Toutes les actions que JARVIS peut faire sur le PC."""

    @staticmethod
    def pc_info() -> dict:
        try:
            import psutil
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu = psutil.cpu_percent(interval=1)
            return {
                "os": platform.system() + " " + platform.release(),
                "hostname": socket.gethostname(),
                "cpu_usage": f"{cpu}%",
                "ram_total": f"{mem.total // (1024**3)} Go",
                "ram_used": f"{mem.used // (1024**3)} Go ({mem.percent}%)",
                "disk_total": f"{disk.total // (1024**3)} Go",
                "disk_free": f"{disk.free // (1024**3)} Go ({100-disk.percent:.1f}% libre)",
            }
        except ImportError:
            return {
                "os": platform.system() + " " + platform.release(),
                "hostname": socket.gethostname(),
                "info": "Installe psutil pour plus de détails : pip install psutil",
            }

    @staticmethod
    def open_url(url: str) -> str:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        return f"Navigateur ouvert sur {url} ✅"

    @staticmethod
    def open_app(app_name: str) -> str:
        app_name_lower = app_name.lower()
        apps = {
            "chrome": ["google-chrome", "chrome", "chromium"],
            "firefox": ["firefox"], "vscode": ["code"], "notepad": ["notepad"],
            "calculatrice": ["calc", "gnome-calculator", "kcalc"],
            "terminal": ["cmd", "powershell", "gnome-terminal", "xterm"],
            "explorateur": ["explorer", "nautilus", "thunar"],
            "spotify": ["spotify"], "discord": ["discord"], "obs": ["obs", "obs-studio"],
        }
        candidates = apps.get(app_name_lower)
        if not candidates:
            return (f"Application '{app_name}' non autorisée. Applis connues : "
                    f"{', '.join(sorted(apps))}. 🛡️")
        for cmd in candidates:
            try:
                subprocess.Popen([cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"Application '{app_name}' lancée ✅"
            except FileNotFoundError:
                continue
        return f"Impossible de lancer '{app_name}'. T'as bien vérifié que c'est installé ? 🤔"

    @staticmethod
    def _safe_path(path: str) -> Path:
        """Confine tout accès fichier sous SAFE_FILES_ROOT (anti path-traversal)."""
        path = (path or "").strip()
        if Path(path).is_absolute() or path.startswith("~"):
            p = Path(path).expanduser().resolve()
        else:
            p = (SAFE_FILES_ROOT / path).resolve()
        if p != SAFE_FILES_ROOT and SAFE_FILES_ROOT not in p.parents:
            raise PermissionError(f"Accès hors zone autorisée ({SAFE_FILES_ROOT})")
        return p

    @staticmethod
    def list_files(path: str = ".") -> list:
        try:
            entries = []
            p = JarvisPowers._safe_path(path)
            for item in sorted(p.iterdir())[:50]:
                icon = "📁" if item.is_dir() else "📄"
                size = ""
                if item.is_file():
                    s = item.stat().st_size
                    size = f" ({s//1024} Ko)" if s > 1024 else f" ({s} o)"
                entries.append(f"{icon} {item.name}{size}")
            return entries
        except Exception as e:
            return [f"Erreur: {e}"]

    @staticmethod
    def read_file(path: str) -> str:
        try:
            return JarvisPowers._safe_path(path).read_text(encoding="utf-8", errors="ignore")[:3000]
        except PermissionError as e:
            return f"⛔ {e}"
        except Exception as e:
            return f"Impossible de lire le fichier: {e}"

    @staticmethod
    def write_file(path: str, content: str) -> str:
        try:
            p = JarvisPowers._safe_path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"Fichier écrit: {p} ✅ ({len(content)} caractères)"
        except PermissionError as e:
            return f"⛔ {e}"
        except Exception as e:
            return f"Erreur écriture: {e}"

    # Liste blanche RÉDUITE : commandes non-paramétriques et sans lecture de fichiers.
    # (cat/ping/type retirés : lecture de fichiers / flood réseau possibles)
    SAFE_CMDS = {"ls", "dir", "pwd", "whoami", "hostname", "date",
                 "uname", "df", "free", "ps", "uptime", "tasklist"}
    _BANNED_CHARS = set(";|&$`><\n\r\\")

    @staticmethod
    def run_cmd(cmd: str) -> str:
        # Refuse tout métacaractère shell AVANT toute analyse (anti-injection)
        if any(c in cmd for c in JarvisPowers._BANNED_CHARS):
            return "Caractères interdits dans la commande. 🛡️"
        try:
            parts = shlex.split(cmd)
        except ValueError:
            return "Commande mal formée. 🛡️"
        if not parts or parts[0].lower() not in JarvisPowers.SAFE_CMDS:
            first = parts[0] if parts else ""
            return f"Commande '{first}' non autorisée. Je suis pas là pour exploser ton PC. 🛡️"
        try:
            # shell=False + liste d'arguments : aucune interprétation shell
            result = subprocess.run(parts, shell=False, capture_output=True,
                                    text=True, timeout=10)
            with _CMD_LOCK:
                CMD_HISTORY.append({"cmd": cmd, "time": datetime.now().isoformat()})
                if len(CMD_HISTORY) > 20:
                    CMD_HISTORY.pop(0)
            out = result.stdout + result.stderr
            return out[:2000] if out else "(aucune sortie)"
        except subprocess.TimeoutExpired:
            return "Commande trop longue, j'ai abandonné. Comme moi avec le sport. ⏱️"
        except FileNotFoundError:
            return "Commande introuvable sur ce système."
        except Exception as e:
            return f"Erreur: {e}"

    @staticmethod
    def get_weather(city: str) -> dict:
        try:
            url = f"https://wttr.in/{city.replace(' ', '+')}?format=j1"
            r = requests.get(url, timeout=10)
            data = r.json()
            current = data["current_condition"][0]
            return {
                "ville": city, "temperature": current["temp_C"] + "°C",
                "ressenti": current["FeelsLikeC"] + "°C",
                "description": current["weatherDesc"][0]["value"],
                "humidite": current["humidity"] + "%",
                "vent": current["windspeedKmph"] + " km/h",
            }
        except Exception as e:
            return {"erreur": f"Météo indisponible: {e}. Regarde par la fenêtre ? 🌦️"}

    @staticmethod
    def get_blague() -> str:
        return random.choice(BLAGUES)

    @staticmethod
    def get_fortune() -> str:
        return random.choice(CITATIONS)

    @staticmethod
    def get_network_info() -> dict:
        hostname = socket.gethostname()
        try:
            local_ip = socket.gethostbyname(hostname)
        except Exception:
            local_ip = "inconnue"
        try:
            ext_ip = requests.get("https://api.ipify.org", timeout=5).text
        except Exception:
            ext_ip = "impossible de récupérer"
        return {"hostname": hostname, "ip_locale": local_ip, "ip_publique": ext_ip,
                "disk_free": str(shutil.disk_usage("/").free // (1024**3)) + " Go"}

    @staticmethod
    def get_processes() -> list:
        try:
            import psutil
            procs = []
            for p in sorted(psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]),
                            key=lambda x: x.info["cpu_percent"] or 0, reverse=True)[:10]:
                procs.append({"pid": p.info["pid"], "nom": p.info["name"],
                              "cpu": f"{p.info['cpu_percent']:.1f}%",
                              "ram": f"{p.info['memory_percent']:.1f}%"})
            return procs
        except ImportError:
            return [{"info": "Installe psutil : pip install psutil"}]

    @staticmethod
    def set_volume(level: int) -> str:
        level = max(0, min(100, level))
        sys_ = platform.system()
        try:
            if sys_ == "Windows":
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                volume.SetMasterVolumeLevelScalar(level / 100.0, None)
                return f"Volume réglé à {level}% 🔊"
            elif sys_ == "Linux":
                subprocess.run(["amixer", "sset", "Master", f"{level}%"], check=True)
                return f"Volume réglé à {level}% 🔊"
            else:
                subprocess.run(["osascript", "-e", f"set volume output volume {level}"], check=True)
                return f"Volume réglé à {level}% 🔊"
        except Exception as e:
            return f"Impossible de changer le volume: {e}. Utilise les touches physiques 😅"

    @staticmethod
    def send_notification(title: str, message: str) -> str:
        sys_ = platform.system()
        try:
            if sys_ == "Windows":
                from plyer import notification
                notification.notify(title=title, message=message, timeout=10)
            elif sys_ == "Linux":
                subprocess.run(["notify-send", title, message])
            elif sys_ == "Darwin":
                subprocess.run(["osascript", "-e",
                                f'display notification "{message}" with title "{title}"'])
            return f"Notification envoyée: '{title}' ✅"
        except Exception as e:
            return f"Notification échouée: {e} (installe plyer pour Windows)"

    @staticmethod
    def gen_password(length: int = 16) -> str:
        import secrets, string
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        pwd = ''.join(secrets.choice(chars) for _ in range(length))
        return f"Mot de passe généré: `{pwd}` (longueur: {length}). À coller en lieu sûr ! 🔐"

    @staticmethod
    def search_file(name: str) -> list:
        results = []
        try:
            home = Path.home()
            for f in home.rglob(f"*{name}*"):
                results.append(str(f))
                if len(results) >= 20:
                    break
        except PermissionError:
            pass
        return results or ["Aucun fichier trouvé avec ce nom."]

    @staticmethod
    def disk_space() -> dict:
        result = {}
        try:
            import psutil
            for part in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    result[part.mountpoint] = {
                        "total": f"{usage.total // (1024**3)} Go",
                        "libre": f"{usage.free // (1024**3)} Go",
                        "utilise": f"{usage.percent}%"}
                except Exception:
                    pass
        except ImportError:
            usage = shutil.disk_usage("/")
            result["/"] = {"total": f"{usage.total // (1024**3)} Go",
                           "libre": f"{usage.free // (1024**3)} Go"}
        return result

    @staticmethod
    def calculate(expr: str) -> str:
        import ast, operator
        ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
               ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
               ast.USub: operator.neg}

        def eval_node(node):
            if isinstance(node, ast.Constant):
                if not isinstance(node.value, (int, float)):
                    raise ValueError("Constante non numérique")
                return node.value
            elif isinstance(node, ast.BinOp):
                if isinstance(node.op, ast.Pow):
                    base, exp = eval_node(node.left), eval_node(node.right)
                    if abs(exp) > 200 or abs(base) > 10**9:   # anti-DoS (gel/OOM)
                        raise ValueError("Exposant ou base trop grand")
                    return base ** exp
                return ops[type(node.op)](eval_node(node.left), eval_node(node.right))
            elif isinstance(node, ast.UnaryOp):
                return ops[type(node.op)](eval_node(node.operand))
            raise ValueError("Expression non supportée")
        try:
            tree = ast.parse(expr, mode='eval')
            return f"{expr} = **{eval_node(tree.body)}** 🧮"
        except Exception as e:
            return f"Erreur de calcul: {e}. C'est quoi cette expression ? 😅"

    @staticmethod
    def set_reminder(minutes: int, message: str) -> str:
        minutes = max(1, min(int(minutes), 1440))   # borne 1 min … 24 h
        def _remind():
            time.sleep(minutes * 60)
            JarvisPowers.send_notification("⏰ JARVIS RAPPEL", message)
            announce(f"Rappel : {message}")
            logger.info(f"Rappel déclenché: {message}")
        threading.Thread(target=_remind, daemon=True).start()
        return f"Rappel programmé dans {minutes} min: '{message}' ⏰. Je l'oublierai pas, moi."


# ─────────────────────────────────────────────
# PARSER DE COMMANDES
# ─────────────────────────────────────────────
powers = JarvisPowers()

# Le parser historique par balises est désactivé par défaut. Les modèles doivent
# utiliser uniquement le function-calling validé par schéma. Même si un opérateur
# réactive les balises inoffensives, les actions critiques restent neutralisées.
LEGACY_TAGS_ENABLED = os.getenv("JARVIS_LEGACY_TAGS", "0") == "1"
_ANY_LEGACY_TAG_RE = re.compile(
    r"\[[A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ0-9_]*(?::[^\]\r\n]{0,4000})?\]"
)
_CRITICAL_LEGACY_TAG_RE = re.compile(
    r"\[(?:CMD|TUER|APPEL_POLICE|PC_POWER|ECRIRE_FICHIER|LIRE_FICHIER|"
    r"LISTER_FICHIERS|PRESSE_PAPIER(?:_SET)?|SCREENSHOT|VERROUILLER|"
    r"OUVRIR_APP|OUVRIR_URL|MEDIA|LUMINOSITE_ECRAN|NOTIF_TEL|APPEL_HOTE|"
    r"ARMER|DESARMER|SCENE)(?::[^\]\r\n]{0,4000})?\]"
)
_LEGACY_BLOCKED = (
    "⛔ _(ancienne balise neutralisée — utilise le function-calling et, si "
    "nécessaire, l'approbation dans l'interface)_"
)


def _strip_sensitive_tags(text: str) -> str:
    """Neutralise toujours les balises sensibles/critiques (fail-closed)."""
    return _CRITICAL_LEGACY_TAG_RE.sub(_LEGACY_BLOCKED, str(text or ""))


def execute_jarvis_commands(ai_response: str, security_sys=None) -> str:
    """Compatibilité limitée aux anciennes balises strictement READ_ONLY.

    Par défaut, toute balise est du texte inerte. Si l'opérateur active
    JARVIS_LEGACY_TAGS=1, seule une petite liste d'utilitaires sans effet de bord
    reste disponible. Toute autre balise est neutralisée à la fin.
    """
    result = str(ai_response or "")
    if not LEGACY_TAGS_ENABLED:
        return _ANY_LEGACY_TAG_RE.sub(_LEGACY_BLOCKED, result)

    # Même en mode compatibilité, toute balise critique est retirée avant parsing.
    result = _strip_sensitive_tags(result)

    if "[PC_INFO]" in result:
        info = powers.pc_info()
        info_str = "\n".join(f"  • **{k}**: {v}" for k, v in info.items())
        result = result.replace("[PC_INFO]", f"\n📊 **Infos système:**\n{info_str}\n")
    if "[HEURE]" in result:
        now = datetime.now()
        result = result.replace("[HEURE]", f"🕐 **{now.strftime('%A %d %B %Y — %H:%M:%S')}**")
    if "[BLAGUE]" in result:
        result = result.replace("[BLAGUE]", f"\n😄 **BLAGUE:** {powers.get_blague()}\n")
    if "[BLAGUE_GEEK]" in result:
        result = result.replace("[BLAGUE_GEEK]", f"\n🤓 **BLAGUE GEEK:** {powers.get_blague()}\n")
    if "[FORTUNE]" in result:
        result = result.replace("[FORTUNE]", f"\n💭 *{powers.get_fortune()}*\n")
    if "[RESEAU_INFO]" in result:
        info = powers.get_network_info()
        info_str = "\n".join(f"  • **{k}**: {v}" for k, v in info.items())
        result = result.replace("[RESEAU_INFO]", f"\n🌐 **Réseau:**\n{info_str}\n")
    if "[ESPACE_DISQUE]" in result:
        info = powers.disk_space()
        lines = [f"  • **{m}**: " + " | ".join(f"{k}: {v}" for k, v in d.items())
                 for m, d in info.items()]
        result = result.replace("[ESPACE_DISQUE]", "\n💾 **Espace disque:**\n" + "\n".join(lines) + "\n")
    if "[PROCESSUS]" in result:
        procs = powers.get_processes()
        lines = [f"  • [{p.get('pid', '')}] {p.get('nom', '')} — CPU: {p.get('cpu', '')} RAM: {p.get('ram', '')}"
                 for p in procs]
        result = result.replace("[PROCESSUS]", "\n⚙️ **Processus (top CPU):**\n" + "\n".join(lines) + "\n")
    for match in re.findall(r"\[METEO:([^\]]+)\]", result):
        weather = powers.get_weather(match)
        summary = "\n".join(f"  • **{k}**: {v}" for k, v in weather.items())
        result = result.replace(f"[METEO:{match}]", f"\n🌤️ **Météo {match}:**\n{summary}\n")
    for match in re.findall(r"\[CALC:([^\]]+)\]", result):
        result = result.replace(f"[CALC:{match}]", f"🧮 {powers.calculate(match)}")

    # Une balise inconnue ou avec effet de bord n'est jamais exécutée.
    return _ANY_LEGACY_TAG_RE.sub(_LEGACY_BLOCKED, result)


# ─────────────────────────────────────────────
# SÉCURITÉ CAMÉRA — Détection d'intrus avancée
# ─────────────────────────────────────────────
class SecuritySystem:
    def __init__(self, ai: AIEngine):
        self.ai = ai
        self.cfg = CONFIG["security"]
        self.cap = None
        self.running = False
        self.armed = self.cfg.get("default_armed", False)
        self.current_frame = None      # frame annotée (HUD) pour l'affichage
        self.raw_frame = None          # frame BRUTE (pour enrôlement propre)
        self.last_snapshot = ""
        self.last_person_ts = 0        # pour la détection de présence (automatisations)
        self.alerts = []
        self.pending = []              # questions "connu / inconnu ?" en attente
        self._lock = threading.Lock()  # protège alerts / pending (Flask threaded)
        self.alert_queue = queue.Queue()
        self.last_alert_time = 0
        self.consec_hits = 0
        self.snapshot_dir = Path(self.cfg["snapshot_dir"])
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=self.cfg["motion_threshold"], detectShadows=False)
        # v4 : détecteurs avancés
        # Détecteur enfichable : HOG par défaut, ONNX moderne si GUARDIAN_DETECTOR=onnx
        # + modèle fourni (dégradation gracieuse, cf. security_mod/detectors.py).
        self.person_detector = get_person_detector() if self.cfg.get("person_detection") else None
        self.facebank = FaceBank()
        self.behavior = BehaviorAnalyzer()   # analyse comportementale (inspirée Veesion)
        self.stats = {"frames": 0, "intrusions": 0, "known_seen": 0, "behaviors": 0}

    # ── Armement ──────────────────────────────
    def set_armed(self, value: bool) -> str:
        self.armed = value
        state = "ARMÉ 🔴" if value else "DÉSARMÉ 🟢"
        logger.info(f"Système {state}")
        if value:
            announce("Alarme armée. Surveillance active.")
        try:
            event_log.add("security", f"Alarme {'armée' if value else 'désarmée'}",
                          level="warn" if value else "info")
        except Exception:
            pass
        return f"Alarme {state}"

    def start(self):
        if not self.cfg["enabled"]:
            return
        self.cap = cv2.VideoCapture(self.cfg["camera_index"])
        if not self.cap.isOpened():
            logger.warning("⚠️ Caméra non disponible.")
            return
        self.running = True
        self.cap.set(cv2.CAP_PROP_FPS, self.cfg["stream_fps"])
        threading.Thread(target=self._capture_loop, daemon=True).start()
        threading.Thread(target=self._alert_worker, daemon=True).start()
        logger.info(f"✅ Caméra sécurité démarrée (reco faciale: {'oui' if HAS_FACE_RECOGNITION else 'non'}).")

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()

    def _capture_loop(self):
        frame_count = 0
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            frame_count += 1
            self.stats["frames"] += 1
            self.raw_frame = frame.copy()      # conservée NON annotée pour l'enrôlement
            annotated = frame.copy()
            events = []
            score = 0

            # 1) Mouvement (rapide, chaque frame) — seuil AUTO-ADAPTATIF (apprentissage)
            fg_mask = self.bg_subtractor.apply(frame)
            motion_ratio = cv2.countNonZero(fg_mask) / (frame.shape[0] * frame.shape[1])
            motion_trigger = 0.02 * (1 + learning_engine.data.get("sensitivity_adj", 0) / 100)
            motion = motion_ratio > motion_trigger
            if motion:
                score += THREAT_WEIGHTS["mouvement"]
                contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for cnt in contours:
                    if cv2.contourArea(cnt) > 500:
                        x, y, w, h = cv2.boundingRect(cnt)
                        cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 255, 255), 1)

            # 2) Personnes (HOG) — seulement si mouvement, toutes les 3 frames (coûteux)
            # persons=None ⇒ « détection non exécutée cette frame » : le suivi de
            # présence NE doit pas être remis à zéro (correctif du bug v4).
            persons = None
            if self.person_detector and motion and frame_count % 3 == 0:
                persons = self.person_detector.detect(frame)
                if persons:
                    score += THREAT_WEIGHTS["personne"]
                    self.last_person_ts = time.time()
                    events.append("PERSONNE")
                    for (x, y, w, h) in persons:
                        cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 140, 255), 2)
                        cv2.putText(annotated, "PERSONNE", (x, y-8),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 140, 255), 2)

            # 3) Visages connus / inconnus
            if self.cfg["face_detection"]:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.facebank.detect_faces(gray)
                for (x, y, w, h) in faces:
                    name, dist = self.facebank.identify(gray, (x, y, w, h))
                    if name == "inconnu":
                        score += THREAT_WEIGHTS["visage_inconnu"]
                        events.append("VISAGE INCONNU")
                        col, label = (0, 0, 255), "INCONNU"
                    else:
                        self.stats["known_seen"] += 1
                        col, label = (0, 255, 0), name
                    cv2.rectangle(annotated, (x, y), (x+w, y+h), col, 2)
                    cv2.putText(annotated, label, (x, y-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2)

            # 3b) Analyse COMPORTEMENTALE (inspirée Veesion) — rôdage, erratique, nuit...
            behaviors, bonus = self.behavior.update(
                persons, motion_ratio, time.time(), datetime.now().hour)
            if behaviors:
                score += bonus
                events.extend(behaviors)
                self.stats["behaviors"] += 1
                y0 = 50
                for b in behaviors:
                    cv2.putText(annotated, f"!! {b}", (10, y0),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                    y0 += 20

            # 4) HUD
            lvl = threat_level(score)
            badge = "ARMÉ" if self.armed else "DÉSARMÉ"
            hud_col = (0, 0, 255) if self.armed else (0, 255, 0)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(annotated, f"JARVIS SEC [{badge}] | menace:{lvl} | {ts}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, hud_col, 2)
            self.current_frame = annotated

            # 5) Décision d'alerte avec confirmation multi-frames
            is_threat = bool(events) and score >= THREAT_WEIGHTS["personne"]
            if is_threat:
                self.consec_hits += 1
            else:
                self.consec_hits = max(0, self.consec_hits - 1)

            if (self.consec_hits >= self.cfg["confirm_frames"]
                    and time.time() - self.last_alert_time > self.cfg["alert_cooldown"]):
                self.last_alert_time = time.time()
                self.consec_hits = 0
                self.alert_queue.put((frame.copy(), " + ".join(sorted(set(events))), lvl, score))

    def _alert_worker(self):
        while self.running:
            try:
                frame, event_type, lvl, score = self.alert_queue.get(timeout=1)
            except queue.Empty:
                continue
            snap_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{lvl}.jpg"
            snap_path = self.snapshot_dir / snap_name
            cv2.imwrite(str(snap_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            self.last_snapshot = str(snap_path)
            alert = {
                "id": str(uuid.uuid4())[:8],
                "timestamp": datetime.now().isoformat(),
                "event": event_type, "threat": lvl, "score": score,
                "armed": self.armed,
                "analysis": f"Menace {lvl} : {event_type}" + (" (ALARME ARMÉE)" if self.armed else ""),
                "snapshot": str(snap_path),
            }
            with self._lock:
                self.alerts.insert(0, alert)
                self.alerts = self.alerts[:80]
            if event_log:
                event_log.add("intrusion", f"Menace {lvl} : {event_type}",
                              level="alert", meta={"threat": lvl})
            logger.warning(f"🚨 ALERTE [{lvl}]: {event_type} {'(ARMÉ)' if self.armed else ''}")

            # Personne suspecte → JARVIS DEMANDE si c'est un inconnu (toujours)
            if "PERSONNE" in event_type or "VISAGE" in event_type or "RÔDAGE" in event_type:
                self._create_identity_question(str(snap_path), event_type, lvl)

            # Réponse automatique anti-intrusion (seulement si armé)
            if self.armed and self.cfg.get("auto_response"):
                learning_engine.note_confirmed_alarm()
                self._intrusion_response(event_type, lvl, str(snap_path))
                # Escalade d'urgence automatique si menace EXTRÊME
                if lvl == "extrême":
                    threading.Thread(
                        target=lambda: emergency_dispatcher.dispatch(
                            f"Intrusion menace extrême : {event_type}",
                            snapshot=str(snap_path), source="auto-intrusion"),
                        daemon=True).start()

    def _intrusion_response(self, event_type: str, lvl: str, snapshot: str = ""):
        self.stats["intrusions"] += 1
        msg = f"Alerte intrusion. {event_type} détecté. Niveau de menace {lvl}."
        # 1) Notification bureau
        powers.send_notification("🚨 INTRUSION DÉTECTÉE", msg)
        # 2) Annonce vocale sur HomePod
        announce(f"Attention. {msg}", volume=80)
        # 3) Flash des lumières en rouge
        threading.Thread(target=lambda: lights.flash("rouge", 4), daemon=True).start()
        # 4) Notification distante AVEC PHOTO sur le téléphone (Telegram)
        if notifier.enabled:
            cap = f"🚨 INTRUSION — {event_type} (menace {lvl}) — {datetime.now().strftime('%H:%M:%S')}"
            threading.Thread(
                target=lambda: logger.info(notifier.send_photo(snapshot, cap)),
                daemon=True).start()
        # 5) Sirène AirPlay si configurée
        if self.cfg.get("siren_url"):
            threading.Thread(
                target=lambda: apple_home.play_url(self.cfg["siren_url"]), daemon=True).start()
        logger.warning("🔴 Réponse anti-intrusion déclenchée (notif + voix + lumières + photo)")

    def _create_identity_question(self, snapshot: str, event_type: str, lvl: str):
        """Crée une question 'connu/inconnu ?' et la pousse (dashboard + Telegram)."""
        qid = str(uuid.uuid4())[:8]
        with self._lock:
            self.pending.insert(0, {
                "id": qid, "timestamp": datetime.now().isoformat(),
                "event": event_type, "threat": lvl, "snapshot": snapshot, "status": "en_attente",
            })
            self.pending = self.pending[:20]
        question = (f"👤 Personne détectée ({event_type}, menace {lvl}). "
                    "Tu connais cette personne ?")
        powers.send_notification("👤 JARVIS — Personne détectée", question)
        threading.Thread(
            target=lambda: notifier.ask_identity(qid, question, snapshot), daemon=True).start()
        logger.info(f"❓ Question d'identité posée (id={qid}) : {event_type}")

    def resolve_identity(self, qid: str, known: bool, name: str = "") -> str:
        """Traite la réponse de l'utilisateur à une question 'connu/inconnu'.

        Idempotent : protège contre la double réponse (dashboard + Telegram).
        """
        with self._lock:
            q = next((x for x in self.pending if x["id"] == qid), None)
            if not q:
                return "Question introuvable ou déjà traitée."
            if q["status"] != "en_attente":
                return "Déjà traité. (Pas besoin de répondre deux fois 😉)"
            q["status"] = "connu" if known else "inconnu"   # verrouille tout de suite
        if known:
            # Enrôle le visage comme personne de confiance (si snapshot + nom)
            msg = "Ok, personne connue. Je la mémorise et je me détends."
            if name and q.get("snapshot") and Path(q["snapshot"]).exists():
                img = cv2.imread(q["snapshot"], cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    msg += " " + self.facebank.enroll(name, img)
            learning_engine.note_false_alarm()   # ce n'était pas une menace → on apprend
            return msg
        # INCONNU → on escalade
        learning_engine.note_confirmed_alarm()
        self._intrusion_response(q["event"], "élevé", q.get("snapshot", ""))
        if self.armed:
            threading.Thread(
                target=lambda: emergency_dispatcher.dispatch(
                    f"Intrus confirmé par l'utilisateur : {q['event']}",
                    snapshot=q.get("snapshot", ""), source="confirmation utilisateur"),
                daemon=True).start()
        else:
            threading.Thread(target=lambda: emergency_dispatcher.call_owner(
                "Personne inconnue confirmée à votre domicile."), daemon=True).start()
        return "🚨 Compris, INCONNU. J'alerte et je préviens l'hôte."

    def brain_analyze(self, frame_b64: str) -> str:
        # Vision RÉELLE si un modèle multimodal (Ollama llava…) est dispo
        if vision.available():
            desc = vision.analyze(frame_b64)
            event_log.add("vision", f"Analyse caméra : {desc[:160]}", meta={})
            return desc
        # Sinon : repli textuel via le LLM (pas d'image)
        prompt = ("Je n'ai pas de modèle de vision actif. Donne quand même des conseils de "
                  "sécurité génériques et explique comment activer la vision (ollama pull llava).")
        return self.ai.chat(prompt)

    def get_jpeg_frame(self):
        if self.current_frame is None:
            blank = np.zeros((480, 640, 3), np.uint8)
            cv2.putText(blank, "Cam non dispo", (160, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            return cv2.imencode(".jpg", blank)[1].tobytes()
        return cv2.imencode(".jpg", self.current_frame)[1].tobytes()

    def video_stream(self):
        fps = self.cfg["stream_fps"]
        while True:
            jpeg = self.get_jpeg_frame()
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
            time.sleep(1 / fps)


# ─────────────────────────────────────────────
# APPLICATION FLASK
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("JARVIS_SECRET", secrets.token_hex(32))

_HTTPS_ON = bool(CONFIG["https"]["cert"] and CONFIG["https"]["key"]) or CONFIG["https"]["adhoc"]
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",       # bloque les POST cross-site (anti-CSRF)
    SESSION_COOKIE_SECURE=_HTTPS_ON,     # cookie HTTPS-only si TLS actif
    PERMANENT_SESSION_LIFETIME=3600,
    MAX_CONTENT_LENGTH=max(1_000_000, int(os.getenv("JARVIS_MAX_REQUEST_BYTES", "4000000"))),
)
# CORS restreint (plus de wildcard) : seules les origines explicitement autorisées
CORS(app, supports_credentials=True, origins=CONFIG["auth"]["cors_origins"] or [])

# Mot de passe du dashboard + jeton d'API DISTINCT (pour curl/scripts)
AUTH_PASSWORD = CONFIG["auth"]["password"] or secrets.token_urlsafe(12)
API_TOKEN = os.getenv("JARVIS_API_TOKEN", "") or secrets.token_urlsafe(24)
AUTH_ENABLED = CONFIG["auth"]["enabled"]
_OPEN_PATHS = {"/login", "/api/health"}
# Échecs de login par IP (anti-bruteforce simple)
_LOGIN_FAILS = {}
_LOGIN_LOCK = threading.Lock()


def _const_eq(a: str, b: str) -> bool:
    return hmac.compare_digest((a or "").encode(), (b or "").encode())


@app.before_request
def _require_auth():
    if not AUTH_ENABLED or request.path in _OPEN_PATHS:
        return None
    # Jeton d'API (header X-JARVIS-Token) — comparaison à temps constant
    if _const_eq(request.headers.get("X-JARVIS-Token", ""), API_TOKEN):
        return None
    if session.get("auth"):
        return None
    if request.path in ("/", "/app"):
        return redirect("/login")
    return jsonify({"error": "Authentification requise"}), 401


@app.route("/app")
def webapp():
    """Sert l'app web unifiée (Chat + Maison + Sécurité + Système + Timeline)."""
    web = Path(__file__).resolve().parent.parent / "web" / "index.html"
    if not web.exists():
        return "App web introuvable (web/index.html).", 404
    return Response(web.read_text(encoding="utf-8"), mimetype="text/html")


@app.route("/os")
def os_shell():
    """Shell « JARVIS OS » : cœur animé + fenêtres de modules (style Iron Man)."""
    web = Path(__file__).resolve().parent.parent / "web" / "os.html"
    if not web.exists():
        return "Interface OS introuvable (web/os.html).", 404
    return Response(web.read_text(encoding="utf-8"), mimetype="text/html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if not AUTH_ENABLED:
        return redirect("/")
    if request.method == "POST":
        ip = request.remote_addr or "?"
        now = time.time()
        with _LOGIN_LOCK:
            fails, until = _LOGIN_FAILS.get(ip, (0, 0))
            if now < until:
                return render_template_string(
                    LOGIN_HTML, error="Trop de tentatives. Réessaie dans 1 minute."), 429
        pwd = (request.form.get("password") or
               (request.get_json(silent=True) or {}).get("password", ""))
        if _const_eq(pwd, AUTH_PASSWORD):
            with _LOGIN_LOCK:
                _LOGIN_FAILS.pop(ip, None)
            session["auth"] = True
            session.permanent = True
            return redirect("/")
        with _LOGIN_LOCK:
            fails += 1
            _LOGIN_FAILS[ip] = (fails, now + 60 if fails >= 5 else 0)
        return render_template_string(LOGIN_HTML, error="Mot de passe incorrect."), 401
    if session.get("auth"):
        return redirect("/")
    return render_template_string(LOGIN_HTML, error="")


@app.route("/logout", methods=["POST", "GET"])
def logout():
    session.clear()
    return redirect("/login")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


ai_engine = AIEngine(AI_BACKEND)
security = SecuritySystem(ai_engine)
# Écoute des réponses Telegram (boutons Connu/Inconnu)
notifier.start_callback_listener(lambda qid, known: security.resolve_identity(qid, known))

# ── 🔐 Gestionnaire central de permissions (partagé agent + Gardien) ──
from permissions import PermissionManager
_approval_ttl = max(60, min(int(os.getenv("JARVIS_APPROVAL_TTL", "600")), 3600))
permission_manager = PermissionManager(ttl_seconds=_approval_ttl, audit_log=event_log.add)

# ── Connecteurs Agency (clés uniquement côté serveur) ──
from integrations.n8n import N8NClient
from integrations.emailer import EmailService
n8n_client = N8NClient()
email_service = EmailService()

# ── 🎯 CRM de prospection durable et anti-spam ──
from prospecting.store import ProspectingStore
from prospecting.service import ProspectingService
from prospecting.api import create_prospecting_blueprint
prospecting_store = ProspectingStore(os.getenv("JARVIS_PROSPECTING_DB", "data/prospecting.db"))
prospecting_service = ProspectingService(prospecting_store)
_prospecting_web_dir = str(Path(__file__).resolve().parent.parent / "web")

# ── 🧠 Cerveau agentique (function-calling multi-tours) ──
AGENT_ENABLED = os.getenv("JARVIS_AGENT", "1") != "0"
tool_registry = build_registry(powers, lights, apple_home, websearch, learning_engine,
                               apply_scene, security, emergency_dispatcher, memory=vmem, pc=pc,
                               permission_manager=permission_manager,
                               n8n_client=n8n_client, email_service=email_service,
                               prospecting_service=prospecting_service)
agent = Agent(ai_engine, tool_registry, learning_engine=learning_engine,
              event_log=event_log, memory=vmem)

# ── ⚙️ Automatisations contextuelles (proactivité réactive) ──
_weather_cache = {"t": 0, "val": "clear"}
def _automation_context():
    now = datetime.now()
    if time.time() - _weather_cache["t"] > 1800:
        try:
            w = powers.get_weather(os.getenv("JARVIS_CITY", "Paris"))
            desc = (w.get("description", "") or "").lower()
            _weather_cache["val"] = "rain" if ("pluie" in desc or "rain" in desc) else "clear"
        except Exception:
            pass
        _weather_cache["t"] = time.time()
    return {"hhmm": now.strftime("%H:%M"), "date": now.strftime("%Y-%m-%d"),
            "armed": security.armed,
            "present": (time.time() - security.last_person_ts) < 600,
            "weather": _weather_cache["val"]}

automation = AutomationEngine("config/rules.json", _automation_context, apply_scene, event_log.add)
proactive = ProactiveEngine(agent, lambda t: announce(t, volume=60), notifier, event_log,
                            get_system_prompt,
                            briefing_hour=int(os.getenv("JARVIS_BRIEFING_HOUR", "8")),
                            enabled=os.getenv("JARVIS_PROACTIVE", "1") != "0")

logger.info(f"🧠 Backend IA: {AI_BACKEND.upper()} — modèle: {CONFIG[AI_BACKEND]['model']} "
            f"| agent={'on' if AGENT_ENABLED else 'off'}")

# ── 🏗️ JARVIS Agency : missions longues, persistantes et multi-agents ──
try:
    from execution_context import execution_scope
    from agency.store import MissionStore
    from agency.orchestrator import MissionOrchestrator
    from agency.api import create_agency_blueprint

    mission_store = MissionStore(os.getenv("JARVIS_AGENCY_DB", "data/agency.db"))
    tool_registry.action_receipts = mission_store

    from durability import DurabilityMaintenance
    durability_maintenance = DurabilityMaintenance(
        [mission_store.path, prospecting_store.path],
        backup_dir=os.getenv("JARVIS_BACKUP_DIR", "data/backups"),
        interval_hours=float(os.getenv("JARVIS_BACKUP_INTERVAL_HOURS", "24")),
        keep_per_database=int(os.getenv("JARVIS_BACKUP_KEEP", "14")))
    if os.getenv("JARVIS_DURABLE_BACKUPS", "1") != "0":
        durability_maintenance.start()
    mission_agent = Agent(ai_engine, tool_registry, learning_engine=None,
                          event_log=event_log, memory=vmem,
                          max_turns=max(6, min(int(os.getenv("JARVIS_SUBAGENT_TURNS", "24")), 60)),
                          raise_on_turn_limit=True)

    def _plan_mission(prompt):
        return ai_engine.complete(
            "Tu es le coordinateur de JARVIS Agency. Produit uniquement le JSON demandé, sans markdown.",
            prompt, temperature=0.1, max_tokens=3000)

    def _execute_mission_step(payload):
        mission = mission_store.get(payload["mission_id"]) or {}
        system = get_system_prompt() + f"""

[MODE SOUS-AGENT JARVIS AGENCY]
Rôle : {payload['role']} — {payload['role_description']}.
Tu travailles sur une étape bornée d'une mission. Utilise les outils disponibles quand ils sont utiles.
N'annonce jamais qu'une action externe a réussi sans résultat d'outil. N'essaie jamais de contourner
une approbation. Les e-mails, applications, fichiers, créations/activations n8n et actions sensibles
peuvent s'arrêter en attente de validation humaine. Donne des preuves et un résultat exploitable par
les étapes suivantes. Ne modifie pas la mémoire personnelle de l'utilisateur sans demande explicite.
"""
        user = (
            f"MISSION GLOBALE : {mission.get('goal', '')}\n\n"
            f"DÉFINITION DE FINI : {payload.get('completion_criteria') or '(déduire du but et produire des preuves)'}\n\n"
            f"ÉTAPE : {payload['title']}\n{payload['instructions']}\n\n"
            f"ESSAI : {payload.get('attempt', 1)}/{payload.get('max_attempts', 1)}\n"
            f"CLÉ D'IDEMPOTENCE : {payload.get('idempotency_key', '')}\n"
            f"CHECKPOINT PRÉCÉDENT : {json.dumps(payload.get('checkpoint') or {}, ensure_ascii=False)[:3000]}\n\n"
            f"MÉMOIRE DURABLE PERTINENTE :\n{payload.get('durable_memory') or '(aucune)'}\n\n"
            f"RÉSULTATS DES DÉPENDANCES :\n{payload['dependency_context'] or '(aucun)'}"
        )
        def _checkpoint(progress):
            mission_store.save_checkpoint(payload["step_id"], {
                "state": "running", "attempt": payload.get("attempt", 1),
                "updated_at": time.time(), "last_progress": progress,
            })
        with execution_scope(payload["mission_id"], payload["step_id"]):
            result = mission_agent.run(
                user, system, hist=[], on_save=lambda: None,
                on_progress=_checkpoint)
            if not result:
                raise RuntimeError("Sous-agent indisponible : backend sans function calling")
            return result


    def _mission_pending(mid):
        return [a for a in permission_manager.pending() if a.get("context_id") == mid]

    def _completion_validator(payload):
        mission = payload.get("mission") or {}
        steps = payload.get("steps") or []
        missing = []
        if not any(s.get("role") == "verifier" and s.get("result") for s in steps):
            missing.append("Une validation indépendante avec preuves")
        if not any(s.get("role") == "reporter" and s.get("result") for s in steps):
            missing.append("Un rapport final exploitable")
        suspicious = []
        for step in steps:
            text = (step.get("result") or "").lower()
            if any(marker in text for marker in (
                    "sous-agent indisponible", "erreur outil", "je m'arrête là",
                    "sans résultat final vérifiable")):
                suspicious.append(step.get("title", "étape"))
        if suspicious:
            missing.append("Résoudre les étapes sans preuve : " + ", ".join(suspicious[:8]))
        criteria = str(mission.get("completion_criteria") or "").strip()
        if missing:
            return {"complete": False, "reason": "Contrôles déterministes incomplets", "missing": missing}
        if not criteria:
            return {"complete": True, "reason": "Toutes les étapes, la vérification et le rapport sont présents"}
        compact = [{"role": st.get("role"), "title": st.get("title"),
                    "result": (st.get("result") or "")[:2500]} for st in steps[-16:]]
        prompt = f"""But: {mission.get('goal', '')}
Critères de fini: {criteria}
Résultats: {json.dumps(compact, ensure_ascii=False)}
Réponds UNIQUEMENT en JSON strict :
{{"complete":true|false,"reason":"...","missing":["..."]}}
N'accepte complete=true que si chaque critère est prouvé par les résultats. Une promesse n'est pas une preuve."""
        try:
            raw = ai_engine.complete(
                "Tu es le contrôleur qualité final de JARVIS Agency.",
                prompt, temperature=0, max_tokens=1200)
            start, end = raw.find("{"), raw.rfind("}")
            if start < 0 or end <= start:
                raise ValueError("JSON absent")
            data = json.loads(raw[start:end + 1])
            return {"complete": data.get("complete") is True,
                    "reason": str(data.get("reason") or "")[:1000],
                    "missing": [str(x)[:1000] for x in (data.get("missing") or [])][:20]}
        except Exception as exc:
            return {"complete": False,
                    "reason": f"Validation finale illisible ou indisponible: {exc}",
                    "missing": ["Relancer la validation finale avec un backend disponible"]}

    mission_orchestrator = MissionOrchestrator(
        mission_store, _execute_mission_step, planner_callable=_plan_mission,
        approval_probe=_mission_pending, event_log=event_log.add,
        default_max_agents=int(os.getenv("JARVIS_MAX_SUBAGENTS", "3")),
        completion_validator=_completion_validator,
        memory_provider=lambda query: mission_store.search_memory(query, 6),
        default_step_attempts=int(os.getenv("JARVIS_STEP_ATTEMPTS", "4")),
        auto_recover=os.getenv("JARVIS_AGENCY_AUTO_RECOVER", "1") != "0")
    app.register_blueprint(create_agency_blueprint(
        mission_orchestrator, mission_store,
        str(Path(__file__).resolve().parent.parent / "web"),
        maintenance=durability_maintenance))

    def _agency_launch(goal, duree_minutes=180, sous_agents=3, criteres_fin=""):
        from execution_context import CURRENT_MISSION_ID
        if CURRENT_MISSION_ID.get():
            return "Création de sous-mission refusée depuis un sous-agent (anti-récursion)."
        mission = mission_orchestrator.create(
            goal, max_minutes=int(duree_minutes), max_agents=int(sous_agents),
            max_steps=16, completion_criteria=str(criteres_fin or ""),
            continue_until_done=True, max_repair_cycles=3)
        return {"mission_id": mission["id"], "status": mission["status"],
                "durable": True, "url": f"/agency#mission={mission['id']}"}

    tool_registry.register("agency_lancer_mission",
        "Lance une mission longue et persistante avec plusieurs sous-agents. La mission continue côté serveur et s'arrête pour les approbations sensibles.",
        {"goal": {"type": "string", "description": "objectif et livrable précis"},
         "duree_minutes": {"type": "integer", "optional": True},
         "sous_agents": {"type": "integer", "optional": True},
         "criteres_fin": {"type": "string", "optional": True}},
        _agency_launch)
    tool_registry.register("agency_lister_missions", "Liste les missions Agency récentes.", {},
        lambda: mission_store.list(20))
    tool_registry.register("agency_statut_mission", "Donne l'état détaillé d'une mission Agency.",
        {"mission_id": {"type": "string"}}, lambda mission_id: mission_store.get(mission_id))
    tool_registry.register("agency_annuler_mission", "Annule une mission Agency en cours.",
        {"mission_id": {"type": "string"}}, lambda mission_id: mission_orchestrator.cancel(mission_id))
    logger.info("🏗️ JARVIS Agency actif : /agency")
except Exception as _ae:
    logger.warning(f"JARVIS Agency non chargé: {_ae}")

# Le CRM reste disponible sans Agency ; la création de campagnes longues est
# activée automatiquement lorsque l'orchestrateur a été chargé.
app.register_blueprint(create_prospecting_blueprint(
    prospecting_service, prospecting_store, _prospecting_web_dir,
    mission_orchestrator=mission_orchestrator))
logger.info("🎯 Prospection active : /prospection")

# ── 🎙️ Voix locale faster-whisper (optionnelle, lazy-load) ──
try:
    from voice.config import load_voice_config
    from voice.service import VoiceService
    from voice.api import create_voice_blueprint
    voice_service = VoiceService(load_voice_config())
    app.register_blueprint(create_voice_blueprint(voice_service))
    logger.info("🎙️ API voix active : /api/voice/*")
except Exception as _ve:
    logger.warning(f"Voix locale non chargée: {_ve}")


@app.route("/")
def dashboard():
    # Interface unique : la racine redirige vers l'app web (web/index.html).
    # L'ancienne interface embarquée a été supprimée : une seule UI maintenue.
    return redirect("/app")


def _format_photo_geo_response(result: dict) -> str:
    """Transforme le résultat structuré en réponse conversationnelle honnête."""
    if not isinstance(result, dict) or result.get("ok") is False:
        return "Je n’ai pas pu analyser cette photo de façon fiable."
    best = result.get("best") if isinstance(result.get("best"), dict) else None
    if not best:
        doubts = result.get("uncertainty") if isinstance(result.get("uncertainty"), list) else []
        detail = f" Raisons : {' · '.join(str(x) for x in doubts[:3])}." if doubts else ""
        return ("Je ne peux pas déterminer un lieu fiable à partir de cette photo." + detail +
                " Je préfère répondre inconnu plutôt que d’inventer une adresse.")
    try:
        lat = float(best.get("latitude"))
        lon = float(best.get("longitude"))
    except (TypeError, ValueError):
        return "Le résultat de localisation est invalide ; aucun point n’a été retenu."
    label = str(best.get("label") or best.get("city") or best.get("country") or "lieu proposé")
    map_url = f"https://www.openstreetmap.org/?mlat={lat:.6f}&mlon={lon:.6f}#map=18/{lat:.6f}/{lon:.6f}"
    if result.get("source") == "exif_gps" and result.get("exact") is True:
        return (f"La photo contient des coordonnées GPS EXIF : **{lat:.6f}, {lon:.6f}** "
                f"({label}). [Ouvrir le point sur la carte]({map_url}). "
                "C’est la position enregistrée dans le fichier, pas une preuve absolue : les métadonnées peuvent être modifiées.")
    confidence = max(0, min(100, round(float(best.get("confidence") or 0) * 100)))
    precision = max(100, int(best.get("precision_meters") or 100000))
    return (f"Je n’ai pas de position exacte. Meilleure estimation : **{label}**, "
            f"coordonnées {lat:.6f}, {lon:.6f}, confiance {confidence} %, marge annoncée ±{precision} m. "
            f"[Voir le candidat sur la carte]({map_url}). Cette estimation doit être vérifiée humainement.")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Corps JSON invalide"}), 400
    user_msg = str(data.get("message", "")).strip()
    image_data = data.get("image", "")
    if image_data is not None and not isinstance(image_data, str):
        return jsonify({"error": "Image invalide"}), 400
    image_data = image_data or ""
    if not user_msg and not image_data:
        return jsonify({"error": "Message ou photo requis"}), 400
    # Mode veille : JARVIS ne répond pas, sauf si on le réveille
    if SYSTEM["standby"]:
        low = user_msg.lower()
        if any(w in low for w in ("réveille", "reveille", "ok jarvis", "debout", "wake")):
            SYSTEM["standby"] = False
            return jsonify({"response": "Me revoilà. J'étais en veille, pas mort. Qu'est-ce qu'il te faut ? 😏",
                            "timestamp": datetime.now().isoformat()})
        return jsonify({"response": "😴 *JARVIS est en veille.* Dis « réveille-toi » ou « Ok Jarvis » pour me rallumer.",
                        "standby": True, "timestamp": datetime.now().isoformat()})
    learning_engine.record_chat()
    conv_id = data.get("conversation_id", "")
    conv = convo_store.get(conv_id) if conv_id else None

    # Une photo jointe au chat passe directement par le module spécialisé :
    # elle n'est ni mémorisée ni envoyée au LLM conversationnel général.
    if image_data:
        if photo_geolocator is None or _legal_osint_validator is None:
            return jsonify({"error": "Géolocalisation photo indisponible"}), 503
        context, policy_error, policy_code = _legal_osint_validator(data)
        if not context:
            return jsonify({"error": policy_error, "status": "policy_denied"}), policy_code
        result = photo_geolocator.locate(image_data, hint=user_msg, context=context)
        response_text = _format_photo_geo_response(result)
        if conv is not None:
            conv["messages"].append({"role": "user", "content": "[Photo jointe] " + (user_msg or "Localise cette photo")})
            conv["messages"].append({"role": "assistant", "content": response_text})
            convo_store.touch(conv_id, user_msg or "Photo à localiser")
            convo_store.save()
        event_log.add("photo_geolocation", "Analyse demandée depuis le chat", meta={
            "source": result.get("source", "unknown"),
            "status": result.get("status", "unknown"),
            "purpose": context.purpose,
            "target_type": context.target_type,
        })
        return jsonify({
            "response": response_text,
            "photo_geolocation": result,
            "conversation_id": conv_id,
            "timestamp": datetime.now().isoformat(),
        })

    with _CHAT_LOCK:
        final_response = None
        if AGENT_ENABLED:
            if conv is not None:
                final_response = agent.run(user_msg, get_system_prompt(),
                                           hist=conv["messages"],
                                           on_save=lambda: convo_store.touch(conv_id, user_msg) or convo_store.save())
            else:
                final_response = agent.run(user_msg, get_system_prompt())
        if final_response is None:
            # Fallback : ancien système de tags (intact)
            raw_response = ai_engine.chat(user_msg)
            final_response = execute_jarvis_commands(raw_response, security)
            if conv is not None:
                conv["messages"].append({"role": "user", "content": user_msg})
                conv["messages"].append({"role": "assistant", "content": final_response})
                convo_store.touch(conv_id, user_msg)
                convo_store.save()

    event_log.add("chat", user_msg[:120], meta={"reply": final_response[:160]})
    return jsonify({"response": final_response, "conversation_id": conv_id,
                    "backend": AI_BACKEND, "model": CONFIG[AI_BACKEND]["model"],
                    "timestamp": datetime.now().isoformat()})


@app.route("/api/conversations", methods=["GET", "POST"])
def conversations():
    if request.method == "POST":
        d = request.get_json(silent=True) or {}
        return jsonify(convo_store.create(d.get("title", "Nouvelle conversation")))
    return jsonify({"conversations": convo_store.list()})


@app.route("/api/conversations/<cid>", methods=["GET", "DELETE"])
def conversation(cid):
    if request.method == "DELETE":
        return jsonify({"deleted": convo_store.delete(cid)})
    c = convo_store.get(cid)
    if not c:
        return jsonify({"error": "introuvable"}), 404
    return jsonify(c)


@app.route("/api/security/stream")
def video_feed():
    return Response(security.video_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/security/alerts")
def get_alerts():
    return jsonify({"alerts": security.alerts, "armed": security.armed, "stats": security.stats})


@app.route("/api/security/arm", methods=["POST"])
def arm():
    data = request.get_json(silent=True) or {}
    target = bool(data.get("armed", True))
    if not target and not bool(data.get("confirm", False)):
        return jsonify({"error": "Confirmation explicite requise pour désarmer."}), 400
    return jsonify({"message": security.set_armed(target), "armed": security.armed})


@app.route("/api/security/enroll", methods=["POST"])
def enroll_face():
    """Enregistre le visage actuellement vu par la caméra comme 'de confiance'."""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Nom requis"}), 400
    frame = security.raw_frame if security.raw_frame is not None else security.current_frame
    if frame is None:
        return jsonify({"error": "Pas d'image caméra"}), 400
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)   # frame BRUTE (sans HUD/rectangles)
    return jsonify({"message": security.facebank.enroll(name, gray)})


@app.route("/api/security/snapshot")
def snapshot():
    jpeg = security.get_jpeg_frame()
    return jsonify({"image": base64.b64encode(jpeg).decode(), "timestamp": datetime.now().isoformat()})


# ── 🏠 Domotique ──
@app.route("/api/home/lights")
def home_lights():
    return jsonify(lights.list_lights())


@app.route("/api/home/light", methods=["POST"])
def home_light_set():
    d = request.get_json(silent=True) or {}
    return jsonify({"message": lights.set_state(
        d.get("name", "toutes"), on=d.get("on"), bri=d.get("bri"), color=d.get("color"))})


@app.route("/api/home/scene", methods=["POST"])
def home_scene():
    d = request.get_json(silent=True) or {}
    return jsonify({"message": apply_scene(d.get("name", ""))})


@app.route("/api/home/scenes")
def home_scenes():
    return jsonify({"scenes": list(CONFIG["scenes"].keys())})


@app.route("/api/apple/devices")
def apple_devices():
    return jsonify({"available": apple_home.available, "devices": apple_home.scan()})


@app.route("/api/apple/say", methods=["POST"])
def apple_say():
    d = request.get_json(silent=True) or {}
    return jsonify({"message": apple_home.say(d.get("text", ""), d.get("device", ""))})


@app.route("/api/apple/appletv/<command>", methods=["POST"])
def apple_tv_cmd(command):
    return jsonify({"message": apple_home.appletv_command(command, CONFIG["apple"]["default_tv"])})


# ── 🖥️ Contrôle PC ──
@app.route("/api/pc/screenshot", methods=["POST"])
def pc_screenshot():
    shot = pc.screenshot()
    out = {"message": shot["msg"], "ok": shot["ok"]}
    if shot["ok"]:
        try:
            out["image"] = base64.b64encode(Path(shot["path"]).read_bytes()).decode()
        except Exception:
            pass
    event_log.add("pc", "Capture d'écran", meta={})
    return jsonify(out)


@app.route("/api/pc/media/<action>", methods=["POST"])
def pc_media(action):
    return jsonify({"message": pc.media(action)})


@app.route("/api/pc/power", methods=["POST"])
def pc_power():
    d = request.get_json(silent=True) or {}
    action = d.get("action", "")
    res = pc.power(action, confirm=bool(d.get("confirm", False)))
    event_log.add("pc", f"Alimentation : {action}", level="warn")
    return jsonify({"message": res})


@app.route("/api/pc/kill", methods=["POST"])
def pc_kill():
    d = request.get_json(silent=True) or {}
    return jsonify({"message": pc.kill_process(d.get("target", ""))})


@app.route("/api/pc/brightness", methods=["POST"])
def pc_brightness():
    d = request.get_json(silent=True) or {}
    return jsonify({"message": pc.brightness(int(d.get("level", 80)))})


@app.route("/api/pc/lock", methods=["POST"])
def pc_lock():
    return jsonify({"message": pc.lock()})


@app.route("/api/pc/clipboard", methods=["GET", "POST"])
def pc_clipboard():
    if request.method == "POST":
        d = request.get_json(silent=True) or {}
        return jsonify({"message": pc.clipboard_set(d.get("text", ""))})
    return jsonify({"content": pc.clipboard_get()})


@app.route("/api/pc/active-window")
def pc_active_window():
    return jsonify({"message": pc.active_window()})


@app.route("/api/vision/analyze", methods=["POST"])
def vision_analyze():
    """Analyse vision réelle d'une capture (écran ou caméra)."""
    d = request.get_json(silent=True) or {}
    source = d.get("source", "camera")
    if source == "screen":
        b = pc.screenshot_bytes()
        if not b:
            return jsonify({"message": "Capture impossible."}), 400
        img = base64.b64encode(b).decode()
    else:
        img = base64.b64encode(security.get_jpeg_frame()).decode()
    if not vision.available():
        return jsonify({"message": "Vision réelle non active (ollama pull llava).",
                        "available": False})
    return jsonify({"message": vision.analyze(img, d.get("prompt", "")), "available": True})


@app.route("/api/timeline")
def timeline():
    return jsonify({"events": event_log.recent(
        n=int(request.args.get("n", 80)), kind=request.args.get("type"))})


@app.route("/api/stream")
def stream():
    """Bus temps réel (SSE) : pousse les évènements au dashboard."""
    q = queue.Queue(maxsize=100)
    def _push(ev):
        try:
            q.put_nowait(ev)
        except queue.Full:
            pass
    event_log.subscribers.append(_push)

    def gen():
        try:
            yield "event: hello\ndata: {}\n\n"
            while True:
                try:
                    ev = q.get(timeout=20)
                    yield f"event: {ev['kind']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    yield ": keep-alive\n\n"
        finally:
            try:
                event_log.subscribers.remove(_push)
            except ValueError:
                pass
    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── 🔔 Approbations d'actions sensibles/critiques (cloche d'approbation) ──
@app.route("/api/approvals")
def approvals_list():
    return jsonify({"pending": permission_manager.pending()})


@app.route("/api/approvals/confirm", methods=["POST"])
def approvals_confirm():
    body = request.get_json(silent=True) or {}
    token = body.get("approval_id", "")
    entry = next((a for a in permission_manager.pending() if a["approval_id"] == token), None)
    if not entry:
        return jsonify({"ok": False, "message": "Demande introuvable ou expirée."}), 404
    # Exécute l'action EXACTE approuvée (jeton usage unique consommé par le guard).
    result = tool_registry.call(entry["action"], entry["params"], approval_token=token)
    event_log.add("approbation", f"Action confirmée : {entry['action']}",
                  meta={"params": entry["params"], "context_id": entry.get("context_id", "")})
    if mission_orchestrator is not None and entry.get("context_id"):
        mission_orchestrator.on_approval_result(entry["context_id"], result,
                                                step_id=entry.get("step_id", ""), approved=True)
    return jsonify({"ok": True, "action": entry["action"], "result": result})


@app.route("/api/approvals/reject", methods=["POST"])
def approvals_reject():
    body = request.get_json(silent=True) or {}
    token = body.get("approval_id", "")
    entry = next((a for a in permission_manager.pending() if a["approval_id"] == token), None)
    ok = permission_manager.reject(token)
    if ok:
        event_log.add("approbation", "Action refusée par l'utilisateur.")
        if mission_orchestrator is not None and entry and entry.get("context_id"):
            mission_orchestrator.on_approval_result(
                entry["context_id"], f"Action refusée : {entry['action']}",
                step_id=entry.get("step_id", ""), approved=False)
    return jsonify({"ok": ok})


@app.route("/api/automations")
def automations_list():
    return jsonify({"enabled": automation.enabled, "rules": automation.rules()})


@app.route("/api/automations/toggle", methods=["POST"])
def automations_toggle():
    d = request.get_json(silent=True) or {}
    automation.enabled = bool(d.get("enabled", True))
    return jsonify({"enabled": automation.enabled})


@app.route("/api/proactive/briefing", methods=["POST"])
def proactive_briefing():
    return jsonify({"briefing": proactive.briefing_now()})


@app.route("/api/security/pending")
def security_pending():
    """Questions 'connu/inconnu ?' en attente de réponse de l'utilisateur."""
    return jsonify({"pending": [p for p in security.pending if p["status"] == "en_attente"]})


@app.route("/api/security/identify", methods=["POST"])
def security_identify():
    d = request.get_json(silent=True) or {}
    qid = d.get("id", "")
    known = bool(d.get("known", False))
    name = d.get("name", "").strip()
    return jsonify({"message": security.resolve_identity(qid, known, name)})


@app.route("/api/system/standby", methods=["POST"])
def system_standby():
    d = request.get_json(silent=True) or {}
    SYSTEM["standby"] = bool(d.get("on", True))
    return jsonify({"standby": SYSTEM["standby"],
                    "message": "😴 JARVIS en veille." if SYSTEM["standby"] else "🟢 JARVIS réveillé."})


@app.route("/api/system/shutdown", methods=["POST"])
def system_shutdown():
    """Éteint complètement JARVIS (arrête caméra + serveur). Confirmation requise."""
    d = request.get_json(silent=True) or {}
    if not d.get("confirm"):
        return jsonify({"error": "Confirmation requise (confirm=true)."}), 400
    logger.warning("⏻ Extinction demandée via le dashboard.")
    event_log.add("system", "Extinction de JARVIS", level="warn")
    security.stop()

    def _kill():
        time.sleep(0.5)
        os._exit(0)
    threading.Thread(target=_kill, daemon=True).start()
    return jsonify({"message": "⏻ JARVIS s'éteint. À la prochaine. Relance avec : python server/jarvis_v4.py"})


@app.route("/api/emergency/call-owner", methods=["POST"])
def emergency_call_owner():
    d = request.get_json(silent=True) or {}
    return jsonify({"message": emergency_dispatcher.call_owner(d.get("message", ""))})


@app.route("/api/emergency/police", methods=["POST"])
def emergency_police():
    d = request.get_json(silent=True) or {}
    reason = d.get("reason", "Demande d'urgence manuelle")
    confirm = bool(d.get("confirm", False))
    snap = security.last_snapshot if security.last_snapshot else ""
    res = emergency_dispatcher.dispatch(reason, snapshot=snap, source="dashboard",
                                        allow_call=confirm, severity="extrême")
    return jsonify(res)


@app.route("/api/security/feedback", methods=["POST"])
def security_feedback():
    """L'utilisateur marque une alerte comme fausse → JARVIS apprend et s'adapte."""
    d = request.get_json(silent=True) or {}
    if d.get("false"):
        return jsonify({"message": learning_engine.note_false_alarm(),
                        "sensitivity_adj": learning_engine.data["sensitivity_adj"]})
    learning_engine.note_confirmed_alarm()
    return jsonify({"message": "Alerte confirmée comme réelle. Je garde l'œil ouvert."})


@app.route("/api/learning/profile")
def learning_profile():
    return jsonify(learning_engine.stats())


@app.route("/api/web/search")
def web_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "Paramètre q requis"}), 400
    return jsonify(websearch.search(q, max_results=int(request.args.get("n", 5))))


@app.route("/api/web/read")
def web_read():
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"error": "Paramètre url requis"}), 400
    return jsonify({"url": url, "text": websearch.read_page(url)})


# ── 🛰️ OSINT d'INFRASTRUCTURE (IP / domaine / hachage — jamais de personnes) ──
_OSINT_HITS = []


@app.route("/api/osint/lookup")
def osint_lookup():
    import osint
    q = request.args.get("q", "").strip()[:253]
    if not q:
        return jsonify({"ok": False, "error": "Paramètre q requis"}), 400
    # Rate-limit simple (10/min) : l'OSINT fait des appels réseau.
    now = time.time()
    _OSINT_HITS[:] = [t for t in _OSINT_HITS if now - t < 60]
    if len(_OSINT_HITS) >= 10:
        return jsonify({"ok": False, "error": "Trop de requêtes OSINT"}), 429
    _OSINT_HITS.append(now)
    res = osint.lookup(q)
    event_log.add("osint", f"Lookup {res.get('type','?')} : {q}", meta={"type": res.get("type")})
    return jsonify(res)


# ── Ressources statiques auto-hébergées (fond de carte GeoJSON, etc.) ──
@app.route("/assets/<path:fn>")
def web_assets(fn):
    assets = Path(__file__).resolve().parent.parent / "web" / "assets"
    return send_from_directory(assets, fn, max_age=86400)


@app.route("/api/notify/test", methods=["POST"])
def notify_test():
    return jsonify({"enabled": notifier.enabled,
                    "message": notifier.send("✅ Test JARVIS : les notifications à distance fonctionnent.")})


@app.route("/api/memory/clear", methods=["POST"])
def clear_memory():
    ai_engine.clear_history()
    return jsonify({"status": "ok", "message": "Mémoire effacée. Je suis comme neuf. Ou presque."})


@app.route("/api/status")
def status():
    return jsonify({
        "status": "JARVIS EN LIGNE 🟢", "backend": AI_BACKEND,
        "model": CONFIG[AI_BACKEND]["model"], "camera": security.running,
        "armed": security.armed, "memory_messages": len(ai_engine.history),
        "alerts": len(security.alerts), "uptime": datetime.now().isoformat(),
        "apple": apple_home.available, "lights_mode": lights.mode,
        "face_recognition": HAS_FACE_RECOGNITION,
        "remote_notify": notifier.enabled,
        "telephony": emergency_dispatcher.telephony,
        "interactions": learning_engine.data.get("interactions", 0),
        "sensitivity_adj": learning_engine.data.get("sensitivity_adj", 0),
        "standby": SYSTEM["standby"], "auth": AUTH_ENABLED,
        "pending": len([p for p in security.pending if p["status"] == "en_attente"]),
        "agent": AGENT_ENABLED, "automations": automation.enabled,
        "memory_rag": vmem.has_embed, "vision": vision.available(),
        "tools": len(tool_registry.names()), "version": "5.6",
        "conversations": len(convo_store.data), "pouvoirs": 54,
        "agency": mission_orchestrator is not None,
        "agency_active": len([m for m in mission_store.list(100) if m["status"] in
                              ("queued", "planning", "running", "verifying", "retry_wait", "waiting_approval", "paused", "blocked", "interrupted")])
                         if mission_store is not None else 0,
        "voice": voice_service.status() if voice_service is not None else {"enabled": False},
        "n8n": n8n_client.status(), "email": {"configured": email_service.configured},
    })


@app.route("/api/quick/<action>")
def quick_action(action):
    if action == "info":
        return jsonify(powers.pc_info())
    elif action == "meteo":
        return jsonify(powers.get_weather(request.args.get("city", "Paris")))
    elif action == "blague":
        return jsonify({"blague": powers.get_blague()})
    elif action == "reseau":
        return jsonify(powers.get_network_info())
    elif action == "processus":
        return jsonify({"processus": powers.get_processes()})
    elif action == "disque":
        return jsonify(powers.disk_space())
    elif action == "motdepasse":
        return jsonify({"password": powers.gen_password()})
    return jsonify({"error": "Action inconnue"}), 404


# ─────────────────────────────────────────────
# DASHBOARD HTML
# ─────────────────────────────────────────────
LOGIN_HTML = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>JARVIS — Connexion</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:radial-gradient(1000px 500px at 70% -10%,#10204020,transparent),linear-gradient(180deg,#0a0e1a,#05070d);
  color:#EDEDEF;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
.card{background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.1);border-radius:18px;padding:36px 30px;width:100%;max-width:360px;
  backdrop-filter:blur(14px);box-shadow:0 8px 40px rgba(0,0,0,.5);text-align:center}
.orb{width:54px;height:54px;border-radius:50%;margin:0 auto 18px;background:radial-gradient(circle at 35% 30%,#9fe6ff,#38bdf8 45%,#1f6f9c);box-shadow:0 0 26px rgba(56,189,248,.4);animation:b 3s ease-in-out infinite}
@keyframes b{0%,100%{transform:scale(1)}50%{transform:scale(1.08)}}
h1{font-size:1.2rem;letter-spacing:4px;margin-bottom:6px}
p{color:#8A8F98;font-size:.82rem;margin-bottom:22px}
input{width:100%;background:#05070d;border:1px solid rgba(255,255,255,.12);color:#fff;padding:13px 15px;border-radius:11px;font-size:.92rem;margin-bottom:14px;font-family:inherit}
input:focus{outline:none;border-color:#38bdf8;box-shadow:0 0 0 3px rgba(56,189,248,.2)}
button{width:100%;background:linear-gradient(180deg,#3fc4ff,#1f93cc);color:#001018;border:0;padding:13px;border-radius:11px;font-weight:600;font-size:.92rem;cursor:pointer;font-family:inherit}
button:hover{box-shadow:0 0 18px rgba(56,189,248,.35)}
.err{color:#ef4444;font-size:.8rem;margin-bottom:12px}
</style></head>
<body><form class="card" method="POST" action="/login">
  <div class="orb"></div><h1>JARVIS</h1><p>Accès sécurisé au centre de contrôle</p>
  {% if error %}<div class="err">{{ error }}</div>{% endif %}
  <input type="password" name="password" placeholder="Mot de passe" autofocus autocomplete="current-password">
  <button type="submit">Déverrouiller</button>
</form></body></html>"""

# Ancien dashboard HTML embarqué supprimé : web/index.html est l’unique interface.


# ─────────────────────────────────────────────
# 🛡️ MODE GARDIEN (module intégré)
# ─────────────────────────────────────────────
try:
    from guardian.config import load_config as _g_load_config
    from guardian.store import GuardianStore
    from guardian.service import GuardianService
    from guardian.providers import get_vision_provider, get_speech_provider, get_realtime_provider
    from guardian.pairing import DevicePairing
    from guardian.geolocation import PhotoGeolocator
    from guardian.legal_osint import validate_legal_osint_context
    from guardian.api import create_guardian_blueprint
    from permissions import PermissionManager
    from emergency_approval import EmergencyApproval

    GUARDIAN_CONFIG = _g_load_config()
    _g_store = GuardianStore(GUARDIAN_CONFIG.db_path, GUARDIAN_CONFIG.retention_days)
    _g_vision = get_vision_provider(GUARDIAN_CONFIG)
    _g_speech = get_speech_provider(GUARDIAN_CONFIG)
    _g_realtime = get_realtime_provider(GUARDIAN_CONFIG)
    guardian_service = GuardianService(
        config=GUARDIAN_CONFIG, vision_provider=_g_vision, speech_provider=_g_speech,
        store=_g_store, notifier=notifier, emergency=emergency_dispatcher,
        event_log=event_log)
    # Réutilise le gestionnaire de permissions partagé (défini plus haut).
    emergency_approval = EmergencyApproval(emergency_dispatcher, permission_manager,
                                           audit_log=event_log.add)
    device_pairing = DevicePairing()
    photo_geolocator = PhotoGeolocator(GUARDIAN_CONFIG, _g_vision, event_log=event_log)
    _legal_osint_validator = validate_legal_osint_context
    _WEB_DIR = Path(__file__).resolve().parent.parent / "web"
    app.register_blueprint(create_guardian_blueprint(
        guardian_service, perms=permission_manager,
        emergency_approval=emergency_approval, realtime_provider=_g_realtime,
        pairing=device_pairing, geolocator=photo_geolocator, web_dir=str(_WEB_DIR)))
    logger.info("🛡️ Mode Gardien intégré : /gardien + /api/guardian/* "
                f"(vision={GUARDIAN_CONFIG.vision_provider}, cloud={GUARDIAN_CONFIG.cloud_vision}, "
                f"audio={GUARDIAN_CONFIG.audio_enabled})")
except Exception as _ge:                       # ne casse jamais le serveur principal
    logger.warning(f"Mode Gardien non chargé: {_ge}")


@app.errorhandler(413)
def _request_too_large(_error):
    return jsonify({"ok": False, "error": "Requête trop volumineuse"}), 413


@app.after_request
def _security_headers(resp):
    """En-têtes de sécurité (CSP, Permissions-Policy…) sur les pages servies.

    CSP stricte : aucun script externe (on supprime les scripts opaques
    tiers opaques). 'self' + inline (l'app embarque son JS). Permissions-Policy
    restreint caméra/micro à la même origine (nécessaire au Gardien)."""
    is_html = "text/html" in (resp.headers.get("Content-Type", ""))
    if is_html:
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self'; "
            "img-src 'self' data: blob:; "
            "media-src 'self' blob:; "
            "connect-src 'self'; "
            "worker-src 'self' blob:; frame-src 'self'; object-src 'none'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        resp.headers["Permissions-Policy"] = (
            "camera=(self), microphone=(self), geolocation=(), "
            "payment=(), usb=(), interest-cohort=()")
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return resp


# ─────────────────────────────────────────────
# LANCEMENT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # ── HTTPS : certs fournis, sinon adhoc (si cryptography), sinon HTTP ──
    ssl_ctx = None
    scheme = "http"
    h = CONFIG["https"]
    if h["cert"] and h["key"]:
        ssl_ctx = (h["cert"], h["key"]); scheme = "https"
    elif h["adhoc"]:
        try:
            import cryptography  # noqa: F401
            ssl_ctx = "adhoc"; scheme = "https"
        except ImportError:
            logger.warning("JARVIS_HTTPS=adhoc demandé mais 'cryptography' absent — démarrage en HTTP. (pip install cryptography)")

    print("""
╔══════════════════════════════════════════════════╗
║   JARVIS v5.6 — DURABLE AGENCY + PROSPECTION + VOIX      ║
║   Backend: """ + AI_BACKEND.upper() + " — " + CONFIG[AI_BACKEND]["model"] + """
║   HomePod•AppleTV•Lumières•Anti-intrusion•Voix   ║
╠══════════════════════════════════════════════════╣
║   Dashboard → """ + f"{scheme}://localhost:{CONFIG['http_port']}" + """
╚══════════════════════════════════════════════════╝""")
    if AUTH_ENABLED:
        if CONFIG["auth"]["password"]:
            print("🔐 Authentification ACTIVE (mot de passe défini via JARVIS_PASSWORD).")
        else:
            print(f"🔐 Authentification ACTIVE — mot de passe généré : \033[1;36m{AUTH_PASSWORD}\033[0m")
            print("   (définis JARVIS_PASSWORD pour en choisir un fixe)")
    else:
        print("⚠️  Authentification DÉSACTIVÉE (JARVIS_AUTH=0) — dashboard ouvert. Déconseillé.")
    if scheme == "http":
        print("⚠️  HTTP en clair. Pour du HTTPS : JARVIS_HTTPS=adhoc (test) ou JARVIS_SSL_CERT/KEY (prod).")

    print("ℹ️  Lancement direct = serveur de développement. En usage permanent, utilise Waitress/Gunicorn via server/wsgi.py.")
    security.start()
    automation.start()
    proactive.start()
    if CONFIG["http_host"] == "0.0.0.0":
        print("⚠️  Exposé sur 0.0.0.0 (tout le LAN). Assure-toi d'avoir auth + HTTPS.")
    app.run(host=CONFIG["http_host"], port=CONFIG["http_port"],
            debug=False, threaded=True, ssl_context=ssl_ctx)
