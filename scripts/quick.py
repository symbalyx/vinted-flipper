#!/usr/bin/env python3
"""
Quick Decide — Analyse ultra-rapide pour le mobile.
Tu vois une annonce sur ton téléphone → tu colles → le bot dit ACHETER ou SKIP.
"""
import sys, re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(BASE_DIR))
from flipper import FlipEngine
from scanner import ScamDetector


def quick_decide(text: str):
    """Analyse rapide depuis une ligne collée.
    
    Formats acceptés:
    "Nike Air Force 1 25€ très bon état"
    "Nike Air Force 1 | 25 | très bon état | sneakers"
    "https://www.vinted.fr/... 25€" (URL avec prix)
    """
    fe = FlipEngine()
    sd = ScamDetector()
    
    # Nettoyer
    text = text.strip()
    
    # Extraire le prix (pattern: nombre suivi de € ou euro)
    price_match = re.search(r'(\d+[.,]?\d*)\s*(?:€|euro|eur)', text)
    price = float(price_match.group(1).replace(',', '.')) if price_match else 0
    
    # Enlever le prix du texte pour le titre
    title = re.sub(r'\d+[.,]?\d*\s*(?:€|euro|eur)', '', text).strip()
    title = re.sub(r'\s*\|\s*', ' | ', title)  # Normaliser les pipes
    
    if price <= 0:
        return "  ❌ Impossible de détecter le prix. Format: 'Article 25€ état'"
    
    # Extraire l'état
    etat = "bon état"
    for e in ["neuf avec étiquette", "neuf", "très bon état", "tres bon etat",
              "bon état", "bon etat", "satisfaisant"]:
        if e in title.lower():
            etat = e
            break
    
    # Analyse flip
    result = fe.analyze(title, price, etat, "", "")
    
    # Analyse arnaque (rapide, sans infos vendeur)
    scam = sd.analyze(title=title, price=price, category=result.get("categorie",""),
                      brand=result.get("marque",""))
    
    # Décision finale
    profit = result["profit_net"]
    margin = result["marge_pct"]
    scam_score = scam["score_risque"]
    
    lines = []
    lines.append(f"── QUICK DECIDE ──")
    lines.append(f"  {title[:60]}")
    lines.append(f"  Prix: {price:.0f}€ | Revente estimée: {result['estimation_revente']:.0f}€")
    
    if scam_score >= 40:
        lines.append(f"  🚨 RISQUE ARNAQUE ({scam_score}/100) — {scam['niveau']}")
        lines.append(f"  → NE PAS ACHETER")
    elif profit <= 0:
        lines.append(f"  ❌ Profit négatif ({profit:.1f}€) — SKIP")
    elif profit < 8:
        lines.append(f"  ⚠️ Profit faible ({profit:.1f}€) — SKIP (frais trop élevés)")
    elif margin < 20:
        lines.append(f"  ⚠️ Marge trop faible ({margin:.0f}%) — SKIP")
    elif profit >= 20 and margin >= 40:
        lines.append(f"  ✅ ACHETER ! Profit {profit:.0f}€ (marge {margin:.0f}%)")
        lines.append(f"  → Marque: {result['marque']} | Cat: {result['categorie']}")
    elif profit >= 10:
        lines.append(f"  👍 BON FLIP — +{profit:.0f}€ (marge {margin:.0f}%)")
    else:
        lines.append(f"  ➡️ SI BESOIN — +{profit:.0f}€ (marge {margin:.0f}%)")
    
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        print("  Colle ton annonce (titre + prix + état):")
        try:
            text = sys.stdin.readline().strip()
        except EOFError:
            text = ""
    
    if text:
        print(f"\n{quick_decide(text)}\n")
    else:
        print("  Usage: python3 quick.py Nike Air Force 1 25€ très bon état")
