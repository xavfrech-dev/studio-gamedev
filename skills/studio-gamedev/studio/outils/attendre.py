"""Attente économe : réveille Claude seulement quand la page du studio a écrit quelque chose.

Pourquoi : relire les fichiers toutes les 10 à 20 s coûte un tour de Claude à chaque fois (100 à 200 tours
pendant un questionnaire). Ce script attend tout seul, sans jetons, et ne rend la main qu'à un vrai changement.

Attente (questionnaire, demandes de la page) :
  python -I -B attendre.py --projet <projet> [--max 1800]
    Lance-le en arrière-plan (tu es prévenu à la fin) ; sans arrière-plan, garde --max sous le délai de l'outil (540).
    Code 0 + une ligne JSON : {"evenement": "changement", "fichiers": [{"f", "etat": nouveau|modifie|supprime}], "questionnaire": {…}}
    Code 3 : rien de neuf pendant --max secondes (relance-le, sans rien écrire dans la conversation).
    Un changement survenu entre deux attentes n'est jamais perdu : l'état vu est gardé dans .studio/attente.etat.json.

Point de suivi (avant chaque point programmé, sans attendre) :
  python -I -B attendre.py --projet <projet> --point
    Code 3 : rien n'a bougé depuis le dernier point (git, roadmap, progression, décisions, demandes) : pas de point,
    pas de message. Code 0 + une ligne JSON des changements : fais le point. État gardé dans .studio/point.etat.json.

Bibliothèque standard seulement ; lecture seule hors de ces deux fichiers d'état ; une seule commande fixe (git rev-parse).
"""
import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys
import time

sys.dont_write_bytecode = True

ATTENTE = ["reponses_questionnaire.json", "profil.json", "reponses.json", "reglages.json",
           "demandes_vocales/*.json", "demandes/*.json", "recrues/*.json"]
POINT = ["roadmap.json", "progression/*.json", "decisions.json", "reponses.json", "attentes.json",
         "demandes/*.json", "demandes_vocales/*.json"]
IGNORES = {"demandes/statuts.json"}      # écrit par Claude lui-même : ne réveille pas
PAS_S = 2.0
CALME_S = 3.0                            # une rafale d'écritures (dictée, clics) donne un seul réveil
CALME_MAX_S = 15.0


def lire_json(chemin, defaut):
    try:
        with open(chemin, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defaut


def empreintes(studio, motifs):
    out = {}
    for m in motifs:
        for p in glob.glob(os.path.join(studio, *m.split("/"))):
            rel = os.path.relpath(p, studio).replace("\\", "/")
            if rel in IGNORES or not os.path.isfile(p):
                continue
            try:
                with open(p, "rb") as f:
                    out[rel] = hashlib.sha1(f.read(2 * 1024 * 1024)).hexdigest()[:16]
            except OSError:
                continue
    return out


def tete_git(projet):
    try:
        r = subprocess.run(["git", "-C", projet, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return r.stdout.strip()[:40] if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def differences(avant, apres):
    d = [{"f": k, "etat": "nouveau" if k not in avant else "modifie"} for k in sorted(apres) if avant.get(k) != apres[k]]
    d += [{"f": k, "etat": "supprime"} for k in sorted(avant) if k not in apres]
    return d


def ecrire_etat(chemin, donnees):
    tmp = chemin + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(donnees, f)
        os.replace(tmp, chemin)
    except OSError:
        pass


def resume_questionnaire(studio):
    q = lire_json(os.path.join(studio, "reponses_questionnaire.json"), {})
    if not isinstance(q, dict):
        return {}
    rep = q.get("reponses") if isinstance(q.get("reponses"), dict) else {}
    return {"etat": q.get("etat"), "chapitre_courant": q.get("chapitre_courant"),
            "pitch": "vision.pitch" in rep, "derniere": max(rep, key=lambda k: str((rep[k] or {}).get("t", "")) if isinstance(rep[k], dict) else "", default=""),
            "nb_reponses": len(rep)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Attend un changement écrit par la page du studio, sans dépenser de jetons.")
    ap.add_argument("--projet", required=True)
    ap.add_argument("--max", type=float, default=0, help="secondes d'attente au plus (défaut : economie.attente_max_s, sinon 1800)")
    ap.add_argument("--point", action="store_true", help="dire tout de suite si un point de suivi est utile (code 3 : rien de neuf)")
    a = ap.parse_args(argv)
    projet = os.path.abspath(a.projet)
    studio = os.path.join(projet, ".studio")
    if not os.path.isdir(studio):
        print(json.dumps({"erreur": "pas de dossier .studio", "projet": projet}, ensure_ascii=False))
        return 2

    if a.point:
        etat_ch = os.path.join(studio, "point.etat.json")
        avant = lire_json(etat_ch, {})
        apres = empreintes(studio, POINT)
        apres["git:HEAD"] = tete_git(projet)
        diff = differences(avant if isinstance(avant, dict) else {}, apres)
        ecrire_etat(etat_ch, apres)
        if not diff:
            print(json.dumps({"evenement": "rien"}))
            return 3
        print(json.dumps({"evenement": "changement", "fichiers": diff[:40], "nb": len(diff)}, ensure_ascii=False))
        return 0

    conf = lire_json(os.path.join(studio, "studio.config.json"), {})
    eco = conf.get("economie") if isinstance(conf, dict) and isinstance(conf.get("economie"), dict) else {}
    defaut = eco.get("attente_max_s") if isinstance(eco.get("attente_max_s"), (int, float)) and eco.get("attente_max_s") > 0 else 1800
    maxi = max(5.0, min(float(a.max or defaut), 6 * 3600.0))
    etat_ch = os.path.join(studio, "attente.etat.json")
    vu = lire_json(etat_ch, None)
    courant = empreintes(studio, ATTENTE)
    if not isinstance(vu, dict):          # premier appel : l'état actuel sert de départ
        vu = courant
        ecrire_etat(etat_ch, vu)
    fin = time.time() + maxi
    while True:
        diff = differences(vu, courant)
        if diff:
            calme_fin, dernier = time.time() + CALME_MAX_S, courant
            while time.time() < calme_fin:          # attend la fin de la rafale
                time.sleep(CALME_S)
                courant = empreintes(studio, ATTENTE)
                if courant == dernier:
                    break
                dernier = courant
            diff = differences(vu, courant)
            ecrire_etat(etat_ch, courant)
            sortie = {"evenement": "changement", "fichiers": diff[:40], "nb": len(diff)}
            if any(x["f"] == "reponses_questionnaire.json" for x in diff):
                sortie["questionnaire"] = resume_questionnaire(studio)
            print(json.dumps(sortie, ensure_ascii=False))
            return 0
        if time.time() >= fin:
            print(json.dumps({"evenement": "rien", "attendu_s": int(maxi)}))
            return 3
        time.sleep(PAS_S)
        courant = empreintes(studio, ATTENTE)


if __name__ == "__main__":
    sys.exit(main())
