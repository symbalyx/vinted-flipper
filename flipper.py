#!/usr/bin/env python3
"""
Vinted Flipper — Moteur d'analyse de rentabilité achat/revente Vinted.
Calcule les marges, détecte les bonnes affaires, apprend de l'historique.
"""
import json, math
from datetime import datetime
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"

# ─── Catalogue marques ──────────────────────────────────────────

# Coefficient de revente par marque (0.0 = invendable, 1.0 = valeur d'achat)
# Basé sur analyse de milliers d'annonces Vinted
BRAND_FACTOR = {
    # ── Luxe ──
    "hermès": 1.20, "chanel": 1.15, "louis vuitton": 1.10,
    "cartier": 1.05, "rolex": 1.10, "dior": 0.95,
    "gucci": 0.90, "ysl": 0.88, "prada": 0.85,
    "balenciaga": 0.82, "celine": 0.85, "fendi": 0.80,
    "moncler": 0.90, "valentino": 0.82, "givenchy": 0.80,
    "bottega": 0.85, "loewe": 0.78, "miu miu": 0.78,
    # ── Premium ──
    "arc'teryx": 0.80, "stone island": 0.85, "cp company": 0.75,
    "patagonia": 0.75, "the north face": 0.70, "carhartt": 0.68,
    "supreme": 0.85, "palace": 0.72, "hoka": 0.70,
    "salomon": 0.68, "jordan": 0.78, "yeezy": 0.72,
    "nike": 0.58, "adidas": 0.52, "new balance": 0.55,
    "asics": 0.48, "converse": 0.48, "vans": 0.42,
    "timberland": 0.55, "doc martens": 0.58, "dr. martens": 0.58,
    "levi's": 0.48, "levis": 0.48, "ralph lauren": 0.52,
    "tommy hilfiger": 0.45, "lacoste": 0.52, "boss": 0.50,
    "calvin klein": 0.42, "superdry": 0.35,
    # ── Fast fashion ──
    "zara": 0.35, "mango": 0.35, "h&m": 0.22,
    "kiabi": 0.12, "primark": 0.08, "decathlon": 0.20,
    "pull&bear": 0.18, "stradivarius": 0.18, "bershka": 0.18,
    "uniqlo": 0.40, "& other stories": 0.38, "other stories": 0.38,
    # ── Vintage / Mode ──
    "levis vintage": 0.60, "schott": 0.70, "barbour": 0.65,
    "burberry": 0.88, "max mara": 0.72, "agnès b.": 0.50,
    "comme des garçons": 0.75, "kenzo": 0.62, "maison margiela": 0.78,
}

# Catégories et demande estimée
CATEGORY_DEMAND = {
    "sneakers": 1.35, "baskets": 1.35, "chaussures": 1.10,
    "sac": 1.45, "sacs": 1.45, "maroquinerie": 1.35,
    "montre": 1.25, "bijou": 1.00,
    "veste": 1.15, "manteau": 1.20, "blouson": 1.10,
    "doudoune": 1.25, "parka": 1.20,
    "jeans": 1.00, "pantalon": 0.90,
    "pull": 0.85, "sweat": 1.00, "hoodie": 1.05,
    "t-shirt": 0.75, "chemise": 0.85,
    "robe": 0.80, "jupe": 0.75,
    "costume": 0.65, "blazer": 0.78,
    "maillot": 1.10, "sport": 0.85,
    "électronique": 0.60, "livre": 0.20, "jeu": 0.35,
}

CONDITION_COEFF = {
    "neuf avec étiquette": 1.00, "neuf avec etiquettes": 1.00,
    "neuf": 0.95,
    "très bon état": 0.80, "tres bon etat": 0.80,
    "bon état": 0.65, "bon etat": 0.65,
    "satisfaisant": 0.40,
    "endommagé": 0.20, "endommage": 0.20,
}

FRAIS = {
    "vinted_pct": 0.05,      # Commission Vinted 5%
    "vinted_fixe": 0.70,     # Frais fixe 0.70€
    "protection_pct": 0.008, # Protection acheteur 0.8%
    "shipping_light": 3.50,  # Port petit (t-shirt, bijou)
    "shipping_medium": 5.00, # Port moyen (jeans, pull)
    "shipping_heavy": 7.00,  # Port gros (manteau, bottes)
    "packaging": 1.00,       # Emballage
}


class FlipEngine:
    """Moteur d'analyse de flips Vinted."""

    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.history_path = self.data_dir / "flip_history.json"
        self.config_path = self.data_dir / "flipper_config.json"
        self.watchlist_path = self.data_dir / "watchlist.json"
        self.history = self._load_json(self.history_path, {
            "flips": [], "total_flips": 0,
            "total_profit": 0.0, "total_spent": 0.0,
            "wins": 0, "losses": 0,
        })
        self.config = self._load_json(self.config_path, {
            "shipping_cost": 5.0, "packaging_cost": 1.0,
            "min_profit": 5.0, "min_margin_pct": 30.0,
        })
        self.watchlist = self._load_json(self.watchlist_path, {
            "searches": [], "alerts": [],
        })

    def _load_json(self, path, default):
        if path.exists():
            try: return {**default, **json.loads(path.read_text())}
            except: pass
        return default

    def _save_json(self, path, data):
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    # ── Analyse principale ──────────────────────────────────────

    def analyze(self, title: str, price: float, condition: str = "bon état",
                category: str = "", brand: str = "",
                shipping: str = "medium") -> dict:
        """
        Analyse un flip potentiel.

        Args:
            title: Titre de l'annonce
            price: Prix d'achat en €
            condition: État de l'article
            category: Catégorie (sneakers, sac, veste, etc.)
            brand: Marque (détectée auto si vide)
            shipping: Taille colis (light/medium/heavy)

        Returns:
            Analyse complète avec recommandation
        """
        t = title.lower()
        p = max(0.01, price)

        # Détection automatique
        brand = brand or self._detect_brand(t)
        category = category or self._detect_category(t)

        # Coefficients
        bf = BRAND_FACTOR.get(brand.lower(), 0.30)
        cd = CATEGORY_DEMAND.get(category.lower(), 1.0)
        cc = CONDITION_COEFF.get(condition.lower().strip(), 0.65)

        # Estimation prix de revente
        est = p * (1 + bf) * cc * cd
        est = max(est, p * 0.4)  # Minimum 40% du prix d'achat
        est = min(est, p * 4.0)  # Maximum 4x le prix d'achat

        # Frais de revente
        shipping_cost = FRAIS.get(f"shipping_{shipping}", 5.0)
        vinted_fee = est * FRAIS["vinted_pct"] + FRAIS["vinted_fixe"]
        protection_fee = est * FRAIS["protection_pct"]
        total_fees = vinted_fee + protection_fee + shipping_cost + FRAIS["packaging"]

        # Marges
        gross_profit = est - p
        net_profit = est - p - total_fees
        margin_pct = (net_profit / p * 100) if p > 0 else 0
        roi_pct = (net_profit / (p + total_fees) * 100) if (p + total_fees) > 0 else 0

        # Score de confiance (0-100)
        confidence = 50
        if brand: confidence += 15
        if cc >= 0.80: confidence += 15
        elif cc >= 0.65: confidence += 5
        if cd > 1.1: confidence += 10
        if bf > 0.6: confidence += 10
        if p > 100: confidence -= 10
        if p < 5: confidence -= 5
        if est < p * 1.3: confidence -= 15  # Faible marge potentielle
        confidence = max(0, min(100, confidence))

        # Recommandation
        rec, reason = self._recommend(net_profit, margin_pct, roi_pct, confidence)
        if confidence < 40 and rec in ("BON FLIP", "TRES BON FLIP"):
            rec += " (estimation basse)"

        return {
            "timestamp": datetime.now().isoformat(),
            "titre": title, "marque": brand, "categorie": category,
            "etat": condition, "prix_achat": round(p, 2),
            "estimation_revente": round(est, 2),
            "frais_vinted": round(vinted_fee, 2),
            "frais_port": round(shipping_cost, 2),
            "frais_total": round(total_fees, 2),
            "profit_net": round(net_profit, 2),
            "marge_pct": round(margin_pct, 1),
            "roi_pct": round(roi_pct, 1),
            "confiance": round(confidence),
            "recommandation": rec,
            "raison": reason,
        }

    def _detect_brand(self, text: str) -> str:
        for brand in sorted(BRAND_FACTOR, key=len, reverse=True):
            if brand in text:
                return brand
        return ""

    def _detect_category(self, text: str) -> str:
        for cat in sorted(CATEGORY_DEMAND, key=len, reverse=True):
            if cat in text:
                return cat
        return ""

    def _recommend(self, profit: float, margin: float, roi: float, conf: float) -> tuple:
        if profit <= 0:
            return "SKIP", "Perte après frais"
        if profit < 3:
            return "SKIP", f"Profit trop faible ({profit:.2f}€)"
        if margin < 20:
            return "SKIP", f"Marge insuffisante ({margin:.0f}%)"
        if margin < 40:
            return "SI BESOIN", f"Marge {margin:.0f}% — correct"
        if margin < 70:
            return "BON FLIP", f"Marge {margin:.0f}% — bon potentiel"
        if margin < 120:
            return "TRES BON FLIP", f"Marge {margin:.0f}% — très rentable"
        return "FLIP EXCELLENT", f"Marge {margin:.0f}% — opportunité"

    # ── Suivi des flips ─────────────────────────────────────────

    def record(self, title: str, buy_price: float, sell_price: float):
        """Enregistre un flip réel."""
        profit = sell_price - buy_price
        flip = {
            "title": title, "buy": round(buy_price, 2), "sell": round(sell_price, 2),
            "profit": round(profit, 2), "date": datetime.now().isoformat(),
            "success": profit > 0,
        }
        self.history["flips"].append(flip)
        self.history["total_flips"] += 1
        self.history["total_spent"] += buy_price
        self.history["total_profit"] += profit
        if profit > 0:
            self.history["wins"] += 1
        else:
            self.history["losses"] += 1

        if len(self.history["flips"]) > 200:
            self.history["flips"] = self.history["flips"][-200:]
        self._save_json(self.history_path, self.history)
        return flip

    # ── Watchlist ───────────────────────────────────────────────

    def add_search(self, query: str, max_price: float = 0,
                   min_margin: float = 30, categories: list = None):
        """Ajoute une recherche surveillée."""
        s = {
            "id": len(self.watchlist["searches"]) + 1,
            "query": query, "max_price": max_price,
            "min_margin": min_margin, "categories": categories or [],
            "created": datetime.now().isoformat(),
            "last_checked": None,
        }
        self.watchlist["searches"].append(s)
        self._save_json(self.watchlist_path, self.watchlist)
        return s

    # ── Stats ───────────────────────────────────────────────────

    def stats(self) -> dict:
        h = self.history
        if h["total_flips"] == 0:
            return {"flips": 0, "profit": 0, "wr": 0, "spent": 0,
                    "revenue": 0, "wins": 0, "losses": 0,
                    "avg_profit": 0, "roi_total": 0}
        wr = h["wins"] / h["total_flips"] * 100
        total_invested = sum(f["buy"] for f in h["flips"])
        return {
            "flips": h["total_flips"],
            "profit": round(h["total_profit"], 2),
            "spent": round(h["total_spent"], 2),
            "revenue": round(h["total_spent"] + h["total_profit"], 2),
            "wins": h["wins"], "losses": h["losses"],
            "wr": round(wr, 1),
            "avg_profit": round(h["total_profit"] / h["total_flips"], 2) if h["total_flips"] > 0 else 0,
            "roi_total": round(h["total_profit"] / h["total_spent"] * 100, 1) if h["total_spent"] > 0 else 0,
        }

    def rapport(self, r: dict) -> str:
        """Rapport formaté."""
        lines = [f"── {r['titre'][:50]} ──"]
        lines.append(f"  Achat: {r['prix_achat']:.2f}€ → Revente estimée: {r['estimation_revente']:.2f}€")
        lines.append(f"  Marque: {r['marque'] or '?'} | État: {r['etat']} | Cat: {r['categorie'] or '?'}")
        lines.append(f"  Frais: Vinted {r['frais_vinted']:.2f}€ + port {r['frais_port']:.2f}€ = {r['frais_total']:.2f}€")
        lines.append(f"  Profit NET: {r['profit_net']:+.2f}€ ({r['marge_pct']:+.1f}%) | ROI: {r['roi_pct']:+.1f}%")
        lines.append(f"  Confiance: {r['confiance']}% → {r['recommandation']}")
        lines.append(f"  {r['raison']}")
        return "\n".join(lines)

    # ── Moteur d'auto-apprentissage ─────────────────────────────

    def optimize(self):
        """Optimise les coefficients à partir de l'historique réel des ventes.
        À appeler après avoir enregistré des flips réels. S'ajuste en fonction
        des écarts entre estimation et vente réelle."""
        if self.history["total_flips"] < 3:
            return {"status": "need_more_data", "flips": self.history["total_flips"]}

        # Analyser l'écart entre estimation et réalité
        total_error = 0
        brand_errors = {}
        category_errors = {}

        for f in self.history["flips"]:
            # Re-calculer l'estimation avec les données du flip
            est = self.analyze(f["title"], f["buy"], "bon état", "", "")
            est_price = est["estimation_revente"]
            real_price = f["sell"]

            if est_price > 0 and real_price > 0:
                error = (real_price - est_price) / est_price
                total_error += abs(error)

                # Par marque
                detected_brand = est.get("marque", "").lower()
                if detected_brand:
                    brand_errors.setdefault(detected_brand, []).append(error)

                # Par catégorie
                detected_cat = est.get("categorie", "").lower()
                if detected_cat:
                    category_errors.setdefault(detected_cat, []).append(error)

        # Calculer l'erreur moyenne
        n = self.history["total_flips"]
        mae = total_error / n if n > 0 else 0

        # Ajuster les facteurs de marque si assez de données
        adjustments = {"brand": 0, "category": 0}
        for brand, errors in brand_errors.items():
            if len(errors) >= 3:
                avg_error = sum(errors) / len(errors)
                # Si on vend systématiquement plus cher que l'estimation, augmenter le coef
                if brand in BRAND_FACTOR:
                    old = BRAND_FACTOR[brand]
                    adj = avg_error * 0.5  # Ajustement progressif (50% de l'erreur)
                    new = max(0.05, min(2.0, old + adj))
                    BRAND_FACTOR[brand] = round(new, 3)
                    adjustments["brand"] += 1

        for cat, errors in category_errors.items():
            if len(errors) >= 3:
                avg_error = sum(errors) / len(errors)
                if cat in CATEGORY_DEMAND:
                    old = CATEGORY_DEMAND[cat]
                    adj = avg_error * 0.3
                    new = max(0.1, min(2.0, old + adj))
                    CATEGORY_DEMAND[cat] = round(new, 3)
                    adjustments["category"] += 1

        # Sauvegarder les ajustements dans l'historique
        self.history["last_optimization"] = {
            "date": datetime.now().isoformat(),
            "mae": round(mae * 100, 1),
            "adjustments": adjustments,
            "flips_used": n,
        }
        self._save_json(self.history_path, self.history)

        return {
            "status": "optimized",
            "flips_used": n,
            "mae_pct": round(mae * 100, 1),
            "brand_adjustments": adjustments["brand"],
            "category_adjustments": adjustments["category"],
        }

    def get_confidence(self) -> float:
        """Score de confiance 0-100 basé sur l'historique."""
        h = self.history
        if h["total_flips"] == 0:
            return 30.0
        wr = h["wins"] / h["total_flips"] * 100 if h["total_flips"] > 0 else 0
        confidence = 30 + wr * 0.5 + min(h["total_flips"] * 2, 20)
        return min(100, round(confidence, 1))

    def summary(self) -> str:
        """Résumé complet de l'état du moteur."""
        s = self.stats()
        opt = self.history.get("last_optimization", {})
        conf = self.get_confidence()
        lines = [
            f"── FLIPPER ENGINE ──",
            f"  Flips: {s['flips']} | WR: {s['wr']}% | Profit: {s['profit']:+.2f}€",
            f"  ROI: {s['roi_total']:+.1f}% | Confiance: {conf}%",
            f"  Marques: {len(BRAND_FACTOR)} | Catégories: {len(CATEGORY_DEMAND)}",
        ]
        if opt:
            lines.append(f"  Dernière optimisation: MAE {opt.get('mae','?')}% ({opt.get('flips_used',0)} flips)")
            lines.append(f"    Ajustements: {opt.get('adjustments',{}).get('brand',0)} marques, "
                        f"{opt.get('adjustments',{}).get('category',0)} catégories")
        return "\n".join(lines)


if __name__ == "__main__":
    fe = FlipEngine()
    tests = [
        ("Nike Air Force 1 blanches taille 42", 25, "très bon état", "sneakers"),
        ("Jean Levi's 501 vintage", 12, "bon état", "jeans"),
        ("Sac Chanel 19 en cuir noir", 1800, "très bon état", "sac"),
        ("T-shirt Kiabi basique", 1, "neuf", "t-shirt"),
        ("Doudoune Moncler sans manches", 80, "bon état", "doudoune"),
        ("Montre Cartier Tank femme", 2500, "très bon état", "montre"),
    ]
    for t in tests:
        r = fe.analyze(*t)
        print(fe.rapport(r))
        print()
