"""
╔══════════════════════════════════════════════════════════════╗
║  JARVIS v4 — Apprentissage long terme                         ║
║  Profil utilisateur évolutif + détection auto-adaptative      ║
╚══════════════════════════════════════════════════════════════╝

JARVIS s'améliore au fil du temps :
  • Mémorise ce que tu utilises le plus (commandes, scènes, pièces).
  • Apprend tes préférences (enceinte favorite…) et les réinjecte dans son
    prompt → réponses de plus en plus personnalisées.
  • Ajuste TOUT SEUL la sensibilité de la détection d'intrus selon tes retours
    « fausse alerte » / « vraie alerte » (moins de faux positifs avec le temps).

Persisté dans memory/profile.json — survit aux redémarrages.
"""

import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("JARVIS.learning")


class LearningEngine:
    def __init__(self, profile_file: str = "memory/profile.json"):
        self.path = Path(profile_file)
        self.data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text())
            except Exception as e:
                logger.warning(f"Profil illisible: {e}")
        return {
            "created": datetime.now().isoformat(),
            "interactions": 0,
            "command_counts": {},
            "scene_counts": {},
            "room_counts": {},
            "speaker_counts": {},
            "false_alarms": 0,
            "confirmed_alarms": 0,
            "sensitivity_adj": 0,     # +N = moins sensible (s'auto-ajuste)
            "facts": [],              # faits retenus sur l'utilisateur
        }

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.warning(f"Sauvegarde profil ratée: {e}")

    # ── Enregistrement d'usage ────────────────────────────────
    def _bump(self, bucket: str, key: str, n: int = 1):
        d = self.data.setdefault(bucket, {})
        d[key] = d.get(key, 0) + n

    def record_chat(self):
        self.data["interactions"] = self.data.get("interactions", 0) + 1
        self.save()

    def record_command(self, tag: str):
        self._bump("command_counts", tag)

    def record_scene(self, name: str):
        self._bump("scene_counts", name.lower())

    def record_room(self, name: str):
        self._bump("room_counts", name.lower())

    def record_speaker(self, name: str):
        if name:
            self._bump("speaker_counts", name)

    def add_fact(self, fact: str) -> str:
        fact = fact.strip()
        if fact and fact not in self.data["facts"]:
            self.data["facts"].append(fact)
            self.data["facts"] = self.data["facts"][-30:]
            self.save()
            return f"Noté. Je m'en souviendrai : « {fact} »"
        return "Je le savais déjà, mais merci de me prendre pour un poisson rouge."

    # ── Auto-adaptation de la détection ───────────────────────
    def note_false_alarm(self) -> str:
        self.data["false_alarms"] = self.data.get("false_alarms", 0) + 1
        # 1 fausse alerte sur 2 → on baisse la sensibilité d'un cran
        if self.data["false_alarms"] % 2 == 0:
            self.data["sensitivity_adj"] = min(40, self.data.get("sensitivity_adj", 0) + 5)
        self.save()
        return (f"Compris, fausse alerte enregistrée. Je deviens moins parano "
                f"(ajustement +{self.data['sensitivity_adj']}). {self.data['false_alarms']} au total.")

    def note_confirmed_alarm(self):
        self.data["confirmed_alarms"] = self.data.get("confirmed_alarms", 0) + 1
        self.save()

    def motion_threshold(self, base: int) -> int:
        """Seuil de mouvement auto-ajusté selon l'historique de fausses alertes."""
        return max(10, base + self.data.get("sensitivity_adj", 0))

    # ── Helpers de synthèse ───────────────────────────────────
    def _top(self, bucket: str, n: int = 3):
        return Counter(self.data.get(bucket, {})).most_common(n)

    def preferred_speaker(self) -> str:
        top = self._top("speaker_counts", 1)
        return top[0][0] if top else ""

    def profile_summary(self) -> str:
        """Texte court injecté dans le prompt système pour personnaliser JARVIS."""
        if self.data.get("interactions", 0) < 2 and not self.data.get("facts"):
            return ""
        bits = []
        rooms = self._top("room_counts")
        scenes = self._top("scene_counts")
        cmds = self._top("command_counts")
        if rooms:
            bits.append("pièces les plus pilotées : " + ", ".join(f"{k} (x{v})" for k, v in rooms))
        if scenes:
            bits.append("scènes préférées : " + ", ".join(f"{k}" for k, _ in scenes))
        if cmds:
            bits.append("pouvoirs les plus utilisés : " + ", ".join(f"{k}" for k, _ in cmds))
        if self.preferred_speaker():
            bits.append(f"enceinte favorite : {self.preferred_speaker()}")
        if self.data.get("facts"):
            bits.append("à retenir — " + " ; ".join(self.data["facts"][-8:]))
        if not bits:
            return ""
        return ("\n\n[PROFIL UTILISATEUR — adapte-toi à ces habitudes, propose "
                "des raccourcis pertinents] " + " | ".join(bits))

    def stats(self) -> dict:
        return {
            "interactions": self.data.get("interactions", 0),
            "false_alarms": self.data.get("false_alarms", 0),
            "confirmed_alarms": self.data.get("confirmed_alarms", 0),
            "sensitivity_adj": self.data.get("sensitivity_adj", 0),
            "top_commands": self._top("command_counts", 5),
            "top_scenes": self._top("scene_counts", 5),
            "top_rooms": self._top("room_counts", 5),
            "facts": self.data.get("facts", []),
        }
