"""Essai de la règle « vague suivante » (automatismes.py), sans navigateur ni serveur : rien n'est envoyé (STUDIO_ESSAI_SANS_ENVOI),
les envois prévus sont lus dans automatismes.json.

Règle : quand tous les postes libres (hors chaîne moteur) ont fini ou n'ont rien écrit depuis plus de 5 min, UNE demande à
l'assistant (origine auto:vague.<heure>) avec la liste des postes libres et les tâches de taches_disponibles.json. Pas de
doublon tant qu'elle attend ; rien si un poste travaille. Jumeau du test_vague.py du studio d'origine.

python -I -B essai_vague.py
"""
import argparse
import json
import os
import shutil
import sys
import tempfile

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
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)


def main(argv=None):
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args(argv)   # --help n'essaie rien
    racine = tempfile.mkdtemp(prefix="essai_vague_")
    ok = 0
    try:
        st = FauxStudio(os.path.join(racine, "projet"))
        ecrire(st.f("reglages.json"), {"attribution_auto": True, "tyrannie_auto": True})
        ecrire(st.f("taches_disponibles.json"), {"taches": [{"id": "T-300", "titre": "Tâche avec moteur", "moteur": True, "sans_moteur": False},
                                                            {"id": "T-301", "titre": "Tâche sans moteur", "sans_moteur": True}]})
        conf = {"mode": "travail", "moteur": {"nom": "Godot", "processus": ["godot.exe"], "poste": "moteur"},
                "postes": [{"id": "moteur"}, {"id": "atelier"}, {"id": "blender"}, {"id": "scenariste"}]}
        postes = [{"id": "moteur", "nom": "Moteur", "etat": "travaille"}, {"id": "atelier", "nom": "Atelier", "etat": "disponible"},
                  {"id": "blender", "nom": "Blender", "etat": "disponible"}, {"id": "scenariste", "nom": "Scénariste", "etat": "disponible"}]
        progs = {"moteur": ({"pct": 30}, 1.0)}
        t0 = 1_800_000_000.0
        etat = [A.Automatismes(st)]

        def neuf():
            if os.path.exists(st.f("automatismes.json")):
                os.remove(st.f("automatismes.json"))
            etat[0] = A.Automatismes(st)

        def passe(t):
            a = etat[0]
            c = a.contexte(conf, postes, {"jalons": []}, progs, [], None, {})
            return a.vague(c, t)

        def envois():
            return [x for x in etat[0].d.get("essai_envois") or [] if x["route"] == "/api/demande"]

        def verifier(nom, cond, detail=""):
            nonlocal ok
            if not cond:
                raise AssertionError(f"{nom} : {detail}")
            ok += 1
            print("  ok   ", nom)

        # 1) tous finis depuis 6 min (le moteur travaille : chaîne moteur, hors règle) → une demande
        for pid in ("atelier", "blender", "scenariste"):
            progs[pid] = ({"pct": 100, "etape": "fini : vague-3"}, 6.0)
        r = passe(t0)
        verifier("tous finis depuis 6 min : une demande", len(envois()) == 1 and r["envoyee"], r)
        c = envois()[0]["corps"]
        verifier("adressée à l'assistant, origine auto:vague", c["cible"] == "assistant" and c["origine"].startswith("auto:vague."), c)
        verifier("liste des postes libres et des tâches", all(x in c["texte"] for x in ("Atelier (atelier)", "Blender (blender)", "Scénariste (scenariste)", "T-300", "T-301 ")), c["texte"])
        verifier("chaîne moteur hors de la liste", "(moteur)" not in c["texte"], c["texte"])

        # 2) deuxième passage (et une heure plus tard) : la demande attend → aucune nouvelle
        r = passe(t0 + 60)
        verifier("deuxième passage : aucune nouvelle", len(envois()) == 1 and r["attente"] and not r["envoyee"], r)
        passe(t0 + 3600)
        verifier("une heure plus tard, toujours en attente : aucune", len(envois()) == 1)

        # 2b) demande réelle (fichier lisible) traitée → la règle peut repartir
        e = etat[0].d["vague"]
        e["demande"]["id"] = "20261114-160000-000-assistant"
        ecrire(st.f("demandes_vocales", e["demande"]["id"] + ".json"), {"cible": "assistant", "statut": "nouvelle"})
        passe(t0 + 3700)
        verifier("demande encore « nouvelle » : aucune", len(envois()) == 1)
        ecrire(st.f("demandes_vocales", e["demande"]["id"] + ".json"), {"cible": "assistant", "statut": "traitee"})
        r = passe(t0 + 3760)
        verifier("demande traitée : une nouvelle vague", len(envois()) == 2 and r["envoyee"], r)
        # 2c) la nouvelle demande est close aussitôt (l'assistant a lancé la vague) mais les agents n'ont pas encore écrit leur
        # barre : pas de nouvelle demande avant 20 min (avant le correctif : une demande à chaque passage)
        e["demande"]["id"] = "20261114-170000-000-assistant"
        ecrire(st.f("demandes_vocales", e["demande"]["id"] + ".json"), {"cible": "assistant", "statut": "traitee"})
        r = passe(t0 + 3820)
        verifier("close aussitôt : aucune nouvelle avant 20 min", len(envois()) == 2 and not r["envoyee"] and "20 min" in r["raison"], r)
        r = passe(t0 + 3760 + 1201)
        verifier("20 min plus tard, toujours tous libres : une nouvelle", len(envois()) == 3 and r["envoyee"], r)
        neuf()

        # 3) un poste en cours → aucune
        progs["blender"] = ({"pct": 40, "etape": "travaille : rocher"}, 0.5)
        r = passe(t0)
        verifier("un poste en cours : aucune", not envois() and "Blender" in (r["occupe"] or ""), r)
        progs["blender"] = ({"pct": 3, "etape": "travaille : x", "source": "chaîne wf_x"}, 6.0)
        r = passe(t0)
        verifier("barre de chaîne vieille de 6 min : encore au travail, aucune", not envois() and "Blender" in (r["occupe"] or ""), r)

        # 4) fini depuis 2 min → aucune ; barre figée depuis 15 min → libre
        progs["blender"] = ({"pct": 100}, 2.0)
        passe(t0)
        verifier("fini depuis 2 min : on attend", not envois())
        progs["blender"] = ({"pct": 40}, 15.0)
        r = passe(t0)
        verifier("barre figée depuis 15 min : libre, une demande", len(envois()) == 1 and "rien écrit depuis 15 min" in envois()[0]["corps"]["texte"], r)
        neuf()

        # 5) barre « en attente » réécrite souvent : libre, mais 5 min de calme d'abord
        progs["blender"] = ({"pct": 97, "etape": "en attente : fini, la chaîne continue", "attente": True}, 0.2)
        passe(t0)
        verifier("« en attente » vu à l'instant : on attend 5 min", not envois())
        r = passe(t0 + 301)
        verifier("« en attente » depuis 5 min : une demande", len(envois()) == 1, r)
        neuf()

        # 6) réglages coupés → rien
        ecrire(st.f("reglages.json"), {"attribution_auto": True, "tyrannie_auto": True, "pause": True})
        r = passe(t0 + 400)
        verifier("Tout couper : rien", not envois() and r["raison"].startswith("coupée"), r)
        ecrire(st.f("reglages.json"), {"attribution_auto": False, "tyrannie_auto": False})
        r = passe(t0 + 400)
        verifier("attribution et tyrannie coupées : rien", not envois(), r)
        print(f"\n{ok} vérifications vertes (règle « vague suivante »)")
        return 0
    finally:
        shutil.rmtree(racine, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
