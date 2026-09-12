import re, json, sys, glob, os

TARGET = {'f_232251_':'rotation', 'f_232250_':'position', 'f_232252_':'scale'}
INTERP = {'f_232230_':'linear', 'f_232229_':'catmullrom'}

stmt_re = re.compile(r'public static final AnimationDefinition (\w+) = (.*?);\n', re.S)
kf_re = re.compile(r'new Keyframe\(([-\d.eEf]+), KeyframeAnimations\.(m_\d+_)\(\((?:float|double)\)([-\d.eEf]+), \((?:float|double)\)([-\d.eEf]+), \((?:float|double)\)([-\d.eEf]+)\), AnimationChannel\.Interpolations\.(f_\d+_)\)')
chan_re = re.compile(r'\.m_232279_\("([^"]+)", new AnimationChannel\(AnimationChannel\.Targets\.(f_\d+_), new Keyframe\[\]\{(.*?)\}\)\)', re.S)

def f(s): return float(s.rstrip('fF'))

out = {}
for path in sys.argv[1:]:
    src = open(path).read()
    cls = os.path.basename(path).replace('.java','')
    for name, body in stmt_re.findall(src):
        length = f(re.search(r'Builder\.m_232275_\(\(float\)([-\d.eEf]+)\)', body).group(1))
        looping = '.m_232274_()' in body
        anim = {'source': cls, 'length': length, 'loop': looping, 'bones': {}}
        # split the body into channel chunks conservatively
        pos = 0
        for m in chan_re.finditer(body):
            bone, tgt, kfs = m.group(1), TARGET[m.group(2)], m.group(3)
            ks = []
            for t, fn, x, y, z, it in kf_re.findall(kfs):
                ks.append({'t': f(t), 'v': [f(x), f(y), f(z)], 'i': INTERP[it]})
            anim['bones'].setdefault(bone, {})[tgt] = ks
        out[name] = anim
json.dump(out, open(sys.argv[0].replace('parse_anim.py','../ror_anims.json'),'w'), indent=1)
for n,a in out.items():
    print(f"{n:20s} src={a['source'][:14]:14s} len={a['length']:6.3f} loop={str(a['loop']):5s} bones={len(a['bones'])} kf={sum(len(v) for b in a['bones'].values() for v in b.values())}")
