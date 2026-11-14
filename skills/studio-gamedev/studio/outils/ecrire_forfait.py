#!/usr/bin/env python3
"""Écrit <projet>/.studio/forfait.json (barre « Forfait Claude » de l'en-tête du studio). Facultatif.
Writes <project>/.studio/forfait.json (the optional "Claude plan" bar in the studio header).

Le studio ne lit pas tout seul l'usage du forfait : rien dans Claude Code ne le donne à un script.
Ce fichier s'écrit donc avec les chiffres lus ailleurs : écran /usage de Claude Code, page d'usage du
compte, ou un outil d'usage que ton hôte fournit à l'assistant. Sans ce fichier, la barre reste cachée.
The studio cannot read plan usage by itself: write the figures you read elsewhere (Claude Code /usage,
the account usage page, or a usage tool your host gives the assistant). Without the file the bar stays hidden.

Exemples / examples :
  python ecrire_forfait.py --projet . --fenetre "Session (5 h)" 42 2026-11-13T21:00 --fenetre "Semaine" 18 2026-11-17T09:00
  python ecrire_forfait.py --projet . --fenetre "Session" 42 +3h20 --source "à la main toutes les 30 min" --offre Max
  python ecrire_forfait.py --projet . --effacer        (retire le fichier : la barre se cache)

--fenetre NOM PCT_UTILISE REMISE : PCT_UTILISE de 0 à 100 ; REMISE = date ISO (heure locale si sans fuseau),
ou +2h30 / +45m / +1j (dans combien de temps), ou « - » si inconnue.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

if os.path.dirname(os.path.dirname(os.path.abspath(__file__))) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import jsonio  # noqa: E402  (C4 : studio/jsonio.py, lecture avec BOM, écriture atomique communes)
for _flux in (sys.stdout, sys.stderr):                 # G16 : sortie en UTF-8, même redirigée (Windows, cp1252)
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def remise(txt):
    txt = str(txt).strip()
    if txt in ("", "-", "?"):
        return None
    m = re.fullmatch(r"\+(?:(\d+)\s*[jd])?\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*(?:m(?:in)?)?)?", txt, re.I)
    if m and any(m.groups()):
        j, h, mi = (int(x or 0) for x in m.groups())
        return (dt.datetime.now().astimezone() + dt.timedelta(days=j, hours=h, minutes=mi)).isoformat(timespec="seconds")
    try:
        d = dt.datetime.fromisoformat(txt)
    except ValueError:
        raise SystemExit(f"Remise à zéro illisible / unreadable reset: {txt!r} (ISO, +2h30, +45m, +1j ou -)")
    if d.tzinfo is None:
        d = d.astimezone()
    return d.isoformat(timespec="seconds")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--projet", default=".", help="dossier du projet (contient .studio/)")
    ap.add_argument("--fenetre", nargs=3, action="append", metavar=("NOM", "PCT_UTILISE", "REMISE"), default=[])
    ap.add_argument("--source", default="", help="d'où viennent les chiffres et leur cadence, ex. « /usage toutes les 10 min »")
    ap.add_argument("--offre", default="", help="nom de l'offre (facultatif)")
    ap.add_argument("--supplementaire", choices=["actif", "inactif"], help="usage supplémentaire activé ou non")
    ap.add_argument("--depense", help="montant dépensé en usage supplémentaire")
    ap.add_argument("--devise", default="EUR")
    ap.add_argument("--effacer", action="store_true", help="supprime forfait.json (barre cachée)")
    a = ap.parse_args(argv)
    dossier = os.path.join(os.path.abspath(a.projet), ".studio")
    cible = os.path.join(dossier, "forfait.json")
    if a.effacer:
        if os.path.exists(cible):
            os.remove(cible)
        print("forfait.json retiré / removed")
        return 0
    if not a.fenetre:
        ap.error("au moins une --fenetre / at least one --fenetre")
    fen = []
    for nom, pct, rz in a.fenetre:
        try:
            p = float(str(pct).replace(",", "."))
        except ValueError:
            raise SystemExit(f"Pourcentage illisible / unreadable percentage: {pct!r}")
        if not 0 <= p <= 100:
            raise SystemExit(f"Pourcentage hors de 0-100 / out of range: {p}")
        f = {"nom": nom.strip() or "Fenêtre", "pct_utilise": round(p, 1)}
        r = remise(rz)
        if r:
            f["remise_a_zero"] = r
        fen.append(f)
    d = {"maj": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "source": a.source or "ecrire_forfait.py", "fenetres": fen}
    if a.offre:
        d["offre"] = a.offre
    if a.supplementaire:
        d["usage_supplementaire"] = {"actif": a.supplementaire == "actif"}
        if a.depense:
            d["usage_supplementaire"].update(depense=a.depense, devise=a.devise)
    jsonio.ecrire(cible, d)   # écriture atomique : le studio ne lit jamais un fichier à moitié écrit
    print(cible)
    return 0


if __name__ == "__main__":
    sys.exit(main())
