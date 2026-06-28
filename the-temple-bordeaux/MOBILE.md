# The Temple Bordeaux — passe d'adaptation mobile

Site statique (un seul `index.html`, assets self-hostés) repris pour un rendu
**propre, lisible et tactile** sur mobile, en appliquant les principes du
*Mobile Design System* (touch-first, battery-conscious, platform-respectful)
adaptés au web responsive.

## Déjà solide (conservé tel quel)
- Scène WebGL du héro en **pause hors écran et onglet caché** (batterie).
- Qualité 3D **adaptative** (cœurs / mémoire / `save-data`), sac 3D désactivé sur mobile.
- `prefers-reduced-motion` respecté partout, carte Leaflet sans drag sur mobile.
- Hauteur héro en `100svh`, listeners `passive`, aucun `console.log`.

## Améliorations apportées (cette passe)
1. **Cibles tactiles ≥ 44px** (loi de Fitts) — réseaux sociaux, liens de pied de
   page, bouton « Passer l'intro », liens contact, via un bloc
   `@media (hover:none) and (pointer:coarse)`.
2. **Safe-area insets** (encoche / Dynamic Island / barre d'accueil) — nav fixe,
   gouttières (`.wrap`), overlay menu et pied de page respectent
   `env(safe-area-inset-*)` (cohérent avec `viewport-fit=cover`).
3. **Retour au toucher** — le tactile n'a pas de `:hover` : ajout d'états
   `:active` (nav, menu, cartes, avis, liens) pour un feedback de pression.

Aucune logique métier ni structure HTML modifiée — uniquement la couche de
présentation mobile.
