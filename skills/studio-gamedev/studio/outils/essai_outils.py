"""Essai des petits outils du studio (lot H de l'audit du 14/11), bibliothèque standard, sans navigateur ni serveur.

Vérifie :
- G16 : sortie redirigée en cp1252 (comme une console Windows) : cloche.py --help, cloche.py afaire avec « → »,
  ecrire_forfait.py et decouverte_audio.py ne plantent pas et écrivent de l'UTF-8 ;
- M25 : --help des scripts d'essai : l'aide s'affiche, aucun essai ne tourne (code 0, sortie courte) ;
- C5 : cloche.py liste / reservees ne comptent plus une décision déjà répondue dans reponses.json ; decider la refuse (code 2) ;
- M9 : attendre.py et transcript_cc.py trouvent leurs fichiers dans un projet « Mon jeu [v2] » ;
- O14 : transcript_cc.py écarte les résultats d'outils sans perdre le texte visible ;
- G11 : crochet_journal.py numérote les réponses (champ n croissant), même liste pleine (60) ;
- M21 : dictee_propre.py (auto-essai) ;
- M24 : essai_automatismes.py ne laisse plus de dossier temporaire.

Usage : python -I -B essai_outils.py [--garder]      code 0 = tout vert
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

for _flux in (sys.stdout, sys.stderr):                 # sortie en UTF-8, même redirigée (Windows, cp1252)
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
sys.dont_write_bytecode = True
ICI = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(ICI)
sys.path.insert(0, STUDIO)
sys.path.insert(0, ICI)
import attendre  # noqa: E402
import transcript_cc  # noqa: E402

RES = {"ok": 0, "echec": 0}


def ok(cond, msg):
    RES["ok" if cond else "echec"] += 1
    print(("  ok   " if cond else "  ÉCHEC ") + msg)
    return cond


def ecrire(ch, d):
    os.makedirs(os.path.dirname(ch), exist_ok=True)
    with open(ch, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)


def lancer(script, *args, entree=None, env_plus=None):
    """Lance un script comme une redirection Windows : sortie en cp1252 (PYTHONIOENCODING), sans mode UTF-8."""
    env = dict(os.environ, PYTHONIOENCODING="cp1252", PYTHONUTF8="0")
    env.pop("PYTHONLEGACYWINDOWSSTDIO", None)
    env.update(env_plus or {})
    r = subprocess.run([sys.executable, "-I", "-B", script, *args], input=entree, capture_output=True, env=env, timeout=120)
    return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")


def essai_encodage(base):
    print("G16. Sortie redirigée en cp1252")
    cloche = os.path.join(ICI, "cloche.py")
    c, o, e = lancer(cloche, "--help")
    ok(c == 0 and "cloche" in o.lower() and "Traceback" not in e, f"cloche.py --help : code {c}")
    st = os.path.join(base, "enc", ".studio")
    ecrire(os.path.join(st, "decisions.json"), [])
    c, o, e = lancer(cloche, "--dossier", st, "afaire", "--id", "fleche", "--titre", "Essai → flèche ★")
    ok(c == 0 and "→" in o and "Traceback" not in e, f"cloche.py afaire avec « → » : code {c}, message final en UTF-8")
    c, o, e = lancer(os.path.join(ICI, "ecrire_forfait.py"), "--projet", os.path.join(base, "enc"), "--fenetre", "Fenêtre été", "42", "-", "--source", "à la main")
    ok(c == 0 and "Traceback" not in e and os.path.exists(os.path.join(st, "forfait.json")), f"ecrire_forfait.py : code {c}")
    c, o, e = lancer(os.path.join(ICI, "ecrire_forfait.py"), "--help")
    ok(c == 0 and "Traceback" not in e and ("fenêtre" in o.lower() or "fenetre" in o.lower()), f"ecrire_forfait.py --help : code {c}")
    son = os.path.join(base, "enc", "Musique été", "musique")
    os.makedirs(son, exist_ok=True)
    open(os.path.join(son, "MUS_thème_forêt.ogg"), "wb").close()
    c, o, e = lancer(os.path.join(ICI, "decouverte_audio.py"), os.path.join(base, "enc"))
    try:
        trouve = any(p.endswith("MUS_thème_forêt.ogg") for p in json.loads(o)["musiques"])
    except (ValueError, KeyError):
        trouve = False
    ok(c == 0 and trouve, f"decouverte_audio.py : code {c}, chemin accentué rendu en UTF-8")


def essai_aide():
    print("M25. --help des scripts d'essai")
    for n in ("essai_quetes.py", "essai_interim.py", "essai_relecteur.py", "essai_bureaux.py", "essai_automatismes.py", "essai_compat310.py"):
        c, o, e = lancer(os.path.join(ICI, n), "--help")
        ok(c == 0 and "usage" in o.lower() and "RÉUSSI" not in o and "Traceback" not in e, f"{n} --help : aide seule (code {c})")


def essai_cloche(base):
    print("C5. Cloche : décision déjà répondue dans reponses.json")
    st = os.path.join(base, "cloche", ".studio")
    ecrire(os.path.join(st, "decisions.json"), [
        {"id": "ciel", "question": "Quel ciel ?", "options": [{"id": "a", "libelle": "A"}, {"id": "b", "libelle": "B"}], "recommande": "a", "statut": "ouverte"},
        {"id": "sol", "question": "Quel sol ?", "options": [{"id": "a", "libelle": "A"}], "recommande": "a", "statut": "ouverte"}])
    ecrire(os.path.join(st, "reponses.json"), [{"id": "ciel", "choix": "b", "repondu_le": "2026-11-14T12:00:00"}])
    cloche = os.path.join(ICI, "cloche.py")
    c, o, _ = lancer(cloche, "--dossier", st, "liste")
    ok(c == 0 and json.loads(o)["decisions_ouvertes"] == 1, f"liste : 1 décision ouverte (la répondue n'est plus comptée) : {o[:80]!r}")
    c, o, _ = lancer(cloche, "--dossier", st, "reservees")
    ids = [x["id"] for x in json.loads(o)["decidables"] + json.loads(o)["reservees"]] if c == 0 else []
    ok(ids == ["sol"], f"reservees : seulement « sol » ({ids})")
    c, o, e = lancer(cloche, "--dossier", st, "decider", "ciel")
    reps = json.load(open(os.path.join(st, "reponses.json"), encoding="utf-8"))
    ok(c == 2 and len(reps) == 1 and reps[0]["choix"] == "b", f"decider sur une décision déjà répondue : refus (code {c}), réponse de l'utilisateur gardée")
    c, o, e = lancer(cloche, "--dossier", st, "decider", "sol")
    ok(c == 0, f"decider sur une décision vraiment ouverte : accepté (code {c})")
    c, o, _ = lancer(cloche, "--dossier", st, "depense", "--id", "ciel", "--question", "Racheter des crédits ?", "--montant", "5",
                     "--service", "Essai", "--pourquoi", "essai")
    c2, o, _ = lancer(cloche, "--dossier", st, "liste")
    ok(c == 0 and c2 == 0 and [x["id"] for x in json.loads(o)["depenses"]] == ["ciel"],
       f"décision reposée avec un id déjà répondu (plus ancien) : de nouveau ouverte ({o[:80]!r})")
    with open(os.path.join(st, "reponses.json"), "w", encoding="utf-8") as f:
        f.write("{abîmé")
    c, o, _ = lancer(cloche, "--dossier", st, "liste")
    ok(c == 0, f"liste avec un reponses.json illisible : toujours lisible (code {c})")


def essai_crochets(base):
    print("M9. Projet dans un dossier à crochets")
    projet = os.path.join(base, "Mon jeu [v2]")
    st = os.path.join(projet, ".studio")
    ecrire(os.path.join(st, "demandes", "20261114-120000_essai.json"), {"texte": "x"})
    ecrire(os.path.join(st, "reponses.json"), [])
    e = attendre.empreintes(st, ["reponses.json", "demandes/*.json"])
    ok(sorted(e) == ["demandes/20261114-120000_essai.json", "reponses.json"], f"attendre.py voit les fichiers ({sorted(e)})")
    proj_cc = os.path.join(base, "projets [cc]")
    os.makedirs(proj_cc, exist_ok=True)
    ch = os.path.join(proj_cc, "session.jsonl")
    lignes = [
        {"type": "user", "uuid": "u1", "message": {"role": "user", "content": "Bonjour, le texte contient tool_result en clair"}},
        {"type": "user", "uuid": "u2", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "x" * 5000}]}},
        {"type": "assistant", "uuid": "a1", "message": {"role": "assistant", "content": [{"type": "text", "text": "Réponse visible"}]}},
        {"type": "user", "uuid": "u3", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t2", "content": "y"},
                                                                                {"type": "text", "text": "Texte joint au résultat"}]}},
    ]
    with open(ch, "w", encoding="utf-8") as f:
        for l in lignes:
            f.write(json.dumps(l, ensure_ascii=False, separators=(",", ":")) + "\n")
    ok(transcript_cc.session_active(proj_cc) == ch, "transcript_cc.py trouve la session")
    r = transcript_cc.lire(ch)
    ids = [m["id"] for m in r["messages"]]
    print("O14. Résultats d'outils écartés")
    ok(ids == ["u1", "a1", "u3"], f"texte gardé, résultat d'outil seul écarté ({ids})")
    print("F. Bandeau « aucune session Claude » : âge de la session, sous-agents compris")
    import studio_etat
    st_obj = studio_etat.Studio.__new__(studio_etat.Studio)
    st_obj.projet = projet
    t3h = time.time() - 180 * 60
    os.utime(ch, (t3h, t3h))
    ok(abs(st_obj.activite_claude({"dossier_session": proj_cc}) - 180) < 1, "session vieille de 3 h : 180 min")
    sous = os.path.join(proj_cc, "session", "subagents", "workflows", "w1")
    os.makedirs(sous, exist_ok=True)
    open(os.path.join(sous, "agent-1.jsonl"), "w").close()
    ok(st_obj.activite_claude({"dossier_session": proj_cc}) < 2, "un sous-agent actif garde la session ouverte")
    ok(studio_etat.Studio.demandes_en_attente([{"lancer": True, "vu": False}, {"lancer": True, "vu": True}], [{"statut": "nouvelle"}]) == (1, 1),
       "ce qui attend : demandes sans statut et messages « nouvelle »")


def essai_crochet_journal(base):
    print("G11. Journal de l'assistant : numéro croissant")
    projet = os.path.join(base, "journal")
    st = os.path.join(projet, ".studio")
    os.makedirs(st, exist_ok=True)
    ecrire(os.path.join(st, "journal_assistant.json"), [{"id": f"x{i}", "texte": f"ancienne {i}"} for i in range(60)])
    tr = os.path.join(projet, "t.jsonl")
    script = os.path.join(ICI, "crochet_journal.py")
    vus = []
    for i in range(3):
        with open(tr, "w", encoding="utf-8") as f:
            f.write(json.dumps({"type": "user", "message": {"role": "user", "content": f"question {i}"}}) + "\n")
            f.write(json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": f"Réponse numéro {i}"}]}}) + "\n")
        entree = json.dumps({"transcript_path": tr, "session_id": "essai", "cwd": projet}).encode("utf-8")
        lancer(script, entree=entree, env_plus={"CLAUDE_PROJECT_DIR": projet})
        j = json.load(open(os.path.join(st, "journal_assistant.json"), encoding="utf-8"))
        vus.append((len(j), j[-1].get("n")))
    ok([v[0] for v in vus] == [60, 60, 60] and [v[1] for v in vus] == [61, 62, 63], f"liste pleine (60) et n croissant : {vus}")


def essai_divers(base):
    print("M21 / M24. Dictée propre, dossiers temporaires")
    c, o, e = lancer(os.path.join(STUDIO, "dictee_propre.py"))
    ok(c == 0 and "19/19" in o, f"dictee_propre.py : auto-essai ({o.strip()[-30:]})")
    tmp = tempfile.mkdtemp(prefix="essai_outils_tmp_")
    try:
        c, o, e = lancer(os.path.join(ICI, "essai_automatismes.py"), env_plus={"TMP": tmp, "TEMP": tmp})
        reste = glob.glob(os.path.join(tmp, "essai_auto_*"))
        ok(c == 0 and not reste, f"essai_automatismes.py : réussi (code {c}) et aucun dossier laissé ({len(reste)})")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--garder", action="store_true", help="garder le dossier temporaire")
    a = a.parse_args(argv)
    base = tempfile.mkdtemp(prefix="essai_outils_")
    try:
        essai_encodage(base)
        essai_aide()
        essai_cloche(base)
        essai_crochets(base)
        essai_crochet_journal(base)
        essai_divers(base)
    finally:
        if a.garder:
            print(f"dossier gardé : {base}")
        else:
            shutil.rmtree(base, ignore_errors=True)
    print(f"\n{RES['ok']} ok, {RES['echec']} échec(s)")
    if not RES["echec"]:
        print("ESSAI DES OUTILS RÉUSSI")
    return 1 if RES["echec"] else 0


if __name__ == "__main__":
    sys.exit(main())
