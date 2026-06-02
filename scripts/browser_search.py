#!/usr/bin/env python3
"""
Vinted Flipper — Assistant de recherche via navigateur.
Ouvre Vinted dans le navigateur et extrait les annonces prometteuses.
"""
import sys, json, time, re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BASE_DIR))
from flipper import FlipEngine


def search_vinted(query: str, min_profit: float = 10.0,
                  max_items: int = 5, pages: int = 1):
    """
    Recherche des articles sur Vinted via le navigateur.
    Utilise le browser tool pour naviguer et extraire les données.
    """
    fe = FlipEngine()
    results = []
    url = f"https://www.vinted.fr/catalog?search_text={query.replace(' ', '+')}&order=price_asc"

    print(f"  Navigation vers: {url}")
    print(f"  Recherche: {query} | Prix croissant | Pages: {pages}")
    print()

    # Note: l'agent parent doit utiliser browser_navigate + browser_snapshot
    # pour extraire les listings. Ce script est un plan d'exécution.
    print("  PROTOCOLE D'UTILISATION:")
    print(f"  1. Ouvre Vinted: browser_navigate(url='{url}')")
    print(f"  2. Extrais les prix: browser_console(expression='...')")
    print(f"  3. Pour chaque annonce, lance: cli.py analyze")
    print()
    print(f"  MARQUES RECHERCHÉES (ordre de rentabilité):")
    print(f"  {', '.join(list(BRAND_FACTOR.keys())[:15])}")
    print()

    # Alternative: suggestions de recherches rentables
    print(f"  RECHERCHES RECOMMANDÉES (prix bas, revente élevée):")
    profitable = [
        ("moncler", 50, 100), ("arc'teryx", 40, 80),
        ("stone island", 30, 60), ("patagonia", 20, 50),
        ("carhartt", 15, 35), ("levi's 501", 10, 20),
        ("nike air force", 20, 40), ("salomon", 25, 45),
        ("montre homme", 15, 30), ("sac cuir", 20, 50),
    ]
    for item, low, high in profitable:
        print(f"  - {item:20s} [{low}€-{high}€] → {fe.analyze(item, low, 'bon état', item)[0]:.2f}€ estimé")

    return results


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "nike air force"
    search_vinted(query)
