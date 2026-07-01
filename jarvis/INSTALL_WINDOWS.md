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
