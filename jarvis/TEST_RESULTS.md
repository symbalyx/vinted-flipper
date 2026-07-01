# Résultats de tests — JARVIS v5.6 Durable Agency + Prospection

## Commandes exécutées

```bash
python -m compileall -q server tests
pytest --disable-warnings -ra
```

## Résultat réel

```text
207 passed
```

La compilation Python s’est terminée sans erreur.

## Couverture ajoutée en v5.6

### Durabilité Agency

- reprise d’une mission interrompue ;
- bail SQLite empêchant deux orchestrateurs d’exécuter la même mission ;
- retries courts puis persistants avec `next_run_at` ;
- panne de planification transformée en reprise programmée, pas en abandon ;
- checkpoints d’étape ;
- cycles de réparation avant validation finale ;
- mission `blocked` lorsque la définition de fini reste incomplète ;
- refus d’approbation conservé comme blocage reprenable ;
- limite de tours du sous-agent considérée comme erreur retentable ;
- reçu d’idempotence empêchant de rejouer une action externe après reprise ;
- mémoire inter-missions persistante après réouverture de SQLite ;
- masquage des e-mails, téléphones et secrets dans la mémoire Agency ;
- sauvegarde SQLite cohérente, contrôle d’intégrité et rétention.

### Prospection

- source professionnelle publique obligatoire ;
- déduplication ;
- qualification et explication du score ;
- aucun champ d’adresse privée ;
- brouillon honnête et droit d’opposition ;
- URL de démonstration mentionnée uniquement lorsqu’elle est fournie ;
- exclusion d’un prospect ou d’un domaine ;
- limites quotidiennes, par domaine et entre envois ;
- protection contre le double envoi ;
- envoi classé `CRITICAL` ;
- masquage des coordonnées et du contenu dans l’audit ;
- création d’une campagne Agency durable depuis `/prospection` ;
- refus d’une campagne sans secteur ou région ;
- absence de sinks DOM `innerHTML` dans l’interface Prospection.

### Régressions historiques

Les tests existants du chat, Gardien, géolocalisation photo autorisée, FaceBank,
permissions, urgences, n8n, voix locale et contrôle PC continuent de passer.

## Ce que ces tests ne prouvent pas

- la disponibilité réelle d’un serveur SMTP ou n8n externe ;
- la qualité commerciale des prospects trouvés sur Internet ;
- une exécution continue pendant plusieurs semaines sur un ordinateur réel ;
- le comportement d’un fournisseur LLM lors d’une panne longue ;
- la haute disponibilité multi-machine.

Ces points nécessitent un test d’endurance en conditions réelles et des comptes
de test dédiés. Le moteur persiste et reprend son état, mais il ne peut pas
travailler pendant que l’ordinateur est éteint.
