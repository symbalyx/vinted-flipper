#!/bin/sh
# Chaine complete : animations -> voile -> bras grossis -> pagaie -> recuit -> verification
set -e
cd "$(dirname "$0")/.."
echo "--- voile (profil C) ---"
python3 tools/voile.py RIVIERE_70_ADAPTATION_ROR_UPDATED.bbmodel E1.bbmodel C | tail -2
echo "--- bras grossis vers la masse de ROR ---"
python3 tools/grossir_bras.py E1.bbmodel E1b.bbmodel
echo "--- pagaie + membrane + griffes allongees ---"
python3 tools/bras_ror.py E1b.bbmodel E2.bbmodel
echo "--- recuit ---"
python3 tools/recook.py E2.bbmodel F FINAL3.bbmodel
echo "--- verification ---"
python3 tools/verify_recook.py E2.bbmodel FINAL3.bbmodel
