"""comptes_relais.py : bloc « Comptes en relais » du studio (plusieurs comptes Claude qui se relaient).

Facultatif : sans comptes.json, calculer() rend None et la page n'affiche rien.

comptes.json (écrit par Claude ou à la main) :
  {"maj": "2026-01-01T12:00:00",
   "comptes": [{"nom": "compte A", "actif": true, "pct_semaine": 40, "remise_semaine": "2026-01-05T00:00:00Z", "note": "…"}, …],
   "mesures": {"semaine_par_fenetre_5h_pleine": 14,          # points de semaine que coûte une fenêtre de 5 h pleine (~98 %)
               "semaine_par_heure_plein_regime": 3.0},       # points de semaine par heure à plein régime
   "plan": {"phase": 1, "fin_phase_1": "…Z", "prochain_retour": "…Z"},   # tout facultatif
   "seuil_epuise": 98}                                      # % de semaine à partir duquel un compte est « épuisé »
forfait.json (compte actif, plus frais) : sa fenêtre la plus longue donne le % de semaine du compte actif,
  sa fenêtre la plus courte (« 5 heures ») le rythme mesuré.

Plan : phase 1 = plein régime jusqu'à fin_phase_1 ; phase 2 = rythme lissé (budget restant / heures jusqu'au prochain
retour d'un compte). Cible de la fenêtre de 5 h = rythme × 5 × (98 / semaine_par_fenetre_5h_pleine), plafonnée à 98 %.
Prévision : « ça tient jusqu'au retour de … » ou « trou de N h avant le retour de … » ; plus la même au rythme mesuré.
Sans dépendance (bibliothèque standard), testable seul : python -I -B comptes_relais.py <comptes.json> [forfait.json]
"""
import calendar
import json
import re
import sys
import time

JOURS = {"fr": ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."], "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
PLAFOND_5H = 98.0


def iso_t(s):
    """ISO 8601 -> secondes epoch. « Z » ou décalage = UTC ; sans fuseau = heure locale de la machine. None si illisible."""
    if not s or not isinstance(s, str):
        return None
    m = re.match(r"^(\d{4})-(\d\d)-(\d\d)[T ](\d\d):(\d\d)(?::(\d\d))?(?:\.\d+)?\s*(Z|[+-]\d\d:?\d\d)?$", s.strip())
    if not m:
        return None
    a, mo, j, h, mi, se, tz = m.groups()
    tup = (int(a), int(mo), int(j), int(h), int(mi), int(se or 0), 0, 0, -1)
    try:
        if tz is None:
            return time.mktime(tup)
        t = calendar.timegm(tup)
        if tz != "Z":
            sg = 1 if tz[0] == "+" else -1
            hh, mm = int(tz[1:3]), int(tz[-2:])
            t -= sg * (hh * 3600 + mm * 60)
        return float(t)
    except (OverflowError, ValueError):
        return None


def nombre(v):
    try:
        f = float(v)
        return f if f == f and abs(f) != float("inf") else None
    except (TypeError, ValueError):
        return None


def jour_txt(t, lg="fr"):
    lt = time.localtime(t)
    return f"{JOURS[lg][lt.tm_wday]} {lt.tm_mday:02d}/{lt.tm_mon:02d} {lt.tm_hour:02d}:{lt.tm_min:02d}"


def num(x, lg="fr", d=1):
    s = f"{x:.{d}f}"
    return s.replace(".", ",") if lg == "fr" else s


def heures(h, lg="fr"):
    h = max(0, h)
    if h < 1:
        return f"{round(h * 60)} min"
    return f"{round(h)} h"


def fenetres(forfait):
    out = []
    for f in (forfait or {}).get("fenetres") or []:
        if not isinstance(f, dict):
            continue
        p, r = nombre(f.get("pct_utilise")), iso_t(f.get("remise_a_zero"))
        if p is None:
            continue
        out.append({"nom": str(f.get("nom") or ""), "pct": p, "remise": r})
    return out


def duree_fenetre_h(nom, defaut=5.0):
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(h|heure|hour)", nom or "", re.I)
    return float(m.group(1).replace(",", ".")) if m else defaut


def calculer(comptes, forfait=None, maintenant=None):
    """Rend le bloc (dict) ou None si comptes.json est absent ou sans compte."""
    if not isinstance(comptes, dict) or not isinstance(comptes.get("comptes"), list):
        return None
    now = time.time() if maintenant is None else float(maintenant)
    seuil = nombre(comptes.get("seuil_epuise")) or 98.0
    mes = comptes.get("mesures") if isinstance(comptes.get("mesures"), dict) else {}
    plan = comptes.get("plan") if isinstance(comptes.get("plan"), dict) else {}
    par_fen = nombre(mes.get("semaine_par_fenetre_5h_pleine"))
    plein = nombre(mes.get("semaine_par_heure_plein_regime"))
    facteur = PLAFOND_5H / par_fen if par_fen and par_fen > 0 else None   # % de fenêtre de 5 h par point de semaine

    fen = fenetres(forfait) if isinstance(forfait, dict) else []
    t_forfait = iso_t((forfait or {}).get("maj")) if isinstance(forfait, dict) else None
    longues = [f for f in fen if f["remise"]]
    hebdo = None
    if longues:
        tard = max(f["remise"] for f in longues)
        hebdo = max((f for f in longues if f["remise"] >= tard - 3600), key=lambda f: f["pct"])
        if len(longues) > 1 and hebdo["remise"] == min(f["remise"] for f in longues):
            hebdo = None                                   # une seule échéance : pas de fenêtre « semaine » distincte
    courte = min(longues, key=lambda f: f["remise"]) if len(longues) > 1 else None

    lignes = []
    for c in comptes["comptes"]:
        if not isinstance(c, dict):
            continue
        nom = str(c.get("nom") or "compte")[:40]
        actif = c.get("actif") is True
        p = nombre(c.get("pct_semaine"))
        r = iso_t(c.get("remise_semaine"))
        source = "comptes.json"
        if actif and hebdo is not None:
            p, source = hebdo["pct"], "forfait.json"
            r = hebdo["remise"] or r
        remis = bool(r and r <= now)
        if remis:
            p = 0.0
            while r <= now:                                # prochaine remise : une semaine plus tard
                r += 7 * 86400
        p = max(0.0, min(100.0, p if p is not None else 0.0))
        statut = "actif" if actif else ("epuise" if p >= seuil else "reserve")
        if statut == "actif":
            txt, txt_en = "actif", "active"
        elif statut == "epuise":
            txt = f"épuisé, revient {jour_txt(r)}" if r else "épuisé"
            txt_en = f"used up, back {jour_txt(r, 'en')}" if r else "used up"
        else:
            txt, txt_en = ("en réserve (remis à zéro)", "in reserve (reset)") if remis else ("en réserve", "in reserve")
        lignes.append({"nom": nom, "actif": actif, "pct": round(p, 1), "statut": statut, "texte": txt, "texte_en": txt_en,
                       "remise": int(r) if r else None, "remise_txt": jour_txt(r) if r else "", "remise_txt_en": jour_txt(r, "en") if r else "",
                       "source": source, "note": str(c.get("note") or "")[:160]})
    if not lignes:
        return None

    dispo = [x for x in lignes if x["statut"] != "epuise"]
    budget = sum(max(0.0, 100.0 - x["pct"]) for x in dispo)
    # prochain retour : le compte épuisé qui revient le plus tôt ; sinon la première remise à venir ; sinon le plan
    cand = [x for x in lignes if x["statut"] == "epuise" and x["remise"] and x["remise"] > now] or \
           [x for x in lignes if x["remise"] and x["remise"] > now]
    if cand:
        ret = min(cand, key=lambda x: x["remise"])
        retour, retour_nom = float(ret["remise"]), ret["nom"]
    else:
        retour, retour_nom = iso_t(plan.get("prochain_retour")), ""
    H = (retour - now) / 3600 if retour and retour > now else None

    fin1 = iso_t(plan.get("fin_phase_1"))
    phase = int(nombre(plan.get("phase")) or 1)
    if phase == 1 and fin1 and fin1 <= now:
        phase = 2
    if phase == 1 and not fin1:
        phase = 2 if H else 1

    def cible_de(r):
        return min(PLAFOND_5H, r * 5 * facteur) if facteur and r is not None else None

    ret_fr = f"{retour_nom} ({jour_txt(retour)})" if retour and retour_nom else (jour_txt(retour) if retour else "")
    ret_en = f"{retour_nom} ({jour_txt(retour, 'en')})" if retour and retour_nom else (jour_txt(retour, "en") if retour else "")

    def prevision(rythmes):
        """rythmes : [(durée_h ou None = jusqu'au bout, pts/h)]. Rend (tient, t_fin, trou_h)."""
        b, t = budget, now
        for d, r in rythmes:
            if r is None or r <= 0:
                return True, None, 0.0
            dur = d if d is not None else float("inf")
            if b <= r * dur:
                t_fin = t + b / r * 3600
                if retour and t_fin < retour:
                    return False, t_fin, (retour - t_fin) / 3600
                return True, t_fin, 0.0
            b -= r * dur
            t += dur * 3600
        return True, None, 0.0

    rythme = cible = rythme2 = None
    if phase == 1:
        rythme = plein
        cible = PLAFOND_5H if plein else None
        h1 = max(0.0, (fin1 - now) / 3600) if fin1 else None
        if H is not None and h1 is not None:
            h1 = min(h1, H)
            reste2 = budget - (plein or 0) * h1
            h2 = H - h1
            rythme2 = reste2 / h2 if plein and h2 > 0 and reste2 > 0 else (0.0 if plein and h2 > 0 else None)
            if plein and rythme2 is not None:
                rythme2 = min(rythme2, plein)
        tient, t_fin, trou = prevision([(h1, plein), (None, rythme2 if rythme2 else plein)]) if plein else (True, None, 0.0)
        if plein and rythme2 == 0.0:
            tient, t_fin, trou = prevision([(None, plein)])
    else:
        if H:
            rythme = budget / H
            if plein:
                rythme = min(rythme, plein)
        else:
            rythme = plein
        cible = cible_de(rythme)
        tient, t_fin, trou = (prevision([(None, rythme)]) if rythme else ((budget > 0), None, (H or 0.0) if budget <= 0 else 0.0))
        if budget <= 0 and H:
            tient, t_fin, trou = False, now, H

    # rythme mesuré : fenêtre courte de forfait.json (% utilisé depuis son début)
    mesure = None
    if courte and facteur and t_forfait:
        dh = duree_fenetre_h(courte["nom"])
        ecoule = (t_forfait - (courte["remise"] - dh * 3600)) / 3600
        if 0.25 <= ecoule <= dh:
            mesure = (courte["pct"] / ecoule) / facteur

    def phrase(ok, t_fin, trou, lg):
        if not retour:
            if t_fin:
                return (f"ça tient jusqu'à {jour_txt(t_fin)}" if lg == "fr" else f"lasts until {jour_txt(t_fin, 'en')}")
            return "ça tient" if lg == "fr" else "it holds"
        if ok:
            return (f"ça tient jusqu'au retour de {ret_fr}" if lg == "fr" else f"holds until {ret_en} is back")
        qui = retour_nom or (jour_txt(retour) if lg == "fr" else jour_txt(retour, "en"))
        return (f"à sec {jour_txt(t_fin)}, trou de {heures(trou)} avant le retour de {qui}" if lg == "fr"
                else f"dry {jour_txt(t_fin, 'en')}, {heures(trou, 'en')} gap before {qui} is back")

    prev, prev_en = phrase(tient, t_fin, trou, "fr"), phrase(tient, t_fin, trou, "en")
    mes_fr = mes_en = ""
    m_tient, m_fin, m_trou = True, None, 0.0
    if mesure:
        m_tient, m_fin, m_trou = prevision([(None, mesure)])
        mes_fr = f"au rythme mesuré ({num(mesure)} pt/h) : {phrase(m_tient, m_fin, m_trou, 'fr')}"
        mes_en = f"at the measured pace ({num(mesure, 'en')} pt/h): {phrase(m_tient, m_fin, m_trou, 'en')}"

    morceaux, morceaux_en = [f"Phase {phase}"], [f"Phase {phase}"]
    if cible is not None:
        morceaux.append(f"fenêtre de 5 h → {round(cible)} %")
        morceaux_en.append(f"5-hour window → {round(cible)}%")
    if rythme is not None:
        morceaux.append(f"{num(rythme)} pt/h")
        morceaux_en.append(f"{num(rythme, 'en')} pt/h")
    morceaux.append(prev)
    morceaux_en.append(prev_en)

    detail = [f"Budget de semaine des comptes disponibles : {round(budget)} points ({', '.join(x['nom'] + ' ' + str(round(100 - x['pct'])) for x in dispo) or 'aucun'})."]
    detail_en = [f"Weekly budget of the available accounts: {round(budget)} points."]
    if phase == 1:
        if fin1:
            detail.append(f"Phase 1 : plein régime (fenêtre de 5 h à 97-99 %) jusqu'à {jour_txt(fin1)}.")
            detail_en.append(f"Phase 1: full speed (5-hour window at 97-99%) until {jour_txt(fin1, 'en')}.")
        if rythme2 is not None:
            c2 = cible_de(rythme2)
            detail.append(f"Puis phase 2 : {num(rythme2)} pt/h" + (f", fenêtre de 5 h vers {round(c2)} %" if c2 is not None else "") + ".")
            detail_en.append(f"Then phase 2: {num(rythme2, 'en')} pt/h" + (f", 5-hour window around {round(c2)}%" if c2 is not None else "") + ".")
    else:
        detail.append("Phase 2 : rythme lissé = budget restant / heures jusqu'au prochain retour d'un compte.")
        detail_en.append("Phase 2: smoothed pace = budget left / hours until the next account is back.")
    if retour:
        detail.append(f"Prochain retour : {ret_fr}" + (f", dans {heures(H)}" if H else "") + ".")
        detail_en.append(f"Next account back: {ret_en}.")
    if mes_fr:
        detail.append(mes_fr[0].upper() + mes_fr[1:] + ".")
        detail_en.append(mes_en[0].upper() + mes_en[1:] + ".")

    return {
        "maj": int(now), "comptes": lignes,
        "plan": {
            "phase": phase, "cible_5h": None if cible is None else round(cible), "rythme_cible": None if rythme is None else round(rythme, 2),
            "rythme_phase2": None if rythme2 is None else round(rythme2, 2), "rythme_mesure": None if mesure is None else round(mesure, 2),
            "budget": round(budget, 1), "retour": int(retour) if retour else None, "retour_nom": retour_nom,
            "tient": bool(tient), "a_sec": int(t_fin) if t_fin else None, "trou_h": round(trou, 1),
            "mesure_tient": bool(m_tient), "mesure_trou_h": round(m_trou, 1) if mesure else None,
            "prevision": prev, "prevision_en": prev_en, "mesure": mes_fr, "mesure_en": mes_en,
            "ligne": " · ".join(morceaux), "ligne_en": " · ".join(morceaux_en),
            "detail": "\n".join(detail), "detail_en": "\n".join(detail_en),
        },
    }


def lire(chemin):
    try:
        with open(chemin, encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return None


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    print(json.dumps(calculer(lire(sys.argv[1]), lire(sys.argv[2]) if len(sys.argv) > 2 else None), ensure_ascii=False, indent=1))
