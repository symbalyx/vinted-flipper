# JARVIS v5.6 — image de production (auto-hébergement Docker)
FROM python:3.11-slim

# Dépendances système minimales pour OpenCV (headless) + healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends \
      libglib2.0-0 libgl1 curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    JARVIS_HOST=0.0.0.0 \
    JARVIS_PORT=8004

WORKDIR /app

# En conteneur (souvent headless) on utilise opencv-python-headless au lieu de
# opencv-contrib-python : pas de reconnaissance faciale cv2.face (dégradation
# gracieuse), mais image bien plus légère et sans dépendance graphique.
COPY requirements_v4.txt requirements-optional.txt ./
RUN pip install -r requirements_v4.txt gunicorn \
    && pip uninstall -y opencv-contrib-python || true \
    && pip install "opencv-python-headless>=4.10.0"

COPY . .

EXPOSE 8004
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:8004/api/health || exit 1

WORKDIR /app/server
# 1 worker (état sécurité/Gardien en mémoire), threads pour le SSE + MJPEG.
CMD ["gunicorn", "-w", "1", "-k", "gthread", "--threads", "8", \
     "--timeout", "120", "--graceful-timeout", "30", \
     "-b", "0.0.0.0:8004", "wsgi:app"]
