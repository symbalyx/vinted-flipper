# Installation — Linux (production)

## 1. Prérequis
- Python 3.10+ (`python3 --version`)
- `git`, `curl`
- (Optionnel, vision locale) [Ollama](https://ollama.com) : `ollama pull llava`

## 2. Récupération & config
```bash
cd jarvis
cp .env.example .env
# édite .env : JARVIS_PASSWORD, backend IA, options GUARDIAN_*
```

## 3. Environnement Python
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements_v4.txt
# optionnel : pip install -r requirements-optional.txt
```

## 4. Lancement production (Gunicorn)
```bash
./scripts/run_linux.sh
```
Le script crée le venv au besoin, charge `.env`, puis lance **Gunicorn** sur
`wsgi:app` (arrêt gracieux, logs rotatifs dans `logs/`).
Ouvre : `http://localhost:8004/app` (le Gardien : `http://localhost:8004/gardien`).

> Un seul worker (`JARVIS_WORKERS=1`) : l'état sécurité/Gardien est en mémoire.
> Pour scaler, il faudra externaliser l'état (hors périmètre actuel).

## 5. HTTPS
Recommandé : **reverse-proxy** (nginx/Caddy) devant Gunicorn. Sinon, certificats :
```bash
export JARVIS_SSL_CERT=/chemin/cert.pem JARVIS_SSL_KEY=/chemin/key.pem
./scripts/run_linux.sh
```

## 6. Démarrage automatique (systemd)
`/etc/systemd/system/jarvis.service` :
```ini
[Unit]
Description=JARVIS
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/jarvis
ExecStart=/opt/jarvis/scripts/run_linux.sh
Restart=on-failure
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload && sudo systemctl enable --now jarvis
```

## 7. Healthcheck
```bash
./scripts/healthcheck.sh http://localhost:8004/api/health
```

## 8. Tests
```bash
python -m compileall server tests
pytest -q
```
