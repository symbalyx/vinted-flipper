#!/usr/bin/env python3
"""
Niche Finder v1 — Analyse les tendances Vinted pour trouver les niches du moment.
Identifie les articles avec forte demande et faible offre.

Méthodes d'analyse:
  1. Ratio favoris/temps → demande instantanée
  2. Prix moyen par marque×catégorie → tendance prix
  3. Articles avec +50 favoris mais encore disponibles → pénurie
  4. Marques émergentes (croissance favoris vs âge du compte)
  5. Saisonnalité: ce qui se vend MAINTENANT vs dans 30 jours
"""
import json, sys, math, os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict

BASE_DIR = Path(__file__).parent.parent.resolve()
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"


class NicheFinder:
    """Analyse les données Vinted pour trouver les niches rentables."""

    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.cache_dir = self.data_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.items: List[Dict] = []
        self.analysis = {}

    def load_scraped(self, file_path: str = None) -> int:
        """Charge les résultats d'un scraping."""
        if file_path:
            path = Path(file_path)
            if path.exists():
                data = json.loads(path.read_text())
                if isinstance(data, list):
                    self.items = data
                elif isinstance(data, dict):
                    self.items = data.get("items", data.get("results", []))
                return len(self.items)

        # Chercher dans le cache les fichiers récents
        if self.cache_dir.exists():
            files = sorted(self.cache_dir.glob("*.json"), key=os.path.getmtime, reverse=True)
            for f in files[:5]:
                try:
                    data = json.loads(f.read_text())
                    items = data.get("items", []) if isinstance(data, dict) else data
                    if items:
                        self.items.extend(items)
                except:
                    pass

        return len(self.items)

    def analyze(self, force: bool = False) -> Dict[str, Any]:
        """Analyse complète des niches."""
        if not self.items:
            return {"error": "Aucune donnée. Utilise load_scraped() d'abord."}

        results = {}

        # 1. Top marques par fréquence
        results["top_brands"] = self._brand_frequency()

        # 2. Top catégories par demande (favoris)
        results["top_categories"] = self._demand_analysis()

        # 3. Articles avec forte demande (favoris élevés)
        results["high_demand_items"] = self._high_demand_items()

        # 4. Niches rentables (bon prix / forte demande)
        results["profitable_niches"] = self._profitable_niches()

        # 5. Marques émergentes
        results["emerging_brands"] = self._emerging_brands()

        # 6. Recommandations shopping
        results["shopping_tips"] = self._shopping_tips()

        # 7. Analyse saisonnière
        results["seasonal"] = self._seasonal_advice()

        self.analysis = results
        return results

    def _brand_frequency(self) -> List[Dict]:
        """Top marques trouvées."""
        brands = Counter(i.get("brand", "Inconnu") for i in self.items if i.get("brand"))
        total = sum(brands.values())
        return [{"brand": b, "count": c, "pct": round(c / total * 100, 1)}
                for b, c in brands.most_common(15)]

    def _demand_analysis(self) -> List[Dict]:
        """Analyse la demande par catégorie."""
        # On déduit la catégorie du titre
        cat_keywords = {
            "sneakers": ["sneaker", "basket", "chaussure", "air force", "jordan", "nike", "adidas"],
            "sac": ["sac", "bag", "maroquinerie"],
            "veste": ["veste", "jacket", "blouson"],
            "doudoune": ["doudoune", "down", "puffer"],
            "manteau": ["manteau", "coat", "parka"],
            "t-shirt": ["t-shirt", "tee-shirt", "tshirt"],
            "jeans": ["jean", "jeans", "denim"],
            "pull": ["pull", "sweat", "hoodie", "sweatshirt"],
            "montre": ["montre", "watch"],
            "robe": ["robe", "dress"],
            "maillot": ["maillot", "jersey", "foot"],
        }

        cat_items = defaultdict(list)
        for item in self.items:
            title = (item.get("title", "") or "").lower()
            for cat, kws in cat_keywords.items():
                if any(kw in title for kw in kws):
                    cat_items[cat].append(item)
                    break
            else:
                cat_items["autre"].append(item)

        results = []
        for cat, items in sorted(cat_items.items(), key=lambda x: -len(x[1])):
            favs = [i.get("favourited", 0) for i in items]
            prices = [i.get("price", 0) for i in items if i.get("price", 0) > 0]
            avg_favs = sum(favs) / len(favs) if favs else 0
            avg_price = sum(prices) / len(prices) if prices else 0
            # Score de demande: favoris moyens pondéré par le nombre d'articles
            demand_score = avg_favs * math.log(len(items) + 1, 10)
            results.append({
                "categorie": cat,
                "count": len(items),
                "avg_price": round(avg_price, 0),
                "avg_favourites": round(avg_favs, 1),
                "demand_score": round(demand_score, 1),
                "total_favs": sum(favs),
            })

        return sorted(results, key=lambda x: -x["demand_score"])

    def _high_demand_items(self, min_favs: int = 20) -> List[Dict]:
        """Articles avec forte demande (beaucoup de favoris)."""
        items = sorted(
            [i for i in self.items if (i.get("favourited", 0) or 0) >= min_favs],
            key=lambda x: -x.get("favourited", 0)
        )[:20]

        result = []
        for item in items:
            price = item.get("price", 0) or 0
            favs = item.get("favourited", 0) or 0
            est_profit = price * 0.3 - 5  # Estimation rapide: +30% - frais
            result.append({
                "title": item.get("title", "?"),
                "price": price,
                "favourited": favs,
                "demand_intensity": "TRES FORTE" if favs > 100 else "FORTE" if favs > 50 else "MOYENNE",
                "est_flip_profit": round(est_profit, 0) if price > 0 else 0,
                "brand": item.get("brand", ""),
                "url": item.get("url", ""),
            })
        return result

    def _profitable_niches(self) -> List[Dict]:
        """Trouve les niches rentables: forte demande, prix accessible."""
        niches = defaultdict(lambda: {"count": 0, "total_favs": 0, "total_price": 0, "items": []})

        for item in self.items:
            brand = item.get("brand", "Inconnu").lower().strip()
            if not brand or brand in ("inconnu", "", "?", "non spécifié"):
                continue
            price = item.get("price", 0) or 0
            favs = item.get("favourited", 0) or 0
            niches[brand]["count"] += 1
            niches[brand]["total_favs"] += favs
            niches[brand]["total_price"] += price
            niches[brand]["items"].append(item)

        results = []
        for brand, data in niches.items():
            if data["count"] < 2:
                continue
            avg_price = data["total_price"] / data["count"]
            avg_favs = data["total_favs"] / data["count"]
            # Score: favoris moyens par article / prix moyen * 100
            # Un article à 30€ avec 50 favoris > un article à 300€ avec 50 favoris
            if avg_price > 0 and avg_favs > 0:
                score = (avg_favs / avg_price) * data["count"]
                results.append({
                    "brand": brand.title(),
                    "count": data["count"],
                    "avg_price": round(avg_price, 0),
                    "avg_favourites": round(avg_favs, 1),
                    "demand_per_euro": round(avg_favs / avg_price, 3),
                    "niche_score": round(score, 1),
                })

        return sorted(results, key=lambda x: -x["niche_score"])[:15]

    def _emerging_brands(self) -> List[Dict]:
        """Marques qui montent (beaucoup de favoris pour peu d'articles)."""
        brands = defaultdict(lambda: {"count": 0, "total_favs": 0, "total_views": 0})

        for item in self.items:
            brand = item.get("brand", "").lower().strip()
            if not brand:
                continue
            brands[brand]["count"] += 1
            brands[brand]["total_favs"] += item.get("favourited", 0) or 0
            brands[brand]["total_views"] += item.get("views", 0) or 0

        results = []
        for brand, data in brands.items():
            if data["count"] < 1 or data["count"] > 20:
                continue
            avg_favs = data["total_favs"] / data["count"]
            if avg_favs > 10:
                results.append({
                    "brand": brand.title(),
                    "count": data["count"],
                    "avg_favourites": round(avg_favs, 1),
                    "total_favs": data["total_favs"],
                    "potential": "NICHE CHAUDE" if avg_favs > 30 else "INTERESSANT" if avg_favs > 15 else "A SURVEILLER",
                })

        return sorted(results, key=lambda x: -x["avg_favourites"])[:10]

    def _shopping_tips(self) -> List[str]:
        """Conseils shopping basés sur l'analyse."""
        tips = []
        if not self.analysis:
            return tips

        top_cats = self.analysis.get("top_categories", [])
        if top_cats:
            hot_cat = top_cats[0]
            tips.append(f"La catégorie {hot_cat['categorie']} a la + forte demande "
                       f"(moy. {hot_cat['avg_favourites']:.0f} fav, {hot_cat['count']} articles).")

        high_demand = self.analysis.get("high_demand_items", [])
        if high_demand:
            top_item = high_demand[0]
            tips.append(f"Article le + demandé: {top_item['title'][:40]} "
                       f"({top_item['favourited']} fav, {top_item['price']:.0f}€).")

        niches = self.analysis.get("profitable_niches", [])
        if niches:
            top_niche = niches[0]
            tips.append(f"Niche la + rentable: {top_niche['brand']} "
                       f"({top_niche['avg_favourites']:.0f} fav en moyenne, {top_niche['avg_price']:.0f}€).")

        # Conseils généraux
        tips.append("Privilégie les articles avec +20 favoris encore disponibles → forte demande non satisfaite.")
        tips.append("Ratio fav/prix > 1 = bonne affaire potentielle. > 3 = niche chaude.")
        tips.append("Marques avec peu d'annonces mais bcp de favoris = niche émergente, peu de concurrence.")

        return tips

    def _seasonal_advice(self) -> str:
        """Conseil saisonnier."""
        month = datetime.now().month
        season_map = {
            1: "Hiver: doudounes, manteaux, pulls. Achete articles d'ete en solde.",
            2: "Fevrier: encore l'hiver. Commence a chercher les articles de printemps.",
            3: "Mars: transition. Vends vestes mi-saison. Stocke robes et t-shirts.",
            4: "Avril: printemps. Vends trenchs, blousons. Achete pour l'ete.",
            5: "Mai: printemps avance. Vends robes, baskets. Les vestes d'hiver sont invendables.",
            6: "Juin: ete arrive. Vends maillots, shorts. Achete articles d'automne en vide-grenier.",
            7: "Juillet: basse saison Vinted. Achete en lot, revends en septembre.",
            8: "Aout: prepare la rentree. Vends sacs a dos, fournitures. Achete pulls, vestes.",
            9: "Septembre: RENTREE. Forte demande: sweats, pulls, vestes, chemises.",
            10: "Octobre: l'hiver arrive. Vends doudounes, parkas, boots.",
            11: "Novembre: BLACK FRIDAY. Vends accessoires, bijoux, sacs, electronique.",
            12: "Decembre: FETES. Vends robes soiree, costumes, accessoires de fete.",
        }
        return season_map.get(month, "Saison non déterminée.")

    def report(self) -> str:
        """Rapport complet des niches du moment."""
        if not self.analysis:
            self.analyze()

        lines = [f"── NICHES DU MOMENT ({datetime.now():%d/%m/%Y}) ──"]

        # Stats générales
        lines.append(f"\n{len(self.items)} articles analyses")

        # Top catégories
        cats = self.analysis.get("top_categories", [])
        if cats:
            lines.append(f"\nCategories les + demandeuses:")
            for c in cats[:5]:
                bar = "█" * max(1, int(c["demand_score"] / 10))
                lines.append(f"  {c['categorie']:12s} {bar} (moy. {c['avg_favourites']:.0f} fav)")

        # Top niches rentables
        niches = self.analysis.get("profitable_niches", [])
        if niches:
            lines.append(f"\nNiches rentables (demande/prix):")
            for n in niches[:8]:
                lines.append(f"  {n['brand']:20s} {n['avg_favourites']:>4.0f} fav "
                           f"| {n['avg_price']:>4.0f}€ | score: {n['niche_score']:.0f}")

        # Articles forte demande
        high = self.analysis.get("high_demand_items", [])
        if high:
            lines.append(f"\nArticles les + demandes dispo:")
            for h in high[:5]:
                lines.append(f"  {h['title'][:45]:45s} {h['price']:>5.0f}€ ❤️{h['favourited']:>4d} "
                           f"{h['demand_intensity']}")

        # Marques émergentes
        emerging = self.analysis.get("emerging_brands", [])
        if emerging:
            lines.append(f"\nMarques emergentes (peu d'offres, forte demande):")
            for e in emerging[:5]:
                lines.append(f"  {e['brand']:20s} {e['avg_favourites']:>4.0f} fav/moy. | {e['potential']}")

        # Conseils
        tips = self.analysis.get("shopping_tips", [])
        if tips:
            lines.append(f"\nConseils:")
            for t in tips:
                lines.append(f"  - {t}")

        # Saison
        seasonal = self.analysis.get("seasonal", "")
        if seasonal:
            lines.append(f"\nSaison:")
            lines.append(f"  {seasonal}")

        return "\n".join(lines)


# ─── CLI ─────────────────────────────────────────────────────

def cmd_analyze(args):
    """Analyse les données scrapées et trouve les niches."""
    nf = NicheFinder()
    file = getattr(args, 'file', None)
    count = nf.load_scraped(file)
    if count == 0:
        print("Aucune donnee. Passe un fichier avec --file ou fais un search d'abord.")
        return
    print(f"Analyse de {count} articles...")
    nf.analyze()
    print(f"\n{nf.report()}")


def cmd_search_niches(args):
    """Cherche ET analyse en une commande."""
    query = " ".join(args.query) if hasattr(args, 'query') and args.query else ""
    if not query:
        print("Recherche: ", end="")
        query = input().strip()
    if not query:
        return

    # Chercher via le scraper
    from scripts.pro_scraper import VintedScraper
    scraper = VintedScraper()
    items = scraper.search(query, page=1, per_page=50)

    if not items:
        print("Aucun article trouve. Essaie avec set_cookie() ou un proxy.")
        return

    # Analyser
    nf = NicheFinder()
    nf.items = items
    nf.analyze()
    print(f"\n{nf.report()}")

    # Recommandations d'achat
    print(f"\nRecommandations d'achat pour '{query}':")
    high = nf.analysis.get("high_demand_items", [])
    for h in high[:5]:
        flip_est = h["est_flip_profit"]
        if flip_est > 0:
            action = "ACHETER" if flip_est > 15 else "PEUT-ETRE" if flip_est > 5 else "NON"
            print(f"  {action:10s} {h['title'][:40]:40s} {h['price']:>5.0f}€ -> est. +{flip_est:.0f}€")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Niche Finder Vinted")
    sub = parser.add_subparsers(dest="cmd")
    p_analyze = sub.add_parser("analyze", help="Analyse des donnees existantes")
    p_analyze.add_argument("--file", help="Fichier JSON scrape")
    p_search = sub.add_parser("search", help="Cherche et analyse")
    p_search.add_argument("query", nargs="*", help="Terme de recherche")

    args = parser.parse_args()
    if args.cmd == "search":
        cmd_search_niches(args)
    else:
        cmd_analyze(args)
