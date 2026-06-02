#!/usr/bin/env python3
"""
Vinted Flipper CLI — Interface tout-en-un.
Analyse, tracke, scanne les arnaques et génère des annonces pro.
"""
import argparse, sys, json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BASE_DIR))
from flipper import FlipEngine, BRAND_FACTOR
from scanner import ScamDetector
from listing import ListingGenerator

C = {"g": "\033[92m", "r": "\033[91m", "y": "\033[93m", "c": "\033[96m", "b": "\033[1m", "n": "\033[0m"}
p = lambda t, c="": print(f"{c}{t}{C['n']}")

def header(text):
    print(f"\n{C['b']}{C['c']}{'='*55}{C['n']}")
    print(f"{C['b']}{C['c']}  {text}{C['n']}")
    print(f"{C['b']}{C['c']}{'='*55}{C['n']}")


def cmd_analyze(args):
    """Analyse un flip potentiel."""
    fe = FlipEngine()
    titre = input(f"  {C['b']}Titre:{C['n']} ").strip()
    if not titre: return
    prix = _input_float("Prix achat (€)")
    if prix is None: return
    etat = input(f"  {C['b']}État (neuf/t bon/bon/satisf):{C['n']} [bon] ").strip() or "bon état"
    cat = input(f"  {C['b']}Catégorie:{C['n']} ").strip()
    marque = input(f"  {C['b']}Marque:{C['n']} ").strip()
    ship = input(f"  {C['b']}Port (light/medium/heavy):{C['n']} [medium] ").strip() or "medium"

    r = fe.analyze(titre, prix, etat, cat, marque, ship)
    print(f"\n{C['g']}{fe.rapport(r)}{C['n']}")

    # Scam check
    print()
    scan = input(f"  Scanner l'annonce ? (o/N) ").strip().lower()
    if scan == 'o':
        sd = ScamDetector()
        sr = sd.analyze(title=titre, price=prix, category=cat, brand=marque)
        print(f"\n{sd.rapport(sr)}")

    # Enregistrer ?
    save = input(f"\n  Enregistrer ce flip ? (o/N) ").strip().lower()
    if save == 'o':
        revente = _input_float("Prix de revente réel (€)")
        if revente:
            fe.record(titre, prix, revente)
            p(f"  ✅ Flip enregistré !", C['g'])

    # Générer annonce ?
    gen = input(f"  Générer une annonce pro ? (o/N) ").strip().lower()
    if gen == 'o':
        _generate_listing(marque, cat, etat, prix, r.get("estimation_revente", prix*1.3), titre)


def cmd_scam(args):
    """Détecte les arnaques sur une annonce."""
    sd = ScamDetector()
    print(f"  Analyse d'arnaque — entre les infos de l'annonce\n")
    titre = input(f"  {C['b']}Titre:{C['n']} ").strip() or "?"
    prix = _input_float("Prix (€)") or 0
    desc = input(f"  {C['b']}Description:{C['n']} ").strip() or ""
    cat = input(f"  {C['b']}Catégorie:{C['n']} ").strip()
    marque = input(f"  {C['b']}Marque:{C['n']} ").strip()

    # Infos vendeur
    rev = input(f"  {C['b']}Nombre d'avis vendeur:{C['n']} [0] ").strip()
    reviews = int(rev) if rev.isdigit() else 0
    jours = input(f"  {C['b']}Âge du compte (jours):{C['n']} [999] ").strip()
    age = int(jours) if jours.isdigit() else 999
    stock = input(f"  {C['b']}Photos issues d'internet ? (o/N):{C['n']} ").strip().lower() == 'o'
    phone = input(f"  {C['b']}Téléphone vérifié ? (O/n):{C['n']} ").strip().lower() != 'n'

    r = sd.analyze(
        title=titre, price=prix, description=desc,
        category=cat, brand=marque,
        seller_reviews=reviews, seller_joined_days=age,
        is_stock_photo=stock, seller_has_verified_phone=phone,
    )
    print(f"\n{sd.rapport(r)}")


def cmd_generate(args):
    """Génère une annonce pro."""
    print(f"  Générateur d'annonce professionnelle\n")
    marque = input(f"  {C['b']}Marque:{C['n']} ").strip()
    if not marque: return
    cat = input(f"  {C['b']}Catégorie:{C['n']} ").strip() or "default"
    etat = input(f"  {C['b']}État:{C['n']} [bon état] ").strip() or "bon état"
    taille = input(f"  {C['b']}Taille:{C['n']} ").strip()
    couleur = input(f"  {C['b']}Couleur:{C['n']} [noir] ").strip() or "noir"
    modele = input(f"  {C['b']}Modèle:{C['n']} ").strip()
    matiere = input(f"  {C['b']}Matière:{C['n']} ").strip()
    spec = input(f"  {C['b']}Point fort:{C['n']} ").strip()
    prix_achat = _input_float("Prix d'achat (€)") or 0

    _generate_listing(marque, cat, etat, prix_achat, 0, f"{marque} {modele}".strip())


def _generate_listing(marque, cat, etat, prix_achat, prix_estime, titre_indicatif):
    """Helper: génère et affiche une annonce."""
    lg = ListingGenerator()
    # Estimer prix si pas fourni
    if prix_estime <= 0 and prix_achat > 0:
        fe = FlipEngine()
        r = fe.analyze(titre_indicatif, prix_achat, etat, cat, marque)
        prix_estime = r.get("estimation_revente", prix_achat * 1.3)

    # Suggérer prix si pas d'achat
    prix_conseil = prix_estime or 50

    r = lg.generate(
        marque=marque, categorie=cat, etat=etat,
        taille="", couleur="noir",
        prix_achat=prix_achat, prix_estime=prix_conseil,
    )

    print(f"\n{C['g']}{lg.rapport(r)}{C['n']}")

    # Sauvegarder ?
    save = input(f"\n  Sauvegarder l'annonce ? (o/N) ").strip().lower()
    if save == 'o':
        path = f"annonce_{datetime.now():%Y%m%d_%H%M}.txt"
        with open(path, "w") as f:
            f.write(f"=== {r['titre']} ===\n\n")
            f.write(f"Prix conseillé: {r['prix_conseille']['conseille']:.2f}€\n\n")
            f.write(r['description'])
        p(f"  ✅ Sauvegardée: {path}", C['g'])


def _input_float(prompt):
    try:
        val = input(f"  {C['b']}{prompt}:{C['n']} ").strip().replace(",", ".")
        return float(val) if val else None
    except ValueError:
        p("  Valeur invalide", C['r'])
        return None


def cmd_batch(args):
    """Analyse plusieurs annonces en lot."""
    fe = FlipEngine()
    entries = 0
    p("  Mode batch — une annonce par ligne: titre | prix | état | catégorie | marque", C['y'])
    p("  Ligne vide pour terminer\n")
    while True:
        try:
            line = input(f"  [{entries+1}] ").strip()
            if not line: break
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 2: continue
            titre = parts[0]
            try: prix = float(parts[1].replace(",", "."))
            except: continue
            etat = parts[2] if len(parts) > 2 else "bon état"
            cat = parts[3] if len(parts) > 3 else ""
            marque = parts[4] if len(parts) > 4 else ""
            r = fe.analyze(titre, prix, etat, cat, marque)
            rec = r['recommandation']
            color = C['g'] if "FLIP" in rec else C['r'] if rec == "SKIP" else C['y']
            p(f"    {rec:20s} | {r['profit_net']:+.2f}€ | {r['marge_pct']:+.1f}% | {titre[:40]}", color)
            entries += 1
        except EOFError: break
    p(f"\n  {entries} annonces analysées", C['c'])


def cmd_stats(args):
    """Affiche les stats."""
    fe = FlipEngine()
    s = fe.stats()
    if s["flips"] == 0:
        p("  Aucun flip enregistré.", C['y'])
    else:
        p(f"  STATS FLIPS", C['b'])
        p(f"  Total: {s['flips']} | WR: {s['wr']}% ({s['wins']}W/{s['losses']}L)")
        p(f"  Investi: {s['spent']:.2f}€ | Revenu: {s['revenue']:.2f}€")
        profit_color = C['g'] if s['profit'] > 0 else C['r']
        p(f"  Profit total: {profit_color}{s['profit']:+.2f}€{C['n']}")
        p(f"  Profit moyen: {s['avg_profit']:.2f}€ | ROI: {s['roi_total']:+.1f}%")


def cmd_history(args):
    """Liste les flips."""
    fe = FlipEngine()
    if not fe.history["flips"]:
        p("  Aucun flip.", C['y']); return
    p(f"  {'Date':<12} {'Profit':>8} {'Titre':<45}", C['b'])
    p(f"  {'-'*65}")
    for f in reversed(fe.history["flips"][-20:]):
        prof = f['profit']
        c = C['g'] if prof > 0 else C['r']
        p(f"  {f['date'][:10]:<12} {c}{prof:>+8.2f}€{C['n']} {f['title'][:45]}")


def cmd_export(args):
    """Exporte en JSON."""
    fe = FlipEngine()
    path = args.file or f"flips_{datetime.now():%Y%m%d}.json"
    with open(path, "w") as f:
        json.dump(fe.history, f, indent=2, ensure_ascii=False)
    p(f"  ✅ Exporté: {path} ({len(fe.history['flips'])} flips)", C['g'])


def cmd_optimize(args):
    """Optimise les coefficients du moteur selon l'historique."""
    fe = FlipEngine()
    p(f"  Optimisation du moteur d'apprentissage...", C['y'])
    result = fe.optimize()
    if result["status"] == "need_more_data":
        p(f"  ⚠ Besoin d'au moins 3 flips enregistrés (actuel: {result['flips']})", C['y'])
    else:
        p(f"  ✅ Optimisation terminée!", C['g'])
        p(f"     Flips utilisés: {result['flips_used']}")
        p(f"     Erreur moyenne (MAE): {result['mae_pct']}%")
        p(f"     Marques ajustées: {result['brand_adjustments']}")
        p(f"     Catégories ajustées: {result['category_adjustments']}")
        p(f"  Le moteur est maintenant plus précis pour tes prochaines estimations.", C['g'])


def cmd_summary(args):
    """Résumé complet de l'état du moteur."""
    fe = FlipEngine()
    print(f"  {fe.summary()}")
    # Stats des marques
    p(f"\n  Top 5 marques (coeff revente):", C['b'])
    for brand, coeff in sorted(BRAND_FACTOR.items(), key=lambda x: -x[1])[:5]:
        bar = "█" * max(1, int(coeff * 10))
        p(f"    {brand:20s} {bar} x{coeff:.2f}")
    # Stats du détecteur
    sd = ScamDetector()
    p(f"\n  Scanner: {sd.model['analyses']} analyses | {sd.model['confirmed_fakes']} faux confirmés | {sd.model['confirmed_real']} réels confirmés", C['b'])


def main():
    parser = argparse.ArgumentParser(description="Vinted Flipper — Analyse, Scanne, Génère")
    parser.add_argument("cmd", nargs="?", default="analyze",
                        choices=["analyze", "batch", "stats", "history",
                                "export", "scam", "generate",
                                "optimize", "summary"],
                        help="Commande")
    parser.add_argument("--file", "-f", help="Fichier export")
    args = parser.parse_args()

    cmds = {
        "analyze": cmd_analyze,
        "batch": cmd_batch,
        "stats": cmd_stats,
        "history": cmd_history,
        "export": cmd_export,
        "scam": cmd_scam,
        "generate": cmd_generate,
        "optimize": cmd_optimize,
        "summary": cmd_summary,
    }

    header(f"VINTED FLIPPER — {args.cmd.upper()}")
    cmds[args.cmd](args)


if __name__ == "__main__":
    main()
