"""Retire des animations par nom (doublons mesures par doublons.py)."""
import json, sys
bb = json.load(open(sys.argv[1]))
noms = set(open(sys.argv[3]).read().split())
avant = len(bb['animations'])
bb['animations'] = [a for a in bb['animations'] if a['name'] not in noms]
json.dump(bb, open(sys.argv[2], 'w'), separators=(',', ':'))
manquants = noms - {a['name'] for a in json.load(open(sys.argv[1]))['animations']}
print('%d animations -> %d (%d retirees)' % (avant, len(bb['animations']), avant - len(bb['animations'])))
for n in sorted(noms):
    print('   retiree :', n)
if manquants:
    print('   INTROUVABLES :', manquants)
