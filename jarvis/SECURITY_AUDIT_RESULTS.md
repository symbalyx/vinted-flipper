# Audit sécurité final — JARVIS v5.6

## Périmètre vérifié

- moteur Agency, stockage SQLite, planification et approbations ;
- connecteurs e-mail et n8n ;
- CRM et campagne de prospection ;
- interfaces `/agency` et `/prospection` ;
- mémoire inter-missions et reçus d’idempotence ;
- non-régression des protections Gardien, Photo → globe et voix locale.

## Résultats principaux

### Corrigé — abandon prématuré des missions

Une erreur d’étape ne devient plus un faux succès. Les erreurs transitoires sont
retentées avec backoff. Après épuisement des essais courts, une nouvelle série
est programmée et persistée. Les pannes du planificateur ou de l’orchestrateur
passent elles aussi en `retry_wait` lorsque `continue_until_done` est actif.

### Corrigé — perte de mission au redémarrage

Les missions, étapes, dépendances, checkpoints, heartbeats et dates de reprise
sont stockés dans SQLite. Les états `interrupted`, `paused` et `retry_wait` sont
repris par le superviseur. Un bail atomique empêche deux workers d’exécuter la
même mission simultanément.

### Corrigé — double effet externe après crash

Les actions externes réussies créent un reçu dérivé de la mission, de l’étape,
de l’outil et des paramètres exacts. Une reprise identique réutilise le résultat
sans renvoyer l’e-mail ou recréer l’action.

### Corrigé — faux achèvement

Une mission ne passe à `completed` qu’après contrôle de sa définition de fini.
En cas de manque, JARVIS ajoute correction, revalidation et rapport. Après les
cycles autorisés, elle reste `blocked` et reprenable au lieu d’être déclarée
réussie.

### Corrigé — refus d’approbation traité comme échec destructif

Un refus place désormais l’étape et la mission en `blocked`. L’action n’est pas
exécutée. Une reprise explicite peut demander une stratégie différente, sans
contourner l’approbation refusée.

### Ajouté — sauvegardes cohérentes et contrôle d’intégrité

Les bases Agency et Prospection sont vérifiées avec `PRAGMA quick_check`, puis
copiées avec l’API SQLite de sauvegarde. Les fichiers sont remplacés atomiquement
et une rétention bornée évite une croissance illimitée du dossier de backup.

### Corrigé — mémoire contenant des coordonnées ou secrets

La mémoire inter-missions conserve des méthodes et preuves, pas le CRM complet.
Les e-mails, numéros de téléphone et chaînes ressemblant à des secrets sont
masqués dans l’objectif, les critères, le verdict et les résultats conservés.
Les paramètres sensibles sont également masqués dans les journaux d’approbation.

## Prospection

Les protections suivantes sont actives :

- URL de source professionnelle publique obligatoire ;
- aucune adresse privée dans le schéma ;
- déduplication et motifs de score ;
- liste d’exclusion par prospect, e-mail et domaine ;
- droit d’opposition dans les brouillons ;
- aucune route CRM d’envoi direct ;
- chaque envoi réel est `CRITICAL` et approuvé individuellement ;
- limites quotidienne, par domaine et entre deux messages ;
- aucune affirmation de démonstration sans URL réelle ;
- campagne Agency limitée à 50 prospects par demande ;
- aucun envoi automatique dans la définition de fini de campagne.

## Vérifications statiques

- aucune occurrence de `innerHTML`, `insertAdjacentHTML` ou `document.write`
  dans les interfaces servies ;
- aucun secret probable codé en dur détecté ;
- le jeton JARVIS n’est pas conservé dans le stockage navigateur ;
- les fichiers `.env`, bases runtime, conversations, logs et snapshots sont
  exclus du paquet final ;
- compilation Python réussie ;
- **207 tests réussis**.

## Risques résiduels et limites

1. **Processus local.** Le superviseur est un thread du serveur. SQLite permet la
   reprise et les baux, mais ce n’est pas encore une file distribuée Redis/RQ ou
   Celery. L’ordinateur doit être allumé pour travailler.
2. **Blocage légitime.** Une approbation, un secret de configuration, une source
   inexistante ou une décision humaine peut maintenir une mission en `blocked`
   ou `waiting_approval`. JARVIS ne doit pas contourner ce blocage.
3. **Fournisseurs externes.** SMTP, n8n, moteurs LLM et recherche web peuvent être
   indisponibles ou limiter les requêtes. Le backoff évite une boucle agressive,
   mais ne peut pas réparer un compte ou une clé invalide.
4. **Prospection.** Le module applique des garde-fous produit ; l’utilisateur
   reste responsable du respect des règles applicables à sa juridiction et des
   conditions des sources consultées.
5. **Tests d’endurance.** La persistance et la reprise sont testées de façon
   automatisée, mais une campagne de plusieurs semaines doit encore être
   validée sur une machine dédiée avec sauvegardes et supervision.

## Recommandations de déploiement

- conserver `JARVIS_AUTH=1` et utiliser HTTPS hors de `localhost` ;
- exécuter JARVIS comme service Windows ou `systemd` avec redémarrage automatique ;
- sauvegarder régulièrement `data/agency.db` et `data/prospecting.db` ;
- utiliser des comptes SMTP/n8n de test avant production ;
- surveiller l’espace disque et la taille des bases ;
- migrer vers workers Redis/RQ ou Celery avant une répartition multi-machine.
