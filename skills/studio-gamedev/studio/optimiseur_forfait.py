"""studio/optimiseur_forfait.py : « Optimiser le forfait » (interrupteur vert / gris à côté de la barre du forfait).
Plan optimiser ("Optimise the plan" switch next to the plan bar).

Coupé par défaut (réglage `forfait_optimise` de .studio/reglages.json). Allumé, à chaque relevé de forfait.json :
  1. note le relevé dans .studio/forfait_historique.json (un relevé par valeur de « maj », 48 au plus) ;
  2. calcule le rythme de chaque fenêtre (points gagnés par heure entre les deux derniers relevés) et sa projection
     au moment de sa remise à zéro (pct + rythme × heures restantes) ;
  3. écrit .studio/forfait_consigne.json, lue par Claude : nombre de postes cible, postes à ajouter ou à retirer, raison.

Règles (les mêmes qu'à la main) :
  - fenêtre courte (celle qui se remet à zéro le plus tôt, ex. « 5 heures ») projetée sous 90 % et forfait long (hebdo)
    pas épuisé avant sa remise à zéro : on AJOUTE des postes (agents en parallèle) ;
  - projetée au-dessus de 95 %, ou plus de 85 % utilisés avec plus de 20 min avant la remise à zéro, ou hebdo projeté
    au-delà de 100 % : on RETIRE les postes les moins prioritaires ;
  - entre les deux : on garde. En fin de semaine, la fenêtre longue vise juste sous 100 % (99 %) à sa remise à zéro.
  - la CHAÎNE CRITIQUE n'est jamais coupée : postes protégés du studio, poste de la chaîne active, poste de l'outil
    lourd (moteur), liste `chaine_critique` de studio.config.json.
  - au plus 3 postes ajoutés ou retirés par relevé, jamais plus de 12 postes (les 12 bureaux).

Sans fichier : `python -I -B optimiseur_forfait.py --projet <projet>` (relit forfait.json, etat.json, reglages.json,
écrit la consigne et l'affiche) ; `--json` pour la consigne brute. Bibliothèque standard seulement.
"""
import argparse
import datetime as dt
import math
import os
import re
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
if ICI not in sys.path:
    sys.path.insert(0, ICI)
import jsonio  # noqa: E402

REGLAGE = "forfait_optimise"
CIBLE_COURT = 90.0          # sous ce % projeté : on ajoute
PLAFOND_COURT = 95.0        # au-dessus : on retire
ALERTE_PCT = 85.0           # déjà plus de 85 % utilisés…
ALERTE_MARGE_MIN = 20.0     # … et plus de 20 min avant la remise à zéro : on retire
CIBLE_LONG = 99.0           # fenêtre longue (hebdo) : finir juste sous 100 %
PAS_MAX = 3                 # postes ajoutés ou retirés par relevé
POSTES_MAX = 12             # 12 bureaux
HISTO_MAX = 48
ECART_MIN_S = 120           # deux relevés à moins de 2 min : pas de rythme fiable
SPECIALISTE_RE = re.compile(r"(?:^|-)(?:specialiste|sp[eé]cialiste|interim|int[eé]rim|temp)(?:-|$)", re.I)
PROTEGES_DEFAUT = {"assistant", "coordinateur", "atelier", "chinois", "tyrannie", "sante", "unreal", "chef-unreal", "direction"}


def iso_t(s):
    """Date ISO -> secondes (fuseau respecté ; sans fuseau : heure locale). None si illisible."""
    s = str(s or "").strip()
    if not s:
        return None
    try:
        d = dt.datetime.fromisoformat(s[:-1] + "+00:00" if s.endswith("Z") else s)
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.astimezone()
    return d.timestamp()


def fenetres_valides(forfait):
    """[{nom, pct, remise_t}] des fenêtres lisibles (pct de 0 à 100)."""
    out = []
    for f in (forfait or {}).get("fenetres") or []:
        if not isinstance(f, dict):
            continue
        try:
            p = float(f.get("pct_utilise"))
        except (TypeError, ValueError):
            continue
        if not 0 <= p <= 100:
            continue
        out.append({"nom": str(f.get("nom") or "?"), "pct": p, "remise_t": iso_t(f.get("remise_a_zero"))})
    return out


LONG_RE = re.compile(r"hebdo|semaine|week|7\s*(?:j|d|jours|days)|sept", re.I)


def court_et_long(fen):
    """La fenêtre courte (ex. 5 h) et la longue (ex. hebdo), ou None. La longue se reconnaît à son nom (hebdo, semaine,
    week, 7 j) : en fin de semaine, elle peut se remettre à zéro avant la courte. Sinon : remise la plus lointaine."""
    datees = sorted([f for f in fen if f["remise_t"]], key=lambda f: f["remise_t"])
    if not datees:
        return (fen[0] if fen else None), None
    longue = next((f for f in datees if LONG_RE.search(f["nom"])), datees[-1] if len(datees) > 1 else None)
    courtes = [f for f in datees if f is not longue]
    if not courtes:
        return longue, None
    return courtes[0], longue


def noter_releve(histo, forfait):
    """Ajoute le relevé de forfait.json à l'historique (une fois par « maj »). Rend l'historique (liste)."""
    histo = [h for h in (histo if isinstance(histo, list) else []) if isinstance(h, dict) and h.get("t")]
    t = iso_t((forfait or {}).get("maj"))
    fen = fenetres_valides(forfait)
    if t is None or not fen:
        return histo
    if histo and abs(histo[-1]["t"] - t) < 1:
        return histo
    histo.append({"t": t, "fenetres": {f["nom"]: f["pct"] for f in fen}})
    histo.sort(key=lambda h: h["t"])
    return histo[-HISTO_MAX:]


def rythme(histo, nom):
    """Points par heure de la fenêtre `nom` entre les deux derniers relevés qui la portent. None si inconnu ou après
    une remise à zéro (le % a baissé)."""
    pts = [(h["t"], h["fenetres"][nom]) for h in histo if isinstance(h.get("fenetres"), dict) and nom in h["fenetres"]]
    if len(pts) < 2:
        return None
    (t1, p1), (t2, p2) = pts[-2], pts[-1]
    if t2 - t1 < ECART_MIN_S or p2 < p1:
        return None
    return (p2 - p1) / ((t2 - t1) / 3600.0)


def projection(pct, r, remise_t, maintenant):
    """% projeté au moment de la remise à zéro."""
    if r is None or not remise_t:
        return None
    return pct + r * max(0.0, (remise_t - maintenant) / 3600.0)


def chaine_critique(conf, postes, chaine=None):
    """Identifiants jamais retirés : protégés du studio, chaîne active, poste de l'outil lourd, `chaine_critique` de la config."""
    ids = set(PROTEGES_DEFAUT)
    try:
        import restructuration as rs
        ids |= set(getattr(rs, "PROTEGES", ()) or ())
    except Exception:
        pass
    conf = conf if isinstance(conf, dict) else {}
    for x in conf.get("chaine_critique") or []:
        if isinstance(x, str):
            ids.add(x)
    if conf.get("session_poste"):
        ids.add(str(conf["session_poste"]))
    for o in conf.get("outils_lourds") or []:
        if isinstance(o, dict) and o.get("poste"):
            ids.add(str(o["poste"]))
    m = conf.get("moteur")
    if isinstance(m, dict) and m.get("poste"):
        ids.add(str(m["poste"]))
    if isinstance(chaine, dict) and chaine.get("poste"):
        ids.add(str(chaine["poste"]))
    for p in postes or []:
        if isinstance(p, dict) and p.get("id") and ("moteur" in str(p["id"]) or p.get("protege") is True):
            ids.add(str(p["id"]))
    return ids


def priorite(p, rang_conf, ordre):
    """Plus petit = retiré en premier : spécialistes et intérimaires, puis recrues (les plus récentes d'abord),
    puis postes de la config (les derniers d'abord). `ordre` (ordre_equipe de la page) départage."""
    pid = str(p.get("id") or "")
    o = ordre.index(pid) if pid in ordre else len(ordre)
    if SPECIALISTE_RE.search(pid):
        return (0, -o, "")
    if p.get("genre") == "recrue":
        return (1, -o, -(iso_t(p.get("cree_le")) or 0))   # récente = retirée avant
    return (2, -o, -rang_conf.get(pid, 99))


def calculer(forfait, histo, postes, conf=None, reglages=None, chaine=None, maintenant=None):
    """La consigne (dict). Fonction pure : aucun fichier lu ni écrit."""
    maintenant = time.time() if maintenant is None else maintenant
    reglages = reglages if isinstance(reglages, dict) else {}
    conf = conf if isinstance(conf, dict) else {}
    postes = [p for p in (postes or []) if isinstance(p, dict) and p.get("id")]
    base = {"maj": dt.datetime.fromtimestamp(maintenant).astimezone().isoformat(timespec="seconds"), "actif": reglages.get(REGLAGE) is True,
            "decision": "coupe", "delta": 0, "cible": None, "actifs": None, "ajouter": [], "a_recruter": 0, "retirer": [], "proteges": [],
            "projection": {}, "rythme": {}, "raison": "Optimiseur coupé.", "raison_en": "Optimizer off.",
            "ligne": "Optimiseur coupé", "ligne_en": "Optimizer off"}
    if not base["actif"]:
        return base
    if reglages.get("pause"):
        base.update(decision="attendre", raison="Automatismes en pause (« Tout couper »).", raison_en="Automations paused (\"Stop all\").",
                    ligne="En pause", ligne_en="Paused")
        return base
    fen = fenetres_valides(forfait)
    c, l = court_et_long(fen)
    if not c:
        base.update(decision="attendre", raison="Pas de forfait.json lisible.", raison_en="No readable forfait.json.",
                    ligne="Attend le forfait", ligne_en="Waiting for plan data")
        return base
    travail = [p for p in postes if p.get("etat") == "travaille"]
    libres = [p for p in postes if p.get("etat") in ("disponible", "fini")]
    crit = chaine_critique(conf, postes, chaine)
    proteges_actifs = [p["id"] for p in travail if p["id"] in crit]
    actifs = len(travail)
    base.update(actifs=actifs, proteges=sorted(proteges_actifs), decision="garder", cible=actifs)
    rc, rl = rythme(histo, c["nom"]), (rythme(histo, l["nom"]) if l else None)
    pc, pl = projection(c["pct"], rc, c["remise_t"], maintenant), (projection(l["pct"], rl, l["remise_t"], maintenant) if l else None)
    base["rythme"] = {c["nom"]: None if rc is None else round(rc, 2)}
    base["projection"] = {c["nom"]: None if pc is None else round(pc, 1)}
    if l:
        base["rythme"][l["nom"]] = None if rl is None else round(rl, 2)
        base["projection"][l["nom"]] = None if pl is None else round(pl, 1)
    if pc is None:
        base.update(decision="attendre", raison="Il faut deux relevés du forfait pour mesurer le rythme.",
                    raison_en="Two plan readings are needed to measure the pace.", ligne="Attend un 2e relevé", ligne_en="Waiting for a 2nd reading")
        return base
    h_c = max(0.05, ((c["remise_t"] or maintenant) - maintenant) / 3600.0)
    min_c = h_c * 60
    # cible : le rythme se partage entre la session et les postes au travail (la session compte pour un)
    def cible_pour(pct, r, h, vise):
        if r is None or r <= 0:
            return None
        par_poste = r / (actifs + 1)
        return int(math.floor((vise - pct) / h / par_poste)) - 1
    cibles = [x for x in (cible_pour(c["pct"], rc, h_c, CIBLE_COURT),
                          cible_pour(l["pct"], rl, max(0.05, (l["remise_t"] - maintenant) / 3600.0), CIBLE_LONG) if l and pl is not None else None) if x is not None]
    cible = min(cibles) if cibles else actifs + 1
    cible = max(len(proteges_actifs), min(POSTES_MAX, cible))
    hebdo_ok = l is None or (l["pct"] < CIBLE_LONG and (pl is None or pl < CIBLE_LONG))
    pct_txt = f"{round(pc)} %"
    if pc > PLAFOND_COURT or (c["pct"] > ALERTE_PCT and min_c > ALERTE_MARGE_MIN) or (pl is not None and pl > 100):
        if pl is not None and pl > 100 and not (pc > PLAFOND_COURT or c["pct"] > ALERTE_PCT):
            raison = (f"{l['nom']} projeté à {round(pl)} % avant sa remise à zéro.", f"{l['nom']} projected at {round(pl)}% before its reset.")
            motif = (f"{l['nom']} {round(pl)} % projeté", f"{l['nom']} {round(pl)}% projected")
        elif pc > PLAFOND_COURT:
            raison = (f"{pct_txt} projeté à la remise à zéro de « {c['nom']} » (plafond {int(PLAFOND_COURT)} %).",
                      f"{round(pc)}% projected at the \"{c['nom']}\" reset (ceiling {int(PLAFOND_COURT)}%).")
            motif = (f"{pct_txt} projeté", f"{round(pc)}% projected")
        else:
            raison = (f"{round(c['pct'])} % déjà utilisés, remise à zéro dans {int(min_c)} min.", f"{round(c['pct'])}% already used, reset in {int(min_c)} min.")
            motif = (f"{round(c['pct'])} % utilisés", f"{round(c['pct'])}% used")
        retirables = sorted([p for p in travail if p["id"] not in crit],
                            key=lambda p: priorite(p, {x.get("id"): i for i, x in enumerate(conf.get("postes") or []) if isinstance(x, dict)},
                                                   list(reglages.get("ordre_equipe") or [])))
        n = min(PAS_MAX, len(retirables), max(1, actifs - cible))
        if n <= 0:
            base.update(decision="garder", raison=raison[0] + " Seule la chaîne critique travaille : rien à retirer.",
                        raison_en=raison[1] + " Only the critical chain is working: nothing to remove.",
                        ligne=f"Garder : {motif[0]}, chaîne critique seule", ligne_en=f"Keep: {motif[1]}, critical chain only")
            return base
        base.update(decision="retirer", delta=-n, cible=actifs - n, retirer=[p["id"] for p in retirables[:n]], raison=raison[0], raison_en=raison[1],
                    ligne=f"−{n} poste{'s' if n > 1 else ''} : {motif[0]}", ligne_en=f"−{n} desk{'s' if n > 1 else ''}: {motif[1]}")
        return base
    if pc < CIBLE_COURT and hebdo_ok and actifs < POSTES_MAX:
        n = min(PAS_MAX, POSTES_MAX - actifs, max(1, cible - actifs))
        rang = {x.get("id"): i for i, x in enumerate(conf.get("postes") or []) if isinstance(x, dict)}
        ordre = list(reglages.get("ordre_equipe") or [])
        ajout = [p["id"] for p in sorted(libres, key=lambda p: priorite(p, rang, ordre), reverse=True)][:n]
        base.update(decision="ajouter", delta=n, cible=actifs + n, ajouter=ajout, a_recruter=max(0, n - len(ajout)),
                    raison=f"{pct_txt} projeté à la remise à zéro de « {c['nom']} » : il reste du forfait à consommer.",
                    raison_en=f"{round(pc)}% projected at the \"{c['nom']}\" reset: plan left to use.",
                    ligne=f"+{n} poste{'s' if n > 1 else ''} : {pct_txt} projeté à la remise à zéro",
                    ligne_en=f"+{n} desk{'s' if n > 1 else ''}: {round(pc)}% projected at reset")
        return base
    if pc < CIBLE_COURT:
        base.update(raison=f"{pct_txt} projeté, mais le forfait long est presque épuisé.", raison_en=f"{round(pc)}% projected, but the long window is nearly used up.",
                    ligne=f"Garder {actifs} : hebdo presque plein", ligne_en=f"Keep {actifs}: weekly nearly full")
    else:
        base.update(raison=f"{pct_txt} projeté : dans la cible ({int(CIBLE_COURT)} à {int(PLAFOND_COURT)} %).",
                    raison_en=f"{round(pc)}% projected: on target ({int(CIBLE_COURT)} to {int(PLAFOND_COURT)}%).",
                    ligne=f"Garder {actifs} poste{'s' if actifs > 1 else ''} : {pct_txt} projeté", ligne_en=f"Keep {actifs} desk{'s' if actifs != 1 else ''}: {round(pc)}% projected")
    return base


def passer(studio, conf=None, postes=None, chaine=None, maintenant=None):
    """Un passage (alimentation ou ligne de commande) : note le relevé, calcule et écrit la consigne. Rend la consigne."""
    reglages = jsonio.lire(os.path.join(studio, "reglages.json"), {}) or {}
    forfait = jsonio.lire(os.path.join(studio, "forfait.json"), None)
    ch_h = os.path.join(studio, "forfait_historique.json")
    histo = jsonio.lire(ch_h, [])
    if isinstance(forfait, dict):
        neuf = noter_releve(histo, forfait)
        if neuf != histo:
            jsonio.ecrire(ch_h, neuf)
        histo = neuf
    if conf is None:
        conf = jsonio.lire(os.path.join(studio, "studio.config.json"), {}) or {}
    if postes is None:
        etat = jsonio.lire(os.path.join(studio, "etat.json"), {}) or {}
        postes, chaine = etat.get("postes") or [], etat.get("chaine_active")
    cons = calculer(forfait if isinstance(forfait, dict) else None, histo if isinstance(histo, list) else [], postes, conf,
                    reglages if isinstance(reglages, dict) else {}, chaine, maintenant)
    ch_c = os.path.join(studio, "forfait_consigne.json")
    ancienne = jsonio.lire(ch_c, None)
    comparer = lambda d: {k: v for k, v in (d or {}).items() if k != "maj"} if isinstance(d, dict) else d
    if comparer(ancienne) != comparer(cons):
        jsonio.ecrire(ch_c, cons)
    return cons


def main(argv=None):
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--projet", default=".", help="dossier du projet (contient .studio/)")
    ap.add_argument("--json", action="store_true", help="affiche la consigne brute")
    a = ap.parse_args(argv)
    studio = os.path.join(os.path.abspath(a.projet), ".studio")
    if not os.path.isdir(studio):
        raise SystemExit(f"Pas de dossier .studio / no .studio folder: {studio}")
    cons = passer(studio)
    if a.json:
        import json
        print(json.dumps(cons, ensure_ascii=False, indent=1))
    else:
        conf = jsonio.lire(os.path.join(studio, "studio.config.json"), {}) or {}
        en = str(conf.get("langue") or "fr")[:2].lower() == "en"
        print(cons["ligne_en" if en else "ligne"] + " | " + cons["raison_en" if en else "raison"])
        if cons["ajouter"] or cons["a_recruter"]:
            print(("add: " if en else "ajouter : ") + ", ".join(cons["ajouter"] + ([f"+{cons['a_recruter']} " + ("to hire" if en else "à recruter")] if cons["a_recruter"] else [])))
        if cons["retirer"]:
            print(("remove: " if en else "retirer : ") + ", ".join(cons["retirer"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
