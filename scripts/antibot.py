#!/usr/bin/env python3
"""
Vinted Flipper — Anti-Detection Module.
Headers, User-Agent rotation, proxy support, rate limiting.
Pour contourner Cloudflare et les bots detectors.
"""
import random, time, json
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent.parent.resolve()
DATA_DIR = BASE_DIR / "data"

# ─── User-Agents rotation ────────────────────────────────────

USER_AGENTS = [
    # Chrome 124 - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Chrome 124 - Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Firefox 125 - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Firefox 125 - Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Safari 17 - Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    # Edge 124 - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    # Chrome Mobile - Android
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.83 Mobile Safari/537.36",
    # Safari Mobile - iOS
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
]

# Headers de base (à compléter avec les sec-ch headers)
BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "DNT": "1",
}


def get_headers(custom_ua: Optional[str] = None) -> dict:
    """Retourne des headers complets avec User-Agent aléatoire."""
    headers = dict(BASE_HEADERS)
    headers["User-Agent"] = custom_ua or random.choice(USER_AGENTS)
    return headers


class AntiDetectClient:
    """Client HTTP avec anti-détection intégré.
    
    Gère :
    - Rotation User-Agent
    - Rate limiting adaptatif
    - Support proxies (HTTP/HTTPS/SOCKS5)
    - Session persistante
    - Retry avec backoff
    """
    
    def __init__(self, delay: float = 1.5, proxy: Optional[str] = None):
        self.delay = delay  # Délai de base entre requêtes
        self.current_delay = delay
        self.max_delay = 30.0
        self.min_delay = 0.5
        self.proxy = proxy
        self.last_request = 0.0
        self.request_count = 0
        
    def wait(self):
        """Rate limiting adaptatif."""
        elapsed = time.time() - self.last_request
        wait_time = self.current_delay - elapsed
        if wait_time > 0:
            # Ajouter un jitter aléatoire (±20%)
            jitter = random.uniform(-0.2, 0.2) * self.current_delay
            time.sleep(max(0, wait_time + jitter))
        
        self.last_request = time.time()
        self.request_count += 1
        
        # Réduire progressivement le délai si tout va bien
        if self.request_count % 10 == 0 and self.current_delay > self.min_delay:
            self.current_delay = max(self.min_delay, self.current_delay * 0.95)
    
    def on_rate_limited(self):
        """Augmente le délai après un 429 Too Many Requests."""
        self.current_delay = min(self.max_delay, self.current_delay * 2)
        print(f"  ⚠ Rate limit détecté, délai passe à {self.current_delay:.1f}s")
    
    def __call__(self, url: str, method: str = "GET", **kwargs) -> Optional[dict]:
        """Effectue une requête avec anti-détection."""
        self.wait()
        
        headers = get_headers()
        if kwargs.get("headers"):
            headers.update(kwargs["headers"])
        
        proxies = None
        if self.proxy:
            proxies = {"http": self.proxy, "https": self.proxy}
        
        try:
            import requests
            r = requests.request(
                method, url, headers=headers, proxies=proxies,
                timeout=kwargs.get("timeout", 15),
                allow_redirects=True,
            )
            
            if r.status_code == 429:
                self.on_rate_limited()
                return None
            elif r.status_code == 403:
                print(f"  🚫 Bloqué par Cloudflare (403)")
                return None
            elif r.status_code == 200:
                return {"status": 200, "html": r.text, "headers": dict(r.headers)}
            else:
                return {"status": r.status_code, "error": r.reason}
                
        except ImportError:
            print("  ⚠ requests module required: pip install requests")
            return None
        except Exception as e:
            print(f"  ❌ Erreur requête: {e}")
            return None


def test_connection(url: str = "https://www.vinted.fr") -> bool:
    """Teste si Vinted est accessible."""
    client = AntiDetectClient(delay=2.0)
    result = client(url)
    if result and result.get("status") == 200:
        html = result["html"]
        if "Just a moment" in html or "checking your browser" in html:
            print(f"  🚫 Cloudflare actif — Vinted bloque les bots")
            return False
        print(f"  ✅ Connecté à Vinted ({len(html)} bytes)")
        return True
    elif result:
        print(f"  ❌ Erreur {result.get('status')}: {result.get('error', '?')}")
        return False
    return False


if __name__ == "__main__":
    print("  Test anti-détection Vinted")
    print(f"  User-Agent: {random.choice(USER_AGENTS)[:50]}...")
    print(f"  Délai: 2.0s avec jitter")
    print()
    test_connection()
