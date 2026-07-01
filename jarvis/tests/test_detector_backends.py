"""Interface enfichable de détection (HOG par défaut, ONNX optionnel)."""
import numpy as np

from security_mod.detectors import (
    get_person_detector, HOGDetector, OnnxPersonDetector, postprocess_yolo)


def test_factory_defaults_to_hog():
    det = get_person_detector()
    assert isinstance(det, HOGDetector) and det.name == "hog"


def test_factory_onnx_falls_back_when_unavailable(monkeypatch):
    # Aucun modèle fourni → ONNX indisponible → fallback HOG (jamais d'exception).
    monkeypatch.delenv("GUARDIAN_ONNX_MODEL", raising=False)
    det = get_person_detector(prefer="onnx")
    assert isinstance(det, HOGDetector)


def test_onnx_available_false_without_model():
    assert OnnxPersonDetector(model_path="").available() is False
    assert OnnxPersonDetector(model_path="/does/not/exist.onnx").available() is False


def test_postprocess_yolo_decodes_person_box():
    # Sortie YOLOv8 synthétique (1, 84, 2) : 1 personne forte, 1 sous le seuil.
    out = np.zeros((1, 84, 2), dtype=np.float32)
    # Détection 0 : centre (320,320), taille 100x200, score personne 0.9
    out[0, 0, 0], out[0, 1, 0], out[0, 2, 0], out[0, 3, 0] = 320, 320, 100, 200
    out[0, 4, 0] = 0.9
    # Détection 1 : score 0.1 (rejetée)
    out[0, 0, 1], out[0, 1, 1], out[0, 2, 1], out[0, 3, 1] = 10, 10, 20, 40
    out[0, 4, 1] = 0.1
    boxes = postprocess_yolo(out, orig_w=640, orig_h=640, input_size=640, conf_threshold=0.4)
    assert len(boxes) == 1
    x, y, w, h = boxes[0]
    assert w == 100 and h == 200 and x == 270 and y == 220   # cx-w/2, cy-h/2


def test_postprocess_yolo_empty_when_all_below_threshold():
    out = np.zeros((1, 84, 3), dtype=np.float32)
    out[0, 4, :] = 0.05
    assert postprocess_yolo(out, 640, 640) == []


def test_hog_detector_runs_on_blank_frame():
    det = HOGDetector()
    boxes = det.detect(np.zeros((240, 320, 3), dtype=np.uint8))
    assert isinstance(boxes, list)   # image vide → aucune personne, pas d'erreur
