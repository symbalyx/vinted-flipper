#!/usr/bin/env python3
"""
Listing Generator — Crée des annonces Vinted professionnelles.
Titres optimisés SEO, descriptions détaillées, prix recommandés.
"""
from datetime import datetime
from typing import Optional

# ─── Modèles de descriptions par catégorie ────────────────────

TEMPLATES = {
    "sneakers": """{etat_desc}

✅ POINTS FORTS :
• Modèle emblématique et intemporel
• Confortable au quotidien
• {specificite}

📌 INFORMATIONS :
• Marque : {marque}
• Taille : {taille}
• Couleur : {couleur}
• Matière : {matiere}
• État : {etat} (voir photos)

📏 MESURES / TAILLE :
• Taille indiquée sur la chaussure : {taille}
• Pointure conseillée : {taille_conseillee}
• Boîte d'origine : {boite}
• Livré avec : {accessoires}

⚠ PETITS DÉFAUTS :
{defauts}

📦 ENVOI SOIGNÉ :
• Expédié sous 24h ouvrées
• Bien protégé dans un carton adapté
• Numéro de suivi fourni automatiquement

💬 N'hésitez pas à me contacter pour plus de photos ou d'informations !
Je réponds rapidement.

#vinted #sneakers #{marque_slug} #{couleur_slug} #{taille} #{categorie_slug}""",

    "sac": """{etat_desc}

✨ UNE PIÈCE {hype} POUR LES AMATEURS DE BELLES MAROQUINERIES

✅ POINTS FORTS :
• {specificite}
• Modèle très recherché
• Parfait pour le quotidien ou les occasions spéciales

📌 INFORMATIONS :
• Marque : {marque}
• Modèle : {modele}
• Couleur : {couleur}
• Matière : {matiere}
• État : {etat} (voir photos)
• Dimensions : {dimensions}

🔍 DÉTAILS :
• Intérieur : {interieur}
• Fermeture : {fermeture}
• Bandoulière / Anses : {anses}
• Accessoires inclus : {accessoires}

⚠ PETITS DÉFAUTS :
{defauts}

📦 ENVOI SOIGNÉ :
• Expédié sous 24h ouvrées
• Protégé dans un carton avec papier de soie
• Numéro de suivi fourni

💬 Contactez-moi pour toute question ou pour des photos supplémentaires !

#{marque_slug} #{couleur_slug} #{categorie_slug} #sac #{modele_slug} #maroquinerie""",

    "default": """{etat_desc}

✅ POINTS FORTS :
• {specificite}
• Idéal pour un usage quotidien
• Excellent rapport qualité-prix

📌 INFORMATIONS :
• Marque : {marque}
• Taille : {taille}
• Couleur : {couleur}
• Matière : {matiere}
• État : {etat}

📏 MESURES :
• Voir photos pour les mesures détaillées

⚠ PETITS DÉFAUTS :
{defauts}

📦 ENVOI SOIGNÉ :
• Expédié sous 24h ouvrées
• Bien emballé et protégé
• Suivi fourni

💬 Contactez-moi pour plus d'informations !

#{marque_slug} #{couleur_slug} #{categorie_slug}""",
}

# Descriptions d'état
ETAT_DESC = {
    "neuf avec étiquette": "🆕 VENDU AVEC ÉTIQUETTE — jamais porté, emballage d'origine intact",
    "neuf": "🆕 JAMAIS PORTÉ — article neuf, sans étiquette",
    "très bon état": "✨ EXCELLENT ÉTAT — très peu porté, comme neuf",
    "bon état": "👍 BON ÉTAT — porté quelques fois, pas de défaut majeur",
    "satisfaisant": "🔍 ÉTAT CORRECT — quelques signes d'usage visibles (voir photos)",
}

# Suggestions de prix de mise en vente
PRICING_ADVICE = {
    "luxe": 0.95,       # 95% de l'estimation (le luxe se vend bien moins cher sur Vinted)
    "premium": 1.0,     # 100%
    "mid": 1.05,        # 105% (on peut tenter plus haut)
    "fast_fashion": 0.85,  # 85% (fast fashion se vend moins cher)
}


class ListingGenerator:
    """Génère des annonces Vinted professionnelles optimisées."""

    def __init__(self):
        self.categories_hype = {
            "sneakers": True, "sac": True, "doudoune": True,
            "montre": True, "veste": True, "manteau": True,
        }

    def generate(self, marque: str, categorie: str, etat: str,
                 taille: str = "", couleur: str = "noir",
                 prix_achat: float = 0, prix_estime: float = 0,
                 matiere: str = "", modele: str = "",
                 specificite: str = "", defauts: str = "Aucun défaut notable.",
                 dimensions: str = "", boite: str = "non",
                 accessoires: str = "aucun",
                 interieur: str = "bon état",
                 fermeture: str = "", anses: str = "",
                 **kwargs) -> dict:
        """Génère une annonce complète.

        Args:
            marque: Marque de l'article
            categorie: Catégorie (sneakers, sac, etc.)
            etat: État (neuf avec étiquette, très bon état, etc.)
            taille: Taille (42, M, L, etc.)
            couleur: Couleur
            prix_achat: Prix d'achat (pour conseil)
            prix_estime: Prix de revente estimé
            matiere: Matière (cuir, coton, etc.)
            modele: Modèle (Air Force 1, Speedy, etc.)
            specificite: Point fort principal
            defauts: Défauts à mentionner
            dimensions: Dimensions du sac/objet
            boite: Boîte d'origine
            accessoires: Accessoires inclus

        Returns:
            Dict avec titre, description, tags, prix conseillé
        """
        etat = etat.lower().strip() or "bon état"
        cat = categorie.lower().strip()
        mq = marque.lower().strip()

        # Normalisation
        etat_key = self._normalize_etat(etat)

        # ─── Titre optimisé SEO ────────────────────────────────
        titre = self._generate_title(marque, modele, categorie, couleur, etat_key, taille)

        # ─── Prix conseillé ────────────────────────────────────
        prix_conseils = self._pricing_advice(prix_achat, prix_estime, marque, categorie)

        # ─── Tags / Hashtags ───────────────────────────────────
        tags = self._generate_tags(marque, modele, categorie, couleur, taille)

        # ─── Description ───────────────────────────────────────
        etat_desc = ETAT_DESC.get(etat_key, f"État: {etat}")
        hype = "RECHERCHÉE" if cat in self.categories_hype else "DE QUALITÉ"
        taille_conseillee = taille
        boite_txt = "Oui ✅" if boite.lower() in ("oui", "o", "yes") else "Non"
        accessoires_txt = accessoires or "aucun"
        defauts_txt = defauts or "Aucun défaut notable."

        # Slug pour hashtags
        def slug(s): return s.lower().replace(" ", "").replace("'", "").replace("-", "")

        data = {
            "etat_desc": etat_desc, "hype": hype,
            "marque": marque, "marque_slug": slug(marque),
            "modele": modele, "modele_slug": slug(modele) if modele else "",
            "categorie_slug": slug(categorie),
            "etat": etat_key,
            "taille": taille, "taille_conseillee": taille_conseillee,
            "couleur": couleur, "couleur_slug": slug(couleur),
            "matiere": matiere or "Voir description",
            "specificite": specificite or "Article de qualité",
            "defauts": defauts_txt,
            "dimensions": dimensions or "Voir photos",
            "boite": boite_txt,
            "accessoires": accessoires_txt,
            "interieur": interieur,
            "fermeture": fermeture or "Voir photos",
            "anses": anses or "Voir photos",
        }

        template = TEMPLATES.get(cat, TEMPLATES["default"])
        description = template.format(**data)

        return {
            "titre": titre,
            "description": description,
            "tags": tags,
            "prix_conseille": prix_conseils,
            "categorie": categorie,
            "etat": etat_key,
        }

    def _normalize_etat(self, etat: str) -> str:
        mapping = {
            "neuf avec étiquette": "neuf avec étiquette",
            "neuf avec etiquette": "neuf avec étiquette",
            "neuf": "neuf",
            "très bon état": "très bon état",
            "tres bon etat": "très bon état",
            "t bon état": "très bon état",
            "bon état": "bon état",
            "bon etat": "bon état",
            "satisfaisant": "satisfaisant",
            "état correct": "satisfaisant",
        }
        return mapping.get(etat.lower().strip(), "bon état")

    def _generate_title(self, marque: str, modele: str, categorie: str,
                        couleur: str, etat: str, taille: str) -> str:
        """Génère un titre optimisé pour le référencement Vinted."""

        # Structure: [Marque] [Modèle] - [Couleur] - [Taille] - [État]
        parts = [marque]
        if modele:
            parts.append(modele)
        parts.append(couleur)
        if taille:
            parts.append(taille)
        # Ajouter des mots-clés selon catégorie
        cat_keywords = {
            "sneakers": ["Baskets", "Chaussures"],
            "sac": ["Sac", "Maroquinerie"],
            "veste": ["Veste"],
            "manteau": ["Manteau"],
            "doudoune": ["Doudoune"],
            "jeans": ["Jean"],
            "montre": ["Montre"],
            "t-shirt": ["T-shirt", "Tee-shirt"],
        }
        for kw in cat_keywords.get(categorie.lower(), []):
            if kw.lower() not in " ".join(parts).lower():
                parts.append(kw)

        titre = " - ".join(parts)
        # Limiter à 80 caractères (optimisé Vinted)
        if len(titre) > 80:
            titre = titre[:77] + "..."

        # Ajouter état si distinctif
        if etat == "neuf avec étiquette":
            titre = f"🆕 {titre}"
        elif etat == "neuf":
            titre = f"NEUF {titre}"

        return titre[:100]

    def _pricing_advice(self, prix_achat: float, prix_estime: float,
                        marque: str, categorie: str) -> dict:
        """Conseil de prix de mise en vente."""
        mq = marque.lower().strip()
        cat = categorie.lower().strip()

        # Déterminer le segment
        luxe_brands = ["chanel", "hermès", "louis vuitton", "dior", "cartier", "rolex"]
        premium_brands = ["arc'teryx", "stone island", "moncler", "supreme", "patagonia"]
        fast_fashion = ["kiabi", "primark", "bershka", "pull&bear", "stradivarius"]

        if any(b in mq for b in luxe_brands):
            segment = "luxe"
        elif any(b in mq for b in premium_brands):
            segment = "premium"
        elif any(b in mq for b in fast_fashion):
            segment = "fast_fashion"
        elif prix_estime > 200:
            segment = "premium"
        else:
            segment = "mid"

        coef = PRICING_ADVICE.get(segment, 1.0)
        conseil = round(prix_estime * coef, 2)
        max_price = round(prix_estime * (coef + 0.15), 2)
        min_price = round(prix_estime * (coef - 0.10), 2)

        marge_min = min_price - prix_achat
        marge_conseil = conseil - prix_achat

        return {
            "min": min_price,
            "conseille": conseil,
            "max": max_price,
            "segment": segment,
            "marge_min": round(marge_min, 2),
            "marge_conseil": round(marge_conseil, 2),
            "prix_achat": prix_achat,
        }

    def _generate_tags(self, marque: str, modele: str, categorie: str,
                       couleur: str, taille: str) -> list:
        """Génère des hashtags Vinted."""
        def slug(s):
            return s.lower().replace(" ", "").replace("'", "").replace("-", "")

        tags = [slug(marque)]
        if modele:
            tags.append(slug(modele))
        tags.append(slug(categorie))
        if couleur:
            tags.append(slug(couleur))
        if taille:
            tags.append(taille.lower())
        tags.append("vinted")
        tags.append("bonneaffaire")

        # Tags spécifiques par catégorie
        cat_tags = {
            "sneakers": ["sneakers", "baskets", "chaussures"],
            "sac": ["sac", "maroquinerie", "luxe"],
            "montre": ["montre", "bijou"],
            "veste": ["veste", "mode"],
            "doudoune": ["doudoune", "hiver"],
        }
        tags.extend(cat_tags.get(categorie.lower(), []))
        return list(set(tags))

    def rapport(self, r: dict) -> str:
        """Rapport formaté de l'annonce générée."""
        lines = []
        lines.append(f"── Annonce générée ─────────────────────────────")
        lines.append(f"  {r['titre']}")
        lines.append("")
        lines.append(f"  PRIX CONSEILLÉ:")
        pr = r['prix_conseille']
        lines.append(f"    Min: {pr['min']:.2f}€ | Conseillé: {pr['conseille']:.2f}€ | Max: {pr['max']:.2f}€")
        lines.append(f"    Segment: {pr['segment']}")
        lines.append(f"    Marge: {pr['marge_conseil']:+.2f}€ (achat {pr['prix_achat']:.2f}€)")
        lines.append("")
        lines.append(f"  DESCRIPTION:")
        for line in r['description'].split('\n'):
            lines.append(f"  {line}")
        lines.append("")
        lines.append(f"  TAGS: {'  '.join(f'#{t}' for t in r['tags'][:10])}")
        return "\n".join(lines)


if __name__ == "__main__":
    lg = ListingGenerator()

    # Test 1: Sneakers
    r1 = lg.generate(
        marque="Nike", modele="Air Force 1", categorie="sneakers",
        etat="très bon état", taille="42", couleur="blanc",
        prix_achat=25, prix_estime=45,
        specificite="Modèle iconique, très confortable",
        matiere="Cuir", boite="oui",
    )
    print(lg.rapport(r1))
    print()

    # Test 2: Sac
    r2 = lg.generate(
        marque="Chanel", modele="Classique", categorie="sac",
        etat="très bon état", couleur="noir",
        prix_achat=1800, prix_estime=3500,
        specificite="Modèle iconique intemporel, excellent état",
        matiere="Cuir d'agneau",
        dimensions="25x15x8 cm",
        fermeture="Clip lock",
        anses="Bandoulière chaîne",
        accessoires="Boîte, dustbag, carte d'authenticité",
        interieur="Impeccable",
    )
    print(lg.rapport(r2))
