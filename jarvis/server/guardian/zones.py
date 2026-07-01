"""
Zones configurables du champ de la caméra.

Types de zones :
  • porch   — porche / zone d'accueil (parler poliment y est normal)
  • door    — contact avec la porte (déclencheur fort)
  • path    — chemin d'accès
  • ignore  — zone à ne jamais traiter (ex. arbre qui bouge)
  • private — zone privée à protéger fortement
  • public  — masque de la voie publique : on N'ENGAGE PAS les passants

Les coordonnées sont normalisées (0..1) pour être indépendantes de la
résolution. Un point est dans une zone si le centre du sujet y tombe.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

Point = Tuple[float, float]

ZONE_TYPES = ("porch", "door", "path", "ignore", "private", "public")


def _point_in_poly(x: float, y: float, poly: List[Point]) -> bool:
    """Ray casting. poly = liste de (x,y) normalisés."""
    if len(poly) < 3:
        return False
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi):
            inside = not inside
        j = i
    return inside


@dataclass
class Zone:
    name: str
    kind: str
    polygon: List[Point] = field(default_factory=list)

    def contains(self, x: float, y: float) -> bool:
        return _point_in_poly(x, y, self.polygon)


class ZoneMap:
    """Ensemble de zones. Tolère une config vide (tout est 'porch' par défaut)."""

    def __init__(self, zones: List[Zone] = None):
        self.zones = zones or []

    @classmethod
    def from_config(cls, cfg) -> "ZoneMap":
        zones = []
        for z in (cfg or []):
            kind = z.get("kind")
            if kind not in ZONE_TYPES:
                continue
            poly = [(float(p[0]), float(p[1])) for p in z.get("polygon", [])
                    if isinstance(p, (list, tuple)) and len(p) == 2]
            zones.append(Zone(name=z.get("name", kind), kind=kind, polygon=poly))
        return cls(zones)

    def classify(self, x: float, y: float) -> str:
        """Renvoie le type de zone du point. Priorité : ignore/public > door >
        private > path > porch. Hors de toute zone définie ⇒ 'porch' (neutre)."""
        hits = [z.kind for z in self.zones if z.contains(x, y)]
        for prio in ("ignore", "public", "door", "private", "path", "porch"):
            if prio in hits:
                return prio
        return "porch"

    def is_masked(self, x: float, y: float) -> bool:
        """True si le point est dans une zone à ignorer (ignore) ou voie publique."""
        z = self.classify(x, y)
        return z in ("ignore", "public")
