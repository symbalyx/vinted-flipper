"""
Interface enfichable de détection de personnes (Étape 6).

Objectif : garder **HOG** comme détecteur léger par défaut (aucun téléchargement,
installation minimale), tout en permettant de brancher un détecteur **ONNX
moderne** (ex. YOLOv8-person) sans casser l'installation minimale.

Le backend ONNX est optionnel et à **dégradation gracieuse** : sans
`onnxruntime` ni modèle fourni (`GUARDIAN_ONNX_MODEL`), la fabrique retombe
automatiquement sur HOG.

Inspiration de conception (import-guard + fallback) : projet open-source
`thevickypedia/Jarvis` (licence MIT) — voir CREDITS.md. Le post-traitement
YOLO ci-dessous est une implémentation propre (numpy + cv2.dnn.NMSBoxes),
testable indépendamment d'un vrai modèle.
"""

import os
import logging

import numpy as np

logger = logging.getLogger("JARVIS.detectors")


class DetectorBackend:
    """Contrat commun : detect(frame) -> [(x, y, w, h), …]."""
    name = "base"

    def detect(self, frame):
        raise NotImplementedError

    def available(self) -> bool:
        return True


class HOGDetector(DetectorBackend):
    """Détecteur HOG par défaut (délègue à PersonDetector, installation minimale)."""
    name = "hog"

    def __init__(self):
        from .detector import PersonDetector
        self._impl = PersonDetector()

    def detect(self, frame):
        return self._impl.detect(frame)


def postprocess_yolo(output, orig_w, orig_h, input_size=640,
                     conf_threshold=0.4, iou_threshold=0.5):
    """Décode une sortie YOLOv8 (1, 84, N) → boîtes de PERSONNES (classe 0).

    Fonction PURE et testable (aucun runtime requis). Retourne une liste de
    (x, y, w, h) en coordonnées de l'image d'origine.
    """
    import cv2

    arr = np.asarray(output, dtype=np.float32)
    if arr.ndim == 3:
        arr = arr[0]
    # YOLOv8 sort (features, N) avec features = 4 + nb_classes (84 pour COCO).
    # On veut (N, features) : on transpose si les features sont en lignes.
    if arr.shape[0] in (84, 85) and arr.shape[0] != arr.shape[1]:
        arr = arr.T
    if arr.shape[1] < 5:
        return []

    boxes, scores = [], []
    gain_x, gain_y = orig_w / input_size, orig_h / input_size
    # Colonnes 0..3 = cx,cy,w,h ; 4.. = scores de classes (classe 0 = personne).
    class_scores = arr[:, 4:]
    person_conf = class_scores[:, 0] if class_scores.shape[1] else np.zeros(len(arr))
    for i, pc in enumerate(person_conf):
        if pc < conf_threshold:
            continue
        cx, cy, w, h = arr[i, 0], arr[i, 1], arr[i, 2], arr[i, 3]
        x = (cx - w / 2) * gain_x
        y = (cy - h / 2) * gain_y
        boxes.append([int(x), int(y), int(w * gain_x), int(h * gain_y)])
        scores.append(float(pc))
    if not boxes:
        return []
    idxs = cv2.dnn.NMSBoxes(boxes, scores, conf_threshold, iou_threshold)
    if idxs is None or len(idxs) == 0:
        return []
    idxs = np.array(idxs).flatten()
    return [tuple(boxes[i]) for i in idxs]


class OnnxPersonDetector(DetectorBackend):
    """Détecteur ONNX moderne (optionnel). Requiert `onnxruntime` + un modèle
    YOLOv8-person (`GUARDIAN_ONNX_MODEL`). Sinon indisponible → fallback HOG.

    ⚠️ Chemin fonctionnel mais NON testé en CI (nécessite un modèle .onnx réel).
    Le décodage (postprocess_yolo) est, lui, couvert par des tests.
    """
    name = "onnx"

    def __init__(self, model_path: str = None, input_size: int = 640,
                 conf_threshold: float = 0.4):
        self.model_path = model_path or os.getenv("GUARDIAN_ONNX_MODEL", "")
        self.input_size = input_size
        self.conf_threshold = conf_threshold
        self._sess = None

    def available(self) -> bool:
        if not self.model_path or not os.path.exists(self.model_path):
            return False
        try:
            import onnxruntime  # noqa: F401
        except Exception:
            return False
        return True

    def _ensure_session(self):
        if self._sess is None:
            import onnxruntime as ort
            self._sess = ort.InferenceSession(
                self.model_path, providers=["CPUExecutionProvider"])

    def detect(self, frame):
        import cv2
        self._ensure_session()
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(
            frame, 1 / 255.0, (self.input_size, self.input_size),
            swapRB=True, crop=False)
        inp = self._sess.get_inputs()[0].name
        out = self._sess.run(None, {inp: blob})[0]
        return postprocess_yolo(out, w, h, self.input_size, self.conf_threshold)


def get_person_detector(prefer: str = None) -> DetectorBackend:
    """Fabrique : renvoie le backend demandé s'il est disponible, sinon HOG.

    `prefer` (ou GUARDIAN_DETECTOR) ∈ {hog, onnx}. Fail-safe : jamais d'exception
    à l'installation minimale — on retombe toujours sur HOG.
    """
    choice = (prefer or os.getenv("GUARDIAN_DETECTOR", "hog")).lower()
    if choice == "onnx":
        det = OnnxPersonDetector()
        if det.available():
            logger.info("🧠 Détecteur ONNX moderne activé (%s).", det.model_path)
            return det
        logger.warning("Détecteur ONNX indemandé mais indisponible (modèle/onnxruntime) "
                       "→ fallback HOG.")
    return HOGDetector()
