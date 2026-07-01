# Changelog JARVIS v5.5 Agency + Voice

## Agency

- moteur de missions persistantes SQLite ;
- planification LLM stricte avec plan déterministe de secours ;
- 1 à 8 sous-agents et étapes parallèles selon dépendances ;
- reprise après redémarrage et annulation coopérative ;
- interface `/agency` et API `/api/agency/*` ;
- outils de chat pour lancer, consulter et annuler une mission ;
- contexte d’approbation lié à la mission et à l’étape ;
- reprise automatique après exécution d’une approbation ;
- refus d’une action = étape échouée, jamais comptée comme accomplie ;
- après redémarrage, une approbation perdue est recréée au lieu d’être supposée réussie ;
- arguments sensibles masqués dans les journaux.

## Connecteurs

- client n8n Public API avec clé côté serveur ;
- validation de workflows et blocage des nœuds risqués par défaut ;
- création/modification sensibles, activation/désactivation critiques ;
- SMTP avec validation des destinataires et envoi critique.

## Voix

- API `/api/voice/status`, `/warmup`, `/transcribe` ;
- chargement paresseux et thread-safe de faster-whisper ;
- modèle, device, quantification, langue, VAD et beam configurables ;
- capture navigateur avec echo cancellation, noise suppression et AGC ;
- détection client de la fin de parole et interruption de la synthèse ;
- fallback Web Speech si le module local n’est pas installé.

## Tests

- stockage et cycle de missions ;
- parallélisme et attente d’approbation ;
- liaison des approbations aux missions ;
- validation n8n et refus d’Execute Command ;
- validation SMTP ;
- API voix multipart et présence des protections frontend.
