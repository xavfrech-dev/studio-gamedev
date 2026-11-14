"""Cloche du studio : déposer ce qui attend l'utilisateur, pour qu'il le règle d'un clic (Python standard uniquement).

Studios jumeaux : ce fichier a un jumeau dans l'autre studio (ici : studio/outils/cloche.py). Dossier visé : --dossier <dossier des fichiers du studio> ; sinon, avec
--projet <projet>, <projet>/.studio ; sinon le dossier de ce script s'il contient decisions.json ou etat.json.

  python -I cloche.py afaire  --id fab-arbres --titre "Ajouter le pack d'arbres depuis Fab" --genre fab --lien https://www.fab.com/… [--detail …] [--option id=libellé …] [--recommande id]
  python -I cloche.py depense --id tripo-credits --question "Racheter 1000 crédits Tripo ?" --montant 10 --service Tripo --pourquoi "…" [--devise €]
  python -I cloche.py attend  --cle <clé de demandes/statuts.json> --question "Je garde l'ancien ciel ou le nouveau ?"
  python -I cloche.py fait    --id fab-arbres             (à-faire réglé : il quitte la cloche)
  python -I cloche.py liste                                (ce qui attend encore, en JSON)
  python -I cloche.py decider <id> [--choix X] [--raison "…"] [--absence | --present]
                                                           (le coordinateur tranche une décision ouverte à la place de l'utilisateur)
  python -I cloche.py reservees                            (décisions ouvertes gardées pour l'utilisateur, et celles que le coordinateur peut trancher)
  python -I cloche.py proposer --id <base> --titre "Lancer la tâche V1-12 ?" --raison "…" [--detail …] [--poste p] [--origine suggestion:<id>] [--action "…"] [--langue en]
                                                           (F : proposition à un clic « Faire » (★) / « Plus tard », 3 ouvertes au plus)
  python -I cloche.py note --genre ordre|relance|roadmap|reversible --titre "…" --raison "…"
                                                           (F : petite décision prise seul par l'assistant, notée dans decisions.json)

Assistant actif (proposer, note ; references/point_equipe.md du skill) :
  proposer : décision « ouverte » genre « proposition », id prop-<base>-<date>, choix faire (★) / plus_tard, raison, origine, action.
  Refus code 2 : déjà 3 propositions ouvertes (une de même base est remplacée), ou « Plus tard » répondu à cette base il y a moins
  de 2 h. Refus code 3 : une dépense (passe par « depense », jamais d'étoile). Une proposition réservée (publication, suppression…)
  est posée, mais seul l'utilisateur la tranche (decider la refuse). La réponse arrive dans reponses.json : « faire » vaut accord.
  note : décision déjà « repondue » (genre petite_decision, decide_par « assistant » ou « assistant (absence) », raison, en_absence).
  Seulement la liste blanche : ordre des tâches prêtes, relance d'un agent figé, statut de roadmap prouvé par un commit, choix
  réversible sans coût. Refus code 3 si le texte touche une chose réservée (dépense, suppression, publication, système, compte).

Décider à la place (decider) : choix par défaut = la recommandation (★) ; un autre choix exige --raison.
  Écrit la réponse dans reponses.json {id, choix, texte_libre, repondu_le, decide_par, raison} et passe la décision à
  « repondue » dans decisions.json avec reponse, repondue_le, decide_par, decide_le, raison, en_absence, recommandation_suivie.
  decide_par = « coordinateur (absence) » si reglages.json dit mode_absent (ou --absence), sinon « coordinateur ».
  REFUS (code 3, rien n'est écrit) des décisions réservées à l'utilisateur : dépense (champ depense, type depense, montant,
  ou mots d'argent : €, crédits, achat, abonnement, paiement…), suppression, publication (publier, push, mise en ligne…),
  réglage de Windows ou du système, compte ou identifiants, ou décision marquée reserve_utilisateur (ou tout champ reserve_<qui> vrai) /
  reserve: depense|suppression|publication|systeme|compte (voir references/absence.md du skill).
  Les mots sont cherchés dans la question, le titre et l'option choisie. Code 2 : décision introuvable, déjà réglée, choix invalide.

Où ça va :
  afaire  -> a_faire.json         [{id, titre, detail, genre: fab|reconnexion|ecoute|autre, lien, options, recommande, statut: a_faire, cree_le}]
                                   la réponse arrive dans reponses.json avec l'id « afaire:<id> » : agis, puis « fait ».
  depense -> decisions.json       décision « ouverte » avec depense {montant, devise, service, pourquoi} : jamais d'étoile,
                                   rien n'est dépensé sans « J'accepte » (réponse dans reponses.json, id de la décision).
  attend  -> demandes/statuts.json statut « attend_utilisateur » + question : « <agent> attend ta réponse » sous la cloche.
                                   Repasse le statut à « lancé » ou « fini » dès que la réponse est là.
Écriture atomique ; rien n'est effacé ; une entrée de même id est remplacée.
"""
import argparse
import json
import os
import re
import sys
import time

if os.path.dirname(os.path.dirname(os.path.abspath(__file__))) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import jsonio  # noqa: E402  (C4 : studio/jsonio.py, lecture avec BOM, écriture atomique communes)

GENRES = ("fab", "reconnexion", "ecoute", "autre")


def maintenant():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def lire(chemin, defaut):
    try:
        return jsonio.lire_strict(chemin)
    except FileNotFoundError:
        return defaut
    except Exception as e:
        sys.exit(f"{chemin} illisible ({e}) : rien n'est écrit")


def ecrire(chemin, donnees):
    jsonio.ecrire(chemin, donnees)


def dossier(a):
    if a.dossier:
        return a.dossier
    if a.projet:
        return os.path.join(a.projet, ".studio")
    ici = os.path.dirname(os.path.abspath(__file__))
    if any(os.path.exists(os.path.join(ici, x)) for x in ("decisions.json", "etat.json")):
        return ici
    sys.exit("dossier du studio inconnu : --dossier <dossier> ou --projet <projet>")


def liste_de(v, cle):
    return v if isinstance(v, list) else (v.get(cle) if isinstance(v, dict) and isinstance(v.get(cle), list) else [])


def options(brut):
    out = []
    for o in brut or []:
        i, _, l = o.partition("=")
        if not i.strip():
            sys.exit(f"option invalide : {o!r} (forme id=libellé)")
        out.append({"id": i.strip(), "libelle": (l or i).strip()})
    return out


# Ce que le coordinateur ne tranche jamais à la place de l'utilisateur, même en son absence (decider refuse, code 3).
RESERVES = {
    "depense": "elle dépense de l'argent ou des crédits",
    "suppression": "elle supprime des fichiers ou des données",
    "publication": "elle publie, pousse ou met en ligne",
    "systeme": "elle touche Windows ou le système",
    "compte": "elle touche un compte ou des identifiants",
}
MOTS_RESERVES = (
    ("depense", re.compile(r"€|\d\s*(euros?\b|dollars?\b|\$|usd\b)|\$\s*\d|\bcr[ée]dits?\b|ach[eèé]t|\bachats?\b|\babonnement|\bpay(er|ant|ante|ée?)\b|"
                           r"\bpaiement|\bfactur|\bd[ée]pense d'argent|\bcarte bancaire", re.I)),
    ("suppression", re.compile(r"\bsupprim|\beffac|\bd[ée]trui|\b[ée]cras|\bvider\b|\bd[ée]sinstall|\bcorbeille|\bdelete\b|\brm\s+-|\bpurger?\b|\bformat(er|age)\b", re.I)),
    ("publication", re.compile(r"\bpubli(er|e|é|ée|és|ées|cation|ons|ez)\b|\bpush\b|\bpouss(er|e|é)\b|\bmise en ligne|\bmettre en ligne|"
                               r"\brelease\b|\bsteam\b|\bitch\.io", re.I)),
    ("systeme", re.compile(r"\bwindows\b|\bregedit\b|\bhkey_|\bregistre (de |du )?(windows|syst[eè]me)|\bbios\b|\bpilotes? (graphique|de la carte|nvidia|amd)|\bdrivers?\b|"
                           r"\bt[âa]che planifi|\bpare-feu|\bfirewall|\bantivirus|\b[ée]l[ée]vation|\badministrateur|"
                           r"\bred[ée]marr(er|age) (le |du )?pc|\bpartition", re.I)),
    ("compte", re.compile(r"\bcr[ée]er (un|son|le) compte|\bcompte (epic|steam|github|google|microsoft|tripo|fab|elevenlabs)\b|\bse (re)?connecter\b|\bidentifiants?\b|\bmot de passe|\bconditions d'utilisation|"
                          r"\baccepter les conditions|\bcl[ée] d'api|\bjeton d'acc[eè]s|\btoken\b", re.I)),
)
NON = ("", "aucune", "aucun", "non", "false", "0", "none")


def options_de(dec):
    o = dec.get("options") if isinstance(dec.get("options"), list) else dec.get("choix")
    return [x for x in o if isinstance(x, dict)] if isinstance(o, list) else []


def motif_reserve(dec, choix=None):
    """Pourquoi la décision est gardée pour l'utilisateur ('' : le coordinateur peut la trancher).
    choix=None : toutes les options comptent (liste « reservees ») ; sinon seulement l'option choisie."""
    if not isinstance(dec, dict):
        return ""
    if dec.get("depense") or dec.get("type") == "depense" or str(dec.get("montant", "")).strip() not in NON:
        return RESERVES["depense"]
    if any(str(k).startswith("reserve_") and v for k, v in dec.items()):
        return "elle est marquée réservée à l'utilisateur (reserve_utilisateur)"
    r = str(dec.get("reserve") or "").strip().lower()
    if r not in NON:
        return RESERVES.get(r, f"elle est marquée réservée ({r})")
    textes = [dec.get("question"), dec.get("titre")]
    for o in options_de(dec):
        if choix is None or o.get("id") == choix:
            textes += [o.get("libelle"), o.get("detail")]
    t = " ".join(str(x) for x in textes if x)
    for genre, rx in MOTS_RESERVES:
        m = rx.search(t)
        if m:
            return f"{RESERVES[genre]} (mot repéré : « {m.group(0).strip()} »)"
    return ""


def ouverte(dec):
    return str(dec.get("statut") or "ouverte") == "ouverte"


def repondues(racine):
    """C5 : ids déjà répondus dans reponses.json (la page répond là ; decisions.json peut rester « ouverte » si le serveur
    n'a pas pu la fermer). Fichier absent ou illisible : aucun id (la liste reste lisible, rien n'est écrit)."""
    try:
        r = jsonio.lire_strict(os.path.join(racine, "reponses.json"))
    except (OSError, ValueError):
        return {}
    r = liste_de(r, "reponses")
    return {str(x.get("id")): str(x.get("repondu_le") or "") for x in r if isinstance(x, dict) and x.get("id") not in (None, "")}


def deja_repondue(dec, reps):
    """Réponse plus récente que la décision : une décision reposée avec le même id (depense --id, remplacement) reste ouverte."""
    i = str(dec.get("id"))
    if i not in reps:
        return False
    cree, rep = str(dec.get("cree_le") or ""), reps[i]
    return not (cree and rep and rep < cree)


def en_absence(racine):
    r = lire(os.path.join(racine, "reglages.json"), {})
    return bool(isinstance(r, dict) and r.get("mode_absent"))


def refus(message, code):
    print(message, file=sys.stderr)
    sys.exit(code)


# F (assistant actif) : propositions à un clic et petites décisions prises seul (notées).
PROPOSITIONS_MAX = 3
PLUS_TARD_H = 2
PETITES = {
    "ordre": "ordre des tâches prêtes",
    "relance": "relance d'un agent figé",
    "roadmap": "statut de roadmap prouvé par un commit",
    "reversible": "choix réversible sans coût",
}


def propositions_ouvertes(l):
    return [x for x in l if isinstance(x, dict) and x.get("genre") == "proposition" and ouverte(x)]


def plus_tard_jusqua(racine, base):
    """« HH:MM » si « Plus tard » a été répondu à une proposition de cette base il y a moins de PLUS_TARD_H heures, sinon ''."""
    pref = f"prop-{base}-"
    for x in reversed(liste_de(lire(os.path.join(racine, "reponses.json"), []), "reponses")):
        if isinstance(x, dict) and str(x.get("id") or "").startswith(pref) and x.get("choix") == "plus_tard":
            try:
                t = time.mktime(time.strptime(str(x.get("repondu_le") or "")[:19], "%Y-%m-%dT%H:%M:%S"))
            except (ValueError, OverflowError):
                return ""
            fin = t + PLUS_TARD_H * 3600
            return time.strftime("%H:%M", time.localtime(fin)) if fin > time.time() else ""
    return ""


def horodate(t):
    return t.replace("-", "").replace(":", "").replace("T", "-")


def main(argv=None):
    for flux in (sys.stdout, sys.stderr):              # « ★ », « € » : jamais d'erreur d'écriture sur une console ou un tube en cp1252
        try:
            if (flux.encoding or "").lower().replace("-", "") != "utf8":
                flux.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    p = argparse.ArgumentParser(description="Déposer ce qui attend l'utilisateur sous la cloche du studio.")
    p.add_argument("--dossier")
    p.add_argument("--projet")
    s = p.add_subparsers(dest="quoi", required=True)
    a = s.add_parser("afaire")
    a.add_argument("--id", required=True)
    a.add_argument("--titre", required=True)
    a.add_argument("--detail", default="")
    a.add_argument("--genre", choices=GENRES, default="autre")
    a.add_argument("--lien", default="")
    a.add_argument("--option", action="append")
    a.add_argument("--recommande", default="")
    d = s.add_parser("depense")
    d.add_argument("--id", required=True)
    d.add_argument("--question", required=True)
    d.add_argument("--montant", required=True)
    d.add_argument("--devise", default="€")
    d.add_argument("--service", required=True)
    d.add_argument("--pourquoi", required=True)
    d.add_argument("--contexte", default="")
    t = s.add_parser("attend")
    t.add_argument("--cle", required=True)
    t.add_argument("--question", required=True)
    f = s.add_parser("fait")
    f.add_argument("--id", required=True)
    s.add_parser("liste")
    k = s.add_parser("decider", help="trancher une décision ouverte à la place de l'utilisateur (★ par défaut)")
    k.add_argument("id")
    k.add_argument("--choix", default="")
    k.add_argument("--raison", default="")
    g = k.add_mutually_exclusive_group()
    g.add_argument("--absence", action="store_true", help="noter « coordinateur (absence) » même sans mode_absent")
    g.add_argument("--present", action="store_true", help="noter « coordinateur » même en mode absent")
    s.add_parser("reservees", help="décisions ouvertes gardées pour l'utilisateur, et celles que le coordinateur peut trancher")
    pr = s.add_parser("proposer", help="proposition à un clic « Faire » (★) / « Plus tard »")
    pr.add_argument("--id", required=True, help="base de l'id (ex. l'id de la suggestion)")
    pr.add_argument("--titre", required=True)
    pr.add_argument("--raison", required=True)
    pr.add_argument("--detail", default="")
    pr.add_argument("--poste", default="")
    pr.add_argument("--origine", default="")
    pr.add_argument("--action", default="", help="ce que « Faire » lance")
    pr.add_argument("--langue", choices=("fr", "en"), default="fr")
    no = s.add_parser("note", help="petite décision prise seul, notée (liste blanche)")
    no.add_argument("--genre", required=True, choices=sorted(PETITES))
    no.add_argument("--titre", required=True)
    no.add_argument("--raison", required=True)
    no.add_argument("--id", default="")
    a_ = p.parse_args(argv)
    racine = dossier(a_)
    af_ch, dec_ch, st_ch = (os.path.join(racine, "a_faire.json"), os.path.join(racine, "decisions.json"),
                            os.path.join(racine, "demandes", "statuts.json"))
    if a_.quoi == "decider":
        brut = lire(dec_ch, [])
        l = liste_de(brut, "decisions")
        dec = next((x for x in l if isinstance(x, dict) and x.get("id") == a_.id), None)
        if dec is None:
            refus(f"décision « {a_.id} » introuvable dans {dec_ch} : rien n'est écrit", 2)
        if not ouverte(dec):
            refus(f"décision « {a_.id} » déjà réglée (statut {dec.get('statut')}, réponse « {dec.get('reponse', '')} ») : rien n'est écrit", 2)
        if deja_repondue(dec, repondues(racine)):
            refus(f"décision « {a_.id} » déjà répondue dans reponses.json (decisions.json pas encore à jour) : rien n'est écrit", 2)
        ids = [o.get("id") for o in options_de(dec)]
        choix = a_.choix or str(dec.get("recommande") or "")
        motif = motif_reserve(dec, choix or None)          # avant tout le reste : une décision réservée est toujours refusée en code 3
        if motif:
            refus(f"REFUS : la décision « {a_.id} » est réservée à l'utilisateur, car {motif}. "
                  "Le coordinateur ne la tranche pas, même en son absence : elle reste sous la cloche. Rien n'est écrit.", 3)
        if not choix:
            refus(f"« {a_.id} » n'a pas de choix recommandé : donne --choix <id> et --raison", 2)
        if ids and choix not in ids:
            refus(f"--choix « {choix} » inconnu : choix possibles {', '.join(map(str, ids))}", 2)
        suit = choix == str(dec.get("recommande") or "")
        if not suit and not a_.raison.strip():
            refus("choix différent de la recommandation (★) : --raison obligatoire. Rien n'est écrit.", 2)
        raison = a_.raison.strip() or "recommandation (★) suivie"
        absent = a_.absence or (not a_.present and en_absence(racine))
        par = "coordinateur (absence)" if absent else "coordinateur"
        t = maintenant()
        rep_ch = os.path.join(racine, "reponses.json")
        reps = lire(rep_ch, [])
        if not isinstance(reps, list):
            refus("reponses.json n'est pas une liste : rien n'est écrit", 2)
        r = {"id": a_.id, "choix": choix, "texte_libre": "", "repondu_le": t, "decide_par": par, "raison": raison}
        ecrire(rep_ch, [x for x in reps if not (isinstance(x, dict) and x.get("id") == a_.id)] + [r])
        dec.update({"statut": "repondue", "reponse": choix, "repondue_le": t, "decide_par": par, "decide_le": t,
                    "raison": raison, "en_absence": absent, "recommandation_suivie": suit})
        ecrire(dec_ch, dict(brut, decisions=l) if isinstance(brut, dict) else l)
        print(json.dumps({"ok": True, "decision": dec, "reponse": r}, ensure_ascii=False))
    elif a_.quoi == "proposer":
        base = re.sub(r"[^A-Za-z0-9_.-]+", "-", a_.id.strip()).strip("-")[:60]
        if not base or not a_.titre.strip() or not a_.raison.strip():
            refus("--id, --titre et --raison ne peuvent pas être vides : rien n'est écrit", 2)
        if motif_reserve({"titre": a_.titre, "question": a_.raison, "explication": a_.action}, "").startswith(RESERVES["depense"]):
            refus(f"REFUS : « {a_.titre} » dépense de l'argent ou des crédits. Passe par « cloche.py depense » (jamais d'étoile). Rien n'est écrit.", 3)
        jusqua = plus_tard_jusqua(racine, base)
        if jusqua:
            refus(f"« {base} » : l'utilisateur a répondu « Plus tard » ; pas de nouvelle proposition avant {jusqua}. Rien n'est écrit.", 2)
        brut = lire(dec_ch, [])
        l = liste_de(brut, "decisions")
        meme = next((x for x in propositions_ouvertes(l) if x.get("base") == base), None)
        if meme is None and len(propositions_ouvertes(l)) >= PROPOSITIONS_MAX:
            refus(f"déjà {PROPOSITIONS_MAX} propositions ouvertes : attends une réponse avant d'en poser une autre. Rien n'est écrit.", 2)
        en = a_.langue == "en"
        t = maintenant()
        e = {"id": meme["id"] if meme else f"prop-{base}-{horodate(t)}", "base": base,
             "genre": "proposition", "titre": a_.titre.strip(), "question": a_.titre.strip(),
             "explication": a_.raison.strip() + (f" {a_.detail.strip()}" if a_.detail.strip() else ""), "raison": a_.raison.strip(),
             "choix": [{"id": "faire", "libelle": "Do it" if en else "Faire"}, {"id": "plus_tard", "libelle": "Later" if en else "Plus tard"}],
             "recommande": "faire", "propose_par": "assistant", "statut": "ouverte", "cree_le": meme.get("cree_le", t) if meme else t}
        for k in ("poste", "origine", "action"):
            if getattr(a_, k).strip():
                e[k] = getattr(a_, k).strip()
        motif = motif_reserve(e, "faire")
        n = [x for x in l if not (isinstance(x, dict) and x.get("id") == e["id"])] + [e]
        ecrire(dec_ch, dict(brut, decisions=n) if isinstance(brut, dict) else n)
        print(json.dumps({"ok": True, "decision": e, "reservee": motif or None}, ensure_ascii=False))
    elif a_.quoi == "note":
        motif = motif_reserve({"titre": a_.titre, "question": a_.raison})
        if motif:
            refus(f"REFUS : « {a_.titre} » n'est pas une petite décision, car {motif}. Pose une décision pour l'utilisateur. Rien n'est écrit.", 3)
        absent = en_absence(racine)
        t = maintenant()
        id_ = a_.id.strip() or f"petite-{a_.genre}-{horodate(t)}"
        brut = lire(dec_ch, [])
        l = liste_de(brut, "decisions")
        e = {"id": id_, "genre": "petite_decision", "petite": a_.genre, "titre": a_.titre.strip(), "question": a_.titre.strip(),
             "explication": f"{PETITES[a_.genre]} : {a_.raison.strip()}", "choix": [{"id": "fait", "libelle": "Fait"}],
             "statut": "repondue", "reponse": "fait", "repondue_le": t, "decide_par": "assistant (absence)" if absent else "assistant",
             "decide_le": t, "raison": a_.raison.strip(), "en_absence": absent, "cree_le": t}
        n = [x for x in l if not (isinstance(x, dict) and x.get("id") == id_)] + [e]
        ecrire(dec_ch, dict(brut, decisions=n) if isinstance(brut, dict) else n)
        print(json.dumps({"ok": True, "decision": e}, ensure_ascii=False))
    elif a_.quoi == "reservees":
        deja = repondues(racine)
        ouv = [x for x in liste_de(lire(dec_ch, []), "decisions") if isinstance(x, dict) and ouverte(x) and not deja_repondue(x, deja)]
        res, ok = [], []
        for x in ouv:
            m = motif_reserve(x)
            if m:
                res.append({"id": x.get("id"), "question": x.get("question") or x.get("titre", ""), "motif": m})
            else:
                ok.append({"id": x.get("id"), "question": x.get("question") or x.get("titre", ""), "recommande": x.get("recommande", "")})
        print(json.dumps({"mode_absent": en_absence(racine), "reservees": res, "decidables": ok}, ensure_ascii=False, indent=1))
    elif a_.quoi == "afaire":
        if a_.lien and not a_.lien.startswith(("https://", "http://")):
            sys.exit("lien : http(s) seulement")
        l = [x for x in liste_de(lire(af_ch, []), "a_faire") if isinstance(x, dict) and x.get("id") != a_.id]
        e = {"id": a_.id, "titre": a_.titre, "detail": a_.detail, "genre": a_.genre, "statut": "a_faire", "cree_le": maintenant()}
        if a_.lien:
            e["lien"] = a_.lien
        o = options(a_.option)
        if o:
            e["options"] = o
            if a_.recommande:
                if a_.recommande not in [x["id"] for x in o]:
                    sys.exit("--recommande doit être l'id d'une --option")
                e["recommande"] = a_.recommande
        ecrire(af_ch, l + [e])
        print(json.dumps({"ok": True, "a_faire": e}, ensure_ascii=False))
    elif a_.quoi == "depense":
        brut = lire(dec_ch, [])
        l = [x for x in liste_de(brut, "decisions") if not (isinstance(x, dict) and x.get("id") == a_.id)]
        try:
            m = float(str(a_.montant).replace(",", "."))
        except ValueError:
            sys.exit("--montant : un nombre")
        e = {"id": a_.id, "question": a_.question, "titre": a_.question, "contexte": a_.contexte or a_.pourquoi,
             "explication": a_.contexte or a_.pourquoi, "type": "depense",
             "depense": {"montant": int(m) if m == int(m) else m, "devise": a_.devise, "service": a_.service, "pourquoi": a_.pourquoi},
             "options": [{"id": "accepter", "libelle": "J'accepte la dépense"}, {"id": "refuser", "libelle": "Je refuse"}],
             "statut": "ouverte", "cree_le": maintenant()}
        ecrire(dec_ch, (dict(brut, decisions=l + [e]) if isinstance(brut, dict) else l + [e]))
        print(json.dumps({"ok": True, "decision": e}, ensure_ascii=False))
    elif a_.quoi == "attend":
        st = lire(st_ch, {})
        if not isinstance(st, dict):
            sys.exit("statuts.json n'est pas un objet : rien n'est écrit")
        v = st.get(a_.cle) if isinstance(st.get(a_.cle), dict) else {}
        st[a_.cle] = dict(v, statut="attend_utilisateur", question=a_.question, maj=maintenant())
        ecrire(st_ch, st)
        print(json.dumps({"ok": True, "statut": {a_.cle: st[a_.cle]}}, ensure_ascii=False))
    elif a_.quoi == "fait":
        brut = lire(af_ch, [])
        l = liste_de(brut, "a_faire")
        trouve = False
        for x in l:
            if isinstance(x, dict) and x.get("id") == a_.id:
                x["statut"], x["fait_le"], trouve = "fait", maintenant(), True
        if not trouve:
            sys.exit(f"à-faire « {a_.id} » introuvable")
        ecrire(af_ch, dict(brut, a_faire=l) if isinstance(brut, dict) else l)
        print(json.dumps({"ok": True}, ensure_ascii=False))
    else:
        af = [x for x in liste_de(lire(af_ch, []), "a_faire") if isinstance(x, dict) and x.get("statut", "a_faire") not in ("fait", "annule")]
        deja = repondues(racine)                        # C5 : une décision déjà répondue par la page n'est plus comptée ouverte
        dec = [x for x in liste_de(lire(dec_ch, []), "decisions") if isinstance(x, dict) and x.get("statut", "ouverte") == "ouverte"
               and not deja_repondue(x, deja)]
        st = lire(st_ch, {})
        att = {k: v for k, v in (st.items() if isinstance(st, dict) else []) if isinstance(v, dict) and str(v.get("statut", "")).startswith("attend_")}
        print(json.dumps({"a_faire": af, "decisions_ouvertes": len(dec), "depenses": [x for x in dec if x.get("depense") or x.get("type") == "depense"],
                          "agents_qui_attendent": att}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
