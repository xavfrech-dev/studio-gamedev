"""Essai de « Comptes en relais » (studio/comptes_relais.py, bloc à côté de la barre du forfait).
Test of the "Relay accounts" block.

Cas joués sans serveur ni navigateur : sans fichier ou sans compte (rien), plan qui tient, « tient si on ralentit »
(le plan tient, le rythme mesuré non), budget insuffisant (trou), phase 2 après fin_phase_1, phase 1 sans fin_phase_1
(reste en phase 1), compte remis à zéro (0 %, remise une semaine plus tard), forfait.json prêté seulement au compte qu'il
nomme, seuil_relais (budget jusqu'au % de changement de compte), horizon « remise à zéro de … » quand aucun compte n'est
épuisé, horizon sans nom (plan.prochain_retour seul), et balayage : jamais de « trou de 0 min ».

python -I -B essai_comptes_relais.py      code 0 = tout vert
"""
import calendar
import os
import random
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ICI))
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
import comptes_relais as C  # noqa: E402

ECHECS = []


def ok(cond, quoi):
    print(("  ok   " if cond else "  ÉCHEC ") + quoi)
    if not cond:
        ECHECS.append(quoi)


def t(s):
    return float(calendar.timegm(tuple(int(x) for x in (s[0:4], s[5:7], s[8:10], s[11:13], s[14:16], 0)) + (0, 0, 0)))


NOW = t("2026-01-05T12:00")            # lundi midi UTC
MES = {"semaine_par_fenetre_5h_pleine": 14, "semaine_par_heure_plein_regime": 3.0}


def base(**kw):
    d = {"comptes": [
        {"nom": "compte A", "actif": True, "pct_semaine": 80, "remise_semaine": "2026-01-12T00:00:00Z"},
        {"nom": "compte B", "actif": False, "pct_semaine": 0, "remise_semaine": "2026-01-12T16:00:00Z"},
        {"nom": "compte C", "actif": False, "pct_semaine": 99, "remise_semaine": "2026-01-08T22:00:00Z"},
    ], "mesures": dict(MES), "plan": {"phase": 1, "fin_phase_1": "2026-01-06T11:00:00Z"}}
    d.update(kw)
    return d


def forfait(pct_hebdo, pct_5h, compte=None, maj="2026-01-05T12:00:00Z"):
    f = {"maj": maj, "fenetres": [
        {"nom": "Hebdo", "pct_utilise": pct_hebdo, "remise_a_zero": "2026-01-12T00:00:00Z"},
        {"nom": "5 heures", "pct_utilise": pct_5h, "remise_a_zero": "2026-01-05T15:00:00Z"}]}
    if compte:
        f["compte"] = compte
    return f


print("1. sans fichier / sans compte")
ok(C.calculer(None) is None, "comptes.json absent : None")
ok(C.calculer({"comptes": []}) is None, "liste vide : None")
ok(C.calculer({"comptes": "x"}) is None, "liste illisible : None")

print("2. plan qui tient (phase 1 puis phase 2 lissée)")
r = C.calculer(base(), None, NOW)
p = r["plan"]
st = {c["nom"]: c["statut"] for c in r["comptes"]}
ok(st == {"compte A": "actif", "compte B": "reserve", "compte C": "epuise"}, f"statuts {st}")
ok(p["budget"] == 120, f"budget 20 + 100 = 120 ({p['budget']})")
ok(p["phase"] == 1 and p["tient"] and p["retour_type"] == "retour" and p["retour_nom"] == "compte C", "phase 1, tient, retour de compte C")
ok("ça tient jusqu'au retour de compte C" in p["prevision"], p["prevision"])
ok(p["rythme_phase2"] is not None and 0 < p["rythme_phase2"] < 3, f"rythme de phase 2 {p['rythme_phase2']}")
ok(p["ralentir"] is False, "sans mesure : pas de « ralentir »")

print("3. tient si on ralentit (rythme mesuré trop haut)")
r = C.calculer(base(), forfait(80, 90), NOW)     # 90 % de la fenêtre de 5 h en 2 h : ~3,2 pt/h
p = r["plan"]
ok(p["tient"] and p["mesure_tient"] is False and p["ralentir"] is True, f"ralentir {p['ralentir']}, mesure {p['rythme_mesure']}")
ok("trou de" in p["mesure"] and "avant le retour de compte C" in p["mesure"], p["mesure"])
ok("ralentit" in p["detail"], "détail : « ne tient que si on ralentit »")
r = C.calculer(base(), forfait(80, 10), NOW)
ok(r["plan"]["ralentir"] is False and r["plan"]["mesure_tient"], "rythme mesuré bas : pas de « ralentir »")

print("4. budget insuffisant : trou")
d = base()
d["comptes"][1]["pct_semaine"] = 95                              # 25 points, plein régime jusqu'à mercredi 11:00 UTC
d["plan"] = {"phase": 1, "fin_phase_1": "2026-01-07T11:00:00Z"}
p = C.calculer(d, None, NOW)["plan"]
ok(p["tient"] is False and p["trou_h"] > 0 and "trou de" in p["prevision"], p["prevision"])
d["plan"] = {"phase": 2}
ok(C.calculer(d, None, NOW)["plan"]["tient"], "phase 2 : le rythme lissé tient par construction")
d["comptes"][0]["pct_semaine"] = 100
d["comptes"][1]["pct_semaine"] = 100
p = C.calculer(d, None, NOW)["plan"]
ok(p["budget"] == 0 and p["tient"] is False, "budget nul : trou jusqu'au retour")

print("5. phases")
p = C.calculer(base(plan={"phase": 1, "fin_phase_1": "2026-01-05T06:00:00Z"}), None, NOW)["plan"]
ok(p["phase"] == 2 and p["cible_5h"] is not None and p["cible_5h"] < 98, f"fin_phase_1 passée : phase 2, cible {p['cible_5h']} %")
p = C.calculer(base(plan={"phase": 1}), None, NOW)["plan"]
ok(p["phase"] == 1 and p["rythme_cible"] == 3.0 and "sans date de fin" in p["detail"], "phase 1 sans fin_phase_1 : reste en phase 1")

print("6. compte remis à zéro")
d = base()
d["comptes"][2]["remise_semaine"] = "2026-01-05T10:00:00Z"       # compte C remis à zéro il y a 2 h
r = C.calculer(d, None, NOW)
c = [x for x in r["comptes"] if x["nom"] == "compte C"][0]
ok(c["pct"] == 0 and c["statut"] == "reserve" and "remis à zéro" in c["texte"], f"compte C : {c['pct']} %, {c['texte']}")
ok(c["remise"] == int(t("2026-01-12T10:00")), "prochaine remise une semaine plus tard")
ok(r["plan"]["retour_type"] == "remise" and "remise à zéro de compte A" in r["plan"]["prevision"],
   f"plus d'épuisé : horizon = remise à zéro ({r['plan']['prevision']})")

print("7. forfait.json prêté seulement au compte qu'il nomme")
r = C.calculer(base(), forfait(70, 20, "compte A"), NOW)
a = [x for x in r["comptes"] if x["nom"] == "compte A"][0]
ok(a["pct"] == 70 and a["source"] == "forfait.json", "forfait de compte A : 70 % pour compte A")
d = base()
d["comptes"][0]["actif"], d["comptes"][1]["actif"] = False, True          # comptes.json passé à B avant forfait.json
r = C.calculer(d, forfait(83, 20, "compte A"), NOW)
b = [x for x in r["comptes"] if x["nom"] == "compte B"][0]
ok(b["pct"] == 0 and b["source"] == "comptes.json", "compte B actif, forfait encore de compte A : B garde 0 %")
r = C.calculer(base(), forfait(70, 20), NOW)
ok([x for x in r["comptes"] if x["nom"] == "compte A"][0]["pct"] == 70, "forfait sans nom : prêté à l'actif")

print("8. seuil_relais")
p = C.calculer(base(seuil_relais=95), None, NOW)["plan"]
ok(p["budget"] == 110 and p["seuil_relais"] == 95, f"budget (95-80) + (95-0) = 110 ({p['budget']})")
ok(C.calculer(base(seuil_relais=0), None, NOW)["plan"]["seuil_relais"] == 100, "seuil_relais invalide : 100")

print("9. horizon sans nom (plan.prochain_retour seul)")
d = {"comptes": [{"nom": "compte A", "actif": True, "pct_semaine": 90}], "mesures": dict(MES),
     "plan": {"phase": 1, "fin_phase_1": "2026-01-09T00:00:00Z", "prochain_retour": "2026-01-08T22:00:00Z"}}
p = C.calculer(d, None, NOW)["plan"]
ok(p["tient"] is False and p["retour_nom"] == "", "budget court, horizon sans nom")
ok("trou de" in p["prevision"] and "le retour de" not in p["prevision"], f"phrase sans nom : {p['prevision']}")

print("10. balayage : jamais de « trou de 0 min »")
rnd = random.Random(7)
mauvais = 0
for _ in range(5000):
    d = base()
    d["comptes"][0]["pct_semaine"] = rnd.uniform(0, 100)
    d["comptes"][1]["pct_semaine"] = rnd.uniform(0, 100)
    d["seuil_relais"] = rnd.choice([None, 90, 95, 100])
    now = NOW + rnd.uniform(-40, 80) * 3600
    r = C.calculer(d, forfait(d["comptes"][0]["pct_semaine"], rnd.uniform(0, 100)), now)
    for txt in (r["plan"]["prevision"], r["plan"]["mesure"]):
        if "trou de 0 min" in txt:
            mauvais += 1
ok(mauvais == 0, f"{mauvais} « trou de 0 min » sur 5000 tirages")

print("11. compte actif sans fenêtre de 5 h (fenêtre « 5 heures » absente, seulement des fenêtres hebdo)")
d = base(rythme_mesure={"t": "2026-01-05T11:50:00Z", "points_h": 4.0})
d["comptes"][0]["fenetre_5h"] = False
f = {"maj": "2026-01-05T12:00:00Z", "compte": "compte A", "fenetres": [
    {"nom": "Hebdo · tous les modèles", "pct_utilise": 10, "remise_a_zero": "2026-01-12T00:00:00Z"},
    {"nom": "Hebdo · autre modèle", "pct_utilise": 0, "remise_a_zero": "2026-01-12T00:00:00Z"},
    {"nom": "5 heures", "pct_utilise": None, "remise_a_zero": None, "absente": True}]}
r = C.calculer(d, f, NOW)
a = [x for x in r["comptes"] if x["nom"] == "compte A"][0]
ok(a["pct"] == 10 and a["source"] == "forfait.json", f"sans 5 h : 10 % lu dans forfait.json ({a['pct']}, {a['source']})")
ok("5 h" not in r["plan"]["ligne"] and r["plan"]["cible_5h"] is None, f"sans 5 h : la ligne du plan ne parle pas de fenêtre de 5 h ({r['plan']['ligne']})")
ok(r["plan"]["rythme_mesure"] == 4.0, f"sans 5 h : rythme mesuré de comptes.json → rythme_mesure ({r['plan']['rythme_mesure']})")
ok("sans fenêtre de 5 h" in r["plan"]["detail"], "sans 5 h : le détail le dit")
d2 = base(rythme_mesure={"t": "2026-01-05T08:00:00Z", "points_h": 4.0})
d2["comptes"][0]["fenetre_5h"] = False
ok(C.calculer(d2, f, NOW)["plan"]["rythme_mesure"] is None, "sans 5 h : rythme_mesure de plus de 2 h ignoré")
r2 = C.calculer(base(), forfait(10, 40, "compte A"), NOW)
ok(r2["plan"]["cible_5h"] == 98 and "fenêtre de 5 h → 98 %" in r2["plan"]["ligne"], f"avec 5 h : ligne inchangée ({r2['plan']['ligne']})")
ok(r2["plan"]["rythme_mesure"] is not None, "avec 5 h : rythme mesuré par la fenêtre de 5 h")

print("\n" + ("tout vert" if not ECHECS else f"{len(ECHECS)} échec(s)"))
sys.exit(1 if ECHECS else 0)
