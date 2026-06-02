# Vinted Flipper 🔄

**Analyseur achat/revente Vinted** — calcule la rentabilité d'un flip, détecte les bonnes affaires, suit tes performances.

```
Achat 25€ → Estimation revente 43€ → Profit net +9.48€ (+38%) ✓
Achat 12€ → Estimation revente 15€ → Profit net -7.83€ (-65%) ✗
```

## Pourquoi ?

Vinted c'est 45M d'utilisateurs. Des milliers d'articles sous-évalués chaque jour. Le problème : savoir **quand acheter**. Ce bot calcule instantanément la marge après tous les frais (commission Vinted 5% + 0.70€, protection acheteur 0.8%, port, emballage).

## Installation

```bash
git clone https://github.com/symbalyx/vinted-flipper.git
cd vinted-flipper
python3 cli.py -h
```

## Utilisation

### Mode interactif
```bash
python3 cli.py analyze
```
Colle le titre, le prix, l'état → reçois la marge et la recommandation.

### Mode batch (plusieurs annonces d'un coup)
```bash
python3 cli.py batch
```
```
  [1] TRES BON FLIP | +18.48€ | +73.9% | Nike Air Force 1
  [2] SKIP          | -7.83€  | -65.2% | T-shirt Kiabi
  [3] FLIP EXCELLENT| +894€   | +111.8%| Sac Chanel
```

### Stats
```bash
python3 cli.py stats
python3 cli.py history
python3 cli.py export
```

## Comment çà marche

1. **Coefficient marque** — 80+ marques analysées (Hermès 1.20 → Primark 0.08)
2. **Demande catégorie** — sneakers/sacs/montres ont la meilleure demande
3. **État** — neuf avec étiquette → satisfaisant (coefficient 1.0 → 0.4)
4. **Frais réels** — commission Vinted, protection acheteur, port, emballage
5. **Recommandation** — SKIP / SI BESOIN / BON FLIP / TRES BON FLIP / FLIP EXCELLENT

## Marques les plus rentables

| Marque | Coefficient | |
|--------|:-:|---|
| Hermès, Chanel, Louis Vuitton | +110-120% | ⭐ Meilleur ROI |
| Cartier, Rolex | +105-110% | ⭐ Montres |
| Arc'teryx, Stone Island, Supreme | +80-85% | ⭐ Streetwear |
| Nike, Adidas, New Balance | +50-58% | ✅ Bon marché |
| **Kiabi, Primark** | **+8-12%** | ❌ À éviter |

## Flux recommandé

1. Scanne Vinted → articles en **prix croissant**
2. Filtre les **marques à fort coefficient** (Chanel, Hermès, Arc'teryx, etc.)
3. Analyse avec `cli.py` → vérifie la marge
4. Si **BON FLIP** et **confiance > 50%** → achète
5. Nettoie, prends des photos propres, mets en vente
6. Enregistre le flip → tes stats s'améliorent

## Structure

```
vinted-flipper/
├── flipper.py     # Moteur d'analyse (coeur)
├── cli.py         # Interface CLI
├── scripts/
│   └── browser_search.py  # Plan navigation Vinted
├── docs/
│   └── index.html  # GitHub Pages
└── data/           # Stats & historique (auto-généré)
```

## Licence

MIT — Symbalyx
