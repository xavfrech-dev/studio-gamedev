"""Essai du placement des bureaux du studio (bibliothèque standard, sans navigateur).

Usage : python -I -B essai_bureaux.py

Lit le plan de la page (studio.html, entre « PLAN-DEBUT » et « PLAN-FIN ») et l'emprise du mobilier des paliers
(paliers.js, entre « EMPRISES-DEBUT » et « EMPRISES-FIN »), puis vérifie, à chacun des 5 paliers et pour 1 à 12 postes :
- chaque bureau (plateau + chaise) reste dans la pièce, ne touche aucun autre bureau, aucun meuble, aucune plante,
  aucun tapis, aucun passage (porte, accueil de l'assistant, allées) ;
- chaque point où un perso se tient autour d'un bureau (POINTS_BUREAU : debout à côté, en attente, visite de
  l'assistant, tournée de l'assistant) ne touche ni un meuble ni un autre bureau, ni le plateau ou la chaise du sien ;
- la page n'a jamais plus de postes que de bureaux (NB_BUREAUX = nombre de SLOTS) ;
- les coins de loisir des persos libres ne touchent ni un meuble ni un bureau ;
- les bureaux sont alignés : trois rangées sur trois colonnes, ou contre le mur du fond ; dans les rangées du milieu et de
  devant, jamais un bureau seul au centre (le milieu ne se remplit qu'après la gauche et la droite).
Sortie : « OK » ou la liste des chevauchements ; code de retour 1 en cas d'échec.
Les tables d'emprise décrivent le décor ; le contrôle sur l'image réellement dessinée (chaque boîte et chaque tapis
relevés pendant le dessin, étiquettes des postes comprises) se fait dans le navigateur : window.__bureauxEssai().
"""
import argparse
import json
import os
import re
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(ICI)
sys.dont_write_bytecode = True
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
W, H = 16.0, 12.0
R_PERSO = 0.25


def bloc(chemin, debut, fin):
    s = open(chemin, encoding="utf-8").read()
    i, j = s.index(debut), s.index(fin)
    return s[i:j]


def tableau(txt, nom):
    m = re.search(r"const " + nom + r"\s*=\s*(\[.*?\]|\{.*?\});\s*(?://|\n)", txt, re.S)
    if not m:
        raise SystemExit(f"{nom} introuvable")
    return json.loads(m.group(1))


BUREAU = None   # emprise d'un bureau : lue dans la page (EMPRISE_BUREAU) par main(), jamais recopiée ici


def parties_bureau(sx, sy):
    return [(sx + r[0], sy + r[1], sx + r[2], sy + r[3]) for r in BUREAU.values()]


def rect_bureau(sx, sy):
    l = parties_bureau(sx, sy)
    return (min(r[0] for r in l), min(r[1] for r in l), max(r[2] for r in l), max(r[3] for r in l))


def touche(a, b, marge=0.0):
    return a[0] < b[2] + marge and b[0] < a[2] + marge and a[1] < b[3] + marge and b[1] < a[3] + marge


def cercle_touche(cx, cy, r, b):
    dx = max(b[0] - cx, 0, cx - b[2])
    dy = max(b[1] - cy, 0, cy - b[3])
    return dx * dx + dy * dy < r * r


def main(argv=None):
    global STUDIO, BUREAU
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--studio", help="autre copie du studio (comparaison)")
    a = a.parse_args(argv)
    if a.studio:
        STUDIO = a.studio
    plan = bloc(os.path.join(STUDIO, "studio.html"), "PLAN-DEBUT", "PLAN-FIN")
    slots = tableau(plan, "SLOTS")
    page = tableau(plan, "EMPRISES_PAGE")
    loisirs = tableau(plan, "COINS_LOISIR")
    passages = tableau(plan, "PASSAGES")
    BUREAU = tableau(plan, "EMPRISE_BUREAU")
    points = tableau(plan, "POINTS_BUREAU")
    page_html = open(os.path.join(STUDIO, "studio.html"), encoding="utf-8").read()
    m = re.search(r"const NB_BUREAUX\s*=\s*(\d+)", page_html)
    meubles = tableau(bloc(os.path.join(STUDIO, "paliers.js"), "EMPRISES-DEBUT", "EMPRISES-FIN") + "\n", "EMPRISES")
    err = []
    if not m or int(m.group(1)) != len(slots):
        err.append(f"NB_BUREAUX ({m.group(1) if m else '?'}) différent du nombre de bureaux ({len(slots)})")
    for cle in ("debout", "attente", "visite", "tournee"):
        if cle not in points:
            err.append(f"POINTS_BUREAU sans « {cle} »")
    if len(slots) != 12:
        err.append(f"{len(slots)} bureaux au lieu de 12")
    rangs = sorted({y for _, y in slots if y > 1.5})
    colonnes = sorted({x for x, y in slots if y > 1.5})
    for x, y in slots:
        if y > 1.5 and (x not in colonnes or len(colonnes) != 3):
            err.append(f"bureau ({x}, {y}) hors des trois colonnes")
    for y in rangs:
        if sum(1 for _, yy in slots if yy == y) != 3:
            err.append(f"rangée y={y} incomplète")
    for p in range(1, 6):
        actifs = [e for e in meubles + page if e["de"] <= p <= e["a"]]
        durs = [e for e in actifs if not e.get("tapis")]
        for n in range(1, len(slots) + 1):
            pris = slots[:n]
            rects = [rect_bureau(x, y) for x, y in pris]
            for i, ((x, y), r) in enumerate(zip(pris, rects)):
                nom = f"palier {p}, {n} postes, bureau {i + 1} ({x}, {y})"
                if r[0] < 0.2 or r[1] < 0.2 or r[2] > W - 0.2 or r[3] > H - 0.2:
                    err.append(nom + " : sort de la pièce")
                for j in range(i + 1, len(rects)):
                    if touche(r, rects[j], 0.3):
                        err.append(nom + f" : touche le bureau {j + 1}")
                for e in actifs:
                    if touche(r, e["r"]):
                        err.append(nom + " : touche " + e["id"])
                for e in passages:
                    if touche(r, e["r"]):
                        err.append(nom + " : sur le passage " + e["id"])
                for quoi, (dx, dy) in points.items():
                    px, py = x + dx, y + dy
                    for e in durs:
                        if cercle_touche(px, py, R_PERSO, e["r"]):
                            err.append(nom + f" : point « {quoi} » dans " + e["id"])
                    for e in passages:
                        if quoi in ("debout", "attente") and cercle_touche(px, py, R_PERSO, e["r"]):
                            err.append(nom + f" : point « {quoi} » sur le passage " + e["id"])
                    for j, r2 in enumerate(rects):
                        zones = parties_bureau(*pris[j]) if j == i else [r2]   # son propre bureau : plateau et chaise
                        if any(cercle_touche(px, py, R_PERSO, z) for z in zones):
                            err.append(nom + f" : point « {quoi} » dans le bureau {j + 1}")
            for c in loisirs:
                if not (c["de"] <= p <= c["a"]):
                    continue
                for e in durs:
                    if cercle_touche(c["gx"], c["gy"], R_PERSO, e["r"]):
                        err.append(f"palier {p} : coin {c['cle']} dans {e['id']}")
                for j, r2 in enumerate(rects):
                    if cercle_touche(c["gx"], c["gy"], R_PERSO, r2):
                        err.append(f"palier {p}, {n} postes : coin {c['cle']} dans le bureau {j + 1}")
            for y in rangs[1:]:                 # rangées du milieu et de devant : pas de bureau seul au centre
                xs = sorted(x for x, yy in pris if yy == y)
                if colonnes[1] in xs and not (colonnes[0] in xs and colonnes[2] in xs):
                    err.append(f"{n} postes : rangée y={y} avec un bureau seul au milieu")
            fond = [x for x, y in pris if y <= 1.5]
            if fond and n <= 9:
                err.append(f"{n} postes : bureau contre le fond avant que les rangées soient pleines")
    # bureau de l'auditeur (facultatif) : posé en plus des 12, il ne touche rien, à tous les paliers et avec 12 postes
    aud = None
    if "SLOT_AUDITEUR" in plan:
        aud = tableau(plan, "SLOT_AUDITEUR")
        ax, ay = aud
        ra = rect_bureau(ax, ay)
        if ra[0] < 0.2 or ra[1] < 0.2 or ra[2] > W - 0.2 or ra[3] > H - 0.2:
            err.append("bureau de l'auditeur : sort de la pièce")
        for i, (x, y) in enumerate(slots):
            if touche(ra, rect_bureau(x, y), 0.3):
                err.append(f"bureau de l'auditeur : touche le bureau {i + 1}")
        for p in range(1, 6):
            actifs = [e for e in meubles + page if e["de"] <= p <= e["a"]]
            for e in actifs:
                if touche(ra, e["r"]):
                    err.append(f"palier {p} : bureau de l'auditeur touche " + e["id"])
            for e in passages:
                if touche(ra, e["r"]):
                    err.append("bureau de l'auditeur sur le passage " + e["id"])
            for quoi, (dx, dy) in points.items():
                px, py = ax + dx, ay + dy
                if px + R_PERSO > W - 0.05 or py + R_PERSO > H - 0.05:
                    err.append(f"bureau de l'auditeur : point « {quoi} » contre le mur")
                for e in actifs:
                    if not e.get("tapis") and cercle_touche(px, py, R_PERSO, e["r"]):
                        err.append(f"palier {p} : point « {quoi} » de l'auditeur dans " + e["id"])
                for i, (x, y) in enumerate(slots):
                    if cercle_touche(px, py, R_PERSO, rect_bureau(x, y)):
                        err.append(f"point « {quoi} » de l'auditeur dans le bureau {i + 1}")
            for c in loisirs:
                if c["de"] <= p <= c["a"] and cercle_touche(c["gx"], c["gy"], R_PERSO, ra):
                    err.append(f"palier {p} : coin {c['cle']} dans le bureau de l'auditeur")
    err = sorted(set(err))
    if err:
        print("ÉCHEC :\n- " + "\n- ".join(err[:80]) + (f"\n… et {len(err) - 80} autres" if len(err) > 80 else ""))
        return 1
    print(f"OK : {len(slots)} bureaux, 5 paliers, 1 à {len(slots)} postes : aucun chevauchement (meubles, plantes, tapis, passages, "
          f"coins de loisir, {len(points)} points autour des bureaux), rangées alignées"
          + (f" ; bureau de l'auditeur ({aud[0]}, {aud[1]}) libre aussi" if aud else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
