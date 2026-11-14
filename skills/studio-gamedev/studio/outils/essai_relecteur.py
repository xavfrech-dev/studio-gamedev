"""Essai du relecteur autonome (automatismes.py), sans navigateur ni serveur : rien n'est envoyé (STUDIO_ESSAI_SANS_ENVOI),
les envois prévus sont lus dans .studio/automatismes.json. Un dépôt git jetable sert de projet.

Règle : quand le relecteur est libre (rien à relire, rien en attente), il prend lui-même une relecture utile, par priorité :
commits de la branche principale pas encore relus, branches prêtes à intégrer pas encore relues, puis en rotation : tests du
projet, tests creux, roadmap et doc. Une à la fois, une toutes les 20 min au plus ; rien en pause, machine bloquante ou
attribution coupée. Le mode absent ne l'arrête pas : le studio continue pendant l'absence (lot E de l'autonomie).

python -I -B essai_relecteur.py
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ICI))
os.environ["STUDIO_ESSAI_SANS_ENVOI"] = "1"
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
import automatismes as A  # noqa: E402


class FauxStudio:
    def __init__(self, projet):
        self.projet = projet
        self.dossier = os.path.join(projet, ".studio")
        os.makedirs(self.dossier, exist_ok=True)

    def f(self, *p):
        return os.path.join(self.dossier, *p)

    def recrues(self):
        return []

    @staticmethod
    def exclue(t):
        return False


def ecrire(chemin, d):
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)


def git(projet, *a, age_s=0):
    env = dict(os.environ, GIT_AUTHOR_NAME="Essai", GIT_AUTHOR_EMAIL="essai@exemple.invalid",
               GIT_COMMITTER_NAME="Essai", GIT_COMMITTER_EMAIL="essai@exemple.invalid")
    if age_s:
        d = f"{int(time.time() - age_s)} +0000"
        env.update(GIT_AUTHOR_DATE=d, GIT_COMMITTER_DATE=d)
    r = subprocess.run(["git", "-C", projet, *a], env=env, capture_output=True, text=True)
    assert r.returncode == 0, (a, r.stderr)
    return r.stdout.strip()


def commit(projet, nom, age_s=0):
    with open(os.path.join(projet, nom), "w", encoding="utf-8") as f:
        f.write(nom)
    git(projet, "add", nom)
    git(projet, "commit", "-q", "-m", f"Ajout de {nom}", age_s=age_s)


def main(argv=None):
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args(argv)   # M25 : --help n'essaie rien
    racine = tempfile.mkdtemp(prefix="essai_relecteur_")
    projet = os.path.join(racine, "projet")
    os.makedirs(projet)
    ok = 0
    try:
        git(projet, "init", "-q", "-b", "main")
        git(projet, "config", "commit.gpgsign", "false")
        for i in range(3):
            commit(projet, f"a{i}.txt")
        st = FauxStudio(projet)
        conf = {"mode": "travail", "langue": "fr", "postes": [{"id": "code"}, {"id": "relecture", "nom": "Relecteur"}]}
        ecrire(st.f("reglages.json"), {"attribution_auto": True})

        def postes(etat="disponible", **k):
            return [{"id": "code", "nom": "Code", "genre": "fixe", "etat": "travaille", "progression": 40, "calme_min": 2, "demandes": [], "depuis": 1},
                    dict({"id": "relecture", "nom": "Relecteur", "genre": "fixe", "etat": etat, "progression": None, "calme_min": None,
                          "demandes": [], "depuis": 1}, **k)]

        def envois():
            return [x for x in (A.lire(st.f("automatismes.json"), {}) or {}).get("essai_envois") or []
                    if x["route"] == "/api/confier" and x["corps"]["agent"] == "relecture"]

        def reculer(s=A.RELECT_ECART_S + 1):
            rl = A.lire(st.f("relecteur.json"), {})
            rl["t"] = rl.get("t", 0) - s
            ecrire(st.f("relecteur.json"), rl)

        a = A.Automatismes(st)
        # 1. libre : relecture des commits de main pas encore relus (premier passage : les derniers), par le circuit /api/confier
        r = a.passer(conf, postes(), None, {}, [], None, {})
        e = envois()
        assert len(e) == 1, e
        c0 = e[0]["corps"]
        assert c0["tache_id"].startswith("relecture-commits-") and c0["origine"] == "auto:fin-de-tache", c0
        assert "Ajout de a0.txt" in c0["mission"] and "Ajout de a2.txt" in c0["mission"], c0["mission"]
        assert r["relecteur"]["derniere"]["genre"] == "commits", r["relecteur"]
        tete = git(projet, "rev-parse", "main")
        assert A.lire(st.f("relecteur.json"), {})["dernier_commit"] == tete
        ok += 1
        # 2. jamais de boucle : dix passages de suite → toujours une seule demande ; la page voit le délai
        for _ in range(10):
            r = a.passer(conf, postes(), None, {}, [], None, {})
        assert len(envois()) == 1 and r["relecteur"]["prochaine_dans_s"] > 0, (envois(), r["relecteur"])
        ok += 1
        # 3. vingt minutes plus tard : branche prête (calme depuis 1 h, d'avance sur main) pas encore relue
        git(projet, "checkout", "-q", "-b", "v1/fonction")
        commit(projet, "b.txt", age_s=3600)
        git(projet, "checkout", "-q", "main")
        git(projet, "checkout", "-q", "-b", "v1/en-cours")
        commit(projet, "c.txt")                         # dernier commit il y a quelques secondes : encore en travail
        git(projet, "checkout", "-q", "main")
        reculer()
        a.passer(conf, postes(), None, {}, [], None, {})
        e = envois()
        assert len(e) == 2 and e[1]["corps"]["tache_id"].startswith("relecture-branche-v1.fonction-"), e[-1]
        assert "v1/fonction" in e[1]["corps"]["mission"] and "en-cours" not in e[1]["corps"]["mission"], e[1]["corps"]["mission"]
        ok += 1
        # 4. plus rien dans git : rotation tests → tests creux → doc → tests (le plus ancien d'abord)
        genres = []
        for _ in range(4):
            reculer()
            a.passer(conf, postes(), None, {}, [], None, {})
            genres.append(A.lire(st.f("relecteur.json"), {})["derniere"]["genre"])
        assert genres == ["tests", "tests_creux", "doc", "tests"], genres
        assert "vraies entrées" in envois()[3]["corps"]["mission"], envois()[3]
        ok += 1
        # 5. un nouveau commit sur main passe avant la rotation, et seul lui est à relire
        commit(projet, "d.txt")
        reculer()
        a.passer(conf, postes(), None, {}, [], None, {})
        m = envois()[-1]["corps"]
        assert m["tache_id"].startswith("relecture-commits-") and "Ajout de d.txt" in m["mission"] and "a2.txt" not in m["mission"], m
        ok += 1
        # 6. rien quand il n'est pas libre, en pause, machine bloquante, attribution coupée
        n = len(envois())
        cas = [({"attribution_auto": True}, postes("travaille"), {}, "occupé"),
               ({"attribution_auto": True}, postes(demandes=[{"titre": "relire X", "statut": "nouvelle"}]), {}, "occupé"),
               ({"attribution_auto": True, "pause": True}, postes(), {}, "pause"),
               ({"attribution_auto": True}, postes(), {"bloquant": True}, "saturée"),
               ({}, postes(), {}, "coupée")]
        for regl, pp, sante, mot in cas:
            ecrire(st.f("reglages.json"), regl)
            reculer()
            r = a.passer(conf, pp, None, {}, [], None, sante)
            assert len(envois()) == n and mot in (r["relecteur"]["raison"] or ""), (mot, r["relecteur"])
        r = a.passer(dict(conf, mode="accueil"), postes(), None, {}, [], None, {})
        assert len(envois()) == n
        ok += 1
        # 6 bis. mode absent : le relecteur continue (le studio continue pendant l'absence)
        ecrire(st.f("reglages.json"), {"attribution_auto": True, "mode_absent": True})
        reculer()
        r = a.passer(conf, postes(), None, {}, [], None, {})
        assert len(envois()) == n + 1 and not r["relecteur"]["raison"], r["relecteur"]
        n = len(envois())
        ok += 1
        # 7. tyrannie seule : même circuit, origine « auto:temporaire » (celle que le serveur permet sans attribution automatique)
        ecrire(st.f("reglages.json"), {"tyrannie_auto": True})
        reculer()
        a.passer(conf, postes(), None, {}, [], None, {})
        assert len(envois()) == n + 1 and envois()[-1]["corps"]["origine"] == "auto:temporaire", envois()[-1]
        ok += 1
        # 8. refus du serveur : rien n'est marqué relu, mais le délai de 20 min court quand même (pas de boucle)
        ecrire(st.f("reglages.json"), {"attribution_auto": True})
        commit(projet, "e.txt")
        reculer()
        vrai = a.poster
        a.poster = lambda route, corps: {"ok": False, "code": 429, "erreur": "déjà une attribution en attente"}
        r = a.passer(conf, postes(), None, {}, [], None, {})
        rl = A.lire(st.f("relecteur.json"), {})
        assert rl["dernier_commit"] != git(projet, "rev-parse", "main") and time.time() - rl["t"] < 5, rl
        assert "attente" in (r["relecteur"]["raison"] or ""), r["relecteur"]
        a.poster = vrai
        reculer()
        a.passer(conf, postes(), None, {}, [], None, {})
        assert "Ajout de e.txt" in envois()[-1]["corps"]["mission"], envois()[-1]
        ok += 1
        # 9. projet en anglais, poste désigné par la config (poste_relecture), métier « review » ; sans dépôt git : rotation
        projet2 = os.path.join(racine, "sans_git")
        os.makedirs(projet2)
        st2 = FauxStudio(projet2)
        ecrire(st2.f("reglages.json"), {"attribution_auto": True})
        conf2 = {"mode": "travail", "langue": "en", "postes": [{"id": "qa-desk"}], "poste_relecture": "qa-desk"}
        b = A.Automatismes(st2)
        b.passer(conf2, [{"id": "qa-desk", "nom": "QA", "etat": "disponible", "demandes": [], "depuis": 1}], None, {}, [], None, {})
        e2 = [x for x in b.d.get("essai_envois") or [] if x["route"] == "/api/confier"]
        assert len(e2) == 1 and e2[0]["corps"]["agent"] == "qa-desk" and e2[0]["corps"]["mission"].startswith("Re-run the project tests"), e2
        st3 = FauxStudio(os.path.join(racine, "metier"))
        c3 = A.Automatismes(st3).contexte({"postes": [{"id": "alice", "metiers": ["review"]}]}, [{"id": "alice"}], None, {}, [], None, {})
        assert A.Automatismes(st3).poste_relecteur(c3) == "alice"
        c4 = A.Automatismes(st3).contexte({"postes": [{"id": "code"}, {"id": "art"}]}, [{"id": "code"}, {"id": "art"}], None, {}, [], None, {})
        assert A.Automatismes(st3).poste_relecteur(c4) is None
        ok += 1
    finally:
        shutil.rmtree(racine, ignore_errors=True)
    print(f"ESSAI DU RELECTEUR AUTONOME RÉUSSI ({ok}/10)")


if __name__ == "__main__":
    main()
