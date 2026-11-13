"""Essai des automatismes côté serveur (S37), sans navigateur ni serveur : rien n'est envoyé (STUDIO_ESSAI_SANS_ENVOI),
les envois prévus sont lus dans .studio/automatismes.json.

python -I -B essai_automatismes.py
"""
import json
import os
import sys
import tempfile
import time

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ICI))
os.environ["STUDIO_ESSAI_SANS_ENVOI"] = "1"
import automatismes as A  # noqa: E402


class FauxStudio:
    def __init__(self, d):
        self.dossier = d

    def f(self, *p):
        return os.path.join(self.dossier, *p)

    def recrues(self):
        return [{"nom": "renfort", "metiers": ["son"]}]

    @staticmethod
    def exclue(t):
        return False


def ecrire(chemin, d):
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)


def main():
    d = tempfile.mkdtemp(prefix="essai_auto_")
    st = FauxStudio(d)
    conf = {"mode": "travail", "langue": "fr", "postes": [{"id": "code"}, {"id": "art"}, {"id": "son"}], "moteur": {"nom": "Godot"}}
    ecrire(st.f("taches_disponibles.json"), {"taches": [
        {"id": "J1-01", "titre": "Contrôleur du joueur", "critere": "il saute", "statut": "a_faire", "poste": "code", "pour": ["code"], "moteur": True, "sans_moteur": False},
        {"id": "J1-02", "titre": "Bible de style", "critere": "validée", "statut": "a_faire", "poste": "art", "pour": ["art"], "moteur": False, "sans_moteur": True},
        {"id": "J1-03", "titre": "Liste des sons", "critere": "écrite", "statut": "a_faire", "poste": "son", "pour": ["son"], "moteur": False, "sans_moteur": True},
        {"id": "J1-04", "titre": "Tests du saut", "critere": "verts", "statut": "a_faire", "poste": "code", "pour": ["code"], "moteur": False, "sans_moteur": True},
        {"id": "J2-01", "titre": "Niveau 2", "statut": "a_faire", "poste": "niveaux", "pour": ["niveaux"], "moteur": True}]})
    ecrire(st.f("decisions.json"), [{"id": "ciel", "titre": "Quel ciel ?", "poste": "art", "statut": "en_attente"}])
    ok = 0

    def postes(**etats):
        base = {"code": {"etat": "travaille", "progression": 40, "calme_min": 2}, "art": {"etat": "travaille", "progression": 40, "calme_min": 2},
                "son": {"etat": "travaille", "progression": 40, "calme_min": 2}, "renfort": {"etat": "travaille", "progression": 40, "calme_min": 2, "genre": "recrue"}}
        for k, v in etats.items():
            base[k] = dict(base[k], **v)
        return [dict({"id": k, "nom": k.capitalize(), "genre": "fixe", "depuis": 1000, "demandes": []}, **v) for k, v in base.items()]

    def envois():
        return (A.lire(st.f("automatismes.json"), {}) or {}).get("essai_envois") or []

    # 1. tout coupé : rien ne part, même avec une fin de tâche
    ecrire(st.f("reglages.json"), {})
    a = A.Automatismes(st)
    p = postes(son={"etat": "disponible", "progression": 100, "fin_de_tache": True, "calme_min": 12, "fini": "Ambiances"})
    a.passer(conf, p, None, {}, [], None, {})
    a.d["fins"]["son"]["debut"] -= 200
    a.passer(conf, p, None, {}, [], None, {})
    assert not envois(), envois()
    ok += 1
    # 2. attribution en fin de tâche : après 2 min, la première tâche de son métier, origine auto:fin-de-tache, une seule fois
    ecrire(st.f("reglages.json"), {"attribution_auto": True})
    os.remove(st.f("automatismes.json"))
    a = A.Automatismes(st)
    a.d["traites"] = []
    a.passer(conf, p, None, {}, [], None, {})
    assert not envois(), "pas avant 2 min"
    a.d["fins"]["son"]["debut"] -= 130
    a.passer(conf, p, None, {}, [], None, {})
    e = envois()
    assert len(e) == 1 and e[0]["route"] == "/api/confier" and e[0]["corps"]["tache_id"] == "J1-03" and e[0]["corps"]["origine"] == "auto:fin-de-tache", e
    a.passer(conf, p, None, {}, [], None, {})
    assert len(envois()) == 1, "une seule fois"
    ok += 1
    # 3. tyrannie : diagnostic (décision pour « art »), rôle temporaire sans moteur, demandes à l'assistant, plus rien une minute après
    ecrire(st.f("reglages.json"), {"tyrannie_auto": True})
    if os.path.exists(st.f("automatismes.json")):
        os.remove(st.f("automatismes.json"))
    a = A.Automatismes(st)
    p = postes(art={"etat": "attend", "progression": 40, "calme_min": 30, "texte": "attend ta décision sur le ciel"},
               code={"etat": "attend", "progression": 30, "calme_min": 25, "texte": "attend le moteur pour compiler"})
    progs = {"art": ({"pct": 40, "etape": "attend ta décision sur le ciel"}, 30), "code": ({"pct": 30, "etape": "attend le moteur pour compiler", "tache": "J1-01"}, 25)}
    r = a.passer(conf, p, None, progs, [], None, {})
    dg = {x["id"]: x for x in r["tyrannie"]["diagnostics"]}
    assert dg["art"]["type"] == "decision" and dg["art"]["decision"] == "ciel" and r["remonter"] == ["ciel"], dg
    assert dg["code"]["type"] == "moteur", dg
    e = envois()
    tempo = [x for x in e if x["corps"].get("origine") == "auto:temporaire"]
    assert {x["corps"]["agent"] for x in tempo} == {"art", "code"}, tempo
    assert next(x for x in tempo if x["corps"]["agent"] == "code")["corps"]["tache_id"] == "J1-04", tempo   # sans moteur, pas sa tâche bloquée
    assert any(x["route"] == "/api/demande" and "bloqués" in x["corps"]["texte"] for x in e), e
    n = len(e)
    a.d["tyr"]["tour"] -= 61
    a.passer(conf, p, None, progs, [], None, {})
    assert len(envois()) == n, "même liste une minute après : rien de plus"
    ok += 1
    # 4. jamais « bloqué » à 100 % ni avec des nouvelles de moins de 20 min ; pause : rien
    p2 = postes(code={"etat": "attend", "progression": 100, "calme_min": 90, "texte": "attend"}, art={"etat": "attend", "progression": 40, "calme_min": 5, "texte": "attend"})
    c = a.contexte(conf, p2, None, {}, [], None, {})
    assert [q["id"] for q in a.bloques(c)] == [], a.bloques(c)
    ecrire(st.f("reglages.json"), {"tyrannie_auto": True, "pause": True})
    c = a.contexte(conf, p, None, progs, [], None, {})
    assert not a.actif_tyran(c)
    ok += 1
    # 5. renvoi d'une recrue à 100 % sans travail de son métier, après 30 min seulement
    ecrire(st.f("reglages.json"), {"tyrannie_auto": True})
    ecrire(st.f("taches_disponibles.json"), {"taches": [{"id": "J1-02", "titre": "Bible", "statut": "a_faire", "poste": "art", "moteur": False, "sans_moteur": True}]})
    a = A.Automatismes(st)
    a.d["essai_envois"] = []
    p3 = postes(renfort={"etat": "disponible", "progression": 100, "calme_min": 40})
    c = a.contexte(conf, p3, None, {}, [], None, {})
    a.tyrannie(c, 10000.0)
    assert not [x for x in envois() if x["route"] == "/api/renvoyer"] and "renfort" in a.d["sans_metier"]
    a.tyrannie(c, 10000.0 + 1801)
    assert [x for x in a.d["essai_envois"] if x["route"] == "/api/renvoyer"], a.d["essai_envois"]
    ok += 1
    # 6. embauche : une tâche dont le poste n'a personne → une recrue, une par heure
    ecrire(st.f("reglages.json"), {"embauche_auto": True})
    ecrire(st.f("taches_disponibles.json"), {"taches": [{"id": "J2-01", "titre": "Niveau 2", "statut": "a_faire", "poste": "niveaux", "moteur": True}]})
    os.remove(st.f("automatismes.json"))
    a = A.Automatismes(st)
    a.d["essai_envois"] = []
    c = a.contexte(conf, postes(), None, {}, [], None, {})
    a.embauche(c, 50000.0)
    a.embauche(c, 50000.0 + 60)
    rec = [x for x in a.d["essai_envois"] if x["route"] == "/api/recruter"]
    assert len(rec) == 1 and rec[0]["corps"]["nom"] == "niveaux", rec
    ok += 1
    print(f"ESSAI DES AUTOMATISMES CÔTÉ SERVEUR RÉUSSI ({ok}/6)")


if __name__ == "__main__":
    main()
