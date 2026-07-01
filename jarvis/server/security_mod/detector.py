"""
╔══════════════════════════════════════════════════════════════╗
║  JARVIS v4 — Détection d'intrus                               ║
║  Personnes (HOG) + visages connus/inconnus (LBPH) + scoring  ║
╚══════════════════════════════════════════════════════════════╝

Améliorations vs v3 (qui ne faisait que du "mouvement de pixels") :
  • Détection de SILHOUETTE HUMAINE (HOG) → ignore chat, rideau, ombre.
  • Reconnaissance de VISAGES CONNUS vs INCONNUS → un inconnu = vraie menace.
  • SCORE DE MENACE pondéré (mouvement < visage connu < personne < inconnu).
  • Confirmation multi-frames pour éliminer les faux positifs.

Tout fonctionne avec opencv-python seul. La reconnaissance faciale exploite
opencv-contrib-python (cv2.face) si présent ; sinon tout visage est traité
comme "inconnu" (sécurité par défaut).
"""

import re
import json
import time
import logging
import unicodedata
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger("JARVIS.detector")

# cv2.face fait partie d'opencv-contrib-python (optionnel)
HAS_FACE_RECOGNITION = hasattr(cv2, "face")


def safe_person_id(name: str) -> str:
    """Transforme un nom AFFICHÉ en identifiant de DOSSIER sûr.

    Empêche toute traversée de chemin : ../, chemins absolus, séparateurs,
    caractères spéciaux. Le résultat ne contient que [a-z0-9_-]. Renvoie '' si
    rien d'exploitable ne reste (l'appelant doit alors refuser l'enrôlement).
    """
    if not isinstance(name, str):
        return ""
    norm = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    norm = norm.lower().strip()
    norm = re.sub(r"[^a-z0-9]+", "_", norm).strip("_")
    norm = norm[:48]
    if not norm or norm in (".", "..") or norm.startswith("."):
        return ""
    return norm


class PersonDetector:
    """Détecteur de silhouette humaine basé sur HOG (aucun téléchargement requis)."""

    def __init__(self):
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detect(self, frame):
        """Retourne une liste de boîtes (x, y, w, h) pour chaque personne détectée."""
        # On réduit l'image : HOG est coûteux, et 640px suffit largement.
        h, w = frame.shape[:2]
        scale = 640 / w if w > 640 else 1.0
        small = cv2.resize(frame, (int(w * scale), int(h * scale))) if scale != 1.0 else frame
        rects, weights = self.hog.detectMultiScale(
            small, winStride=(8, 8), padding=(8, 8), scale=1.05
        )
        boxes = []
        for (x, y, bw, bh), weight in zip(rects, weights):
            if weight < 0.5:                 # filtre les détections faibles
                continue
            inv = 1.0 / scale
            boxes.append((int(x * inv), int(y * inv), int(bw * inv), int(bh * inv)))
        return boxes


class FaceBank:
    """Reconnaît les visages de confiance. Tout visage non reconnu = intrus.

    Durcissements :
      • `person_id` SÛR (safe_person_id) ≠ nom AFFICHÉ ≠ dossier d'images :
        impossible de sortir de known_dir via ../, chemin absolu, etc.
      • Enrôlement MULTI-IMAGES requis avant de considérer une identité fiable.
      • État « incertain » + score de confiance retournés par identify().
      • Suppression et révision (expiration) d'une identité.

    La reconnaissance faciale n'est JAMAIS la seule condition pour déclencher
    ou annuler une alerte (cf. policy/state_machine du Gardien).
    """

    MIN_SAMPLES = 3                         # enrôlement fiable = plusieurs images

    def __init__(self, known_dir: str = "security/known_faces",
                 model_file: str = "security/facebank.yml",
                 confidence_threshold: float = 70.0,
                 uncertain_margin: float = 15.0):
        self.known_dir = Path(known_dir).resolve()
        self.known_dir.mkdir(parents=True, exist_ok=True)
        self.model_file = Path(model_file)
        self.confidence_threshold = confidence_threshold   # LBPH: + bas = + sûr
        self.uncertain_margin = uncertain_margin           # zone grise → "incertain"
        self.labels = {}                                   # id -> person_id sûr
        self.display = {}                                  # person_id -> nom affiché
        self.cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.recognizer = None
        self.trained = False
        self._load_display()
        if HAS_FACE_RECOGNITION:
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
            self.train()

    # ── Chemins sûrs ───────────────────────────────────────────
    def _person_dir(self, person_id: str) -> Path:
        """Résout un dossier d'identité en RESTANT confiné dans known_dir."""
        target = (self.known_dir / person_id).resolve()
        if self.known_dir not in target.parents and target != self.known_dir:
            raise ValueError("Chemin hors de FaceBank (traversée bloquée)")
        return target

    def _meta_path(self) -> Path:
        return self.known_dir / "_display.json"

    def _load_display(self):
        try:
            self.display = json.loads(self._meta_path().read_text(encoding="utf-8"))
        except Exception:
            self.display = {}

    def _save_display(self):
        try:
            self._meta_path().write_text(
                json.dumps(self.display, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def detect_faces(self, gray):
        return self.cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))

    # ── Enrôlement (multi-images, nom sanitisé) ────────────────
    def enroll(self, name: str, gray_frame) -> str:
        """Ajoute UN échantillon de visage pour une identité. Plusieurs appels
        (>= MIN_SAMPLES) sont nécessaires pour une reconnaissance fiable."""
        person_id = safe_person_id(name)
        if not person_id:
            return "⛔ Nom d'enrôlement invalide (rejeté). Utilise des lettres/chiffres."
        try:
            person_dir = self._person_dir(person_id)
        except ValueError:
            return "⛔ Nom d'enrôlement refusé (chemin non autorisé)."
        faces = self.detect_faces(gray_frame)
        if len(faces) == 0:
            return "Aucun visage net détecté — recommence face caméra, bien éclairé."
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        roi = cv2.resize(gray_frame[y:y + h, x:x + w], (200, 200))
        person_dir.mkdir(parents=True, exist_ok=True)
        idx = len(list(person_dir.glob("*.png")))
        cv2.imwrite(str(person_dir / f"{idx}.png"), roi)
        self.display[person_id] = (name or person_id).strip()[:60]
        self._save_display()
        self.train()
        count = idx + 1
        if count < self.MIN_SAMPLES:
            return (f"📸 Échantillon {count}/{self.MIN_SAMPLES} pour « {self.display[person_id]} ». "
                    f"Ajoute encore {self.MIN_SAMPLES - count} prise(s) pour fiabiliser.")
        return f"✅ « {self.display[person_id]} » enrôlé ({count} échantillons)."

    def delete_identity(self, name: str) -> str:
        """Supprime une identité (dossier d'images + métadonnées)."""
        person_id = safe_person_id(name)
        if not person_id:
            return "⛔ Identité invalide."
        try:
            person_dir = self._person_dir(person_id)
        except ValueError:
            return "⛔ Chemin non autorisé."
        if not person_dir.exists():
            return "Identité introuvable."
        for f in person_dir.glob("*.png"):
            f.unlink()
        try:
            person_dir.rmdir()
        except OSError:
            pass
        self.display.pop(person_id, None)
        self._save_display()
        self.train()
        return f"🗑️ Identité « {name} » supprimée."

    def list_identities(self) -> list:
        out = []
        for person_dir in sorted(p for p in self.known_dir.iterdir() if p.is_dir()):
            n = len(list(person_dir.glob("*.png")))
            out.append({"person_id": person_dir.name,
                        "display": self.display.get(person_dir.name, person_dir.name),
                        "samples": n, "reliable": n >= self.MIN_SAMPLES})
        return out

    def train(self) -> bool:
        if not HAS_FACE_RECOGNITION:
            return False
        images, ids, self.labels = [], [], {}
        next_id = 0
        for person_dir in sorted(self.known_dir.iterdir()):
            if not person_dir.is_dir():
                continue
            samples = list(person_dir.glob("*.png"))
            if not samples:
                continue
            self.labels[next_id] = person_dir.name
            for img_path in samples:
                img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    images.append(cv2.resize(img, (200, 200)))
                    ids.append(next_id)
            next_id += 1
        if not images:
            self.trained = False
            return False
        self.recognizer.train(images, np.array(ids))
        self.trained = True
        logger.info(f"🧠 FaceBank entraînée: {[self.display.get(v, v) for v in self.labels.values()]}")
        return True

    def identify(self, gray, face_box):
        """Renvoie (nom, confiance). nom ∈ {nom_affiché, 'incertain', 'inconnu'}.

        Un visage en limite de seuil est marqué « incertain » plutôt que reconnu
        à tort sur un seul échantillon peu fiable."""
        if not (HAS_FACE_RECOGNITION and self.trained):
            return ("inconnu", 0.0)
        x, y, w, h = face_box
        roi = cv2.resize(gray[y:y + h, x:x + w], (200, 200))
        label, distance = self.recognizer.predict(roi)
        person_id = self.labels.get(label, "")
        n_samples = len(list((self.known_dir / person_id).glob("*.png"))) if person_id else 0
        if distance <= self.confidence_threshold and n_samples >= self.MIN_SAMPLES:
            return (self.display.get(person_id, person_id), distance)
        if distance <= self.confidence_threshold + self.uncertain_margin:
            return ("incertain", distance)
        return ("inconnu", distance)


class BehaviorAnalyzer:
    """Analyse COMPORTEMENTALE (inspirée Veesion) — la menace vient du
    comportement, pas seulement de l'identité.

    Détecte des schémas suspects à partir du suivi temporel :
      • rôdage / loitering   : personne présente trop longtemps
      • mouvements erratiques: forte variance de mouvement (agitation)
      • présence nocturne    : personne détectée aux heures sensibles
      • approche rapide      : silhouette qui grossit vite (se rue vers la cam)
    """

    def __init__(self, loiter_seconds: float = 18.0,
                 night_hours=range(0, 6), absent_grace: float = 2.0):
        self.loiter_seconds = loiter_seconds
        self.night_hours = set(night_hours)
        self.absent_grace = absent_grace   # tolérance avant de considérer un départ
        self.person_since = None           # timestamp d'apparition continue
        self.last_present = 0.0            # dernière frame AVEC personne
        self.motion_window = []            # historique court de motion_ratio
        self.last_area = 0

    def update(self, persons, motion_ratio: float, now: float,
               hour: int = None) -> tuple:
        """Retourne (behaviors, bonus_score).

        IMPORTANT : `persons=None` signifie « la détection lourde n'a pas tourné
        cette frame » → on NE réinitialise PAS le suivi de présence (bug v4).
        `persons=[]` signifie « détection effectuée, personne absente ».
        """
        behaviors, bonus = [], 0
        detection_ran = persons is not None
        has_person = bool(persons)

        if has_person:
            if self.person_since is None:
                self.person_since = now
            self.last_present = now
        elif detection_ran:
            # Détection effectuée sans personne : on attend la grâce avant reset,
            # pour ne pas perdre le suivi sur une frame ratée isolée.
            if self.person_since is not None and (now - self.last_present) > self.absent_grace:
                self.person_since = None
                self.last_area = 0
        # persons is None → on conserve l'état tel quel (frame sans détection).

        active = self.person_since is not None
        if active:
            dwell = now - self.person_since
            if dwell >= self.loiter_seconds:
                behaviors.append(f"RÔDAGE ({int(dwell)}s)")
                bonus += 2
            if has_person:
                area = max((w * h for (_, _, w, h) in persons), default=0)
                if self.last_area and area > self.last_area * 1.7:
                    behaviors.append("APPROCHE RAPIDE")
                    bonus += 1
                self.last_area = area

        # Mouvements erratiques : variance élevée de la fenêtre de mouvement
        self.motion_window.append(motion_ratio)
        self.motion_window = self.motion_window[-30:]
        if len(self.motion_window) >= 10:
            mean = sum(self.motion_window) / len(self.motion_window)
            var = sum((x - mean) ** 2 for x in self.motion_window) / len(self.motion_window)
            if var > 0.0015 and active:
                behaviors.append("MOUVEMENTS ERRATIQUES")
                bonus += 1

        # Présence nocturne
        h = hour if hour is not None else 0
        if active and h in self.night_hours:
            behaviors.append("PRÉSENCE NOCTURNE")
            bonus += 2

        return behaviors, bonus


# ── Scoring de menace ─────────────────────────────────────────
THREAT_WEIGHTS = {
    "mouvement": 1,
    "visage_connu": 0,        # une tête connue n'est pas une menace
    "visage_inconnu": 3,
    "personne": 2,
}


def threat_level(score: int) -> str:
    if score >= 8:
        return "extrême"
    if score >= 5:
        return "élevé"
    if score >= 2:
        return "moyen"
    return "bas"
