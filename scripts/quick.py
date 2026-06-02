#!/usr/bin/env python3
"""
Quick Decide v2 — Décision rapide, ton naturel.
Tu vois une annonce sur ton tel, tu colles, le bot te dit si ça vaut le coup.
Style: pote qui te donne son avis, pas un terminal de trading.
"""
import sys, re, random
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(BASE_DIR))
from flipper import FlipEngine
from scanner import ScamDetector


# ─── Réponses humaines ───────────────────────────────────────

ACHAT_TOP = [
    "GO. {profit}€ de marge, {margin}% — fonce.",
    "Clairement oui. Tu prends {profit}€ net, vends vite.",
    "Bon plan. +{profit}€, marge {margin}%. A prendre.",
]

ACHAT_BON = [
    "Bon flip. {profit}€ de bénéf, correct.",
    "Ouais ça le fait. +{profit}€, rien à dire.",
    "C'est okay. {profit}€ de marge, ça tourne.",
]

SKIP_PERTE = [
    "Non. Tu perds {profit}€ après frais.",
    "Perte. Pas rentable.",
    "Avec les frais t'es dans le rouge. Skip.",
]

SKIP_FAIBLE = [
    "Bof. {profit}€ de marge c'est trop juste avec les frais Vinted.",
    "Marge trop faible ({profit}€). Ça vaut pas le temps.",
    "{profit}€ net, franchement ça vaut pas le détour.",
]

ARNAQUE_DETECTEE = [
    "Attention arnaque. Score: {score}/100. Je passerais.",
    "Signaux d'arnaque. Risque {score}%. Passe ton chemin.",
    "Ça sent pas bon. {score}% de risque. Je tenterais pas.",
]

MAYBE = [
    "Limite. +{profit}€, marge {margin}%. A voir si t'as besoin.",
    "Pour dépanner. {profit}€ c'est pas fou. Si t'as rien d'autre.",
    "Moyen. {profit}€ de marge. Ça dépend de ton budget.",
]

BEST_DEAL = [
    "Excellente affaire. +{profit}€, {margin}% de marge.",
    "Top! {profit}€ net. Prends-le.",
    "Gros profit: +{profit}€ ({margin}%). A prendre les yeux fermés.",
]


def quick_decide(text: str):
    """Analyse rapide depuis une ligne collée."""
    fe = FlipEngine()
    sd = ScamDetector()
    
    text = text.strip()
    
    # Extraire le prix
    price_match = re.search(r'(\d+[.,]?\d*)\s*(?:€|euro|eur)', text)
    price = float(price_match.group(1).replace(',', '.')) if price_match else 0
    
    title = re.sub(r'\d+[.,]?\d*\s*(?:€|euro|eur)', '', text).strip()
    title = re.sub(r'\s*\|\s*', ' | ', title)
    
    if price <= 0:
        price_match2 = re.search(r'(\d+[.,]?\d*)', text)
        if price_match2:
            price = float(price_match2.group(1).replace(',', '.'))
            if price > 1000:
                price = 0
    
    if price <= 0 or price > 99999:
        return "  Impossible de détecter le prix. Essaye: Article 25€ tres bon etat"
    
    # Extraire l'état
    etat = "bon etat"
    etat_patterns = ["neuf avec etiquette", "neuf avec etiquettes", "neuf",
                     "tres bon etat", "très bon état", "très bon etat",
                     "bon etat", "bon état", "satisfaisant"]
    for e in sorted(etat_patterns, key=len, reverse=True):
        if e in title.lower():
            etat = e
            title = title.lower().replace(e, "").strip()
            break
    
    # Nettoyer
    title = re.sub(r'[|;:]', ' ', title).strip()
    title = re.sub(r'\s+', ' ', title)[:80]
    
    if not title or len(title) < 3:
        title = "Article"
    
    result = fe.analyze(title, price, etat, "", "")
    
    scam = sd.analyze(title=title, price=price,
                      category=result.get("categorie",""),
                      brand=result.get("marque",""))
    
    profit = result["profit_net"]
    margin = result["marge_pct"]
    scam_score = scam["score_risque"]
    
    # Construire la réponse
    lines = [f"--- {title[:60].strip()} ---"]
    lines.append(f"Achat: {price:.0f}€ | Revente estimee: {result['estimation_revente']:.0f}€")
    
    if scam_score >= 40:
        msg = random.choice(ARNAQUE_DETECTEE).format(score=scam_score)
        lines.append(f"Score: {scam_score}/100")
    elif profit <= 0:
        msg = random.choice(SKIP_PERTE).format(profit=profit)
    elif profit < 8 or margin < 20:
        msg = random.choice(SKIP_FAIBLE).format(profit=profit)
    elif profit >= 25 and margin >= 50:
        msg = random.choice(BEST_DEAL).format(profit=int(profit), margin=int(margin))
    elif profit >= 20 and margin >= 40:
        msg = random.choice(ACHAT_TOP).format(profit=int(profit), margin=int(margin))
    elif profit >= 10:
        msg = random.choice(ACHAT_BON).format(profit=int(profit), margin=int(margin))
    else:
        msg = random.choice(MAYBE).format(profit=int(profit), margin=int(margin))
    
    lines.append(msg)
    lines.append(f"{result['marque']} — {result['categorie']}")
    lines.append(f"Profit net: {profit:+.0f}€ (marge {margin:.0f}%)")
    
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        print("Colle ton annonce (titre + prix + etat):")
        try:
            text = sys.stdin.readline().strip()
        except EOFError:
            text = ""
    
    if text:
        print(f"\n{quick_decide(text)}\n")
    else:
        print("Usage: python3 quick.py Nike Air Force 1 25€ tres bon etat")
