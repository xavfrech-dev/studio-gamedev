"""Fil résumé de la session : <projet>/FIL.md (une ligne par message ou réponse traités).

Pourquoi : chaque réveil de l'assistant relit toute la conversation. Avec FIL.md, une session neuve reprend le fil
en quelques lignes au lieu de traîner des centaines de milliers de jetons.

  python -I -B fil.py --projet <projet> ajouter "ce qui a été dit ou décidé — ce qui attend" [--heure HH:MM]
  python -I -B fil.py --projet <projet> lire
  python -I -B fil.py --projet <projet> entete "# Projet : …"     (remplace l'en-tête)

Format : en-tête (lignes qui commencent par #), puis une ligne par échange « HH:MM — texte ». Seules les
GARDE (40) dernières lignes d'échange sont gardées ; l'en-tête reste toujours. Écriture atomique.
Bibliothèque standard seulement ; n'écrit que FIL.md.
"""
import argparse
import datetime as dt
import os
import sys

for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

GARDE = 40
ENTETE_DEFAUT = ["# Fil du studio : une ligne par message ou réponse traités (heure — dit ou décidé — ce qui attend).",
                 "# À lire à chaque reprise ; l'en-tête reste, les 40 dernières lignes sont gardées."]


def lire(chemin):
    try:
        with open(chemin, encoding="utf-8-sig") as f:
            lignes = [l.rstrip("\r\n") for l in f]
    except OSError:
        return list(ENTETE_DEFAUT), []
    entete = [l for l in lignes if l.startswith("#")]
    corps = [l for l in lignes if l.strip() and not l.startswith("#")]
    return (entete or list(ENTETE_DEFAUT)), corps


def ecrire(chemin, entete, corps):
    corps = corps[-GARDE:]
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(entete + [""] + corps) + "\n")
    os.replace(tmp, chemin)
    return corps


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fil résumé FIL.md du studio.")
    ap.add_argument("--projet", required=True)
    sp = ap.add_subparsers(dest="cmd", required=True)
    a1 = sp.add_parser("ajouter")
    a1.add_argument("texte")
    a1.add_argument("--heure", default="")
    sp.add_parser("lire")
    a3 = sp.add_parser("entete")
    a3.add_argument("lignes", nargs="+")
    a = ap.parse_args(argv)
    projet = os.path.abspath(a.projet)
    if not os.path.isdir(projet):
        print("projet introuvable : " + projet, file=sys.stderr)
        return 2
    chemin = os.path.join(projet, "FIL.md")
    entete, corps = lire(chemin)
    if a.cmd == "lire":
        print("\n".join(entete + [""] + corps))
        return 0
    if a.cmd == "entete":
        entete = [l if l.startswith("#") else "# " + l for l in a.lignes]
        ecrire(chemin, entete, corps)
        return 0
    texte = " ".join(a.texte.split())[:400]
    if not texte:
        return 2
    heure = a.heure or dt.datetime.now().strftime("%H:%M")
    corps = ecrire(chemin, entete, corps + [f"{heure} — {texte}"])
    print(f"FIL.md : {len(corps)} ligne(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
