# -*- coding: utf-8 -*-
"""Questionnaire adaptatif : chaque réponse oriente les suivantes (Python standard uniquement).

Jumeau du bloc ADAPTATION de studio.html (même logique, mêmes données : le bloc « adaptation » et les
« variantes » de questions.<langue>.json, produits par outils/construire_questions.py). Sert au repli
conversation (outils/questionnaire.py) et aux essais (outils/essai_questionnaire.py, qui compare les deux).

- deduire(qf, reponses, exclure)  : réponses déduites des règles et du pitch (jamais à la place d'une réponse
                                    de l'utilisateur ; une déduction dont la cause a changé disparaît) ;
- appliquer(qf, rq, exclure)      : met ces déductions dans le fichier de réponses (ajouts, retraits) ;
- suivante(qf, reponses, …)       : prochaine question jamais tranchée (pas de répétition) ;
- titre(qf, q, reponses)          : la question reformulée selon les choix faits ;
- acquis(qf, reponses, sauf)      : le rappel court de ce qui est déjà acquis.
"""
import re
import unicodedata

VIAS_DEDUITES = ("regle", "pitch")


def norm(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if not ("̀" <= c <= "ͯ"))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _val(reponses, cle):
    r = reponses.get(cle)
    return r.get("valeur") if isinstance(r, dict) else None


def cond(si, reponses):
    """Conditions « si » : toutes les clés, tous les opérateurs vrais. Une clé sans réponse rend egal, dans,
    seul faux ; different_de et aucun_de vrais ; existe selon sa valeur."""
    if not si:
        return True
    for cle, c in si.items():
        v = _val(reponses, cle)
        absent = v is None
        liste = v if isinstance(v, list) else [v]
        for op, x in c.items():
            if op == "egal":
                ok = not absent and x in liste
            elif op == "different_de":
                ok = absent or x not in liste
            elif op == "dans":
                ok = not absent and any(y in x for y in liste)
            elif op == "existe":
                ok = (not absent) if x else absent
            elif op == "seul":
                ok = not absent and liste == [x]
            elif op == "aucun_de":
                ok = absent or not any(y in x for y in liste)
            else:
                ok = True
            if not ok:
                return False
    return True


def question(qf, cle):
    for q in qf.get("questions", []):
        if q.get("id") == cle:
            return q
    return None


def deduites_du_pitch(qf, pitch):
    """{clé: (valeur, mot)} : mots entiers du pitch ; deux valeurs pour une question à choix unique = rien."""
    n = " " + norm(pitch) + " "
    trouve = {}
    for m in (qf.get("adaptation") or {}).get("pitch", []):
        mot = next((w for w in m["mots"] if norm(w) and (" " + norm(w) + " ") in n), None)
        if mot:
            trouve.setdefault(m["cle"], []).append((m["valeur"], mot))
    res = {}
    for cle, l in trouve.items():
        q = question(qf, cle)
        if not q:
            continue
        valeurs = []
        for v, _ in l:
            if v not in valeurs:
                valeurs.append(v)
        if q.get("type") == "multi":
            res[cle] = (valeurs, l[0][1])
        elif len(valeurs) == 1:
            res[cle] = (valeurs[0], l[0][1])
    return res


def deduire(qf, reponses, exclure=()):
    """Toutes les réponses déduites, à partir des seules réponses non déduites (base). Ordre : pitch puis règles,
    jusqu'à ce que plus rien ne change. Rend {clé: réponse} pour les clés absentes de la base."""
    ad = qf.get("adaptation") or {}
    textes = ad.get("textes") or {}
    base = {k: v for k, v in reponses.items() if isinstance(v, dict) and v.get("via") not in VIAS_DEDUITES}
    exclure = set(exclure or ())
    cur = dict(base)
    ajout = {}
    p = base.get("vision.pitch")
    if p and isinstance(p.get("valeur"), str) and p.get("source") == "utilisateur":
        for cle, (v, mot) in sorted(deduites_du_pitch(qf, p["valeur"]).items()):
            if cle in cur or cle in exclure:
                continue
            r = {"valeur": v, "source": "deduit", "via": "pitch",
                 "raison": (textes.get("raison_pitch") or "pitch : {mot}").replace("{mot}", mot)}
            cur[cle] = ajout[cle] = r
    for _ in range(20):
        change = False
        for regle in ad.get("regles", []):
            if not cond(regle.get("si"), cur):
                continue
            for cle, v in regle.get("fixe", {}).items():
                if cle in cur or cle in exclure:
                    continue
                r = {"valeur": v, "source": "deduit", "via": "regle", "raison": regle.get("raison", "")}
                cur[cle] = ajout[cle] = r
                change = True
        if not change:
            break
    return ajout


def difference(qf, reponses, exclure=()):
    """(à écrire {clé: réponse}, à retirer [clés]) pour que les déductions du fichier suivent les réponses."""
    d = deduire(qf, reponses, exclure)
    ecrire = {k: r for k, r in d.items()
              if not isinstance(reponses.get(k), dict) or reponses[k].get("valeur") != r["valeur"]
              or reponses[k].get("via") != r["via"]}
    retirer = [k for k, r in reponses.items()
               if isinstance(r, dict) and r.get("via") in VIAS_DEDUITES and k not in d]
    return ecrire, retirer


def appliquer(qf, rq, exclure=(), horodatage=None):
    """Met les déductions dans rq (le contenu de reponses_questionnaire.json). Rend (écrites, retirées)."""
    rep = rq.setdefault("reponses", {})
    ecrire, retirer = difference(qf, rep, exclure)
    for k in retirer:
        rep.pop(k, None)
    for k, r in ecrire.items():
        r = dict(r)
        if horodatage:
            r["t"] = horodatage
        rep[k] = r
    return ecrire, retirer


def mode_de(rq):
    m = rq.get("mode")
    if m in ("rapide", "complet", "adoption"):
        return m
    return "complet" if _val(rq.get("reponses", {}), "accueil.mode") == "complet" else "rapide"


def incluse(q, reponses, mode, fixes=()):
    if q.get("chapitre") != "fin" and (q.get("seulement_rapide") if mode == "complet" else not q.get("rapide")):
        return False
    if not cond(q.get("si"), reponses):
        return False
    if q.get("id") in set(fixes or ()):
        return False
    if mode == "adoption" and (reponses.get(q.get("id")) or {}).get("via") == "analyse":
        return False
    return True


def tranchee(q, reponses, revoir=False):
    """Une question déjà tranchée n'est jamais reposée (le récapitulatif de fin reste toujours accessible)."""
    if q.get("chapitre") == "fin":
        return False
    r = reponses.get(q.get("id"))
    if not isinstance(r, dict):
        return False
    return not (revoir and r.get("source") == "a_confirmer")


def suivante(qf, reponses, mode, fixes=(), depuis=None, revoir=False):
    """Prochaine question à poser : la première non tranchée (depuis=None, reprise), ou la première après
    « depuis ». None = plus rien après."""
    tous = qf.get("questions", [])
    i0 = 0
    if depuis:
        idx = [k for k, q in enumerate(tous) if q.get("id") == depuis]
        i0 = idx[0] + 1 if idx else 0
    for q in tous[i0:]:
        if incluse(q, reponses, mode, fixes) and not tranchee(q, reponses, revoir):
            return q
    return None


def libelle(qf, cle, v):
    q = question(qf, cle) or {}
    lib = {c["id"]: c.get("libelle", c["id"]) for c in q.get("choix", [])}
    if isinstance(v, list):
        return ", ".join(str(lib.get(x, x)) for x in v)
    if isinstance(v, (dict, bool)) or v is None:
        return ""
    return str(lib.get(v, v))


def titre(qf, q, reponses):
    """Titre reformulé : la première variante vraie, {clé} remplacé par le libellé de la réponse."""
    for var in q.get("variantes") or []:
        if cond(var.get("si"), reponses):
            return re.sub(r"\{([a-z0-9_.]+)\}", lambda m: libelle(qf, m.group(1), _val(reponses, m.group(1))) or m.group(0), var["titre"])
    return q.get("titre", "")


def acquis(qf, reponses, sauf=None, maxi=6):
    """[{cle, valeur (libellé), source, raison}] des clés du rappel déjà réglées (hors « à confirmer »)."""
    out = []
    for cle in (qf.get("adaptation") or {}).get("acquis", []):
        r = reponses.get(cle)
        if cle == sauf or not isinstance(r, dict) or r.get("source") not in ("utilisateur", "deduit"):
            continue
        lib = libelle(qf, cle, r.get("valeur"))
        if lib:
            out.append({"cle": cle, "valeur": lib, "source": r["source"], "raison": r.get("raison", "")})
    return out[:maxi]
