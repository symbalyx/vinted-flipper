#!/usr/bin/env python3
"""
Vinted Flipper — Rapport quotidien.
Lance le Deal Finder et affiche les opportunités du jour.
Utilisé par le cron matinal.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(BASE_DIR))

from deals import DealFinder
from flipper import FlipEngine
from scanner import ScamDetector

def main():
    print("=" * 55)
    print("  VINTED FLIPPER — RAPPORT QUOTIDIEN")
    print(f"  {__import__('datetime').datetime.now():%d/%m/%Y %H:%M}")
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
    
    print(f"\n  💡 Conseil du jour: utilise 'cli.py analyze' pour analyser une annonce")
    print(f"     et 'cli.py scam' pour détecter les arnaques.")
    print()

if __name__ == "__main__":
    main()
