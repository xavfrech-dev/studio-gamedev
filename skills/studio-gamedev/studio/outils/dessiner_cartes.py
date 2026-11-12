# -*- coding: utf-8 -*-
"""Dessine les illustrations des cartes du questionnaire : studio/cartes/<nom>.svg.

Style « carnet » : papier crème, trait d'encre, lavis gris, hachures, une
seule couleur d'accent (rouille). Tout est tracé ici, à la main, en
coordonnées : aucune image générée, aucune police (les chiffres sont des
tracés), aucun logo de marque.

    python -I -B studio/outils/dessiner_cartes.py            # écrit tous les SVG
    python -I -B studio/outils/dessiner_cartes.py --verifier # liste les dessins manquants

Draws every questionnaire card illustration as a hand-coded SVG.
Standard library only.
"""
import math
import os
import sys
sys.dont_write_bytecode = True   # jamais de __pycache__ dans le dossier du skill

ICI = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(ICI)
SORTIE = os.path.join(STUDIO, "cartes")

PAPIER = "#f3ead8"
ENCRE = "#2a241d"
ACCENT = "#b4532a"

STYLE = (
    ".i{fill:none;stroke:%(e)s;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}"
    ".t{fill:none;stroke:%(e)s;stroke-width:1.2;stroke-linecap:round;stroke-linejoin:round}"
    ".ic{fill:%(p)s;stroke:%(e)s;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}"
    ".iw{fill:%(e)s;fill-opacity:.16;stroke:%(e)s;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}"
    ".ia{fill:%(a)s;stroke:%(e)s;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}"
    ".a{fill:none;stroke:%(a)s;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round}"
    ".w{fill:%(e)s;fill-opacity:.12;stroke:none}"
    ".f{fill:%(e)s;stroke:none}"
    ".af{fill:%(a)s;stroke:none}"
    ".d{fill:none;stroke:%(e)s;stroke-width:1.4;stroke-dasharray:3 4;stroke-linecap:round}"
) % {"e": ENCRE, "p": PAPIER, "a": ACCENT}

DESSINS = {}
_NOM = [""]


def dessin(*noms):
    def deco(fn):
        for n in noms:
            DESSINS[n] = fn
        return fn
    return deco


def n(v):
    v = round(v, 1)
    return str(int(v)) if v == int(v) else str(v)


# ------------------------------------------------------------ primitives
def L(x1, y1, x2, y2, c="i"):
    return '<line x1="%s" y1="%s" x2="%s" y2="%s" class="%s"/>' % (n(x1), n(y1), n(x2), n(y2), c)


def P(d, c="i"):
    return '<path d="%s" class="%s"/>' % (d, c)


def C(x, y, r, c="i"):
    return '<circle cx="%s" cy="%s" r="%s" class="%s"/>' % (n(x), n(y), n(r), c)


def E(x, y, rx, ry, c="i"):
    return '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" class="%s"/>' % (n(x), n(y), n(rx), n(ry), c)


def R(x, y, w, h, c="i", r=0):
    s = '<rect x="%s" y="%s" width="%s" height="%s" class="%s"' % (n(x), n(y), n(w), n(h), c)
    return s + (' rx="%s"/>' % n(r) if r else "/>")


def pts(p):
    return " ".join("%s,%s" % (n(x), n(y)) for x, y in p)


def PL(p, c="i"):
    return '<polyline points="%s" class="%s"/>' % (pts(p), c)


def PG(p, c="i"):
    return '<polygon points="%s" class="%s"/>' % (pts(p), c)


def H(el):
    """Hachures : remplace la classe d'un élément par le motif hachuré."""
    return el.replace('class="w"', 'fill="url(#h-%s)"' % _NOM[0]).replace(
        'class="h"', 'fill="url(#h-%s)"' % _NOM[0])


def hach(x, y, w, h, r=0):
    return H(R(x, y, w, h, "h", r))


def hachP(d):
    return H(P(d, "h"))


def hachC(x, y, r):
    return H(C(x, y, r, "h"))


def G(items, tr):
    return '<g transform="%s">%s</g>' % (tr, "".join(items))


def sol(x, y, rx):
    return E(x, y, rx, max(2.5, rx * 0.16), "w")


# ------------------------------------------------------------ chiffres tracés (pas de police)
CHIFFRES = {
    "0": "M3,0 C-0.6,0 -0.6,10 3,10 C6.6,10 6.6,0 3,0",
    "1": "M1.2,2.2 L3.6,0 L3.6,10",
    "2": "M0.5,2.6 C1,-0.6 6.2,-0.4 5.6,3 C5.1,5.6 0.6,7.8 0.4,10 L6,10",
    "3": "M0.6,0.6 L5.6,0.6 L2.6,4.4 C6.8,4.2 6.8,10 3,10 C1.6,10 0.6,9.4 0.2,8.6",
    "4": "M4.6,10 L4.6,0 L0,7 L6.2,7",
    "5": "M5.6,0 L1.2,0 L0.6,4.6 C4,3.2 6.4,5.2 5.9,7.6 C5.3,10.4 1.5,10.5 0.3,8.8",
    "6": "M5,0.4 C1,0 0,5 0.3,7 C0.6,10.4 5.8,10.5 5.8,7 C5.8,4 1.6,4 0.4,6.6",
    "7": "M0,0.4 L6,0.4 L2.2,10",
    "8": "M3,4.7 C0,4.5 0.4,0 3,0 C5.6,0 6,4.5 3,4.7 C-0.6,5 0,10 3,10 C6,10 6.6,5 3,4.7",
    "9": "M1,9.6 C5,10 6,5 5.7,3 C5.4,-0.4 0.3,-0.5 0.3,3 C0.3,6 4.6,6 5.6,3.4",
    "+": "M0,5 L5.4,5 M2.7,2.3 L2.7,7.7",
}


def texte(s, x, y, h, c="i"):
    """Chiffres tracés à la main, hauteur h, coin haut-gauche (x, y)."""
    k = h / 10.0
    out = []
    for ch in s:
        d = CHIFFRES.get(ch)
        if d:
            out.append('<path d="%s" class="%s" vector-effect="non-scaling-stroke" transform="translate(%s %s) scale(%s)"/>'
                       % (d, c, n(x), n(y), n(k)))
        x += (7.6 if ch != "1" else 6.0) * k
    return "".join(out)


def largeur_texte(s, h):
    k = h / 10.0
    return sum((7.6 if ch != "1" else 6.0) * k for ch in s) - 1.6 * k


# ------------------------------------------------------------ éléments récurrents
def etoile(x, y, r, c="ia", pointes=5, creux=0.45, rot=-90):
    p = []
    for i in range(pointes * 2):
        rr = r if i % 2 == 0 else r * creux
        a = math.radians(rot + i * 180.0 / pointes)
        p.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    return PG(p, c)


def coeur(x, y, s, c="ia"):
    return P("M%s,%s C%s,%s %s,%s %s,%s C%s,%s %s,%s %s,%s Z" % (
        n(x), n(y + 9 * s), n(x - 16 * s), n(y - 2 * s), n(x - 8 * s), n(y - 13 * s), n(x), n(y - 5 * s),
        n(x + 8 * s), n(y - 13 * s), n(x + 16 * s), n(y - 2 * s), n(x), n(y + 9 * s)), c)


def engrenage(x, y, r, dents=8, c="iw", trou="ic"):
    p = []
    for i in range(dents * 4):
        a = math.radians(i * 90.0 / dents)
        rr = r if (i % 4) in (1, 2) else r * 0.78
        p.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    return PG(p, c) + C(x, y, r * 0.3, trou)


def horloge(x, y, r, minutes=None, c="ic"):
    out = [C(x, y, r, c)]
    if minutes:
        f = min(minutes, 60) / 60.0
        if f >= 1:
            out.append(C(x, y, r * 0.82, "af"))
        else:
            a = math.radians(-90 + 360 * f)
            gx, gy = x + r * 0.82 * math.cos(a), y + r * 0.82 * math.sin(a)
            out.append(P("M%s,%s L%s,%s A%s,%s 0 %d 1 %s,%s Z" % (
                n(x), n(y), n(x), n(y - r * 0.82), n(r * 0.82), n(r * 0.82), 1 if f > 0.5 else 0, n(gx), n(gy)), "af"))
    for i in range(12):
        a = math.radians(i * 30)
        k = 0.86 if i % 3 else 0.78
        out.append(L(x + r * k * math.cos(a), y + r * k * math.sin(a), x + r * 0.95 * math.cos(a), y + r * 0.95 * math.sin(a), "t"))
    out.append(L(x, y, x, y - r * 0.6))
    out.append(L(x, y, x + r * 0.42, y + r * 0.1))
    out.append(C(x, y, 2, "f"))
    return "".join(out)


def personne(x, base, s=1.0, c="ic", tete="ic"):
    return (P("M%s,%s Q%s,%s %s,%s Q%s,%s %s,%s Z" % (
        n(x - 11 * s), n(base), n(x - 11 * s), n(base - 24 * s), n(x), n(base - 24 * s),
        n(x + 11 * s), n(base - 24 * s), n(x + 11 * s), n(base)), c)
        + C(x, base - 32 * s, 7 * s, tete))


def tete(x, y, s=1.0, c="ic"):
    return C(x, y, 5 * s, c) + P("M%s,%s Q%s,%s %s,%s" % (n(x - 8 * s), n(y + 15 * s), n(x), n(y + 4 * s), n(x + 8 * s), n(y + 15 * s)), "i")


def sapin(x, base, h, c="iw"):
    w = h * 0.36
    return (L(x, base, x, base - h * 0.2) +
            PG([(x, base - h), (x + w * 0.7, base - h * 0.55), (x + w * 0.35, base - h * 0.55), (x + w, base - h * 0.18),
                (x - w, base - h * 0.18), (x - w * 0.35, base - h * 0.55), (x - w * 0.7, base - h * 0.55)], c))


def arbre_rond(x, base, h, c="iw"):
    return L(x, base, x, base - h * 0.45) + C(x, base - h * 0.62, h * 0.34, c)


def montagne(x, base, w, h, c="iw", neige=False):
    out = PG([(x - w / 2, base), (x, base - h), (x + w / 2, base)], c)
    if neige:
        out += PG([(x - w * 0.15, base - h * 0.7), (x, base - h), (x + w * 0.15, base - h * 0.7), (x + w * 0.05, base - h * 0.64), (x - w * 0.04, base - h * 0.72)], "ic")
    return out


def soleil(x, y, r, c="ia", rayons=10):
    out = [C(x, y, r, c)]
    for i in range(rayons):
        a = math.radians(i * 360.0 / rayons)
        out.append(L(x + (r + 4) * math.cos(a), y + (r + 4) * math.sin(a), x + (r + 10) * math.cos(a), y + (r + 10) * math.sin(a)))
    return "".join(out)


def nuage(x, y, s=1.0, c="ic"):
    return P("M%s,%s Q%s,%s %s,%s Q%s,%s %s,%s Q%s,%s %s,%s Q%s,%s %s,%s Z" % (
        n(x - 22 * s), n(y + 8 * s), n(x - 26 * s), n(y - 6 * s), n(x - 10 * s), n(y - 6 * s),
        n(x - 6 * s), n(y - 20 * s), n(x + 8 * s), n(y - 12 * s),
        n(x + 26 * s), n(y - 16 * s), n(x + 24 * s), n(y + 2 * s),
        n(x + 30 * s), n(y + 10 * s), n(x + 18 * s), n(y + 8 * s)), c)


def lune(x, y, r, c="ia"):
    return P("M%s,%s A%s,%s 0 1 0 %s,%s A%s,%s 0 0 1 %s,%s Z" % (
        n(x), n(y - r), n(r), n(r), n(x), n(y + r), n(r * 1.25), n(r * 1.25), n(x), n(y - r)), c)


def bulle(x, y, w, h, c="ic", queue="g"):
    qx = x + w * 0.25 if queue == "g" else x + w * 0.75
    d = qx - 10 if queue == "g" else qx + 10
    return P("M%s,%s h%s a8,8 0 0 1 8,8 v%s a8,8 0 0 1 -8,8 H%s L%s,%s L%s,%s H%s a8,8 0 0 1 -8,-8 v%s a8,8 0 0 1 8,-8 Z" % (
        n(x + 8), n(y), n(w - 16), n(h - 16), n(qx + 6), n(d), n(y + h + 10), n(qx - 6), n(y + h), n(x + 8), n(-(h - 16))), c)


def ecran(x, y, w, h, c="ic", pied=True):
    out = R(x, y, w, h, c, 4) + R(x + 5, y + 5, w - 10, h - 10, "t", 2)
    if pied:
        out += L(x + w / 2, y + h, x + w / 2, y + h + 8) + L(x + w / 2 - 12, y + h + 8, x + w / 2 + 12, y + h + 8)
    return out


def cube_iso(x, y, s, haut="ic", gauche="iw", droite="ic"):
    k = 0.87 * s
    return (PG([(x - k, y), (x, y + s / 2), (x, y + s * 1.5), (x - k, y + s)], gauche) +
            PG([(x + k, y), (x, y + s / 2), (x, y + s * 1.5), (x + k, y + s)], droite) +
            PG([(x, y - s / 2), (x + k, y), (x, y + s / 2), (x - k, y)], haut))


def manette(x, y, s=1.0, c="ic"):
    return (P("M%s,%s C%s,%s %s,%s %s,%s L%s,%s C%s,%s %s,%s %s,%s C%s,%s %s,%s %s,%s L%s,%s C%s,%s %s,%s %s,%s Z" % (
        n(x - 22 * s), n(y - 10 * s),
        n(x - 34 * s), n(y - 10 * s), n(x - 38 * s), n(y + 22 * s), n(x - 26 * s), n(y + 22 * s),
        n(x - 14 * s), n(y + 10 * s),
        n(x - 6 * s), n(y + 8 * s), n(x + 6 * s), n(y + 8 * s), n(x + 14 * s), n(y + 10 * s),
        n(x + 26 * s), n(y + 22 * s), n(x + 38 * s), n(y + 22 * s), n(x + 34 * s), n(y - 10 * s),
        n(x + 22 * s), n(y - 10 * s),
        n(x + 8 * s), n(y - 13 * s), n(x - 8 * s), n(y - 13 * s), n(x - 22 * s), n(y - 10 * s)), c) +
        L(x - 26 * s, y, x - 16 * s, y) + L(x - 21 * s, y - 5 * s, x - 21 * s, y + 5 * s) +
        C(x + 18 * s, y - 3 * s, 2.6 * s, "af") + C(x + 24 * s, y + 3 * s, 2.6 * s, "f"))


def camera(x, y, s=1.0, c="ic"):
    return (R(x - 14 * s, y - 9 * s, 28 * s, 18 * s, c, 3) + PG([(x + 14 * s, y - 4 * s), (x + 24 * s, y - 9 * s), (x + 24 * s, y + 9 * s), (x + 14 * s, y + 4 * s)], "iw") +
            C(x - 4 * s, y - 15 * s, 5 * s, "ic") + C(x + 7 * s, y - 15 * s, 5 * s, "ic") + C(x - 7 * s, y, 2.4 * s, "af"))


def dossier(x, y, w, h, c="ic"):
    return P("M%s,%s v%s h%s v%s h%s l-6,-7 h%s Z" % (n(x), n(y), n(h), n(w), n(-(h - 8)), n(-(w - 34)), n(-22)), c) + L(x, y + 12, x + w, y + 12, "t")


def crayon(x1, y1, x2, y2, c="ic"):
    a = math.atan2(y2 - y1, x2 - x1)
    px, py = -math.sin(a) * 5, math.cos(a) * 5
    tx, ty = x2 + math.cos(a) * 12, y2 + math.sin(a) * 12
    return (PG([(x1 + px, y1 + py), (x2 + px, y2 + py), (x2 - px, y2 - py), (x1 - px, y1 - py)], c) +
            PG([(x2 + px, y2 + py), (tx, ty), (x2 - px, y2 - py)], "ic") +
            PG([(x2 + px * 0.35 + (tx - x2) * 0.65, y2 + py * 0.35 + (ty - y2) * 0.65), (tx, ty), (x2 - px * 0.35 + (tx - x2) * 0.65, y2 - py * 0.35 + (ty - y2) * 0.65)], "f") +
            PG([(x1 + px, y1 + py), (x1 - px, y1 - py), (x1 - px - math.cos(a) * 6, y1 - py - math.sin(a) * 6), (x1 + px - math.cos(a) * 6, y1 + py - math.sin(a) * 6)], "ia"))


def livre_ouvert(x, y, w, h, c="ic"):
    return (P("M%s,%s Q%s,%s %s,%s L%s,%s Q%s,%s %s,%s Z" % (n(x), n(y), n(x - w * 0.5), n(y - 10), n(x - w), n(y - 4), n(x - w), n(y + h), n(x - w * 0.5), n(y + h - 6), n(x), n(y + h + 4)), c) +
            P("M%s,%s Q%s,%s %s,%s L%s,%s Q%s,%s %s,%s Z" % (n(x), n(y), n(x + w * 0.5), n(y - 10), n(x + w), n(y - 4), n(x + w), n(y + h), n(x + w * 0.5), n(y + h - 6), n(x), n(y + h + 4)), c))


def moteur(x, y):
    """Machine neutre (aucun logo) : bloc, piston, volant d'inertie."""
    return (sol(80, 100, 52) + R(x - 34, y - 14, 58, 44, "ic", 4) + R(x - 28, y - 26, 16, 12, "iw") +
            R(x - 6, y - 26, 16, 12, "iw") + L(x - 34, y + 30, x + 24, y + 30) +
            engrenage(x + 34, y + 12, 15, 9, "iw") + L(x - 28, y - 2, x + 16, y - 2, "t") + L(x - 28, y + 6, x + 16, y + 6, "t"))


def personnage_face(x, y, r=26):
    return C(x, y, r, "ic")


def joueurs(liste, s=1.0):
    return "".join(personne(px, py, s, "ia" if i == 0 else "ic") for i, (px, py) in enumerate(liste))


# ============================================================ dessins
# --- accueil
@dessin("eclair")
def _():
    return [sol(80, 104, 30), PG([(92, 14), (58, 64), (78, 64), (68, 104), (106, 50), (86, 50), (100, 14)], "ia"),
            L(36, 44, 54, 44, "t"), L(30, 56, 50, 56, "t"), L(36, 68, 52, 68, "t")]


@dessin("carnet")
def _():
    return [sol(80, 104, 46), livre_ouvert(80, 34, 44, 60),
            L(46, 44, 72, 47, "t"), L(46, 52, 72, 55, "t"), L(46, 60, 66, 63, "t"), L(46, 68, 72, 71, "t"),
            L(88, 47, 114, 44, "t"), L(88, 55, 114, 52, "t"), L(88, 63, 108, 60, "t"),
            P("M98,30 L98,62 L102,57 L106,62 L106,30", "ia")]


@dessin("marque_page")
def _():
    return [sol(80, 102, 40), R(50, 22, 60, 76, "ic", 4), R(50, 22, 10, 76, "iw", 3),
            L(68, 38, 100, 38, "t"), L(68, 46, 94, 46, "t"),
            P("M86,14 L86,108 L92,100 L98,108 L98,14 Z", "ia")]


@dessin("pousse")
def _():
    return [P("M40,98 Q80,84 120,98 Z", "iw"), P("M80,94 Q78,70 82,48", "i"),
            P("M81,64 Q62,62 56,46 Q74,44 81,64 Z", "iw"), P("M82,54 Q96,38 112,40 Q106,58 82,54 Z", "ia")]


@dessin("graine")
def _():
    return [P("M34,96 Q80,80 126,96 Z", "iw"), E(80, 78, 22, 14, "ia"), P("M64,76 Q80,66 96,76", "t"),
            P("M82,62 Q90,46 80,30", "d"), etoile(104, 40, 6, "ic", 4, 0.3)]


@dessin("boites")
def _():
    return [sol(80, 102, 44), R(46, 74, 70, 24, "ic", 2), R(52, 52, 60, 22, "iw", 2), R(58, 30, 48, 22, "ia", 2),
            L(54, 86, 108, 86, "t"), L(60, 63, 104, 63, "t"), etoile(82, 41, 6, "ic")]


@dessin("medaille")
def _():
    return [PG([(62, 14), (76, 14), (88, 50), (74, 50)], "ia"), PG([(98, 14), (84, 14), (72, 50), (86, 50)], "iw"),
            C(80, 72, 24, "ic"), C(80, 72, 18, "t"), etoile(80, 72, 11, "ia")]


@dessin("drapeau")
def _():
    return [sol(64, 104, 20), L(62, 104, 62, 18), C(62, 16, 3, "f"),
            P("M62,22 Q78,14 94,22 Q108,30 122,22 L122,54 Q108,62 94,54 Q78,46 62,54 Z", "ia")]


@dessin("miroir")
def _():
    return [sol(80, 106, 30), L(80, 92, 80, 104), L(66, 104, 94, 104), E(80, 54, 28, 38, "ic"), E(80, 54, 22, 32, "w"),
            personne(80, 82, 0.9, "iw", "ic"), P("M62,32 Q70,22 80,20", "a")]


# --- vision
@dessin("bougie")
def _():
    return [hachC(80, 58, 44), C(80, 40, 22, "ic"), sol(80, 100, 26), R(68, 52, 24, 46, "ic", 2),
            P("M70,52 Q74,58 78,52", "t"), L(80, 52, 80, 44), P("M80,22 Q90,34 84,42 Q80,46 76,42 Q70,34 80,22 Z", "ia")]


@dessin("cible")
def _():
    return [C(76, 62, 36, "ic"), C(76, 62, 26, "iw"), C(76, 62, 16, "ic"), C(76, 62, 7, "ia"),
            L(76, 62, 126, 20), PL([(118, 16), (126, 20), (122, 28)]), L(112, 30, 120, 22, "t")]


@dessin("tasse")
def _():
    return [E(80, 96, 40, 7, "iw"), P("M50,58 L56,92 Q80,98 104,92 L110,58 Z", "ic"), E(80, 58, 30, 6, "iw"),
            P("M108,64 Q126,64 122,78 Q118,86 104,84", "i"),
            P("M70,46 Q64,38 70,30 Q76,22 70,14", "a"), P("M86,46 Q80,38 86,30 Q92,22 86,14", "t")]


@dessin("boussole")
def _():
    return [sol(80, 104, 30), C(80, 60, 36, "ic"), C(80, 60, 29, "t"),
            PG([(80, 30), (88, 60), (72, 60)], "ia"), PG([(80, 90), (88, 60), (72, 60)], "iw"), C(80, 60, 3, "f"),
            L(80, 22, 80, 27), L(80, 93, 80, 98), L(42, 60, 47, 60), L(113, 60, 118, 60)]


@dessin("foudre")
def _():
    return [nuage(80, 34, 1.3, "iw"), PG([(84, 44), (66, 74), (80, 74), (70, 102), (98, 66), (84, 66), (94, 44)], "ia"),
            L(58, 98, 50, 104), L(84, 106, 92, 110, "t"), L(60, 106, 54, 112, "t"), L(94, 100, 104, 104)]


@dessin("rire")
def _():
    return [sol(80, 104, 30), C(80, 58, 36, "ic"), P("M60,48 Q66,40 72,48", "i"), P("M88,48 Q94,40 100,48", "i"),
            P("M60,64 Q80,96 100,64 Z", "ia"), P("M66,66 L94,66", "t"), L(44, 30, 38, 24, "t"), L(116, 30, 122, 24, "t")]


@dessin("coeur")
def _():
    return [sol(80, 104, 30), coeur(78, 60, 2.6, "ia"), coeur(114, 34, 0.9, "ic"), coeur(46, 30, 0.6, "iw")]


@dessin("pieces")
def _():
    out = [sol(76, 102, 44)]
    for i in range(5):
        out.append(E(66, 92 - i * 8, 24, 7, "ic"))
    out += [E(108, 72, 14, 22, "ia"), E(108, 72, 9, 16, "t")]
    return out


@dessin("chrono")
def _():
    return [sol(80, 106, 28), R(74, 16, 12, 8, "iw", 2), L(80, 24, 80, 30), L(104, 32, 110, 26),
            horloge(80, 64, 34, 20)]


@dessin("public")
def _():
    return [sol(80, 104, 50), personne(50, 100, 0.85, "iw"), personne(110, 100, 0.85, "iw"), personne(80, 100, 1.1, "ia")]


# --- genres
@dessin("epee")
def _():
    return [sol(80, 106, 30), PG([(108, 16), (116, 20), (76, 72), (68, 66)], "ic"), L(112, 18, 74, 68, "t"),
            PG([(58, 58), (64, 54), (88, 78), (82, 82)], "ia"), PG([(70, 72), (76, 78), (60, 94), (54, 88)], "iw"), C(54, 96, 5, "ic")]


@dessin("feu_camp")
def _():
    return [sol(80, 100, 44), PG([(44, 96), (48, 88), (112, 98), (108, 104)], "iw"), PG([(116, 96), (112, 88), (48, 98), (52, 104)], "iw"),
            P("M80,24 Q102,48 96,74 Q92,90 80,90 Q66,90 64,74 Q62,58 72,48 Q72,62 80,64 Q76,44 80,24 Z", "ia"),
            P("M80,58 Q90,70 86,82 Q80,88 74,82 Q72,72 80,58 Z", "ic"),
            E(38, 100, 7, 5, "ic"), E(122, 100, 7, 5, "ic")]


@dessin("bouclier")
def _():
    return [sol(80, 106, 30), P("M80,16 Q100,24 116,22 Q118,74 80,102 Q42,74 44,22 Q60,24 80,16 Z", "ic"),
            P("M80,24 Q96,30 108,30 Q108,72 80,92 Z", "iw"), PL([(56, 50), (80, 66), (104, 50)], "a"), PL([(58, 62), (80, 78), (102, 62)], "a")]


@dessin("plateforme")
def _():
    return [R(28, 84, 34, 10, "iw", 2), R(70, 60, 30, 10, "iw", 2), R(110, 38, 28, 10, "iw", 2),
            P("M46,80 Q62,36 84,56", "d"), personne(46, 84, 0.55, "ia"), C(124, 28, 5, "ic"), C(124, 28, 2, "af")]


@dessin("donjon")
def _():
    return [hach(36, 20, 88, 84), P("M50,104 V54 Q50,26 80,26 Q110,26 110,54 V104 Z", "ic"),
            P("M60,104 V58 Q60,38 80,38 Q100,38 100,58 V104 Z", "iw"),
            cube_iso(80, 80, 12, "ic", "iw", "ia"), C(80, 80, 1.6, "f")]


@dessin("viseur")
def _():
    return [C(80, 60, 34, "ic"), C(80, 60, 14, "a"), L(80, 18, 80, 44), L(80, 76, 80, 102), L(38, 60, 64, 60), L(96, 60, 122, 60),
            C(80, 60, 3, "af")]


@dessin("echecs")
def _():
    return [sol(80, 102, 46), P("M42,98 L46,86 L50,62 L44,62 L44,46 L52,46 L52,52 L58,52 L58,46 L66,46 L66,52 L72,52 L72,46 L80,46 L80,62 L74,62 L78,86 L82,98 Z", "iw"),
            P("M96,98 Q96,84 104,80 Q96,74 100,64 Q104,58 110,58 Q116,58 120,64 Q124,74 116,80 Q124,84 124,98 Z", "ia"), C(110, 50, 8, "ia")]


@dessin("tour")
def _():
    return [sol(60, 104, 30), P("M42,104 L46,44 L40,44 L40,30 L48,30 L48,36 L56,36 L56,30 L64,30 L64,36 L72,36 L72,30 L80,30 L80,44 L74,44 L78,104 Z", "ic"),
            hach(52, 58, 14, 18), L(84, 40, 118, 54, "a"), PL([(112, 48), (118, 54), (110, 57)], "a"),
            C(122, 96, 5, "iw"), C(110, 98, 4, "iw"), C(132, 92, 4, "iw")]


@dessin("ville")
def _():
    return [sol(80, 102, 52), R(32, 60, 26, 40, "iw"), PG([(30, 60), (45, 46), (60, 60)], "ic"),
            R(62, 40, 34, 60, "ic"), R(68, 48, 8, 8, "t"), R(82, 48, 8, 8, "t"), R(68, 62, 8, 8, "t"), R(82, 62, 8, 8, "ia"),
            R(100, 68, 28, 32, "iw"), PG([(98, 68), (114, 54), (130, 68)], "ia"), R(74, 82, 10, 18, "ic")]


@dessin("avion")
def _():
    return [nuage(48, 92, 0.8, "iw"), P("M30,60 Q60,54 118,56 Q132,58 132,62 Q132,66 118,66 L40,66 Z", "ic"),
            PG([(70, 60), (94, 30), (102, 30), (88, 60)], "iw"), PG([(72, 66), (94, 88), (100, 88), (88, 66)], "iw"),
            PG([(34, 60), (28, 40), (38, 40), (46, 58)], "ia"), L(102, 60, 116, 60, "t")]


@dessin("course")
def _():
    out = [sol(56, 104, 20), L(54, 104, 54, 18), C(54, 16, 3, "f"), R(54, 22, 66, 40, "ic")]
    for r in range(4):
        for c in range(6):
            if (r + c) % 2 == 0:
                out.append(R(54 + c * 11, 22 + r * 10, 11, 10, "f"))
    out += [L(126, 74, 140, 74, "a"), L(120, 84, 140, 84, "a"), L(128, 94, 140, 94, "a")]
    return out


@dessin("ballon")
def _():
    return [E(88, 102, 26, 4, "w"), C(86, 60, 34, "ic"), PG([(86, 46), (98, 55), (94, 69), (78, 69), (74, 55)], "ia"),
            L(86, 46, 86, 28), L(98, 55, 116, 50), L(94, 69, 104, 86), L(78, 69, 68, 86), L(74, 55, 56, 50),
            L(30, 50, 44, 50, "t"), L(26, 62, 44, 62, "t"), L(32, 74, 46, 74, "t")]


@dessin("cartes")
def _():
    return [sol(80, 106, 40), G([R(-18, -28, 36, 52, "iw", 4)], "translate(56 64) rotate(-18)"),
            G([R(-18, -28, 36, 52, "ic", 4), etoile(0, -2, 8, "iw")], "translate(104 64) rotate(18)"),
            G([R(-18, -28, 36, 52, "ic", 4), coeur(0, -2, 0.9, "ia")], "translate(80 58)")]


@dessin("puzzle")
def _():
    piece = "M0,0 h12 a6,6 0 1 1 12,0 h12 v12 a6,6 0 1 0 0,12 v12 h-12 a6,6 0 1 1 -12,0 h-12 v-12 a6,6 0 1 0 0,-12 Z"
    return [sol(80, 102, 44), G([P(piece, "ic")], "translate(40 38)"), G([P(piece, "ia")], "translate(86 52) rotate(12)")]


@dessin("bulle")
def _():
    return [bulle(30, 22, 76, 50, "ic"), L(42, 38, 92, 38, "t"), L(42, 48, 84, 48, "t"), L(42, 58, 70, 58, "t"),
            bulle(92, 62, 42, 28, "ia", "d"), C(104, 76, 2, "f"), C(113, 76, 2, "f"), C(122, 76, 2, "f")]


@dessin("horreur")
def _():
    return [lune(114, 32, 14, "ia"), P("M20,104 Q80,78 140,104 Z", "iw"),
            P("M52,90 L52,58 L68,40 L84,58 L84,90 Z", "ic"), R(62, 70, 10, 20, "f"), R(56, 60, 6, 6, "af"),
            P("M106,94 L106,64 M106,74 L96,62 M106,70 L118,58 M106,82 L114,76", "i")]


@dessin("note")
def _():
    return [sol(80, 104, 40), E(56, 88, 10, 7, "f"), E(96, 78, 10, 7, "f"), L(65, 87, 65, 34), L(105, 77, 105, 24),
            PG([(65, 34), (105, 24), (105, 34), (65, 44)], "f"), E(122, 52, 7, 5, "af"), L(128, 51, 128, 24, "a"), P("M128,24 Q136,30 134,40", "a")]


@dessin("cubes")
def _():
    return [sol(80, 104, 44), cube_iso(62, 72, 18, "ic", "iw", "ic"), cube_iso(96, 72, 18, "ic", "iw", "ia"), cube_iso(79, 44, 18, "ia", "iw", "ic")]


@dessin("vide")
def _():
    return [C(80, 60, 32, "d"), L(60, 82, 100, 38, "a")]


# --- session
@dessin("sablier")
def _():
    return [sol(80, 106, 30), R(52, 16, 56, 8, "iw", 2), R(52, 96, 56, 8, "iw", 2),
            P("M58,24 Q58,50 80,60 Q102,50 102,24 Z", "ic"), P("M58,96 Q58,70 80,60 Q102,70 102,96 Z", "ic"),
            P("M66,34 Q80,40 94,34 Q92,48 80,54 Q68,48 66,34 Z", "ia"), P("M62,96 Q80,80 98,96 Z", "ia"), L(80, 60, 80, 86, "d")]


@dessin("horloge")
def _():
    return [sol(80, 104, 30), horloge(80, 58, 38, 45)]


@dessin("nuit")
def _():
    return [lune(76, 58, 30, "ia"), etoile(118, 30, 6, "ic"), etoile(122, 82, 4, "ic"), etoile(40, 28, 4, "ic"), etoile(46, 92, 3, "f")]


# --- public
@dessin("manette")
def _():
    return [sol(80, 100, 40), manette(80, 60, 1.35)]


@dessin("famille")
def _():
    return [sol(80, 104, 50), personne(52, 100, 1.0, "iw"), personne(108, 100, 1.0, "iw"), personne(80, 100, 0.65, "ia")]


@dessin("flamme")
def _():
    return [sol(80, 104, 28), P("M80,14 Q112,46 104,78 Q98,100 80,100 Q60,100 56,80 Q52,58 66,44 Q66,62 76,66 Q70,40 80,14 Z", "ia"),
            P("M82,56 Q96,72 92,86 Q86,94 78,90 Q70,84 74,72 Q78,68 82,56 Z", "ic")]


@dessin("potes")
def _():
    return [sol(80, 104, 46), personne(62, 100, 1.0, "iw"), personne(98, 100, 1.0, "ia"), P("M70,84 Q80,78 90,84", "i")]


# --- âge
def badge_age(s):
    out = [sol(80, 104, 30), R(46, 22, 68, 76, "ic", 12), R(52, 28, 56, 64, "t", 8)]
    h = 26
    w = largeur_texte(s, h)
    out.append(texte(s, 80 - w / 2, 46, h))
    if s != "+":
        out.append(L(56, 82, 104, 82, "a"))
    return out


@dessin("age_12")
def _():
    return badge_age("12+")


@dessin("age_16")
def _():
    return badge_age("16+")


@dessin("age_18")
def _():
    return badge_age("18+")


@dessin("age_tous")
def _():
    return [sol(80, 104, 30), R(46, 22, 68, 76, "ic", 12), R(52, 28, 56, 64, "t", 8),
            C(80, 56, 18, "ia"), C(74, 52, 2, "f"), C(86, 52, 2, "f"), P("M72,60 Q80,68 88,60", "i"), L(56, 84, 104, 84, "t")]


@dessin("sous_titres")
def _():
    return [ecran(28, 18, 104, 70), montagne(64, 70, 40, 30, "iw"), montagne(92, 70, 40, 22, "w"),
            R(44, 72, 72, 10, "f", 2), L(50, 77, 98, 77, "a")]


@dessin("touches")
def _():
    def touche(x, y, c="ic"):
        return R(x, y, 30, 26, "iw", 4) + R(x + 3, y + 2, 24, 18, c, 3)
    return [sol(80, 104, 52), touche(65, 40), touche(31, 70), touche(65, 70, "ia"), touche(99, 70),
            PL([(80, 46), (80, 56)]), PL([(76, 50), (80, 46), (84, 50)])]


@dessin("daltonisme")
def _():
    return [P("M24,60 Q80,10 136,60 Q80,110 24,60 Z", "ic"), C(70, 60, 18, "ia"), C(90, 60, 18, "iw"), hachC(80, 74, 12), C(80, 60, 6, "f")]


@dessin("curseurs")
def _():
    return [sol(80, 104, 40), L(50, 24, 50, 96), L(80, 24, 80, 96), L(110, 24, 110, 96),
            R(42, 56, 16, 10, "ic", 3), R(72, 34, 16, 10, "ia", 3), R(102, 74, 16, 10, "ic", 3)]


@dessin("langues")
def _():
    return [bulle(24, 20, 70, 44, "ic"), L(36, 36, 80, 36, "t"), L(36, 46, 70, 46, "t"),
            bulle(66, 54, 70, 40, "ia", "d"), L(78, 68, 122, 68, "i"), L(78, 78, 110, 78, "i")]


@dessin("langue_une")
def _():
    return [bulle(34, 24, 92, 56, "ic"), L(48, 42, 112, 42, "t"), L(48, 52, 100, 52, "t"), L(48, 62, 84, 62, "a")]


@dessin("globe")
def _():
    return [sol(80, 106, 30), C(80, 58, 36, "ic"), E(80, 58, 15, 36, "t"), L(44, 58, 116, 58, "t"),
            P("M48,40 Q80,48 112,40", "t"), P("M48,76 Q80,68 112,76", "t"), P("M38,40 Q80,108 128,52", "a")]


# --- 2D / 3D et caméras
@dessin("plan_2d")
def _():
    out = [R(30, 26, 100, 70, "ic", 3)]
    for i in range(1, 5):
        out.append(L(30 + i * 20, 26, 30 + i * 20, 96, "t"))
    for j in range(1, 4):
        out.append(L(30, 26 + j * 17.5, 130, 26 + j * 17.5, "t"))
    out += [R(30, 78.5, 100, 17.5, "iw"), R(70, 61, 20, 17.5, "ia")]
    return out


@dessin("cube_3d")
def _():
    return [sol(80, 102, 40), cube_iso(80, 40, 34, "ia", "iw", "ic")]


@dessin("iso_25d")
def _():
    return [P("M24,96 L60,70 L136,70 L100,96 Z", "iw"), P("M34,82 L60,62 L120,62 L94,82 Z", "ic"),
            montagne(80, 66, 50, 34, "ic"), personne(78, 82, 0.6, "ia")]


@dessin("cam_fps")
def _():
    return [R(22, 18, 116, 84, "ic", 4), L(22, 64, 138, 64, "t"), montagne(56, 64, 50, 26, "w"), sapin(108, 64, 30, "iw"),
            P("M36,102 Q48,82 62,80 L72,86 Q62,92 58,102 Z", "iw"), P("M124,102 Q112,82 98,80 L88,86 Q98,92 102,102 Z", "iw"),
            C(80, 52, 2.5, "af"), C(80, 52, 6, "a")]


@dessin("cam_tps")
def _():
    return [R(22, 18, 116, 84, "ic", 4), L(22, 60, 138, 60, "t"), sapin(112, 60, 28, "iw"), montagne(52, 60, 40, 18, "w"),
            personne(70, 102, 1.25, "ia", "iw"), L(84, 54, 124, 46, "d")]


@dessin("cam_cote")
def _():
    return [L(22, 92, 138, 92), hach(22, 92, 116, 10), R(92, 66, 34, 8, "iw", 2), personne(52, 92, 0.75, "ia"),
            PL([(70, 56), (88, 56)], "a"), PL([(82, 50), (88, 56), (82, 62)], "a")]


@dessin("cam_dessus")
def _():
    return [R(26, 18, 108, 84, "ic", 4), C(52, 40, 10, "iw"), C(108, 84, 12, "iw"), C(118, 36, 8, "iw"), R(36, 74, 22, 16, "w"),
            E(80, 60, 13, 8, "ia"), C(80, 60, 6, "ic"), PL([(80, 46), (80, 40)], "t")]


@dessin("cam_iso")
def _():
    out = []
    for i in range(3):
        for j in range(3):
            x = 80 + (i - j) * 20
            y = 44 + (i + j) * 11.5
            out.append(PG([(x, y - 11.5), (x + 20, y), (x, y + 11.5), (x - 20, y)], "ic" if (i + j) % 2 else "iw"))
    out.append(cube_iso(80, 50, 12, "ia", "iw", "ic"))
    return out


@dessin("cam_fixe")
def _():
    return [R(22, 18, 116, 84, "iw", 4), R(30, 26, 100, 68, "ic", 2), L(30, 80, 130, 80), R(44, 58, 18, 22, "t"),
            R(102, 52, 16, 28, "iw"), personne(80, 80, 0.6, "ia"), C(26, 22, 2, "f"), C(134, 22, 2, "f"), C(26, 98, 2, "f"), C(134, 98, 2, "f")]


@dessin("cam_libre")
def _():
    return [camera(78, 64, 1.2), P("M34,52 A48,40 0 0 1 120,28", "a"), PL([(112, 22), (120, 28), (112, 34)], "a"),
            P("M126,76 A48,40 0 0 1 40,100", "t"), PL([(48, 94), (40, 100), (48, 106)], "t")]


@dessin("rail")
def _():
    return [P("M20,98 Q80,64 140,82", "i"), P("M20,108 Q80,74 140,92", "i"),
            L(40, 92, 42, 102, "t"), L(60, 84, 62, 94, "t"), L(80, 80, 82, 90, "t"), L(100, 80, 102, 90, "t"), L(120, 82, 121, 92, "t"),
            L(78, 52, 78, 78), camera(76, 42, 1.0)]


@dessin("cam_mixte")
def _():
    return [P("M24,98 Q80,74 136,98", "d"), camera(80, 56, 1.1), P("M44,46 A40,34 0 0 1 112,30", "a"), PL([(105, 24), (112, 30), (104, 35)], "a")]


# --- verbes et systèmes
@dessin("marteau")
def _():
    return [sol(80, 104, 30), G([R(-6, -10, 12, 62, "iw", 3), R(-24, -24, 48, 18, "ic", 3), R(-24, -24, 10, 18, "ia", 2)], "translate(84 46) rotate(30)")]


@dessin("volant")
def _():
    return [C(80, 60, 36, "ic"), C(80, 60, 28, "t"), C(80, 64, 10, "ia"), L(52, 56, 70, 62), L(108, 56, 90, 62), L(80, 74, 80, 92)]


@dessin("coffre")
def _():
    return [sol(80, 104, 46), R(40, 58, 80, 42, "ic", 3), P("M40,58 Q40,30 80,30 Q120,30 120,58 Z", "iw"), L(40, 58, 120, 58),
            R(72, 52, 16, 18, "ia", 2), C(80, 61, 2, "f"), L(56, 34, 56, 100, "t"), L(104, 34, 104, 100, "t")]


@dessin("ombre")
def _():
    return [L(16, 104, 144, 104), hachP("M108,18 L144,104 L72,104 Z"), C(108, 18, 6, "ia"),
            P("M30,104 Q30,82 44,78 L58,74 Q66,74 66,84 L70,104 Z", "iw"), C(52, 64, 9, "iw"), P("M60,82 L74,74", "i")]


@dessin("sac")
def _():
    return [sol(80, 104, 34), P("M66,30 Q66,18 80,18 Q94,18 94,30", "i"), R(50, 30, 60, 70, "ic", 14), R(58, 58, 44, 30, "iw", 6),
            L(58, 66, 102, 66, "t"), R(74, 62, 12, 8, "ia", 2), L(50, 46, 110, 46, "t")]


@dessin("enclume")
def _():
    return [sol(80, 106, 40), P("M34,50 L112,50 Q126,50 128,42 L96,42 L36,42 Q30,46 34,50 Z", "ic"),
            P("M58,50 L104,50 L98,70 L66,70 Z", "iw"), R(54, 70, 56, 10, "iw", 2), R(48, 80, 68, 22, "ic", 2),
            G([R(-4, -24, 8, 30, "ic", 2), R(-14, -32, 28, 12, "ia", 2)], "translate(80 22) rotate(-30)")]


@dessin("disquette")
def _():
    return [sol(80, 106, 34), P("M44,20 H108 L118,30 V100 H44 Z", "ic"), R(58, 20, 40, 26, "iw"), R(84, 24, 8, 18, "ic"),
            R(54, 60, 54, 34, "ia", 2), L(60, 70, 102, 70, "t"), L(60, 80, 94, 80, "t")]


@dessin("ia")
def _():
    return [sol(80, 104, 34), L(80, 22, 80, 32), C(80, 18, 4, "ia"), R(50, 32, 60, 52, "ic", 10), R(56, 44, 48, 22, "iw", 6),
            C(70, 55, 5, "af"), C(90, 55, 5, "af"), L(68, 74, 92, 74, "i"), R(64, 84, 32, 14, "iw", 3)]


@dessin("de")
def _():
    out = [sol(80, 104, 40), cube_iso(80, 34, 38, "ic", "iw", "ic")]
    out += [C(80, 34, 3.5, "af"), C(66, 64, 3, "f"), C(56, 60, 3, "f"), C(46, 56, 3, "f"),
            C(96, 58, 3, "f"), C(108, 70, 3, "f")]
    return out


@dessin("physique")
def _():
    return [L(20, 100, 140, 100), P("M28,40 Q44,10 60,50 Q72,82 84,56 Q94,40 104,70", "d"), C(108, 82, 12, "ia"),
            G([R(-14, -14, 28, 28, "iw", 2)], "translate(40 86) rotate(-14)")]


@dessin("meteo")
def _():
    return [soleil(98, 40, 14, "ia", 9), nuage(70, 62, 1.25, "ic"), L(52, 84, 46, 96, "a"), L(68, 84, 62, 96, "a"), L(84, 84, 78, 96, "a"),
            L(60, 92, 56, 100, "t"), L(76, 92, 72, 100, "t")]


@dessin("crane")
def _():
    return [sol(80, 104, 30), P("M52,58 Q52,22 80,22 Q108,22 108,58 Q108,70 100,74 L100,88 L60,88 L60,74 Q52,70 52,58 Z", "ic"),
            E(68, 56, 8, 9, "f"), E(92, 56, 8, 9, "f"), PG([(80, 64), (84, 74), (76, 74)], "f"),
            L(68, 82, 68, 88, "t"), L(80, 82, 80, 88, "t"), L(92, 82, 92, 88, "t"), PL([(80, 22), (84, 30), (78, 36), (84, 42)], "a")]


@dessin("plume")
def _():
    return [sol(70, 104, 30), P("M46,100 Q60,74 86,48 Q110,24 126,18 Q122,42 104,64 Q86,84 46,100 Z", "iw"),
            P("M46,100 Q80,64 118,26", "i"), P("M126,18 Q122,30 116,38 Q120,26 126,18 Z", "ia"),
            L(86, 64, 96, 72, "t"), L(76, 74, 84, 82, "t"), L(98, 50, 108, 56, "t")]


@dessin("balance")
def _():
    return [sol(80, 104, 30), L(80, 26, 80, 98), L(64, 98, 96, 98), L(38, 40, 122, 32), C(80, 28, 4, "ia"),
            L(38, 40, 28, 66, "t"), L(38, 40, 48, 66, "t"), P("M24,66 Q38,78 52,66 Z", "iw"),
            L(122, 32, 112, 58, "t"), L(122, 32, 132, 58, "t"), P("M108,58 Q122,70 136,58 Z", "ia")]


@dessin("tombe")
def _():
    return [P("M30,100 Q80,88 130,100 Z", "iw"), P("M56,98 V44 Q56,22 80,22 Q104,22 104,44 V98 Z", "ic"),
            L(80, 36, 80, 66), L(70, 46, 90, 46), L(64, 76, 96, 76, "t"), L(68, 84, 92, 84, "t"),
            L(112, 98, 112, 84, "t"), C(112, 81, 4, "ia")]


@dessin("infini")
def _():
    return [P("M80,60 C94,40 126,40 126,60 C126,80 94,80 80,60 C66,40 34,40 34,60 C34,80 66,80 80,60 Z", "a"),
            P("M80,60 C94,40 126,40 126,60 C126,80 94,80 80,60 C66,40 34,40 34,60 C34,80 66,80 80,60 Z", "w")]


@dessin("sac_perce")
def _():
    return [sol(70, 104, 30), P("M48,38 Q60,30 70,38 Q82,30 92,38 L98,86 Q70,96 42,86 Z", "ic"), P("M56,38 Q70,46 84,38", "t"),
            PL([(90, 70), (96, 74), (92, 78), (98, 82)], "i"), C(108, 86, 5, "ia"), C(118, 98, 4, "ia"), C(104, 100, 3, "ic")]


# --- boucle et progression
@dessin("niveau")
def _():
    return [L(30, 98, 130, 98), R(36, 76, 20, 22, "iw"), R(64, 60, 20, 38, "iw"), R(92, 40, 20, 58, "ia"),
            L(36, 50, 74, 28, "a"), PL([(64, 26), (74, 28), (70, 37)], "a")]


@dessin("livre")
def _():
    return [sol(80, 104, 46), livre_ouvert(80, 40, 44, 50, "ic"), L(46, 50, 72, 53, "t"), L(46, 58, 72, 61, "t"), L(46, 66, 66, 69, "t"),
            L(88, 53, 114, 50, "t"), L(88, 61, 114, 58, "t"), P("M84,94 L84,110 L88,106 L92,110 L92,94", "ia")]


@dessin("trophee")
def _():
    return [sol(80, 106, 30), R(60, 92, 40, 10, "iw", 2), L(80, 74, 80, 92), R(72, 84, 16, 8, "ic", 2),
            P("M56,22 H104 V44 Q104,74 80,74 Q56,74 56,44 Z", "ia"), P("M56,30 Q40,30 42,44 Q44,56 58,56", "i"), P("M104,30 Q120,30 118,44 Q116,56 102,56", "i"),
            etoile(80, 44, 8, "ic")]


@dessin("maison")
def _():
    return [sol(80, 104, 46), R(46, 56, 68, 44, "ic"), PG([(38, 58), (80, 24), (122, 58)], "iw"), R(72, 74, 16, 26, "ia"),
            R(52, 66, 12, 12, "t"), R(96, 66, 12, 12, "t"), R(98, 30, 8, 16, "ic")]


@dessin("arbre")
def _():
    return [L(80, 92, 80, 64), L(80, 64, 52, 42), L(80, 64, 108, 42), L(52, 42, 40, 22), L(52, 42, 64, 22), L(108, 42, 120, 22),
            C(80, 94, 8, "ia"), C(80, 64, 7, "ic"), C(52, 42, 7, "ic"), C(108, 42, 7, "ic"), C(40, 22, 5, "iw"), C(64, 22, 5, "iw"), C(120, 22, 5, "ic")]


@dessin("cle")
def _():
    return [sol(80, 104, 34), C(52, 60, 18, "ia"), C(52, 60, 7, "ic"), L(70, 60, 128, 60), L(128, 60, 128, 72), L(116, 60, 116, 70), L(104, 60, 104, 68)]


@dessin("ampoule")
def _():
    return [P("M66,74 Q50,62 52,44 Q56,22 80,22 Q104,22 108,44 Q110,62 94,74 Z", "ia"), R(66, 74, 28, 16, "ic", 2), L(66, 82, 94, 82, "t"),
            R(72, 90, 16, 6, "iw", 2), P("M72,58 L76,46 L80,58 L84,46 L88,58", "i"),
            L(36, 30, 44, 36, "t"), L(124, 30, 116, 36, "t"), L(30, 52, 40, 52, "t"), L(130, 52, 120, 52, "t")]


@dessin("boucle")
def _():
    return [P("M46,60 A34,34 0 0 1 112,48", "a"), PL([(104, 42), (112, 48), (116, 38)], "a"),
            P("M114,60 A34,34 0 0 1 48,72", "i"), PL([(56, 78), (48, 72), (44, 82)], "i"), C(80, 60, 8, "iw")]


@dessin("calendrier")
def _():
    out = [sol(80, 106, 40), R(38, 24, 84, 76, "ic", 4), R(38, 24, 84, 16, "iw", 4), L(56, 18, 56, 30), L(104, 18, 104, 30)]
    for r in range(4):
        for c in range(6):
            x, y = 44 + c * 13, 46 + r * 13
            out.append(R(x, y, 9, 9, "ia" if (r, c) in ((1, 2), (1, 3), (2, 4)) else "t", 1))
    return out


@dessin("niveaux")
def _():
    return [R(22, 44, 30, 30, "iw", 3), R(65, 44, 30, 30, "iw", 3), R(108, 44, 30, 30, "ia", 3),
            L(54, 59, 63, 59), L(97, 59, 106, 59), texte("1", 34, 52, 14), texte("2", 77, 52, 14), texte("3", 120, 52, 14, "i")]


@dessin("monde_ouvert")
def _():
    return [montagne(50, 64, 60, 34, "iw", True), montagne(96, 64, 70, 44, "iw", True), L(16, 64, 144, 64, "t"),
            P("M60,104 Q90,86 80,76 Q72,68 96,64", "a"), sapin(34, 94, 24), sapin(126, 96, 28), arbre_rond(112, 80, 18)]


@dessin("hub")
def _():
    return [L(80, 60, 36, 30), L(80, 60, 124, 30), L(80, 60, 36, 92), L(80, 60, 124, 92),
            C(80, 60, 16, "ia"), C(36, 30, 10, "iw"), C(124, 30, 10, "iw"), C(36, 92, 10, "iw"), C(124, 92, 10, "ic"), maison_mini(80, 62)]


def maison_mini(x, y):
    return PG([(x - 7, y - 2), (x, y - 9), (x + 7, y - 2)], "ic") + R(x - 5, y - 2, 10, 8, "ic")


@dessin("arene")
def _():
    return [E(80, 64, 58, 34, "iw"), E(80, 64, 46, 25, "ic"), H(E(80, 64, 46, 25, "w")), E(80, 66, 36, 18, "ic"),
            personne(80, 74, 0.55, "ia")]


def carte_taille(f):
    out = [R(28, 18, 104, 84, "ic", 3)]
    for i in range(1, 4):
        out.append(L(28 + i * 26, 18, 28 + i * 26, 102, "t"))
    for j in range(1, 3):
        out.append(L(28, 18 + j * 28, 132, 18 + j * 28, "t"))
    w, h = 104 * f, 84 * f
    out.append(R(80 - w / 2, 60 - h / 2, w, h, "ia", 2))
    return out


@dessin("taille_petite")
def _():
    return carte_taille(0.25)


@dessin("taille_moyenne")
def _():
    return carte_taille(0.55)


@dessin("taille_grande")
def _():
    return carte_taille(0.85)


@dessin("mixte")
def _():
    return [R(30, 20, 100, 80, "ic", 3), hachP("M30,20 H130 L30,100 Z"), L(30, 100, 130, 20),
            maison_mini(104, 78), P("M98,52 Q98,40 106,40 Q114,40 114,52 Q114,58 106,66 Q98,58 98,52 Z", "ia"), C(106, 51, 3, "ic")]


@dessin("main")
def _():
    return [R(26, 24, 96, 72, "ic", 3), P("M36,80 Q52,52 66,68 Q80,84 96,50", "a"), crayon(126, 18, 100, 44)]


# --- paysages et saisons
@dessin("foret")
def _():
    return [soleil(122, 30, 7, "ia", 8), L(16, 98, 144, 98), sapin(40, 98, 56), sapin(66, 98, 70, "ic"), arbre_rond(96, 98, 50), sapin(122, 98, 44)]


@dessin("montagne")
def _():
    return [montagne(58, 98, 80, 66, "iw", True), montagne(108, 98, 70, 48, "ic", True), L(58, 32, 58, 20), PG([(58, 20), (70, 24), (58, 28)], "ia")]


@dessin("desert")
def _():
    return [soleil(116, 34, 10, "ia", 9), P("M14,98 Q50,70 84,90 Q110,74 146,92 L146,104 L14,104 Z", "iw"),
            P("M58,86 V52 Q58,46 64,46 Q70,46 70,52 V86 M58,66 H50 V56 M70,62 H78 V52", "i")]


@dessin("palmier")
def _():
    return [soleil(124, 30, 8, "ia", 8), P("M30,92 Q70,74 110,92 Z", "iw"), P("M18,100 Q30,96 42,100 T66,100 T90,100 T114,100 T138,100", "i"),
            P("M70,84 Q66,60 76,34", "i"), P("M76,34 Q60,26 46,36", "i"), P("M76,34 Q92,24 106,32", "i"), P("M76,34 Q62,40 58,54", "i"), P("M76,34 Q92,40 96,54", "i"),
            C(74, 40, 3, "f")]


@dessin("immeubles")
def _():
    out = [L(16, 100, 144, 100), R(26, 46, 26, 54, "iw"), R(56, 26, 30, 74, "ic"), R(90, 54, 22, 46, "iw"), R(116, 38, 26, 62, "ic")]
    for r in range(5):
        for c in range(2):
            out.append(R(62 + c * 12, 34 + r * 12, 6, 7, "ia" if (r, c) == (1, 1) else "t"))
    for r in range(4):
        out.append(R(122, 46 + r * 12, 14, 6, "t"))
    return out


@dessin("vagues")
def _():
    return [P("M70,70 L70,30 L98,64 Z", "ia"), L(70, 30, 70, 74), P("M50,74 H100 L92,84 H58 Z", "ic"),
            P("M14,90 Q26,82 38,90 T62,90 T86,90 T110,90 T134,90 T158,90", "i"), P("M20,102 Q32,94 44,102 T68,102 T92,102 T116,102 T140,102", "t")]


@dessin("grotte")
def _():
    return [P("M16,104 Q20,30 80,24 Q140,30 144,104 Z", "iw"), P("M36,104 Q40,48 80,44 Q120,48 124,104 Z", "f"),
            PG([(56, 50), (60, 64), (64, 48)], "ic"), PG([(90, 46), (94, 60), (98, 47)], "ic"),
            L(110, 104, 106, 82, "i"), P("M106,82 Q100,72 106,64 Q114,72 106,82 Z", "ia")]


@dessin("planete")
def _():
    return [C(80, 60, 28, "ic"), H(C(80, 60, 28, "w")), C(80, 60, 28, "i"), P("M30,70 Q80,30 130,50", "i"), P("M30,70 Q42,82 80,72 Q118,62 130,50", "a"),
            etoile(32, 28, 4, "f"), etoile(128, 92, 5, "ia"), etoile(124, 22, 3, "f")]


@dessin("chateau")
def _():
    return [L(16, 100, 144, 100), R(54, 50, 52, 50, "ic"),
            P("M36,100 V40 H40 V34 H46 V40 H52 V34 H58 V40 H62 V100 Z", "iw"), P("M98,100 V40 H102 V34 H108 V40 H114 V34 H120 V40 H124 V100 Z", "iw"),
            P("M70,100 V82 Q80,70 90,82 V100 Z", "f"), L(111, 34, 111, 18), PG([(111, 18), (124, 22), (111, 26)], "ia")]


@dessin("saisons")
def _():
    return [C(80, 60, 38, "ic"), L(80, 22, 80, 98, "t"), L(42, 60, 118, 60, "t"),
            C(62, 42, 6, "ia"), C(56, 38, 3, "ic"), C(68, 38, 3, "ic"), C(56, 46, 3, "ic"), C(68, 46, 3, "ic"),
            soleil(98, 42, 6, "iw", 8), P("M54,84 Q62,68 72,74 Q66,86 54,84 Z", "iw"),
            L(98, 70, 98, 88, "t"), L(90, 74, 106, 84, "t"), L(90, 84, 106, 74, "t")]


@dessin("printemps")
def _():
    out = [P("M24,96 Q70,70 136,30", "i"), P("M64,74 Q72,58 70,50", "t"), P("M100,52 Q110,64 118,64", "t")]
    for x, y in ((70, 48), (40, 84), (120, 64), (110, 40)):
        for k in range(5):
            a = math.radians(k * 72 - 90)
            out.append(C(x + 5 * math.cos(a), y + 5 * math.sin(a), 4.5, "ic"))
        out.append(C(x, y, 3, "af"))
    return out


@dessin("ete")
def _():
    return [soleil(80, 48, 20, "ia", 12), P("M14,96 Q30,88 46,96 T78,96 T110,96 T142,96", "i"), P("M30,106 Q46,98 62,106 T94,106 T126,106", "t")]


@dessin("automne")
def _():
    feuille = "M0,-12 Q10,-4 6,8 L0,12 L-6,8 Q-10,-4 0,-12 Z"
    return [L(16, 102, 144, 102), G([P(feuille, "ia"), L(0, -10, 0, 16, "t")], "translate(54 46) rotate(-20)"),
            G([P(feuille, "iw"), L(0, -10, 0, 16, "t")], "translate(98 34) rotate(30)"),
            G([P(feuille, "ia"), L(0, -10, 0, 16, "t")], "translate(108 82) rotate(70)"),
            G([P(feuille, "ic"), L(0, -10, 0, 16, "t")], "translate(70 92) rotate(-80) scale(.8)"), P("M60,64 Q72,72 68,84", "d")]


@dessin("hiver")
def _():
    out = [P("M14,100 Q80,86 146,100 Z", "ic"), sapin(48, 98, 56, "iw"), P("M40,64 Q48,60 56,64", "ic")]
    for k in range(3):
        a = math.radians(k * 60)
        out.append(L(104 - 20 * math.cos(a), 46 - 20 * math.sin(a), 104 + 20 * math.cos(a), 46 + 20 * math.sin(a)))
    out += [C(104, 46, 4, "ia"), C(132, 80, 2, "f"), C(84, 82, 2, "f"), C(124, 22, 2, "f")]
    return out


# --- histoire
@dessin("parchemin")
def _():
    return [sol(80, 106, 46), R(44, 26, 72, 70, "ic"), E(44, 61, 8, 37, "iw"), E(116, 61, 8, 37, "iw"),
            L(56, 42, 104, 42, "t"), L(56, 52, 100, 52, "t"), L(56, 62, 104, 62, "t"), L(56, 72, 90, 72, "t"), C(98, 84, 6, "ia")]


@dessin("plume_encre")
def _():
    return [sol(70, 104, 30), P("M48,74 H84 V96 Q84,102 78,102 H54 Q48,102 48,96 Z", "iw"), R(54, 66, 24, 8, "ic", 2), E(66, 74, 18, 4, "f"),
            P("M66,72 Q86,40 118,16 Q118,38 98,52 Q84,62 66,72 Z", "ia"), L(66, 72, 112, 24, "i")]


@dessin("ruines")
def _():
    return [L(16, 100, 144, 100), R(38, 46, 16, 54, "ic"), PG([(34, 46), (58, 46), (56, 40), (36, 40)], "iw"),
            PG([(70, 100), (70, 66), (78, 60), (86, 68), (86, 100)], "ic"), R(98, 88, 40, 12, "iw"), C(118, 82, 5, "ia"),
            P("M40,52 Q48,62 40,72 Q48,80 42,90", "a")]


@dessin("clap")
def _():
    return [sol(80, 106, 40), R(38, 50, 84, 50, "ic", 2), G([R(0, -12, 84, 12, "iw"), L(14, -12, 22, 0), L(34, -12, 42, 0), L(54, -12, 62, 0)], "translate(38 48) rotate(-14)"),
            R(38, 50, 84, 10, "f"), L(46, 72, 108, 72, "t"), L(46, 84, 96, 84, "t"), C(112, 86, 6, "ia")]


@dessin("journal")
def _():
    return [sol(80, 106, 40), R(42, 20, 64, 82, "iw", 4), R(48, 20, 58, 82, "ic", 4), R(98, 52, 16, 14, "ia", 3),
            L(58, 38, 92, 38, "t"), L(58, 48, 88, 48, "t"), crayon(124, 92, 112, 52)]


@dessin("ligne")
def _():
    return [L(26, 60, 134, 60), C(26, 60, 6, "ic"), C(134, 60, 7, "ia"), C(62, 60, 3, "f"), C(98, 60, 3, "f")]


@dessin("fourche")
def _():
    return [L(22, 64, 74, 64), P("M74,64 Q96,64 130,32", "i"), P("M74,64 Q96,64 130,94", "i"), C(22, 64, 6, "ic"), C(74, 64, 5, "f"),
            C(130, 32, 7, "ia"), C(130, 94, 7, "ic")]


@dessin("arbre_branches")
def _():
    return [L(18, 60, 52, 60), P("M52,60 Q66,60 86,34", "i"), P("M52,60 Q66,60 86,86", "i"), P("M86,34 Q100,22 132,20", "i"), P("M86,34 Q104,40 132,44", "i"),
            P("M86,86 Q104,78 132,72", "i"), P("M86,86 Q104,98 132,100", "i"), C(18, 60, 5, "ic"), C(52, 60, 4, "f"), C(86, 34, 4, "f"), C(86, 86, 4, "f"),
            C(132, 20, 5, "ia"), C(132, 44, 5, "ic"), C(132, 72, 5, "ic"), C(132, 100, 5, "ia")]


@dessin("fin_une")
def _():
    return [P("M20,96 Q60,96 70,72 Q80,48 112,52", "i"), C(20, 96, 5, "ic"), L(116, 56, 116, 18), PG([(116, 20), (138, 28), (116, 36)], "ia")]


@dessin("fins")
def _():
    out = [L(18, 64, 54, 64), P("M54,64 Q80,64 110,26", "i"), L(54, 64, 110, 64), P("M54,64 Q80,64 110,100", "i"), C(18, 64, 5, "ic")]
    for y, c in ((26, "ia"), (64, "iw"), (100, "ic")):
        out += [L(112, y, 112, y - 18), PG([(112, y - 18), (128, y - 13), (112, y - 8)], c)]
    return out


# --- styles visuels
@dessin("stylise")
def _():
    return [P("M14,100 Q48,62 84,88 Q110,70 146,96 L146,104 L14,104 Z", "iw"), L(56, 82, 56, 60),
            P("M56,60 Q34,62 38,44 Q40,24 58,26 Q76,22 76,42 Q80,62 56,60 Z", "ia"), C(112, 36, 12, "ic")]


@dessin("realiste")
def _():
    return [R(22, 16, 116, 88, "ic", 2), montagne(66, 80, 70, 50, "iw", True), montagne(108, 80, 60, 34, "ic"), H(P("M22,80 L138,80 L138,104 L22,104 Z", "w")),
            L(22, 80, 138, 80), L(34, 74, 52, 74, "t"), P("M96,70 L98,52 L100,70", "t"), C(120, 32, 6, "ia")]


@dessin("pixel")
def _():
    grille = ["0110110", "1221221", "1222221", "1222221", "0122210", "0012100", "0001000"]
    out = []
    s = 11
    x0, y0 = 80 - 3.5 * s, 60 - 3.5 * s
    for r, ligne in enumerate(grille):
        for c, v in enumerate(ligne):
            if v != "0":
                out.append(R(x0 + c * s, y0 + r * s, s, s, "f" if v == "1" else "af"))
    out.append(R(x0 + 2 * s, y0 + 2 * s, s, s, "ic"))
    return out


@dessin("low_poly")
def _():
    return [PG([(30, 98), (62, 34), (80, 98)], "iw"), PG([(62, 34), (94, 98), (80, 98)], "ic"), PG([(62, 34), (84, 60), (94, 98)], "w"),
            PG([(86, 98), (112, 44), (138, 98)], "ia"), PG([(112, 44), (120, 98), (138, 98)], "iw"), L(20, 98, 144, 98)]


@dessin("cel")
def _():
    return [sol(80, 104, 34), C(80, 60, 34, "ic"), P("M80,26 A34,34 0 0 1 80,94 Q100,76 98,58 Q96,38 80,26 Z", "w"),
            P("M58,40 Q64,32 72,32", "i"), C(80, 60, 34, "i").replace('class="i"', 'class="i" style="stroke-width:3.6"'), P("M46,66 Q80,80 114,66", "a")]


@dessin("voxel")
def _():
    s = 12
    out = [sol(80, 104, 40), cube_iso(80, 80, s, "ic", "iw", "ic"), cube_iso(80, 68, s, "ic", "iw", "ic")]
    for (x, y, c) in ((80, 38, "ia"), (80 - 10.4, 44, "ia"), (80 + 10.4, 44, "ia"), (80, 50, "ia"), (80, 26, "ia")):
        out.append(cube_iso(x, y, s, c, "iw", "ic"))
    return out


@dessin("dessin_main")
def _():
    return [R(24, 20, 92, 76, "ic", 2), P("M34,80 Q44,60 54,66 Q62,70 66,58 Q72,44 84,52", "t"), P("M36,82 Q46,62 56,68 Q64,72 68,60 Q74,46 86,54", "i"),
            C(98, 40, 8, "t"), C(97, 41, 8, "t"), crayon(140, 64, 110, 88)]


# --- palettes
@dessin("soleil")
def _():
    return [soleil(80, 58, 22, "ia", 12)]


@dessin("lune")
def _():
    return [lune(74, 60, 30, "iw"), etoile(116, 32, 6, "ia"), etoile(120, 84, 4, "ic"), etoile(42, 30, 4, "ic")]


@dessin("contraste")
def _():
    return [C(80, 60, 36, "ic"), P("M80,24 A36,36 0 0 1 80,96 Z", "f"), C(66, 60, 8, "ia")]


@dessin("brume")
def _():
    return [montagne(56, 84, 80, 44, "w"), montagne(108, 84, 70, 34, "w"), L(20, 60, 70, 60, "t"), L(60, 70, 132, 70, "t"), L(28, 80, 120, 80, "t"),
            L(40, 90, 140, 90, "t"), L(20, 100, 100, 100, "t"), C(118, 34, 7, "ia")]


@dessin("arc_en_ciel")
def _():
    return [P("M22,96 A58,58 0 0 1 138,96", "a").replace('class="a"', 'class="a" style="stroke-width:7"'),
            P("M32,96 A48,48 0 0 1 128,96", "i").replace('class="i"', 'class="i" style="stroke-width:7;stroke-opacity:.35"'),
            P("M42,96 A38,38 0 0 1 118,96", "i").replace('class="i"', 'class="i" style="stroke-width:6"'),
            nuage(36, 96, 0.6), nuage(124, 96, 0.6)]


@dessin("melange")
def _():
    return [C(62, 50, 22, "iw"), C(98, 50, 22, "ic"), C(80, 78, 22, "ia"), C(80, 60, 22, "i"), C(62, 50, 22, "i"), C(98, 50, 22, "i")]


@dessin("pinceau")
def _():
    return [P("M34,92 Q56,70 82,76 Q100,80 120,64", "a").replace('class="a"', 'class="a" style="stroke-width:7"'),
            G([R(-4, -40, 8, 40, "iw", 3), R(-5, 0, 10, 8, "ic"), P("M-5,8 Q-6,20 0,26 Q6,20 5,8 Z", "ia")], "translate(110 40) rotate(30)")]


@dessin("panier")
def _():
    return [sol(80, 104, 40), P("M32,48 L42,48 L54,88 L110,88 L120,58 L46,58", "i"), C(60, 98, 5, "ic"), C(104, 98, 5, "ic"),
            R(58, 38, 18, 20, "ia", 2), R(80, 44, 22, 14, "iw", 2)]


@dessin("etincelles")
def _():
    return [etoile(74, 62, 30, "ia", 4, 0.22), etoile(116, 32, 12, "ic", 4, 0.25), etoile(118, 88, 8, "iw", 4, 0.25), etoile(38, 30, 7, "ic", 4, 0.25)]


@dessin("dossier")
def _():
    return [sol(80, 104, 46), dossier(34, 30, 92, 66, "iw"), R(48, 48, 64, 46, "ic", 2), L(56, 60, 104, 60, "t"), L(56, 70, 96, 70, "t"), R(56, 78, 18, 10, "ia")]


@dessin("planches")
def _():
    return [R(22, 18, 116, 84, "iw", 3), G([R(-16, -12, 32, 26, "ic"), montagne(0, 10, 22, 14, "w")], "translate(48 42) rotate(-5)"),
            G([R(-16, -12, 32, 26, "ic"), C(0, 0, 7, "ia")], "translate(102 40) rotate(6)"),
            G([R(-20, -12, 40, 26, "ic"), L(-14, 0, 14, 0, "t"), L(-14, 6, 8, 6, "t")], "translate(76 78) rotate(-2)"),
            C(48, 30, 2.5, "af"), C(102, 28, 2.5, "af"), C(76, 66, 2.5, "af")]


# --- interface
def ecran_jeu():
    return [R(20, 16, 120, 88, "ic", 4), montagne(60, 90, 60, 36, "w"), montagne(104, 90, 60, 26, "w"), L(20, 90, 140, 90, "t")]


@dessin("hud_minimal")
def _():
    return ecran_jeu() + [C(80, 58, 2, "af"), L(30, 96, 50, 96, "a")]


@dessin("hud_classique")
def _():
    return ecran_jeu() + [R(28, 24, 40, 6, "iw", 2), R(28, 24, 28, 6, "af", 2), C(124, 34, 10, "ic"), R(56, 92, 48, 8, "ic", 2),
                          L(68, 92, 68, 100, "t"), L(80, 92, 80, 100, "t"), L(92, 92, 92, 100, "t")]


@dessin("hud_riche")
def _():
    return ecran_jeu() + [R(20, 16, 120, 12, "iw", 3), R(24, 32, 26, 50, "ic", 2), R(110, 32, 26, 50, "ic", 2), R(54, 90, 52, 12, "ic", 2),
                          L(28, 40, 46, 40, "t"), L(28, 48, 42, 48, "t"), L(28, 56, 46, 56, "t"), R(28, 62, 12, 8, "af"),
                          L(114, 40, 132, 40, "t"), L(114, 48, 128, 48, "t"), R(114, 60, 18, 14, "iw"), C(30, 22, 2, "f"), C(38, 22, 2, "f")]


@dessin("menu_moderne")
def _():
    return [R(30, 16, 100, 88, "ic", 6), R(46, 32, 68, 12, "iw", 6), R(46, 50, 68, 12, "ia", 6), R(46, 68, 68, 12, "iw", 6), R(46, 86, 40, 8, "t", 4)]


@dessin("menu_retro")
def _():
    return [R(22, 14, 116, 82, "iw", 14), R(32, 22, 96, 64, "f", 10), R(52, 36, 50, 6, "ic"), R(52, 50, 40, 6, "ic"), R(52, 64, 46, 6, "ic"),
            PG([(40, 48), (46, 53), (40, 58)], "af"), R(56, 96, 48, 10, "iw", 2)]


@dessin("carte")
def _():
    return [PG([(24, 26), (56, 18), (84, 28), (136, 18), (136, 92), (104, 102), (76, 92), (24, 102)], "ic"),
            L(56, 18, 56, 94, "t"), L(84, 28, 84, 92, "t"), L(104, 22, 104, 102, "t"),
            P("M34,86 Q50,60 70,70 Q90,82 100,56 Q106,42 116,40", "d"), L(112, 34, 122, 44, "a"), L(122, 34, 112, 44, "a")]


# --- son
@dessin("musique_adaptative")
def _():
    return [P("M18,84 Q34,84 42,70 Q52,52 64,70 Q74,86 86,56 Q96,30 110,44 Q122,56 142,26", "a"),
            L(18, 98, 142, 98, "t"), E(48, 38, 6, 4, "f"), L(53, 37, 53, 18), E(118, 82, 6, 4, "f"), L(123, 81, 123, 62)]


@dessin("musique_douce")
def _():
    return [P("M16,76 Q36,66 56,76 T96,76 T136,76", "t"), P("M16,86 Q36,76 56,86 T96,86 T136,86", "t"),
            E(76, 58, 9, 6, "af"), L(84, 56, 84, 22), P("M84,22 Q98,28 96,40", "i")]


@dessin("orchestre")
def _():
    out = [L(20, 30 + i * 12, 140, 30 + i * 12, "t") for i in range(5)]
    out += [E(50, 72, 7, 5, "f"), L(56, 71, 56, 34), E(80, 60, 7, 5, "f"), L(86, 59, 86, 26), L(56, 34, 86, 26, "i"),
            E(112, 54, 7, 5, "af"), L(118, 53, 118, 20, "a"), L(56, 40, 86, 32)]
    return out


@dessin("silence")
def _():
    return [sol(80, 104, 30), E(70, 80, 12, 8, "iw"), L(81, 78, 81, 30), P("M81,30 Q98,38 94,52", "i"), L(44, 96, 116, 24, "a")]


@dessin("bibliotheque")
def _():
    out = [R(26, 18, 108, 86, "ic", 2), L(26, 60, 134, 60), L(26, 104, 134, 104)]
    x = 32
    for i, w in enumerate((8, 10, 7, 12, 8, 9, 11)):
        out.append(R(x, 26 if i % 3 else 30, w, 34 if i % 3 else 30, "ia" if i == 3 else "iw"))
        x += w + 3
    x = 32
    for i, w in enumerate((10, 8, 12, 9, 8, 10)):
        out.append(R(x, 70 if i % 2 else 66, w, 34 if i % 2 else 38, "iw" if i % 2 else "ic"))
        x += w + 4
    return out


@dessin("partition")
def _():
    out = [sol(80, 106, 40), R(34, 14, 92, 88, "ic", 2)]
    for b in (30, 64):
        out += [L(42, b + i * 5, 118, b + i * 5, "t") for i in range(5)]
    out += [E(56, 44, 4, 3, "f"), L(60, 43, 60, 26), E(74, 40, 4, 3, "f"), L(78, 39, 78, 22), E(96, 76, 4, 3, "af"), L(100, 75, 100, 58, "a"),
            E(108, 72, 4, 3, "f"), L(112, 71, 112, 54)]
    return out


@dessin("onomatopee")
def _():
    out = []
    p = []
    for i in range(18):
        r = 44 if i % 2 == 0 else 28
        a = math.radians(i * 20)
        p.append((80 + r * math.cos(a), 60 + r * 0.78 * math.sin(a)))
    out.append(PG(p, "ia"))
    out += [P("M78,40 L82,40 L81,66 L79,66 Z", "f"), C(80, 76, 3, "f")]
    return out


def micro_(x, y, s=1.0, c="ic"):
    return (R(x - 10 * s, y - 34 * s, 20 * s, 36 * s, c, 10 * s) + P("M%s,%s Q%s,%s %s,%s Q%s,%s %s,%s" % (
        n(x - 16 * s), n(y - 10 * s), n(x - 16 * s), n(y + 12 * s), n(x), n(y + 12 * s), n(x + 16 * s), n(y + 12 * s), n(x + 16 * s), n(y - 10 * s)), "i")
        + L(x, y + 12 * s, x, y + 26 * s) + L(x - 10 * s, y + 26 * s, x + 10 * s, y + 26 * s)
        + L(x - 6 * s, y - 24 * s, x + 6 * s, y - 24 * s, "t") + L(x - 6 * s, y - 16 * s, x + 6 * s, y - 16 * s, "t"))


@dessin("micro")
def _():
    return [sol(80, 104, 24), micro_(80, 66, 1.1, "ia")]


@dessin("micros")
def _():
    return [sol(80, 104, 46), micro_(58, 70, 0.9, "ic"), micro_(102, 70, 0.9, "ia")]


@dessin("ambiance_3d")
def _():
    return [P("M66,96 Q60,80 64,66 Q56,60 60,52 Q60,30 82,28 Q102,28 102,50 Q102,66 94,72 L94,96 Z", "ic"),
            P("M40,40 A40,40 0 0 0 40,90", "t"), P("M28,30 A54,54 0 0 0 28,100", "t"), P("M118,40 A40,40 0 0 1 118,90", "a"), P("M130,30 A54,54 0 0 1 130,100", "t"),
            C(112, 24, 4, "ia")]


@dessin("haut_parleur")
def _():
    return [PG([(40, 48), (56, 48), (78, 28), (78, 92), (56, 72), (40, 72)], "ic"), R(40, 48, 16, 24, "iw"),
            P("M92,46 Q100,60 92,74", "a"), P("M102,36 Q116,60 102,84", "i"), P("M112,26 Q132,60 112,94", "t")]


# --- plateformes
@dessin("pc")
def _():
    return [sol(70, 104, 46), ecran(30, 22, 74, 52), R(110, 40, 26, 62, "iw", 3), C(123, 52, 4, "ia"), L(116, 64, 130, 64, "t"),
            R(40, 92, 54, 10, "ic", 2), montagne(66, 66, 40, 26, "w")]


@dessin("pc_puissant")
def _():
    return [sol(80, 104, 50), ecran(20, 26, 70, 50), R(98, 18, 40, 84, "iw", 4), C(118, 40, 10, "ic"), C(118, 40, 4, "af"), C(118, 70, 10, "ic"),
            C(118, 70, 4, "f"), L(104, 90, 132, 90, "a"), L(30, 52, 54, 40, "t"), L(30, 62, 74, 40, "t")]


@dessin("navigateur")
def _():
    return [R(20, 20, 120, 80, "ic", 6), L(20, 36, 140, 36), C(30, 28, 2.5, "af"), C(38, 28, 2.5, "f"), C(46, 28, 2.5, "f"),
            R(56, 24, 76, 8, "iw", 4), R(32, 46, 40, 44, "iw", 2), L(82, 50, 128, 50, "t"), L(82, 60, 122, 60, "t"), L(82, 70, 128, 70, "t"), R(82, 78, 30, 10, "ia", 2)]


@dessin("mobile")
def _():
    return [sol(80, 106, 26), R(56, 12, 48, 92, "ic", 8), R(61, 22, 38, 70, "iw", 2), C(80, 98, 3, "f"), R(72, 16, 16, 2, "f"), C(80, 56, 8, "ia")]


@dessin("console")
def _():
    return [sol(80, 104, 50), R(28, 34, 74, 26, "ic", 6), L(28, 50, 102, 50, "t"), C(92, 42, 2.5, "af"), manette(110, 82, 0.75)]


@dessin("console_portable")
def _():
    return [sol(80, 104, 50), R(18, 34, 124, 54, "ic", 22), R(48, 40, 64, 42, "iw", 3), C(32, 56, 6, "ic"), C(128, 66, 6, "ic"),
            C(128, 48, 3, "af"), C(34, 74, 3, "f"), montagne(80, 82, 40, 24, "ic")]


@dessin("portable")
def _():
    return [sol(80, 104, 50), R(36, 24, 88, 56, "ic", 4), R(42, 30, 76, 44, "iw", 2), P("M22,80 H138 L130,94 H30 Z", "ic"), L(66, 87, 94, 87, "t"),
            C(80, 52, 6, "ia")]


@dessin("vr")
def _():
    return [P("M24,50 Q24,36 40,36 H120 Q136,36 136,50 V72 Q136,84 122,84 H100 Q92,84 88,76 Q80,66 72,76 Q68,84 60,84 H38 Q24,84 24,72 Z", "ic"),
            E(54, 60, 16, 12, "iw"), E(106, 60, 16, 12, "ia"), P("M24,52 Q8,52 10,70", "i"), P("M136,52 Q152,52 150,70", "i")]


@dessin("briques")
def _():
    def brique(x, y, w, c):
        out = R(x, y, w, 20, c, 2)
        for i in range(int(w // 20)):
            out += R(x + 5 + i * 20, y - 6, 10, 6, c, 1)
        return out
    return [sol(80, 104, 46), brique(36, 78, 80, "iw"), brique(56, 52, 60, "ia"), brique(46, 26, 40, "ic")]


@dessin("clavier")
def _():
    out = [sol(76, 102, 50), R(18, 54, 96, 40, "ic", 4)]
    for r in range(3):
        for c in range(8):
            out.append(R(24 + c * 11, 60 + r * 10, 8, 7, "ia" if (r, c) == (1, 2) else "t", 1))
    out += [P("M126,58 Q126,46 134,46 Q142,46 142,58 V78 Q142,90 134,90 Q126,90 126,78 Z", "ic"), L(126, 64, 142, 64, "t"), L(134, 46, 134, 64, "t"),
            P("M134,46 Q134,30 118,28", "t")]
    return out


@dessin("tactile")
def _():
    return [R(36, 16, 52, 92, "ic", 8), R(41, 26, 42, 70, "iw", 2), C(70, 56, 9, "a"), C(70, 56, 16, "t"),
            P("M86,108 L80,68 Q80,62 86,62 Q92,62 92,68 L94,82 Q100,78 104,82 Q110,80 112,86 Q118,84 120,92 L118,108 Z", "ic")]


@dessin("clavier_manette")
def _():
    out = [R(14, 36, 70, 30, "ic", 4)]
    for r in range(2):
        for c in range(6):
            out.append(R(20 + c * 10, 42 + r * 10, 7, 7, "t", 1))
    out += [manette(108, 74, 0.95), L(84, 50, 92, 50, "a")]
    return out


# --- moteurs (pictogrammes neutres, sans logo)
@dessin("moteur_libre")
def _():
    return [moteur(72, 56), P("M58,44 V36 Q58,28 66,28 Q74,28 74,36", "i"), R(54, 42, 24, 20, "ia", 3), C(66, 52, 3, "f")]


@dessin("moteur_polyvalent")
def _():
    return [moteur(72, 56), G([R(-3, -16, 6, 32, "ia", 2), C(0, -18, 6, "ia"), C(0, -18, 2.5, "ic")], "translate(66 52) rotate(45)"),
            G([R(-3, -16, 6, 32, "ic", 2), R(-5, 10, 10, 10, "iw", 2)], "translate(66 52) rotate(-45)")]


@dessin("moteur_lourd")
def _():
    return [moteur(72, 60), R(36, 18, 10, 26, "iw"), R(52, 24, 10, 20, "iw"), C(42, 12, 6, "ic"), C(52, 8, 5, "ic"), C(60, 16, 4, "ia")]


@dessin("moteur_web")
def _():
    return [moteur(72, 56), C(64, 52, 12, "ia"), E(64, 52, 5, 12, "t"), L(52, 52, 76, 52, "t")]


@dessin("moteur_web3d")
def _():
    return [moteur(72, 56), C(64, 52, 13, "ic"), E(64, 52, 5, 13, "t"), L(51, 52, 77, 52, "t"), cube_iso(66, 46, 8, "ia", "iw", "ic")]


@dessin("moteur_code")
def _():
    return [moteur(72, 56), P("M58,42 Q52,42 52,48 V50 Q52,54 48,54 Q52,54 52,58 V60 Q52,66 58,66", "a"),
            P("M70,42 Q76,42 76,48 V50 Q76,54 80,54 Q76,54 76,58 V60 Q76,66 70,66", "a")]


@dessin("moteur_maison")
def _():
    return [sol(80, 104, 50), R(26, 62, 108, 10, "ic", 2), L(34, 72, 34, 100), L(126, 72, 126, 100), L(34, 90, 126, 90, "t"),
            G([R(-3, -10, 6, 34, "iw", 2), R(-12, -18, 24, 10, "ic", 2)], "translate(58 44) rotate(-20)"),
            G([R(-3, -14, 6, 30, "ia", 2), C(0, -18, 7, "ia"), C(0, -20, 3, "ic")], "translate(100 42) rotate(25)"), engrenage(80, 50, 10, 8, "iw")]


@dessin("script")
def _():
    return [sol(80, 106, 44), R(40, 18, 80, 84, "ic", 3), L(50, 32, 74, 32, "a"), L(58, 42, 96, 42, "t"), L(58, 52, 88, 52, "t"),
            L(50, 62, 70, 62, "a"), L(58, 72, 104, 72, "t"), L(58, 82, 90, 82, "t"), L(50, 92, 64, 92, "a")]


@dessin("code")
def _():
    return [PL([(54, 34), (30, 60), (54, 86)], "i"), PL([(106, 34), (130, 60), (106, 86)], "i"), L(92, 26, 68, 94, "a")]


@dessin("noeuds")
def _():
    return [R(18, 26, 40, 30, "ic", 4), R(18, 26, 40, 9, "iw", 4), R(102, 64, 40, 30, "ic", 4), R(102, 64, 40, 9, "ia", 4),
            R(30, 74, 36, 24, "ic", 4), P("M58,44 C82,44 78,78 102,78", "a"), P("M66,86 C84,86 84,86 102,86", "i"),
            C(58, 44, 3, "f"), C(102, 78, 3, "af")]


@dessin("noeuds_code")
def _():
    return [R(16, 28, 40, 30, "ic", 4), R(16, 28, 40, 9, "iw", 4), R(16, 72, 40, 30, "ic", 4), R(16, 72, 40, 9, "ia", 4),
            P("M56,46 C72,46 72,62 86,62", "a"), P("M56,90 C72,90 72,62 86,62", "i"),
            PL([(104, 44), (90, 62), (104, 80)], "i"), PL([(130, 44), (144, 62), (130, 80)], "i"), L(124, 40, 110, 84, "a")]


def etiquette_(neuve):
    out = [sol(80, 104, 40), P("M42,38 L96,38 L124,64 L96,90 L42,90 Z", "ic"), C(104, 64, 5, "ic"), P("M104,64 Q120,40 134,40", "t"),
           L(52, 54, 84, 54, "t"), L(52, 66, 78, 66, "t"), L(52, 78, 84, 78, "t")]
    if neuve:
        out += [etoile(44, 30, 10, "ia", 4, 0.3), etoile(30, 48, 5, "ic", 4, 0.3)]
    else:
        out.append(R(52, 50, 24, 8, "af"))
    return out


@dessin("etiquette")
def _():
    return etiquette_(False)


@dessin("etiquette_neuve")
def _():
    return etiquette_(True)


def branches_(lfs):
    out = [L(20, 76, 140, 76), P("M44,76 Q56,40 76,40 L100,40 Q118,40 124,76", "i")]
    for x in (32, 60, 92, 136):
        out.append(C(x, 76, 6, "ic"))
    out += [C(76, 40, 6, "ia"), C(104, 40, 6, "ia")]
    if lfs:
        out.append(cube_iso(36, 30, 14, "iw", "iw", "ic"))
    return out


@dessin("branches")
def _():
    return branches_(False)


@dessin("branches_lfs")
def _():
    return branches_(True)


# --- multijoueur
@dessin("solo")
def _():
    return [sol(80, 104, 26), personne(80, 100, 1.4, "ia")]


@dessin("coop_ligne")
def _():
    return [sol(80, 104, 56), ecran(18, 46, 44, 32), ecran(98, 46, 44, 32), personne(40, 72, 0.6, "ia"), personne(120, 72, 0.6, "iw"),
            P("M66,40 Q80,30 94,40", "a"), P("M60,30 Q80,16 100,30", "t"), C(80, 44, 2.5, "af")]


@dessin("ecran_partage")
def _():
    return [ecran(26, 18, 108, 64), L(80, 23, 80, 77), personne(54, 72, 0.6, "ia"), personne(106, 72, 0.6, "iw"),
            P("M36,106 V96 Q36,90 44,90 H116 Q124,90 124,96 V106", "iw")]


@dessin("versus")
def _():
    return [sol(80, 104, 54), personne(40, 100, 1.1, "ia"), personne(120, 100, 1.1, "iw"),
            PG([(84, 32), (70, 60), (82, 60), (74, 86), (92, 54), (80, 54), (90, 32)], "ic")]


def foule_(nb, cols):
    out = [sol(80, 104, 56)]
    rows = (nb + cols - 1) // cols
    s = 0.9 if nb <= 4 else (0.5 if nb <= 16 else 0.32)
    dx = 100 / max(cols, 1)
    dy = 26 * s * 1.6
    k = 0
    for r in range(rows):
        for c in range(cols):
            if k >= nb:
                break
            x = 80 + (c - (cols - 1) / 2) * dx
            y = 100 - (rows - 1 - r) * dy
            out.append(personne(x, y, s, "ia" if k == nb - 1 - (cols // 2) else ("iw" if (r + c) % 2 else "ic")))
            k += 1
    return out


@dessin("joueurs_2")
def _():
    return [sol(80, 104, 40), personne(60, 100, 1.1, "ia"), personne(100, 100, 1.1, "iw")]


@dessin("joueurs_4")
def _():
    return [sol(80, 104, 56), personne(38, 100, 0.85, "iw"), personne(66, 100, 0.85, "ia"), personne(94, 100, 0.85, "ic"), personne(122, 100, 0.85, "iw")]


@dessin("joueurs_16")
def _():
    out = [sol(80, 104, 56)]
    for r in range(3):
        for c in range(6):
            if r == 2 and c >= 4:
                continue
            x = 32 + c * 19 + (r % 2) * 9
            y = 52 + r * 24
            out.append(personne(x, y, 0.42, "ia" if (r, c) == (1, 2) else ("iw" if (r + c) % 2 else "ic")))
    return out


@dessin("foule")
def _():
    out = [L(16, 100, 144, 100)]
    for r in range(4):
        for c in range(12):
            x = 22 + c * 10.5 + (r % 2) * 5
            y = 48 + r * 14
            out.append(C(x, y, 3.6, "af" if (r, c) in ((1, 5), (2, 8)) else ("iw" if (r + c) % 3 else "ic")))
    return out


@dessin("hote")
def _():
    return [sol(70, 104, 50), R(36, 52, 52, 48, "ic"), PG([(30, 54), (62, 28), (94, 54)], "iw"),
            R(50, 66, 24, 18, "ia", 2), P("M104,46 Q116,36 128,46", "a"), P("M98,38 Q116,22 134,38", "t"), personne(120, 100, 0.5, "iw"), personne(140, 100, 0.5, "ic")]


@dessin("serveur")
def _():
    out = [sol(80, 106, 36), R(50, 14, 60, 90, "ic", 3)]
    for i in range(4):
        y = 22 + i * 20
        out += [R(56, y, 48, 14, "iw", 2), C(96, y + 7, 2.5, "af" if i % 2 == 0 else "f"), L(62, y + 7, 84, y + 7, "t")]
    return out


@dessin("nuage")
def _():
    return [nuage(80, 52, 1.6, "ic"), L(64, 74, 64, 102, "i"), PL([(58, 80), (64, 74), (70, 80)]), L(96, 74, 96, 102, "a"), PL([(90, 96), (96, 102), (102, 96)], "a")]


@dessin("plan")
def _():
    out = [R(22, 18, 116, 84, "iw", 2)]
    for i in range(1, 7):
        out.append(L(22 + i * 16.5, 18, 22 + i * 16.5, 102, "t"))
    out += [R(40, 34, 50, 40, "ic"), L(40, 54, 70, 54), L(70, 34, 70, 74), R(96, 56, 26, 30, "ic"), C(114, 34, 8, "ia"), L(114, 26, 114, 42, "t"), L(106, 34, 122, 34, "t")]
    return out


@dessin("prototype")
def _():
    return [sol(80, 104, 40), P("M80,22 L114,40 L114,78 L80,96 L46,78 L46,40 Z", "d"), L(80, 22, 80, 58, "d"), L(46, 40, 80, 58, "d"), L(114, 40, 80, 58, "d"),
            L(46, 40, 80, 22, "i"), L(80, 22, 114, 40, "i"), L(46, 78, 80, 96, "i"), L(80, 96, 114, 78, "i"),
            L(122, 42, 122, 78, "a"), L(118, 42, 126, 42, "a"), L(118, 78, 126, 78, "a")]


# --- monétisation
@dessin("cadeau")
def _():
    return [sol(80, 104, 40), R(44, 50, 72, 50, "ic", 2), R(40, 40, 80, 14, "iw", 2), R(74, 40, 12, 60, "ia"),
            P("M80,40 Q60,18 56,32 Q54,42 80,40 Z", "ia"), P("M80,40 Q100,18 104,32 Q106,42 80,40 Z", "ia")]


@dessin("etiquette_prix")
def _():
    return [sol(80, 104, 40), P("M42,40 L96,40 L120,64 L96,88 L42,88 Z", "ic"), C(102, 64, 5, "ic"), E(66, 64, 14, 14, "ia"), E(66, 64, 8, 8, "t")]


@dessin("gemme")
def _():
    return [sol(80, 104, 34), PG([(56, 40), (104, 40), (122, 58), (80, 100), (38, 58)], "ia"), L(38, 58, 122, 58), PL([(56, 40), (66, 58), (80, 100), (94, 58), (104, 40)], "t"),
            L(66, 58, 80, 40, "t"), L(94, 58, 80, 40, "t"), PG([(62, 44), (70, 44), (64, 54)], "ic")]


@dessin("chapeau_dons")
def _():
    return [E(80, 96, 50, 8, "iw"), P("M50,96 L54,60 Q80,52 106,60 L110,96 Z", "ic"), E(80, 60, 26, 6, "f"), R(52, 84, 56, 8, "ia"),
            C(70, 40, 7, "ia"), C(92, 30, 6, "ic"), C(84, 48, 5, "ic")]


@dessin("stand")
def _():
    out = [sol(80, 104, 50), R(36, 66, 88, 34, "ic", 2), L(40, 40, 40, 66), L(120, 40, 120, 66)]
    for i in range(5):
        out.append(P("M%s,30 h17.6 v12 a8.8,8.8 0 0 1 -17.6,0 Z" % n(36 + i * 17.6), "ia" if i % 2 == 0 else "ic"))
    out += [R(50, 58, 16, 8, "iw"), R(72, 56, 14, 10, "ic"), R(94, 58, 18, 8, "iw")]
    return out


@dessin("vitrine")
def _():
    out = [sol(80, 104, 52), R(24, 18, 112, 84, "ic", 3), R(24, 18, 112, 14, "iw", 3), L(30, 58, 130, 58), L(30, 86, 130, 86)]
    for i, c in enumerate(("iw", "ia", "ic", "iw", "ic")):
        out.append(R(34 + i * 19, 40, 14, 18, c, 1))
        out.append(R(34 + i * 19, 68, 14, 18, "ic" if i % 2 else "iw", 1))
    return out


@dessin("chapeau")
def _():
    return [sol(80, 104, 40), E(80, 88, 46, 10, "iw"), P("M56,88 L58,36 Q80,30 102,36 L104,88 Z", "ic"), E(80, 36, 22, 5, "ic"), R(57, 70, 46, 10, "ia")]


@dessin("fauteuil")
def _():
    return [sol(80, 106, 44), P("M50,74 V36 Q50,26 60,26 H100 Q110,26 110,36 V74 Z", "ia"), R(36, 60, 18, 36, "ic", 6), R(106, 60, 18, 36, "ic", 6),
            R(52, 74, 56, 16, "ic", 4), L(46, 96, 46, 104), L(114, 96, 114, 104)]


def prix_(k):
    out = [sol(80, 104, 20 + k * 12)]
    x0 = 80 - (k - 1) * 15
    for j in range(k):
        for i in range(2 + j * 2):
            haut = i == 1 + j * 2
            out.append(E(x0 + j * 30, 96 - i * 9, 14, 6, "ia" if haut and j == k - 1 else "ic"))
    return out


@dessin("prix_1")
def _():
    return prix_(1)


@dessin("prix_2")
def _():
    return prix_(2)


@dessin("prix_3")
def _():
    return prix_(3)


@dessin("prix_4")
def _():
    return prix_(4)


# --- ambition
@dessin("boite_petite")
def _():
    return [sol(80, 104, 50), cube_iso(80, 96 - 18, 12, "ia", "iw", "ic"), cube_iso(110, 40, 30, "d", "d", "d")]


@dessin("boite_moyenne")
def _():
    return [sol(80, 104, 50), cube_iso(80, 100 - 36, 24, "ia", "iw", "ic")]


@dessin("boite_grande")
def _():
    return [sol(80, 104, 54), cube_iso(80, 102 - 58, 38, "ia", "iw", "ic")]


@dessin("lune_soir")
def _():
    return [lune(116, 34, 16, "ia"), etoile(40, 26, 4, "f"), etoile(76, 18, 3, "f"), R(36, 54, 56, 46, "ic"), PG([(30, 56), (64, 30), (98, 56)], "iw"),
            R(52, 66, 18, 16, "ia"), L(61, 66, 61, 82, "t"), L(52, 74, 70, 74, "t")]


@dessin("equipe")
def _():
    return [sol(80, 104, 58), personne(36, 100, 0.8, "iw"), personne(124, 100, 0.8, "iw"), personne(62, 100, 0.95, "ic"), personne(98, 100, 0.95, "ia")]


# --- IA et outils
@dessin("image")
def _():
    return [R(26, 20, 108, 80, "iw", 3), R(34, 28, 92, 64, "ic", 2), montagne(66, 92, 56, 40, "iw"), montagne(102, 92, 50, 26, "w"), C(108, 44, 8, "ia")]


@dessin("modele_3d")
def _():
    out = [sol(80, 104, 40)]
    r = 34
    out.append(C(80, 60, r, "ic"))
    for k in (0.35, 0.75):
        out.append(E(80, 60, r * k, r, "t"))
    for y in (-0.6, 0, 0.6):
        out.append(E(80, 60 + y * r, r * math.sqrt(1 - y * y), r * 0.18 * math.sqrt(1 - y * y), "t"))
    for (x, y) in ((80, 26), (80, 94), (46, 60), (114, 60), (68, 40), (92, 80)):
        out.append(C(x, y, 3, "af"))
    return out


@dessin("onde")
def _():
    out = [L(16, 60, 144, 60, "t")]
    for i, h in enumerate((6, 14, 24, 38, 30, 18, 42, 28, 12, 22, 34, 16, 8)):
        x = 26 + i * 9
        out.append(L(x, 60 - h / 2 - 4, x, 60 + h / 2 + 4, "a" if 5 <= i <= 7 else "i"))
    return out


@dessin("interdit")
def _():
    return [C(80, 60, 36, "ic"), C(80, 60, 36, "a").replace('class="a"', 'class="a" style="stroke-width:6"'), L(56, 84, 104, 36, "a").replace('class="a"', 'class="a" style="stroke-width:6"')]


@dessin("loupe")
def _():
    return [R(24, 22, 74, 80, "ic", 2), L(32, 36, 86, 36, "t"), L(32, 48, 80, 48, "t"), L(32, 60, 86, 60, "t"), L(32, 72, 72, 72, "t"), L(32, 84, 82, 84, "t"),
            C(92, 56, 22, "iw"), C(92, 56, 22, "i"), L(108, 72, 132, 98), L(108, 72, 132, 98, "a").replace('class="a"', 'class="a" style="stroke-width:6"')]


@dessin("valide")
def _():
    return [sol(80, 104, 30), C(80, 58, 36, "ic"), PL([(60, 60), (74, 74), (102, 42)], "a").replace('class="a"', 'class="a" style="stroke-width:7"')]


@dessin("croquis")
def _():
    return [R(22, 20, 96, 80, "ic", 2), P("M36,82 Q40,54 62,52 Q82,50 86,78", "t"), P("M38,84 Q42,56 64,54 Q84,52 88,80", "t"),
            C(62, 42, 8, "t"), L(32, 86, 96, 86, "d"), crayon(142, 44, 112, 76)]


@dessin("modelage")
def _():
    return [sol(70, 104, 40), cube_iso(68, 44, 26, "ic", "iw", "ic"), L(68, 70, 68, 22, "i"), PL([(64, 28), (68, 20), (72, 28)]),
            L(68, 70, 118, 92, "a"), PL([(110, 94), (120, 93), (114, 85)], "a"), L(68, 70, 26, 94, "t"), C(68, 70, 4, "f")]


def jauge(f):
    a = math.radians(180 + 180 * f)
    return [sol(80, 100, 44), P("M28,84 A52,52 0 0 1 132,84 Z", "ic"), P("M36,84 A44,44 0 0 1 124,84", "t"),
            P("M%s,%s A44,44 0 0 1 124,84" % (n(80 + 44 * math.cos(math.radians(-30))), n(84 + 44 * math.sin(math.radians(-30)))), "a"),
            L(80, 84, 80 + 38 * math.cos(a), 84 + 38 * math.sin(a)), C(80, 84, 5, "f"), L(24, 84, 136, 84)]


@dessin("jauge_basse")
def _():
    return jauge(0.15)


@dessin("jauge_moyenne")
def _():
    return jauge(0.5)


@dessin("jauge_haute")
def _():
    return jauge(0.88)


@dessin("plafond")
def _():
    return [L(24, 100, 136, 100), R(34, 70, 18, 30, "iw"), R(60, 54, 18, 46, "iw"), R(86, 44, 18, 56, "ic"), R(112, 62, 18, 38, "iw"),
            L(24, 40, 136, 40, "a"), L(24, 40, 136, 40, "d")]


@dessin("demander")
def _():
    return [bulle(36, 18, 88, 66, "ic"), P("M68,42 Q68,30 80,30 Q92,30 92,42 Q92,50 80,54 L80,62", "a"), C(80, 72, 3, "af")]


def essai(nb):
    out = [C(66, 62, 34, "ic"), C(66, 62, 22, "iw"), C(66, 62, 10, "ic")]
    for k in range(nb):
        y = 62 - k * 14 + (nb - 1) * 7
        out += [L(66 + k * 4, y, 134, y - 28), PL([(126, y - 34), (134, y - 28), (128, y - 20)], "a" if k == 0 else "i")]
    return out


@dessin("essai_un")
def _():
    return essai(1)


@dessin("essai_deux")
def _():
    return essai(2)


@dessin("jalons")
def _():
    out = [P("M14,100 Q50,92 70,74 Q90,56 146,52", "i")]
    for i, (x, y) in enumerate(((34, 96), (62, 80), (90, 60), (116, 54))):
        out += [L(x, y, x, y - 18), R(x - 6, y - 26, 12, 9, "iw", 1)]
    out += [L(140, 52, 140, 22), PG([(140, 22), (154, 27), (140, 32)], "ia")]
    return out


@dessin("jalons_courts")
def _():
    return [P("M20,96 Q70,90 136,56", "i"), L(64, 88, 64, 68), R(58, 60, 12, 9, "iw", 1), L(132, 58, 132, 26), PG([(132, 26), (148, 31), (132, 36)], "ia")]


@dessin("engrenages")
def _():
    return [engrenage(62, 64, 30, 10, "iw"), engrenage(108, 42, 22, 8, "ia")]


@dessin("feu_vert")
def _():
    return [sol(80, 106, 20), L(80, 96, 80, 106), R(62, 14, 36, 82, "ic", 10), C(80, 30, 9, "iw"), C(80, 55, 9, "iw"), C(80, 80, 9, "ia")]


@dessin("coche")
def _():
    out = [R(34, 16, 92, 88, "ic", 3)]
    for i in range(3):
        y = 34 + i * 24
        out += [R(44, y - 7, 14, 14, "t", 2), PL([(46, y), (50, y + 5), (58, y - 6)], "a"), L(66, y, 112, y, "t")]
    return out


@dessin("dossier_ignore")
def _():
    return [sol(80, 104, 46), P("M34,30 v66 h92 v-58 h-58 l-6,-8 h-28 Z", "d"), dossier(48, 48, 64, 44, "iw"), L(52, 96, 108, 44, "a")]


@dessin("disque")
def _():
    return [sol(80, 104, 46), R(30, 30, 100, 64, "ic", 4), C(66, 62, 22, "iw"), C(66, 62, 6, "ic"), L(66, 62, 104, 46), C(104, 46, 3, "f"),
            C(116, 84, 3, "af"), L(36, 36, 40, 36, "t")]


# --- assistant
@dessin("badge")
def _():
    return [L(80, 14, 80, 30, "t"), R(46, 30, 68, 70, "ic", 6), R(70, 34, 20, 6, "iw", 2), C(80, 58, 12, "ia"), L(60, 82, 100, 82, "i"), L(64, 90, 96, 90, "t")]


@dessin("trousseau")
def _():
    out = [C(80, 32, 14, "i")]
    for i, ang in enumerate((-40, 0, 40)):
        out.append(G([L(0, 0, 0, 44), C(0, 50, 7, "ia" if i == 1 else "ic"), L(0, 30, 6, 30), L(0, 36, 5, 36)], "translate(80 44) rotate(%d)" % ang))
    return out


@dessin("acolyte")
def _():
    return [etoile(66, 56, 32, "ic"), etoile(118, 36, 13, "ia"), P("M96,44 Q104,52 102,60", "d"), C(58, 52, 3, "f"), C(74, 52, 3, "f"), P("M58,64 Q66,70 74,64", "i")]


@dessin("noeud_papillon")
def _():
    return [sol(80, 100, 40), P("M80,60 L34,36 Q26,60 34,84 Z", "ia"), P("M80,60 L126,36 Q134,60 126,84 Z", "ia"), R(70, 48, 20, 24, "ic", 5),
            L(44, 50, 56, 56, "t"), L(116, 50, 104, 56, "t")]


@dessin("humain")
def _():
    return [sol(80, 106, 30), P("M48,104 Q48,72 80,72 Q112,72 112,104 Z", "ia"), C(80, 46, 20, "ic"), P("M60,44 Q62,24 80,24 Q100,24 100,44 Q90,34 76,36 Q66,36 60,44 Z", "iw"),
            C(73, 48, 2, "f"), C(87, 48, 2, "f"), P("M74,56 Q80,60 86,56", "i")]


@dessin("robot")
def _():
    return [sol(80, 106, 30), L(80, 14, 80, 24), C(80, 12, 4, "ia"), R(56, 24, 48, 36, "ic", 8), R(62, 32, 36, 18, "iw", 4), C(72, 41, 4, "af"), C(88, 41, 4, "af"),
            R(52, 64, 56, 38, "ic", 6), R(66, 72, 28, 14, "iw", 2), L(52, 72, 40, 90), L(108, 72, 120, 90)]


@dessin("animal")
def _():
    return [sol(80, 106, 30), PG([(48, 30), (62, 56), (52, 64)], "ia"), PG([(112, 30), (98, 56), (108, 64)], "ia"),
            P("M48,58 Q50,40 80,40 Q110,40 112,58 Q114,74 80,98 Q46,74 48,58 Z", "ic"), P("M62,72 Q80,66 98,72 Q90,90 80,98 Q70,90 62,72 Z", "iw"),
            C(68, 60, 3, "f"), C(92, 60, 3, "f"), C(80, 88, 4, "f")]


@dessin("fantome")
def _():
    return [E(80, 104, 30, 4, "w"), P("M50,98 V54 Q50,24 80,24 Q110,24 110,54 V98 L100,90 L90,98 L80,90 L70,98 L60,90 Z", "ic"),
            E(70, 54, 5, 7, "f"), E(90, 54, 5, 7, "f"), E(80, 72, 5, 6, "ia")]


def visage(yeux, bouche, extra=()):
    return [sol(80, 106, 30), C(80, 60, 36, "ic")] + list(yeux) + list(bouche) + list(extra)


@dessin("espiegle")
def _():
    return visage([C(66, 52, 3.5, "f"), P("M88,52 Q94,46 100,52", "i")], [P("M62,68 Q80,86 98,68", "i"), P("M82,76 Q86,88 92,78", "ia")],
                  [P("M58,42 L72,38", "t"), P("M88,40 L102,42", "t")])


@dessin("serieux")
def _():
    return visage([C(66, 54, 8, "t"), C(94, 54, 8, "t"), L(74, 54, 86, 54, "t"), C(66, 54, 2.5, "f"), C(94, 54, 2.5, "f")], [L(68, 76, 92, 76)],
                  [R(52, 86, 56, 10, "ia", 3)])


@dessin("sarcastique")
def _():
    return visage([C(66, 56, 3, "f"), C(94, 54, 3, "f")], [P("M66,76 Q82,78 96,68", "i")], [L(58, 48, 74, 48), P("M86,40 Q94,36 102,42", "a")])


@dessin("zen")
def _():
    return [sol(80, 104, 46), P("M40,100 Q44,84 62,82 L98,82 Q116,84 120,100 Z", "iw"), P("M66,82 Q64,58 80,56 Q96,58 94,82 Z", "ic"), C(80, 44, 11, "ic"),
            P("M74,44 Q76,46 78,44", "t"), P("M82,44 Q84,46 86,44", "t"), P("M66,70 Q56,78 60,84", "i"), P("M94,70 Q104,78 100,84", "i"),
            P("M80,22 Q86,28 80,32 Q74,28 80,22 Z", "ia")]


@dessin("sourire")
def _():
    return visage([C(68, 52, 3.5, "f"), C(92, 52, 3.5, "f")], [P("M62,68 Q80,84 98,68", "a")])


@dessin("absurde")
def _():
    return [sol(80, 104, 40), P("M36,64 Q60,40 96,60 Q60,84 36,64 Z", "ic"), PG([(96, 60), (122, 44), (118, 60), (122, 78)], "iw"), C(50, 60, 3, "f"),
            P("M40,52 L42,30 L66,30 L64,52", "ic"), R(38, 50, 30, 6, "ia"), L(60, 68, 72, 64, "t")]


@dessin("geek")
def _():
    return visage([C(66, 54, 11, "ic"), C(94, 54, 11, "ic"), L(77, 54, 83, 54), C(66, 54, 3, "f"), C(94, 54, 3, "f")],
                  [P("M70,76 Q80,82 90,76", "i")], [PL([(110, 22), (120, 30), (110, 38)], "a"), L(100, 40, 106, 20, "a")])


@dessin("cloche")
def _():
    return [sol(80, 106, 30), C(80, 18, 4, "f"), P("M54,84 Q56,42 80,32 Q104,42 106,84 Z", "ia"), R(46, 82, 68, 8, "iw", 4), C(80, 96, 6, "ic"),
            P("M40,40 Q34,52 38,64", "t"), P("M120,40 Q126,52 122,64", "t")]


def freq(minutes):
    if minutes <= 60:
        return [sol(80, 104, 30), horloge(80, 58, 38, minutes)]
    return [sol(80, 104, 50), horloge(52, 60, 26, 60), horloge(108, 60, 26, 60)]


@dessin("freq_15")
def _():
    return freq(15)


@dessin("freq_30")
def _():
    return freq(30)


@dessin("freq_60")
def _():
    return freq(60)


@dessin("freq_120")
def _():
    return freq(120)


@dessin("jumeaux")
def _():
    return [sol(80, 104, 46), personne(58, 100, 1.05, "ia"), personne(102, 100, 1.05, "ia"), L(80, 44, 80, 92, "d")]


@dessin("palette")
def _():
    return [P("M80,20 Q130,20 134,58 Q136,90 104,96 Q90,98 92,84 Q94,74 82,76 Q70,78 66,92 Q60,102 44,96 Q22,86 28,56 Q36,20 80,20 Z", "ic"),
            C(58, 44, 7, "ia"), C(82, 36, 7, "iw"), C(106, 46, 7, "f"), C(112, 70, 7, "ic"), E(48, 72, 6, 5, "ic")]


@dessin("gomme")
def _():
    return [L(20, 84, 60, 84, "i"), L(60, 84, 98, 84, "d"), G([R(-24, -12, 48, 24, "ic", 3), R(-24, -12, 18, 24, "ia", 3)], "translate(100 62) rotate(-30)")]




# ------------------------------------------------------------ sortie
def svg(nom):
    _NOM[0] = nom
    corps = "".join(x for x in DESSINS[nom]() if x)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 120" width="160" height="120" role="img" aria-label="%s">\n'
        '<defs><pattern id="h-%s" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        '<line x1="0" y1="0" x2="0" y2="4" stroke="%s" stroke-width="1" stroke-opacity=".5"/></pattern>'
        '<style>%s</style></defs>\n'
        '<rect x="1" y="1" width="158" height="118" rx="10" fill="%s"/>'
        '<ellipse cx="80" cy="62" rx="62" ry="46" fill="%s" fill-opacity=".045"/>'
        '<rect x="5" y="5" width="150" height="110" rx="7" fill="none" stroke="%s" stroke-opacity=".28" stroke-width=".8"/>\n'
        '%s\n</svg>\n' % (nom, nom, ENCRE, STYLE, PAPIER, ENCRE, ENCRE, corps))


def illustrations_demandees():
    sys.path.insert(0, ICI)
    import construire_questions as cq
    return cq.illustrations()


if __name__ == "__main__":
    voulues = illustrations_demandees()
    manquants = [v for v in voulues if v not in DESSINS]
    if manquants:
        print("Dessins manquants :", " ".join(manquants))
        sys.exit(1)
    if "--verifier" in sys.argv:
        print("OK : %d dessins pour %d illustrations demandées" % (len(DESSINS), len(voulues)))
        sys.exit(0)
    os.makedirs(SORTIE, exist_ok=True)
    for f in os.listdir(SORTIE):
        if f.endswith(".svg") and f[:-4] not in voulues:
            os.remove(os.path.join(SORTIE, f))
    for nom in voulues:
        with open(os.path.join(SORTIE, nom + ".svg"), "w", encoding="utf-8", newline="\n") as f:
            f.write(svg(nom))
    print("%d illustrations écrites dans %s" % (len(voulues), SORTIE))
