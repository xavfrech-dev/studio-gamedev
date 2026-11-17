"""Essai d'attendre.py (retours d'un utilisateur, 17/11) : attente sans fin et réglages visuels muets.

  python -I -B studio/outils/essai_attente.py

Vérifie :
  1. sans --max, attendre.py ne rend jamais la main tout seul (toujours vivant après 8 s, aucun « rien »),
     même avec economie.attente_max_s = 5 dans la config (réglage ignoré) ;
  2. un vrai changement (demande écrite) le réveille, code 0 ;
  3. --max N rend « rien », code 3 (seul cas du code 3) ;
  4. reglages.json : ordre_equipe, blague, sante_auto, maj ne changent pas l'empreinte ; mode_absent,
     attribution_auto, facteur_auto la changent ; un reglages.json illisible garde une empreinte brute ;
  5. fil.py : FIL.md garde l'en-tête et les 40 dernières lignes.
Code 0 si tout passe, 1 sinon. Bibliothèque standard seulement ; dossier temporaire effacé à la fin.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import attendre  # noqa: E402

ECHECS = []


def ok(cond, texte):
    print(("OK   " if cond else "ECHEC ") + texte)
    if not cond:
        ECHECS.append(texte)


def ecrire(chemin, donnees):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(donnees, f)


def lancer(projet, *args):
    return subprocess.Popen([sys.executable, "-I", "-B", os.path.join(ICI, "attendre.py"), "--projet", projet, *args],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def main():
    tmp = tempfile.mkdtemp(prefix="essai_attente_")
    try:
        projet = os.path.join(tmp, "Mon jeu")
        st = os.path.join(projet, ".studio")
        ecrire(os.path.join(st, "studio.config.json"), {"economie": {"attente_max_s": 5}})
        ecrire(os.path.join(st, "reglages.json"), {"ordre_equipe": ["a", "b"], "blague": True, "maj": "1"})

        # 1. sans --max : pas de fin toute seule, même avec attente_max_s = 5
        p = lancer(projet)
        time.sleep(8)
        ok(p.poll() is None, "sans --max : toujours en attente après 8 s (attente_max_s = 5 ignoré)")
        # un réglage purement visuel ne le réveille pas
        ecrire(os.path.join(st, "reglages.json"), {"ordre_equipe": ["b", "a"], "blague": False, "maj": "2",
                                                    "sante_auto": True, "theme": "nuit"})
        time.sleep(7)
        ok(p.poll() is None, "réglages visuels (ordre, blague, thème, maj) : pas de réveil")
        # 2. un vrai changement le réveille
        ecrire(os.path.join(st, "demandes_vocales", "20261117-120000_essai.json"), {"texte": "salut"})
        try:
            out, _ = p.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            p.kill()
            out = ""
        ok(p.returncode == 0 and '"changement"' in out and "demandes_vocales" in out,
           f"une demande le réveille, code 0 ({p.returncode}, {out.strip()[:120]})")
        # mode_absent réveille
        p = lancer(projet)
        time.sleep(3)
        ecrire(os.path.join(st, "reglages.json"), {"ordre_equipe": ["b", "a"], "mode_absent": True})
        try:
            out, _ = p.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            p.kill()
            out = ""
        ok(p.returncode == 0 and "reglages.json" in out, f"mode_absent réveille ({p.returncode})")

        # 3. --max : code 3
        p = lancer(projet, "--max", "3")
        try:
            out, _ = p.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            p.kill()
            out = ""
        ok(p.returncode == 3 and '"rien"' in out, f"--max 3 : « rien », code 3 ({p.returncode})")

        # 4. empreinte des réglages
        e = attendre.empreinte_reglages
        base = e(json.dumps({"mode_absent": False, "ordre_equipe": [1]}).encode())
        ok(e(json.dumps({"mode_absent": False, "ordre_equipe": [2], "blague": False, "maj": "x",
                         "sante_auto": True}).encode()) == base, "empreinte : clés visuelles ignorées")
        for cle, val in (("mode_absent", True), ("attribution_auto", True), ("facteur_auto", True),
                         ("point_auto", True), ("pause", True)):
            d = {"mode_absent": False, "ordre_equipe": [1]}
            d[cle] = val
            ok(e(json.dumps(d).encode()) != base, f"empreinte : {cle} compte")
        ok(e(b"{pas du json") == b"{pas du json", "reglages.json illisible : empreinte brute")

        # 5. FIL.md : en-tête gardé, 40 dernières lignes
        import fil
        fil.main(["--projet", projet, "entete", "# Projet : essai", "# Langue : fr"])
        for i in range(55):
            fil.main(["--projet", projet, "ajouter", f"échange {i} — rien n'attend", "--heure", "12:00"])
        with open(os.path.join(projet, "FIL.md"), encoding="utf-8") as f:
            lignes = [l for l in f.read().splitlines() if l.strip()]
        ok(lignes[:2] == ["# Projet : essai", "# Langue : fr"], "FIL.md : en-tête gardé")
        corps = [l for l in lignes if not l.startswith("#")]
        ok(len(corps) == 40 and corps[0].startswith("12:00 — échange 15") and corps[-1].endswith("échange 54 — rien n'attend"),
           f"FIL.md : 40 dernières lignes ({len(corps)})")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(("ECHECS : %d" % len(ECHECS)) if ECHECS else "Tout passe.")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
