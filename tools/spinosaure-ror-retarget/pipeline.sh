#!/bin/sh
# Chaine complete : animations -> voile -> bras -> recuit -> verification
set -e
cd "$(dirname "$0")/.."
echo "--- voile (profil C) ---"
python3 tools/voile.py RIVIERE_70_ADAPTATION_ROR_UPDATED.bbmodel E1.bbmodel C | tail -3
echo "--- bras (pagaie + membrane + griffes) ---"
python3 tools/bras_ror.py E1.bbmodel E2.bbmodel
echo "--- recuit ---"
python3 tools/recook.py E2.bbmodel F FINAL2.bbmodel
echo "--- verification : rien d autre que des cles supprimees ---"
python3 tools/verify_recook.py E2.bbmodel FINAL2.bbmodel
