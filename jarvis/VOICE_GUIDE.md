# Guide voix locale JARVIS

## Installation

```bash
pip install -r requirements-voice.txt
```

Le premier chargement télécharge le modèle si celui-ci n’est pas déjà présent.
Précharge-le après le démarrage :

```bash
curl -X POST http://localhost:8004/api/voice/warmup
```

## Profils conseillés

### CPU ancien ou portable

```dotenv
VOICE_STT_MODEL=tiny
VOICE_STT_DEVICE=cpu
VOICE_STT_COMPUTE_TYPE=int8
VOICE_BEAM_SIZE=1
```

### CPU correct, français plus fiable

```dotenv
VOICE_STT_MODEL=base
VOICE_STT_DEVICE=cpu
VOICE_STT_COMPUTE_TYPE=int8
VOICE_BEAM_SIZE=1
```

### GPU NVIDIA

```dotenv
VOICE_STT_MODEL=small
VOICE_STT_DEVICE=cuda
VOICE_STT_COMPUTE_TYPE=float16
VOICE_BEAM_SIZE=1
```

## Latence

La latence dépend du processeur, du modèle et de la durée de la phrase. Le client
coupe le flux après le silence au lieu d’envoyer un long enregistrement. Pour
une conversation plus naturelle, active `VOICE_AUTO_SEND=1` après avoir vérifié
que la détection de fin de parole fonctionne correctement dans la pièce.

## Confidentialité

L’audio est transcrit localement avec faster-whisper, placé dans un fichier
temporaire puis supprimé. Il n’est pas conservé par le module voix.
