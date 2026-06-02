#!/usr/bin/env python3
"""
Vinted Flipper — Rapport quotidien.
Lance le Deal Finder, conseils saisonniers + stratégies pro.
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
    print("=" * 55)
    print("  VINTED FLIPPER — RAPPORT QUOTIDIEN")
    print(f"  {now:%d/%m/%Y %H:%M}")
    print("=" * 55)

    # Stats du moteur
    fe = FlipEngine()
    stats = fe.stats()
    if stats["flips"] > 0:
        print(f"\n  📊 FLIPS: {stats['flips']} | WR: {stats['wr']}% | "
              f"Profit: {stats['profit']:+.2f}€ | ROI: {stats['roi_total']:+.1f}%")

    # Stats du scanner
    sd = ScamDetector()
    if sd.model["analyses"] > 0:
        print(f"  🛡️ SCANNER: {sd.model['analyses']} analyses | "
              f"{sd.model['confirmed_fakes']} faux | {sd.model['confirmed_real']} authentiques")

    # Deal Finder
    df = DealFinder()

    # Plan pour 3 budgets
    for budget in [100, 200, 500]:
        plan = df.daily_plan(budget=budget)
        if plan["items_to_buy"] > 0:
            print(f"\n  🎯 BUDGET {budget}€/JOUR: "
                  f"{plan['items_to_buy']} articles → +{plan['total_profit_est']:.0f}€ "
                  f"(ROI {plan['roi_est']:+.0f}%, revente {plan['time_to_sell']})")
            weekly = plan['total_profit_est'] * 5
            monthly = plan['total_profit_est'] * 22
            print(f"     Semaine: +{weekly:.0f}€ | Mois: +{monthly:.0f}€")

    # Top recommandations
    print(f"\n  🔍 RECHERCHES À FAIRE AUJOURD'HUI:")
    df.scan_all()
    small = [o for o in df.opportunities if o["buy_price"] <= 40][:3]
    medium = [o for o in df.opportunities if 40 < o["buy_price"] <= 100][:3]
    for o in small[:3]:
        print(f"    • {o['brand'].title()} {o['category']} → "
              f"~{o['buy_price']}€ → ~{o['est_sell']:.0f}€ (+{o['profit_net']:.0f}€)")
    for o in medium[:3]:
        print(f"    • {o['brand'].title()} {o['category']} → "
              f"~{o['buy_price']:.0f}€ → ~{o['est_sell']:.0f}€ (+{o['profit_net']:.0f}€)")

    print()

    # ── CONSEIL SAISONNIER ──
    season_tips = {
        1: "Janvier: Soldes d'hiver → achète des articles d'été à prix brader. Vends manteaux, doudounes, pulls.",
        2: "Février: Dernière ligne droite pour l'hiver. Achète des articles de printemps en préparation.",
        3: "Mars: Prépare le printemps. Vends trenchs, blousons légers, pulls fins. Achète robes, t-shirts.",
        4: "Avril: Le printemps est là. Vends vestes mi-saison, chemises. Stocke robes, shorts, sandales.",
        5: "Mai: Pleine saison printemps. Vends robes, t-shirts, baskets. Vestes d'hiver = invendables.",
        6: "Juin: Prépare l'été. Vends maillots, shorts, sandales. Achète articles d'automne en vide-greniers.",
        7: "Juillet: Basse saison Vinted. Profite pour acheter en lot. Vends plage, chapeaux, lunettes.",
        8: "Août: Prépare la rentrée. Vends vêtements scolaires, sacs à dos. Achète pulls, vestes.",
        9: "Septembre: RENTRÉE — forte demande. Vends sweats, pulls, vestes légères, chemises.",
        10: "Octobre: L'hiver arrive. Vends doudounes, parkas, manteaux, boots. Achète en brocante.",
        11: "Novembre: BLACK FRIDAY — promos. Vends accessoires, bijoux, sacs, articles de fête.",
        12: "Décembre: FÊTES — pic d'achat. Vends robes soirée, costumes, accessoires, bijoux, sacs.",
    }
    tip = season_tips.get(now.month, "")
    if tip:
        print(f"  📅 {calendar.month_name[now.month].upper()}:")
        for line in tip.split(". "):
            print(f"     • {line.strip()}")
        print()

    # 💡 STRATÉGIES PRO
    print(f"  💡 STRATÉGIES DES PROS:")
    strategies = [
        "Sourcing: vide-greniers, Emmaüs, dépôts-vente → prix ×0.3 par rapport à Vinted",
        "Photos: fond blanc + lumière naturelle + 5+ photos = +40% de vues",
        "Prix: commencer 20% au-dessus du prix cible, accepter offres -10%",
        "Descriptions: marque + taille + état + matière + mesures + hashtags",
        "Publication: dimanche/lundi matin (9h-11h) = meilleur trafic",
        "Gestion stock: FIFO — brader -20% après 30 jours, -40% après 60 jours",
        "Achats décalés: acheter l'hiver en juillet, l'été en janvier",
    ]
    for s in strategies:
        print(f"     • {s}")

    print(f"\n  💡 Utilité: cli.py analyze | scam | generate | deals | plan | batch")
    print()


if __name__ == "__main__":
    main()
