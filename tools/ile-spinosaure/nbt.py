"""Encodeur NBT minimal (big-endian, gzip), suffisant pour un schematic Sponge v2.

Les valeurs Python sont typees explicitement par des enveloppes : Byte, Short, Int, Long,
Float, Double, String, List (type des elements), Compound (dict), ByteArray, IntArray.
"""
import gzip
import struct

TAG = {'end': 0, 'byte': 1, 'short': 2, 'int': 3, 'long': 4, 'float': 5, 'double': 6,
       'bytearray': 7, 'string': 8, 'list': 9, 'compound': 10, 'intarray': 11, 'longarray': 12}


class T:
    __slots__ = ('kind', 'v', 'elem')

    def __init__(self, kind, v, elem=None):
        self.kind, self.v, self.elem = kind, v, elem


def Byte(v): return T('byte', int(v))
def Short(v): return T('short', int(v))
def Int(v): return T('int', int(v))
def Long(v): return T('long', int(v))
def Float(v): return T('float', float(v))
def Double(v): return T('double', float(v))
def String(v): return T('string', str(v))
def ByteArray(v): return T('bytearray', bytes(v))
def IntArray(v): return T('intarray', [int(x) for x in v])
def Compound(d): return T('compound', d)
def List(elem, items): return T('list', list(items), elem)


def _str(s):
    b = s.encode('utf-8')
    return struct.pack('>H', len(b)) + b


def _payload(t):
    k, v = t.kind, t.v
    if k == 'byte':
        return struct.pack('>b', v)
    if k == 'short':
        return struct.pack('>h', v)
    if k == 'int':
        return struct.pack('>i', v)
    if k == 'long':
        return struct.pack('>q', v)
    if k == 'float':
        return struct.pack('>f', v)
    if k == 'double':
        return struct.pack('>d', v)
    if k == 'string':
        return _str(v)
    if k == 'bytearray':
        return struct.pack('>i', len(v)) + v
    if k == 'intarray':
        return struct.pack('>i', len(v)) + struct.pack('>%di' % len(v), *v)
    if k == 'list':
        elem = t.elem if v else 'end'
        return struct.pack('>bi', TAG[elem], len(v)) + b''.join(_payload(x) for x in v)
    if k == 'compound':
        out = []
        for nom, val in v.items():
            out.append(struct.pack('>b', TAG[val.kind]) + _str(nom) + _payload(val))
        out.append(b'\x00')
        return b''.join(out)
    raise ValueError(k)


def ecrire(chemin, nom_racine, racine):
    data = struct.pack('>b', TAG['compound']) + _str(nom_racine) + _payload(racine)
    with gzip.open(chemin, 'wb', compresslevel=9) as f:
        f.write(data)
    return len(data)
