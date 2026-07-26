#!/usr/bin/env python3
"""Assemble site/index.html — un seul fichier, aucune dépendance réseau.

Les polices, le logo et les motifs sont embarqués ; seules les photographies
restent des fichiers séparés (mises en cache par le navigateur, chargées en
différé). Lancer : python3 build.py
"""
import math
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "site"

BRICK = "#8E1710"


def read(name):
    return (HERE / name).read_text(encoding="utf-8")


# ── logo vectorisé depuis la plaquette, recolorable via currentColor ────────
LOGO_SRC = read("logo.svg")
LOGO_PATHS = re.search(r"<g.*</g>", LOGO_SRC, re.S).group(0)


def logo(cls="logo", extra=""):
    return (
        f'<svg class="{cls}" viewBox="0 0 1268 1232" fill="currentColor" '
        f'role="img" aria-label="Logo RHESO"{extra}>{LOGO_PATHS}</svg>'
    )


def logo_deco(cls="logo"):
    return (
        f'<svg class="{cls}" viewBox="0 0 1268 1232" fill="currentColor" '
        f'aria-hidden="true">{LOGO_PATHS}</svg>'
    )


# ── motifs de la charte : rayons et marches. Tracés à la main, jamais animés ─
def rays():
    """Éventail de rayons du coin inférieur gauche — motif de la plaquette.

    Longueurs et épaisseurs volontairement irrégulières : c'est un tracé, pas
    une figure géométrique. Le rayon part d'un centre situé hors du cadre.
    """
    inner = [26, 31, 27, 34, 29, 36, 30, 33, 28, 35, 31, 37, 29, 34, 30, 32, 27]
    outer = [96, 118, 104, 132, 112, 141, 120, 128, 108, 136, 122, 145, 114, 130, 118, 124, 102]
    widths = [4.5, 6, 3.5, 6.5, 4, 7, 4.5, 5.5, 3.5, 6, 4, 6.5, 3.5, 5, 4, 5.5, 3]
    parts = []
    for i, (r0, r1, w) in enumerate(zip(inner, outer, widths)):
        a = math.radians(-94 + i * 5.9)
        x0, y0 = 6 + r0 * math.cos(a), 148 + r0 * math.sin(a)
        x1, y1 = 6 + r1 * math.cos(a), 148 + r1 * math.sin(a)
        parts.append(
            f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" '
            f'stroke-width="{w}"/>'
        )
    return (
        '<svg class="rays hero-rays" viewBox="0 0 150 160" fill="none" '
        'stroke="currentColor" stroke-linecap="round" aria-hidden="true">'
        + "".join(parts)
        + "</svg>"
    )


def steps():
    """Escalier rouge du coin inférieur droit (motif de la plaquette)."""
    n, w, h = 6, 100, 100
    d = "M100 100"
    for i in range(n):
        x = w - (i + 1) * (w / n)
        y = h - (i + 1) * (h / n)
        d += f"H{x:.1f}V{y:.1f}"
    d += "H100Z"
    return (
        '<svg class="steps" viewBox="0 0 100 100" preserveAspectRatio="none" '
        f'aria-hidden="true"><path d="{d}" fill="#E73535"/></svg>'
    )


# ── assemblage ─────────────────────────────────────────────────────────────
fonts = "\n".join(
    read(f) for f in ("face-montserrat.css", "face-montserrat-italic.css", "face-jetbrains.css")
)
css = "\n".join(
    read(f) for f in ("01-tokens.css", "02-base.css", "03-layout.css", "04-console.css")
)
head = read("00-head.html").replace("{{FONTS}}", fonts).replace("{{CSS}}", css)

body = (
    read("05-body.html")
    .replace("{{LOGO_BIG}}", logo_deco("logo"))
    .replace("{{RAYS_HERO}}", rays())
    .replace("{{STEPS}}", steps())
)
# les logos restants sont décoratifs sauf celui de l'en-tête (déjà étiqueté
# par l'aria-label du lien) : on les rend transparents aux lecteurs d'écran
body = body.replace("{{LOGO}}", logo_deco("logo"))

script = read("06-data.js") + "\n" + read("07-app.js")

page = head + body + "\n<script>\n" + script + "\n</script>\n</body>\n</html>\n"

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "index.html").write_text(page, encoding="utf-8")

# favicon : le logo de la plaquette, en rouge brique sur fond crème
(OUT / "favicon.svg").write_text(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-84 -72 1436 1376">'
    '<rect x="-84" y="-72" width="1436" height="1376" rx="250" fill="#FBF5DF"/>'
    f'<g fill="{BRICK}">{LOGO_PATHS}</g></svg>',
    encoding="utf-8",
)

print(f"site/index.html — {len(page.encode('utf-8')) / 1024:.0f} Kio")
