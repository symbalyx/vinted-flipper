"""
╔══════════════════════════════════════════════════════════════╗
║  JARVIS v4 — Contrôle des lumières                            ║
║  Philips Hue (pont local) + mode SIMULÉ pour démo            ║
╚══════════════════════════════════════════════════════════════╝

Deux modes, choisis automatiquement :
  • HUE      : si un pont Philips Hue est configuré (IP + clé API)
  • SIMULÉ   : sinon, des lampes virtuelles en mémoire pour tester le dashboard,
               les scènes et la réponse anti-intrusion sans matériel.

Obtenir une clé Hue (1 minute) :
  1. Trouve l'IP du pont : https://discovery.meethue.com
  2. Appuie sur le bouton physique du pont
  3. curl -X POST http://<IP_PONT>/api -d '{"devicetype":"jarvis#home"}'
  4. Mets l'IP et le "username" renvoyé dans config :
        HUE_BRIDGE_IP=192.168.1.x   HUE_USERNAME=xxxxx
"""

import os
import logging
import requests

logger = logging.getLogger("JARVIS.lights")

# Couleurs nommées → coordonnées CIE xy (compatibles Hue) + teinte de secours
COLORS = {
    "rouge":   {"xy": [0.675, 0.322], "name": "rouge"},
    "vert":    {"xy": [0.409, 0.518], "name": "vert"},
    "bleu":    {"xy": [0.167, 0.040], "name": "bleu"},
    "jaune":   {"xy": [0.443, 0.476], "name": "jaune"},
    "orange":  {"xy": [0.556, 0.408], "name": "orange"},
    "rose":    {"xy": [0.385, 0.222], "name": "rose"},
    "violet":  {"xy": [0.272, 0.110], "name": "violet"},
    "cyan":    {"xy": [0.170, 0.300], "name": "cyan"},
    "blanc":   {"xy": [0.323, 0.329], "name": "blanc"},
    "chaud":   {"xy": [0.500, 0.415], "name": "blanc chaud"},
    "froid":   {"xy": [0.313, 0.329], "name": "blanc froid"},
}


class LightController:
    def __init__(self, bridge_ip: str = "", username: str = ""):
        self.bridge_ip = bridge_ip or os.getenv("HUE_BRIDGE_IP", "")
        self.username = username or os.getenv("HUE_USERNAME", "")
        self.mode = "hue" if (self.bridge_ip and self.username) else "simulé"
        # Lampes virtuelles pour le mode simulé
        self._sim = {
            "salon":     {"on": False, "bri": 80, "color": "blanc chaud"},
            "chambre":   {"on": False, "bri": 50, "color": "blanc chaud"},
            "cuisine":   {"on": False, "bri": 100, "color": "blanc"},
            "bureau":    {"on": False, "bri": 90, "color": "blanc froid"},
            "entrée":    {"on": False, "bri": 70, "color": "blanc"},
        }
        logger.info(f"💡 Lumières: mode {self.mode.upper()}")

    @property
    def _base(self) -> str:
        return f"http://{self.bridge_ip}/api/{self.username}"

    # ── Listing ───────────────────────────────────────────────
    def list_lights(self) -> dict:
        if self.mode == "simulé":
            return {n: dict(s) for n, s in self._sim.items()}
        try:
            r = requests.get(f"{self._base}/lights", timeout=5)
            data = r.json()
            out = {}
            for _id, light in data.items():
                st = light.get("state", {})
                out[light.get("name", _id)] = {
                    "id": _id,
                    "on": st.get("on", False),
                    "bri": round(st.get("bri", 0) / 254 * 100) if "bri" in st else None,
                    "reachable": st.get("reachable", True),
                }
            return out
        except Exception as e:
            return {"erreur": f"Pont Hue injoignable: {e}"}

    def _hue_id(self, name: str):
        try:
            r = requests.get(f"{self._base}/lights", timeout=5)
            for _id, light in r.json().items():
                if light.get("name", "").lower() == name.lower():
                    return _id
            # match partiel
            for _id, light in r.json().items():
                if name.lower() in light.get("name", "").lower():
                    return _id
        except Exception:
            pass
        return None

    # ── Actions ───────────────────────────────────────────────
    def set_state(self, name: str, on: bool = None, bri: int = None,
                  color: str = None) -> str:
        name = (name or "").strip()
        if name.lower() in ("toutes", "tout", "all", "partout"):
            results = [self.set_state(n, on, bri, color) for n in self.list_lights()
                       if n != "erreur"]
            return " | ".join(results)

        if self.mode == "simulé":
            key = self._sim_key(name)
            if not key:
                return f"Lampe '{name}' inconnue (dispo: {', '.join(self._sim)})"
            if on is not None:
                self._sim[key]["on"] = on
            if bri is not None:
                self._sim[key]["bri"] = max(0, min(100, bri))
                self._sim[key]["on"] = bri > 0
            if color is not None and color.lower() in COLORS:
                self._sim[key]["color"] = COLORS[color.lower()]["name"]
                self._sim[key]["on"] = True
            s = self._sim[key]
            etat = "allumée" if s["on"] else "éteinte"
            return f"💡 {key.capitalize()}: {etat} ({s['bri']}%, {s['color']})"

        # Mode Hue réel
        _id = self._hue_id(name)
        if not _id:
            return f"Lampe '{name}' introuvable sur le pont Hue."
        body = {}
        if on is not None:
            body["on"] = on
        if bri is not None:
            body["on"] = True
            body["bri"] = max(1, min(254, round(bri / 100 * 254)))
        if color is not None and color.lower() in COLORS:
            body["on"] = True
            body["xy"] = COLORS[color.lower()]["xy"]
        try:
            requests.put(f"{self._base}/lights/{_id}/state", json=body, timeout=5)
            return f"💡 '{name}' mis à jour ({body})"
        except Exception as e:
            return f"Échec contrôle '{name}': {e}"

    def _sim_key(self, name: str):
        nl = name.lower()
        if nl in self._sim:
            return nl
        for k in self._sim:
            if nl in k or k in nl:
                return k
        return None

    def all_off(self) -> str:
        return self.set_state("toutes", on=False)

    def flash(self, color: str = "rouge", times: int = 3) -> str:
        """Fait clignoter toutes les lampes — utilisé par l'alarme anti-intrusion."""
        import time
        for _ in range(max(1, times)):
            self.set_state("toutes", on=True, bri=100, color=color)
            time.sleep(0.4)
            self.set_state("toutes", on=False)
            time.sleep(0.3)
        return f"🚨 Flash {color} x{times}"
