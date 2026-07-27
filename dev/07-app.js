/* ═══════════════════════════════════════════════════════════════════════════
   Interface
   ═══════════════════════════════════════════════════════════════════════════ */
const BY_ID = {};
AXES.forEach(a => { BY_ID[a.id] = a; });
const IDS = AXES.map(a => a.id);
const MAX = 4;                                    /* cinq crans : 0 → 4 */

const S = { mix:{R:2,H:2,E:2,S:2,O:2}, active:'H', exo:null };

const $ = (id) => document.getElementById(id);
const REDUCED = matchMedia('(prefers-reduced-motion:reduce)').matches;
const clamp = (v) => v < 0 ? 0 : v > MAX ? MAX : v;

/* Typographie française : espace insécable avant : ; ! ? et après «. */
const NB = ' ';
const fr = (v) => String(v == null ? '' : v)
  .replace(/ ([:;!?»])/g, NB + '$1').replace(/« /g, '«' + NB);
const esc = (v) => fr(v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
  .replace(/"/g,'&quot;').replace(/'/g,'&#39;');

const lv = (ax, i) => BY_ID[ax].levels[i];
const cur = (ax) => lv(ax, S.mix[ax]);

/* ── graduations autour d’un bouton rotatif ───────────────────────────────── */
function ticks(){
  let d = '';
  for (let i = 0; i <= 24; i++) {
    const a = (-132 + i * 11) * Math.PI / 180;
    const long = i % 6 === 0;
    const r1 = long ? 41 : 44, r2 = 48;
    d += `M${(50 + r1 * Math.sin(a)).toFixed(1)} ${(50 - r1 * Math.cos(a)).toFixed(1)}`
       + `L${(50 + r2 * Math.sin(a)).toFixed(1)} ${(50 - r2 * Math.cos(a)).toFixed(1)}`;
  }
  return `<svg class="knob-ticks" viewBox="0 0 100 100" fill="none" stroke="currentColor"
    stroke-width="1.1" stroke-linecap="round" aria-hidden="true"><path d="${d}"/></svg>`;
}

/* ═══════════════════════════════════════════════════════════════════════════
   03 · Les cinq curseurs
   ═══════════════════════════════════════════════════════════════════════════ */
function buildAxes(){
  $('axes').innerHTML = AXES.map(a => `
    <article class="axis" style="--c:${a.c};--ct:${a.ct}">
      <span class="axis-l" aria-hidden="true">${a.id}</span>
      <div class="axis-h">
        <p class="axis-name">${esc(a.name)}</p>
        <h3 class="axis-q">${esc(a.key)}</h3>
        <p class="axis-sub">${esc(a.sub)}</p>
      </div>
      <div class="axis-spec">
        <b aria-hidden="true">1 → 5</b>
        ${a.levels.map(l => `<span>${esc(l.label)}</span>`).join('')}
      </div>
      <p class="axis-watch">${esc(a.watch)}</p>
    </article>`).join('');
}

/* ═══════════════════════════════════════════════════════════════════════════
   05 · Les 25 réglages
   ═══════════════════════════════════════════════════════════════════════════ */
function buildStrata(){
  $('strata').innerHTML = AXES.map(a => `
    <div class="stratum" style="--c:${a.c};--ct:${a.ct}">
      <div class="stratum-h">
        <b aria-hidden="true">${a.id}</b>
        <span>${esc(a.name)} — ${esc(a.key)}</span>
      </div>
      <div class="rungs">
        ${a.levels.map((l,i) => `
          <button class="rung${l.full ? ' demo' : ''}" type="button" aria-pressed="false"
            data-ax="${a.id}" data-lv="${i}"
            aria-label="Ouvrir ${l.code} ${esc(l.label)} dans la console">
            <b aria-hidden="true">${l.code}</b><span>${esc(l.label)}</span>
          </button>`).join('')}
      </div>
    </div>`).join('');

  $('strata').addEventListener('click', (ev) => {
    const b = ev.target.closest('.rung');
    if (!b) return;
    set(b.dataset.ax, Number(b.dataset.lv));
    $('console').scrollIntoView({behavior: REDUCED ? 'auto' : 'smooth', block:'start'});
  });
}

/* ═══════════════════════════════════════════════════════════════════════════
   04 · La console
   ═══════════════════════════════════════════════════════════════════════════ */
/* Choisir une situation remet les cinq curseurs au cran central et pose
   l'exercice. La console ne propose aucun réglage : c'est précisément ce
   qu'il y a à apprendre. */
function buildExercices(){
  $('premix').innerHTML = EXERCICES.map(p => `
    <button type="button" data-tag="${esc(p.tag)}" aria-pressed="false">
      <b>${esc(p.tag)}</b><span>${esc(p.name)}</span>
    </button>`).join('');
  $('premix').addEventListener('click', (ev) => {
    const b = ev.target.closest('button');
    if (!b) return;
    const p = EXERCICES.find(x => x.tag === b.dataset.tag);
    if (!p) return;
    S.exo = S.exo === p.tag ? null : p.tag;
    if (S.exo) IDS.forEach(k => { S.mix[k] = 2; });
    render();
    if (S.exo) toast('À vous : réglez les cinq curseurs pour « ' + p.name + ' ».');
  });
}

function buildMods(){
  $('mods').innerHTML = AXES.map(a => `
    <div class="mod" id="mod-${a.id}" style="--c:${a.c};--ct:${a.ct};--cl:${a.l}">
      <span class="mod-id" aria-hidden="true"><b>${a.id}</b><span>${esc(a.name)}</span></span>
      <div class="leds" id="leds-${a.id}" aria-hidden="true">
        ${[0,1,2,3,4].map(i => `
          <button class="led" type="button" tabindex="-1" data-ax="${a.id}" data-lv="${i}"
            title="${a.levels[i].code} — ${esc(a.levels[i].label)}"><i></i></button>`).join('')}
      </div>
      <div class="knob" id="knob-${a.id}" role="slider" tabindex="0" data-ax="${a.id}"
        aria-label="${esc(a.full)} — ${esc(a.key)}"
        aria-valuemin="1" aria-valuemax="5" aria-valuenow="1" aria-valuetext="">
        ${ticks()}<span class="knob-ix" id="ix-${a.id}"></span>
      </div>
      <div class="mod-out">
        <b id="out-code-${a.id}"></b>
        <span id="out-label-${a.id}"></span>
      </div>
    </div>`).join('');

  AXES.forEach(a => {
    const knob = $('knob-' + a.id);

    /* Glisser le bouton : le mouvement vertical et horizontal comptent tous
       les deux, comme sur un vrai potentiomètre. Un simple appui, sans
       glissement, avance d’un cran — le réglage reste atteignable au doigt. */
    let drag = null;
    knob.addEventListener('pointerdown', (ev) => {
      knob.setPointerCapture(ev.pointerId);
      knob.classList.add('grabbing');
      drag = {x:ev.clientX, y:ev.clientY, from:S.mix[a.id], moved:0};
      S.active = a.id;
      render();
    });
    knob.addEventListener('pointermove', (ev) => {
      if (!drag) return;
      const dx = ev.clientX - drag.x, dy = drag.y - ev.clientY;
      drag.moved = Math.max(drag.moved, Math.abs(dx) + Math.abs(dy));
      const next = clamp(drag.from + Math.round((dx + dy) / 22));
      if (next !== S.mix[a.id]) set(a.id, next);
    });
    const end = (ev) => {
      if (!drag) return;
      knob.classList.remove('grabbing');
      if (drag.moved < 7) set(a.id, S.mix[a.id] >= MAX ? 0 : S.mix[a.id] + 1);
      drag = null;
      if (knob.hasPointerCapture(ev.pointerId)) knob.releasePointerCapture(ev.pointerId);
    };
    knob.addEventListener('pointerup', end);
    knob.addEventListener('pointercancel', end);

    knob.addEventListener('keydown', (ev) => {
      const n = S.mix[a.id];
      let next = n;
      switch (ev.key) {
        case 'ArrowUp': case 'ArrowRight': next = clamp(n + 1); break;
        case 'ArrowDown': case 'ArrowLeft': next = clamp(n - 1); break;
        case 'PageUp': next = clamp(n + 2); break;
        case 'PageDown': next = clamp(n - 2); break;
        case 'Home': next = 0; break;
        case 'End': next = MAX; break;
        default:
          if (/^[1-5]$/.test(ev.key)) { next = Number(ev.key) - 1; break; }
          return;
      }
      ev.preventDefault();
      set(a.id, next);
    });

    /* La molette n’agit que sur un bouton déjà sélectionné : le défilement
       de la page n’est jamais détourné. */
    knob.addEventListener('wheel', (ev) => {
      if (document.activeElement !== knob) return;
      ev.preventDefault();
      set(a.id, clamp(S.mix[a.id] + (ev.deltaY < 0 ? 1 : -1)));
    }, {passive:false});

    knob.addEventListener('focus', () => { S.active = a.id; render(); });

    $('leds-' + a.id).addEventListener('click', (ev) => {
      const b = ev.target.closest('.led');
      if (b) set(a.id, Number(b.dataset.lv));
    });
  });
}

function set(ax, i){
  const n = clamp(i);
  if (S.mix[ax] === n && S.active === ax) return;
  S.mix[ax] = n;
  S.active = ax;
  render();
}

/* ── rendu ────────────────────────────────────────────────────────────────── */
function render(){
  AXES.forEach(a => {
    const i = S.mix[a.id], l = lv(a.id, i);

    const knob = $('knob-' + a.id);
    knob.setAttribute('aria-valuenow', String(i + 1));
    knob.setAttribute('aria-valuetext', fr(`${l.code}, niveau ${i + 1} sur 5 : ${l.label}`));
    $('ix-' + a.id).style.transform = `rotate(${-132 + i * 66}deg)`;

    Array.prototype.forEach.call($('leds-' + a.id).children, (b, n) => {
      b.classList.toggle('on', n <= i);
    });

    $('out-code-' + a.id).textContent = l.code;
    $('out-label-' + a.id).textContent = fr(l.label);
    $('mod-' + a.id).classList.toggle('live', S.active === a.id);
  });

  $('mix-codes').innerHTML = AXES.map(a => {
    const l = cur(a.id);
    /* fond en variante foncée : le blanc reste lisible sur les cinq couleurs */
    return `<b style="background:${a.ct};color:#fff" title="${esc(l.label)}">${l.code}</b>`;
  }).join('');

  $('mix-sig').textContent = signature();

  Array.prototype.forEach.call($('premix').children, (b) => {
    b.setAttribute('aria-pressed', String(b.dataset.tag === S.exo));
  });

  document.querySelectorAll('.rung').forEach(b => {
    b.setAttribute('aria-pressed',
      String(S.mix[b.dataset.ax] === Number(b.dataset.lv)));
  });

  renderRead();
  renderFiche();
}

/* Lecture du mix — purement descriptive.
   Elle décrit la FORME du réglage : son amplitude, les curseurs poussés, ceux
   laissés bas. Aucun seuil propre à RHESO, aucune combinaison désignée comme
   risquée : ces règles-là appartiennent à la formation. La console montre ce
   que l'on vient de régler, elle ne le juge pas. */
function renderRead(){
  const v = IDS.map(k => S.mix[k]);
  const hi = Math.max.apply(null, v), lo = Math.min.apply(null, v);
  const ampl = hi - lo;
  const names = (lvl) => IDS.filter(k => S.mix[k] === lvl).map(k => BY_ID[k].full);
  const liste = (a) => a.length > 1
    ? a.slice(0, -1).join(', ') + ' et ' + a[a.length - 1]
    : a[0];

  let txt;
  if (ampl === 0) {
    txt = 'Les cinq curseurs sont au même cran. Déplacez-en un : le réglage prend'
        + ' forme, et cette forme se discute.';
  } else {
    txt = 'Amplitude de ' + ampl + ' cran' + (ampl > 1 ? 's' : '') + '. '
        + 'Vous poussez ' + liste(names(hi)) + ' ; '
        + 'vous laissez en retrait ' + liste(names(lo)) + '.';
  }

  $('mix-read').className = 'mix-read ' + (ampl >= 3 ? 'watch' : 'calm');
  $('mix-label').textContent = S.exo
    ? fr('Exercice · ' + (EXERCICES.find(x => x.tag === S.exo) || {}).name)
    : 'Lecture du réglage';
  $('mix-text').textContent = fr(S.exo
    ? txt + ' Est-ce le réglage que cette situation réclame ? La réponse se'
          + ' construit en formation — la console ne la donne pas.'
    : txt);
}

function renderFiche(){
  const a = BY_ID[S.active], i = S.mix[S.active], l = a.levels[i];

  const body = l.full ? `
    <div class="fiche-blk">
      <h4>Ce que je fais</h4>
      <ul>${l.do.map(x => `<li>${esc(x)}</li>`).join('')}</ul>
    </div>
    <div class="fiche-blk say">
      <h4>Ce que je dis</h4>
      <ul>${l.say.map(x => `<li>${esc(x)}${NB}»</li>`).join('')}</ul>
    </div>
    <div class="fiche-intent">
      <span class="lbl">L’intention</span>
      <b>${esc(l.int)}</b>
    </div>
    <div class="fiche-blk">
      <h4>Frontière ${a.id}${i} / ${l.code}</h4>
      <p class="fiche-q">${esc(l.bd)}</p>
    </div>
    <p class="demo-flag">Fiche publiée en exemple</p>`
  : `
    <div class="fiche-blk">
      <h4>La question du curseur</h4>
      <p class="fiche-q"><b>${esc(a.key)}</b></p>
    </div>
    <div class="fiche-blk">
      <h4>Ce qu’il faut surveiller</h4>
      <p class="fiche-q">${esc(a.watch)}</p>
    </div>
    <div class="locked">
      <div class="locked-h">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" aria-hidden="true"><rect x="4.5" y="10.5" width="15" height="10" rx="2"/><path d="M8.2 10.5V7.8a3.8 3.8 0 0 1 7.6 0v2.7"/></svg>
        <span>Fiche réservée à la formation</span>
      </div>
      <p>
        Le contenu opérationnel de ce réglage n’est pas publié sur cette page.
        La fiche complète comprend :
      </p>
      <ul>
        <li>Ce que je fais</li>
        <li>Ce que je dis</li>
        <li>L’intention</li>
        <li>La frontière avec le niveau voisin</li>
      </ul>
      <a class="btn btn-ghost" href="mailto:methoderheso@gmail.com?subject=Acc%C3%A8s%20au%20r%C3%A9f%C3%A9rentiel%20RHESO">
        Demander l’accès au référentiel
      </a>
    </div>
    <p class="fiche-q" style="color:var(--muted);font-size:.82rem">
      Pour voir à quoi ressemble une fiche complète, ouvrez
      <b>${DEMO} « ${esc(BY_ID[DEMO[0]].levels[Number(DEMO[1]) - 1].label)} »</b>.
    </p>`;

  $('fiche').style.setProperty('--c', a.c);
  $('fiche').style.setProperty('--ct', a.ct);
  $('fiche').innerHTML = `
    <div class="fiche-top">
      <div class="fiche-eye">
        <span>${esc(a.full)} · cran ${i + 1} sur 5</span>
        <span>${l.full ? 'Fiche complète' : 'Structure publiée'}</span>
      </div>
      <p class="fiche-code">${l.code}</p>
      <h3 class="fiche-title">${esc(l.label)}</h3>
      <p class="fiche-line">${esc(l.line)}</p>
    </div>
    <div class="fiche-steps" role="group" aria-label="Crans du curseur ${esc(a.full)}">
      ${a.levels.map((x,n) => `
        <button type="button" data-lv="${n}" aria-pressed="${n === i}"
          aria-label="Cran ${n + 1} : ${esc(x.label)}">${x.code}</button>`).join('')}
    </div>
    <div class="fiche-body">${body}</div>`;

  $('fiche').querySelector('.fiche-steps').addEventListener('click', (ev) => {
    const b = ev.target.closest('button');
    if (b) set(a.id, Number(b.dataset.lv));
  });
}

/* ── partage ──────────────────────────────────────────────────────────────── */
const signature = () => IDS.map(k => k + (S.mix[k] + 1)).join('');

function readHash(){
  const m = /#reglage=([RHESO][1-5]){5}/.exec(location.hash);
  if (!m) return false;
  const pairs = location.hash.slice(9).match(/[RHESO][1-5]/g) || [];
  let ok = false;
  pairs.forEach(p => {
    if (!BY_ID[p[0]]) return;
    S.mix[p[0]] = Number(p[1]) - 1;
    ok = true;
  });
  if (ok) { S.exo = null; S.active = pairs[0][0]; }
  return ok;
}

function share(){
  const url = location.origin + location.pathname + '#reglage=' + signature();
  const done = () => toast('Lien du réglage copié.');
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url).then(done, () => { location.hash = '#reglage=' + signature(); });
  } else {
    location.hash = '#reglage=' + signature();
    toast('Réglage inscrit dans l’adresse de la page.');
  }
}

let toastT = null;
function toast(msg){
  let el = document.querySelector('.toast');
  if (!el) {
    el = document.createElement('div');
    el.className = 'toast';
    el.setAttribute('role', 'status');
    document.body.appendChild(el);
  }
  el.textContent = fr(msg);
  clearTimeout(toastT);
  toastT = setTimeout(() => el.remove(), 3400);
}

/* ═══════════════════════════════════════════════════════════════════════════
   06 · Les situations
   ═══════════════════════════════════════════════════════════════════════════ */
function buildSituations(){
  $('sit-tabs').innerHTML = SITUATIONS.map((g,i) => `
    <button type="button" role="tab" id="sit-${g.k}" data-k="${g.k}"
      aria-selected="${i === 0}" aria-controls="sit-panel">${esc(g.label)}</button>`).join('');
  $('sit-tabs').addEventListener('click', (ev) => {
    const b = ev.target.closest('button');
    if (b) showSituation(b.dataset.k);
  });
  $('sit-tabs').addEventListener('keydown', (ev) => {
    const b = ev.target.closest('button');
    if (!b) return;
    const i = SITUATIONS.findIndex(g => g.k === b.dataset.k);
    let n = -1;
    if (ev.key === 'ArrowDown' || ev.key === 'ArrowRight') n = (i + 1) % SITUATIONS.length;
    if (ev.key === 'ArrowUp' || ev.key === 'ArrowLeft') n = (i - 1 + SITUATIONS.length) % SITUATIONS.length;
    if (n < 0) return;
    ev.preventDefault();
    showSituation(SITUATIONS[n].k);
    $('sit-' + SITUATIONS[n].k).focus();
  });
  showSituation(SITUATIONS[0].k);
}

function showSituation(k){
  const g = SITUATIONS.find(x => x.k === k) || SITUATIONS[0];
  Array.prototype.forEach.call($('sit-tabs').children, (b) => {
    b.setAttribute('aria-selected', String(b.dataset.k === g.k));
  });
  const p = $('sit-panel');
  p.setAttribute('aria-labelledby', 'sit-' + g.k);
  p.innerHTML = `<h3>${esc(g.title)}</h3>
    <ul class="sit-lines">${g.lines.map((l,i) =>
      `<li><i aria-hidden="true">${String(i + 1).padStart(2,'0')}</i><span>${esc(l)}</span></li>`
    ).join('')}</ul>
    <p class="sit-note">${esc(g.note)}</p>`;
}

function buildRefs(){
  $('refs').innerHTML = REFS.map(r => `<li>${esc(r)}</li>`).join('');
}

/* ═══════════════════════════════════════════════════════════════════════════
   Chrome — en-tête, menu, sommaire actif
   ═══════════════════════════════════════════════════════════════════════════ */
function initChrome(){
  const hdr = $('hdr'), burger = $('burger'), sheet = $('sheet'), label = $('burger-label');

  addEventListener('scroll', () => {
    hdr.classList.toggle('stuck', scrollY > 6);
  }, {passive:true});

  const setSheet = (open) => {
    sheet.hidden = !open;
    burger.setAttribute('aria-expanded', String(open));
    label.textContent = open ? 'FERMER' : 'MENU';
  };
  burger.addEventListener('click', () => setSheet(burger.getAttribute('aria-expanded') !== 'true'));
  sheet.addEventListener('click', (ev) => { if (ev.target.closest('a')) setSheet(false); });
  addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape' && burger.getAttribute('aria-expanded') === 'true') {
      setSheet(false); burger.focus();
    }
  });

  const links = Array.prototype.slice.call(document.querySelectorAll('.hdr-nav a'));
  const targets = links.map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
  if (targets.length && 'IntersectionObserver' in window) {
    const spy = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (!e.isIntersecting) return;
        links.forEach(a => a.removeAttribute('aria-current'));
        const hit = links.find(a => a.getAttribute('href') === '#' + e.target.id);
        if (hit) hit.setAttribute('aria-current', 'true');
      });
    }, {rootMargin:'-45% 0px -50% 0px'});
    targets.forEach(t => spy.observe(t));
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Démarrage
   ═══════════════════════════════════════════════════════════════════════════ */
buildAxes();
buildStrata();
buildExercices();
buildMods();
buildSituations();
buildRefs();
initChrome();

readHash();
render();

$('reset').addEventListener('click', () => {
  S.mix = {R:2, H:2, E:2, S:2, O:2};
  S.exo = null;
  render();
  toast('Console remise au cran central.');
});
$('share').addEventListener('click', share);
addEventListener('hashchange', () => { if (readHash()) render(); });
