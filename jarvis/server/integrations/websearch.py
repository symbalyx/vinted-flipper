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


def is_safe_public_url(url: str) -> bool:
    """Anti-SSRF : http(s) uniquement + rejette IP privées/loopback/link-local."""
    try:
        u = urlparse(url)
        if u.scheme not in ("http", "https") or not u.hostname:
            return False
        for fam, _, _, _, sa in socket.getaddrinfo(u.hostname, None):
            ip = ipaddress.ip_address(sa[0])
            if (ip.is_private or ip.is_loopback or ip.is_link_local
                    or ip.is_reserved or ip.is_multicast):
                return False
        return True
    except Exception:
        return False

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


def read_page(url: str, max_chars: int = 4000) -> str:
    """Récupère le texte lisible d'une page web (pour résumé par l'IA)."""
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    if not is_safe_public_url(url):
        return "⛔ URL refusée (adresse interne/privée ou schéma non autorisé)."
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=False)
        raw = r.text
    except Exception as e:
        return f"Impossible de charger la page : {e}"
    # Vire scripts/styles puis balises
    raw = re.sub(r"<(script|style|noscript|svg|header|footer|nav)[^>]*>.*?</\1>", " ",
                 raw, flags=re.S | re.I)
    text = _clean(raw)
    text = re.sub(r"\s{2,}", " ", text)
    return text[:max_chars] if text else "(page vide ou illisible)"
