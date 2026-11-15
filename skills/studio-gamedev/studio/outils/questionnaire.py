# -*- coding: utf-8 -*-
"""Questionnaire adaptatif en repli conversation (sans la page) : la prochaine question, déjà orientée par les réponses.

Même logique que la page (studio.html, bloc ADAPTATION ; module studio/adaptation.py) : chaque réponse est écrite dans
<projet>/.studio/reponses_questionnaire.json ; les déductions (règles, mots du pitch) suivent ; une question tranchée ou
déduite n'est jamais reposée ; le titre est reformulé selon les choix faits ; un rappel court dit ce qui est acquis ;
relancé, il reprend à la première question non tranchée.

  python -I -B questionnaire.py suivante --projet <projet> [--langue fr|en]
        -> JSON : {question: {id, chapitre, type, titre (reformulé), aide, choix (cartes visibles), recommande}, acquis, deduites}
           ou {fin: true} ; applique d'abord les déductions au fichier.
  python -I -B questionnaire.py repondre --projet <projet> --cle <id> --valeur <v> [--json] [--source utilisateur|a_confirmer] [--via ecrit|clic|voix|passer]
        -> écrit la réponse (--json : valeur JSON, ex. '["pc","web"]'), applique les déductions, puis comme « suivante »
           (+ deduites_nouvelles : ce que cette réponse a permis de déduire).
  python -I -B questionnaire.py acquis --projet <projet>      -> le rappel « Déjà acquis » (JSON)

Le mode (rapide, complet, adoption) vient du fichier (champ mode, sinon accueil.mode) ; les clés « fixes » de
.studio/deductions.json ne sont ni posées ni déduites. Code 0 = bon, 2 = erreur d'usage. Python standard uniquement.
"""
import argparse
import json
import os
import sys
import time

for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
sys.dont_write_bytecode = True
STUDIO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if STUDIO not in sys.path:
    sys.path.insert(0, STUDIO)
import adaptation  # noqa: E402
import jsonio  # noqa: E402

SOURCES = ("utilisateur", "deduit", "a_confirmer", "voix_a_interpreter")
VIAS = ("clic", "ecrit", "voix", "passer")


def horodatage():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def charger(projet, langue=None):
    dossier = os.path.join(projet, ".studio")
    chemin = os.path.join(dossier, "reponses_questionnaire.json")
    rq = jsonio.lire(chemin, None)
    if not isinstance(rq, dict):
        rq = {"version": 1, "etat": "en_cours", "cree_le": horodatage(), "reponses": {}}
    if not isinstance(rq.get("reponses"), dict):
        rq["reponses"] = {}
    lg = langue or rq.get("langue") or "fr"
    lg = lg if lg in ("fr", "en") else "fr"
    rq.setdefault("langue", lg)
    qf = jsonio.lire(os.path.join(STUDIO, "questions.%s.json" % lg), None)
    if not isinstance(qf, dict):
        raise SystemExit("questions.%s.json illisible" % lg)
    ded = jsonio.lire(os.path.join(dossier, "deductions.json"), None)
    fixes = sorted((ded or {}).get("fixes") or {}) if isinstance(ded, dict) else []
    recs = (ded or {}).get("recommandes") or {} if isinstance(ded, dict) else {}
    return chemin, rq, qf, fixes, recs


def sauver(chemin, rq):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    rq["maj"] = horodatage()
    jsonio.ecrire(chemin, rq)


def presenter(qf, rq, fixes, recs):
    rep = rq["reponses"]
    mode = adaptation.mode_de(rq)
    q = adaptation.suivante(qf, rep, mode, fixes)
    deduites = sorted(k for k, r in rep.items() if isinstance(r, dict) and r.get("source") == "deduit")
    if not q or rq.get("etat") == "termine":
        return {"fin": True, "mode": mode, "acquis": adaptation.acquis(qf, rep), "deduites": deduites}
    out = {"id": q["id"], "chapitre": q.get("chapitre"), "type": q.get("type"),
           "titre": adaptation.titre(qf, q, rep), "aide": q.get("aide", "")}
    if q.get("choix"):
        out["choix"] = [{"id": c["id"], "libelle": c.get("libelle", c["id"])} for c in q["choix"]
                        if adaptation.cond(c.get("si"), rep)]
        r = recs.get(q["id"], q.get("recommande"))
        if r is not None:
            out["recommande"] = r
    return {"question": out, "mode": mode, "acquis": adaptation.acquis(qf, rep, sauf=q["id"]), "deduites": deduites}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Questionnaire adaptatif en repli conversation.")
    ap.add_argument("action", choices=("suivante", "repondre", "acquis"))
    ap.add_argument("--projet", required=True)
    ap.add_argument("--langue", choices=("fr", "en"))
    ap.add_argument("--cle")
    ap.add_argument("--valeur")
    ap.add_argument("--json", action="store_true", help="--valeur est du JSON")
    ap.add_argument("--source", default="utilisateur", choices=SOURCES)
    ap.add_argument("--via", default="ecrit", choices=VIAS)
    a = ap.parse_args(argv)
    chemin, rq, qf, fixes, recs = charger(a.projet, a.langue)
    nouvelles = {}
    if a.action == "repondre":
        if not a.cle or a.valeur is None:
            print("repondre demande --cle et --valeur", file=sys.stderr)
            return 2
        if not adaptation.question(qf, a.cle) and not a.cle.startswith("suivi-"):
            print("clé inconnue : %s" % a.cle, file=sys.stderr)
            return 2
        try:
            v = json.loads(a.valeur) if a.json else a.valeur
        except ValueError:
            print("--valeur n'est pas du JSON", file=sys.stderr)
            return 2
        rq["reponses"][a.cle] = {"valeur": v, "source": a.source, "via": a.via, "t": horodatage()}
        if a.cle == "accueil.mode" and v in ("rapide", "complet"):
            rq["mode"] = v
    ecrites, retirees = adaptation.appliquer(qf, rq, fixes, horodatage())
    if a.action == "repondre":
        nouvelles = {k: r["valeur"] for k, r in ecrites.items()}
    if a.action != "acquis" and (a.action == "repondre" or ecrites or retirees):
        sauver(chemin, rq)
    if a.action == "acquis":
        print(json.dumps(adaptation.acquis(qf, rq["reponses"], maxi=20), ensure_ascii=False, indent=1))
        return 0
    res = presenter(qf, rq, fixes, recs)
    if a.action == "repondre":
        res["deduites_nouvelles"] = nouvelles
        res["retirees"] = retirees
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
