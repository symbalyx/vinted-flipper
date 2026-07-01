"""
Appairage d'un appareil Gardien (vieux téléphone / tablette à l'entrée).

Un appareil Gardien obtient un jeton RÉVOCABLE à permissions LIMITÉES : il peut
envoyer des images/transcriptions au Gardien et déclencher la coupure, mais
n'a JAMAIS les permissions de contrôle PC ni le protocole d'urgence complet.

Flux : le propriétaire génère un code d'appairage temporaire (6 chiffres) depuis
l'app authentifiée ; l'appareil l'échange contre un jeton de session limité.
"""

import time
import secrets
import hashlib
import threading


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


GUARDIAN_DEVICE_SCOPES = ("guardian:ingest", "guardian:siren_stop", "guardian:status")
# Explicitement INTERDIT aux appareils Gardien :
FORBIDDEN_DEVICE_SCOPES = ("pc:*", "emergency:*", "system:*", "files:*")


class DevicePairing:
    def __init__(self, code_ttl: float = 300.0):
        self.code_ttl = code_ttl
        self._codes = {}          # code -> (expires, name)
        self._devices = {}        # device_id -> {name, token_hash, scopes, created, revoked}
        self._lock = threading.Lock()

    def create_code(self, name: str = "Appareil Gardien") -> dict:
        code = f"{secrets.randbelow(10**6):06d}"
        with self._lock:
            self._codes[code] = (time.time() + self.code_ttl, name[:40])
        return {"code": code, "expires_in": int(self.code_ttl), "name": name[:40]}

    def redeem(self, code: str, device_name: str = "") -> dict:
        with self._lock:
            entry = self._codes.pop(code, None)
        if not entry:
            return {"ok": False, "error": "Code invalide"}
        expires, name = entry
        if time.time() > expires:
            return {"ok": False, "error": "Code expiré"}
        device_id = secrets.token_urlsafe(8)
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._devices[device_id] = {
                "name": device_name[:40] or name, "token_hash": _hash(token),
                "scopes": list(GUARDIAN_DEVICE_SCOPES), "created": time.time(),
                "revoked": False, "last_seen": time.time()}
        return {"ok": True, "device_id": device_id, "token": token,
                "scopes": list(GUARDIAN_DEVICE_SCOPES),
                "name": device_name[:40] or name}

    def verify(self, device_id: str, token: str) -> bool:
        with self._lock:
            dev = self._devices.get(device_id)
            if not dev or dev["revoked"]:
                return False
            ok = secrets.compare_digest(dev["token_hash"], _hash(token or ""))
            if ok:
                dev["last_seen"] = time.time()
            return ok

    def has_scope(self, device_id: str, scope: str) -> bool:
        with self._lock:
            dev = self._devices.get(device_id)
            return bool(dev and not dev["revoked"] and scope in dev["scopes"])

    def revoke(self, device_id: str) -> bool:
        with self._lock:
            dev = self._devices.get(device_id)
            if not dev:
                return False
            dev["revoked"] = True
            return True

    def list_devices(self) -> list:
        with self._lock:
            return [{"device_id": k, "name": v["name"], "revoked": v["revoked"],
                     "created": v["created"], "last_seen": v["last_seen"],
                     "scopes": v["scopes"]} for k, v in self._devices.items()]
