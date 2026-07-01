"""Configuration pytest : prépare l'environnement et importe l'app une fois."""
import os
import sys
from pathlib import Path

# Environnement de test déterministe AVANT l'import du module
os.environ.setdefault("JARVIS_PASSWORD", "testpass")
os.environ.setdefault("JARVIS_PROACTIVE", "0")
os.environ.setdefault("JARVIS_AUTH", "1")
os.environ.setdefault("JARVIS_BACKEND", "deepseek")

SERVER = Path(__file__).resolve().parent.parent / "server"
sys.path.insert(0, str(SERVER))

import pytest


@pytest.fixture(scope="session")
def J():
    import jarvis_v4
    return jarvis_v4


@pytest.fixture()
def client(J):
    # Évite que le test de rate-limit bloque les autres (état partagé par IP)
    J._LOGIN_FAILS.clear()
    c = J.app.test_client()
    c.post("/login", data={"password": "testpass"})
    return c
