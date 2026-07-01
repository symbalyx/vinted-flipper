"""
╔══════════════════════════════════════════════════════════════╗
║  JARVIS — Géolocalisation d'une PHOTO (best-effort)          ║
╚══════════════════════════════════════════════════════════════╝

Donne une photo d'un lieu → JARVIS estime OÙ elle a été prise et pose un point
sur le globe. Deux étapes séparées (perception ≠ géocodage) :

  1. VISION : un modèle multimodal (Ollama llava local par défaut, ou cloud)
     DÉCRIT des indices (pays, ville, monuments, texte/enseignes, architecture)
     et propose éventuellement des coordonnées, sous forme de JSON validé.
  2. GÉOCODAGE (optionnel, plus fiable) : si un géocodeur est configuré
     (GEOCODER_URL, ex. Nominatim auto-hébergé), on convertit le nom de lieu en
     coordonnées précises. Sinon on retombe sur les coordonnées du modèle.

⚠️ HONNÊTETÉ : ce n'est PAS du GPS. C'est une ESTIMATION à partir d'indices
visuels + géocodage. La confiance est renvoyée ; en cas de doute, aucun point
« certain » n'est affirmé. Aucune identification de personnes.
"""

import os
import json
import logging

from guardian.schemas import _extract_json   # extraction JSON robuste (réutilisée)

logger = logging.getLogger("JARVIS.geolocate")

GEO_PROMPT = (
    "Tu es un analyste de géolocalisation d'images (OSINT de LIEU, pas de "
    "personnes). Observe la photo et déduis OÙ elle a probablement été prise à "
    "partir d'indices visibles : monuments, enseignes, langue du texte, plaques, "
    "architecture, végétation, panneaux. Réponds STRICTEMENT par un JSON valide, "
    "sans texte autour :\n"
    '{"place": "<lieu le plus précis, ex: Tour Eiffel, Paris>", '
    '"country": "<pays>", "city": "<ville>", '
    '"landmarks": [<indices>], "visible_text": [<textes lus>], '
    '"lat": <latitude ou null>, "lon": <longitude ou null>, '
    '"confidence": <0.0-1.0>, "reasoning": "<courte explication>"}\n'
    "Si tu n'es pas sûr, mets une faible confidence et lat/lon à null."
)


def _valid_latlon(lat, lon) -> bool:
    try:
        return -90 <= float(lat) <= 90 and -180 <= float(lon) <= 180
    except (TypeError, ValueError):
        return False


def parse_geo(raw) -> dict:
    """Valide la sortie de vision. Retourne un dict normalisé (jamais d'exception)."""
    data = _extract_json(raw)
    if not isinstance(data, dict):
        return {"ok": False, "error": "Réponse de vision illisible"}
    place = str(data.get("place") or "").strip()[:120]
    out = {
        "ok": True,
        "place": place,
        "country": str(data.get("country") or "").strip()[:80],
        "city": str(data.get("city") or "").strip()[:80],
        "landmarks": [str(x)[:80] for x in (data.get("landmarks") or [])][:12],
        "visible_text": [str(x)[:80] for x in (data.get("visible_text") or [])][:12],
        "reasoning": str(data.get("reasoning") or "").strip()[:400],
        "lat": None, "lon": None, "source": "none",
    }
    try:
        conf = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        conf = 0.0
    out["confidence"] = max(0.0, min(1.0, conf))
    lat, lon = data.get("lat"), data.get("lon")
    if _valid_latlon(lat, lon):
        out["lat"], out["lon"] = float(lat), float(lon)
        out["source"] = "model"
    return out


def geocode(place: str, fetch=None) -> dict:
    """Géocode un nom de lieu → {lat, lon, display} via GEOCODER_URL (optionnel).
    `fetch` injectable pour les tests. Retourne {} si non configuré/introuvable."""
    tmpl = os.getenv("GEOCODER_URL", "")
    if not tmpl or not place:
        return {}
    try:
        import requests
        url = tmpl.replace("{q}", requests.utils.quote(place))
        getter = fetch or (lambda u: requests.get(
            u, timeout=float(os.getenv("GEOCODER_TIMEOUT", "6")),
            headers={"User-Agent": "JARVIS-Guardian/5.2"}).json())
        data = getter(url)
        # Format Nominatim : liste d'objets {lat, lon, display_name}.
        if isinstance(data, list) and data:
            item = data[0]
        elif isinstance(data, dict):
            item = data
        else:
            return {}
        lat, lon = item.get("lat"), item.get("lon")
        if _valid_latlon(lat, lon):
            return {"lat": float(lat), "lon": float(lon),
                    "display": str(item.get("display_name") or place)[:200]}
    except Exception as e:
        logger.warning(f"Géocodage échoué: {e}")
    return {}


def locate_photo(image_b64: str, vision_provider, geocode_fetch=None) -> dict:
    """Pipeline complet : vision → (géocodage) → coordonnées + confiance."""
    if vision_provider is None:
        return {"ok": False, "error": "Aucun modèle de vision disponible (Ollama/clé)."}
    try:
        raw = vision_provider.analyze(image_b64, GEO_PROMPT)
    except Exception as e:
        return {"ok": False, "error": f"Vision indisponible: {e}"}
    res = parse_geo(raw)
    if not res.get("ok"):
        return res
    # Géocodage prioritaire (plus fiable) si un lieu est nommé.
    geo = geocode(res["place"], fetch=geocode_fetch) if res["place"] else {}
    if geo:
        res["lat"], res["lon"] = geo["lat"], geo["lon"]
        res["source"] = "geocoder"
        res["display"] = geo.get("display", "")
    res["locatable"] = res["lat"] is not None
    return res
