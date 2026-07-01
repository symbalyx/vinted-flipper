"""
╔══════════════════════════════════════════════════════════════╗
║  JARVIS v5.1 — Vision réelle (multimodale)                    ║
╚══════════════════════════════════════════════════════════════╝

Analyse RÉELLE d'une image (caméra de sécurité ou capture d'écran) par un modèle
multimodal, au lieu du « faux » texte d'avant. Utilise Ollama (llava / llama3.2-
vision / qwen2.5-vl) en local si disponible. Dégradation gracieuse : si aucun
modèle vision n'est joignable, renvoie un message clair.

    ollama pull llava        # ou: llama3.2-vision, qwen2.5-vl
"""

import os
import base64
import logging

import requests

logger = logging.getLogger("JARVIS.vision")

OLLAMA_GEN = os.getenv("OLLAMA_VISION_URL", "http://localhost:11434/api/generate")
VISION_MODEL = os.getenv("JARVIS_VISION_MODEL", "llava")


def available() -> bool:
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        names = [m.get("name", "") for m in r.json().get("models", [])]
        return any(VISION_MODEL.split(":")[0] in n for n in names)
    except Exception:
        return False


def analyze(image_b64: str, prompt: str = "") -> str:
    """Décrit/analyse une image (base64 sans en-tête data:). Renvoie du texte."""
    prompt = prompt or ("Décris ce que tu vois sur cette image de sécurité. "
                        "Y a-t-il une personne, un objet suspect, un risque ? "
                        "Donne un niveau de menace (bas/moyen/élevé). Sois bref et direct.")
    # Nettoie un éventuel préfixe data:image
    if "," in image_b64[:40]:
        image_b64 = image_b64.split(",", 1)[1]
    try:
        r = requests.post(OLLAMA_GEN, json={
            "model": VISION_MODEL, "prompt": prompt,
            "images": [image_b64], "stream": False}, timeout=60)
        r.raise_for_status()
        return r.json().get("response", "").strip() or "(pas de réponse du modèle vision)"
    except requests.exceptions.ConnectionError:
        return ("Vision réelle indisponible : lance Ollama et `ollama pull llava` "
                "(ou définis JARVIS_VISION_MODEL). En attendant, analyse caméra limitée.")
    except Exception as e:
        return f"Analyse vision échouée : {e}"


def analyze_file(path: str, prompt: str = "") -> str:
    try:
        with open(path, "rb") as f:
            return analyze(base64.b64encode(f.read()).decode(), prompt)
    except Exception as e:
        return f"Image illisible : {e}"
