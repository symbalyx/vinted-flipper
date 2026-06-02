#!/usr/bin/env python3
"""
Vinted Flipper — Rapport quotidien v2.
Ton sobre, style note perso. Pas de marketinguiserie.
"""
import sys, calendar
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(BASE_DIR))

from deals import DealFinder
from flipper import FlipEngine
from scanner import ScamDetector


def main():
    now = datetime.now()
    month = now.month
    day = now.day
    
    print("=" * 50)
    print(f"  VINTED FLIPPER — {now:%d/%m/%Y}")
    print("=" * 50)
    
    # Stats du moteur
    fe = FlipEngine()
    stats = fe.stats()
    if stats["flips"] > 0:
        wr_color = "vert" if stats["wr"] >= 60 else "rouge"
        print(f"\n  Bilan: {stats['flips']} flips | {stats['wr']}% reussite | "
              f"+{stats['profit']:.0f}€ | ROI {stats['roi_total']:+.0f}%")
    
    # Stats du scanner
    sd = ScamDetector()
    if sd.model["analyses"] > 0:
        print(f"  Scanner: {sd.model['analyses']} annonces analysees | "
              f"{sd.model['confirmed_fakes']} fausses | {sd.model['confirmed_real']} authentiques")
    
    # Deal Finder
    df = DealFinder()
    
    # Plan pour 3 budgets
    budgets_info = []
    for budget in [100, 200, 500]:
        plan = df.daily_plan(budget=budget)
        if plan["items_to_buy"] > 0:
            budgets_info.append(
                f"  Budget {budget}€/j: {plan['items_to_buy']} achats -> +{plan['total_profit_est']:.0f}€ "
                f"(ROI {plan['roi_est']:+.0f}%, vente sous {plan['time_to_sell']})"
            )
    
    if budgets_info:
        print(f"\n  Plans par budget:")
        for line in budgets_info:
            print(line)
    
    # Top recherches du jour
    print(f"\n  Recherches du jour:")
    df.scan_all()
    small = [o for o in df.opportunities if o["buy_price"] <= 40][:3]
    medium = [o for o in df.opportunities if 40 < o["buy_price"] <= 100][:3]
    for o in small[:3]:
        print(f"    - {o['brand'].title()} {o['category']}: "
              f"~{o['buy_price']:.0f}€ -> ~{o['est_sell']:.0f}€ (+{o['profit_net']:.0f}€)")
    for o in medium[:3]:
        print(f"    - {o['brand'].title()} {o['category']}: "
              f"~{o['buy_price']:.0f}€ -> ~{o['est_sell']:.0f}€ (+{o['profit_net']:.0f}€)")
    
    print()
    
    # Conseil saisonnier
    season_tips = {
        1: "Janvier: soldes d'hiver, achete articles d'ete a prix bradé. Vends manteaux, doudounes.",
        2: "Fevrier: derniere ligne droite pour l'hiver. Achete articles de printemps en preparation.",
        3: "Mars: prepare le printemps. Vends trenchs, blousons, pulls fins.",
        4: "Avril: le printemps arrive. Vends vestes mi-saison, chemises. Stocke robes, shorts.",
        5: "Mai: pleine saison. Vends robes, t-shirts, baskets. Vestes d'hiver invendables.",
        6: "Juin: prepare l'ete. Vends maillots, shorts. Achete articles d'automne en vide-greniers.",
        7: "Juillet: basse saison Vinted. Profite pour acheter en lot.",
        8: "Aout: prepare la rentrée. Vends vetements scolaires. Achete pulls, vestes.",
        9: "Septembre: RENTREE. Forte demande. Vends sweats, pulls, vestes legeres.",
        10: "Octobre: l'hiver arrive. Vends doudounes, parkas, boots.",
        11: "Novembre: Black Friday. Vends accessoires, bijoux, sacs.",
        12: "Decembre: fetes. Vends robes soiree, costumes, accessoires.",
    }
    tip = season_tips.get(month, "")
    if tip:
        print(f"  Calendrier:")
        print(f"    {tip}")
        print()
    
    # 2-3 conseils rapides
    print(f"  Conseils:")
    print(f"    Sources: vide-greniers, Emmaüs, depots-vente -> prix x0.3 vs Vinted")
    print(f"    Photos: fond clair + lumiere naturelle + 5 photos = +40% de vues")
    print(f"    Publication: dimanche/lundi matin (9h-11h) = meilleur trafic")
    print(f"    Stock: brader -20% apres 30 jours, -40% apres 60 jours")
    
    print(f"\n  Commandes: analyze | scam | generate | deals | plan | batch")
    print()


if __name__ == "__main__":
    main()
