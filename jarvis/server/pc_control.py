"""
╔══════════════════════════════════════════════════════════════╗
║  JARVIS v5.1 — Contrôle PC avancé                             ║
║  Capture écran • média • alimentation • process • presse-papier║
╚══════════════════════════════════════════════════════════════╝

Multi-plateforme (Windows / macOS / Linux) avec dégradation gracieuse : si un
outil n'est pas dispo, on renvoie un message clair au lieu de planter.

Garde-fous : les actions DESTRUCTRICES (shutdown/restart/logoff) exigent
`confirm=True`. La capture d'écran/saisie clavier ne sont que locales.

Dépendances optionnelles (toutes facultatives) :
    pip install mss pillow      # capture écran rapide
    pip install pyautogui       # saisie clavier/souris
    pip install pyperclip       # presse-papier portable
"""

import os
import time
import shutil
import logging
import platform
import subprocess
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("JARVIS.pc")
SYS = platform.system()   # 'Windows' | 'Darwin' | 'Linux'


def _run(cmd, timeout=8):
    """Lance une commande système (liste d'args), renvoie (ok, sortie)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except FileNotFoundError:
        return False, f"Outil absent : {cmd[0]}"
    except Exception as e:
        return False, str(e)


class PCController:
    def __init__(self, screenshot_dir="pc/screenshots"):
        self.shot_dir = Path(screenshot_dir)
        self.shot_dir.mkdir(parents=True, exist_ok=True)

    # ── 📸 Capture d'écran ────────────────────────────────────
    def screenshot(self) -> dict:
        """Capture l'écran. Renvoie {'path':..., 'ok':bool, 'msg':...}."""
        path = self.shot_dir / f"screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        # 1) mss (rapide, multi-plateforme)
        try:
            import mss
            with mss.mss() as sct:
                sct.shot(mon=-1, output=str(path))
            return {"ok": True, "path": str(path), "msg": f"Capture enregistrée : {path}"}
        except Exception:
            pass
        # 2) Pillow ImageGrab (Windows/macOS)
        try:
            from PIL import ImageGrab
            ImageGrab.grab().save(str(path))
            return {"ok": True, "path": str(path), "msg": f"Capture enregistrée : {path}"}
        except Exception:
            pass
        # 3) Outils système (Linux/macOS)
        if SYS == "Linux":
            for tool in (["scrot", str(path)], ["import", "-window", "root", str(path)],
                         ["gnome-screenshot", "-f", str(path)]):
                ok, _ = _run(tool)
                if ok and path.exists():
                    return {"ok": True, "path": str(path), "msg": f"Capture : {path}"}
        elif SYS == "Darwin":
            ok, _ = _run(["screencapture", "-x", str(path)])
            if ok and path.exists():
                return {"ok": True, "path": str(path), "msg": f"Capture : {path}"}
        return {"ok": False, "path": "", "msg": "Capture impossible (installe 'mss' ou 'pillow')."}

    def screenshot_bytes(self):
        res = self.screenshot()
        if res["ok"] and Path(res["path"]).exists():
            return Path(res["path"]).read_bytes()
        return None

    # ── 🎵 Contrôle média (touches multimédia) ────────────────
    def media(self, action: str) -> str:
        action = (action or "").lower().strip()
        aliases = {"play": "play", "pause": "play", "play_pause": "play", "lecture": "play",
                   "next": "next", "suivant": "next", "previous": "prev", "prev": "prev",
                   "precedent": "prev", "stop": "stop",
                   "mute": "mute", "vol_up": "vol_up", "vol_down": "vol_down"}
        act = aliases.get(action)
        if not act:
            return f"Action média inconnue : {action}"
        try:
            if SYS == "Linux":
                pc = {"play": "play-pause", "next": "next", "prev": "previous",
                      "stop": "stop"}.get(act)
                if pc:
                    ok, out = _run(["playerctl", pc])
                    if ok:
                        return f"🎵 média : {act}"
                # volume via amixer
                if act == "mute":
                    _run(["amixer", "set", "Master", "toggle"]); return "🔇 mute basculé"
                if act == "vol_up":
                    _run(["amixer", "set", "Master", "5%+"]); return "🔊 +5%"
                if act == "vol_down":
                    _run(["amixer", "set", "Master", "5%-"]); return "🔉 -5%"
                return f"playerctl requis (apt install playerctl) — action {act}"
            elif SYS == "Darwin":
                keymap = {"play": 16, "next": 17, "prev": 18}  # NX media keys
                if act in keymap:
                    scr = (f'tell application "System Events" to key code {100 + keymap[act]}')
                    _run(["osascript", "-e", scr]); return f"🎵 média : {act}"
                vol = {"vol_up": "set volume output volume (output volume of (get volume settings) + 6)",
                       "vol_down": "set volume output volume (output volume of (get volume settings) - 6)",
                       "mute": "set volume with output muted"}.get(act)
                if vol:
                    _run(["osascript", "-e", vol]); return f"🔊 {act}"
            elif SYS == "Windows":
                import ctypes
                VK = {"play": 0xB3, "next": 0xB0, "prev": 0xB1, "stop": 0xB2,
                      "mute": 0xAD, "vol_up": 0xAF, "vol_down": 0xAE}
                code = VK.get(act)
                if code:
                    ctypes.windll.user32.keybd_event(code, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(code, 0, 2, 0)
                    return f"🎵 média : {act}"
        except Exception as e:
            return f"Média impossible : {e}"
        return f"Action média non supportée ici : {act}"

    # ── ⏻ Alimentation (destructif → confirm) ─────────────────
    def power(self, action: str, confirm: bool = False) -> str:
        action = (action or "").lower().strip()
        destructive = {"shutdown", "restart", "reboot", "logoff", "logout"}
        if action in destructive and not confirm:
            return f"⚠️ '{action}' nécessite une confirmation (confirm=true)."
        try:
            if action == "lock":
                cmd = {"Windows": ["rundll32.exe", "user32.dll,LockWorkStation"],
                       "Darwin": ["pmset", "displaysleepnow"],
                       "Linux": ["loginctl", "lock-session"]}.get(SYS)
                _run(cmd); return "🔒 Session verrouillée."
            if action == "sleep":
                cmd = {"Windows": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
                       "Darwin": ["pmset", "sleepnow"],
                       "Linux": ["systemctl", "suspend"]}.get(SYS)
                _run(cmd); return "😴 Mise en veille."
            if action in ("shutdown",):
                cmd = {"Windows": ["shutdown", "/s", "/t", "5"],
                       "Darwin": ["osascript", "-e", 'tell app "System Events" to shut down'],
                       "Linux": ["systemctl", "poweroff"]}.get(SYS)
                _run(cmd); return "⏻ Extinction du PC lancée."
            if action in ("restart", "reboot"):
                cmd = {"Windows": ["shutdown", "/r", "/t", "5"],
                       "Darwin": ["osascript", "-e", 'tell app "System Events" to restart'],
                       "Linux": ["systemctl", "reboot"]}.get(SYS)
                _run(cmd); return "🔁 Redémarrage lancé."
            if action in ("logoff", "logout"):
                cmd = {"Windows": ["shutdown", "/l"],
                       "Darwin": ["osascript", "-e", 'tell app "System Events" to log out'],
                       "Linux": ["loginctl", "terminate-user", os.getenv("USER", "")]}.get(SYS)
                _run(cmd); return "👋 Déconnexion lancée."
        except Exception as e:
            return f"Action alimentation impossible : {e}"
        return f"Action alimentation inconnue : {action} (lock, sleep, shutdown, restart, logoff)"

    def lock(self) -> str:
        return self.power("lock")

    # ── 🗡️ Processus ──────────────────────────────────────────
    def kill_process(self, target: str) -> str:
        try:
            import psutil
        except ImportError:
            return "psutil requis (pip install psutil)."
        target = str(target).strip()
        killed = []
        for p in psutil.process_iter(["pid", "name"]):
            try:
                if target == str(p.info["pid"]) or target.lower() in (p.info["name"] or "").lower():
                    p.terminate(); killed.append(f"{p.info['name']}({p.info['pid']})")
            except Exception:
                continue
        if not killed:
            return f"Aucun processus '{target}'."
        return f"🗡️ Terminé : {', '.join(killed[:10])}"

    # ── 📋 Presse-papier ──────────────────────────────────────
    def clipboard_get(self) -> str:
        try:
            import pyperclip
            return pyperclip.paste() or "(presse-papier vide)"
        except Exception:
            pass
        if SYS == "Linux":
            ok, out = _run(["xclip", "-selection", "clipboard", "-o"])
            if ok:
                return out or "(vide)"
        elif SYS == "Darwin":
            ok, out = _run(["pbpaste"])
            if ok:
                return out or "(vide)"
        return "Presse-papier indisponible (pip install pyperclip)."

    def clipboard_set(self, text: str) -> str:
        try:
            import pyperclip
            pyperclip.copy(text); return "📋 Copié dans le presse-papier."
        except Exception:
            pass
        try:
            if SYS == "Linux":
                p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
                p.communicate(text.encode()); return "📋 Copié."
            elif SYS == "Darwin":
                p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                p.communicate(text.encode()); return "📋 Copié."
            elif SYS == "Windows":
                p = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
                p.communicate(text.encode("utf-16")); return "📋 Copié."
        except Exception as e:
            return f"Copie impossible : {e}"
        return "Presse-papier indisponible."

    # ── ⌨️ Saisie clavier (optionnel, pyautogui) ──────────────
    def type_text(self, text: str) -> str:
        try:
            import pyautogui
            pyautogui.typewrite(text, interval=0.01)
            return f"⌨️ Texte saisi ({len(text)} caractères)."
        except Exception:
            return "Saisie clavier indisponible (pip install pyautogui + environnement graphique)."

    def press_key(self, combo: str) -> str:
        try:
            import pyautogui
            keys = [k.strip() for k in combo.replace("+", " ").split()]
            pyautogui.hotkey(*keys)
            return f"⌨️ Touches : {combo}"
        except Exception:
            return "Touches indisponibles (pip install pyautogui)."

    # ── 🔆 Luminosité écran ───────────────────────────────────
    def brightness(self, level: int) -> str:
        level = max(0, min(100, int(level)))
        try:
            if SYS == "Linux":
                if shutil.which("brightnessctl"):
                    _run(["brightnessctl", "set", f"{level}%"]); return f"🔆 Luminosité {level}%"
                if shutil.which("xrandr"):
                    ok, out = _run(["xrandr", "--listmonitors"])
                    # best effort : applique sur le 1er écran connecté
                    return "xrandr détecté — règle via xbacklight si dispo."
                return "brightnessctl requis (Linux)."
            elif SYS == "Darwin":
                if shutil.which("brightness"):
                    _run(["brightness", str(level / 100)]); return f"🔆 {level}%"
                return "Outil 'brightness' requis (brew install brightness)."
            elif SYS == "Windows":
                ps = (f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
                      f".WmiSetBrightness(1,{level})")
                _run(["powershell", "-Command", ps]); return f"🔆 {level}%"
        except Exception as e:
            return f"Luminosité impossible : {e}"
        return "Luminosité non supportée ici."

    # ── 📂 Ouvrir fichier/dossier avec l'app par défaut ───────
    def open_path(self, path: str) -> str:
        p = Path(path).expanduser()
        if not p.exists():
            return f"Chemin introuvable : {p}"
        try:
            if SYS == "Windows":
                os.startfile(str(p))            # noqa
            elif SYS == "Darwin":
                _run(["open", str(p)])
            else:
                _run(["xdg-open", str(p)])
            return f"📂 Ouvert : {p}"
        except Exception as e:
            return f"Ouverture impossible : {e}"

    # ── 🖥️ Fenêtre active ─────────────────────────────────────
    def active_window(self) -> str:
        try:
            if SYS == "Linux" and shutil.which("xdotool"):
                ok, out = _run(["xdotool", "getactivewindow", "getwindowname"])
                if ok:
                    return f"🖥️ Fenêtre active : {out}"
            elif SYS == "Darwin":
                scr = ('tell application "System Events" to get name of first application '
                       'process whose frontmost is true')
                ok, out = _run(["osascript", "-e", scr])
                if ok:
                    return f"🖥️ App active : {out}"
            elif SYS == "Windows":
                import ctypes
                h = ctypes.windll.user32.GetForegroundWindow()
                buf = ctypes.create_unicode_buffer(512)
                ctypes.windll.user32.GetWindowTextW(h, buf, 512)
                return f"🖥️ Fenêtre active : {buf.value}"
        except Exception as e:
            return f"Fenêtre active inconnue : {e}"
        return "Fenêtre active indisponible sur ce système."
