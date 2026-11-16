"""Essai des barres en temps réel des cartes des postes (correctif jumeau du 16/11 23:40 : « tout est en attente ou à
0 %, vient de commencer, alors que des agents tournent »). Sans navigateur ni serveur, dans un dossier jetable.

Vérifie :
- un poste doublé (« <poste>-2.json ») et un ancien nom déclaré (config « alias_progression ») nourrissent la carte du poste ;
- la barre la plus récente du poste gagne ;
- un poste à part dont l'id finit par « -2 » garde sa barre ;
- agent du flux en cours : sa barre vieille de plus de 30 min reste lue si elle date de sa tâche ; une barre écrite avant le
  départ de l'agent (tâche précédente, 100 %) laisse place au cycle du poste (choisir 17, travail 50, relecture 83) ;
- le texte de la barre de l'agent n'est plus écrasé par le titre du flux ; départ inconnu : le titre du flux reste prioritaire ;
- signe de vie (vivant_t) et départ (debut) lus dans les journaux agent-<id>.jsonl ; un run au journal immobile mais dont un
  agent écrit encore reste suivi ;
- la page : « vient de commencer » seulement pour une barre écrite par l'agent, vivant_t compté dans le silence, cycle = vrai %.

python -I -B essai_barres_temps_reel.py
"""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time

ICI = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(ICI)
sys.path.insert(0, STUDIO)
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

RES = {"ok": 0, "echec": 0}


def ok(cond, msg):
    RES["ok" if cond else "echec"] += 1
    print(("  ok   " if cond else "  ÉCHEC ") + msg)
    return cond


def ecrire(ch, d, age_min=0):
    os.makedirs(os.path.dirname(ch), exist_ok=True)
    with open(ch, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    t = time.time() - age_min * 60
    os.utime(ch, (t, t))


def essai_postes(base):
    print("1. Cartes des postes : barre la plus récente, postes doublés, anciens noms, agent en cours")
    import studio_etat
    projet = os.path.join(base, "Mon jeu barres")
    st = os.path.join(projet, ".studio")
    ids = ("level", "faune", "scenario", "chef", "chef-2", "relecture", "inconnu")
    ecrire(os.path.join(st, "studio.config.json"), {"postes": [{"id": i, "nom": i.capitalize()} for i in ids],
                                                    "alias_progression": {"quetes": "scenario"}})
    prog = os.path.join(st, "progression")
    ecrire(os.path.join(prog, "level.json"), {"pct": 100, "etape": "ancienne tâche finie"}, age_min=240)
    ecrire(os.path.join(prog, "level-2.json"), {"pct": 30, "etape": "Niveau 2 : 12 rouges classés"}, age_min=5)
    ecrire(os.path.join(prog, "faune.json"), {"pct": 100, "etape": "tâche précédente finie"}, age_min=60)
    ecrire(os.path.join(prog, "scenario.json"), {"pct": 40, "etape": "vieille barre du poste"}, age_min=20)
    ecrire(os.path.join(prog, "quetes.json"), {"pct": 5, "etape": "Dialogue du marchand : création de la branche"}, age_min=2)
    ecrire(os.path.join(prog, "chef.json"), {"pct": 60, "etape": "Lot 4, passe 2"}, age_min=78)
    ecrire(os.path.join(prog, "chef-2.json"), {"pct": 100, "etape": "atelier : entre deux étapes"}, age_min=15)
    ecrire(os.path.join(prog, "relecture.json"), {"pct": 100, "etape": "fin du travail"}, age_min=3)
    ecrire(os.path.join(prog, "inconnu.json"), {"pct": 20, "etape": "barre fraîche, départ inconnu"}, age_min=1)
    s = studio_etat.Studio(projet)
    conf = s.config()
    n = time.time()
    flux = {"level": {"genre": "travail", "titre": "Niveau 2 : rouges", "debut": n - 600, "vivant_t": int(n - 30)},
            "faune": {"genre": "travail", "titre": "Comportement du loup", "debut": n - 300, "vivant_t": int(n - 20)},
            "scenario": {"genre": "travail", "titre": "Dialogue du marchand", "debut": n - 400, "vivant_t": int(n - 10)},
            "chef": {"genre": "travail", "titre": "lot4", "debut": n - 120 * 60, "vivant_t": int(n - 40)},
            "relecture": {"genre": "relire", "titre": "", "debut": n - 60, "vivant_t": int(n - 5)},
            "inconnu": {"genre": "travail", "titre": "Titre choisi", "debut": None, "vivant_t": None}}
    q = {x["id"]: x for x in s.postes(conf, None, s.progressions(), {}, [], {}, [], None, None, flux=flux)}
    lv, fa, sc, ch, c2, rl, ic = (q[i] for i in ids)
    ok(lv["progression"] == 30 and lv["progression_source"] == "progression/level-2.json" and lv["ligne"]["complet"] == "Niveau 2 : 12 rouges classés",
       f"poste doublé : level-2.json lu sur la carte level ({lv['progression']} %, {lv['progression_source']}, « {lv['ligne']['complet']} »)")
    ok(lv.get("vivant_t") == int(n - 30), f"signe de vie de l'agent transmis (vivant_t {lv.get('vivant_t')})")
    ok(fa["etat"] == "travaille" and fa["progression"] == 50 and "cycle" in fa["progression_source"] and fa["ligne"]["complet"] == "Comportement du loup",
       f"barre de la tâche précédente (100 %, avant le départ) écartée : cycle {fa['progression']} %, « {fa['ligne']['complet']} »")
    ok(sc["progression"] == 5 and sc["progression_source"] == "progression/quetes.json",
       f"ancien nom déclaré et barre la plus récente : {sc['progression']} % ({sc['progression_source']})")
    ok(ch["progression"] == 60 and ch["ligne"]["complet"] == "Lot 4, passe 2" and ch.get("progression_t"),
       f"barre de 78 min écrite pendant l'agent : gardée ({ch['progression']} %, « {ch['ligne']['complet']} », heure de nouvelle)")
    ok(c2["progression"] == 100 and c2["progression_source"] == "progression/chef-2.json" and ch["progression_source"] == "progression/chef.json",
       f"poste à part « chef-2 » : sa barre reste la sienne ({c2['progression_source']}, chef : {ch['progression_source']})")
    ok(rl["progression"] == 83 and rl["etat"] == "travaille", f"relecture en cours : cycle {rl['progression']} %")
    ok(ic["progression"] == 20 and ic["ligne"]["complet"] == "Titre choisi",
       f"départ inconnu : % de la barre gardé ({ic['progression']}), titre du flux prioritaire (« {ic['ligne']['complet']} »)")
    # sans flux : rien de changé pour un poste sans agent (barre vieille et finie)
    q0 = {x["id"]: x for x in s.postes(conf, None, s.progressions(), {}, [], {}, [], None, None)}
    ok(q0["faune"]["etat"] != "travaille" and q0["faune"]["progression"] == 100 and "vivant_t" not in q0["faune"],
       f"sans agent en cours : faune {q0['faune']['etat']}, {q0['faune']['progression']} %")
    # 6 h plus tard : la barre de l'agent n'est plus crue, le cycle reprend
    vieux = dict(flux["chef"], debut=n - 9 * 3600)
    ecrire(os.path.join(prog, "chef.json"), {"pct": 60, "etape": "Lot 4, passe 2"}, age_min=7 * 60)
    q7 = {x["id"]: x for x in s.postes(conf, None, s.progressions(), {}, [], {}, [], None, None, flux={"chef": vieux})}
    ok(q7["chef"]["progression"] == 50 and "cycle" in q7["chef"]["progression_source"],
       f"barre de plus de 6 h : cycle du poste ({q7['chef']['progression']} %)")


def essai_journaux(base):
    print("2. Journaux des workflows : départ, signe de vie, run au journal immobile mais agent vivant")
    import equipe
    wf = os.path.join(base, "workflows")
    for run, lignes, age_j, agents in (
            ("vivant", [{"type": "started", "agentId": "a1", "label": "travail:level-2"}], 90, {"a1": 1}),
            ("mort", [{"type": "started", "agentId": "b1", "label": "travail:faune"}], 90, {"b1": 80}),
            ("neuf", [{"type": "started", "agentId": "c1", "label": "relire:scenario"}], 1, {})):
        d = os.path.join(wf, run)
        ch = os.path.join(d, "journal.jsonl")
        os.makedirs(d, exist_ok=True)
        with open(ch, "w", encoding="utf-8") as f:
            f.write("\n".join(json.dumps(x) for x in lignes) + "\n")
        t = time.time() - age_j * 60
        os.utime(ch, (t, t))
        for a, age in agents.items():
            ecrire(os.path.join(d, f"agent-{a}.jsonl"), {"x": 1}, age_min=age)
    flux = equipe.agents_en_cours_flux([wf])
    ok(set(flux) == {"level", "scenario"}, f"run immobile mais agent vivant suivi, run mort ignoré ({sorted(flux)})")
    lv = flux.get("level") or {}
    ok(isinstance(lv.get("vivant_t"), int) and abs(lv["vivant_t"] - (time.time() - 60)) < 5,
       f"vivant_t = dernière écriture de agent-a1.jsonl ({lv.get('vivant_t')})")
    attendu_debut = os.name == "nt" or hasattr(os.stat(wf), "st_birthtime")
    ok((isinstance(lv.get("debut"), (int, float))) == attendu_debut, f"debut lu si le système donne la création du fichier ({lv.get('debut')})")
    sc = flux.get("scenario") or {}
    ok(sc.get("genre") == "relire" and sc.get("debut") is None and sc.get("vivant_t") is None, "agent sans journal (en file) : ni départ ni signe de vie")


def essai_page():
    print("3. Page : « vient de commencer », silence, cycle du poste")
    with open(os.path.join(STUDIO, "studio.html"), encoding="utf-8") as f:
        h = f.read()
    ok(re.search(r"a\.debut && t0 && a\.t0c != null && t0 === a\.t0c", h) is not None,
       "« vient de commencer » seulement pour une barre écrite par l'agent (t0)")
    ok("(+e.vivant_t || 0) * 1000" in h and "vivant_t: ep && nombre(ep.vivant_t)" in h, "vivant_t compté dans le silence de l'agent")
    ok("étapes faites du cycle|steps done in the post cycle" in h, "cycle du poste montré comme un vrai %, pas « en continu »")


def main(argv=None):
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args(argv)
    base = tempfile.mkdtemp(prefix="essai_barres_")
    try:
        essai_postes(base)
        essai_journaux(base)
        essai_page()
    finally:
        shutil.rmtree(base, ignore_errors=True)
    print(f"\n{RES['ok']} ok, {RES['echec']} échec(s)")
    return 1 if RES["echec"] else 0


if __name__ == "__main__":
    sys.exit(main())
