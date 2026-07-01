"""Géolocalisation prudente d'une photo : EXIF d'abord, vision ensuite.

Principes de sécurité et d'honnêteté :
- Les coordonnées GPS EXIF sont considérées comme une mesure précise fournie par
  le fichier, mais leur authenticité n'est pas garantie (elles peuvent être
  modifiées).
- Une estimation visuelle n'est JAMAIS présentée comme exacte. Le modèle renvoie
  des candidats classés avec confiance, précision estimée et indices observés.
- Si le JSON est invalide ou la confiance trop faible, le résultat est UNKNOWN.
- Aucune image n'est sauvegardée par ce module.
"""
from __future__ import annotations

import base64
import binascii
import io
import json
import logging
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Optional

from PIL import Image, UnidentifiedImageError

from .legal_osint import LegalOsintContext

logger = logging.getLogger("JARVIS.guardian.geolocation")

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_PIXELS = 25_000_000
MAX_CANDIDATES = 5
MAX_EVIDENCE = 10
MAX_TEXT = 160


@dataclass
class GeoCandidate:
    latitude: float
    longitude: float
    label: str = ""
    country: str = ""
    city: str = ""
    confidence: float = 0.0
    precision_meters: int = 0
    evidence: list[str] = field(default_factory=list)
    source: str = "vision_estimate"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PhotoGeoResult:
    status: str
    source: str
    exact: bool
    best: Optional[GeoCandidate] = None
    candidates: list[GeoCandidate] = field(default_factory=list)
    uncertainty: list[str] = field(default_factory=list)
    warning: str = ""
    provider: str = ""

    def to_dict(self) -> dict:
        return {
            "ok": True,
            "status": self.status,
            "source": self.source,
            "exact": self.exact,
            "best": self.best.to_dict() if self.best else None,
            "candidates": [c.to_dict() for c in self.candidates],
            "uncertainty": list(self.uncertainty),
            "warning": self.warning,
            "provider": self.provider,
        }


GEOLOCATION_PROMPT = """Tu es un module de géolocalisation VISUELLE prudente et respectueuse de la vie privée.
Analyse uniquement les indices visibles : panneaux, texte, architecture, relief,
végétation, signalisation, marquages routiers, transports et monuments.
N'invente jamais une précision impossible. Une ressemblance générale ne suffit
pas pour donner une rue ou un bâtiment exact.

Réponds STRICTEMENT par un objet JSON valide, sans markdown ni texte autour :
{
  "status": "estimated" ou "unknown",
  "candidates": [
    {
      "latitude": nombre entre -90 et 90,
      "longitude": nombre entre -180 et 180,
      "label": "lieu proposé",
      "country": "pays",
      "city": "ville ou région",
      "confidence": nombre entre 0 et 1,
      "precision_meters": entier >= 100,
      "evidence": ["indices visuels concrets"]
    }
  ],
  "uncertainty": ["raisons du doute"]
}

Règles :
- Au maximum 5 candidats, classés du plus probable au moins probable.
- Si aucun indice distinctif n'est visible, status="unknown" et candidates=[].
- Une estimation visuelle n'est jamais « exacte ».
- N'identifie jamais une personne, un visage, un compte social ou une plaque d'immatriculation.
- Ne cherche pas l'adresse d'une résidence privée et ne facilite aucun suivi en temps réel.
- Utilise seulement les indices de lieu non personnels : monuments, enseignes publiques, architecture, relief, voirie et transports.
"""


def _ratio(value: Any) -> float:
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        den = float(value.denominator)
        return float(value.numerator) / den if den else 0.0
    if isinstance(value, (tuple, list)) and len(value) == 2:
        den = float(value[1])
        return float(value[0]) / den if den else 0.0
    return float(value)


def gps_to_decimal(values: Iterable[Any], ref: Any) -> float:
    """Convertit (degrés, minutes, secondes) EXIF en degrés décimaux."""
    vals = list(values)
    if len(vals) != 3:
        raise ValueError("coordonnée GPS EXIF invalide")
    deg, minute, sec = (_ratio(v) for v in vals)
    out = deg + minute / 60.0 + sec / 3600.0
    if isinstance(ref, bytes):
        ref = ref.decode("ascii", errors="ignore")
    normalized_ref = str(ref).strip().upper()
    if normalized_ref in {"S", "W"}:
        out = -out
    return out


def gps_from_ifd(gps: dict) -> Optional[tuple[float, float]]:
    """Extrait latitude/longitude d'un dictionnaire GPS EXIF Pillow."""
    if not isinstance(gps, dict):
        return None
    # IDs EXIF GPS : 1=LatRef, 2=Lat, 3=LonRef, 4=Lon.
    lat_v, lat_ref = gps.get(2), gps.get(1)
    lon_v, lon_ref = gps.get(4), gps.get(3)
    if not all((lat_v, lat_ref, lon_v, lon_ref)):
        return None
    lat = gps_to_decimal(lat_v, lat_ref)
    lon = gps_to_decimal(lon_v, lon_ref)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def decode_image_data(image_data: str, max_bytes: int) -> tuple[bytes, str]:
    """Décode et valide une data-URL/base64 d'image sans la persister."""
    if not isinstance(image_data, str) or not image_data:
        raise ValueError("image manquante")
    mime = "image/jpeg"
    payload = image_data
    if image_data.startswith("data:"):
        header, sep, payload = image_data.partition(",")
        if not sep or ";base64" not in header.lower():
            raise ValueError("data URL d'image invalide")
        mime = header[5:].split(";", 1)[0].lower().strip()
        if mime not in ALLOWED_MIME:
            raise ValueError("format d'image non autorisé (JPEG, PNG ou WebP)")
    # Rejet rapide avant allocation de décodage.
    if len(payload) > int(max_bytes * 4 / 3) + 16:
        raise ValueError("image trop volumineuse")
    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("image base64 invalide") from exc
    if not raw or len(raw) > max_bytes:
        raise ValueError("image trop volumineuse" if raw else "image vide")
    try:
        with Image.open(io.BytesIO(raw)) as im:
            if im.width <= 0 or im.height <= 0 or im.width * im.height > MAX_PIXELS:
                raise ValueError("dimensions d'image non autorisées")
            detected = (im.format or "").upper()
            if detected not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("format d'image non autorisé")
            im.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("fichier image illisible") from exc
    return raw, mime


def extract_exif_gps(raw: bytes) -> Optional[tuple[float, float]]:
    try:
        with Image.open(io.BytesIO(raw)) as im:
            exif = im.getexif()
            if not exif:
                return None
            try:
                gps = exif.get_ifd(0x8825)  # GPSInfo
            except Exception:
                gps = exif.get(0x8825)
            return gps_from_ifd(gps) if gps else None
    except Exception:
        return None


def _extract_json(raw: Any) -> Optional[dict]:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    obj = json.loads(text[start:idx + 1])
                    return obj if isinstance(obj, dict) else None
                except Exception:
                    return None
    return None


def _clean_text(value: Any) -> str:
    return str(value or "").strip()[:MAX_TEXT]


def parse_visual_geolocation(raw: Any) -> tuple[list[GeoCandidate], list[str], str]:
    """Valide strictement la sortie du modèle. Retourne candidats, doutes, erreur."""
    data = _extract_json(raw)
    if not isinstance(data, dict):
        return [], [], "JSON de géolocalisation invalide"
    if set(data) - {"status", "candidates", "uncertainty"}:
        return [], [], "champs inattendus dans la réponse de géolocalisation"
    status = data.get("status")
    if status not in {"estimated", "unknown"}:
        return [], [], "status de géolocalisation invalide"
    candidates = data.get("candidates", [])
    uncertainty = data.get("uncertainty", [])
    if not isinstance(candidates, list) or not isinstance(uncertainty, list):
        return [], [], "listes de géolocalisation invalides"
    doubts = [_clean_text(x) for x in uncertainty[:MAX_EVIDENCE] if _clean_text(x)]
    if status == "unknown":
        return [], doubts, ""
    out: list[GeoCandidate] = []
    for item in candidates[:MAX_CANDIDATES]:
        if not isinstance(item, dict):
            return [], doubts, "candidat de géolocalisation invalide"
        allowed = {"latitude", "longitude", "label", "country", "city", "confidence", "precision_meters", "evidence"}
        if set(item) - allowed:
            return [], doubts, "champs inattendus dans un candidat"
        try:
            lat = float(item["latitude"])
            lon = float(item["longitude"])
            conf = float(item["confidence"])
            precision = int(item.get("precision_meters", 0))
        except (KeyError, TypeError, ValueError):
            return [], doubts, "coordonnées ou confiance invalides"
        if not (-90 <= lat <= 90 and -180 <= lon <= 180 and 0 <= conf <= 1):
            return [], doubts, "coordonnées ou confiance hors limites"
        # Une estimation visuelle ne doit pas prétendre à une précision GPS.
        precision = max(100, min(20_000_000, precision or 100_000))
        evidence = item.get("evidence", [])
        if not isinstance(evidence, list):
            return [], doubts, "indices visuels invalides"
        out.append(GeoCandidate(
            latitude=lat,
            longitude=lon,
            label=_clean_text(item.get("label")),
            country=_clean_text(item.get("country")),
            city=_clean_text(item.get("city")),
            confidence=conf,
            precision_meters=precision,
            evidence=[_clean_text(x) for x in evidence[:MAX_EVIDENCE] if _clean_text(x)],
        ))
    out.sort(key=lambda c: c.confidence, reverse=True)
    if not out:
        return [], doubts, "aucun candidat exploitable"
    return out, doubts, ""


class PhotoGeolocator:
    def __init__(self, config, vision_provider=None, event_log=None):
        self.config = config
        self.vision = vision_provider
        self.event_log = event_log
        self._lock = threading.Lock()
        self._requests: list[float] = []
        self.rate_limit = max(1, min(30, int(getattr(config, "photo_geo_rate_limit_per_min", 6))))
        self.min_confidence = float(getattr(config, "photo_geo_min_confidence", 0.35))

    def _rate_ok(self) -> bool:
        now = time.time()
        with self._lock:
            self._requests = [t for t in self._requests if now - t < 60]
            if len(self._requests) >= self.rate_limit:
                return False
            self._requests.append(now)
            return True

    def locate(self, image_data: str, hint: str = "", context: LegalOsintContext | None = None) -> dict:
        # L’API publique valide obligatoirement le contexte légal. Les appels
        # internes/tests sans contexte restent possibles, mais sont traités comme
        # une analyse personnelle locale et ne débloquent aucun outil de profilage.
        context = context or LegalOsintContext(
            purpose="personal_photo", target_type="place", authorized=True
        )
        if not self._rate_ok():
            return {"ok": False, "error": "Trop de requêtes de géolocalisation", "status": "rate_limited"}
        try:
            raw, _mime = decode_image_data(image_data, int(self.config.max_image_bytes))
        except ValueError as exc:
            return {"ok": False, "error": str(exc), "status": "invalid_image"}

        gps = extract_exif_gps(raw)
        if gps:
            lat, lon = gps
            best = GeoCandidate(
                latitude=lat, longitude=lon, label="Coordonnées GPS du fichier",
                confidence=1.0, precision_meters=15, source="exif_gps",
                evidence=["Métadonnées GPS EXIF présentes dans l'image"],
            )
            result = PhotoGeoResult(
                status="located", source="exif_gps", exact=True, best=best,
                candidates=[best],
                warning="Les métadonnées EXIF peuvent être modifiées ; vérifie le lieu avant toute décision sensible.",
            )
            self._audit("Géolocalisation photo par EXIF", {
                "source": "exif_gps", "purpose": context.purpose,
                "target_type": context.target_type,
            })
            return result.to_dict()

        provider_name = getattr(self.vision, "name", "") if self.vision else ""
        if not self.vision:
            return PhotoGeoResult(
                status="unknown", source="none", exact=False,
                uncertainty=["Aucune coordonnée EXIF et aucun fournisseur vision configuré."],
                warning="Impossible de localiser précisément cette photo sans métadonnées ni analyse visuelle.",
            ).to_dict()
        try:
            if hasattr(self.vision, "available") and not self.vision.available():
                return PhotoGeoResult(
                    status="unknown", source="vision_unavailable", exact=False, provider=provider_name,
                    uncertainty=["Le modèle de vision configuré est indisponible."],
                    warning="Lance le modèle vision local ou active explicitement un fournisseur cloud.",
                ).to_dict()
            prompt = GEOLOCATION_PROMPT
            prompt += (
                f"\nFinalité autorisée : {context.purpose}. "
                f"Type de cible autorisé : {context.target_type}."
            )
            hint = _clean_text(hint)
            if hint:
                prompt += f"\nIndice fourni par l'utilisateur (non vérifié) : {hint}"
            # Réutilise la chaîne base64 originale ; le fournisseur sait retirer le préfixe data:.
            model_raw = self.vision.analyze(image_data, prompt)
        except Exception as exc:
            logger.warning("Géolocalisation visuelle indisponible: %s", exc)
            return PhotoGeoResult(
                status="unknown", source="vision_error", exact=False, provider=provider_name,
                uncertainty=["Le fournisseur vision n'a pas pu analyser l'image."],
                warning="Aucune localisation fiable n'a été produite.",
            ).to_dict()

        candidates, uncertainty, error = parse_visual_geolocation(model_raw)
        if error:
            self._audit("Géolocalisation photo UNKNOWN", {
                "error": error, "provider": provider_name,
                "purpose": context.purpose, "target_type": context.target_type,
            })
            return PhotoGeoResult(
                status="unknown", source="vision_invalid", exact=False, provider=provider_name,
                uncertainty=[error], warning="Réponse du modèle invalide : aucun point n'a été retenu.",
            ).to_dict()
        candidates = [c for c in candidates if c.confidence >= self.min_confidence]
        if not candidates:
            return PhotoGeoResult(
                status="unknown", source="vision_estimate", exact=False, provider=provider_name,
                uncertainty=uncertainty or ["Confiance visuelle insuffisante."],
                warning="La photo ne contient pas assez d'indices distinctifs pour une localisation fiable.",
            ).to_dict()
        best = candidates[0]
        result = PhotoGeoResult(
            status="estimated", source="vision_estimate", exact=False, best=best,
            candidates=candidates, uncertainty=uncertainty, provider=provider_name,
            warning="Estimation visuelle seulement : le point peut être éloigné de plusieurs kilomètres.",
        )
        self._audit("Géolocalisation photo estimée", {
            "provider": provider_name, "confidence": best.confidence,
            "precision_meters": best.precision_meters,
            "purpose": context.purpose, "target_type": context.target_type,
        })
        return result.to_dict()

    def _audit(self, message: str, meta: dict) -> None:
        if not self.event_log:
            return
        try:
            self.event_log.add("photo_geolocation", message, meta=meta)
        except Exception:
            logger.exception("Échec de journalisation géolocalisation")
