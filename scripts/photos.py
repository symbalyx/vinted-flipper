#!/usr/bin/env python3
"""
Vinted Flipper — Photos Pro.
Guide photo par catégorie pour des annonces qui vendent mieux et plus cher.
"""
from datetime import datetime

PHOTO_GUIDES = {
    "sneakers": {
        "title": "Baskets / Sneakers",
        "photos_min": 6,
        "angles": [
            "Profil extérieur (côté gauche)",
            "Profil extérieur (côté droit)",
            "Avant (face)",
            "Arrière (talon)",
            "Semelle (dessous, montrer l'usure)",
            "Intérieur (talon, étiquette taille)",
        ],
        "tips": [
            "Fond blanc ou neutre — poser au sol sur une surface claire",
            "Lumière naturelle, pas de flash",
            "Mettre les lacets bien lacés (propre)",
            "Nettoyer les semelles avec une lingette avant photo",
            "Montrer l'étiquette taille dans la chaussure",
            "Si boîte d'origine → la montrer dans au moins une photo",
            "Angle 3/4 = meilleur rendu pour les sneakers",
        ],
        "lighting": "Lumière du jour indirecte (près d'une fenêtre). Éviter le soleil direct.",
        "background": "Papier blanc ou fond photo 60x80cm. Pas de carrelage ou parquet.",
        "dont": [
            "Ne pas photographier les pieds portant les chaussures",
            "Éviter les photos de nuit avec flash",
            "Ne pas cacher les défauts avec des filtres",
        ],
    },
    "sac": {
        "title": "Sacs / Maroquinerie",
        "photos_min": 8,
        "angles": [
            "Face avant (debout)",
            "Face arrière",
            "Intérieur (compartiments visibles)",
            "Fermeture / zip (détail)",
            "Anses / bandoulière",
            "Logo / plaque marque (gros plan)",
            "Numéro de série / carte d'authenticité",
            "Défauts éventuels (coins, coutures)",
        ],
        "tips": [
            "Sac posé sur une surface plane ou sur un support (jamais par terre)",
            "Rembourrer le sac avec du papier de soie pour lui donner sa forme",
            "Photographier à hauteur des yeux, pas de dessus",
            "Gros plan sur l'étiquette intérieure (marque + composition)",
            "Montrer les accessoires (dustbag, boîte, carte authent)",
            "Si cuir — montrer la texture en gros plan",
        ],
        "lighting": "Studio lumineux. Si pas possible, lumière naturelle + réflecteur blanc.",
        "background": "Fond blanc ou drap blanc. Mettre en valeur sans distraire.",
        "dont": [
            "Jamais de flash (créé des reflets sur le cuir)",
            "Ne pas pendre le sac par une anse (le déforme)",
            "Éviter les décors chargés (chambre, canapé)",
        ],
    },
    "veste": {
        "title": "Vestes / Manteaux / Blousons",
        "photos_min": 5,
        "angles": [
            "Face (boutonné/fermé)",
            "Face (ouvert)",
            "Dos",
            "Étiquette intérieure (taille, marque, composition)",
            "Détail matière (gros plan tissu)",
        ],
        "tips": [
            "Sur cintre (propre, costaud) ou à plat sur fond blanc",
            "Sur mannequin idéal (donne une idée du rendu)",
            "À plat : bien positionner les manches, col, boutons",
            "Montrer l'épaisseur (photo de profil)",
            "Si doublure → la montrer",
        ],
        "lighting": "Lumière naturelle, éviter les ombres portées du cintre.",
        "background": "Mur blanc ou fond photo. Pas de porte, pas de lit en arrière-plan.",
        "dont": [
            "Jamais sur un cintre tordu ou cabossé",
            "Pas de photo plié en boule sur le lit",
            "Éviter les miroirs sales",
        ],
    },
    "montre": {
        "title": "Montres",
        "photos_min": 6,
        "angles": [
            "Face (cadran, aiguilles)",
            "Profil (épaisseur du boîtier)",
            "Boucle / fermoir",
            "Bracelet (intérieur + extérieur)",
            "Numéro de série (si visible)",
            "Boîte / papiers (si inclus)",
        ],
        "tips": [
            "Montre posée à plat sur un support doux",
            "Propreté impérative : nettoyer le verre et le bracelet avant",
            "Macro pour le cadran (montrer les détails)",
            "Heure photographiée à 10h10 (classique en horlogerie)",
            "Montrer l'état du verre (rayures ?)",
        ],
        "lighting": "Lumière douce, pas de projecteur direct (reflets). Lampe de bureau avec diffuseur.",
        "background": "Tissu noir ou blanc uni. Support à montre si possible.",
        "dont": [
            "Jamais de flash (reflets sur le verre)",
            "Ne pas porter la montre au poignet pour la photo",
            "Éviter les arrière-plans avec des chiffres/horloges",
        ],
    },
    "default": {
        "title": "Tout type d'article",
        "photos_min": 5,
        "angles": [
            "Face avant",
            "Face arrière",
            "Étiquette (taille, marque, composition)",
            "Détail matière / motif",
            "Défauts éventuels",
        ],
        "tips": [
            "Fond blanc ou neutre — toujours",
            "Lumière naturelle — jamais de flash",
            "Repasser/vapeur avant photo (vêtements sans plis)",
            "5 photos minimum — les annonces avec 5+ photos vendent +40%",
            "Montrer les défauts honnêtement (confiance acheteur)",
            "Première photo = la meilleure (vignette dans les résultats)",
            "Formats verticaux recommandés (9:16) pour mobile",
        ],
        "lighting": "Lumière naturelle près d'une fenêtre. Jamais de flash.",
        "background": "Blanc uni. Drap blanc, fond photo, ou mur blanc.",
        "dont": [
            "Pas de selfie / mirror selfie",
            "Pas de filtre Instagram ou saturation",
            "Pas de texte superposé sur la photo",
            "Pas de mains ou visages dans le cadre",
        ],
    },
}


def get_photo_guide(category: str = "") -> dict:
    """Retourne le guide photo pour une catégorie."""
    cat = category.lower().strip()
    for key in PHOTO_GUIDES:
        if key in cat or cat in key:
            return PHOTO_GUIDES[key]
    return PHOTO_GUIDES["default"]


def photo_report(category: str = "", title: str = "") -> str:
    """Rapport photo formaté."""
    guide = get_photo_guide(category or title)
    lines = []
    lines.append(f"── GUIDE PHOTO: {guide['title']} ──")
    lines.append(f"  Photos recommandées: {guide['photos_min']} minimum")
    lines.append("")
    lines.append(f"  📸 ANGLES À PHOTOGRAPHIER:")
    for a in guide['angles']:
        lines.append(f"    • {a}")
    lines.append("")
    lines.append(f"  💡 CONSEILS:")
    for t in guide['tips']:
        lines.append(f"    • {t}")
    lines.append("")
    lines.append(f"  ☀️ ÉCLAIRAGE:")
    lines.append(f"    {guide['lighting']}")
    lines.append("")
    lines.append(f"  🎨 FOND:")
    lines.append(f"    {guide['background']}")
    lines.append("")
    lines.append(f"  ❌ À ÉVITER:")
    for d in guide['dont']:
        lines.append(f"    • {d}")
    return "\n".join(lines)


if __name__ == "__main__":
    # Test
    for cat in ["sneakers", "sac", "veste", "montre", "default"]:
        print(photo_report(category=cat))
        print()
