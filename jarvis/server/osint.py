"""
╔══════════════════════════════════════════════════════════════╗
║  JARVIS — OSINT d'INFRASTRUCTURE (défensif)                   ║
╚══════════════════════════════════════════════════════════════╝

Périmètre volontairement limité à l'OSINT d'INFRASTRUCTURE : adresses IP,
domaines, hachages. Utile pour enrichir une alerte réseau (« quelle est cette IP
qui frappe mon serveur ? »), pas pour cibler des personnes.

⚠️ Interdit par conception : recherche de personnes, réseaux sociaux, visages,
identité — c'est de la surveillance/doxxing, hors de ce module.

Local-first : la géolocalisation d'IP est OPTIONNELLE et désactivée par défaut
(`OSINT_GEO_URL` vide). WHOIS/DNS utilisent des résolveurs standards, avec
dégradation gracieuse (jamais d'exception non gérée, jamais de secret exposé).
"""

import os
import re
import socket
import ipaddress
import logging

logger = logging.getLogger("JARVIS.osint")

_TIMEOUT = float(os.getenv("OSINT_TIMEOUT", "5"))
_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?!-)[a-z0-9-]{1,63}(?<!-)(\.[a-z0-9-]{1,63})+$", re.I)
_HASHES = {32: "md5", 40: "sha1", 64: "sha256"}


# ── Classification (pur, testable) ─────────────────────────────
def classify_ip(ip: str) -> dict:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return {"valid": False}
    return {
        "valid": True, "version": addr.version, "ip": str(addr),
        "private": addr.is_private, "loopback": addr.is_loopback,
        "reserved": addr.is_reserved or addr.is_link_local or addr.is_multicast,
        "global": addr.is_global,
    }


def is_public_ip(ip: str) -> bool:
    c = classify_ip(ip)
    return bool(c.get("valid") and c.get("global"))


def hash_type(value: str) -> str:
    v = (value or "").strip().lower()
    if re.fullmatch(r"[0-9a-f]+", v) and len(v) in _HASHES:
        return _HASHES[len(v)]
    return ""


def is_domain(value: str) -> bool:
    return bool(_DOMAIN_RE.match((value or "").strip()))


def query_type(q: str) -> str:
    """Détermine le type d'indicateur : ip | domain | hash | inconnu."""
    q = (q or "").strip()
    if not q:
        return "inconnu"
    if classify_ip(q).get("valid"):
        return "ip"
    if hash_type(q):
        return "hash"
    if is_domain(q):
        return "domain"
    return "inconnu"


# ── Réseau (dégradation gracieuse) ─────────────────────────────
def reverse_dns(ip: str) -> str:
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return ""


def resolve_domain(domain: str) -> list:
    """Résout un domaine en n'exposant QUE des adresses publiques (anti-SSRF).

    Un domaine qui résout vers une IP privée/loopback/réservée est ignoré (on ne
    divulgue pas d'infrastructure interne et on n'ouvre aucune connexion vers elle).
    """
    try:
        infos = socket.getaddrinfo(domain, None)
    except Exception:
        return []
    out = set()
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if not (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            out.add(addr)
    return sorted(out)


def whois_query(query: str, server: str = "whois.iana.org") -> str:
    """WHOIS brut via le port 43 (sans clé d'API). Dégradation gracieuse."""
    try:
        with socket.create_connection((server, 43), timeout=_TIMEOUT) as s:
            s.sendall((query + "\r\n").encode())
            data = b""
            while len(data) < 65536:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
        return data.decode("utf-8", "replace")
    except Exception as e:
        return f"(whois indisponible: {e})"


def geolocate_ip(ip: str, fetch=None) -> dict:
    """Géolocalisation OPTIONNELLE via un fournisseur configuré (OSINT_GEO_URL).
    Désactivée par défaut (local-first). `fetch` injectable pour les tests."""
    url_tmpl = os.getenv("OSINT_GEO_URL", "")
    if not url_tmpl or not is_public_ip(ip):
        return {}
    try:
        import requests
        getter = fetch or (lambda u: requests.get(u, timeout=_TIMEOUT).json())
        data = getter(url_tmpl.replace("{ip}", ip))
        lat = data.get("lat") or data.get("latitude")
        lon = data.get("lon") or data.get("longitude")
        if lat is None or lon is None:
            return {}
        return {"lat": float(lat), "lon": float(lon),
                "country": data.get("country") or data.get("country_name") or "",
                "city": data.get("city") or "", "org": data.get("org") or data.get("isp") or ""}
    except Exception:
        return {}


# ── Point d'entrée ─────────────────────────────────────────────
def lookup(query: str) -> dict:
    """Dispatch OSINT infra. Ne cible QUE IP/domaine/hachage."""
    q = (query or "").strip()
    kind = query_type(q)
    if kind == "inconnu":
        return {"ok": False, "type": "inconnu",
                "error": "Indicateur non reconnu (IP, domaine ou hachage attendu)."}

    if kind == "ip":
        info = classify_ip(q)
        result = {"ok": True, "type": "ip", **info}
        if not info.get("global"):
            result["note"] = "IP privée/réservée : pas de recherche externe (local)."
            return result
        result["reverse_dns"] = reverse_dns(q)
        result["geo"] = geolocate_ip(q)          # {} si non configuré
        result["whois"] = whois_query(q, "whois.arin.net")[:4000]
        return result

    if kind == "domain":
        return {"ok": True, "type": "domain", "domain": q.lower(),
                "addresses": resolve_domain(q),
                "whois": whois_query(q)[:4000]}

    if kind == "hash":
        return {"ok": True, "type": "hash", "algo": hash_type(q), "hash": q.lower(),
                "note": "Comparer à une base de réputation (VirusTotal/MISP) via ta clé serveur."}
    return {"ok": False, "type": kind, "error": "non supporté"}
