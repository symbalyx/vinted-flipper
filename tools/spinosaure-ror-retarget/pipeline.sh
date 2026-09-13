#!/bin/sh
set -e
cd "$(dirname "$0")/.."
echo "--- doublons retires ---"
python3 tools/retire.py RIVIERE_70_ADAPTATION_ROR_UPDATED.bbmodel E0.bbmodel /tmp/a_supprimer.txt
echo "--- voile (profil C) ---"
python3 tools/voile.py E0.bbmodel E1.bbmodel C | tail -2
echo "--- bras grossis ---"
python3 tools/grossir_bras.py E1.bbmodel E1b.bbmodel | head -2
echo "--- griffes allongees ---"
python3 tools/bras_ror.py E1b.bbmodel E1c.bbmodel
echo "--- nageoires (main, avant-bras, orteils, tibia) ---"
python3 tools/nageoires.py E1c.bbmodel E2.bbmodel
echo "--- recuit ---"
python3 tools/recook.py E2.bbmodel F FINAL4.bbmodel
echo "--- verification ---"
python3 tools/verify_recook.py E2.bbmodel FINAL4.bbmodel
