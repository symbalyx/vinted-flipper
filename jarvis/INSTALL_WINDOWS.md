# Installation — Windows (production)

## 1. Prérequis
- Python 3.10+ (coche « Add python.exe to PATH » à l'installation)
- (Optionnel, vision locale) [Ollama](https://ollama.com) : `ollama pull llava`

## 2. Config
```powershell
cd jarvis
Copy-Item .env.example .env
notepad .env   # JARVIS_PASSWORD, backend IA, options GUARDIAN_*
```

## 3. Lancement production (Waitress)
```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_windows.ps1
```
Le script crée le venv, installe les dépendances + **Waitress**, charge `.env`
et sert `wsgi:app`.
Ouvre : `http://localhost:8004/app` — Gardien : `http://localhost:8004/gardien`.

> Waitress ne gère pas TLS : placer **IIS** ou un reverse-proxy HTTPS devant
> pour du HTTPS.

## 4. Démarrage automatique
Planificateur de tâches → « Créer une tâche » :
- Déclencheur : *À l'ouverture de session* (ou *Au démarrage*).
- Action : `powershell.exe` avec arguments
  `-ExecutionPolicy Bypass -File C:\jarvis\scripts\run_windows.ps1`.
- Cocher « Exécuter même si l'utilisateur n'est pas connecté ».

Alternative service : [NSSM](https://nssm.cc) pointant sur
`.venv\Scripts\waitress-serve.exe --listen=0.0.0.0:8004 wsgi:app`
(répertoire de travail = `jarvis\server`).

## 5. Healthcheck
```powershell
Invoke-WebRequest http://localhost:8004/api/health | Select-Object -Expand Content
```

## 6. Tests
```powershell
python -m compileall server tests
pytest -q
```

## 7. Dépannage
- Webcam non détectée : autorise l'accès caméra (Paramètres → Confidentialité).
- `opencv` : **n'installe pas** `opencv-python` en plus de `opencv-contrib-python`.


## Agency, n8n et voix

Pour la voix locale :

```bash
pip install -r requirements-voice.txt
```

Configure ensuite `VOICE_STT_MODEL`, `VOICE_STT_DEVICE` et
`VOICE_STT_COMPUTE_TYPE`, puis appelle `POST /api/voice/warmup` après le
démarrage. L'interface Agency est disponible sur `/agency`.

Pour n8n, renseigne `N8N_URL` et `N8N_API_KEY`. Pour les e-mails, renseigne les
variables `SMTP_*`. Les actions externes restent bloquées jusqu'à approbation
dans JARVIS.

## v5.6 — démarrage durable

Conserve les fichiers suivants entre deux mises à jour :

```text
data/agency.db
data/prospecting.db
```

Pour réduire la latence vocale après le démarrage :

```powershell
Invoke-RestMethod -Method Post http://localhost:8004/api/voice/warmup
```

Interfaces supplémentaires :

```text
http://localhost:8004/agency
http://localhost:8004/prospection
```

Pour qu’une mission reprenne après redémarrage de Windows, installe le script de
lancement comme service ou tâche planifiée avec redémarrage automatique. JARVIS
ne travaille pas quand le PC est éteint, mais il reprend sa base SQLite au
prochain démarrage.
