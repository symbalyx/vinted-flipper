# Vinted Flipper 🔄

**Analyseur achat/revente Vinted** — détecte les arnaques, calcule les marges, génère des annonces pro, suit tes performances.

```
Achat 25€ → Marge +9.48€ (+38%) → Annonce pro générée ✅
Arnaque détectée : "Chanel à 45€" → Score risque 100/100 🔴
```

## 3 modules en 1

| Module | Commande | Utilité |
|---|---|---|
| **Flipper** | `analyze` | Calcule la rentabilité (frais Vinted, marque, état, catégorie) |
| **Scanner** | `scam` | Détecte les arnaques (prix, description, vendeur, photos) |
| **Listing** | `generate` | Génère des annonces professionnelles |

## Installation

```bash
git clone https://github.com/symbalyx/vinted-flipper.git
cd vinted-flipper
python3 cli.py -h
```

## Utilisation

### Analyse complète (flip + scan + annonce)
```bash
python3 cli.py analyze
```
Entre le titre, le prix, la catégorie → reçois :
- La **marge estimée** et la recommandation
- Le **scan d'arnaque**
- L'**annonce pro générée**

### Détection d'arnaques
```bash
python3 cli.py scam
```
Détecte : prix anormal, phrases suspectes, nouveau compte, photos volées, contact hors plateforme.

### Mode batch
```bash
python3 cli.py batch
```
```
  Nike Air Force 1 | 25 | très bon état | sneakers | nike
  → BON FLIP        | +9.48€ | +37.9%
  
  Sac Chanel | 45 | bon état | sac | chanel
  → SKIP (arnaque probable)
```

### Stats & Historique
```bash
python3 cli.py stats    # Profit total, win rate, ROI
python3 cli.py history  # Derniers flips
python3 cli.py export   # Export JSON
```

## Comment ça marche

### Flipper
- 80+ marques avec coefficient de revente (Hermès 1.20 → Primark 0.08)
- 20+ catégories avec demande estimée
- Frais réels Vinted (5% + 0.70€ + 0.8% protection + port + emballage)

### Scanner arnaque
- 6 facteurs d'analyse : prix, description, titre, vendeur, photos, marque
- 100+ phrases d'arnaque détectées
- Score de risque 0-100 avec alertes détaillées

### Listing pro
- Templates par catégorie (sneakers, sac, veste, montre...)
- Titre optimisé SEO Vinted
- Prix conseillé avec fourchette (min/max)
- Hashtags automatiques

## Marques les plus rentables

| Marque | Coefficient | |
|---|---|---|
| Hermès, Chanel, Louis Vuitton | +110-120% | ⭐ Meilleur ROI |
| Cartier, Rolex | +105-110% | ⭐ Montres |
| Arc'teryx, Stone Island, Supreme | +80-85% | ⭐ Streetwear |
| Nike, Adidas | +50-58% | ✅ Bon marché |
| Kiabi, Primark | +8-12% | ❌ À éviter |

## Prochaines étapes

- [ ] Interface web (Flask)
- [ ] Monitoring automatique des nouvelles annonces
- [ ] Alerts Telegram/Discord pour les bonnes affaires
- [ ] Base de données des prix de vente réels

## Licence

MIT — Symbalyx
