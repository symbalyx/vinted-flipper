# Guide Durable Agency v5.6

## Objectif

Le moteur Durable Agency empêche trois problèmes fréquents des agents longs :

1. perdre tout le travail après un redémarrage ;
2. considérer une étape partielle comme terminée ;
3. rejouer une action externe déjà exécutée.

## Création d’une mission

Depuis `/agency`, renseigne :

- l’objectif global ;
- une définition de fini mesurable ;
- la durée d’une tranche de calcul ;
- le nombre de sous-agents ;
- le nombre maximal d’étapes initiales ;
- le nombre de cycles de réparation.

Exemple de définition de fini :

```text
- 20 prospects dédupliqués ;
- une URL source pour chacun ;
- score et motif documentés ;
- 5 brouillons ;
- aucun envoi ;
- rapport final et contrôle anti-spam.
```

## Persistance

La base `data/agency.db` contient :

- `missions` ;
- `mission_steps` ;
- `mission_events` ;
- `mission_artifacts` ;
- `agency_memory` ;
- `mission_action_receipts`.

Sauvegarde cette base avec l’application arrêtée, ou utilise une sauvegarde
SQLite cohérente. Ne supprime pas `data/agency.db` lors d’une mise à jour.

## Heartbeat et bail

Chaque mission active renouvelle un bail SQLite. Un second worker qui voit le
même identifiant ne peut pas le réclamer tant que le bail est valide. Si le
processus meurt, le bail expire et un autre worker reprend la mission.

## Retries

Une erreur transitoire déclenche des essais courts avec backoff exponentiel.
Après l’épuisement d’une série d’essais, le mode `continue_until_done` programme
une nouvelle série plus tard au lieu de déclarer un faux succès.

Les erreurs persistantes peuvent donc rester en `retry_wait`. Les erreurs du
planificateur ou de l’orchestrateur suivent elles aussi un backoff durable au
lieu de transformer la mission en échec terminal. Utilise le journal pour
corriger une configuration si nécessaire ; le superviseur reprendra ensuite.

## Définition de fini

Une mission n’est jamais `completed` simplement parce que toutes les étapes ont
retourné du texte. Le validateur vérifie :

- présence d’une étape de vérification ;
- présence d’un rapport ;
- absence de marqueur d’erreur ou d’indisponibilité ;
- critères explicites fournis par l’utilisateur.

Si le résultat est incomplet, JARVIS ajoute un cycle :

```text
correction → revalidation → nouveau rapport
```

Après le maximum de cycles, la mission passe à `blocked`. Elle reste conservée
et peut être reprise après ajout d’informations.

## Idempotence

Les actions externes réussies sont enregistrées avec une clé dérivée de :

```text
mission_id + step_id + nom de l’outil + paramètres normalisés
```

Un retry identique réutilise le reçu. Les paramètres différents demandent une
nouvelle approbation et produisent une nouvelle action.

## Mémoire durable

Après validation, JARVIS enregistre une synthèse de méthodes et de preuves. Les
prochaines missions proches la reçoivent dans leur contexte. Les coordonnées
sont masquées dans cette synthèse ; le CRM reste la source détaillée.

## Arrêt volontaire

Les seules causes normales d’arrêt avant succès sont :

- annulation explicite ;
- refus d’une approbation indispensable, qui place la mission en `blocked` ;
- attente d’une approbation ;
- blocage nécessitant une information humaine ;
- serveur éteint, avec reprise au prochain démarrage.

## Sauvegardes et contrôle d’intégrité

Lorsque `JARVIS_DURABLE_BACKUPS=1`, JARVIS utilise l’API de sauvegarde SQLite et
`PRAGMA quick_check` pour créer des copies cohérentes de `agency.db` et
`prospecting.db` dans `data/backups/`. La fréquence et la rétention sont réglées
par `JARVIS_BACKUP_INTERVAL_HOURS` et `JARVIS_BACKUP_KEEP`.

Ces copies locales ne remplacent pas une sauvegarde hors machine. Synchronise le
dossier de sauvegarde vers un support distinct si les missions sont importantes.

## Haute disponibilité

La v5.6 est robuste avec SQLite et plusieurs workers grâce aux baux, mais elle
n’est pas un cluster distribué complet. Pour répartir des missions sur plusieurs
machines, la prochaine évolution recommandée est Redis/RQ ou Celery avec une
base PostgreSQL.
