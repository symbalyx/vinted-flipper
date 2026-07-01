"""
╔══════════════════════════════════════════════════════════════╗
║  JARVIS v4 — Recherche Web                                    ║
║  DuckDuckGo (aucune clé API) + lecture de page web           ║
╚══════════════════════════════════════════════════════════════╝

Zéro dépendance en plus (juste `requests`, déjà présent) et zéro clé API.
Deux capacités :
  • search(query)   → top résultats web (titre + extrait + url)
  • read_page(url)  → texte d'une page (pour que l'IA la résume)

Stratégie en cascade :
  1. DuckDuckGo Instant Answer (réponses factuelles directes)
  2. DuckDuckGo Lite (HTML léger, facile à parser)
  3. DuckDuckGo HTML (repli)
"""

import re
import html
import socket
import logging
import ipaddress
from urllib.parse import urlparse

import requests

logger = logging.getLogger("JARVIS.websearch")


def _ip_is_blocked(ip: ipaddress._BaseAddress) -> bool:
    return bool(
        ip.is_private or ip.is_loopback or ip.is_link_local
        or ip.is_reserved or ip.is_multicast or ip.is_unspecified
        or (ip.version == 6 and getattr(ip, "ipv4_mapped", None) is not None
            and _ip_is_blocked(ip.ipv4_mapped)))


def validate_url_for_fetch(url: str):
    """Anti-SSRF strict. Retourne (ok: bool, raison: str, ips: list[str]).

    Refuse : schéma ≠ http/https, identifiants intégrés (user:pass@), hôte absent,
    IP privée/loopback/link-local/réservée/multicast/unspecified, 169.254.169.254
    (link-local → métadonnées cloud), ::1, ainsi que les hôtes qui NE résolvent
    pas. Toutes les adresses résolues doivent être publiques.
    """
    try:
        u = urlparse(url)
    except Exception:
        return False, "URL illisible", []
    if u.scheme not in ("http", "https"):
        return False, "schéma non autorisé", []
    if u.username or u.password or "@" in (u.netloc or ""):
        return False, "identifiants intégrés interdits", []
    host = u.hostname
    if not host:
        return False, "hôte absent", []
    try:
        infos = socket.getaddrinfo(host, u.port or (443 if u.scheme == "https" else 80),
                                   proto=socket.IPPROTO_TCP)
    except Exception:
        return False, "résolution DNS impossible", []
    ips = []
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False, "adresse invalide", []
        if _ip_is_blocked(ip):
            return False, f"adresse interne/réservée refusée ({ip})", []
        ips.append(str(ip))
    if not ips:
        return False, "aucune adresse résolue", []
    return True, "", ips


def is_safe_public_url(url: str) -> bool:
    """Anti-SSRF : http(s) uniquement + rejette IP privées/loopback/link-local."""
    ok, _, _ = validate_url_for_fetch(url)
    return ok

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"}


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    return html.unescape(text).strip()


def _unwrap_ddg(url: str) -> str:
    """DuckDuckGo emballe les liens dans /l/?uddg=<url_encodée> : on déballe."""
    m = re.search(r"uddg=([^&]+)", url or "")
    if m:
        return requests.utils.unquote(m.group(1))
    if url and url.startswith("//"):
        return "https:" + url
    return url


def instant_answer(query: str) -> str:
    """Réponse factuelle directe si DuckDuckGo en connaît une (sinon '')."""
    try:
        r = requests.get("https://api.duckduckgo.com/",
                         params={"q": query, "format": "json", "no_html": 1,
                                 "skip_disambig": 1, "t": "jarvis"},
                         headers=HEADERS, timeout=10)
        data = r.json()
        if data.get("AbstractText"):
            src = data.get("AbstractSource", "")
            return f"{data['AbstractText']}" + (f" (source : {src})" if src else "")
        if data.get("Answer"):
            return str(data["Answer"])
        related = data.get("RelatedTopics", [])
        for topic in related:
            if isinstance(topic, dict) and topic.get("Text"):
                return topic["Text"]
    except Exception as e:
        logger.debug(f"Instant answer KO: {e}")
    return ""


def _anchors_with_class(html_text: str, cls: str) -> list:
    """Retourne [(attrs, contenu)] des <a> portant la classe donnée.

    Indépendant de l'ordre des attributs (href peut être avant ou après class).
    """
    out = []
    for attrs, inner in re.findall(r'<a\b([^>]*)>(.*?)</a>', html_text, re.S):
        if re.search(rf'class="[^"]*\b{re.escape(cls)}\b[^"]*"', attrs):
            out.append((attrs, inner))
    return out


def _href(attrs: str) -> str:
    m = re.search(r'href="([^"]+)"', attrs)
    return _unwrap_ddg(m.group(1)) if m else ""


def _parse_lite(html_text: str, max_results: int) -> list:
    # lite.duckduckgo.com : <a rel="nofollow" href="..." class="result-link">titre</a>
    anchors = _anchors_with_class(html_text, "result-link")
    snippets = re.findall(r'<td[^>]+class="result-snippet"[^>]*>(.*?)</td>', html_text, re.S)
    results = []
    for i, (attrs, title) in enumerate(anchors[:max_results]):
        results.append({
            "title": _clean(title),
            "url": _href(attrs),
            "snippet": _clean(snippets[i]) if i < len(snippets) else "",
        })
    return results


def _parse_html(html_text: str, max_results: int) -> list:
    anchors = _anchors_with_class(html_text, "result__a")
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html_text, re.S)
    results = []
    for i, (attrs, title) in enumerate(anchors[:max_results]):
        results.append({
            "title": _clean(title),
            "url": _href(attrs),
            "snippet": _clean(snippets[i]) if i < len(snippets) else "",
        })
    return results


def search(query: str, max_results: int = 5) -> dict:
    """Recherche web. Retourne {'answer': str, 'results': [{title,url,snippet}]}."""
    query = (query or "").strip()
    if not query:
        return {"answer": "", "results": [], "error": "Requête vide"}

    answer = instant_answer(query)
    results = []
    # 1) Lite
    try:
        r = requests.get("https://lite.duckduckgo.com/lite/",
                         params={"q": query}, headers=HEADERS, timeout=12)
        results = _parse_lite(r.text, max_results)
    except Exception as e:
        logger.debug(f"DDG lite KO: {e}")
    # 2) Repli HTML
    if not results:
        try:
            r = requests.get("https://html.duckduckgo.com/html/",
                             params={"q": query}, headers=HEADERS, timeout=12)
            results = _parse_html(r.text, max_results)
        except Exception as e:
            logger.debug(f"DDG html KO: {e}")

    if not answer and not results:
        return {"answer": "", "results": [],
                "error": "Aucun résultat (DuckDuckGo injoignable ou requête trop floue)."}
    return {"answer": answer, "results": results}


MAX_PAGE_BYTES = 3_000_000       # limite de taille (anti-DoS)
MAX_REDIRECTS = 3


def read_page(url: str, max_chars: int = 4000) -> str:
    """Récupère le texte lisible d'une page web (pour résumé par l'IA).

    Anti-SSRF : chaque saut (URL initiale ET chaque redirection) est revalidé
    (schéma, hôte, IP publique) AVANT la requête ; les redirections sont suivies
    manuellement et bornées. Empêche une URL publique de rediriger vers localhost.
    Taille de réponse et timeout bornés.
    """
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    raw = ""
    try:
        for _hop in range(MAX_REDIRECTS + 1):
            ok, reason, _ips = validate_url_for_fetch(url)
            if not ok:
                return f"⛔ URL refusée ({reason})."
            r = requests.get(url, headers=HEADERS, timeout=15,
                             allow_redirects=False, stream=True)
            if r.is_redirect or r.status_code in (301, 302, 303, 307, 308):
                nxt = r.headers.get("Location", "")
                r.close()
                if not nxt:
                    return "(redirection sans cible)"
                # Résout les redirections relatives par rapport à l'URL courante.
                from urllib.parse import urljoin
                url = urljoin(url, nxt)
                continue
            # Lecture bornée en taille.
            chunks, total = [], 0
            for chunk in r.iter_content(8192):
                chunks.append(chunk)
                total += len(chunk)
                if total >= MAX_PAGE_BYTES:
                    break
            r.close()
            raw = b"".join(chunks).decode(r.encoding or "utf-8", "replace")
            break
        else:
            return "⛔ Trop de redirections."
    except Exception as e:
        return f"Impossible de charger la page : {e}"
    # Vire scripts/styles puis balises
    raw = re.sub(r"<(script|style|noscript|svg|header|footer|nav)[^>]*>.*?</\1>", " ",
                 raw, flags=re.S | re.I)
    text = _clean(raw)
    text = re.sub(r"\s{2,}", " ", text)
    return text[:max_chars] if text else "(page vide ou illisible)"
