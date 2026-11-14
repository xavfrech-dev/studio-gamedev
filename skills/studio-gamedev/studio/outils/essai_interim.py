"""Essai de la relecture partagée (automatismes.py, règle du studio), sans navigateur ni serveur : rien n'est
envoyé (STUDIO_ESSAI_SANS_ENVOI), les envois prévus sont lus dans .studio/automatismes.json.

Règle : un relecteur dont la relecture est prévue à plus de 60 min (restant_min de sa progression) partage son lot : la moitié
va d'abord à un autre relecteur libre, sinon à un « Relecteur (intérim) » embauché (mission = la liste de ses éléments ; 2 au
plus en même temps ; 6 partages par heure au plus). À la fin de sa part, l'intérimaire est renvoyé (« mission d'intérim finie »)
sauf s'il reste une relecture à faire : gardé alors 30 min au plus.

python -I -B essai_interim.py
"""
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


LOT = [f"commit a{i} : relire le module {i}" for i in range(8)]


def main():
    racine = tempfile.mkdtemp(prefix="essai_interim_")
    ok = 0
    try:
        st = FauxStudio(os.path.join(racine, "projet"))
        conf = {"mode": "travail", "langue": "fr", "postes": [{"id": "code"}, {"id": "relecture", "nom": "Relecteur"}]}
        ecrire(st.f("reglages.json"), {"attribution_auto": True, "tyrannie_auto": True})
        progs = {"relecture": ({"pct": 10, "restant_min": 120, "lot": LOT, "poste": "relecture"}, 1)}

        def rel(restant=120, etat="travaille"):
            return {"id": "relecture", "nom": "Relecteur", "genre": "fixe", "etat": etat, "progression": 10, "restant_min": restant,
                    "calme_min": 1, "demandes": [], "depuis": 1}

        def code():
            return {"id": "code", "nom": "Code", "genre": "fixe", "etat": "travaille", "progression": 40, "calme_min": 2, "demandes": [], "depuis": 1}

        def interim(nom, etat, pc=None):
            return {"id": nom, "nom": nom, "genre": "recrue", "etat": etat, "progression": pc, "restant_min": None, "calme_min": 1, "demandes": [], "depuis": 1}

        def envois(a, route):
            return [x["corps"] for x in a.d.get("essai_envois") or [] if x["route"] == route]

        a = A.Automatismes(st)
        # 1. relecteur à 120 min → intérimaire embauché avec la moitié du lot (mission = ses éléments) ; le relecteur garde l'autre
        r = a.passer(conf, [code(), rel()], None, progs, [], None, {})
        rec = envois(a, "/api/recruter")
        assert len(rec) == 1 and rec[0]["nom"] == "relecteur-interim-1" and rec[0]["lancer"] is True, rec
        assert rec[0]["nom_affiche"] == "Relecteur (intérim) 1" and "intérim" in rec[0]["role"], rec[0]
        m = rec[0]["mission"]
        assert all(x in m for x in LOT[4:]) and not any(x in m for x in LOT[:4]), m
        assert envois(a, "/api/agent") == [{"id": "relecteur-interim-1", "metiers": ["relecture"]}], envois(a, "/api/agent")
        dem = [x for x in envois(a, "/api/demande") if x.get("cible") == "relecture"]
        assert len(dem) == 1 and "Tu gardes seulement" in dem[0]["texte"] and LOT[0] in dem[0]["texte"] and LOT[7] in dem[0]["texte"].split("Tu gardes")[0], dem
        assert r["partages"] and r["partages"][-1]["bulle"] == "je partage ma relecture avec un intérimaire", r["partages"]
        assert r["interimaires"] == ["relecteur-interim-1"], r
        types = [j["type"] for j in a.d["journal"]]
        assert "embauche_interim" in types and "partage" in types, types
        ok += 1
        # 2. jamais de boucle : le même lot n'est pas repartagé
        for _ in range(5):
            a.passer(conf, [code(), rel()], None, progs, [], None, {})
        assert len(envois(a, "/api/recruter")) == 1
        ok += 1
        # 3. l'intérimaire travaille, puis finit sa part → renvoyé (« mission d'intérim finie »), visible dans les renvois
        it = "relecteur-interim-1"
        a.passer(conf, [code(), rel(), interim(it, "attend")], None, progs, [], None, {})
        assert not envois(a, "/api/renvoyer"), "renvoyé avant d'avoir travaillé"
        a.passer(conf, [code(), rel(), interim(it, "travaille", 50)], None, progs, [], None, {})
        assert not envois(a, "/api/renvoyer")
        r = a.passer(conf, [code(), rel(40), interim(it, "disponible", 100)], None, progs, [], None, {})
        rv = envois(a, "/api/renvoyer")
        assert rv == [{"nom": it, "motif": "mission d'intérim finie"}], rv
        assert r["interimaires"] == [] and any(x["nom"] == it for x in r["renvois"]), r
        assert any(j["type"] == "renvoi_interim" and j["ok"] for j in a.d["journal"]), a.d["journal"]
        ok += 1
        # 4. relecture encore à faire : l'intérimaire fini est gardé, puis renvoyé au bout de 30 min
        b = A.Automatismes(FauxStudio(os.path.join(racine, "garde")))
        ecrire(b.s.f("reglages.json"), {"attribution_auto": True})
        b.passer(conf, [code(), rel()], None, progs, [], None, {})
        b.passer(conf, [code(), rel(), interim(it, "travaille", 50)], None, progs, [], None, {})
        ecrire(b.s.f("taches_disponibles.json"), {"taches": [{"id": "R-9", "titre": "Relire la sauvegarde", "metier": "relecture", "statut": "a_faire"}]})
        b.passer(conf, [code(), rel(40), interim(it, "disponible", 100)], None, progs, [], None, {})
        assert not envois(b, "/api/renvoyer") and it in b.d["interim"]["interimaires"], b.d["interim"]
        b.d["interim"]["interimaires"][it]["fini_t"] -= A.INTERIM_GARDE_S + 1
        b.passer(conf, [code(), rel(40), interim(it, "disponible", 100)], None, progs, [], None, {})
        assert envois(b, "/api/renvoyer") == [{"nom": it, "motif": "mission d'intérim finie"}], envois(b, "/api/renvoyer")
        ok += 1
        # 5. un autre relecteur libre passe avant l'intérim : la moitié lui est confiée, personne n'est embauché
        c_ = A.Automatismes(FauxStudio(os.path.join(racine, "libre")))
        ecrire(c_.s.f("reglages.json"), {"attribution_auto": True})
        conf2 = dict(conf, postes=conf["postes"] + [{"id": "relecteur-b", "nom": "Relectrice B"}])
        lb = {"id": "relecteur-b", "nom": "Relectrice B", "genre": "fixe", "etat": "disponible", "progression": None, "restant_min": None, "demandes": [], "depuis": 1}
        r = c_.passer(conf2, [code(), rel(), lb], None, progs, [], None, {})
        cf = [x for x in envois(c_, "/api/confier") if x["agent"] == "relecteur-b"]
        assert not envois(c_, "/api/recruter") and len(cf) == 1 and LOT[7] in cf[0]["mission"] and LOT[0] not in cf[0]["mission"], cf
        assert r["partages"][-1]["bulle"] == "je partage ma relecture avec Relectrice B", r["partages"]
        ok += 1
        # 6. garde-fous : sous 60 min rien ; pause rien ; jamais plus de 2 intérimaires
        d_ = A.Automatismes(FauxStudio(os.path.join(racine, "garde_fous")))
        ecrire(d_.s.f("reglages.json"), {"attribution_auto": True})
        d_.passer(conf, [code(), rel(55)], None, progs, [], None, {})
        ecrire(d_.s.f("reglages.json"), {"attribution_auto": True, "pause": True})
        d_.passer(conf, [code(), rel()], None, progs, [], None, {})
        assert not envois(d_, "/api/recruter"), envois(d_, "/api/recruter")
        ecrire(d_.s.f("reglages.json"), {"attribution_auto": True})
        d_.d["interim"]["interimaires"] = {"relecteur-interim-1": {"t": 1}, "relecteur-interim-2": {"t": 1}}
        pp = [code(), rel(), interim("relecteur-interim-1", "travaille", 20), interim("relecteur-interim-2", "travaille", 20)]
        d_.passer(conf, pp, None, progs, [], None, {})
        assert not envois(d_, "/api/recruter") and any(j.get("refus") == "2 intérimaires au plus" for j in d_.d["journal"]), d_.d["journal"]
        ok += 1
        # 7. projet en anglais : bulle et motif en anglais ; lot pris dans la dernière demande du relecteur
        e_ = A.Automatismes(FauxStudio(os.path.join(racine, "en")))
        ecrire(e_.s.f("reglages.json"), {"attribution_auto": True})
        ecrire(e_.s.f("demandes", "20261114-relecture.json"), {"nom": "relecture", "mission": "Review:\n" + "\n".join(f"- item {i}" for i in range(6))})
        r = e_.passer(dict(conf, langue="en"), [code(), rel(90)], None, {}, [], None, {})
        rec = envois(e_, "/api/recruter")
        assert len(rec) == 1 and "item 5" in rec[0]["mission"] and "item 0" not in rec[0]["mission"], rec
        assert r["partages"][-1]["bulle"] == "I'm sharing my review with a temp", r["partages"]
        ok += 1
    finally:
        shutil.rmtree(racine, ignore_errors=True)
    print(f"ESSAI DE LA RELECTURE PARTAGÉE RÉUSSI ({ok}/7)")


if __name__ == "__main__":
    main()
