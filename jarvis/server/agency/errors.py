"""
Classification structurée des erreurs d'exécution des étapes (v5.7 incrément 2).

Toutes les exceptions ne se valent pas : une panne réseau/temporaire doit être
retentée ; une erreur permanente (validation, permission, config) doit bloquer
ou échouer proprement ; un refus d'approbation ne doit JAMAIS être retenté
automatiquement pour contourner l'utilisateur.
"""
from __future__ import annotations

import re


class ErrorType:
    TRANSIENT_NETWORK = "TRANSIENT_NETWORK"
    TRANSIENT_TIMEOUT = "TRANSIENT_TIMEOUT"
    TRANSIENT_RATE_LIMIT = "TRANSIENT_RATE_LIMIT"
    TRANSIENT_SERVICE_UNAVAILABLE = "TRANSIENT_SERVICE_UNAVAILABLE"
    TRANSIENT_WORKER_LOST = "TRANSIENT_WORKER_LOST"
    PERMANENT_VALIDATION = "PERMANENT_VALIDATION"
    PERMANENT_PERMISSION = "PERMANENT_PERMISSION"
    PERMANENT_CONFIGURATION = "PERMANENT_CONFIGURATION"
    PERMANENT_UNSUPPORTED = "PERMANENT_UNSUPPORTED"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    CANCELLED_BY_USER = "CANCELLED_BY_USER"


TRANSIENT = {
    ErrorType.TRANSIENT_NETWORK, ErrorType.TRANSIENT_TIMEOUT,
    ErrorType.TRANSIENT_RATE_LIMIT, ErrorType.TRANSIENT_SERVICE_UNAVAILABLE,
    ErrorType.TRANSIENT_WORKER_LOST,
}
PERMANENT = {
    ErrorType.PERMANENT_VALIDATION, ErrorType.PERMANENT_PERMISSION,
    ErrorType.PERMANENT_CONFIGURATION, ErrorType.PERMANENT_UNSUPPORTED,
}


def is_transient(error_type: str) -> bool:
    return error_type in TRANSIENT


def is_permanent(error_type: str) -> bool:
    return error_type in PERMANENT


def needs_human(error_type: str) -> bool:
    return error_type in (ErrorType.HUMAN_REQUIRED, ErrorType.CANCELLED_BY_USER)


# Motifs textuels (utile quand l'exécuteur renvoie une chaîne d'erreur/résultat).
_RATE = re.compile(r"\b(rate.?limit|429|too many requests|quota)\b", re.I)
_TIMEOUT = re.compile(r"\b(timed?.?out|timeout|deadline)\b", re.I)
_UNAVAIL = re.compile(r"\b(unavailable|503|502|504|connection refused|"
                      r"ollama|cannot connect|not reachable|max retries)\b", re.I)
_NETWORK = re.compile(r"\b(network|dns|temporarily|reset by peer|"
                      r"connection (?:aborted|error))\b", re.I)
_PERMISSION = re.compile(r"\b(403|401|permission denied|unauthorized|forbidden|"
                         r"approbation|approval)\b", re.I)
_VALIDATION = re.compile(r"\b(400|422|invalid|validation|schema|malformed|"
                         r"bad request)\b", re.I)
_CONFIG = re.compile(r"\b(config|missing (?:key|credential|env)|not configured|"
                     r"clé absente|introuvable)\b", re.I)
_UNSUPPORTED = re.compile(r"\b(not supported|unsupported|not implemented|"
                          r"501|non supporté)\b", re.I)
_APPROVAL_REJECT = re.compile(r"\b(refus|rejected|denied by user|approbation refusée)\b", re.I)


def classify_error(exc: BaseException | None = None, text: str = "") -> str:
    """Retourne un ErrorType. On combine le TYPE d'exception et un motif textuel."""
    blob = text or ""
    if exc is not None:
        blob = f"{type(exc).__name__}: {exc} {blob}"

    # Types d'exception réseau bien connus (sans importer requests ici).
    name = type(exc).__name__ if exc is not None else ""
    if name in ("Timeout", "ConnectTimeout", "ReadTimeout") or _TIMEOUT.search(blob):
        return ErrorType.TRANSIENT_TIMEOUT
    if _RATE.search(blob):
        return ErrorType.TRANSIENT_RATE_LIMIT
    if name in ("ConnectionError", "ConnectionResetError", "ConnectionRefusedError",
                "NewConnectionError", "socket.gaierror", "gaierror") or _NETWORK.search(blob):
        return ErrorType.TRANSIENT_NETWORK
    if _UNAVAIL.search(blob):
        return ErrorType.TRANSIENT_SERVICE_UNAVAILABLE

    if _APPROVAL_REJECT.search(blob):
        return ErrorType.HUMAN_REQUIRED
    if _PERMISSION.search(blob):
        return ErrorType.PERMANENT_PERMISSION
    if _VALIDATION.search(blob) or name in ("ValueError", "ValidationError", "KeyError"):
        return ErrorType.PERMANENT_VALIDATION
    if _CONFIG.search(blob):
        return ErrorType.PERMANENT_CONFIGURATION
    if _UNSUPPORTED.search(blob) or name in ("NotImplementedError",):
        return ErrorType.PERMANENT_UNSUPPORTED

    # Par défaut : on considère l'erreur comme temporaire (on retente prudemment)
    # plutôt que d'échouer définitivement une mission sur une exception inconnue.
    return ErrorType.TRANSIENT_SERVICE_UNAVAILABLE
