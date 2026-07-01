"""
Configuration du mode Gardien — uniquement via variables d'environnement.

⚠️ Aucune clé d'API ne doit jamais transiter par le navigateur. Toutes les
clés (OpenAI, Gemini, …) restent côté serveur, lues ici depuis l'environnement.
"""

import os
from dataclasses import dataclass, field, asdict


def _b(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def _i(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _f(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass
class GuardianConfig:
    # ── Confidentialité / local-first ───────────────────────────
    # 0 = aucune image ne quitte le réseau local (vision 100% locale).
    cloud_vision: bool = False
    # Audio désactivé par défaut (capture micro + conversation temps réel).
    audio_enabled: bool = False
    # Rétention des événements/snapshots (jours) avant purge automatique.
    retention_days: int = 7
    # Sauvegarde des transcriptions (désactivée par défaut = vie privée).
    save_transcripts: bool = False

    # ── Politique d'escalade ────────────────────────────────────
    # L'escalade automatique (sirène/flash sans humain) est OFF par défaut.
    auto_escalate: bool = False
    # Secondes de présence avant de considérer un « rôdage ».
    loiter_seconds: float = 20.0
    # Nombre de confirmations de suivi avant de parler.
    min_confirmations: int = 3
    # Cooldown (s) entre deux prises de parole.
    speak_cooldown: float = 6.0
    # Cooldown (s) entre deux alertes.
    alert_cooldown: float = 30.0
    # Durée max d'une sirène (s) et cooldown.
    siren_max_seconds: int = 30
    siren_cooldown: float = 60.0

    # ── Fournisseurs ────────────────────────────────────────────
    vision_provider: str = "ollama"          # ollama | openai | gemini
    speech_provider: str = "ollama"          # ollama | openai | gemini | template
    realtime_provider: str = "none"          # none | openai | gemini
    openai_realtime_model: str = "gpt-realtime-2"

    # ── Limites de robustesse ───────────────────────────────────
    max_image_bytes: int = 2_000_000         # 2 Mo : refuse les images trop lourdes
    request_timeout: float = 20.0            # AbortController côté serveur
    rate_limit_per_min: int = 30             # requêtes d'analyse / minute / session
    # Géolocalisation photo : endpoint plus coûteux, volontairement plus limité.
    photo_geo_rate_limit_per_min: int = 6
    photo_geo_min_confidence: float = 0.35

    # ── Chemins ────────────────────────────────────────────────
    db_path: str = "memory/guardian.db"
    snapshot_dir: str = "security/guardian_snaps"

    zones: dict = field(default_factory=dict)

    def public_dict(self) -> dict:
        """Vue sûre à exposer au navigateur (aucun secret ici)."""
        d = asdict(self)
        d.pop("zones", None)
        return d


def load_config() -> GuardianConfig:
    return GuardianConfig(
        cloud_vision=_b("GUARDIAN_CLOUD_VISION", "0"),
        audio_enabled=_b("GUARDIAN_AUDIO_ENABLED", "0"),
        retention_days=_i("GUARDIAN_RETENTION_DAYS", 7),
        save_transcripts=_b("GUARDIAN_SAVE_TRANSCRIPTS", "0"),
        auto_escalate=_b("GUARDIAN_AUTO_ESCALATE", "0"),
        loiter_seconds=_f("GUARDIAN_LOITER_SECONDS", 20.0),
        min_confirmations=_i("GUARDIAN_MIN_CONFIRMATIONS", 3),
        speak_cooldown=_f("GUARDIAN_SPEAK_COOLDOWN", 6.0),
        alert_cooldown=_f("GUARDIAN_ALERT_COOLDOWN", 30.0),
        siren_max_seconds=_i("GUARDIAN_SIREN_MAX_SECONDS", 30),
        siren_cooldown=_f("GUARDIAN_SIREN_COOLDOWN", 60.0),
        vision_provider=os.getenv("GUARDIAN_VISION_PROVIDER", "ollama"),
        speech_provider=os.getenv("GUARDIAN_SPEECH_PROVIDER", "ollama"),
        realtime_provider=os.getenv("GUARDIAN_REALTIME_PROVIDER", "none"),
        openai_realtime_model=os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime-2"),
        max_image_bytes=_i("GUARDIAN_MAX_IMAGE_BYTES", 2_000_000),
        request_timeout=_f("GUARDIAN_REQUEST_TIMEOUT", 20.0),
        rate_limit_per_min=_i("GUARDIAN_RATE_LIMIT_PER_MIN", 30),
        photo_geo_rate_limit_per_min=_i("GUARDIAN_PHOTO_GEO_RATE_LIMIT_PER_MIN", 6),
        photo_geo_min_confidence=_f("GUARDIAN_PHOTO_GEO_MIN_CONFIDENCE", 0.35),
        db_path=os.getenv("GUARDIAN_DB_PATH", "memory/guardian.db"),
        snapshot_dir=os.getenv("GUARDIAN_SNAPSHOT_DIR", "security/guardian_snaps"),
    )
