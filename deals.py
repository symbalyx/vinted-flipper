#!/usr/bin/env python3
"""
Vinted Flipper — Deal Finder.
Analyse toutes les marques × catégories, classe les opportunités,
et te dit EXACTEMENT quoi chercher pour gagner de l'argent.
"""
import json, math, sys
from datetime import datetime
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BASE_DIR))
from flipper import FlipEngine, BRAND_FACTOR, CATEGORY_DEMAND, FRAIS


class DealFinder:
    """Analyseur d'opportunités — trouve les flips les plus rentables."""

    def __init__(self):
        self.fe = FlipEngine()
        self.opportunities = []

    def scan_all(self, min_margin: float = 20.0,
                 max_price: float = 500.0,
                 min_profit: float = 8.0) -> list:
        """Analyse toutes les combinaisons marque × catégorie × prix.
        
        Classe les opportunités par score de rentabilité.
        
        Args:
            min_margin: Marge minimum (%) pour être considéré
            max_price: Prix d'achat maximum
            min_profit: Profit net minimum en €
            
        Returns:
            Liste d'opportunités classées par score
        """
        self.opportunities = []
        
        # Prix d'achat RÉALISTES par segment de marque
        # (basé sur les prix qu'on trouve VRAIMENT sur Vinted)
        realistic_prices = {
            # Luxe: minimum 200-500€
            "hermès": [500, 800, 1200],
            "chanel": [300, 500, 800],
            "louis vuitton": [200, 400, 600],
            "rolex": [2000, 3000, 5000],
            "cartier": [500, 1000, 2000],
            "dior": [200, 400],
            "gucci": [100, 200, 300],
            "balenciaga": [100, 200],
            "prada": [100, 200],
            "fendi": [100, 200],
            "moncler": [80, 150, 250],
            "stone island": [60, 100, 150],
            # Premium: 30-150€
            "arc'teryx": [50, 80, 120],
            "patagonia": [30, 50, 80],
            "the north face": [30, 50, 80],
            "carhartt": [25, 40, 60],
            "supreme": [50, 80, 120],
            "nike": [20, 35, 50],
            "adidas": [15, 25, 40],
            "new balance": [20, 35, 50],
            "salomon": [30, 50, 70],
            "jordan": [30, 50, 80],
            "levi's": [10, 15, 25],
            "levis": [10, 15, 25],
            "timberland": [30, 50],
            "doc martens": [30, 50, 70],
            # Fast fashion (bas prix, volume)
            "zara": [5, 10, 15],
            "mango": [5, 10, 15],
            "pull&bear": [3, 6, 10],
            "stradivarius": [3, 6, 10],
            "bershka": [3, 6, 10],
            "uniqlo": [8, 12, 18],
            "h&m": [3, 6, 10],
        }
        
        # États testés
        conditions = ["très bon état", "bon état"]
        
        # Catégories les plus demandées (top 15)
        top_categories = sorted(CATEGORY_DEMAND.keys(), key=lambda c: -CATEGORY_DEMAND[c])[:15]
        
        for brand in BRAND_FACTOR:
            bf = BRAND_FACTOR[brand]
            
            # Prix réalistes pour cette marque (ou fallback)
            prices = realistic_prices.get(brand, [20, 35, 50])
            
            for cat in top_categories:
                cd = CATEGORY_DEMAND.get(cat, 1.0)
                
                for price in prices:
                    if price > max_price:
                        continue
                    
                    for cond in conditions:
                        # Simulation de l'analyse
                        result = self.fe.analyze(
                            f"{brand.title()} {cat}", price, cond, cat, brand
                        )
                        
                        if result["profit_net"] >= min_profit and result["marge_pct"] >= min_margin:
                            # Score composé
                            profit_score = min(result["profit_net"] / 50, 2.0) * 40
                            margin_score = min(result["marge_pct"] / 100, 2.0) * 30
                            confidence_score = result["confiance"] * 0.3
                            
                            total_score = profit_score + margin_score + confidence_score
                            
                            self.opportunities.append({
                                "brand": brand,
                                "category": cat,
                                "condition": cond,
                                "buy_price": price,
                                "est_sell": result["estimation_revente"],
                                "profit_net": result["profit_net"],
                                "margin_pct": result["marge_pct"],
                                "roi_pct": result["roi_pct"],
                                "confidence": result["confiance"],
                                "score": round(total_score, 1),
                                "label": result["recommandation"],
                            })
        
        # Trier par score descendant
        self.opportunities.sort(key=lambda o: -o["score"])
        
        # Enlever les doublons (garder le meilleur pour chaque marque×catégorie)
        seen = set()
        unique_by_segment = {"low": [], "mid": [], "high": []}
        for o in self.opportunities:
            key = f"{o['brand']}_{o['category']}_{o['condition']}"
            if key not in seen:
                seen.add(key)
                if o["buy_price"] <= 40:
                    unique_by_segment["low"].append(o)
                elif o["buy_price"] <= 100:
                    unique_by_segment["mid"].append(o)
                else:
                    unique_by_segment["high"].append(o)
        
        # Prendre les meilleurs de chaque segment
        self.opportunities = (
            sorted(unique_by_segment["low"], key=lambda x: -x["score"])[:15] +
            sorted(unique_by_segment["mid"], key=lambda x: -x["score"])[:20] +
            sorted(unique_by_segment["high"], key=lambda x: -x["score"])[:15]
        )
        return self.opportunities

    def get_top_opportunities(self, n: int = 10) -> list:
        """Retourne les top N opportunités."""
        if not self.opportunities:
            self.scan_all()
        return self.opportunities[:n]

    def get_recommended_searches(self, n: int = 10) -> list:
        """Génère les recherches Vinted à faire."""
        tops = self.get_top_opportunities(n)
        searches = []
        
        for o in tops:
            brand = o["brand"].title()
            cat = o["category"].title()
            
            # Générer des termes de recherche optimisés
            search_terms = [
                f"{brand} {cat}",
                f"{brand}",
            ]
            
            # Ajouter des mots-clés selon la catégorie
            cat_keywords = {
                "sneakers": ["baskets", "chaussures"],
                "sac": ["sac", "maroquinerie"],
                "veste": ["veste", "blouson"],
                "doudoune": ["doudoune", "parka"],
                "montre": ["montre", "bracelet"],
                "jeans": ["jean", "denim"],
                "t-shirt": ["t-shirt", "tee-shirt"],
            }
            
            for kw in cat_keywords.get(o["category"], []):
                search_terms.append(f"{brand} {kw}")
            
            searches.append({
                "brand": o["brand"],
                "category": o["category"],
                "searches": search_terms[:3],
                "buy_price_max": round(o["buy_price"] * 1.3),
                "est_profit": o["profit_net"],
                "est_margin": o["margin_pct"],
                "confidence": o["confidence"],
            })
        
        return searches

    def daily_plan(self, budget: float = 200.0) -> dict:
        """Génère un plan d'action quotidien avec un budget donné.
        
        Adapte les recommandations au budget : 
        - Petit budget (<100€) : premium abordable (Arc'teryx, Nike, Carhartt)
        - Budget moyen (100-500€) : mix premium + luxe accessible
        - Gros budget (500€+) : luxe
        """
        tops = self.get_top_opportunities(50)
        
        # Segmenter par prix d'achat
        cheap = [o for o in tops if o["buy_price"] <= 40]  # < 40€
        medium = [o for o in tops if 40 < o["buy_price"] <= 100]  # 40-100€
        expensive = [o for o in tops if o["buy_price"] > 100]  # > 100€
        
        # Adapter au budget
        if budget < 100:
            candidates = cheap + medium[:5]
        elif budget < 500:
            candidates = cheap + medium + expensive[:5]
        else:
            candidates = cheap + medium + expensive
        
        # Filtrer par score et accessibilité
        candidates = [o for o in candidates if o["score"] > 50]
        
        # Sélectionner les meilleurs dans le budget
        total_invest = 0
        total_profit = 0
        plan = []
        
        for o in sorted(candidates, key=lambda x: -x["score"]):
            if total_invest + o["buy_price"] <= budget:
                plan.append(o)
                total_invest += o["buy_price"]
                total_profit += o["profit_net"]
        
        # Si pas assez d'articles sélectionnés (luxe trop cher), 
        # compléter avec des articles moins chers
        if len(plan) < 2:
            for o in cheap:
                if o not in plan and total_invest + o["buy_price"] <= budget:
                    plan.append(o)
                    total_invest += o["buy_price"]
                    total_profit += o["profit_net"]
        
        # Temps de revente estimé selon le segment
        avg_price = total_invest / max(len(plan), 1)
        if avg_price < 50:
            time_to_sell = "3-10 jours"
        elif avg_price < 150:
            time_to_sell = "7-21 jours"
        else:
            time_to_sell = "14-45 jours"
        
        return {
            "budget": budget,
            "total_invest": round(total_invest, 2),
            "total_profit_est": round(total_profit, 2),
            "roi_est": round(total_profit / total_invest * 100, 1) if total_invest > 0 else 0,
            "items_to_buy": len(plan),
            "time_to_sell": time_to_sell,
            "avg_price_per_item": round(avg_price, 0),
            "plan": plan,
        }

    def report(self, budget: float = 200.0) -> str:
        """Rapport complet avec recherches actionnables.
        Adapté au budget pour des conseils réalistes."""
        
        # Analyser TOUTES les opportunités
        self.scan_all()
        
        lines = []
        lines.append(f"── DEAL FINDER — Rapport Opportunités ──")
        lines.append(f"  Budget: {budget:.0f}€ | {len(self.opportunities)} opportunités trouvées")
        lines.append("")
        
        # ── STRATÉGIE : Petits flips rapides (< 40€ achat) ──
        small = [o for o in self.opportunities if o["buy_price"] <= 40][:8]
        if small:
            lines.append(f"  🔥 FLIPS RAPIDES (achat < 40€, revente sous 3-10 jours)")
            lines.append(f"  {'':4s}{'Marque':<18s}{'Article':<14s}{'Achat':>8}{'→ Revente':>10}{'Profit':>8}{'Marge':>7}")
            lines.append(f"  {'':4s}{'-'*60}")
            for o in small[:5]:
                lines.append(f"  {'':4s}{o['brand'].title():<18s}{o['category']:<14s}"
                            f"{o['buy_price']:>4.0f}€ → {o['est_sell']:>5.0f}€ "
                            f"{o['profit_net']:>+6.2f}€ {o['margin_pct']:>+5.0f}%")
            lines.append("")
        
        # ── STRATÉGIE : Flips confortables (40-100€ achat) ──
        medium = [o for o in self.opportunities if 40 < o["buy_price"] <= 100][:8]
        if medium:
            lines.append(f"  💰 FLIPS CONFORTABLES (achat 40-100€, revente sous 7-21 jours)")
            lines.append(f"  {'':4s}{'Marque':<18s}{'Article':<14s}{'Achat':>8}{'→ Revente':>10}{'Profit':>8}{'Marge':>7}")
            lines.append(f"  {'':4s}{'-'*60}")
            for o in medium[:5]:
                lines.append(f"  {'':4s}{o['brand'].title():<18s}{o['category']:<14s}"
                            f"{o['buy_price']:>4.0f}€ → {o['est_sell']:>5.0f}€ "
                            f"{o['profit_net']:>+6.2f}€ {o['margin_pct']:>+5.0f}%")
            lines.append("")
        
        # ── STRATÉGIE : Luxe (100€+ achat) ──
        large = [o for o in self.opportunities if 100 < o["buy_price"]][:8]
        if large and budget >= 300:
            lines.append(f"  👑 LUXE (achat 100€+, revente sous 14-45 jours)")
            lines.append(f"  {'':4s}{'Marque':<18s}{'Article':<14s}{'Achat':>8}{'→ Revente':>10}{'Profit':>8}{'Marge':>7}")
            lines.append(f"  {'':4s}{'-'*60}")
            for o in large[:3]:
                lines.append(f"  {'':4s}{o['brand'].title():<18s}{o['category']:<14s}"
                            f"{o['buy_price']:>4.0f}€ → {o['est_sell']:>5.0f}€ "
                            f"{o['profit_net']:>+8.2f}€ {o['margin_pct']:>+5.0f}%")
            lines.append("")
        
        # ── RECHERCHES À COPIER-COLLER ──
        lines.append(f"  🔍 RECHERCHES À FAIRE SUR VINTED AUJOURD'HUI")
        
        # Recherches rapides
        for o in small[:3]:
            brand = o['brand'].title()
            cat = o['category'].lower()
            max_price = int(o['buy_price'] * 1.3)
            lines.append(f"    • « {brand} {cat} » — max {max_price}€ → est. +{o['profit_net']:.0f}€")
        
        # Recherches confortables
        for o in medium[:2]:
            brand = o['brand'].title()
            cat = o['category'].lower()
            max_price = int(o['buy_price'] * 1.3)
            lines.append(f"    • « {brand} {cat} » — max {max_price}€ → est. +{o['profit_net']:.0f}€")
        
        lines.append("")
        
        # ── PLAN D'ACTION ──
        plan = self.daily_plan(budget=budget)
        lines.append(f"  🎯 PLAN DU JOUR ({budget:.0f}€)")
        if plan['items_to_buy'] > 0:
            lines.append(f"     Acheter {plan['items_to_buy']} articles pour {plan['total_invest']:.0f}€")
            lines.append(f"     Profit estimé: +{plan['total_profit_est']:.0f}€ (ROI {plan['roi_est']:+.0f}%)")
            lines.append(f"     Revente sous {plan['time_to_sell']}")
            lines.append(f"     Prix moyen/article: {plan['avg_price_per_item']:.0f}€")
            lines.append("")
            lines.append(f"     Liste d'achat:")
            for i, p in enumerate(plan['plan'][:8], 1):
                lines.append(f"     {i}. {p['brand'].title():15s} {p['category']:12s} "
                            f"~{p['buy_price']:.0f}€ → ~{p['est_sell']:.0f}€ "
                            f"(+{p['profit_net']:.0f}€)")
            
            # Projection
            daily = plan['total_profit_est']
            weekly = daily * 5
            monthly = daily * 22
            lines.append("")
            lines.append(f"     PROJECTION:")
            lines.append(f"     1 jour:    +{daily:.0f}€")
            lines.append(f"     1 semaine: +{weekly:.0f}€ (5j)")
            lines.append(f"     1 mois:    +{monthly:.0f}€ (22j)")
        
        return "\n".join(lines)


# ─── CLI intégré ───────────────────────────────────────────────

def cmd_deals(args):
    """Affiche les meilleures opportunités."""
    df = DealFinder()
    budget = float(getattr(args, 'budget', 200)) if args else 200
    print(f"\n{df.report(budget=budget)}")


def cmd_plan(args):
    """Génère un plan d'action avec budget."""
    df = DealFinder()
    budget = float(getattr(args, 'budget', 200)) if args else 200
    plan = df.daily_plan(budget=budget)
    
    lines = [f"── PLAN D'ACTION QUOTIDIEN (budget {budget:.0f}€) ──"]
    lines.append(f"  Budget: {budget:.0f}€")
    lines.append(f"  Investissement: {plan['total_invest']:.0f}€ ({plan['items_to_buy']} articles)")
    lines.append(f"  Profit estimé: {plan['total_profit_est']:+.2f}€")
    lines.append(f"  ROI: {plan['roi_est']:+.0f}%")
    lines.append(f"  Temps de revente estimé: {plan['time_to_sell']}")
    lines.append("")
    lines.append(f"  À ACHETER AUJOURD'HUI:")
    for i, p in enumerate(plan['plan'][:10], 1):
        lines.append(f"  {i}. {p['brand'].title():15s} {p['category']:12s} "
                    f"~{p['buy_price']:.0f}€ → ~{p['est_sell']:.0f}€ "
                    f"(+{p['profit_net']:.0f}€, marge {p['margin_pct']:.0f}%)")
    
    lines.append(f"\n  PROJECTION HEBDOMADAIRE:")
    if plan['items_to_buy'] > 0:
        daily_profit = plan['total_profit_est']
        weekly = daily_profit * 5  # 5 jours de chasse
        monthly = daily_profit * 22  # 22 jours ouvrés
        lines.append(f"  1 jour:  +{daily_profit:.0f}€")
        lines.append(f"  1 semaine: +{weekly:.0f}€ (5j)")
        lines.append(f"  1 mois:   +{monthly:.0f}€ (22j)")
        lines.append(f"  → Avec un budget de {budget:.0f}€/jour")
    
    print("\n".join(lines))


if __name__ == "__main__":
    df = DealFinder()
    print(df.report(n=10))
    print()
    cmd_plan(type('args', (), {'budget': 200})())
