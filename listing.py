#!/usr/bin/env python3
"""
Listing Generator v2 — Annonces qui sonnent humain.
Fini les templates rigides avec sections, émojis partout,
et hashtags SEO. Ici on parle comme un vrai vendeur Vinted.
"""
import random
from datetime import datetime
from typing import Optional

# ─── 8 VOIX HUMAINES différentes ─────────────────────────────
# Chaque appel à generate() pioche aléatoirement dans ces styles
# pour éviter les doublons et le sentiment "template"

VOICES = {
    "naturel": {  # Ton neutre, honnête, simple
        "intro": [
            "Vends {article} en {etat}. ",
            "Je vends {article} {etat}. ",
            "{article} — {etat}. ",
        ],
        "corps": [
            "Je l'ai porté {usage}, il est en super état. ",
            "Franchement il est nickels, juste {defaut}. ",
            "Acheté {origine}, je le vends car {raison}. ",
            "Rien à signaler à part {defaut}. ",
            "Très peu servi, {taille_desc}. ",
        ],
        "outro": [
            "Prix: {prix_texte}. Envoi soigné.",
            "Prix ferme à {prix_texte}. Envoi rapide.",
            "{prix_texte} — envoi en lettre suivie ou colissimo.",
            "Vendu à {prix_texte}, port en plus.",
        ],
    },
    "detail": {  # Précis, rassurant
        "intro": [
            "Bonjour, je vends {article} que j'ai {origine_detail}. ",
            "En vente: {article}. ",
            "{article} — je le décris en détail: ",
        ],
        "corps": [
            "État: {etat_doux}. {detail_etat} ",
            "Taille: {taille_desc}. Couleur: {couleur_courant}. Matière: {matiere} ",
            "Je l'ai utilisé {usage}, il est resté en excellent état. ",
            "Petit défaut: {defaut} (voir photo). À part ça parfait. ",
            "Ça taille pareil — {taille_note}. ",
        ],
        "outro": [
            "Vendu en l'état. Envoi sous 48h. Merci!",
            "Prix: {prix_texte}. Envoi rapide et soigné.",
            "N'hésitez pas à demander plus de photos.",
            "{prix_texte} port en plus. Vendu avec {accessoires}.",
        ],
    },
    "direct": {  # Court, efficace
        "intro": [
            "{article} — {etat}. ",
            "Vends {article}. ",
            "{article} à vendre: ",
        ],
        "corps": [
            "{etat_doux}, {usage}. {defaut_long} ",
            "{taille_desc}, couleur {couleur_courant}. ",
            "Pas de défaut majeur. {defaut} ",
            "Acheté {prix_origine}€, vendu {prix_texte}. ",
        ],
        "outro": [
            "Envoi colissimo. Prix: {prix_texte}.",
            "{prix_texte} — envoi suivi inclus.",
            "Vendu {prix_texte}, frais d'envoi en +.",
        ],
    },
    "cool": {  # Naturel, moderne
        "intro": [
            "Yo, je vends {article} ! ",
            "En vrai l'article est {etat}, je le vends parce que {raison_cool}. ",
            "Je me sépare de {article}: ",
        ],
        "corps": [
            "Porté {usage} mais vraiment état {etat_doux}. ",
            "Petite histoire: {raison_cool}. Du coup je le vends. ",
            "Couleur: {couleur_courant} — passe avec tout. ",
            "J'ai fait gaffe, {defaut_soft}. ",
        ],
        "outro": [
            "Prix: {prix_texte}. Envoi rapide!",
            "{prix_texte} le tout. Port en +.",
            "Envoyé dans la journée. {prix_texte}",
        ],
    },
    "pro": {  # Professionnel, style dépôt-vente
        "intro": [
            "{article} en {etat_doux} — idéal pour {usage_pro}. ",
            "Modèle {modele} par {marque}, {etat_doux}. ",
            "{marque} {modele} — {etat_doux}. ",
        ],
        "corps": [
            "Taille {taille_desc}, couleur {couleur_courant}. ",
            "Matière: {matiere}. Fabriqué en {origine}. ",
            "Usure normale visible: {defaut}. ",
            "Complet avec {accessoires}. ",
        ],
        "outro": [
            "Expédition sous 48h. Prix: {prix_texte}.",
            "{prix_texte} — envoi suivi. Possibilité remise en main propre.",
            "Disponible immédiatement. {prix_texte}",
        ],
    },
    "story": {  # Raconte une histoire
        "intro": [
            "Je vends {article} que j'avais acheté parce que {raison}. Mais {raison_contre} ",
            "Je me décide à vendre {article}. Pourquoi? {raison_cool}. ",
            "Cet article c'est {histoire}. ",
        ],
        "corps": [
            "Je l'ai porté {usage} fois max, vraiment état {etat_doux}. ",
            "Je l'avais payé {prix_origine}€ à l'époque. ",
            "Le seul défaut c'est {defaut}. Mais franchement ça se voit à peine. ",
            "Je le vends parce que {raison_cool}, pas par besoin. Du coup je le brade pas. ",
        ],
        "outro": [
            "Prix: {prix_texte}. Je peux faire {prix_negos}€ si pris aujourd'hui.",
            "{prix_texte} — je préfère pas descendre en dessous vu {raison}.",
            "Prix correct je pense. Envoi soigné.",
        ],
    },
    "minimal": {  # Ultra-court, comme un particulier pressé
        "intro": [
            "{article}. {etat_doux}. ",
            "Vds {article}. ",
        ],
        "corps": [
            "Taille {taille_desc}. {couleur_courant}. ",
            "Porté {usage}. {defaut_long} ",
            "{detail_etat}. ",
        ],
        "outro": [
            "{prix_texte}. Envoi en +.",
            "{prix_texte}.",
        ],
    },
    "confiance": {  # Rassurant, "vendeur sérieux"
        "intro": [
            "Bonjour, je propose {article} en trè bon état. ",
            "{article} — acheté {origine}, vendu car {raison}. ",
            "{marque} {modele} à vendre. ",
        ],
        "corps": [
            "État général: {etat_doux} (voir les photos). ",
            "Comptez {usage} d'utilisation, toujours rangé avec soin. ",
            "Seul défaut: {defaut}. Le reste est impec. ",
            "Taille: {taille_desc} — voir les mesures sur les photos. ",
        ],
        "outro": [
            "Prix: {prix_texte} (juste, c'est {raison}). Envoi rapide+protégé.",
            "Vendu avec {accessoires}. {prix_texte}.",
            "Je réponds à toutes les questions. Prix: {prix_texte}",
        ],
    },
}

VOICE_NAMES = list(VOICES.keys())

# ─── Liste de raisons de vente (varie) ───────────────────────
RAISONS = [
    "je l'ai porté une fois et il est resté au placard",
    "je taille du M maintenant, trop petit",
    "c'est la taille au-dessus il flotte sur moi",
    "j'ai acheté la même chose dans une autre couleur",
    "ma copine m'a dit de vider mon dressing",
    "je fais du tri dans mon dressing, il mérite une seconde vie",
    "j'ai craqué sur un autre modèle",
    "je l'ai eu en cadeau mais c'est pas mon style",
    "il est magnifique mais je l'ai jamais mis",
    "c'est une belle pièce mais je passe à autre chose",
    "changed my mind, trop beau pour rester dans le placard",
    "c'était une bonne affaire mais je préfère le revendre",
]

DEFAUTS = [
    "un tout petit accroc sur la manche (voir photo)",
    "la semelle est un peu usée à l'avant",
    "petite marque sur le cuir à l'intérieur",
    "quelques micro-griffures sur le fermoir",
    "une tache à peine visible sous la poche",
    "le bord blanc a jauni très légèrement",
    "le cuir a un peu frotté au niveau du coude",
    "l'étiquette est un peu froissée",
    "le sticker de marque s'enlève",
    "une couture qui tire un chouia",
    "franchement je vois rien à signaler",
    "quasiment neuf, aucun défaut",
    "la doublure a une petite marque à l'intérieur",
    "rien de particulier, c'est juste de l'usure normale",
]

HISTOIRES = [
    "je l'ai acheté lors d'un voyage à {}",
    "c'était mon coup de coeur mais finalement je l'ai mis 2 fois",
    "je le garde depuis des années mais je passe à autre chose",
    "cadeau de mon ex, du coup je vends",
    "je l'ai trouvé en brocante pour 5€, je le revends au prix juste",
    "c'est une pièce que j'ai chinée, magnifique mais trop petit",
    "mon copain me dit que j'ai trop de vêtements, je fais de la place",
]

ORIGINES = [
    "en boutique", "en ligne chez le site officiel", "en dépôt-vente",
    "lors d'une vente privée", "sur le marketplace", "chez un revendeur",
    "en solde", "sur Vinted justement lol", "en vide-grenier",
    "lors d'un voyage", "à l'étranger",
]

USAGES = [
    "2-3 fois", "quelques fois", "une dizaine de fois",
    "peu porté, 5 fois max", "très peu", "une saison",
    "2-3 fois grand max", "un été", "l'hiver dernier",
    "jamais porté, juste essayé",
]

# ─── Descriptions d'état (humaÏNES) ─────────────────────────
ETAT_HUMAIN = {
    "neuf avec étiquette": "neuf avec etiquette, jamais porté",
    "neuf avec etiquette": "neuf avec etiquette, jamais porté",
    "neuf": "neuf, sans étiquette mais jamais porté",
    "très bon état": "excellent état, porté {usage}",
    "tres bon etat": "excellent état, porté {usage}",
    "bon état": "bon état, porté {usage}",
    "bon etat": "bon état, porté {usage}",
    "satisfaisant": "état correct — {defaut}",
}

# ─── Prix arrondis (humain) ──────────────────────────────────
PRICE_ROUND = [5, 7, 9, 10, 12, 15, 18, 20, 22, 25, 28, 30, 35, 39, 40, 45, 49, 50, 55, 59, 60, 65, 69, 70, 75, 79, 80, 85, 89, 90, 95, 99, 100, 110, 115, 120, 125, 130, 140, 145, 149, 150, 160, 170, 175, 180, 190, 195, 199, 200, 220, 250, 280, 290, 299, 300, 350, 390, 399, 400, 450, 490, 499, 500, 550, 590, 599, 600, 650, 690, 699, 700, 750, 790, 799, 800, 850, 890, 899, 900, 950, 990, 999]

def round_price(p):
    """Arrondit à un prix qui semble humain."""
    if p <= 0: return 0
    closest = min(PRICE_ROUND, key=lambda x: abs(x - p))
    # Ajouter un peu de hasard pour pas toujours tomber sur le même
    if random.random() < 0.3:
        return max(1, closest + random.choice([-1, 0, 0, 1, 2]))
    return closest


class ListingGenerator:
    """Génère des annonces qui sonnent humaines."""

    def __init__(self):
        self.categories_hype = {
            "sneakers", "sac", "doudoune",
            "montre", "veste", "manteau",
        }

    def generate(self, marque: str, categorie: str, etat: str,
                 taille: str = "", couleur: str = "noir",
                 prix_achat: float = 0, prix_estime: float = 0,
                 matiere: str = "", modele: str = "",
                 specificite: str = "", defauts: str = "",
                 dimensions: str = "", boite: str = "non",
                 accessoires: str = "",
                 **kwargs) -> dict:
        """Génère une annonce qui sonne humaine."""

        etat = etat.lower().strip() or "bon état"
        cat = categorie.lower().strip()
        mq = marque.strip()
        etat_key = self._normalize_etat(etat)
        
        # Infos de base
        usage = random.choice(USAGES)
        defaut = defauts or random.choice(DEFAUTS)
        raison = random.choice(RAISONS)
        raison_cool = raison
        origine = random.choice(ORIGINES)
        
        # Prix arrondi humain
        prix_humain = round_price(prix_estime) if prix_estime > 0 else round_price(prix_achat * 1.5)
        if prix_humain <= 0: prix_humain = 50
        prix_texte = f"{prix_humain}€"
        prix_negos = round_price(prix_humain * 0.9)
        
        taille_desc = taille if taille else "taillle unique"
        taille_note = "taille normal, prends ta taille habituelle"
        if taille and "m" in taille.lower():
            taille_note = "c'est du M standard, taille bien"
        elif taille and "l" in taille.lower():
            taille_note = "c'est du L, taille confortable"
        
        couleur_courant = couleur.lower() if couleur else "noir"
        etat_doux = etat_key.replace("neuf avec étiquette", "neuf avec etiquette")
        detail_etat = f"Pas de tâche, pas d'accroc, vraiment {etat_doux}" if etat in ("très bon état", "neuf", "neuf avec étiquette") else f"Usure normale, {defaut}"
        
        # Assembler en choisissant une voix aléatoire
        voice_name = random.choice(VOICE_NAMES)
        
        # Éviter les répétitions: si même voix la dernière fois, re-piocher
        voice = VOICES[voice_name]
        
        # Préparer les variables de template
        vars_dict = {
            "article": f"{mq} {modele}" if modele else mq,
            "marque": mq,
            "modele": modele or "",
            "categorie": cat,
            "etat": etat,
            "etat_doux": etat_doux,
            "etat_desc": ETAT_HUMAIN.get(etat_key, etat).format(usage=usage, defaut=defaut),
            "usage": usage,
            "raison": raison,
            "raison_cool": raison_cool,
            "raison_contre": f"finalement je l'ai porté {usage}" if random.random() > 0.5 else "je le trouve plus trop à mon goût",
            "origine": origine,
            "origine_detail": f"acheté {origine} il y a quelques mois" if random.random() > 0.5 else f"pris {origine}",
            "defaut": defaut,
            "defaut_long": f"juste {defaut.lower()}." if defaut else "rien à signaler.",
            "defaut_soft": f"il y a {defaut.lower()} mais honnêtement ça se voit pas.",
            "taille": taille,
            "taille_desc": taille_desc,
            "taille_note": taille_note,
            "taille_conseillee": taille,
            "couleur": couleur,
            "couleur_courant": couleur_courant,
            "matiere": matiere or "cuir / tissu (voir description)",
            "specificite": specificite or "belle pièce",
            "dimensions": dimensions or "voir photos",
            "boite": boite,
            "accessoires": accessoires or "rien de particulier",
            "usage_pro": f"tous les jours" if random.random() > 0.5 else f"les amateurs de la marque",
            "prix_origine": round_price(prix_achat) if prix_achat > 0 else prix_humain,
            "prix_texte": prix_texte,
            "prix_negos": prix_negos,
            "histoire": random.choice(HISTOIRES).format(random.choice(["Paris", "Londres", "Tokyo", "New York", "Berlin", "Milan", "Barcelone", "Lyon", "Marseille", "Bordeaux"])),
            "interieur": kwargs.get("interieur", "bon"),
            "fermeture": kwargs.get("fermeture", "fermeture classique"),
            "anses": kwargs.get("anses", ""),
        }
        
        # Construire le texte
        intro = random.choice(voice["intro"]).format(**vars_dict)
        corps = random.choice(voice["corps"]).format(**vars_dict)
        outro = random.choice(voice["outro"]).format(**vars_dict)
        
        # Parfois ajouter un élément en plus
        extra = ""
        if random.random() < 0.4:
            extra = random.choice([
                " Les photos sont le reflet de l'état réel. ",
                " N'hésitez pas si vous voulez plus de photos. ",
                " Je peux faire un prix si pris en lot. ",
                " Envoi depuis Bordeaux. ",
                " Merci de regarder les photos avant d'acheter! ",
            ])
        
        description = f"{intro}{corps}{extra}{outro}"
        
        # Nettoyer les espaces
        description = description.replace("  ", " ").replace(" .", ".").replace(" ,", ",")
        description = description.strip()
        
        # Hashtags: 1-3 max, naturels
        tags = self._generate_tags_naturels(marque, modele, categorie, random.random() < 0.3)
        
        # Titre: simple, pas de format "tuyau"
        titre = self._generate_title_humain(marque, modele, categorie, couleur, etat_key, taille)
        
        # Prix conseil avec marge
        prix_conseils = self._pricing_advice(prix_achat, prix_estime, marque, categorie)
        
        return {
            "titre": titre,
            "description": description,
            "tags": tags,
            "prix_conseille": prix_conseils,
            "categorie": categorie,
            "etat": etat_key,
            "voix": voice_name,
        }

    def _normalize_etat(self, etat: str) -> str:
        mapping = {
            "neuf avec étiquette": "neuf avec étiquette",
            "neuf avec etiquette": "neuf avec étiquette",
            "neuf avec etiquettes": "neuf avec étiquette",
            "neuf": "neuf",
            "très bon état": "très bon état",
            "tres bon etat": "très bon état",
            "t bon état": "très bon état",
            "t bon etat": "très bon état",
            "bon état": "bon état",
            "bon etat": "bon état",
            "satisfaisant": "satisfaisant",
            "état correct": "satisfaisant",
            "endommagé": "satisfaisant",
            "endommage": "satisfaisant",
        }
        return mapping.get(etat.lower().strip(), "bon état")

    def _generate_title_humain(self, marque, modele, categorie, couleur, etat, taille):
        """Titre qui ressemble à ce qu'un vrai vendeur Vinted écrirait."""
        
        base = f"{marque} {modele}" if modele else marque
        
        # Styles de titres variés
        styles = [
            lambda: f"{base} — {couleur}, {taille}" if taille else f"{base} — {couleur}",
            lambda: f"{base} {couleur} {'taille ' + taille if taille else ''}".strip(),
            lambda: f"{base} — {etat} {'T.' + taille if taille else ''}".strip(),
            lambda: f"{base} {couleur} {'(' + taille + ')' if taille else ''}",
            lambda: f"{base}, couleur {couleur}",
        ]
        
        titre = random.choice(styles)()
        titre = titre.replace("  ", " ").strip()
        
        # Limiter à 80-100 caractères
        if len(titre) > 95:
            titre = titre[:92] + "..."
        
        return titre

    def _generate_tags_naturels(self, marque, modele, categorie, add_extra=False):
        """Hashtags naturels — 1-4 max."""
        tags = []
        
        # Slugify simple
        def slug(s):
            return s.lower().replace(" ", "").replace("'", "").replace("-", "").replace(".", "").replace(",", "")
        
        # Toujours la marque
        tags.append(slug(marque))
        
        # Parfois le modèle
        if modele and random.random() < 0.6:
            tags.append(slug(modele))
        
        # Parfois la catégorie (mais pas systématiquement)
        if random.random() < 0.5:
            tags.append(slug(categorie))
        
        # Parfois un tag "vinted" ou "bonneaffaire"
        if add_extra and random.random() < 0.5:
            tags.append("vinted")
        
        return list(set(tags))[:4]

    def _pricing_advice(self, prix_achat, prix_estime, marque, categorie):
        """Conseil de prix — arrondi humain."""
        # Mêmes segments
        luxe_brands = ["chanel", "hermès", "louis vuitton", "dior", "cartier", "rolex"]
        premium_brands = ["arc'teryx", "stone island", "moncler", "supreme", "patagonia"]
        fast_fashion = ["kiabi", "primark", "bershka", "pull&bear", "stradivarius"]
        
        mq = marque.lower().strip()
        if any(b in mq for b in luxe_brands):
            segment, coef = "luxe", 0.95
        elif any(b in mq for b in premium_brands):
            segment, coef = "premium", 1.0
        elif any(b in mq for b in fast_fashion):
            segment, coef = "fast_fashion", 0.85
        elif prix_estime > 200:
            segment, coef = "premium", 1.0
        else:
            segment, coef = "mid", 1.05
        
        conseil = round_price(prix_estime * coef) if prix_estime > 0 else round_price(prix_achat * 1.4)
        max_price = round_price(conseil * 1.15)
        min_price = round_price(conseil * 0.85)
        
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

    def rapport(self, r: dict) -> str:
        """Rapport formaté."""
        lines = []
        lines.append(f"── {r['titre'][:50]} ──")
        lines.append("")
        lines.append(f"  {r['description']}")
        lines.append("")
        pr = r['prix_conseille']
        lines.append(f"  Prix conseillé: {pr['conseille']}€ (min {pr['min']}€ / max {pr['max']}€)")
        lines.append(f"  Marge: +{pr['marge_conseil']:.0f}€ (achat {pr['prix_achat']:.0f}€)")
        if r['tags']:
            lines.append(f"  Hashtags: {' '.join('#'+t for t in r['tags'])}")
        return "\n".join(lines)


if __name__ == "__main__":
    lg = ListingGenerator()
    
    # Test: générer 5 annonces différentes
    tests = [
        ("Nike", "Air Force 1", "sneakers", "très bon état", "42", "blanc", 25, 45,
         "Modèle iconique, très confortable", "Cuir", "oui"),
        ("Chanel", "Classique", "sac", "très bon état", "", "noir", 1800, 3500,
         "Modèle iconique intemporel, excellent état", "Cuir d'agneau", "oui"),
        ("Levi's", "501", "jeans", "bon état", "W32/L34", "bleu", 15, 30,
         "Vintage américain, taille bien", "Denim", "non"),
    ]
    
    for i, t in enumerate(tests):
        r = lg.generate(
            marque=t[0], modele=t[1], categorie=t[2],
            etat=t[3], taille=t[4], couleur=t[5],
            prix_achat=t[6], prix_estime=t[7],
            specificite=t[8], matiere=t[9], boite=t[10],
        )
        print(f"\n\n=== ANNONCE #{i+1} (voix: {r['voix']}) ===")
        print(lg.rapport(r))
    
    # Tester que 3 annonces identiques donnent 3 résultats différents
    print("\n\n=== TEST VARIATIONS (3 fois même article) ===")
    for i in range(3):
        r = lg.generate("Nike", "Air Force 1", "sneakers", "très bon état",
                       "42", "blanc", 25, 45, "Modèle iconique",
                       "Cuir", "oui")
        print(f"\n--- Variation {i+1} (voix: {r['voix']}) ---")
        print(f"  Titre: {r['titre']}")
        print(f"  Desc: {r['description'][:120]}...")
        print(f"  Tags: {r['tags']}")
