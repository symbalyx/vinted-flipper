"""
Suivi temporel PERSISTANT des personnes.

Corrige le bug historique : la détection lourde (HOG/ONNX) ne tourne pas à
chaque frame. Le tracker NE DOIT PAS être remis à zéro pendant les frames sans
détection. On distingue donc explicitement :

    update(detections=None)  → « aucune détection n'a tourné cette frame »
                               (on conserve et on vieillit les pistes)
    update(detections=[])    → « la détection a tourné, personne trouvée »
                               (on peut faire disparaître les pistes périmées)

Chaque piste expose : id temporaire, boîte englobante, première/dernière
apparition, durée de présence, trajectoire, aire lissée, zone, confiance,
nombre de confirmations.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

Box = Tuple[int, int, int, int]   # x, y, w, h


def _iou(a: Box, b: Box) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1, y1 = max(ax, bx), max(ay, by)
    x2, y2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    iw, ih = max(0, x2 - x1), max(0, y2 - y1)
    inter = iw * ih
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


@dataclass
class PersonTrack:
    id: str
    box: Box
    first_seen: float
    last_seen: float
    confidence: float = 0.0
    confirmations: int = 1
    smoothed_area: float = 0.0
    trajectory: List[Tuple[float, float]] = field(default_factory=list)
    zone: str = "porch"
    missed: int = 0                     # frames de détection consécutives sans match

    @property
    def dwell(self) -> float:
        return max(0.0, self.last_seen - self.first_seen)

    def center_norm(self, frame_w: int, frame_h: int) -> Tuple[float, float]:
        x, y, w, h = self.box
        return ((x + w / 2) / max(1, frame_w), (y + h / 2) / max(1, frame_h))

    def to_dict(self) -> dict:
        return {
            "id": self.id, "box": list(self.box), "dwell": round(self.dwell, 1),
            "confirmations": self.confirmations, "confidence": round(self.confidence, 2),
            "zone": self.zone, "smoothed_area": round(self.smoothed_area, 1),
            "first_seen": self.first_seen, "last_seen": self.last_seen,
        }


class PersonTracker:
    """Suivi multi-personnes simple par IoU (sans dépendance lourde)."""

    def __init__(self, iou_threshold: float = 0.3, max_missed: int = 5,
                 ttl_seconds: float = 3.0, area_smooth: float = 0.6):
        self.iou_threshold = iou_threshold
        self.max_missed = max_missed       # disparition après N frames de détection ratées
        self.ttl_seconds = ttl_seconds     # ou après ce délai sans aucune mise à jour
        self.area_smooth = area_smooth
        self.tracks: Dict[str, PersonTrack] = {}

    def update(self, detections: Optional[List[Box]], now: float = None,
               zone_map=None, frame_w: int = 640, frame_h: int = 480,
               confidences: Optional[List[float]] = None) -> List[PersonTrack]:
        """
        detections=None  → aucune détection cette frame : on conserve les pistes
                           (on les vieillit seulement par TTL temporel).
        detections=[]    → détection effectuée, rien vu : on incrémente 'missed'.
        """
        now = now or time.time()

        if detections is None:
            # Pas de détection lourde cette frame → on NE réinitialise rien.
            self._expire_by_time(now)
            return self.active_tracks(now)

        confidences = confidences or [1.0] * len(detections)
        unmatched = set(self.tracks)
        used = set()

        for det, conf in zip(detections, confidences):
            best_id, best_iou = None, self.iou_threshold
            for tid, tr in self.tracks.items():
                if tid in used:
                    continue
                score = _iou(tr.box, det)
                if score >= best_iou:
                    best_id, best_iou = tid, score
            if best_id is not None:
                tr = self.tracks[best_id]
                tr.box = det
                tr.last_seen = now
                tr.confidence = conf
                tr.confirmations += 1
                tr.missed = 0
                area = det[2] * det[3]
                tr.smoothed_area = (self.area_smooth * tr.smoothed_area
                                    + (1 - self.area_smooth) * area) if tr.smoothed_area else area
                cx, cy = (det[0] + det[2] / 2) / max(1, frame_w), (det[1] + det[3] / 2) / max(1, frame_h)
                tr.trajectory.append((round(cx, 3), round(cy, 3)))
                tr.trajectory = tr.trajectory[-50:]
                if zone_map is not None:
                    tr.zone = zone_map.classify(cx, cy)
                used.add(best_id)
                unmatched.discard(best_id)
            else:
                tid = uuid.uuid4().hex[:8]
                cx, cy = (det[0] + det[2] / 2) / max(1, frame_w), (det[1] + det[3] / 2) / max(1, frame_h)
                zone = zone_map.classify(cx, cy) if zone_map is not None else "porch"
                self.tracks[tid] = PersonTrack(
                    id=tid, box=det, first_seen=now, last_seen=now,
                    confidence=conf, smoothed_area=det[2] * det[3],
                    trajectory=[(round(cx, 3), round(cy, 3))], zone=zone)
                used.add(tid)

        # Pistes non matchées : la détection a tourné mais ne les a pas revues.
        for tid in unmatched:
            self.tracks[tid].missed += 1

        # Suppression : trop de frames de détection ratées.
        for tid in [t for t, tr in self.tracks.items() if tr.missed > self.max_missed]:
            del self.tracks[tid]

        return self.active_tracks(now)

    def _expire_by_time(self, now: float):
        for tid in [t for t, tr in self.tracks.items()
                    if now - tr.last_seen > self.ttl_seconds]:
            del self.tracks[tid]

    def active_tracks(self, now: float = None) -> List[PersonTrack]:
        now = now or time.time()
        return [tr for tr in self.tracks.values()
                if now - tr.last_seen <= self.ttl_seconds]

    def reset(self):
        self.tracks.clear()
