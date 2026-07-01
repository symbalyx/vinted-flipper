"""
╔══════════════════════════════════════════════════════════════╗
║  JARVIS v5 — Moteur d'automatisations (proactivité réactive)  ║
╚══════════════════════════════════════════════════════════════╝

Fait passer JARVIS de « réactif » à « proactif » : une boucle de fond évalue le
contexte (heure × présence × météo × alarme) et déclenche des scènes tout seul.
Règles déclaratives dans config/rules.json, évaluateur SÛR (liste blanche, jamais
d'eval), anti-rebond (une fois par jour par règle).
"""

import json
import time
import logging
import threading
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("JARVIS.auto")

OPS = {
    "time_between": lambda ctx, a: a["from"] <= ctx["hhmm"] <= a["to"],
    "armed":        lambda ctx, a: ctx["armed"] == a["value"],
    "presence":     lambda ctx, a: ctx["present"] == a["value"],
    "weather":      lambda ctx, a: ctx["weather"] == a["value"],
}

DEFAULT_RULES = [
    {"id": "sunset_warm", "name": "Ambiance chaude le soir", "scene": "soirée",
     "when": [{"op": "time_between", "from": "19:00", "to": "19:20"},
              {"op": "presence", "value": True}]},
    {"id": "auto_away", "name": "Absence automatique", "scene": "absence",
     "when": [{"op": "presence", "value": False},
              {"op": "time_between", "from": "09:00", "to": "18:00"}]},
    {"id": "bedtime", "name": "Heure du coucher", "scene": "bonne nuit",
     "when": [{"op": "time_between", "from": "23:30", "to": "23:50"}]},
]


class AutomationEngine:
    def __init__(self, rules_file, ctx_provider, do_scene, on_event):
        self.path = Path(rules_file)
        self.ctx_provider = ctx_provider
        self.do_scene = do_scene
        self.on_event = on_event
        self.enabled = True
        self._fired = {}
        if not self.path.exists():
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(json.dumps(DEFAULT_RULES, ensure_ascii=False, indent=2))
            except Exception:
                pass

    def rules(self):
        try:
            return json.loads(self.path.read_text()) if self.path.exists() else []
        except Exception:
            return []

    def _match(self, rule, ctx):
        try:
            return all(OPS[c["op"]](ctx, c) for c in rule.get("when", []) if c["op"] in OPS)
        except Exception:
            return False

    def tick(self):
        if not self.enabled:
            return
        ctx = self.ctx_provider()
        today = ctx["date"]
        for r in self.rules():
            rid = r.get("id")
            if r.get("once_per_day", True) and self._fired.get(rid) == today:
                continue
            if self._match(r, ctx):
                self._fired[rid] = today
                try:
                    self.do_scene(r["scene"])
                    self.on_event("automation",
                                  f"Règle « {r.get('name', rid)} » → scène {r['scene']}",
                                  meta={"rule": rid})
                    logger.info(f"⚙️ Automatisation déclenchée : {r.get('name', rid)}")
                except Exception as e:
                    logger.warning(f"Règle {rid} KO: {e}")

    def start(self, period=60):
        def _loop():
            while True:
                try:
                    self.tick()
                except Exception as e:
                    logger.debug(f"tick auto: {e}")
                time.sleep(period)
        threading.Thread(target=_loop, daemon=True, name="automation").start()
        logger.info("⚙️ Moteur d'automatisations démarré.")
