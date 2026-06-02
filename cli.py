#!/usr/bin/env python3
"""
Vinted Flipper CLI — Interface interactive.
Analyse, tracke et optimise tes flips Vinted.
"""
import argparse, sys, json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BASE_DIR))
from flipper import FlipEngine

C = {"g": "\033[92m", "r": "\033[91m", "y": "\033[93m", "c": "\033[96m", "b": "\033[1m", "n": "\033[0m"}


def p(text, color=""):
    print(f"{color}{text}{C['n']}")


def header(text):
    print(f"\n{C['b']}{C['c']}{'='*55}{C['n']}")
    print(f"{C['b']}{C['c']}  {text}{C['n']}")
    print(f"{C['b']}{C['c']}{'='*55}{C['n']}")


def cmd_analyze(args):
    """Analyse un flip potentiel."""
    fe = FlipEngine()
    titre = input(f"  {C['b']}Titre:{C['n']} ").strip()
    if not titre: return
    prix = input(f"  {C['b']}Prix achat (€):{C['n']} ").strip().replace(",", ".")
    if not prix: return
    try: prix = float(prix)
    except: p("  Prix invalide", C['r']); return

    etat = input(f"  {C['b']}État (neuf/t bon/bon/satisf):{C['n']} [bon] ").strip() or "bon état"
    cat = input(f"  {C['b']}Catégorie:{C['n']} ").strip()
    marque = input(f"  {C['b']}Marque:{C['n']} ").strip()
    ship = input(f"  {C['b']}Port (light/medium/heavy):{C['n']} [medium] ").strip() or "medium"

    r = fe.analyze(titre, prix, etat, cat, marque, ship)
    print(f"\n{C['g']}{fe.rapport(r)}{C['n']}")

    # Enregistrer ?
    save = input(f"\n  Enregistrer ce flip ? (o/N) ").strip().lower()
    if save == 'o':
        revente = float(input(f"  {C['b']}Prix de revente réel (€):{C['n']} ").strip().replace(",", "."))
        fe.record(titre, prix, revente)
        s = "✅" if revente > prix else "❌"
        p(f"  {s} Flip enregistré !", C['g'])


def cmd_batch(args):
    """Analyse plusieurs annonces en mode rapide."""
    fe = FlipEngine()
    entries = 0
    p(f"  Mode batch — colle une annonce par ligne (titre | prix | état | catégorie | marque)", C['y'])
    p(f"  Exemple: Nike Air Force 1 | 25 | très bon état | sneakers | nike", C['y'])
    p(f"  Ligne vide pour terminer\n")
    while True:
        try:
            line = input(f"  [{entries+1}] ").strip()
            if not line: break
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 2:
                p("    Format: titre | prix | état | catégorie | marque", C['y'])
                continue
            titre = parts[0]
            try: prix = float(parts[1].replace(",", "."))
            except: p("    Prix invalide", C['r']); continue
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
    """Affiche les stats de flips."""
    fe = FlipEngine()
    s = fe.stats()
    if s["flips"] == 0:
        p("  Aucun flip enregistré.", C['y'])
    else:
        p("  STATS FLIPS", C['b'])
        p(f"  Total: {s['flips']} | WR: {s['wr']}% ({s['wins']}W/{s['losses']}L)")
        p(f"  Investi: {s['spent']:.2f}€ | Revenu: {s['revenue']:.2f}€")
        profit = s['profit']
        profit_color = C['g'] if profit > 0 else C['r']
        p(f"  Profit total: {profit_color}{profit:+.2f}€{C['n']}")
        p(f"  Profit moyen/flip: {s['avg_profit']:.2f}€")
        p(f"  ROI total: {s['roi_total']:+.1f}%")

        if s["flips"] > 0:
            p(f"\n  Derniers flips:", C['b'])
            for f in fe.history["flips"][-5:]:
                prof = f['profit']
                c = C['g'] if prof > 0 else C['r']
                p(f"  {c}{prof:+.2f}€{C['n']} | {f['title'][:45]}")


def cmd_history(args):
    """Liste tous les flips."""
    fe = FlipEngine()
    if not fe.history["flips"]:
        p("  Aucun flip enregistré.", C['y']); return
    p(f"  {'Date':<12} {'Profit':>8} {'Titre':<45}", C['b'])
    p(f"  {'-'*65}", C['b'])
    for f in reversed(fe.history["flips"][-20:]):
        d = f['date'][:10]
        prof = f['profit']
        c = C['g'] if prof > 0 else C['r']
        p(f"  {d:<12} {c}{prof:>+8.2f}€{C['n']} {f['title'][:45]}")


def cmd_watch(args):
    """Gère la watchlist."""
    fe = FlipEngine()
    if args.action == "add":
        q = input("  Recherche: ").strip()
        mx = input("  Prix max (0=aucun): ").strip()
        fe.add_search(q, float(mx) if mx else 0)
        p(f"  ✅ Recherche ajoutée: {q}", C['g'])
    elif args.action == "list":
        if not fe.watchlist["searches"]:
            p("  Aucune recherche surveillée.", C['y'])
        else:
            for s in fe.watchlist["searches"]:
                p(f"  #{s['id']} {s['query']} (max {s['max_price']:.0f}€)")


def cmd_export(args):
    """Exporte les flips en JSON."""
    fe = FlipEngine()
    path = args.file or f"flips_export_{datetime.now():%Y%m%d}.json"
    with open(path, "w") as f:
        json.dump(fe.history, f, indent=2, ensure_ascii=False)
    p(f"  ✅ Exporté: {path} ({len(fe.history['flips'])} flips)", C['g'])


def main():
    parser = argparse.ArgumentParser(description="Vinted Flipper CLI")
    parser.add_argument("cmd", nargs="?", default="analyze",
                        choices=["analyze", "batch", "stats", "history", "watch", "export"],
                        help="Commande")
    parser.add_argument("--action", default="add", help="Action pour watch")
    parser.add_argument("--file", "-f", help="Fichier pour export")
    args = parser.parse_args()

    cmds = {
        "analyze": cmd_analyze,
        "batch": cmd_batch,
        "stats": cmd_stats,
        "history": cmd_history,
        "watch": cmd_watch,
        "export": cmd_export,
    }

    header(f"VINTED FLIPPER — {args.cmd.upper()}")
    cmds[args.cmd](args)


if __name__ == "__main__":
    main()
