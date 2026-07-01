# Guide JARVIS Agency v5.6

## Ce que fait Agency

Agency transforme une demande complexe en mission persistante. Le coordinateur
crée un graphe d’étapes, lance les travaux indépendants en parallèle, conserve
les checkpoints dans SQLite et contrôle la définition de fini avant de déclarer
la mission terminée.

Rôles disponibles : analyste, chercheur, constructeur, ingénieur n8n,
communication, audit sécurité, vérification, rapport, recherche de prospects,
qualification commerciale, rédaction de prise de contact et conformité.

## Lancer une mission

Depuis `/agency`, renseigne l’objectif et surtout des critères mesurables. Exemple :

```text
Objectif : auditer le projet, corriger les failles prioritaires et produire le ZIP.
Définition de fini : compilation réussie, tous les tests verts, aucun secret,
ZIP extrait et retesté, rapport final avec limites.
```

Pour une campagne de prospection, utilise directement `/prospection` puis
**Lancer une campagne durable**. JARVIS crée une mission Agency avec recherche
publique, déduplication, scoring, brouillons non envoyés et contrôle conformité.

## États

- `queued`, `planning`, `running` : travail prêt ou actif ;
- `retry_wait` : nouvel essai persistant programmé ;
- `waiting_approval` : une action externe attend l’utilisateur ;
- `paused` : tranche de calcul finie, reprise automatique ;
- `blocked` : information, permission ou stratégie humaine nécessaire ;
- `completed` : critères finaux vérifiés ;
- `cancelled` : arrêt explicite par l’utilisateur.

Un refus d’approbation ne devient ni un succès ni un abandon : la mission reste
`blocked` et peut être reprise avec une stratégie différente.

## Durée de vie

`max_minutes` est une tranche de calcul, pas la durée de vie totale. En mode
`continue_until_done`, le superviseur reprend les missions `paused`,
`interrupted` et `retry_wait`, y compris après un redémarrage. Les actions déjà
réussies utilisent des reçus d’idempotence pour éviter les doublons.

Le serveur doit naturellement être en fonctionnement pour travailler. Lorsqu’il
est éteint, la base conserve l’état et la reprise a lieu au prochain démarrage.
Une tâche impossible ou dépendante d’une validation reste `blocked` plutôt que
d’être déclarée terminée à tort.

Voir `DURABLE_AGENCY_GUIDE.md` pour les baux, retries, mémoire et sauvegardes.
