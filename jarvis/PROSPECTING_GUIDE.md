# Guide Prospection v5.6

## Finalité

Le module aide à organiser une prospection professionnelle raisonnable. Il ne
remplace pas un avis juridique et ne doit pas servir à collecter des données
privées, contourner des conditions d’utilisation ou envoyer des messages en
masse.

## Informations acceptées

- nom de l’entreprise ;
- URL de source professionnelle publique ;
- site officiel ;
- e-mail professionnel publié ;
- contact professionnel public facultatif ;
- région ;
- constats vérifiables ;
- base de contact : public B2B, relation existante, consentement ou recommandation.

Aucun champ d’adresse privée n’est prévu.

## Campagne durable

Dans `/prospection`, indique le secteur, la région, le nombre de prospects et
l’offre, puis clique sur **Lancer avec Agency**. La mission créée continue par
tranches jusqu’à ce que le CRM et le rapport satisfassent les critères. Elle
prépare éventuellement des brouillons, mais n’envoie aucun message.

## Pipeline conseillé

```text
recherche publique
→ déduplication
→ vérification de la source
→ qualification
→ classement
→ brouillon
→ contrôle conformité
→ approbation individuelle
→ envoi éventuel
→ réponse / exclusion / relance
```

## Scoring

Le score est explicable, pas magique. Il peut prendre en compte :

- présence d’une source ;
- existence ou absence d’un site ;
- e-mail professionnel public ;
- zone connue ;
- problème numérique documenté ;
- relation existante ou consentement.

Une absence de site est un indice, pas une certitude de besoin.

## Messages

Le brouillon par défaut :

- explique honnêtement pourquoi le prospect est contacté ;
- propose un échange court ;
- n’affirme pas avoir créé un site sans URL de démonstration réelle ;
- inclut une possibilité simple d’opposition.

## Envoi

Aucune route publique du CRM n’envoie directement un message. Le seul envoi se
fait via l’outil `prospection_envoyer_brouillon`, classé `CRITICAL`.

Garde-fous :

- approbation par brouillon ;
- maximum quotidien ;
- maximum par domaine ;
- délai minimal entre deux envois ;
- liste de suppression e-mail et domaine ;
- protection contre le double envoi du même brouillon ;
- reçu d’idempotence de la mission.

## Exemple de mission

```text
Trouve 15 menuisiers autour de Bordeaux depuis leurs sites officiels et annuaires
professionnels publics. Ajoute l’URL de preuve, déduplique, note la qualité de
leur présence web, prépare 5 brouillons courts et n’envoie aucun message.
Définition de fini : 15 fiches sourcées, 5 brouillons, rapport de conformité.
```

## Interdictions produit

- adresses personnelles ;
- données sensibles ;
- extraction derrière connexion ;
- contournement de CAPTCHA ;
- achat ou utilisation de listes volées ;
- faux prétexte ;
- affirmation mensongère de travail déjà réalisé ;
- envoi automatique de masse ;
- recontact d’un prospect supprimé.
