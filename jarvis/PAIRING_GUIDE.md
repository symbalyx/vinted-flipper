# Appairer un téléphone / une tablette comme « sonnette Gardien »

Un vieux téléphone ou une tablette posé(e) à l'entrée devient la **sonnette IA** :
caméra + haut-parleur, piloté par JARVIS. Un appareil Gardien a des **permissions
limitées** (`guardian:*`) et **jamais** le contrôle PC ni l'urgence complète.

## Principe
1. Depuis l'app **authentifiée** (`/app`), tu génères un **code d'appairage
   temporaire** (6 chiffres, valable 5 min).
2. L'appareil échange ce code contre un **token de session révocable**.
3. Tu peux **révoquer** l'appareil à tout moment.

## Étapes (API)
Génère un code (session authentifiée) :
```bash
curl -X POST http://localhost:8004/api/guardian/pair/create \
  -H "Content-Type: application/json" -H "X-JARVIS-Token: $TOKEN" \
  -d '{"name":"Tablette entrée"}'
# → {"code":"482913","expires_in":300,"name":"Tablette entrée"}
```
Sur l'appareil, échange le code :
```bash
curl -X POST http://localhost:8004/api/guardian/pair/redeem \
  -H "Content-Type: application/json" \
  -d '{"code":"482913","device_name":"iPad entrée"}'
# → {"ok":true,"device_id":"...","token":"...","scopes":["guardian:ingest",...]}
```
Lister / révoquer :
```bash
curl .../api/guardian/pair/devices   -H "X-JARVIS-Token: $TOKEN"
curl -X POST .../api/guardian/pair/revoke -H "X-JARVIS-Token: $TOKEN" \
  -H "Content-Type: application/json" -d '{"device_id":"..."}'
```

## Sur l'appareil (page `/gardien`)
- **Caméra avant/arrière** : sélecteur « Caméra ».
- **Micro** : désactivé par défaut (audio OFF). S'active seulement si
  `GUARDIAN_AUDIO_ENABLED=1`.
- **Test haut-parleur** : bouton « Déclencher la sirène » (coupe immédiatement).
- **Indicateur réseau** : pastille « en ligne / hors ligne » + reconnexion auto.
- **Plein écran / écran allumé** : « Garder l'écran allumé » (Wake Lock).
- **Coupure immédiate** : bouton toujours accessible (caméra + micro + audio).

## Limitation connue
Actuellement, la page `/gardien` s'appuie sur la **session authentifiée** (cookie)
partagée avec l'app. Le chemin « token d'appareil non authentifié par session »
(header `X-Guardian-Device`/`X-Guardian-Token` accepté dans `before_request`)
est **fourni côté serveur (endpoints + révocation) mais pas encore activé dans le
middleware d'auth**. En pratique : connecte l'appareil une fois via `/login`, ou
place-le derrière le reverse-proxy du LAN. Voir §6 de `CHANGELOG_GUARDIAN.md`.
