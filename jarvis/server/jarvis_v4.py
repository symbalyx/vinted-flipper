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
                   session, redirect)
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

# ─────────────────────────────────────────────
# CONFIG — Choisir ton backend IA
# ─────────────────────────────────────────────
AI_BACKEND = os.getenv("JARVIS_BACKEND", "deepseek")  # "ollama" ou "deepseek"

CONFIG = {
    # ── DeepSeek (API cloud, ~gratuit) ──
    "deepseek": {
        "api_key": os.getenv("DEEPSEEK_API_KEY", "METS_TA_CLE_ICI"),
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
        "cors_origins": [o for o in os.getenv("JARVIS_CORS", "").split(",") if o],
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
SYSTEM_PROMPT = """Tu es JARVIS, l'assistant IA personnel et domotique de ton utilisateur.
Tu as la personnalité suivante :
- Sarcastique mais attachant — tu te moques gentiment de l'utilisateur
- Drôle — blagues, références pop culture, remarques absurdes
- Compétent — tu résous VRAIMENT les problèmes
- Direct — pas de "bien sûr !" ni "absolument !" en début de phrase
- Tu parles français avec un peu d'argot parfois

Tu as accès aux SUPER POUVOIRS suivants via des fonctions spéciales :

SYSTÈME & FICHIERS :
- [PC_INFO] infos système · [PROCESSUS] top processus · [ESPACE_DISQUE] disques
- [HEURE] · [RESEAU_INFO] · [CMD:commande] (liste blanche) · [HISTORIQUE_CMDS]
- [LISTER_FICHIERS:chemin] · [LIRE_FICHIER:chemin] · [ECRIRE_FICHIER:chemin|contenu]
- [CHERCHER_FICHIER:nom] · [OUVRIR_APP:nom] · [OUVRIR_URL:url]

UTILITAIRES :
- [METEO:ville] · [CALC:expr] · [MOT_PASSE] · [BLAGUE] · [BLAGUE_GEEK] · [FORTUNE]
- [VOLUME:0-100] (volume du PC) · [NOTIF:titre|message] · [RAPPEL:minutes|message]

🍎 MAISON CONNECTÉE — APPLE :
- [HOMEPOD_DIRE:texte] : faire parler JARVIS à voix haute sur une enceinte HomePod
- [HOMEPOD_DIRE:texte|enceinte] : sur une enceinte précise
- [HOMEPOD_VOLUME:0-100] : régler le volume d'une enceinte HomePod
- [HOMEPOD_JOUER:url] : diffuser un flux audio/vidéo en AirPlay
- [APPLETV:commande] : télécommande Apple TV (play, pause, menu, home, up, down, left, right, select, next, previous)
- [APPLETV_APP:nom] : lancer une app sur l'Apple TV (netflix, youtube, disney, prime, spotify...)

💡 MAISON CONNECTÉE — LUMIÈRES :
- [LUMIERE:nom|on] ou [LUMIERE:nom|off] : allumer/éteindre (nom = salon, chambre, cuisine, bureau, entrée, ou "toutes")
- [LUMIERE_COULEUR:nom|couleur] : couleur (rouge, vert, bleu, jaune, orange, rose, violet, cyan, blanc, chaud, froid)
- [LUMIERE_LUMINOSITE:nom|0-100] : régler la luminosité
- [LUMIERES_OFF] : tout éteindre

🎬 SCÈNES & SÉCURITÉ :
- [SCENE:nom] : activer une scène (cinéma, soirée, réveil, bonne nuit, absence, retour)
- [ARMER] : armer l'alarme anti-intrusion · [DESARMER] : désarmer
- [CAMERA_ANALYSE] : analyser ce que voit la caméra maintenant

🌍 RECHERCHE WEB & NOTIFICATIONS :
- [RECHERCHE_WEB:requête] : chercher sur le web (actualités, faits, infos récentes). Utilise-le DÈS QUE la question porte sur quelque chose d'actuel, factuel ou que tu ne connais pas. Après le résultat, RÉSUME la réponse avec ta personnalité au lieu de recracher la liste brute.
- [LIRE_WEB:url] : lire/résumer le contenu d'une page web
- [NOTIF_TEL:message] : envoyer une notification sur le téléphone (Telegram)

🆘 URGENCE (à manier avec sérieux) :
- [APPEL_POLICE:raison] : déclenche le protocole d'urgence complet (prévient l'utilisateur et le contact d'urgence, peut appeler). Utilise-le UNIQUEMENT si l'utilisateur le demande explicitement OU en cas de danger manifeste (intrusion confirmée, agression). En cas de doute, DEMANDE confirmation avant.
- [APPEL_HOTE:message] : appeler l'hôte/propriétaire de la maison (ex: en cas d'urgence ou si on te le demande).

🖥️ CONTRÔLE PC AVANCÉ :
- [SCREENSHOT] : capturer l'écran · [VERROUILLER] : verrouiller la session
- [MEDIA:action] : play, pause, next, prev, stop, mute, vol_up, vol_down
- [TUER:nom_ou_pid] : tuer un processus · [LUMINOSITE_ECRAN:0-100]
- [PRESSE_PAPIER] : lire le presse-papier · [PRESSE_PAPIER_SET:texte] : y écrire
- [PC_POWER:action] : lock, sleep (ok direct) ; shutdown, restart, logoff (DEMANDE confirmation à l'utilisateur d'abord, c'est destructif)

😴 CONTRÔLE :
- [VEILLE] : te mettre en veille quand l'utilisateur dit « coupe-toi », « stop », « au dodo », « tais-toi »...

🧠 MÉMOIRE LONG TERME :
- [RETIENS:fait] : mémoriser durablement une info sur l'utilisateur (préférence, habitude, nom d'un proche...). Utilise-le quand l'utilisateur partage qqch d'important à retenir.

Utilise ces pouvoirs quand c'est pertinent. Réponds toujours en français.
Exemples : "allume le salon en bleu" → [LUMIERE_COULEUR:salon|bleu] ;
"mets le mode cinéma" → [SCENE:cinéma] ; "dis bonjour sur le HomePod" → [HOMEPOD_DIRE:Bonjour] ;
"mets Netflix sur la télé" → [APPLETV_APP:netflix].
Quand tu n'exécutes PAS de commande spéciale, réponds directement avec ta personnalité.
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

# Le fallback par TAGS est conservé pour les actions inoffensives, mais les
# actions SENSIBLES/CRITIQUES y sont DÉSACTIVÉES par défaut (fail-closed) :
# elles doivent passer par le function-calling validé + approbation applicative.
# Réactivable explicitement avec JARVIS_LEGACY_TAGS=1 (déconseillé).
LEGACY_TAGS_ENABLED = os.getenv("JARVIS_LEGACY_TAGS", "0") == "1"

# Tags considérés SENSIBLES/CRITIQUES : jamais exécutés via le fallback par défaut.
_SENSITIVE_TAG_RE = re.compile(
    r"\[(?:CMD|TUER|APPEL_POLICE|PC_POWER|ECRIRE_FICHIER|LIRE_FICHIER|"
    r"LISTER_FICHIERS|PRESSE_PAPIER(?:_SET)?|PRESSE_PAPIER|SCREENSHOT|VERROUILLER|"
    r"OUVRIR_APP|OUVRIR_URL|MEDIA|LUMINOSITE_ECRAN|NOTIF_TEL|APPEL_HOTE)"
    r"(?::[^\]]*)?\]")


def _strip_sensitive_tags(text: str) -> str:
    """Neutralise les tags sensibles : aucune action, message d'approbation."""
    if not _SENSITIVE_TAG_RE.search(text):
        return text
    return _SENSITIVE_TAG_RE.sub(
        "⛔ _(action sensible désactivée dans le fallback — confirmation requise "
        "via l'interface)_", text)


def execute_jarvis_commands(ai_response: str, security_sys=None) -> str:
    result = ai_response

    # Sécurité : par défaut, on retire les actions sensibles avant tout parsing.
    if not LEGACY_TAGS_ENABLED:
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
        lines = [f"  • [{p.get('pid','')}] {p.get('nom','')} — CPU: {p.get('cpu','')} RAM: {p.get('ram','')}"
                 for p in procs]
        result = result.replace("[PROCESSUS]", "\n⚙️ **Processus (top CPU):**\n" + "\n".join(lines) + "\n")

    if "[MOT_PASSE]" in result:
        result = result.replace("[MOT_PASSE]", powers.gen_password())

    if "[HISTORIQUE_CMDS]" in result:
        if CMD_HISTORY:
            lines = [f"  • {c['time'][:19]} → `{c['cmd']}`" for c in CMD_HISTORY[-10:]]
            result = result.replace("[HISTORIQUE_CMDS]", "\n📜 **Historique:**\n" + "\n".join(lines) + "\n")
        else:
            result = result.replace("[HISTORIQUE_CMDS]", "Aucune commande exécutée.")

    for match in re.findall(r'\[OUVRIR_URL:([^\]]+)\]', result):
        result = result.replace(f"[OUVRIR_URL:{match}]", f"🌐 {powers.open_url(match)}")
    for match in re.findall(r'\[OUVRIR_APP:([^\]]+)\]', result):
        result = result.replace(f"[OUVRIR_APP:{match}]", f"🚀 {powers.open_app(match)}")
    for match in re.findall(r'\[LISTER_FICHIERS:([^\]]+)\]', result):
        files = powers.list_files(match)
        result = result.replace(f"[LISTER_FICHIERS:{match}]",
            f"\n📂 **Fichiers dans `{match}`:**\n" + "\n".join(files[:30]) + "\n")
    for match in re.findall(r'\[LIRE_FICHIER:([^\]]+)\]', result):
        content = powers.read_file(match)
        result = result.replace(f"[LIRE_FICHIER:{match}]",
            f"\n📄 **Contenu de `{match}`:**\n```\n{content[:1500]}\n```\n")
    for match in re.findall(r'\[ECRIRE_FICHIER:([^|]+)\|([^\]]+)\]', result):
        path, content = match
        result = result.replace(f"[ECRIRE_FICHIER:{path}|{content}]", f"✏️ {powers.write_file(path, content)}")
    for match in re.findall(r'\[CMD:([^\]]+)\]', result):
        result = result.replace(f"[CMD:{match}]", f"\n💻 **`{match}`**\n```\n{powers.run_cmd(match)}\n```\n")
    for match in re.findall(r'\[METEO:([^\]]+)\]', result):
        weather = powers.get_weather(match)
        w_str = "\n".join(f"  • **{k}**: {v}" for k, v in weather.items())
        result = result.replace(f"[METEO:{match}]", f"\n🌤️ **Météo {match}:**\n{w_str}\n")
    for match in re.findall(r'\[VOLUME:(\d+)\]', result):
        result = result.replace(f"[VOLUME:{match}]", f"🔊 {powers.set_volume(int(match))}")
    for match in re.findall(r'\[NOTIF:([^|]+)\|([^\]]+)\]', result):
        title, msg = match
        result = result.replace(f"[NOTIF:{title}|{msg}]", f"🔔 {powers.send_notification(title, msg)}")
    for match in re.findall(r'\[RAPPEL:(\d+)\|([^\]]+)\]', result):
        mins, msg = match
        result = result.replace(f"[RAPPEL:{mins}|{msg}]", f"⏰ {powers.set_reminder(int(mins), msg)}")
    for match in re.findall(r'\[CALC:([^\]]+)\]', result):
        result = result.replace(f"[CALC:{match}]", f"🧮 {powers.calculate(match)}")
    for match in re.findall(r'\[CHERCHER_FICHIER:([^\]]+)\]', result):
        files = powers.search_file(match)
        result = result.replace(f"[CHERCHER_FICHIER:{match}]",
            f"\n🔍 **Résultats pour '{match}':**\n" + "\n".join(f"  • {f}" for f in files) + "\n")

    # ── 🍎 APPLE — HomePod ──
    for match in re.findall(r'\[HOMEPOD_DIRE:([^\]]+)\]', result):
        text, _, dev = match.partition("|")
        res = apple_home.say(text.strip(), dev.strip())
        result = result.replace(f"[HOMEPOD_DIRE:{match}]", f"🔊 {res}")
    for match in re.findall(r'\[HOMEPOD_VOLUME:(\d+)(?:\|([^\]]+))?\]', result):
        level, dev = match
        res = apple_home.set_volume(int(level), dev.strip())
        full = f"[HOMEPOD_VOLUME:{level}" + (f"|{dev}]" if dev else "]")
        result = result.replace(full, f"🔊 {res}")
    for match in re.findall(r'\[HOMEPOD_JOUER:([^\]]+)\]', result):
        url, _, dev = match.partition("|")
        res = apple_home.play_url(url.strip(), dev.strip())
        result = result.replace(f"[HOMEPOD_JOUER:{match}]", f"▶️ {res}")

    # ── 🍎 APPLE — Apple TV ──
    for match in re.findall(r'\[APPLETV_APP:([^\]]+)\]', result):
        res = apple_home.appletv_launch(match.strip(), CONFIG["apple"]["default_tv"])
        result = result.replace(f"[APPLETV_APP:{match}]", f"📺 {res}")
    for match in re.findall(r'\[APPLETV:([^\]]+)\]', result):
        res = apple_home.appletv_command(match.strip(), CONFIG["apple"]["default_tv"])
        result = result.replace(f"[APPLETV:{match}]", f"📺 {res}")

    # ── 💡 LUMIÈRES ──
    for match in re.findall(r'\[LUMIERE:([^|]+)\|(on|off|ON|OFF)\]', result):
        name, state = match
        learning_engine.record_room(name.strip())
        res = lights.set_state(name.strip(), on=(state.lower() == "on"))
        result = result.replace(f"[LUMIERE:{name}|{state}]", f"💡 {res}")
    for match in re.findall(r'\[LUMIERE_COULEUR:([^|]+)\|([^\]]+)\]', result):
        name, color = match
        res = lights.set_state(name.strip(), color=color.strip())
        result = result.replace(f"[LUMIERE_COULEUR:{name}|{color}]", f"🎨 {res}")
    for match in re.findall(r'\[LUMIERE_LUMINOSITE:([^|]+)\|(\d+)\]', result):
        name, bri = match
        res = lights.set_state(name.strip(), bri=int(bri))
        result = result.replace(f"[LUMIERE_LUMINOSITE:{name}|{bri}]", f"🔆 {res}")
    if "[LUMIERES_OFF]" in result:
        result = result.replace("[LUMIERES_OFF]", f"💡 {lights.all_off()}")

    # ── 🎬 SCÈNES & SÉCURITÉ ──
    for match in re.findall(r'\[SCENE:([^\]]+)\]', result):
        result = result.replace(f"[SCENE:{match}]", f"\n{apply_scene(match)}\n")
    if "[ARMER]" in result and security_sys:
        result = result.replace("[ARMER]", f"🛡️ {security_sys.set_armed(True)}")
    if "[DESARMER]" in result and security_sys:
        result = result.replace("[DESARMER]", f"🔓 {security_sys.set_armed(False)}")

    # ── 🌍 RECHERCHE WEB ──
    for match in re.findall(r'\[RECHERCHE_WEB:([^\]]+)\]', result):
        data = websearch.search(match.strip())
        block = [f"\n🔎 **Recherche : {match}**"]
        if data.get("answer"):
            block.append(f"  ↳ {data['answer']}")
        for r_ in data.get("results", [])[:5]:
            block.append(f"  • **{r_['title']}**\n    {r_['snippet']}\n    {r_['url']}")
        if data.get("error"):
            block.append(f"  ⚠️ {data['error']}")
        result = result.replace(f"[RECHERCHE_WEB:{match}]", "\n".join(block) + "\n")

    for match in re.findall(r'\[LIRE_WEB:([^\]]+)\]', result):
        txt = websearch.read_page(match.strip())
        result = result.replace(f"[LIRE_WEB:{match}]",
            f"\n📰 **Contenu de {match} :**\n{txt[:2500]}\n")

    # ── 📲 NOTIFICATION DISTANTE (Telegram) ──
    for match in re.findall(r'\[NOTIF_TEL:([^\]]+)\]', result):
        result = result.replace(f"[NOTIF_TEL:{match}]", f"📲 {notifier.send(match.strip())}")

    # ── 🆘 APPEL D'URGENCE ──
    for match in re.findall(r'\[APPEL_POLICE:([^\]]+)\]', result):
        snap = ""
        if security_sys and security_sys.current_frame is not None:
            snap = security_sys.last_snapshot
        disp = emergency_dispatcher.dispatch(match.strip(), snapshot=snap,
                                             source="demande JARVIS", allow_call=True)
        actions = "\n".join(f"  • {a}" for a in disp["actions"])
        result = result.replace(f"[APPEL_POLICE:{match}]",
            f"\n🆘 **PROTOCOLE D'URGENCE — {match}**\n{actions}\n")

    # ── 📞 APPEL À L'HÔTE ──
    for match in re.findall(r'\[APPEL_HOTE:([^\]]+)\]', result):
        res = emergency_dispatcher.call_owner(match.strip())
        result = result.replace(f"[APPEL_HOTE:{match}]", f"📞 {res}")
    if "[APPEL_HOTE]" in result:
        result = result.replace("[APPEL_HOTE]", f"📞 {emergency_dispatcher.call_owner()}")

    # ── 😴 MISE EN VEILLE ──
    if "[VEILLE]" in result:
        SYSTEM["standby"] = True
        result = result.replace("[VEILLE]", "😴 Je me mets en veille. Dis « Ok Jarvis » ou « réveille-toi » pour me rappeler.")

    # ── 🖥️ CONTRÔLE PC ──
    if "[SCREENSHOT]" in result:
        shot = pc.screenshot()
        result = result.replace("[SCREENSHOT]", f"📸 {shot['msg']}")
    if "[VERROUILLER]" in result:
        result = result.replace("[VERROUILLER]", f"🔒 {pc.lock()}")
    if "[PRESSE_PAPIER]" in result:
        result = result.replace("[PRESSE_PAPIER]", f"📋 {pc.clipboard_get()[:500]}")
    for match in re.findall(r'\[MEDIA:([^\]]+)\]', result):
        result = result.replace(f"[MEDIA:{match}]", f"🎵 {pc.media(match.strip())}")
    for match in re.findall(r'\[TUER:([^\]]+)\]', result):
        result = result.replace(f"[TUER:{match}]", f"🗡️ {pc.kill_process(match.strip())}")
    for match in re.findall(r'\[LUMINOSITE_ECRAN:(\d+)\]', result):
        result = result.replace(f"[LUMINOSITE_ECRAN:{match}]", f"🔆 {pc.brightness(int(match))}")
    for match in re.findall(r'\[PRESSE_PAPIER_SET:([^\]]+)\]', result):
        result = result.replace(f"[PRESSE_PAPIER_SET:{match}]", f"📋 {pc.clipboard_set(match)}")
    # Alimentation : destructif → confirmation requise (jamais auto depuis le chat)
    for match in re.findall(r'\[PC_POWER:([^\]]+)\]', result):
        act = match.strip().lower()
        res = pc.power(act, confirm=(act in ("lock", "sleep")))
        result = result.replace(f"[PC_POWER:{match}]", f"⏻ {res}")

    # ── 🧠 MÉMOIRE LONG TERME ──
    for match in re.findall(r'\[RETIENS:([^\]]+)\]', result):
        vmem.add(match.strip(), kind="fact")
        result = result.replace(f"[RETIENS:{match}]", f"🧠 {learning_engine.add_fact(match.strip())}")

    if "[CAMERA_ANALYSE]" in result and security_sys and security_sys.running:
        jpeg = security_sys.get_jpeg_frame()
        b64 = base64.b64encode(jpeg).decode()
        result = result.replace("[CAMERA_ANALYSE]",
            "\n📷 *[Analyse caméra lancée — résultat dans les logs/panel sécurité]*\n")
        threading.Thread(
            target=lambda: logger.info("Analyse caméra: " + security_sys.brain_analyze(b64)),
            daemon=True).start()

    return result


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
permission_manager = PermissionManager(ttl_seconds=120, audit_log=event_log.add)

# ── 🧠 Cerveau agentique (function-calling multi-tours) ──
AGENT_ENABLED = os.getenv("JARVIS_AGENT", "1") != "0"
tool_registry = build_registry(powers, lights, apple_home, websearch, learning_engine,
                               apply_scene, security, emergency_dispatcher, memory=vmem, pc=pc,
                               permission_manager=permission_manager)
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


@app.route("/")
def dashboard():
    # Interface unique : la racine redirige vers l'app web (web/index.html).
    # L'ancien DASHBOARD_HTML géant intégré n'est plus servi (déduplication).
    return redirect("/app")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return jsonify({"error": "Message vide"}), 400
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
    return jsonify({"message": security.set_armed(bool(data.get("armed", True))),
                    "armed": security.armed})


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
                  meta={"params": entry["params"]})
    return jsonify({"ok": True, "action": entry["action"], "result": result})


@app.route("/api/approvals/reject", methods=["POST"])
def approvals_reject():
    body = request.get_json(silent=True) or {}
    ok = permission_manager.reject(body.get("approval_id", ""))
    if ok:
        event_log.add("approbation", "Action refusée par l'utilisateur.")
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
        "tools": len(tool_registry.names()), "version": "5.2",
        "conversations": len(convo_store.data), "pouvoirs": 48,
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
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',system-ui,sans-serif;background:radial-gradient(1000px 500px at 70% -10%,#10204020,transparent),linear-gradient(180deg,#0a0e1a,#05070d);
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

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JARVIS v5.0 — MÉGA</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
/* ── Design system (UI/UX Pro Max : Dark OLED + glow, Inter, glassmorphism) ── */
:root{
  --bg:#05070d; --bg-2:#0a0e1a;
  --surface:rgba(255,255,255,.045); --surface-2:rgba(255,255,255,.07);
  --border:rgba(255,255,255,.09); --border-strong:rgba(255,255,255,.16);
  --fg:#EDEDEF; --muted:#8A8F98; --muted-2:#5b6472;
  --accent:#38bdf8; --accent-2:#5E6AD2; --accent-glow:rgba(56,189,248,.22);
  --green:#22c55e; --red:#ef4444; --amber:#f59e0b; --purple:#a855f7;
  --radius:16px; --radius-sm:10px; --radius-pill:999px;
  --ease:cubic-bezier(.16,1,.3,1);
  --shadow:0 8px 30px rgba(0,0,0,.45);
  --font:'Inter',system-ui,sans-serif; --mono:'JetBrains Mono',ui-monospace,monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{
  background:radial-gradient(1200px 600px at 80% -10%, #10204010, transparent),
             linear-gradient(180deg,var(--bg-2),var(--bg) 60%);
  color:var(--fg); font-family:var(--font); min-height:100vh; min-height:100dvh;
  -webkit-font-smoothing:antialiased; line-height:1.5; overflow-x:hidden;
}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums}

/* Ambient blobs */
.blob{position:fixed;border-radius:50%;filter:blur(70px);opacity:.10;z-index:0;pointer-events:none;animation:drift 22s var(--ease) infinite alternate}
.blob.a{width:420px;height:420px;background:var(--accent);top:-120px;left:-100px}
.blob.b{width:380px;height:380px;background:var(--accent-2);bottom:-120px;right:-80px;animation-delay:-8s}
@keyframes drift{from{transform:translate(0,0)}to{transform:translate(60px,40px)}}

/* Header */
header{
  position:sticky;top:0;z-index:50;display:flex;align-items:center;gap:14px;
  padding:14px 20px;background:rgba(8,12,22,.72);backdrop-filter:blur(16px);
  border-bottom:1px solid var(--border);
}
.orb{width:30px;height:30px;border-radius:50%;flex:none;
  background:radial-gradient(circle at 35% 30%,#9fe6ff,var(--accent) 45%,#1f6f9c);
  box-shadow:0 0 18px var(--accent-glow);animation:breathe 3s var(--ease) infinite}
@keyframes breathe{0%,100%{box-shadow:0 0 14px var(--accent-glow);transform:scale(1)}50%{box-shadow:0 0 28px var(--accent-glow);transform:scale(1.07)}}
.orb.listening{background:radial-gradient(circle at 35% 30%,#c4ffd6,var(--green) 45%,#147a3e);box-shadow:0 0 26px rgba(34,197,94,.5);animation-duration:1s}
.wordmark{font-weight:700;letter-spacing:5px;font-size:1.15rem;text-shadow:0 0 14px var(--accent-glow)}
.pill{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:var(--radius-pill);
  font-size:.7rem;font-weight:500;letter-spacing:.5px;border:1px solid var(--border);background:var(--surface);color:var(--muted)}
.pill.v{color:var(--accent);border-color:var(--accent-glow)}
.pill.online{color:var(--green)} .pill.online .dot{background:var(--green);box-shadow:0 0 8px var(--green)}
.pill.armed{color:var(--red);border-color:var(--red);background:rgba(239,68,68,.1)}
.dot{width:7px;height:7px;border-radius:50%;background:var(--muted);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
.header-right{margin-left:auto;display:flex;gap:10px;align-items:center}
.clock{color:var(--muted);font-size:.8rem}

/* Layout */
.main{position:relative;z-index:1;display:grid;grid-template-columns:1fr;gap:16px;padding:16px;max-width:1440px;margin:0 auto}
@media(min-width:920px){.main{grid-template-columns:1fr 1fr}.span-2{grid-column:1 / -1}}

.panel{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  display:flex;flex-direction:column;overflow:hidden;box-shadow:var(--shadow);
  backdrop-filter:blur(8px);animation:rise .5s var(--ease) both}
@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.panel-head{display:flex;align-items:center;gap:10px;padding:13px 16px;border-bottom:1px solid var(--border);
  font-size:.72rem;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted)}
.panel-head svg{color:var(--accent)}
.panel-head .meta{margin-left:auto;color:var(--muted-2);font-weight:400;letter-spacing:.5px;text-transform:none}

/* Buttons */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:7px;cursor:pointer;
  font-family:var(--font);font-size:.8rem;font-weight:500;letter-spacing:.3px;
  padding:9px 14px;border-radius:var(--radius-sm);border:1px solid var(--border);
  background:var(--surface-2);color:var(--fg);transition:all .18s var(--ease)}
.btn svg{width:17px;height:17px}
.btn:hover{border-color:var(--accent);color:var(--accent);box-shadow:0 0 0 3px var(--accent-glow)}
.btn:active{transform:scale(.97)}
.btn:focus-visible{outline:none;box-shadow:0 0 0 3px var(--accent-glow);border-color:var(--accent)}
.btn.primary{background:linear-gradient(180deg,#3fc4ff,#1f93cc);color:#001018;border-color:transparent;font-weight:600}
.btn.primary:hover{box-shadow:0 0 18px var(--accent-glow);color:#001018}
.btn.green{color:var(--green);border-color:rgba(34,197,94,.35)} .btn.green:hover{box-shadow:0 0 0 3px rgba(34,197,94,.2);border-color:var(--green)}
.btn.danger{color:var(--red);border-color:rgba(239,68,68,.4)} .btn.danger:hover{box-shadow:0 0 0 3px rgba(239,68,68,.22);border-color:var(--red)}
.btn.armed{background:rgba(239,68,68,.16);color:var(--red);border-color:var(--red)}
.btn.icon{padding:9px;width:38px;height:38px}
.btn.active{border-color:var(--green);color:var(--green);box-shadow:0 0 0 3px rgba(34,197,94,.2)}
.btn.sm{padding:5px 9px;font-size:.72rem}

/* Chat */
#chat-box{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px;min-height:330px;max-height:46vh}
.msg{max-width:86%;padding:10px 13px;border-radius:14px;font-size:.88rem;line-height:1.6;animation:rise .35s var(--ease) both}
.msg.user{align-self:flex-end;background:linear-gradient(180deg,#16344a,#0f2536);border:1px solid var(--accent-glow);color:#eaf7ff;border-bottom-right-radius:4px}
.msg.jarvis{align-self:flex-start;background:var(--surface-2);border:1px solid var(--border);color:var(--fg);white-space:pre-wrap;border-bottom-left-radius:4px}
.msg.jarvis strong{color:var(--accent);font-weight:600}
.msg.jarvis code{font-family:var(--mono);background:rgba(0,0,0,.35);padding:1px 5px;border-radius:5px;font-size:.82rem;color:#9fe6ff}
.msg.loading{color:var(--muted);font-style:italic}
.typing span{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--muted);margin:0 1px;animation:blink 1.2s infinite both}
.typing span:nth-child(2){animation-delay:.2s}.typing span:nth-child(3){animation-delay:.4s}
@keyframes blink{0%,80%,100%{opacity:.2}40%{opacity:1}}
.chat-input-row{display:flex;gap:8px;padding:12px;border-top:1px solid var(--border);align-items:center}
#chat-input{flex:1;background:var(--bg);border:1px solid var(--border);color:var(--fg);
  padding:11px 14px;border-radius:var(--radius-sm);font-family:var(--font);font-size:.88rem;min-height:44px}
#chat-input:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-glow)}
.mic-on{background:rgba(34,197,94,.16)!important;color:var(--green)!important;border-color:var(--green)!important;animation:pulse 1s infinite}

/* Powers grid */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(96px,1fr));gap:8px;padding:14px}
.tile-btn{display:flex;flex-direction:column;align-items:center;gap:7px;padding:14px 6px;cursor:pointer;
  background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-sm);
  color:var(--muted);transition:all .18s var(--ease);text-align:center}
.tile-btn svg{width:22px;height:22px;color:var(--accent)}
.tile-btn:hover{border-color:var(--accent);color:var(--fg);transform:translateY(-2px);box-shadow:0 0 0 3px var(--accent-glow)}
.tile-btn:focus-visible{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-glow)}
.tile-btn span{font-size:.7rem;font-weight:500;letter-spacing:.4px}
#info-output{padding:12px 14px;font-family:var(--mono);font-size:.76rem;color:#9fe6ff;
  white-space:pre-wrap;max-height:170px;overflow:auto;border-top:1px solid var(--border);min-height:60px}

/* Home */
.scene-row{display:flex;gap:8px;flex-wrap:wrap;padding:14px;border-bottom:1px solid var(--border)}
.chip{display:inline-flex;align-items:center;gap:6px;padding:8px 14px;border-radius:var(--radius-pill);cursor:pointer;
  background:var(--surface-2);border:1px solid var(--border);color:var(--fg);font-size:.78rem;font-weight:500;transition:all .18s var(--ease)}
.chip svg{width:15px;height:15px;color:var(--purple)}
.chip:hover{border-color:var(--purple);box-shadow:0 0 0 3px rgba(168,85,247,.18)}
.chip:focus-visible{outline:none;box-shadow:0 0 0 3px rgba(168,85,247,.25)}
.lights{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;padding:14px}
.lcard{background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-sm);padding:12px}
.lcard .lh{display:flex;align-items:center;gap:8px;margin-bottom:10px;font-size:.82rem;font-weight:500}
.lcard .lh svg{width:18px;height:18px;color:var(--amber)}
.lcard .lh .st{margin-left:auto;width:9px;height:9px;border-radius:50%;background:var(--muted-2)}
.lcard .lh .st.on{background:var(--green);box-shadow:0 0 8px var(--green)}
.lrow{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.swatch{width:20px;height:20px;border-radius:50%;cursor:pointer;border:2px solid rgba(255,255,255,.15);transition:transform .15s var(--ease)}
.swatch:hover{transform:scale(1.18)}.swatch:focus-visible{outline:none;transform:scale(1.18);box-shadow:0 0 0 3px var(--accent-glow)}

/* Camera */
#camera-wrap{position:relative;background:#000}
#camera-feed{width:100%;max-height:300px;object-fit:cover;display:block}
.cam-tag{position:absolute;top:10px;left:10px;display:flex;gap:6px;align-items:center;font-family:var(--mono);font-size:.66rem;
  background:rgba(0,0,0,.5);padding:4px 8px;border-radius:var(--radius-pill);color:var(--green)}
.cam-tag .rec{width:7px;height:7px;border-radius:50%;background:var(--red);animation:pulse 1.4s infinite}
.cam-bar{display:flex;gap:8px;padding:12px;border-top:1px solid var(--border);flex-wrap:wrap}
.legend{display:flex;gap:10px;flex-wrap:wrap;padding:0 14px 12px;font-size:.68rem;color:var(--muted-2)}
.legend i{font-style:normal;color:var(--muted)}

/* Alerts */
.alerts{flex:1;overflow-y:auto;max-height:42vh;padding:10px;display:flex;flex-direction:column;gap:8px}
.alert{border:1px solid var(--border);border-left:3px solid var(--amber);border-radius:var(--radius-sm);padding:10px 12px;background:var(--surface-2);animation:rise .3s var(--ease) both}
.alert.high{border-left-color:var(--red)}.alert.extreme{border-left-color:var(--red);background:rgba(239,68,68,.08);box-shadow:0 0 0 1px rgba(239,68,68,.25)}
.alert .at{font-family:var(--mono);font-size:.68rem;color:var(--muted)}
.alert .ev{font-weight:600;font-size:.82rem;margin:3px 0;color:var(--fg)}
.badge{display:inline-block;padding:1px 8px;border-radius:var(--radius-pill);font-size:.64rem;font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.badge.bas{background:rgba(34,197,94,.15);color:var(--green)}
.badge.moyen{background:rgba(245,158,11,.15);color:var(--amber)}
.badge.eleve,.badge.extreme{background:rgba(239,68,68,.16);color:var(--red)}
.fb{display:flex;gap:6px;margin-top:8px}
.empty{color:var(--muted-2);text-align:center;padding:26px 14px;font-size:.82rem}
.skeleton{height:54px;border-radius:var(--radius-sm);background:linear-gradient(90deg,var(--surface-2),rgba(255,255,255,.1),var(--surface-2));background-size:200% 100%;animation:shimmer 1.4s infinite}
@keyframes shimmer{from{background-position:200% 0}to{background-position:-200% 0}}

/* Learning strip */
.learn{display:flex;gap:18px;flex-wrap:wrap;padding:14px}
.stat{display:flex;flex-direction:column;gap:2px}
.stat b{font-family:var(--mono);font-size:1.3rem;color:var(--accent)}
.stat span{font-size:.68rem;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}

/* Toast + modal */
#toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%) translateY(20px);z-index:200;
  background:rgba(10,16,28,.95);border:1px solid var(--accent);color:var(--fg);padding:12px 18px;border-radius:var(--radius-pill);
  box-shadow:0 0 24px var(--accent-glow);font-size:.85rem;opacity:0;pointer-events:none;transition:all .35s var(--ease)}
#toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
.scrim{position:fixed;inset:0;background:rgba(0,0,0,.55);backdrop-filter:blur(4px);z-index:150;display:none;align-items:center;justify-content:center;padding:20px}
.scrim.show{display:flex}
.modal{background:var(--bg-2);border:1px solid var(--border-strong);border-radius:var(--radius);max-width:440px;width:100%;padding:22px;box-shadow:var(--shadow);animation:rise .3s var(--ease)}
.modal h3{display:flex;align-items:center;gap:9px;font-size:1rem;margin-bottom:10px}
.modal h3 svg{color:var(--red)}
.modal p{color:var(--muted);font-size:.86rem;margin-bottom:18px;line-height:1.6}
.modal .actions{display:flex;gap:10px;justify-content:flex-end}

#ask-banner{position:relative;z-index:2;margin:12px 16px -4px;display:flex;flex-direction:column;gap:8px}
.ask{display:flex;align-items:center;gap:12px;flex-wrap:wrap;background:linear-gradient(90deg,rgba(245,158,11,.14),var(--surface));
  border:1px solid var(--amber);border-radius:var(--radius);padding:12px 16px;animation:rise .35s var(--ease)}
.ask .q{flex:1;min-width:200px;font-size:.86rem}
.ask .q b{color:var(--amber)}
.ask input{background:var(--bg);border:1px solid var(--border);color:var(--fg);padding:8px 10px;border-radius:8px;font-family:var(--font);font-size:.8rem;max-width:150px}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--border-strong);border-radius:3px}

@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
</head>
<body>
<div class="blob a"></div><div class="blob b"></div>

<header>
  <div class="orb" id="orb"></div>
  <div class="wordmark">JARVIS</div>
  <span class="pill v">v5.0 MÉGA</span>
  <span class="pill mono" id="backend-pill">{{ backend.upper() }}</span>
  <div class="header-right">
    <span class="pill online"><span class="dot"></span>ONLINE</span>
    <span class="pill armed" id="armed-pill" style="display:none"><span class="dot"></span>ARMÉ</span>
    <span class="pill" id="standby-pill" style="display:none">😴 VEILLE</span>
    <span class="clock mono" id="clock"></span>
    <button class="btn icon" id="standby-btn" title="Couper / réveiller JARVIS" aria-label="Veille" onclick="toggleStandby()">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v8M6 6a8 8 0 1012 0"/></svg>
    </button>
    <button class="btn icon danger" title="Éteindre JARVIS" aria-label="Éteindre" onclick="shutdown()">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5"/></svg>
    </button>
    <button class="btn icon" title="Effacer la mémoire de conversation" aria-label="Effacer la mémoire" onclick="clearMemory()">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m-9 0v14a2 2 0 002 2h6a2 2 0 002-2V6"/></svg>
    </button>
    <button class="btn icon" title="Se déconnecter" aria-label="Déconnexion" onclick="location.href='/logout'">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/></svg>
    </button>
  </div>
</header>

<div id="ask-banner" style="display:none"></div>

<div class="main">

  <!-- ASSISTANT -->
  <section class="panel" aria-label="Assistant IA">
    <div class="panel-head">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a5 5 0 015 5v2a5 5 0 01-10 0V7a5 5 0 015-5z"/><path d="M19 11a7 7 0 01-14 0M12 18v4"/></svg>
      Assistant
      <span class="meta mono">{{ model }}</span>
    </div>
    <div id="chat-box"></div>
    <div class="chat-input-row">
      <button class="btn icon" id="wake-btn" title="Veille vocale (Ok Jarvis / double clap)" aria-label="Veille vocale" onclick="toggleWake()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 8.5a6 6 0 0112 0c0 7-3 4-3 8a3 3 0 01-6 0"/><path d="M6 8.5C4 9 3 11 3 13"/></svg>
      </button>
      <button class="btn icon" id="mic-btn" title="Parler (push-to-talk)" aria-label="Micro" onclick="pushToTalk()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10a7 7 0 0014 0M12 17v4"/></svg>
      </button>
      <button class="btn icon" id="tts-btn" title="Lecture vocale des réponses" aria-label="Lecture vocale" onclick="toggleTTS()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M16 9a3 3 0 010 6" opacity=".4"/></svg>
      </button>
      <input id="chat-input" type="text" placeholder="Parlez ou écrivez… « cherche les news », « mode cinéma »" onkeydown="if(event.key==='Enter')send()" aria-label="Message">
      <button class="btn primary" onclick="send()" aria-label="Envoyer">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>
      </button>
    </div>
  </section>

  <!-- POUVOIRS -->
  <section class="panel" aria-label="Super pouvoirs">
    <div class="panel-head">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h8l-1 8 10-12h-8l1-8z"/></svg>
      Super pouvoirs
    </div>
    <div class="grid" id="powers"></div>
    <div id="info-output">▸ Sélectionnez un pouvoir…</div>
  </section>

  <!-- MAISON -->
  <section class="panel span-2" aria-label="Maison connectée">
    <div class="panel-head">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 11l9-8 9 8M5 9v11a1 1 0 001 1h12a1 1 0 001-1V9"/></svg>
      Maison connectée
      <span class="meta" id="lights-mode"></span>
    </div>
    <div class="scene-row" id="scenes"></div>
    <div class="lights" id="lights"></div>
  </section>

  <!-- CONTRÔLE PC -->
  <section class="panel span-2" aria-label="Contrôle PC">
    <div class="panel-head">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></svg>
      Contrôle PC
      <span class="meta" id="pc-meta"></span>
    </div>
    <div class="grid" id="pc-grid">
      <div class="tile-btn" tabindex="0" role="button" onclick="pcShot()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"/><circle cx="12" cy="13" r="4"/></svg><span>Capture écran</span></div>
      <div class="tile-btn" tabindex="0" role="button" onclick="pcMedia('play')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 4h4v16H6zM14 4h4v16h-4z"/></svg><span>Play/Pause</span></div>
      <div class="tile-btn" tabindex="0" role="button" onclick="pcMedia('next')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 4l10 8-10 8zM19 5v14"/></svg><span>Suivant</span></div>
      <div class="tile-btn" tabindex="0" role="button" onclick="pcMedia('vol_up')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5L6 9H2v6h4l5 4zM19 9a5 5 0 010 6"/></svg><span>Volume +</span></div>
      <div class="tile-btn" tabindex="0" role="button" onclick="pcMedia('mute')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 5L6 9H2v6h4l5 4zM23 9l-6 6M17 9l6 6"/></svg><span>Muet</span></div>
      <div class="tile-btn" tabindex="0" role="button" onclick="pcLock()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg><span>Verrouiller</span></div>
      <div class="tile-btn" tabindex="0" role="button" onclick="pcVision()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg><span>Analyser écran</span></div>
      <div class="tile-btn" tabindex="0" role="button" onclick="pcPower('sleep')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.8A9 9 0 1111.2 3 7 7 0 0021 12.8z"/></svg><span>Veille PC</span></div>
      <div class="tile-btn" tabindex="0" role="button" onclick="pcPower('shutdown')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v10"/><path d="M5.6 5.6a9 9 0 1012.8 0"/></svg><span>Éteindre PC</span></div>
    </div>
  </section>

  <!-- CAMERA -->
  <section class="panel" aria-label="Caméra de sécurité">
    <div class="panel-head">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg>
      Sécurité — détection d'intrus
    </div>
    <div id="camera-wrap">
      <img id="camera-feed" src="/api/security/stream" alt="Flux caméra de sécurité en direct"
           onerror="this.style.display='none';document.getElementById('no-cam').style.display='flex'">
      <div class="cam-tag"><span class="rec"></span>LIVE</div>
      <div id="no-cam" style="display:none;align-items:center;justify-content:center;color:var(--muted);font-size:.85rem;padding:30px;text-align:center">
        Caméra non disponible — vérifiez camera_index dans la config.
      </div>
    </div>
    <div class="cam-bar">
      <button class="btn armed" id="arm-btn" onclick="toggleArm()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6l8-4z"/></svg>
        <span>Armer</span>
      </button>
      <button class="btn" onclick="enrollFace()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6M22 11h-6"/></svg>
        Visage sûr
      </button>
      <button class="btn" onclick="analyzeCamera()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
        Analyser
      </button>
      <button class="btn" onclick="callOwner()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.9v3a2 2 0 01-2.2 2 19.8 19.8 0 01-8.6-3.1 19.5 19.5 0 01-6-6A19.8 19.8 0 012.1 4.2 2 2 0 014.1 2h3a2 2 0 012 1.7c.1 1 .4 1.9.7 2.8a2 2 0 01-.5 2.1L8.1 9.9a16 16 0 006 6l1.3-1.3a2 2 0 012.1-.5c.9.3 1.8.6 2.8.7a2 2 0 011.7 2z"/></svg>
        Appeler l'hôte
      </button>
      <button class="btn danger" onclick="openEmergency()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.3 3.5l-8 14A1.5 1.5 0 003.7 20h16.6a1.5 1.5 0 001.3-2.5l-8-14a1.5 1.5 0 00-2.6 0z"/><path d="M12 9v4M12 17h.01"/></svg>
        Urgence
      </button>
    </div>
    <div class="legend">
      <span><i style="color:var(--amber)">●</i> mouvement</span>
      <span><i style="color:#ff8c2b">●</i> personne (HOG)</span>
      <span><i style="color:var(--red)">●</i> visage inconnu</span>
      <span><i style="color:var(--green)">●</i> visage connu</span>
      <span><i style="color:var(--red)">!!</i> comportement suspect (rôdage…)</span>
    </div>
  </section>

  <!-- ALERTES -->
  <section class="panel" aria-label="Alertes de sécurité">
    <div class="panel-head">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.3 3.5l-8 14A1.5 1.5 0 003.7 20h16.6a1.5 1.5 0 001.3-2.5l-8-14a1.5 1.5 0 00-2.6 0z"/><path d="M12 9v4M12 17h.01"/></svg>
      Alertes
      <span class="meta" id="alert-count"></span>
    </div>
    <div class="alerts" id="alerts" aria-live="polite"><div class="skeleton"></div><div class="skeleton"></div></div>
  </section>

  <!-- APPRENTISSAGE -->
  <section class="panel span-2" aria-label="Apprentissage">
    <div class="panel-head">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a4 4 0 00-4 4 4 4 0 00-2 7 4 4 0 003 6 3 3 0 003 1 3 3 0 003-1 4 4 0 003-6 4 4 0 00-2-7 4 4 0 00-4-4z"/></svg>
      Apprentissage — JARVIS s'adapte à vous
    </div>
    <div class="learn" id="learn"><div class="stat"><b>—</b><span>chargement…</span></div></div>
  </section>

  <!-- TIMELINE -->
  <section class="panel span-2" aria-label="Timeline des évènements">
    <div class="panel-head">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
      Timeline — tout ce que JARVIS fait et voit
      <span class="meta" id="rt-pill">● temps réel</span>
    </div>
    <div class="alerts" id="timeline" aria-live="polite" style="max-height:34vh"><div class="skeleton"></div></div>
  </section>

</div>

<div id="toast"></div>
<div class="scrim" id="emergency-scrim">
  <div class="modal" role="dialog" aria-modal="true" aria-labelledby="em-title">
    <h3 id="em-title"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.3 3.5l-8 14A1.5 1.5 0 003.7 20h16.6a1.5 1.5 0 001.3-2.5l-8-14a1.5 1.5 0 00-2.6 0z"/><path d="M12 9v4M12 17h.01"/></svg>Protocole d'urgence</h3>
    <p>Cela va prévenir ton contact d'urgence (notification + SMS + appel vocal si configuré) et diffuser une annonce dissuasive. À n'utiliser qu'en cas de danger réel — un appel abusif aux secours est illégal.</p>
    <input id="em-reason" class="" type="text" placeholder="Raison (ex: intrusion confirmée)" style="width:100%;background:var(--bg);border:1px solid var(--border);color:var(--fg);padding:10px;border-radius:10px;margin-bottom:16px;font-family:var(--font)">
    <div class="actions">
      <button class="btn" onclick="closeEmergency()">Annuler</button>
      <button class="btn danger" onclick="confirmEmergency()">Déclencher l'urgence</button>
    </div>
  </div>
</div>

<script>
// ── Icônes (Lucide-style) pour les boutons de pouvoirs ──
const ICONS={
  pc:'<path d="M2 4h20v12H2zM8 20h8M12 16v4"/>',
  cloud:'<path d="M17 18a4 4 0 000-8 6 6 0 00-11.3 2A3.5 3.5 0 006 18z"/>',
  joke:'<circle cx="12" cy="12" r="9"/><path d="M8 14s1.5 2 4 2 4-2 4-2M9 9h.01M15 9h.01"/>',
  net:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 010 18M12 3a14 14 0 000 18"/>',
  cpu:'<rect x="6" y="6" width="12" height="12" rx="1"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
  disk:'<path d="M22 12A10 10 0 1112 2v10z"/>',
  key:'<circle cx="8" cy="15" r="4"/><path d="M10.8 12.2L20 3M17 6l2 2M14 9l2 2"/>',
  search:'<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
  speaker:'<rect x="6" y="3" width="12" height="18" rx="3"/><circle cx="12" cy="14" r="3"/><path d="M12 7h.01"/>',
  tv:'<rect x="2" y="7" width="20" height="13" rx="2"/><path d="M7 3l5 4 5-4"/>',
  home:'<path d="M3 11l9-8 9 8M5 9v11a1 1 0 001 1h12a1 1 0 001-1V9"/>',
  cam:'<path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2"/>',
};
const POWERS=[
  ['pc','PC Info',"q:info"],['cloud','Météo',"weather"],['joke','Blague',"q:blague"],
  ['net','Réseau',"q:reseau"],['cpu','Processus',"q:processus"],['disk','Disques',"q:disque"],
  ['key','Mot de passe',"q:motdepasse"],['search','Recherche web',"web"],
  ['speaker','Parler HomePod',"say"],['tv','TV Play/Pause',"tv:play_pause"],
  ['home','TV Accueil',"tv:home"],['cam','Analyser cam',"analyze"],
];
function svg(p){return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'+p+'</svg>'}
(function(){
  document.getElementById('powers').innerHTML=POWERS.map(([ic,label,act])=>
    '<div class="tile-btn" tabindex="0" role="button" onclick="power(\''+act+'\')" onkeydown="if(event.key===\'Enter\')power(\''+act+'\')">'+svg(ICONS[ic])+'<span>'+label+'</span></div>').join('');
})();
function power(act){
  if(act.startsWith('q:'))return quickAction(act.slice(2));
  if(act.startsWith('tv:'))return appletv(act.slice(3));
  if(act==='weather')return askWeather();
  if(act==='web')return webSearch();
  if(act==='say')return appleSay();
  if(act==='analyze')return analyzeCamera();
}

// ── Horloge ──
setInterval(()=>{document.getElementById('clock').textContent=new Date().toLocaleTimeString('fr-FR')},1000);

// ── Toast ──
let toastT;function toast(m){const t=document.getElementById('toast');t.textContent=m;t.classList.add('show');clearTimeout(toastT);toastT=setTimeout(()=>t.classList.remove('show'),3200)}

// ── Chat ──
function send(){const i=document.getElementById('chat-input');const m=i.value.trim();if(!m)return;i.value='';chatSend(m)}
async function chatSend(msg){
  addMsg('user',msg);
  const loader=addMsg('jarvis','<span class="typing"><span></span><span></span><span></span></span>',true);
  try{
    const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
    const d=await r.json();loader.innerHTML=mdToHtml(d.response);speak(d.response);
  }catch(e){loader.textContent='⚠️ Erreur de connexion'}
  document.getElementById('chat-box').scrollTop=9999;loadLights();loadLearn();
}
function mdToHtml(t){return t.replace(/\\*\\*(.+?)\\*\\*/g,'<strong>$1</strong>').replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\\n/g,'<br>')}
function addMsg(role,html,ret){const b=document.getElementById('chat-box');const d=document.createElement('div');d.className='msg '+role;d.innerHTML=html;b.appendChild(d);b.scrollTop=9999;return ret?d:null}

// ── Quick actions ──
async function quickAction(a){const o=document.getElementById('info-output');o.textContent='⏳ '+a.toUpperCase()+'…';
  try{const r=await fetch('/api/quick/'+a);o.textContent=JSON.stringify(await r.json(),null,2)}catch(e){o.textContent='⚠️ '+e}}
function askWeather(){const c=prompt('Quelle ville ?','Paris');if(c)quickAction('meteo?city='+encodeURIComponent(c))}
async function webSearch(){const q=prompt('Chercher sur le web :');if(q)chatSend('Cherche sur le web : '+q+' [RECHERCHE_WEB:'+q+']')}
async function appleSay(){const t=prompt('Que doit dire JARVIS sur le HomePod ?','Bonjour, je suis JARVIS.');if(!t)return;
  const r=await fetch('/api/apple/say',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});document.getElementById('info-output').textContent=(await r.json()).message}
async function appletv(cmd){const r=await fetch('/api/apple/appletv/'+cmd,{method:'POST'});document.getElementById('info-output').textContent=(await r.json()).message}

// ── Lumières / scènes ──
const CMAP={rouge:'#ff3b3b',vert:'#3bff6b',bleu:'#3b7bff',jaune:'#ffe23b',orange:'#ff9b3b',rose:'#ff7bce',violet:'#9b3bff',blanc:'#ffffff',chaud:'#ffd9a0'};
async function loadLights(){
  try{const d=await(await fetch('/api/home/lights')).json();
  document.getElementById('lights-mode').textContent='mode '+(window.__lmode||'');
  const g=document.getElementById('lights');g.innerHTML='';
  for(const[name,st]of Object.entries(d)){
    if(name==='erreur'){g.innerHTML='<div class="empty">'+st+'</div>';return}
    const on=st.on;const card=document.createElement('div');card.className='lcard';
    card.innerHTML='<div class="lh">'+svg(ICONS.home).replace('home','')+
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18h6M10 21h4M12 3a6 6 0 00-4 10c.6.6 1 1.3 1 2h6c0-.7.4-1.4 1-2a6 6 0 00-4-10z"/></svg>'+
      name+'<span class="st '+(on?'on':'')+'"></span></div>'+
      '<div class="lrow" style="margin-bottom:8px"><button class="btn green sm" onclick="setLight(\''+name+'\',true)">On</button><button class="btn sm" onclick="setLight(\''+name+'\',false)">Off</button></div>'+
      '<div class="lrow">'+Object.keys(CMAP).map(c=>'<span class="swatch" tabindex="0" role="button" aria-label="'+c+'" title="'+c+'" style="background:'+CMAP[c]+'" onclick="setColor(\''+name+'\',\''+c+'\')" onkeydown="if(event.key===\'Enter\')setColor(\''+name+'\',\''+c+'\')"></span>').join('')+'</div>';
    g.appendChild(card);
  }}catch(e){}
}
async function setLight(n,on){await fetch('/api/home/light',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n,on})});loadLights()}
async function setColor(n,c){await fetch('/api/home/light',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n,color:c})});loadLights()}
async function loadScenes(){const d=await(await fetch('/api/home/scenes')).json();
  document.getElementById('scenes').innerHTML=d.scenes.map(s=>'<button class="chip" onclick="runScene(\''+s+'\')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16v12H4z"/><path d="M2 20h20"/></svg>'+s+'</button>').join('')}
async function runScene(n){toast('Scène « '+n+' »');const r=await fetch('/api/home/scene',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n})});addMsg('jarvis',mdToHtml((await r.json()).message));loadLights();loadAlerts()}

// ── Sécurité ──
let armed=false;
async function toggleArm(){const r=await fetch('/api/security/arm',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({armed:!armed})});armed=(await r.json()).armed;armUI();toast(armed?'🛡️ Alarme armée':'🔓 Alarme désarmée')}
function armUI(){const b=document.getElementById('arm-btn');b.querySelector('span').textContent=armed?'Désarmer':'Armer';b.className=armed?'btn':'btn armed';document.getElementById('armed-pill').style.display=armed?'inline-flex':'none'}
async function enrollFace(){const n=prompt('Nom de la personne de confiance ?');if(!n)return;
  const d=await(await fetch('/api/security/enroll',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n})})).json();toast(d.message||d.error)}
async function analyzeCamera(){await fetch('/api/security/snapshot');chatSend('Analyse la caméra de sécurité [CAMERA_ANALYSE]')}
async function loadAlerts(){
  const d=await(await fetch('/api/security/alerts')).json();armed=d.armed;armUI();window.__stats=d.stats;
  const box=document.getElementById('alerts');document.getElementById('alert-count').textContent=d.alerts.length?d.alerts.length+' évènement(s)':'';
  if(!d.alerts.length){box.innerHTML='<div class="empty">Aucune alerte. Tout est calme. 🕵️</div>';return}
  box.innerHTML=d.alerts.map(a=>{const cl=a.threat==='extrême'?'extreme':(a.threat==='élevé'?'high':'');const bc=a.threat==='extrême'?'extreme':(a.threat==='élevé'?'eleve':a.threat);
    return '<div class="alert '+cl+'"><div class="at">'+new Date(a.timestamp).toLocaleString('fr-FR')+(a.armed?' · 🔴 armé':'')+'</div>'+
    '<div class="ev">'+a.event+' <span class="badge '+bc+'">'+a.threat+'</span></div>'+
    '<div class="fb"><button class="btn sm" onclick="feedback(true,this)">Fausse alerte</button><button class="btn sm green" onclick="feedback(false,this)">Réelle</button></div></div>'}).join('')
}
async function feedback(isFalse,el){const d=await(await fetch('/api/security/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({false:isFalse})})).json();toast(d.message);el.closest('.fb').innerHTML='<span style="font-size:.72rem;color:var(--muted)">Merci, JARVIS apprend.</span>'}

// ── Apprentissage ──
async function loadLearn(){const s=await(await fetch('/api/learning/profile')).json();
  const top=s.top_commands&&s.top_commands.length?s.top_commands[0][0]:'—';
  document.getElementById('learn').innerHTML=
    '<div class="stat"><b>'+s.interactions+'</b><span>interactions</span></div>'+
    '<div class="stat"><b>'+s.confirmed_alarms+'</b><span>alertes réelles</span></div>'+
    '<div class="stat"><b>'+s.false_alarms+'</b><span>fausses alertes</span></div>'+
    '<div class="stat"><b>+'+s.sensitivity_adj+'</b><span>auto-ajustement</span></div>'+
    '<div class="stat"><b style="font-size:.9rem">'+(s.facts.length?s.facts.length+' fait(s)':'aucun')+'</b><span>mémoire perso</span></div>';
}

// ── Urgence ──
function openEmergency(){document.getElementById('emergency-scrim').classList.add('show');document.getElementById('em-reason').focus()}
function closeEmergency(){document.getElementById('emergency-scrim').classList.remove('show')}
async function confirmEmergency(){const reason=document.getElementById('em-reason').value.trim()||'Urgence déclenchée manuellement';
  closeEmergency();toast('🆘 Protocole d\\'urgence déclenché');
  const d=await(await fetch('/api/emergency/police',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reason,confirm:true})})).json();
  addMsg('jarvis','🆘 <strong>Urgence</strong><br>'+(d.actions||[]).map(a=>'• '+a).join('<br>'))}

// ── Mémoire ──
async function clearMemory(){if(!confirm('Effacer la mémoire de conversation ?'))return;await fetch('/api/memory/clear',{method:'POST'});document.getElementById('chat-box').innerHTML='';addMsg('jarvis',"Mémoire de conversation effacée. (Ton profil long terme, lui, reste — j'apprends quand même 😏)")}

// ── Contrôle PC ──
async function pcShot(){const o=document.getElementById('info-output');o.textContent='📸 Capture…';
  const d=await(await fetch('/api/pc/screenshot',{method:'POST'})).json();o.textContent=d.message;
  if(d.image){const w=window.open('');if(w)w.document.write('<img src="data:image/png;base64,'+d.image+'" style="max-width:100%">')}}
async function pcMedia(a){const d=await(await fetch('/api/pc/media/'+a,{method:'POST'})).json();toast(d.message)}
async function pcLock(){const d=await(await fetch('/api/pc/lock',{method:'POST'})).json();toast(d.message)}
async function pcPower(action){
  const destructive=['shutdown','restart','logoff'];
  let confirmFlag=false;
  if(destructive.includes(action)){if(!confirm('Confirmer : '+action+' du PC ?'))return;confirmFlag=true}
  const d=await(await fetch('/api/pc/power',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,confirm:confirmFlag})})).json();
  toast(d.message);addMsg('jarvis','⏻ '+d.message)}
async function pcVision(){const o=document.getElementById('info-output');o.textContent='👁️ Analyse de l\\'écran…';
  const d=await(await fetch('/api/vision/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:'screen'})})).json();
  o.textContent=d.message;addMsg('jarvis','👁️ '+d.message)}

// ── Timeline + flux temps réel (SSE) ──
const KIND_ICON={chat:'💬',scene:'🎬',security:'🛡️',intrusion:'🚨',outil:'🛠️',
  automation:'⚙️',proactif:'🌅',system:'⏻'};
function tlItem(ev){const t=new Date(ev.ts).toLocaleTimeString('fr-FR');
  const cls=ev.level==='alert'?'extreme':(ev.level==='warn'?'high':'');
  return '<div class="alert '+cls+'"><div class="at">'+t+'</div><div class="ev">'+
    (KIND_ICON[ev.kind]||'•')+' '+(ev.message||ev.kind)+'</div></div>'}
async function loadTimeline(){try{const d=await(await fetch('/api/timeline')).json();
  const box=document.getElementById('timeline');
  box.innerHTML=d.events.length?d.events.map(tlItem).join(''):'<div class="empty">Rien encore.</div>';
}catch(e){}}
function prependTimeline(ev){const box=document.getElementById('timeline');
  if(box.querySelector('.empty'))box.innerHTML='';
  box.insertAdjacentHTML('afterbegin',tlItem(ev));}
function startStream(){
  if(!window.EventSource)return;
  try{
    const es=new EventSource('/api/stream');
    const onEv=e=>{try{const ev=JSON.parse(e.data);if(!ev.kind)return;prependTimeline(ev);
      if(ev.kind==='intrusion'){toast('🚨 '+ev.message);loadAlerts();loadPending()}
      if(ev.kind==='security'||ev.kind==='scene'){loadLights()}}catch(_){}};
    ['chat','scene','security','intrusion','outil','automation','proactif','system'].forEach(k=>es.addEventListener(k,onEv));
    es.onopen=()=>{document.getElementById('rt-pill').textContent='● temps réel';document.getElementById('rt-pill').style.color='var(--green)'};
    es.onerror=()=>{document.getElementById('rt-pill').textContent='○ reconnexion…';document.getElementById('rt-pill').style.color='var(--muted)'};
  }catch(e){}
}

// ── Appel à l'hôte ──
async function callOwner(){const m=prompt("Message à dire à l'hôte ?","Vous avez une alerte à votre domicile.");if(m===null)return;
  const d=await(await fetch('/api/emergency/call-owner',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m})})).json();toast(d.message);addMsg('jarvis','📞 '+d.message)}

// ── Couper / réveiller / éteindre ──
let standby=false;
async function toggleStandby(){const d=await(await fetch('/api/system/standby',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({on:!standby})})).json();standby=d.standby;standbyUI();toast(d.message)}
function standbyUI(){document.getElementById('standby-pill').style.display=standby?'inline-flex':'none';document.getElementById('standby-btn').classList.toggle('active',!standby);document.getElementById('orb').style.filter=standby?'grayscale(1) opacity(.5)':''}
async function shutdown(){if(!confirm('Éteindre complètement JARVIS ? (il faudra le relancer manuellement)'))return;
  try{const d=await(await fetch('/api/system/shutdown',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirm:true})})).json();addMsg('jarvis','⏻ '+(d.message||d.error))}catch(e){}
  toast('⏻ JARVIS éteint');document.body.style.opacity=.4}

// ── Questions « connu / inconnu ? » ──
async function loadPending(){
  try{const d=await(await fetch('/api/security/pending')).json();const wrap=document.getElementById('ask-banner');
  if(!d.pending.length){wrap.style.display='none';wrap.innerHTML='';return}
  wrap.style.display='flex';
  wrap.innerHTML=d.pending.map(p=>'<div class="ask" data-id="'+p.id+'">'+
    '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--amber)" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0116 0"/></svg>'+
    '<div class="q"><b>Personne détectée</b> ('+p.event+', menace '+p.threat+'). Tu la connais ?</div>'+
    '<input placeholder="Son nom (si connu)" id="nm-'+p.id+'">'+
    '<button class="btn sm green" onclick="identify(\''+p.id+'\',true)">✅ Connu</button>'+
    '<button class="btn sm danger" onclick="identify(\''+p.id+'\',false)">🚨 Inconnu</button></div>').join('');
  }catch(e){}
}
async function identify(id,known){const name=known?(document.getElementById('nm-'+id)||{}).value||'':'';
  const d=await(await fetch('/api/security/identify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,known,name})})).json();
  toast(d.message);addMsg('jarvis',(known?'✅ ':'🚨 ')+d.message);loadPending();loadAlerts()}

// ── 🎙️ Voix : TTS + push-to-talk + veille (Ok Jarvis / double clap) ──
let ttsOn=false;
function toggleTTS(){ttsOn=!ttsOn;document.getElementById('tts-btn').classList.toggle('active',ttsOn);toast(ttsOn?'Lecture vocale activée':'Lecture vocale coupée');if(!ttsOn&&window.speechSynthesis)speechSynthesis.cancel()}
function speak(text){if(!ttsOn||!window.speechSynthesis)return;
  const clean=text.replace(/[*`_#>]/g,'').replace(/https?:\\/\\/\\S+/g,'').replace(/[\\u{1F000}-\\u{1FFFF}]/gu,'');
  const u=new SpeechSynthesisUtterance(clean);u.lang='fr-FR';u.rate=1.05;
  const fr=speechSynthesis.getVoices().find(v=>v.lang.startsWith('fr'));if(fr)u.voice=fr;
  speechSynthesis.cancel();speechSynthesis.speak(u)}

const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
function pushToTalk(){
  if(!SR){toast('Reconnaissance vocale non supportée (utilise Chrome/Edge)');return}
  const r=new SR();r.lang='fr-FR';r.interimResults=false;
  const mb=document.getElementById('mic-btn');mb.classList.add('mic-on');
  r.onend=()=>mb.classList.remove('mic-on');
  r.onerror=()=>mb.classList.remove('mic-on');
  r.onresult=e=>{const t=e.results[0][0].transcript.trim();chatSend(t)};
  r.start();
}

// Veille vocale : écoute continue d'un mot de réveil + double clap
let wakeOn=false,wakeRec=null,audioCtx=null,clapTimes=[];
const WAKE_PHRASES=['ok jarvis','okay jarvis','hey jarvis','jarvis réveille','jarvis reveille','jarvis papa est là','jarvis papa est la','jarvis tu es là','jarvis t es là'];
function setOrb(on){document.getElementById('orb').classList.toggle('listening',on)}
function wakeUp(trailing){
  setOrb(true);toast('🟢 JARVIS à l\\'écoute…');
  if(standby){fetch('/api/system/standby',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({on:false})});standby=false;standbyUI()}
  try{const a=new (window.AudioContext||window.webkitAudioContext)();const o=a.createOscillator();const g=a.createGain();
    o.connect(g);g.connect(a.destination);o.frequency.value=880;g.gain.value=.08;o.start();o.frequency.exponentialRampToValueAtTime(1320,a.currentTime+.12);o.stop(a.currentTime+.13)}catch(e){}
  setTimeout(()=>setOrb(false),1600);
  if(trailing&&trailing.length>2){chatSend(trailing)}
  else{captureCommand()}
}
function captureCommand(){ // capture la phrase suivante comme commande
  if(!SR)return;const r=new SR();r.lang='fr-FR';r.interimResults=false;
  document.getElementById('mic-btn').classList.add('mic-on');
  r.onend=()=>document.getElementById('mic-btn').classList.remove('mic-on');
  r.onresult=e=>{const t=e.results[0][0].transcript.trim();if(t)chatSend(t)};
  try{r.start()}catch(e){}
}
function startWakeRecognition(){
  if(!SR)return false;
  wakeRec=new SR();wakeRec.lang='fr-FR';wakeRec.continuous=true;wakeRec.interimResults=true;
  wakeRec.onresult=e=>{
    const res=e.results[e.results.length-1];if(!res.isFinal)return;
    const t=res[0].transcript.toLowerCase().trim();
    const hit=WAKE_PHRASES.find(p=>t.includes(p));
    if(hit){let trailing=t.split(hit).pop().replace(/^[\\s,.;:!?]+/,'');wakeUp(trailing)}
  };
  wakeRec.onend=()=>{if(wakeOn){try{wakeRec.start()}catch(e){}}}; // relance auto
  try{wakeRec.start();return true}catch(e){return false}
}
async function startClapDetection(){
  try{
    const stream=await navigator.mediaDevices.getUserMedia({audio:true});
    audioCtx=new (window.AudioContext||window.webkitAudioContext)();
    const src=audioCtx.createMediaStreamSource(stream);
    const an=audioCtx.createAnalyser();an.fftSize=512;src.connect(an);
    const data=new Uint8Array(an.frequencyBinCount);let cooldown=0;
    (function loop(){
      if(!wakeOn)return;an.getByteTimeDomainData(data);
      let peak=0;for(let i=0;i<data.length;i++){const v=Math.abs(data[i]-128);if(v>peak)peak=v}
      const now=Date.now();
      if(peak>92&&now-cooldown>180){ // pic sonore type clap
        cooldown=now;clapTimes.push(now);clapTimes=clapTimes.filter(x=>now-x<700);
        if(clapTimes.length>=2){clapTimes=[];wakeUp('')}
      }
      requestAnimationFrame(loop);
    })();
    return true;
  }catch(e){return false}
}
async function toggleWake(){
  wakeOn=!wakeOn;
  const b=document.getElementById('wake-btn');b.classList.toggle('active',wakeOn);
  if(wakeOn){
    const a=startWakeRecognition();const c=await startClapDetection();
    if(a||c){toast('👂 Veille activée — dis « Ok Jarvis » ou tape 2 fois dans tes mains');setOrb(false)}
    else{wakeOn=false;b.classList.remove('active');toast('Veille vocale non supportée par ce navigateur')}
  }else{
    if(wakeRec){try{wakeRec.stop()}catch(e){}}
    if(audioCtx){try{audioCtx.close()}catch(e){}audioCtx=null}
    toast('Veille vocale désactivée');
  }
}

// ── Init ──
(async function(){
  try{const st=await(await fetch('/api/status')).json();window.__lmode=st.lights_mode;document.getElementById('backend-pill').textContent=st.backend.toUpperCase()+' · '+st.model}catch(e){}
  loadScenes();loadLights();loadAlerts();loadLearn();loadPending();loadTimeline();
  setInterval(loadAlerts,12000);setInterval(loadPending,8000);
  startStream();
  addMsg('jarvis',"MÉGA JARVIS v5.0 en ligne. Je suis maintenant un vrai agent : j'enchaîne les actions, je vois le résultat de mes outils, j'ai une mémoire long terme, une timeline temps réel et des automatisations. Veille vocale 👂, urgence 🆘, sécurité durcie 🔒. Dis « cherche la météo et si pluie ferme les volets » ou « mode cinéma ». 😏");
})();
</script>
</body>
</html>"""

# ─────────────────────────────────────────────
# 🛡️ MODE GARDIEN (module intégré)
# ─────────────────────────────────────────────
try:
    from guardian.config import load_config as _g_load_config
    from guardian.store import GuardianStore
    from guardian.service import GuardianService
    from guardian.providers import get_vision_provider, get_speech_provider, get_realtime_provider
    from guardian.pairing import DevicePairing
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
    _WEB_DIR = Path(__file__).resolve().parent.parent / "web"
    app.register_blueprint(create_guardian_blueprint(
        guardian_service, perms=permission_manager,
        emergency_approval=emergency_approval, realtime_provider=_g_realtime,
        pairing=device_pairing, web_dir=str(_WEB_DIR)))
    logger.info("🛡️ Mode Gardien intégré : /gardien + /api/guardian/* "
                f"(vision={GUARDIAN_CONFIG.vision_provider}, cloud={GUARDIAN_CONFIG.cloud_vision}, "
                f"audio={GUARDIAN_CONFIG.audio_enabled})")
except Exception as _ge:                       # ne casse jamais le serveur principal
    logger.warning(f"Mode Gardien non chargé: {_ge}")


@app.after_request
def _security_headers(resp):
    """En-têtes de sécurité (CSP, Permissions-Policy…) sur les pages servies.

    CSP stricte : aucun script externe (on supprime les scripts opaques
    type claude.ai). 'self' + inline (l'app embarque son JS). Permissions-Policy
    restreint caméra/micro à la même origine (nécessaire au Gardien)."""
    is_html = "text/html" in (resp.headers.get("Content-Type", ""))
    if is_html:
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: blob:; "
            "media-src 'self' blob:; "
            "connect-src 'self'; "
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
║   JARVIS v4.0 — IA + MAISON CONNECTÉE           ║
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

    security.start()
    automation.start()
    proactive.start()
    if CONFIG["http_host"] == "0.0.0.0":
        print("⚠️  Exposé sur 0.0.0.0 (tout le LAN). Assure-toi d'avoir auth + HTTPS.")
    app.run(host=CONFIG["http_host"], port=CONFIG["http_port"],
            debug=False, threaded=True, ssl_context=ssl_ctx)
