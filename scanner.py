#!/usr/bin/env python3
"""
Scam Detector v2 — Détection multi-couche des arnaques et fausses marques.
Apprend de chaque analyse pour s'améliorer en continu.
"""
import re, json, math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
MAX_SCAM_SCORE = 100

# ═══════════════════════════════════════════════════════════════
# BASE DE CONNAISSANCE ANTI-ARNAQUE
# ═══════════════════════════════════════════════════════════════

# ─── 1. DÉTECTION DES FAUSSES MARQUES ─────────────────────────

# Mots-clés indiquant une contrefaçon dans le titre
FAKE_BRAND_TITLE_KEYWORDS = [
    "réplique", "replique", "copie", "fake", "fausse", "faux",
    "contrefaçon", "contrefacon", "imitation", "simili",
    "inspiré de", "inspire de", "inspiré", "inspire",
    "style", "type", "version", "modèle de", "modele de",
    "1:1", "1/1", "AAA", "AAA+", "AAAA", "qualité supérieure",
    "qualite superieure", "qualité premium", "qualite premium",
    "usine", "factory", "direct usine", "d'usine",
    "sans marque", "no brand", "pas de marque",
    "dupe", "duplicate", "homologue", "alternative",
    "même qualité", "meme qualite", "même que",
]

# Détection des marques luxe suspectes par anomalie prix
LUXURY_BRANDS = [
    "chanel", "louis vuitton", "hermès", "hermes", "gucci",
    "dior", "ysl", "saint laurent", "prada", "balenciaga",
    "fendi", "celine", "givenchy", "valentino", "loewe",
    "bottega", "cartier", "rolex", "moncler", "supreme",
    "stone island", "off-white", "offwhite", "balmain",
]

# Marques qui n'existent pas ou sont des arnaques connues
KNOWN_FAKE_BRANDS = [
    "abibas", "adibas", "adidas style", "nike style",
    "puma style", "channel", "lui vitton", "louis vuiton",
    "louis vuitton style", "gucci style", "dolce gabana",
    "dolce gabbana style", "versace style", "armany",
    "armani style", "hugo boss style", "boss style",
    "calvin clein", "calvin klein style", "tommy hilfiger style",
    "ralph lauren style", "levis style", "superme",
    "sapreme", "supreme style", "yeezy style", "nike air max style",
    "air jordan style", "jordan style", "moncler style",
    "canada goose style", "north face style",
]

# Marques fréquemment contrefaites (nécessitent vigilance)
COUNTERFEIT_RISK_BRANDS = {
    "chanel": 0.95, "louis vuitton": 0.95, "hermès": 0.93, "hermes": 0.93,
    "rolex": 0.95, "cartier": 0.90, "dior": 0.85, "gucci": 0.85,
    "balenciaga": 0.80, "prada": 0.80, "fendi": 0.78,
    "moncler": 0.75, "supreme": 0.85, "stone island": 0.70,
    "off-white": 0.85, "offwhite": 0.85, "yeezy": 0.70,
    "nike": 0.40, "air jordan": 0.65, "jordan": 0.65,
}

# ─── 2. PRIX MINIMUM RÉALISTE PAR MARQUE + CATÉGORIE ──────────

LUXURY_PRICE_FLOOR = {
    "chanel": {"sac": 200, "maroquinerie": 150, "bijou": 100, "montre": 500},
    "louis vuitton": {"sac": 150, "maroquinerie": 100, "bijou": 80},
    "hermès": {"sac": 400, "maroquinerie": 300, "bijou": 200},
    "hermes": {"sac": 400, "maroquinerie": 300, "bijou": 200},
    "rolex": {"montre": 1500, "bijou": 500},
    "cartier": {"montre": 800, "bijou": 300},
    "dior": {"sac": 100, "maroquinerie": 80, "bijou": 50},
    "gucci": {"sac": 80, "maroquinerie": 60, "chaussures": 60},
    "balenciaga": {"sac": 80, "chaussures": 60},
    "prada": {"sac": 80, "maroquinerie": 60},
    "fendi": {"sac": 70, "maroquinerie": 50},
    "stone island": {"veste": 50, "pull": 30, "sweat": 30},
    "moncler": {"veste": 80, "doudoune": 100},
    "supreme": {"t-shirt": 30, "sweat": 50, "hoodie": 60},
}

# ─── 3. PHRASES D'ARNAQUE PAR CATÉGORIE ────────────────────────

SCAM_PATTERNS = {
    "hors_plateforme": [
        r"(06|07)\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d",
        r"(?:\+33|0033)\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d",
        r"whatsapp", r"snapchat", r"télégram", r"telegram",
        r"hors.?vinted", r"hors.?plateforme", r"hors.?site",
        r"en.?dehors", r"pas par vinted", r"autre moyen",
        r"paiement.?ext[ée]rieur", r"paypal hors",
        r"virement", r"paiement par", r"cb direct",
    ],
    "urgence_liquidite": [
        r"besoin.?d'argent", r"besoin.?urgent", r"liquidation",
        r"d[ée]m[ée]nagement.?urgent", r"d[ée]part.?[ée]tranger",
        r"tout.?doit.?dispara[îi]tre", r"solde.?avant.?d[ée]part",
        r"urgence.?absolue", r"motif.?visa", r"vite.?vendu",
    ],
    "pas_de_retour": [
        r"ni.?retour", r"sans.?retour", r"pas.?de.?retour",
        r"non.?remboursable", r"pas.?de.?remboursement",
        r"vendu.?tel.?quel", r"en.?l'[eé]tat",
    ],
    "photos_volées": [
        r"photo.?internet", r"photo.?non.?contractuelle",
        r"photo.?d'usine", r"photo.?professionnelle",
        r"pas.?le.?temps.?de.?prendre",
        r"photo.?issue", r"image.?internet",
    ],
    "histoire_incohérente": [
        r"vends.?pour.?un.?ami", r"pour.?le.?compte.?de",
        r"cadeau.?dont.?je.?n'ai.?pas.?besoin",
        r"re[çc]u.?en.?cadeau", r"trouv[ée].?dans.?un.?vide.?grenier",
        r"h[ée]ritage", r"succession",
    ],
}

# ─── 4. INDICATEURS DE COMPTE SUSPECT ─────────────────────────

SUSPICIOUS_ACCOUNT = {
    "nouveau_sans_avis": 15,
    "moins_7_jours": 20,
    "moins_30_jours": 8,
    "pas_photo_profil": 5,
    "pas_telephone_verifie": 5,
    "note_basse": 15,
    "peu_avis": 8,
}


class ScamDetector:
    """Détecteur d'arnaques v2 — auto-apprentissage."""

    def __init__(self):
        self.data_dir = DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.model_path = self.data_dir / "scam_model.json"
        self.model = self._load_model()
        self.alertes = []

    def _load_model(self) -> dict:
        default = {
            "analyses": 0, "confirmed_fakes": 0, "confirmed_real": 0,
            "brand_risk_adjustments": {},
            "price_floor_adjustments": {},
            "last_updated": datetime.now().isoformat(),
        }
        if self.model_path.exists():
            try:
                data = json.loads(self.model_path.read_text())
                for k, v in default.items(): data.setdefault(k, v)
                return data
            except: pass
        return default

    def _save_model(self):
        self.model["last_updated"] = datetime.now().isoformat()
        self.model_path.write_text(json.dumps(self.model, indent=2))

    def analyze(self, title: str = "", price: float = 0,
                description: str = "", category: str = "",
                brand: str = "", seller_rating: Optional[float] = None,
                seller_reviews: int = 0, seller_joined_days: int = 999,
                has_real_photos: Optional[bool] = None,
                is_stock_photo: Optional[bool] = None,
                seller_has_profile_pic: Optional[bool] = None,
                seller_has_verified_phone: Optional[bool] = None,
                has_multiple_identical_listings: bool = False) -> dict:
        """
        Analyse complète avec détection des fausses marques.

        Returns:
            Dict avec score (0-100), niveau, alertes, factors détaillés
        """
        self.alertes = []
        score = 0
        t = (title or "").lower()
        d = (description or "").lower()
        b = brand.lower().strip() if brand else ""
        c = category.lower().strip() if category else ""

        # ═══════════════════════════════════════════════════════
        # COUCHE 1 : DÉTECTION DES FAUSSES MARQUES (POIDS FORT)
        # ═══════════════════════════════════════════════════════

        # 1A. Mots-clés de contrefaçon dans le titre
        for kw in FAKE_BRAND_TITLE_KEYWORDS:
            if kw in t:
                severity = "CRITIQUE" if kw in ("réplique","replique","copie","fake","1:1","1/1","AAA") else "ÉLEVÉ"
                score += 30
                self._alert(f"Contrefaçon suspectée: '{kw}' dans le titre", severity,
                    f"Le terme '{kw}' indique une imitation, pas un article authentique")

        # 1B. Marques qui n'existent pas
        for fake_brand in KNOWN_FAKE_BRANDS:
            if fake_brand in t:
                score += 35
                self._alert("Marque fictive détectée", "CRITIQUE",
                    f"'{fake_brand}' n'est pas une marque réelle, c'est une imitation")

        # 1C. Marque de luxe + "style" dans le titre = imitation
        for lb in LUXURY_BRANDS:
            if lb in t and ("style" in t or "type" in t or "version" in t or "inspir" in t):
                score += 30
                self._alert(f"Imitation '{lb}' détectée", "CRITIQUE",
                    f"'{lb} style/type' = imitation, pas authentique")

        # 1D. Marque luxe à prix ridiculement bas
        if b in COUNTERFEIT_RISK_BRANDS and price > 0:
            risk = COUNTERFEIT_RISK_BRANDS[b]
            if b in LUXURY_PRICE_FLOOR and c:
                for cat_key, floor in LUXURY_PRICE_FLOOR[b].items():
                    if cat_key in c or not c:
                        if price < floor * 0.3:
                            score += 40
                            self._alert("Prix absurde pour cette marque", "CRITIQUE",
                                f"{b.title()} {cat_key} à {price:.0f}€ — authentique coûte {floor}€ minimum")
                        elif price < floor * 0.6:
                            score += 20
                            self._alert("Prix très bas pour cette marque", "ÉLEVÉ",
                                f"Prix {price:.0f}€ vs min réaliste {floor}€ — fort risque contrefaçon")
                        break
            # Marque luxe à < 50€ = alerte générale
            if b in ("chanel","louis vuitton","hermès","rolex","cartier") and price < 50:
                score += max(score, 25)
                if not any("Prix absurde" in a['titre'] for a in self.alertes):
                    self._alert("Prix ridicule pour marque de luxe", "CRITIQUE",
                        f"{b.title()} {price:.0f}€ = 100% contrefaçon à ce prix")

        # 1E. Marque luxe + vendeur inconnu = alerte composée
        if b in COUNTERFEIT_RISK_BRANDS and seller_reviews == 0 and price < 100:
            score += 15
            self._alert("Marque luxe + nouveau vendeur + prix bas", "ÉLEVÉ",
                "Combinaison classique des arnaques aux contrefaçons")

        # ═══════════════════════════════════════════════════════
        # COUCHE 2 : ANALYSE DE LA DESCRIPTION
        # ═══════════════════════════════════════════════════════

        # 2A. Patterns d'arnaque
        for category_name, patterns in SCAM_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, d)
                if matches:
                    if category_name == "hors_plateforme":
                        score += 20
                        self._alert("Contact hors Vinted demandé", "CRITIQUE",
                            f"Le vendeur essaie de contourner Vinted — arnaque quasi-certaine")
                    elif category_name == "pas_de_retour":
                        score += 15
                        self._alert("Politique 'ni retour ni remboursement'", "ÉLEVÉ",
                            "Signe d'une vente sans protection acheteur")
                    elif category_name == "photos_volées":
                        score += 12
                        self._alert("Photos non réelles", "MOYEN",
                            "Le vendeur utilise des photos issues d'internet")
                    elif category_name == "histoire_incohérente":
                        score += 8
                        self._alert("Histoire可疑e", "FAIBLE",
                            "Récit type des annonces frauduleuses")
                    elif category_name == "urgence_liquidite":
                        score += 8
                        self._alert("Urgence / liquidation", "FAIBLE",
                            "Pression à l'achat — technique d'arnaque classique")

        # 2B. Aucune description
        if len(description) < 10:
            score += 8
            self._alert("Aucune description", "MOYEN",
                "Les vendeurs sérieux décrivent leurs articles")

        # 2C. Description copiée (mots répétés)
        words = d.split()
        if len(words) > 5:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.4:
                score += 5
                self._alert("Description générique", "FAIBLE",
                    "Description qui semble copiée-collée")

        # ═══════════════════════════════════════════════════════
        # COUCHE 3 : ANALYSE DU TITRE
        # ═══════════════════════════════════════════════════════

        # 3A. Titre anormalement court
        if len(title) < 10:
            score += 5
            self._alert("Titre très court", "FAIBLE",
                "Les annonces sérieuses ont un titre descriptif")

        # 3B. Titre tout en majuscules (agressivité)
        if title and sum(1 for c in title if c.isupper()) > len(title) * 0.7:
            score += 5
            self._alert("Titre en majuscules", "FAIBLE",
                "Technique d'accroche des arnaqueurs")

        # ═══════════════════════════════════════════════════════
        # COUCHE 4 : ANALYSE DU PRIX
        # ═══════════════════════════════════════════════════════

        # 4A. Prix anormal pour la catégorie
        # Prix moyen estimé par catégorie
        _cat_prices = {
            "sneakers": (20, 200), "baskets": (20, 200),
            "sac": (30, 2000), "sacs": (30, 2000), "maroquinerie": (20, 1500),
            "montre": (20, 5000), "bijou": (10, 1000),
            "veste": (15, 300), "manteau": (20, 400), "doudoune": (25, 350),
            "jeans": (10, 100), "pantalon": (8, 80),
            "t-shirt": (3, 50), "chemise": (8, 80),
            "pull": (8, 100), "sweat": (10, 120), "hoodie": (10, 130),
            "robe": (10, 150), "jupe": (8, 80),
            "costume": (20, 300), "blazer": (15, 200),
            "maillot": (10, 100),
            "electronique": (20, 500), "jeu": (5, 50), "livre": (2, 30),
        }
        if c in _cat_prices:
            low, high = _cat_prices[c]
            if price < low * 0.4:
                self._alert("Prix anormalement bas pour cette catégorie", "MOYEN",
                    f"{price:.0f}€ vs moyenne {low}€-{high}€")
            if price > high * 2:
                self._alert("Prix anormalement élevé", "FAIBLE",
                    "Vérifier que l'article vaut ce prix")

        # ═══════════════════════════════════════════════════════
        # COUCHE 5 : ANALYSE DU VENDEUR
        # ═══════════════════════════════════════════════════════

        if seller_reviews == 0:
            score += 10
            self._alert("Nouveau vendeur (0 avis)", "MOYEN",
                "Aucun historique — compte potentiellement jetable")

        if seller_joined_days < 7:
            score += 12
            self._alert("Compte très récent", "ÉLEVÉ",
                f"Créé il y a {seller_joined_days} jour(s) — comptes fraudeurs fréquents")
        elif seller_joined_days < 30:
            score += 5
            self._alert("Compte récent", "FAIBLE",
                f"Créé il y a {seller_joined_days} jour(s)")

        if seller_rating is not None and seller_reviews > 0:
            if seller_rating < 3.0:
                score += 15
                self._alert("Très mauvaise note", "ÉLEVÉ",
                    f"Note {seller_rating}/5 — d'autres acheteurs ont eu des problèmes")
            elif seller_rating < 4.0:
                score += 5
                self._alert("Note moyenne", "FAIBLE",
                    f"Note {seller_rating}/5")

        if seller_has_profile_pic is False:
            score += 3
        if seller_has_verified_phone is False:
            score += 3

        if has_multiple_identical_listings:
            score += 15
            self._alert("Annonces identiques multiples", "ÉLEVÉ",
                "Même article listé plusieurs fois = arnaque fréquente")

        # ═══════════════════════════════════════════════════════
        # COUCHE 6 : ANALYSE DES PHOTOS
        # ═══════════════════════════════════════════════════════

        if is_stock_photo:
            score += 18
            self._alert("Photos issues d'internet", "ÉLEVÉ",
                "Photos volées = l'article réel sera différent")

        if has_real_photos is False:
            score += 10
            self._alert("Pas de photos réelles", "MOYEN",
                "Aucune photo = cacher l'état réel")

        # ═══════════════════════════════════════════════════════
        # AJUSTEMENTS DYNAMIQUES (modèle apprenant)
        # ═══════════════════════════════════════════════════════

        # Ajustement selon l'historique de cette marque
        if b in self.model["brand_risk_adjustments"]:
            adj = self.model["brand_risk_adjustments"][b]
            if adj["confirmed_fakes"] > adj["confirmed_real"] * 2:
                score += 10  # Cette marque est TRÈS contrefaite dans notre historique

        # ═══════════════════════════════════════════════════════
        # SCORE FINAL
        # ═══════════════════════════════════════════════════════

        score = min(score, MAX_SCAM_SCORE)

        if score >= 60:
            niveau, reco = "CRITIQUE", "NE PAS ACHETER — arnaque très probable"
        elif score >= 40:
            niveau, reco = "ÉLEVÉ", "Déconseillé — risques majeurs"
        elif score >= 20:
            niveau, reco = "MOYEN", "Vigilance — vérifier avant d'acheter"
        elif score >= 10:
            niveau, reco = "FAIBLE", "Quelques points de vigilance"
        else:
            niveau, reco = "SAIN", "Annonce saine — aucun signal d'alerte"

        # Enregistrer l'analyse
        self.model["analyses"] += 1
        self._save_model()

        return {
            "score_risque": score,
            "niveau": niveau,
            "recommandation": reco,
            "alertes": self.alertes,
            "analyse_marque": self._brand_analysis(brand, price, category),
            "facteurs": {
                "prix": f"{price:.0f}€",
                "vendeur": f"{seller_reviews} avis, {seller_joined_days}j",
                "description": f"{len(description)} car.",
            }
        }

    def confirm_fake(self, brand: str):
        """Enregistre une confirmation de contrefaçon pour améliorer le modèle."""
        if brand:
            b = brand.lower().strip()
            if b not in self.model["brand_risk_adjustments"]:
                self.model["brand_risk_adjustments"][b] = {"confirmed_fakes": 0, "confirmed_real": 0}
            self.model["brand_risk_adjustments"][b]["confirmed_fakes"] += 1
            self.model["confirmed_fakes"] += 1
            self._save_model()

    def confirm_real(self, brand: str):
        """Enregistre une confirmation d'authenticité."""
        if brand:
            b = brand.lower().strip()
            if b not in self.model["brand_risk_adjustments"]:
                self.model["brand_risk_adjustments"][b] = {"confirmed_fakes": 0, "confirmed_real": 0}
            self.model["brand_risk_adjustments"][b]["confirmed_real"] += 1
            self.model["confirmed_real"] += 1
            self._save_model()

    def _brand_analysis(self, brand: str, price: float, category: str) -> dict:
        """Analyse de la marque."""
        b = brand.lower().strip() if brand else ""
        c = category.lower().strip() if category else ""
        result = {"marque": brand or "non détectée", "risque_contrefaçon": "inconnu"}

        if b in COUNTERFEIT_RISK_BRANDS:
            risk_pct = COUNTERFEIT_RISK_BRANDS[b] * 100
            if risk_pct > 80:
                result["risque_contrefaçon"] = "TRÈS ÉLEVÉ"
            elif risk_pct > 60:
                result["risque_contrefaçon"] = "ÉLEVÉ"
            elif risk_pct > 40:
                result["risque_contrefaçon"] = "MOYEN"
            else:
                result["risque_contrefaçon"] = "FAIBLE"
            result["pct_contrefacon"] = risk_pct

            # Prix vs seuil
            if b in LUXURY_PRICE_FLOOR and c:
                for cat_key, floor in LUXURY_PRICE_FLOOR[b].items():
                    if cat_key in c or not c:
                        result["prix_minimum_realiste"] = floor
                        if price < floor:
                            result["alerte_prix"] = f"Prix ({price:.0f}€) sous le seuil réaliste ({floor}€)"
                        break

        # Stats du modèle
        if b in self.model["brand_risk_adjustments"]:
            adj = self.model["brand_risk_adjustments"][b]
            result["confirme_fakes"] = adj["confirmed_fakes"]
            result["confirme_reels"] = adj["confirmed_real"]

        return result

    def _alert(self, titre: str, niveau: str, detail: str):
        icon = {"CRITIQUE": "🔴", "ÉLEVÉ": "🟠", "MOYEN": "🟡", "FAIBLE": "🟢"}
        self.alertes.append({
            "titre": titre, "niveau": niveau,
            "detail": detail, "icone": icon.get(niveau, "⚪"),
        })

    def rapport(self, r: dict) -> str:
        """Rapport formaté complet."""
        lines = []
        n = r['niveau']
        s = r['score_risque']

        if n == "CRITIQUE": h = "🔴 FAUSSE MARQUE / ARNAQUE"
        elif n == "ÉLEVÉ": h = "🟠 RISQUE ÉLEVÉ"
        elif n == "MOYEN": h = "🟡 VIGILANCE REQUISE"
        elif n == "FAIBLE": h = "🟢 PRESQUE SAIN"
        else: h = "✅ ANNONCE SAINE"

        lines.append(f"── {h} ──")
        lines.append(f"  Score risque: {s}/{MAX_SCAM_SCORE}")
        lines.append(f"  {r['recommandation']}")

        # Analyse marque
        am = r.get('analyse_marque', {})
        if am.get('risque_contrefaçon'):
            rc = am['risque_contrefaçon']
            icon = {"TRÈS ÉLEVÉ": "🔴", "ÉLEVÉ": "🟠", "MOYEN": "🟡", "FAIBLE": "🟢"}
            lines.append(f"  Marque '{am['marque']}': risque contrefaçon {icon.get(rc,'')} {rc}")
            if 'pct_contrefacon' in am:
                lines.append(f"    {am['pct_contrefacon']:.0f}% des annonces de cette marque sont des fausses")
            if 'alerte_prix' in am:
                lines.append(f"    ⚠ {am['alerte_prix']}")

        if r['alertes']:
            lines.append(f"  Alertes ({len(r['alertes'])}):")
            for a in r['alertes']:
                lines.append(f"    {a['icone']} {a['titre']}")
                lines.append(f"       {a['detail']}")
        else:
            lines.append(f"  ✅ Aucune alerte")

        return "\n".join(lines)


# ─── Test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    sd = ScamDetector()

    # Test 1: Fausse marque évidente
    r1 = sd.analyze(
        title="SAC CHANEL STYLE 1:1 qualité réplique",
        price=45,
        description="Bonjour je vends ce sac chanel contactez moi par sms au 0612345678 paiement hors vinted envoi depuis l'étranger",
        category="sac", brand="chanel",
        seller_reviews=0, seller_joined_days=1,
        is_stock_photo=True,
    )
    print(sd.rapport(r1))
    print()

    # Test 2: Nike Air Force 1 authentique
    r2 = sd.analyze(
        title="Nike Air Force 1 blanches taille 42",
        price=45,
        description="Vends Nike Air Force 1 portées 2 fois, excellent état. Boîte d'origine. Envoi soigné avec suivi.",
        category="sneakers", brand="nike",
        seller_reviews=35, seller_joined_days=365,
        has_real_photos=True, is_stock_photo=False,
        seller_has_profile_pic=True, seller_has_verified_phone=True,
    )
    print(sd.rapport(r2))
    print()

    # Test 3: Marque inexistante
    r3 = sd.analyze(
        title="Superme hoodie style qualité premium taille M",
        price=25,
        description="Superbe hoodie qualité premium livré depuis la Chine",
        category="hoodie", brand="superme",
        seller_reviews=0, seller_joined_days=1,
    )
    print(sd.rapport(r3))

    # Test 4: Savoir du modèle (confirmer des fakes)
    sd.confirm_fake("chanel")
    sd.confirm_fake("chanel")
    sd.confirm_fake("chanel")
    sd.confirm_real("nike")
    print(f"\n  Modèle: {sd.model['analyses']} analyses, {sd.model['confirmed_fakes']} faux confirmés")
