# OSINT légal et géolocalisation photo — périmètre JARVIS v5.4

JARVIS emploie le terme **OSINT autorisé**, pas « doxxing ». Le produit ne peut
pas garantir qu'une enquête est légale dans tous les pays ; il impose donc un
périmètre volontairement plus étroit et traçable.

## Usages acceptés

- analyser une photo personnelle ou un média appartenant à l'utilisateur ;
- retrouver les coordonnées EXIF d'une photo avec l'autorisation du propriétaire ;
- identifier un monument, un lieu public ou une infrastructure publique ;
- retrouver un commerce ou un établissement ouvert au public ;
- analyser un bien, véhicule ou site contrôlé par l'utilisateur ;
- dossier professionnel explicitement autorisé, sans recherche de personne.

## Usages refusés

- identifier une personne à partir de son visage ou de son apparence ;
- retrouver son domicile, son téléphone, son e-mail ou ses comptes sociaux ;
- suivre une personne en temps réel ou reconstituer ses habitudes ;
- exploiter une plaque d'immatriculation pour identifier un particulier ;
- agréger des données personnelles afin d'intimider, exposer ou harceler ;
- contourner le consentement en appelant directement l'API.

Les refus sont appliqués côté serveur par `server/guardian/legal_osint.py`.
L'interface seule n'est pas considérée comme une protection suffisante.

## Ce que « position exacte » signifie réellement

1. **GPS EXIF** : JARVIS peut restituer exactement les coordonnées enregistrées
   dans le fichier. Cela ne prouve pas que la photo a réellement été prise là :
   les métadonnées peuvent être supprimées ou modifiées.
2. **Lieu public distinctif** : la vision peut proposer un monument ou une zone,
   mais le résultat reste une estimation jusqu'à vérification indépendante.
3. **Photo générique sans EXIF** : aucune IA ne peut garantir une rue ou une
   adresse exacte. JARVIS renvoie `unknown` plutôt qu'une fausse certitude.

## Confidentialité

- la photo jointe au chat n'est pas enregistrée dans les conversations ;
- le journal conserve seulement le statut, la source et la finalité, jamais
  l'image ni les coordonnées complètes ;
- `GUARDIAN_CLOUD_VISION=0` garde l'analyse vision sur le réseau local ;
- toute utilisation cloud doit être activée explicitement côté serveur.
