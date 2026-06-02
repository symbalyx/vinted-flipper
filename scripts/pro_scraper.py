#!/usr/bin/env python3
"""
Pro Scraper Vinted v1 — Scraping furtif multi-backend.
Contourne Cloudflare via 4 backends avec fallback automatique.

Architecture:
  Backend 1: npm @powerm1nt/vinted-api (via Node.js) ← PRIORITAIRE
  Backend 2: Playwright stealth (via Node.js puppeteer-extra)
  Backend 3: Cloudscraper + rotation proxies
  Backend 4: Fichier JSON local (mode offline / debug)

Anti-détection:
  - Cookies persistés (access_token_web)
  - Proxy rotation (HTTP/HTTPS/SOCKS5)
  - Délais aléatoires humains (jitter ±40%)
  - User-Agent rotation (12 profils réalistes)
  - Headers complets (sec-ch-ua, sec-fetch-*, etc.)
  - Path navigué réaliste (page d'accueil → search → scroll)
"""

import json, os, sys, time, random, re
import subprocess, shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

BASE_DIR = Path(__file__).parent.parent.resolve()
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
COOKIE_FILE = DATA_DIR / "vinted_cookies.json"
CONFIG_FILE = DATA_DIR / "scraper_config.json"

# ─── 12 profils User-Agent réalistes ────────────────────────
USER_AGENTS = [
    # Windows Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    # Windows Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0",
    # macOS Chrome
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    # macOS Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
    # Linux Chrome
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    # Linux Firefox
    "Mozilla/5.0 (X11; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
    # Android Chrome
    "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Mobile Safari/537.36",
    # iPhone Safari
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Mobile/15E148 Safari/604.1",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
]

# ─── Backend status ──────────────────────────────────────────
BACKENDS = {
    "npm_api": {"available": False, "enabled": True},
    "puppeteer": {"available": False, "enabled": True},
    "direct": {"available": False, "enabled": True},
    "offline": {"available": True, "enabled": True},
}


class VintedScraper:
    """Scraper pro avec fallback multi-backend."""

    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.cache_dir = self.data_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.config = self._load_config()
        self.cookies = self._load_cookies()
        self.stats = {"requests": 0, "cached": 0, "errors": 0, "backends_used": []}
        self._detect_backends()

    def _load_config(self) -> dict:
        default = {
            "proxies": [],
            "proxy_enabled": False,
            "cookie": "",
            "delay_min": 1.5,
            "delay_max": 4.0,
            "max_retries": 3,
            "preferred_backend": "npm_api",
            "auto_fallback": True,
        }
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                default.update(data)
            except:
                pass
        return default

    def _save_config(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(self.config, indent=2, ensure_ascii=False))

    def _load_cookies(self) -> dict:
        if COOKIE_FILE.exists():
            try:
                return json.loads(COOKIE_FILE.read_text())
            except:
                pass
        return {}

    def _save_cookies(self):
        COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
        COOKIE_FILE.write_text(json.dumps(self.cookies, indent=2))

    def set_cookie(self, cookie: str):
        """Injecte un cookie access_token_web manuellement.
        Obviens-le en visitant vinted.fr dans ton navigateur:
        1. Ouvre chrome, va sur vinted.fr
        2. F12 → Application → Cookies → vinted.fr
        3. Copie la valeur de 'access_token_web'
        4. colle-la ici
        """
        self.config["cookie"] = cookie
        self.cookies["access_token_web"] = cookie
        self._save_config()
        self._save_cookies()
        print(f"Cookie injecté: {cookie[:20]}...")

    def add_proxy(self, proxy: str):
        """Ajoute un proxy (format: http://user:pass@ip:port ou socks5://ip:port)"""
        if proxy not in self.config["proxies"]:
            self.config["proxies"].append(proxy)
            self.config["proxy_enabled"] = True
            self._save_config()
            print(f"Proxy ajouté: {proxy[:30]}...")

    def _detect_backends(self):
        """Détecte les backends disponibles."""
        # Backend 1: npm @powerm1nt/vinted-api
        try:
            r = subprocess.run(
                ["node", "-e", "require('@powerm1nt/vinted-api'); console.log('ok')"],
                capture_output=True, text=True, timeout=5,
                cwd=str(BASE_DIR)
            )
            BACKENDS["npm_api"]["available"] = r.returncode == 0 and r.stdout.strip() == "ok"
        except:
            BACKENDS["npm_api"]["available"] = False

        # Backend 2: puppeteer-extra
        try:
            r = subprocess.run(
                ["node", "-e", "require('puppeteer-extra'); console.log('ok')"],
                capture_output=True, text=True, timeout=5,
                cwd=str(BASE_DIR)
            )
            BACKENDS["puppeteer"]["available"] = r.returncode == 0 and r.stdout.strip() == "ok"
        except:
            BACKENDS["puppeteer"]["available"] = False

        # Backend 3: Direct cloudscraper
        try:
            import cloudscraper
            BACKENDS["direct"]["available"] = True
        except:
            BACKENDS["direct"]["available"] = False

        print(f"Backends: npm_api={'OK' if BACKENDS['npm_api']['available'] else 'NON'} "
              f"| puppeteer={'OK' if BACKENDS['puppeteer']['available'] else 'NON'} "
              f"| direct={'OK' if BACKENDS['direct']['available'] else 'NON'} "
              f"| offline=OK")

    def human_delay(self, min_s: float = None, max_s: float = None):
        """Délai aléatoire avec jitter humain."""
        min_s = min_s or self.config["delay_min"]
        max_s = max_s or self.config["delay_max"]
        delay = random.uniform(min_s, max_s)
        # Ajouter un jitter de ±40%
        delay *= random.uniform(0.6, 1.4)
        time.sleep(delay)

    def search(self, query: str, page: int = 1, per_page: int = 20,
               **kwargs) -> List[Dict[str, Any]]:
        """Recherche des articles Vinted. Essaie tous les backends.

        Args:
            query: Terme de recherche
            page: Numéro de page
            per_page: Résultats par page (max 96)
            order: 'relevance', 'newest_first', 'price_low_to_high', etc.

        Returns:
            Liste d'articles avec title, price, brand, favoris, url, etc.
        """
        self.stats["requests"] += 1
        errors = []

        # Essayer chaque backend dans l'ordre configuré
        backends_order = ["npm_api", "puppeteer", "direct"]

        for backend in backends_order:
            if not BACKENDS[backend]["available"] or not BACKENDS[backend]["enabled"]:
                continue

            try:
                self.human_delay(1.0, 2.5)
                items = self._search_with_backend(backend, query, page, per_page, kwargs)
                if items:
                    self.stats["backends_used"].append(backend)
                    self.stats["backends_used"] = list(set(self.stats["backends_used"]))
                    return items
            except Exception as e:
                errors.append(f"{backend}: {e}")
                self.stats["errors"] += 1

        # Si tout a échoué, charger depuis le cache si disponible
        cached = self._load_from_cache(query, page)
        if cached:
            self.stats["cached"] += 1
            print(f"Cache utilisé pour '{query}' page {page}")
            return cached

        return []

    def _search_with_backend(self, backend: str, query: str, page: int,
                              per_page: int, extra: dict) -> list:
        if backend == "npm_api":
            return self._search_npm(query, page, per_page, extra)
        elif backend == "puppeteer":
            return self._search_puppeteer(query, page, per_page, extra)
        elif backend == "direct":
            return self._search_direct(query, page, per_page, extra)
        return []

    def _search_npm(self, query: str, page: int, per_page: int, extra: dict) -> list:
        """Backend 1: npm @powerm1nt/vinted-api."""
        cookie = self.config.get("cookie") or self.cookies.get("access_token_web", "")

        script = f"""
        const vinted = require('@powerm1nt/vinted-api');
        const searchUrl = 'https://www.vinted.fr/catalog?search_text={query}&page={page}&per_page={per_page}';

        async function run() {{
            try {{
                // Injecter cookie si disponible
                {f"const cookie = '{cookie}';" if cookie else ""}
                {f"vinted.fetchCookie = async () => ({{cookie: '{cookie}'}});" if cookie else ""}

                const results = await vinted.search(searchUrl, false, false, {{}});

                if (Array.isArray(results) && results.length > 0) {{
                    const items = results.map(item => ({{
                        id: item.id || null,
                        title: item.title || '',
                        price: item.price?.amount || 0,
                        currency: item.price?.currency_code || 'EUR',
                        brand: item.brand_title || '',
                        size: item.size_title || '',
                        status: item.status || '',
                        favourited: item.favourite_count || 0,
                        photos: item.photos?.length || 0,
                        url: item.url || '',
                        user: item.user?.username || '',
                        user_id: item.user?.id || null,
                        views: item.view_count || 0,
                        created_at: item.created_at_ts || null,
                    }}));
                    console.log(JSON.stringify({{success: true, count: items.length, items}}));
                }} else {{
                    console.log(JSON.stringify({{success: false, error: 'No items', raw: typeof results}}));
                }}
            }} catch(e) {{
                console.log(JSON.stringify({{success: false, error: e.message}}));
            }}
            process.exit(0);
        }}
        run();
        """

        result = subprocess.run(
            ["node", "-e", script],
            capture_output=True, text=True, timeout=30,
            cwd=str(BASE_DIR),
            env={**os.environ, "NODE_PATH": str(BASE_DIR / "node_modules")}
        )

        output = result.stdout.strip()
        if output:
            try:
                data = json.loads(output)
                if data.get("success") and data.get("items"):
                    items = data["items"]
                    self._save_to_cache(query, page, items)
                    return items
                elif data.get("error"):
                    if "cookie" in str(data.get("error", "")).lower():
                        print("  Cookie invalide ou expiré. Mets-en un nouveau avec set_cookie().")
            except json.JSONDecodeError:
                pass

        return []

    def _search_puppeteer(self, query: str, page: int, per_page: int, extra: dict) -> list:
        """Backend 2: Puppeteer extra stealth (le + furtif)."""
        chrome_path = "/opt/hermes/.playwright/chromium-1169/chrome-linux/chrome"
        if not os.path.exists(chrome_path):
            return []

        query_clean = query.replace("'", "\\'")
        script = f"""
        const puppeteer = require('puppeteer-extra');
        const StealthPlugin = require('puppeteer-extra-plugin-stealth');
        puppeteer.use(StealthPlugin());

        (async () => {{
            try {{
                const browser = await puppeteer.launch({{
                    executablePath: '{chrome_path}',
                    headless: true,
                    args: ['--no-sandbox', '--disable-blink-features=AutomationControlled'],
                }});

                const page = await browser.newPage();
                await page.setViewport({{width: 1920, height: 1080}});
                await page.setUserAgent({json.dumps(random.choice(USER_AGENTS))});

                // Warm-up
                await page.goto('https://www.google.fr', {{waitUntil: 'domcontentloaded', timeout: 15000}}).catch(() => {{}});
                await new Promise(r => setTimeout(r, Math.random() * 2000 + 1000));

                // Vinted search
                const url = 'https://www.vinted.fr/catalog?search_text={query_clean}&page={page}&per_page={per_page}';
                await page.goto(url, {{waitUntil: 'networkidle0', timeout: 45000}}).catch(() => {{}});
                await new Promise(r => setTimeout(r, Math.random() * 3000 + 2000));

                const title = await page.title();
                if (title.includes('instant')) {{
                    console.log(JSON.stringify({{success: false, error: 'Cloudflare block'}}));
                    await browser.close();
                    return;
                }}

                // Extraire les données
                const items = await page.evaluate(() => {{
                    const cards = document.querySelectorAll('[class*="new-item"], [data-testid*="item"], article');
                    return Array.from(cards).slice(0, {per_page}).map(card => ({{
                        title: card.querySelector('[class*="title"], h3, h2')?.textContent?.trim() || '',
                        price: parseFloat(card.querySelector('[class*="price"]')?.textContent?.replace(/[^0-9,]/g, '').replace(',', '.') || '0'),
                        url: card.querySelector('a')?.href || '',
                        favourited: parseInt(card.querySelector('[class*="favourite"], [class*="favorite"]')?.textContent?.match(/\d+/)?.[0] || '0'),
                    }}));
                }});

                console.log(JSON.stringify({{success: true, count: items.length, items}}));
                await browser.close();
            }} catch(e) {{
                console.log(JSON.stringify({{success: false, error: e.message}}));
            }}
            process.exit(0);
        }})();
        """

        try:
            result = subprocess.run(
                ["node", "-e", script],
                capture_output=True, text=True, timeout=60,
                cwd=str(BASE_DIR),
                env={**os.environ, "NODE_PATH": str(BASE_DIR / "node_modules")}
            )

            output = result.stdout.strip()
            if output:
                data = json.loads(output)
                if data.get("success") and data.get("items"):
                    items = data["items"]
                    self._save_to_cache(query, page, items)
                    return items
        except:
            pass

        return []

    def _search_direct(self, query: str, page: int, per_page: int, extra: dict) -> list:
        """Backend 3: Cloudscraper direct + proxies."""
        try:
            import cloudscraper
            import urllib.parse

            scraper = cloudscraper.create_scraper(
                browser={"browser": "chrome", "platform": "windows", "desktop": True}
            )

            # Cookie injection
            if self.config.get("cookie"):
                scraper.cookies.set("access_token_web", self.config["cookie"],
                                    domain=".vinted.fr", path="/")

            # Proxy
            proxies = None
            if self.config["proxy_enabled"] and self.config["proxies"]:
                proxy = random.choice(self.config["proxies"])
                proxies = {"http": proxy, "https": proxy}

            ua = random.choice(USER_AGENTS)
            headers = {
                "User-Agent": ua,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://www.vinted.fr/",
                "Origin": "https://www.vinted.fr",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Ch-Ua": '"Chromium";v="136", "Not?A_Brand";v="8"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "DNT": "1",
                "Connection": "keep-alive",
            }

            query_encoded = urllib.parse.quote(query)
            url = f"https://www.vinted.fr/api/v2/catalog/items?search_text={query_encoded}&page={page}&per_page={per_page}"

            resp = scraper.get(url, headers=headers, proxies=proxies, timeout=20)

            if resp.status_code == 200:
                data = resp.json()
                items = []
                for item in data.get("items", []):
                    items.append({
                        "id": item.get("id"),
                        "title": item.get("title", ""),
                        "price": item.get("price", {}).get("amount", 0),
                        "currency": item.get("price", {}).get("currency_code", "EUR"),
                        "brand": item.get("brand_title", ""),
                        "size": item.get("size_title", ""),
                        "favourited": item.get("favourite_count", 0),
                        "photos": len(item.get("photos", [])),
                        "url": item.get("url", ""),
                        "user": item.get("user", {}).get("username", ""),
                        "views": item.get("view_count", 0),
                        "created_at": item.get("created_at_ts"),
                    })
                if items:
                    self._save_to_cache(query, page, items)
                    return items

            # Si 403, sauvegarder la requête pour exécution manuelle
            if resp.status_code == 403:
                self._save_query_for_manual(query, page, per_page)
        except Exception as e:
            pass

        return []

    # ── Cache & Fallback ──────────────────────────────────────

    def _save_to_cache(self, query: str, page: int, items: list):
        """Sauvegarde les résultats dans le cache."""
        cache_file = self.cache_dir / f"{self._slugify(query)}_p{page}.json"
        data = {
            "query": query, "page": page, "count": len(items),
            "timestamp": datetime.now().isoformat(),
            "items": items,
        }
        cache_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def _load_from_cache(self, query: str, page: int, max_age_hours: int = 6) -> list:
        """Charge du cache si encore frais."""
        cache_file = self.cache_dir / f"{self._slugify(query)}_p{page}.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                ts = datetime.fromisoformat(data["timestamp"])
                if datetime.now() - ts < timedelta(hours=max_age_hours):
                    return data.get("items", [])
            except:
                pass
        return []

    def _save_query_for_manual(self, query: str, page: int, per_page: int):
        """Sauvegarde la requête pour exécution depuis un autre PC."""
        manual_file = self.cache_dir / "pending_manual_queries.json"
        queries = []
        if manual_file.exists():
            try:
                queries = json.loads(manual_file.read_text())
            except:
                pass

        queries.append({
            "query": query, "page": page, "per_page": per_page,
            "timestamp": datetime.now().isoformat(),
            "status": "pending",
        })
        manual_file.write_text(json.dumps(queries, indent=2, ensure_ascii=False))
        print(f"Requête sauvegardée pour exécution manuelle: '{query}' p.{page}")

    def _slugify(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")

    # ── Utilitaires ────────────────────────────────────────────

    def get_stats(self) -> dict:
        return {
            **self.stats,
            "cookie_set": bool(self.config.get("cookie") or self.cookies.get("access_token_web")),
            "proxies": len(self.config["proxies"]),
            "proxy_enabled": self.config["proxy_enabled"],
            "backend_npm": BACKENDS["npm_api"]["available"],
            "backend_puppeteer": BACKENDS["puppeteer"]["available"],
            "backend_direct": BACKENDS["direct"]["available"],
        }

    def export_pending_queries(self) -> list:
        """Exporte les requêtes en attente pour exécution manuelle."""
        manual_file = self.cache_dir / "pending_manual_queries.json"
        if manual_file.exists():
            try:
                return json.loads(manual_file.read_text())
            except:
                pass
        return []

    def report(self) -> str:
        """Rapport d'état du scraper."""
        s = self.get_stats()
        lines = ["── SCRAPER VINTED PRO ──"]
        lines.append(f"  Requêtes: {s['requests']} | Cache: {s['cached']} | Erreurs: {s['errors']}")
        lines.append(f"  Backends utilisés: {', '.join(s['backends_used']) or 'aucun'}")
        lines.append(f"  Backends dispo: npm={s['backend_npm']} puppeteer={s['backend_puppeteer']} direct={s['backend_direct']}")
        lines.append(f"  Cookie: {'OK' if s['cookie_set'] else 'MANQUANT — utilise set_cookie()'}")
        lines.append(f"  Proxies: {s['proxies']} {'(actif)' if s['proxy_enabled'] else '(inactif)'}")

        pending = self.export_pending_queries()
        if pending:
            lines.append(f"\n  Requêtes en attente: {len(pending)}")
            for q in pending[:5]:
                lines.append(f"    - '{q['query']}' p.{q['page']} ({q['timestamp'][:16]})")

        lines.append(f"\n  Commandes:")
        lines.append(f"    set_cookie('<token>')    → injecte cookie Vinted")
        lines.append(f"    add_proxy('socks5://...') → ajoute un proxy")
        lines.append(f"    search('nike air force')  → recherche des articles")
        lines.append(f"    export_pending_queries()  → requêtes pour exécution manuelle")

        return "\n".join(lines)


# ─── CLI ─────────────────────────────────────────────────────

def cmd_search(args):
    """Recherche des articles sur Vinted."""
    scraper = VintedScraper()
    query = " ".join(args.query) if hasattr(args, 'query') and args.query else input("Recherche: ")
    pages = int(getattr(args, 'pages', 1))
    all_items = []

    for p in range(1, pages + 1):
        items = scraper.search(query, page=p, per_page=30)
        all_items.extend(items)
        print(f"  Page {p}: {len(items)} articles")

        if not items:
            print("  Plus de résultats ou bloqué.")
            break

    print(f"\nTotal: {len(all_items)} articles pour '{query}'")
    if all_items:
        # Afficher un résumé
        brands = set(i.get("brand", "") for i in all_items if i.get("brand"))
        prices = [i.get("price", 0) for i in all_items if i.get("price", 0) > 0]
        favs = [i.get("favourited", 0) for i in all_items]

        print(f"  Marques: {', '.join(sorted(brands)[:10])}")
        print(f"  Prix: {min(prices):.0f}€ - {max(prices):.0f}€ (moy: {sum(prices)/len(prices):.0f}€)" if prices else "  Pas de prix")
        print(f"  Favoris moyen: {sum(favs)/len(favs):.0f}" if favs else "")

        # Top articles par favoris
        top = sorted(all_items, key=lambda x: x.get("favourited", 0), reverse=True)[:5]
        print(f"\n  Top articles:")
        for t in top:
            print(f"    {t.get('title', '?')[:50]:50s} {t.get('price', 0):>6.0f}€ ❤️{t.get('favourited', 0)}")

    # Sauvegarder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    path = f"search_{scraper._slugify(query)}_{timestamp}.json"
    with open(path, "w") as f:
        json.dump(all_items, f, indent=2, ensure_ascii=False)
    print(f"\nSauvegardé: {path} ({len(all_items)} articles)")


def cmd_stats(args):
    """Statut du scraper."""
    scraper = VintedScraper()
    print(f"\n{scraper.report()}")


def cmd_setcookie(args):
    """Injecte un cookie Vinted."""
    cookie = args.cookie if hasattr(args, 'cookie') and args.cookie else input("Cookie access_token_web: ").strip()
    if cookie:
        scraper = VintedScraper()
        scraper.set_cookie(cookie)
        print("Cookie OK!")


def cmd_addproxy(args):
    """Ajoute un proxy."""
    proxy = args.proxy if hasattr(args, 'proxy') and args.proxy else input("Proxy (http://... ou socks5://...): ").strip()
    if proxy:
        scraper = VintedScraper()
        scraper.add_proxy(proxy)
        print("Proxy OK!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Vinted Pro Scraper")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("stats", help="État du scraper")
    p_search = sub.add_parser("search", help="Rechercher des articles")
    p_search.add_argument("query", nargs="*", help="Terme de recherche")
    p_search.add_argument("--pages", type=int, default=1)
    p_cookie = sub.add_parser("setcookie", help="Injecter un cookie Vinted")
    p_cookie.add_argument("cookie", nargs="?", help="Valeur du cookie")
    p_proxy = sub.add_parser("addproxy", help="Ajouter un proxy")
    p_proxy.add_argument("proxy", nargs="?", help="URL du proxy")

    args = parser.parse_args()
    cmds = {"search": cmd_search, "stats": cmd_stats, "setcookie": cmd_setcookie, "addproxy": cmd_addproxy}
    if args.cmd in cmds:
        cmds[args.cmd](args)
    else:
        cmd_stats(args)
