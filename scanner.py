#!/usr/bin/env python3
"""
Scam Detector — Détecte les arnaques sur les annonces Vinted.
Analyse le prix, la description, le vendeur, les photos pour identifier
les signaux d'alerte. Score de confiance 0-100.
"""
import re, math
from datetime import datetime, timedelta
from typing import Optional

# ─── Seuils de détection ───────────────────────────────────────

PRICE_ANOMALY_THRESHOLD = 0.4  # Prix < 40% de la valeur estimée = alerte
MAX_SCAM_SCORE = 100

# Prix moyen estimé par catégorie pour détection des anomalies
CATEGORY_PRICE_RANGES = {
    "sneakers": (20, 200), "baskets": (20, 200),
    "sac": (30, 2000), "sacs": (30, 2000), "maroquinerie": (20, 1500),
    "montre": (20, 5000), "bijou": (10, 1000),
    "veste": (15, 300), "manteau": (20, 400), "doudoune": (25, 350),
    "jeans": (10, 100), "pantalon": (8, 80),
    "pull": (8, 100), "sweat": (10, 120), "hoodie": (10, 130),
    "t-shirt": (3, 50), "chemise": (8, 80),
    "robe": (10, 150), "jupe": (8, 80),
    "costume": (20, 300), "blazer": (15, 200),
    "maillot": (10, 100),
    "electronique": (20, 500), "jeu": (5, 50), "livre": (2, 30),
}

# Marques luxe souvent contrefaites
COUNTERFEIT_HIGH_RISK = [
    "chanel", "louis vuitton", "gucci", "hermès", "dior", "fendi",
    "prada", "balenciaga", "ysl", "cartier", "rolex", "moncler",
    "supreme", "stone island", "nike jordan", "yeezy",
]

# Phrases types d'arnaques (français)
SCAM_PHRASES = [
    "paiement hors vinted", "en dehors de vinted",
    "paiement par virement", "paiement par paypal hors vinted",
    "je n'utilise pas vinted", "vends en dehors",
    "passe par mon numéro", "contacte moi par sms",
    "envoi depuis l'étranger", "envoi depuis la chine",
    "réplique", "copie", "fausse", "contrefaçon",
    "prix trop bas pour durer", "dernière pièce",
    "vends pour un ami", "vendu pour le compte de",
    "pas de retour possible", "ni retour ni remboursement",
    "je pars à l'étranger", "déménagement urgent",
    "liquidation totale", "tout doit disparaître",
    "urgence absolue", "besoin d'argent vite",
    "motif du visa", "besoin urgent de liquidité",
    "pas le temps de faire des photos",
    "photo issue d'internet", "photo non contractuelle",
    "lot non séparable", "achète sans voir",
    "premier arrivé premier servi",
    "ne me faites pas perdre de temps",
    "prix ferme et définitif",
    "pas de négociation possible",
    "vends car trop petit",  # légitime mais souvent utilisé dans les scams
    "vends car pas utilisé",
]

# Indicateurs de compte suspect
SUSPICIOUS_ACCOUNT_INDICATORS = [
    "nouveau compte", "inscrit aujourd'hui", "inscrit hier",
    "0 avis", "0 évaluation", "nouveau membre",
    "compte créé il y a", "débutant sur vinted",
]

# Marques de luxe avec fourchette de prix réaliste
LUXURY_BRAND_PRICE_FLOOR = {
    "chanel": {"sac": 300, "veste": 400},  # Sac Chanel < 300€ = suspect
    "louis vuitton": {"sac": 250, "maroquinerie": 200},
    "hermès": {"sac": 500, "maroquinerie": 400},
    "rolex": {"montre": 2000},
    "cartier": {"montre": 1000, "bijou": 500},
    "dior": {"sac": 200},
    "gucci": {"sac": 150},
}


class ScamDetector:
    """Détecteur d'arnaques Vinted — analyse multi-facteurs."""

    def __init__(self):
        self.alertes = []

    def analyze(self, title: str = "", price: float = 0,
                description: str = "", category: str = "",
                brand: str = "", seller_rating: Optional[float] = None,
                seller_reviews: int = 0, seller_joined_days: int = 999,
                has_real_photos: Optional[bool] = None,
                is_stock_photo: Optional[bool] = None,
                seller_has_profile_pic: Optional[bool] = None,
                seller_has_verified_phone: Optional[bool] = None) -> dict:
        """
        Analyse multi-facteurs d'une annonce Vinted.

        Args:
            title: Titre de l'annonce
            price: Prix affiché
            description: Description de l'annonce
            category: Catégorie
            brand: Marque
            seller_rating: Note du vendeur (0-5)
            seller_reviews: Nombre d'avis
            seller_joined_days: Âge du compte en jours
            has_real_photos: A des photos réelles (vs stock)
            is_stock_photo: Utilise des photos issues d'internet
            seller_has_profile_pic: Le vendeur a une photo de profil
            seller_has_verified_phone: Téléphone vérifié

        Returns:
            Dict avec score de risque (0-100), alertes, recommandation
        """
        self.alertes = []
        score = 0
        t = title.lower() if title else ""
        d = description.lower() if description else ""
        b = brand.lower() if brand else ""
        c = category.lower() if category else ""

        # ═══ 1. ANALYSE PRIX ═══════════════════════════════════

        # Prix trop bas pour une marque de luxe
        if b in LUXURY_BRAND_PRICE_FLOOR and c:
            for cat_key, floor_price in LUXURY_BRAND_PRICE_FLOOR[b].items():
                if cat_key in c and price < floor_price:
                    severity = "CRITIQUE"
                    if price < floor_price * 0.5:
                        score += 35
                        self._add_alert("Prix anormalement bas", severity,
                            f"{brand.title()} {cat_key} à {price:.0f}€ — minimum réaliste: {floor_price}€")
                    elif price < floor_price:
                        score += 20
                        self._add_alert("Prix très bas pour cette marque", "ÉLEVÉ",
                            f"{brand.title()} {cat_key} à {price:.0f}€ — vérifier l'authenticité")

        # Prix trop bas par rapport à la catégorie
        if c in CATEGORY_PRICE_RANGES:
            low, high = CATEGORY_PRICE_RANGES[c]
            if price < low * 0.5 and price > 0:
                score += 15
                self._add_alert("Prix anormalement bas pour cette catégorie", "ÉLEVÉ",
                    f"{price:.0f}€ alors que la moyenne est {low}€-{high}€")
            elif price < low * 0.7 and price > 0:
                score += 8
                self._add_alert("Prix inférieur à la moyenne", "MOYEN",
                    f"{price:.0f}€ — prix moyen {low}€-{high}€")

        # Prix trop beau pour être vrai (luxe à prix bradé)
        if b in COUNTERFEIT_HIGH_RISK and price < 50 and price > 0:
            score += 25
            self._add_alert("Marque de luxe à prix ridicule", "CRITIQUE",
                f"{brand.title()} à {price:.0f}€ — très probablement une contrefaçon")

        # ═══ 2. ANALYSE DESCRIPTION ═════════════════════════════

        # Phrases d'arnaque
        for phrase in SCAM_PHRASES:
            if phrase in d:
                score += 12
                self._add_alert(f"Phrase suspecte détectée", "MOYEN",
                    f"'{phrase[:40]}...'")

        # Demande de contact hors plateforme
        outside_patterns = [
            r"(06|07)\d{8}", r"(?:\+33|0033)\d{9}",
            r"whatsapp", r"snapchat", r"instagram",
            r"mon (tel|numéro|portable|téléphone|whatsapp)",
            r"contacte moi", r"contactez moi",
            r"hors (vinted|plateforme|site)",
        ]
        for pattern in outside_patterns:
            if re.search(pattern, d):
                score += 20
                self._add_alert("Tentative de contact hors Vinted", "CRITIQUE",
                    "Le vendeur demande de passer par un canal externe — arnaque fréquente")

        # Description trop courte ou générique
        if len(description) < 20:
            score += 8
            self._add_alert("Description très courte", "MOYEN",
                f"{len(description)} caractères — description générique")
        elif len(description) < 50:
            score += 3

        # Description copiée-collée (mots répétés, phrases génériques)
        generic_openings = ["bonjour je vends", "bonjour, je vends", "vends", "à vendre"]
        if any(d.startswith(g) for g in generic_openings) and len(d) < 100:
            score += 5
            self._add_alert("Description générique", "FAIBLE",
                "Description qui semble copiée-collée")

        # ═══ 3. ANALYSE TITRE ═══════════════════════════════════

        # Titre suspect
        suspicious_title = ["urgent", "vite", "brader", "liquidation",
                          "solde", "destockage", "réplique", "copie"]
        for word in suspicious_title:
            if word in t:
                score += 5
                self._add_alert(f"Mot '{word}' dans le titre", "FAIBLE",
                    "Terme souvent utilisé dans les annonces frauduleuses")

        # ═══ 4. ANALYSE VENDEUR ════════════════════════════════

        if seller_rating is not None:
            if seller_rating < 3.0 and seller_reviews > 0:
                score += 15
                self._add_alert("Mauvaise note vendeur", "ÉLEVÉ",
                    f"Note: {seller_rating}/5 ({seller_reviews} avis)")
            elif seller_rating < 4.0 and seller_reviews > 0:
                score += 5
                self._add_alert("Note vendeur moyenne", "FAIBLE",
                    f"Note: {seller_rating}/5")

        if seller_reviews == 0:
            score += 10
            self._add_alert("Nouveau vendeur sans avis", "MOYEN",
                "Aucun avis — compte potentiellement jetable")

        # Compte récent
        if seller_joined_days < 7:
            score += 15
            self._add_alert("Compte très récent", "ÉLEVÉ",
                f"Compte créé il y a {seller_joined_days} jour(s)")
        elif seller_joined_days < 30:
            score += 5
            self._add_alert("Compte récent", "FAIBLE",
                f"Compte créé il y a {seller_joined_days} jour(s)")

        # Pas de photo de profil
        if seller_has_profile_pic is False:
            score += 5
            self._add_alert("Pas de photo de profil", "FAIBLE",
                "Le vendeur n'a pas de photo de profil")

        # Téléphone non vérifié
        if seller_has_verified_phone is False:
            score += 5
            self._add_alert("Téléphone non vérifié", "FAIBLE",
                "Le vendeur n'a pas vérifié son téléphone")

        # ═══ 5. ANALYSE PHOTOS ══════════════════════════════════

        if is_stock_photo:
            score += 20
            self._add_alert("Photo issue d'internet", "ÉLEVÉ",
                "Le vendeur utilise des photos volées — l'article réel peut être différent")

        if has_real_photos is False:
            score += 15
            self._add_alert("Aucune photo réelle", "ÉLEVÉ",
                "Photos manquantes ou génériques")

        # ═══ 6. SCORE COMPOSITE CATÉGORIE + MARQUE ═════════════

        # Marques souvent contrefaites
        if b in COUNTERFEIT_HIGH_RISK:
            score += 5
            self._add_alert("Marque fréquemment contrefaite", "FAIBLE",
                f"{brand.title()} est une marque très contrefaite — vigilance")

        # ═══ RÉSULTAT ═══════════════════════════════════════════

        score = min(score, MAX_SCAM_SCORE)

        # Niveau de risque
        if score >= 60:
            niveau = "CRITIQUE"
            recommandation = "NE PAS ACHETER — forte probabilité d'arnaque"
        elif score >= 40:
            niveau = "ÉLEVÉ"
            recommandation = "Déconseillé — risques importants, demander des photos réelles"
        elif score >= 20:
            niveau = "MOYEN"
            recommandation = "Vigilance recommandée — vérifier avant d'acheter"
        elif score >= 10:
            niveau = "FAIBLE"
            recommandation = "Quelques points de vigilance, mais probablement sûr"
        else:
            niveau = "SAIN"
            recommandation = "Annonce saine — aucun signal d'alerte"

        return {
            "score_risque": score,
            "niveau": niveau,
            "recommandation": recommandation,
            "alertes": self.alertes,
            "facteurs": {
                "prix": self._analyze_price_level(price, brand, category),
                "vendeur": "inconnu" if seller_reviews == 0 else f"{seller_rating}/5 ({seller_reviews} avis)",
                "description": f"{len(description)} caractères",
            }
        }

    def _add_alert(self, titre: str, niveau: str, detail: str):
        self.alertes.append({
            "titre": titre, "niveau": niveau, "detail": detail,
        })

    def _analyze_price_level(self, price: float, brand: str, category: str) -> str:
        b = brand.lower() if brand else ""
        c = category.lower() if category else ""
        if c in CATEGORY_PRICE_RANGES:
            low, high = CATEGORY_PRICE_RANGES[c]
            if price < low * 0.5: return "anormalement bas"
            if price < low: return "bas"
            if price > high * 1.5: return "élevé"
            if price > high: return "au-dessus du marché"
            return "dans la norme"
        return "non évalué"

    def rapport(self, r: dict) -> str:
        """Rapport formaté de l'analyse."""
        lines = []
        niveau = r['niveau']
        score = r['score_risque']

        # Couleur
        if niveau == "CRITIQUE": header = "🔴 ARNAQUE PROBABLE"
        elif niveau == "ÉLEVÉ": header = "🟠 RISQUE ÉLEVÉ"
        elif niveau == "MOYEN": header = "🟡 VIGILANCE"
        elif niveau == "FAIBLE": header = "🟢 PRESQUE SAIN"
        else: header = "✅ ANNONCE SAINE"

        lines.append(f"── Détection arnaque: {header} ──")
        lines.append(f"  Score risque: {score}/{MAX_SCAM_SCORE}")
        lines.append(f"  {r['recommandation']}")
        lines.append(f"  Vendeur: {r['facteurs']['vendeur']}")
        lines.append(f"  Prix: {r['facteurs']['prix']}")
        lines.append(f"  Description: {r['facteurs']['description']}")

        if r['alertes']:
            lines.append(f"  Alertes ({len(r['alertes'])}):")
            for a in r['alertes']:
                icon = {"CRITIQUE": "🔴", "ÉLEVÉ": "🟠", "MOYEN": "🟡", "FAIBLE": "🟢"}
                lines.append(f"    {icon.get(a['niveau'], '⚪')} {a['titre']}")
                lines.append(f"       {a['detail']}")

        return "\n".join(lines)


# ─── Exemples d'utilisation ───────────────────────────────────

def analyze_from_url(url: str, price: float, title: str = "",
                     description: str = "", seller_reviews: int = 0) -> dict:
    """Analyse rapide depuis une URL Vinted."""
    sd = ScamDetector()
    return sd.analyze(
        title=title, price=price, description=description,
        seller_reviews=seller_reviews,
    )


if __name__ == "__main__":
    sd = ScamDetector()

    # Test 1: Annonce suspecte
    r1 = sd.analyze(
        title="SAC CHANEL URGENT",
        price=45,
        description="Bonjour je vends ce sac chanel contactez moi par sms au 0612345678 pas le temps de faire des photos envoi depuis l'étranger paiement hors vinted",
        category="sac",
        brand="chanel",
        seller_reviews=0,
        seller_joined_days=2,
        is_stock_photo=True,
        seller_has_profile_pic=False,
    )
    print(sd.rapport(r1))
    print()

    # Test 2: Annonce saine
    sd2 = ScamDetector()
    r2 = sd2.analyze(
        title="Nike Air Force 1 blanches taille 42",
        price=45,
        description="Vends Nike Air Force 1 portées 2 fois, taille 42, très bon état. Boîte d'origine. Envoi soigné. Prix: 45€. Vinted Protected. N'hésitez pas à me contacter pour plus de photos.",
        category="sneakers",
        brand="nike",
        seller_reviews=35,
        seller_joined_days=365,
        has_real_photos=True,
        is_stock_photo=False,
        seller_has_profile_pic=True,
        seller_has_verified_phone=True,
    )
    print(sd2.rapport(r2))
