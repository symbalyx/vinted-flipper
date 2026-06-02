#!/usr/bin/env python3
"""
Vinted Flipper — Scraper navigateur.
Utilise le browser tool pour naviguer sur Vinted,
extraire les annonces, et les analyser avec le moteur flip.
"""
import sys, json, re, time
from pathlib import Path
from datetime import datetime
from typing import Optional

BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(BASE_DIR))
from flipper import FlipEngine


class VintedBrowserScraper:
    """Scrape les annonces Vinted via navigateur.
    
    Utilise browser_navigate + browser_snapshot + browser_console
    pour extraire les listings et les analyser.
    """
    
    def __init__(self):
        self.fe = FlipEngine()
        self.seen_ids = set()
        
    def search_url(self, query: str, sort: str = "price_asc",
                   price_min: Optional[float] = None,
                   price_max: Optional[float] = None) -> str:
        """Génère l'URL de recherche Vinted."""
        base = "https://www.vinted.fr/catalog"
        params = f"?search_text={query.replace(' ', '+')}&order={sort}"
        if price_min:
            params += f"&price_from={price_min:.0f}"
        if price_max:
            params += f"&price_to={price_max:.0f}"
        return base + params
    
    def extract_listings_from_page(self, html: str) -> list:
        """Extrait les listings du HTML de la page Vinted.
        
        Cherche les patterns de carte d'article Vinted :
        - Titre, prix, marque, lien
        """
        listings = []
        
        # Pattern: cartes articles Vinted
        # Chercher les blocs d'articles avec prix
        price_pattern = re.finditer(
            r'itemprop=["\']price["\'].*?content=["\']([\d.]+)',
            html, re.IGNORECASE
        )
        title_pattern = re.finditer(
            r'itemprop=["\']name["\'].*?content=["\']([^"\']+)',
            html, re.IGNORECASE
        )
        link_pattern = re.finditer(
            r'href=["\'](/catalog/items/\d+[^"\']*)["\']',
            html
        )
        
        prices = [m.group(1) for m in price_pattern]
        titles = [m.group(1) for m in title_pattern]
        links = [m.group(1) for m in link_pattern]
        
        # Combiner les données
        min_len = min(len(prices), len(titles), len(links))
        for i in range(min_len):
            try:
                price = float(prices[i])
                title = titles[i].strip()
                url = f"https://www.vinted.fr{links[i]}"
                
                # Analyser avec le moteur
                analysis = self.fe.analyze(title, price, "bon état", "", "")
                
                listings.append({
                    "title": title,
                    "price": price,
                    "url": url,
                    "est_sell": analysis["estimation_revente"],
                    "profit": analysis["profit_net"],
                    "margin": analysis["marge_pct"],
                    "recommendation": analysis["recommandation"],
                    "brand": analysis.get("marque", ""),
                    "category": analysis.get("categorie", ""),
                })
            except (ValueError, IndexError):
                continue
        
        return listings
    
    def sort_listings(self, listings: list, sort_by: str = "profit") -> list:
        """Trie les listings par rentabilité."""
        if sort_by == "profit":
            return sorted(listings, key=lambda x: -x["profit"])
        elif sort_by == "margin":
            return sorted(listings, key=lambda x: -x["margin"])
        elif sort_by == "price":
            return sorted(listings, key=lambda x: x["price"])
        return listings
    
    def report_listings(self, listings: list, max_items: int = 10) -> str:
        """Rapport formaté des listings trouvés."""
        lines = []
        lines.append(f"── RÉSULTATS VINTED ({len(listings)} annonces) ──")
        lines.append("")
        
        # Trier par profit
        sorted_l = self.sort_listings(listings)
        
        for i, item in enumerate(sorted_l[:max_items], 1):
            profit_color = "💰" if item["profit"] > 10 else "✅" if item["profit"] > 0 else "❌"
            lines.append(
                f"  {profit_color} #{i} {item['title'][:40]:40s}"
            )
            lines.append(
                f"       {item['price']:>5.0f}€ → {item['est_sell']:>5.0f}€ "
                f"| {item['profit']:+.1f}€ ({item['margin']:+.0f}%)"
            )
            lines.append(f"       {item['recommendation']}")
        
        # Stats
        profits = [l["profit"] for l in sorted_l if l["profit"] > 0]
        if profits:
            avg_profit = sum(profits) / len(profits)
            total_profit = sum(profits)
            good_deals = len([l for l in sorted_l if l["profit"] > 10])
            lines.append(f"\n  📊 Stats: {good_deals} bonnes affaires | "
                        f"Profit moyen: {avg_profit:.1f}€ | "
                        f"Total potentiel: {total_profit:.0f}€")
        
        return "\n".join(lines)


# ─── Mode CLI ──────────────────────────────────────────────────

def cmd_scan(args):
    """Recherche et analyse des annonces via navigateur.
    
    Usage: python3 scripts/scraper.py scan "nike air force" [--max-price 50]
    """
    scraper = VintedBrowserScraper()
    query = " ".join(args) if args else "nike"
    
    print(f"🔍 RECHERCHE SUR VINTED: '{query}'")
    print()
    print("  Pour utiliser le scraper :")
    print(f"  1. browser_navigate(url='{scraper.search_url(query)}')")
    print(f"  2. browser_snapshot() pour voir les résultats")
    print(f"  3. browser_console(expression='document.body.innerHTML')")
    print(f"  4. Copie le HTML dans scraper.extract_listings_from_page(html)")
    print()
    print("  RECHERCHES RAPIDES RECOMMANDÉES:")
    print()
    
    searches = [
        ("zara", "veste", 5, 15),
        ("mango", "robe", 5, 15),
        ("carhartt", "veste", 20, 40),
        ("patagonia", "polaire", 15, 40),
        ("arc'teryx", "veste", 30, 70),
        ("nike", "air force", 20, 45),
        ("levi's", "501", 8, 20),
        ("adidas", "originals", 10, 30),
    ]
    
    for brand, item, pmin, pmax in searches:
        fe = FlipEngine()
        title = f"{brand.title()} {item}"
        r = fe.analyze(title, (pmin + pmax) / 2, "bon état", item, brand)
        if r["profit_net"] > 5:
            icon = "💰" if r["profit_net"] > 15 else "✅"
            print(f"  {icon} « {title} » — chercher {pmin}-{pmax}€ → "
                  f"est. {r['estimation_revente']:.0f}€ (+{r['profit_net']:.0f}€)")


def cmd_extract(args):
    """Extrait les listings du HTML collé."""
    scraper = VintedBrowserScraper()
    
    print("  Colle le HTML de la page Vinted (finit par CTRL+D):")
    try:
        html = sys.stdin.read()
    except EOFError:
        return
    
    listings = scraper.extract_listings_from_page(html)
    print(f"\n{scraper.report_listings(listings)}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "extract":
        cmd_extract(sys.argv[2:])
    else:
        cmd_scan(sys.argv[1:])
