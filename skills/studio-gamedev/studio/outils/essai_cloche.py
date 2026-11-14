"""Essai de cloche.py « decider » et « reservees » (Python standard, sans serveur ni navigateur).

python -I -B essai_cloche.py [--dossier D] [--cloche <chemin de cloche.py>]

Faux studio jetable (dossier temporaire neuf) : decisions.json avec une décision normale (★), une décision sans ★,
une dépense, une décision reserve: suppression, une marquée reserve_utilisateur, une qui parle de publier, une qui touche
Windows, une qui crée un compte, une déjà réglée. Vérifie : la ★ est prise par défaut ; reponses.json et decisions.json portent decide_par,
raison, heure ; « coordinateur (absence) » quand reglages.json dit mode_absent ; chaque décision réservée est REFUSÉE
(code 3) sans rien écrire ; un autre choix que la ★ exige une raison ; « reservees » trie juste ; les fichiers restent
lisibles (JSON, même forme qu'avant). Jumeau : le même essai tourne contre le cloche.py d'un studio jumeau avec --cloche.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
ERREURS = []


def verifie(cond, msg):
    print(("  ok    " if cond else "  ÉCHEC ") + msg)
    if not cond:
        ERREURS.append(msg)


def ecrire(chemin, donnees):
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=1)


def lire(chemin):
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def dec(id_, question, recommande="a", **plus):
    d = {"id": id_, "question": question, "contexte": "essai", "recommande": recommande, "statut": "ouverte",
         "options": [{"id": "a", "libelle": "Option A"}, {"id": "b", "libelle": "Option B"}], "cree_le": "2026-11-14T10:00:00"}
    d.update(plus)
    return d


DECISIONS = [
    dec("normale", "Les loups chassent-ils en meute ou seuls ?"),
    dec("sans-etoile", "Quelle couleur pour le ciel ?", recommande=""),
    dec("depense", "Racheter 1000 crédits Tripo ?", recommande="", type="depense",
        depense={"montant": 10, "devise": "€", "service": "Tripo", "pourquoi": "essai"},
        options=[{"id": "accepter", "libelle": "J'accepte la dépense"}, {"id": "refuser", "libelle": "Je refuse"}]),
    dec("reserve-suppr", "Ranger les vieilles builds ?", reserve="suppression"),
    dec("reserve-util", "Changer le nom du jeu ?", reserve_utilisateur=True),
    dec("publier", "On publie la version 0.6 sur GitHub ?"),
    dec("windows", "Créer une tâche planifiée Windows au démarrage ?"),
    dec("compte", "Créer un compte sur le site du moteur ?"),
    dec("achat", "Faire un achat sur Fab pour le pack d'arbres ?"),
    dec("option-effacer", "Que faire du dossier d'essai ?", recommande="garder",
        options=[{"id": "garder", "libelle": "Le garder"}, {"id": "effacer", "libelle": "L'effacer"}]),
    dec("deja", "Déjà réglée ?", statut="repondue", reponse="a"),
]


def lancer(cloche, d, *args):
    r = subprocess.run([sys.executable, "-I", "-B", cloche, "--dossier", d, *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr


def main():
    for flux in (sys.stdout, sys.stderr):              # « ★ » : pas d'erreur dans un tube en cp1252 (-I ignore PYTHONIOENCODING)
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    p = argparse.ArgumentParser()
    p.add_argument("--dossier")
    p.add_argument("--cloche", default=os.path.join(ICI, "cloche.py"))
    a = p.parse_args()
    base = a.dossier or tempfile.mkdtemp(prefix="essai_cloche_")
    d = os.path.join(base, "studio_cloche")
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)
    print(f"Essai de {a.cloche} dans {d}")
    ecrire(os.path.join(d, "decisions.json"), DECISIONS)
    ecrire(os.path.join(d, "reponses.json"), [{"id": "ancienne", "choix": "x", "texte_libre": "", "repondu_le": "2026-11-13T09:00:00"}])
    ecrire(os.path.join(d, "reglages.json"), {"mode_absent": False})
    dch, rch = os.path.join(d, "decisions.json"), os.path.join(d, "reponses.json")

    print("Liste « reservees »")
    c, out, err = lancer(a.cloche, d, "reservees")
    verifie(c == 0, f"reservees répond (code {c} {err.strip()[:120]})")
    r = json.loads(out or "{}")
    res = {x["id"] for x in r.get("reservees", [])}
    ok = {x["id"] for x in r.get("decidables", [])}
    verifie(res == {"depense", "reserve-suppr", "reserve-util", "publier", "windows", "compte", "achat", "option-effacer"}, f"réservées justes : {sorted(res)}")
    verifie(ok == {"normale", "sans-etoile"}, f"décidables justes : {sorted(ok)}")
    verifie("deja" not in res | ok, "une décision réglée n'est pas listée")

    print("Refus des décisions réservées (rien n'est écrit)")
    avant_d, avant_r = open(dch, encoding="utf-8").read(), open(rch, encoding="utf-8").read()
    for i in ("depense", "reserve-suppr", "reserve-util", "publier", "windows", "compte", "achat"):
        c, out, err = lancer(a.cloche, d, "decider", i)
        verifie(c == 3 and "REFUS" in err and "réservée" in err, f"« {i} » refusée (code {c}) : {err.strip()[:110]}")
    c, out, err = lancer(a.cloche, d, "decider", "depense", "--choix", "accepter", "--raison", "essai")
    verifie(c == 3, f"dépense refusée même avec --choix accepter et une raison (code {c})")
    c, out, err = lancer(a.cloche, d, "decider", "option-effacer", "--choix", "effacer", "--raison", "essai")
    verifie(c == 3 and "effac" in err, f"choisir « L'effacer » refusé (code {c})")
    verifie(open(dch, encoding="utf-8").read() == avant_d and open(rch, encoding="utf-8").read() == avant_r,
            "decisions.json et reponses.json inchangés après les refus")

    print("Autres refus")
    c, _, err = lancer(a.cloche, d, "decider", "inconnue")
    verifie(c == 2 and "introuvable" in err, f"décision inconnue : code {c}")
    c, _, err = lancer(a.cloche, d, "decider", "deja")
    verifie(c == 2 and "déjà réglée" in err, f"décision déjà réglée : code {c}")
    c, _, err = lancer(a.cloche, d, "decider", "sans-etoile")
    verifie(c == 2 and "--choix" in err, f"sans ★ ni --choix : code {c}")
    c, _, err = lancer(a.cloche, d, "decider", "normale", "--choix", "zzz")
    verifie(c == 2 and "inconnu" in err, f"--choix inconnu : code {c}")
    c, _, err = lancer(a.cloche, d, "decider", "normale", "--choix", "b")
    verifie(c == 2 and "--raison" in err, f"autre choix que la ★ sans raison : code {c}")
    verifie(open(dch, encoding="utf-8").read() == avant_d, "toujours rien d'écrit")

    print("Décision normale, hors absence : la ★ par défaut")
    c, out, err = lancer(a.cloche, d, "decider", "normale")
    verifie(c == 0, f"normale tranchée (code {c} {err.strip()[:120]})")
    x = next(y for y in lire(dch) if y["id"] == "normale")
    verifie(x["statut"] == "repondue" and x["reponse"] == "a", "statut repondue, réponse = ★")
    verifie(x["decide_par"] == "coordinateur" and x["en_absence"] is False, f"decide_par = {x.get('decide_par')}")
    verifie(x["raison"] == "recommandation (★) suivie" and x["recommandation_suivie"] is True, "raison par défaut notée")
    verifie(len(x.get("decide_le", "")) == 19 and x["decide_le"] == x["repondue_le"], f"heure notée : {x.get('decide_le')}")
    reps = lire(rch)
    rr = [y for y in reps if y["id"] == "normale"]
    verifie(len(rr) == 1 and rr[0]["choix"] == "a" and rr[0]["decide_par"] == "coordinateur" and rr[0]["repondu_le"] == x["decide_le"],
            "réponse écrite dans reponses.json avec qui et quand")
    verifie(any(y["id"] == "ancienne" for y in reps), "les anciennes réponses sont gardées")
    autres = [y for y in lire(dch) if y["id"] != "normale"]
    verifie(autres == [y for y in DECISIONS if y["id"] != "normale"], "les autres décisions ne bougent pas")

    print("En absence : autre choix avec raison")
    ecrire(os.path.join(d, "reglages.json"), {"mode_absent": True, "mode_absent_depuis": "2026-11-14T12:00:00"})
    c, out, err = lancer(a.cloche, d, "decider", "sans-etoile", "--choix", "b", "--raison", "le bleu suit la DA")
    verifie(c == 0, f"sans-etoile tranchée avec --choix (code {c} {err.strip()[:120]})")
    x = next(y for y in lire(dch) if y["id"] == "sans-etoile")
    verifie(x["decide_par"] == "coordinateur (absence)" and x["en_absence"] is True, f"decide_par = {x.get('decide_par')}")
    verifie(x["raison"] == "le bleu suit la DA" and x["recommandation_suivie"] is False, "raison donnée notée")
    c, out, err = lancer(a.cloche, d, "decider", "sans-etoile")
    verifie(c == 2, "une décision tranchée ne se retranche pas")

    print("Forme des fichiers")
    verifie(isinstance(lire(dch), list) and len(lire(dch)) == len(DECISIONS), "decisions.json : même liste, même nombre")
    verifie(all(isinstance(y, dict) and y.get("id") for y in lire(rch)), "reponses.json : liste d'objets avec id")
    c, out, _ = lancer(a.cloche, d, "liste")
    verifie(c == 0 and json.loads(out)["decisions_ouvertes"] == 8, "« liste » compte encore les 8 décisions ouvertes (réservées)")

    print("Assistant actif (lot F) : proposer et note")
    d2 = os.path.join(d, "assistant_actif")
    os.makedirs(d2, exist_ok=True)
    ecrire(os.path.join(d2, "decisions.json"), [])
    for i in (1, 2, 3):
        c, out, err = lancer(a.cloche, d2, "proposer", "--id", f"sugg-{i}", "--titre", f"Lancer la tâche T{i}", "--raison", "tâche prête")
        verifie(c == 0, f"proposition {i} posée (code {c} {err.strip()[:100]})")
    l2 = lire(os.path.join(d2, "decisions.json"))
    p1 = l2[0]
    verifie(p1["genre"] == "proposition" and p1["recommande"] == "faire" and [x["id"] for x in p1["choix"]] == ["faire", "plus_tard"],
            "une proposition : ★ Faire / Plus tard")
    c, out, err = lancer(a.cloche, d2, "proposer", "--id", "sugg-4", "--titre", "Relire X", "--raison", "r")
    verifie(c == 2 and len(lire(os.path.join(d2, "decisions.json"))) == 3, "4e proposition refusée (3 ouvertes au plus)")
    c, out, err = lancer(a.cloche, d2, "proposer", "--id", "sugg-1", "--titre", "Lancer la tâche T1 (maj)", "--raison", "r")
    l2 = lire(os.path.join(d2, "decisions.json"))
    verifie(c == 0 and len(l2) == 3 and l2[-1]["id"] == p1["id"], "même base : la proposition est remplacée, même id")
    c, out, err = lancer(a.cloche, d2, "proposer", "--id", "sugg-9", "--titre", "Racheter 1000 crédits Tripo", "--raison", "r")
    verifie(c == 3, "une dépense n'est jamais une proposition à ★ (code 3)")
    ecrire(os.path.join(d2, "reponses.json"), [{"id": p1["id"], "choix": "plus_tard", "repondu_le": time.strftime("%Y-%m-%dT%H:%M:%S")}])
    l2 = lire(os.path.join(d2, "decisions.json"))
    for x in l2:
        if x["id"] == p1["id"]:
            x["statut"] = "repondue"
    ecrire(os.path.join(d2, "decisions.json"), l2)
    c, out, err = lancer(a.cloche, d2, "proposer", "--id", "sugg-1", "--titre", "Lancer la tâche T1", "--raison", "r")
    verifie(c == 2 and "Plus tard" in err, "« Plus tard » : pas reproposée avant 2 h")
    c, out, err = lancer(a.cloche, d2, "note", "--genre", "ordre", "--titre", "T3 avant T4", "--raison", "T4 dépend de T3")
    n = lire(os.path.join(d2, "decisions.json"))[-1]
    verifie(c == 0 and n["statut"] == "repondue" and n["decide_par"] == "assistant" and n["genre"] == "petite_decision", "petite décision notée")
    c, out, err = lancer(a.cloche, d2, "note", "--genre", "reversible", "--titre", "Supprimer le dossier des essais", "--raison", "x")
    verifie(c == 3, "petite décision qui supprime : refusée (code 3)")

    if not a.dossier:
        shutil.rmtree(base, ignore_errors=True)
    print(f"\n{'ÉCHEC : ' + str(len(ERREURS)) + ' point(s)' if ERREURS else 'Tout est vert.'}")
    sys.exit(1 if ERREURS else 0)


if __name__ == "__main__":
    main()
