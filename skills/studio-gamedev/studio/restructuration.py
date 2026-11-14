"""Plan de restructuration de l'équipe du studio (bouton « Plan de restructuration »). Module commun aux deux studios
jumeaux (skill studio-gamedev et studio d'origine) : seuls les branchements (chemins, routes) changent.

Rien ici n'agit seul sur l'équipe :
  construire_plan()  inventaire de tous les agents (postes, recrues, fiches d'agent), métier de chacun, doublons de métier,
                     agents sans travail depuis longtemps, intérimaires finis, fiches d'agent orphelines ; organigramme cible
                     (un poste par métier, noms clairs) ; renvois, renommages et fiches à ranger, chacun avec sa raison.
  decision()         la décision montrée sous la cloche : « Appliquer le plan » / « Modifier » / « Ne rien faire ».
  appliquer()        seulement après « Appliquer le plan » : renvois et renommages par les routes existantes du serveur
                     (fonctions passées en `ops`), fiches orphelines rangées dans _anciens (jamais supprimées), journal.
                     Un agent en plein travail (progression < 100, demande ou workflow en cours) n'est pas renvoyé :
                     il passe « à renvoyer après sa tâche ».
  suite()            renvois « après sa tâche » repris quand l'agent a fini ; jamais en mode absent (gardés pour le retour).
  defaire()          réembauche des renvoyés et anciens noms remis (le plan est réversible).

Fichiers (dans le dossier du studio) : restructuration.json {"plans": [le plus récent d'abord, 10 au plus]} et
restructuration_journal.json [ce qui a été fait, 300 lignes au plus]. Bibliothèque standard seulement.

Consignes de l'auditeur (facultatif) : restructuration_consignes.json dans le dossier du studio (ou `consignes=` ; sans
dossier donné, celui de ce module). Elles disent ce que le calcul seul ne voit pas :
  {"jamais": [ids jamais renvoyés ni renommés], "garder": [ids gardés malgré le calcul],
   "renvois": [{id, raison}], "renommages": [{id, nouveau, raison}], "metiers": {id: "métier affiché"},
   "archiver": [{fichier, raison, vers?}], "archiver_finis_h": 12, "remarques": [texte]}
Archivage : un fichier progression/<nom>.json (barre d'un chantier fini ou d'un agent parti) va dans progression/_archives
(jamais supprimé, remis en place par defaire()). Un chantier encore en cours n'est archivé qu'après sa fin.
"""
import json
import os
import re
import sys
import time

FICHIER, JOURNAL = "restructuration.json", "restructuration_journal.json"
CONSIGNES = "restructuration_consignes.json"
FICHIER_PROG_RE = re.compile(r"^[A-Za-z0-9][\w.-]{0,80}\.json$")
EN_COURS_H = 6                                   # une barre pas finie, bougée depuis moins de 6 h : chantier en cours
INACTIF_H = 24                                   # sans travail depuis 24 h : renvoi proposé
# agents qui font tourner le studio lui-même : inventoriés, jamais renvoyés ni renommés par un plan
PROTEGES = {"assistant", "coordinateur", "auditeur", "controleur-modeles", "atelier", "chinois", "joueur",
            "sante", "direction", "tyrannie", "r-tyrannie", "hote"}
LIBRES = ("disponible", "fini", "pause", "attend", "libre")

# métier deviné du nom, de l'identifiant et du rôle (du plus précis au plus large) ; inconnu = jamais groupé
METIERS = [
    ("relecture", r"relect|relit|review|relecture"),
    ("tripo", r"tripo"),
    ("nanite", r"nanite"),
    ("blender", r"blender|mod[eé]l(?:eur|isation)\s*3d|modeleur"),
    ("moteur", r"unreal|godot|unity|moteur|engine"),
    ("son", r"\bson\b|audio|sound|musique|music|bruit"),
    ("ia", r"\bia\b|\bai\b|faune|animaux|comportement"),
    ("quetes", r"qu[eê]te|quest"),
    ("level", r"level|niveau"),
    ("scenario", r"sc[eé]nar|story|histoire|dialogue"),
    ("art", r"\bda\b|direction artistique|\bart\b|artist|graphi|texture|sprite|illustr"),
    ("test", r"\btest(?:eur|er|s)?\b|\bqa\b"),
    ("doc", r"\bdoc|documentali|r[eé]dact|writer"),
    ("code", r"programm|d[eé]velopp|\bcode|codeur|gameplay|developer|engineer"),
]
TITRES = {
    "relecture": ("Relecteur", "Reviewer"), "tripo": ("Opérateur Tripo", "Tripo operator"), "nanite": ("Préparateur Nanite", "Nanite preparer"),
    "blender": ("Modeleur 3D", "3D modeller"), "moteur": ("Intégrateur moteur", "Engine integrator"), "son": ("Ingénieur du son", "Sound engineer"),
    "ia": ("Programmeur IA", "AI programmer"), "quetes": ("Concepteur de quêtes", "Quest designer"), "level": ("Level designer", "Level designer"),
    "scenario": ("Scénariste", "Writer"), "art": ("Directeur artistique", "Art director"), "test": ("Testeur", "Tester"),
    "doc": ("Documentaliste", "Documentalist"), "code": ("Programmeur", "Programmer"),
}
METIERS_LARGES = {"art": "art", "son": "son", "ia": "ia", "doc": "doc", "test": "test", "code": "code", "relecture": "relecture",
                  "design": "level", "moteur": "moteur"}   # métiers cochés dans la fiche (liste du studio) → métier du plan


def _tx(fr, en, anglais):
    return en if anglais else fr


def metier_de(a, nom_seul=False):
    """Métier précis d'un agent : d'après son identifiant et son nom, sinon son rôle (« sans moteur » ne fait pas un
    intégrateur moteur), sinon le premier métier coché de sa fiche. nom_seul : d'après l'identifiant et le nom seulement."""
    for cles in (("id", "nom"),) + (() if nom_seul else (("role",),)):
        txt = " ".join(str(a.get(k) or "") for k in cles).lower().replace("-", " ")
        for m, motif in METIERS:
            if re.search(motif, txt):
                return m
    for m in [] if nom_seul else a.get("metiers") or []:
        if m in METIERS_LARGES:
            return METIERS_LARGES[m]
    return None


def protege(a):
    i = str(a.get("id") or "")
    return a.get("genre") == "studio" or i in PROTEGES or i.split("r-", 1)[-1] in PROTEGES


def nom_pas_clair(a, noms_vus):
    """Un nom qui ne dit pas le métier : l'identifiant recopié, une étiquette technique, un doublon, un nom trop long."""
    nom = str(a.get("nom") or "").strip()
    brut = str(a.get("id") or "").split("r-", 1)[-1] if str(a.get("id") or "").startswith("r-") else str(a.get("id") or "")
    if not nom or nom == brut or nom == str(a.get("id")) or (re.search(r"[-_]", nom) and " " not in nom):
        return "nom = identifiant"
    if re.search(r"\((?:recrue|int[ée]rim|temp)\)|int[ée]rim|\d{2,}|\s\d+$", nom, re.I):     # « Modeleur 3D » reste clair
        return "étiquette technique dans le nom"
    if noms_vus.get(nom.lower(), 0) > 1:
        return "même nom qu'un autre agent"
    if len(nom) > 32:
        return "nom trop long"
    return None


def lire_consignes(dossier):
    """Consignes de l'auditeur (restructuration_consignes.json), {} sans fichier ou s'il est illisible."""
    c = _lire(os.path.join(dossier, CONSIGNES), {}) if dossier else {}
    return c if isinstance(c, dict) else {}


def progressions_de(dossier, maintenant=None):
    """[{fichier, pct, age_h, poste}] des barres progression/*.json du dossier (premier niveau seulement)."""
    t = maintenant or time.time()
    p = os.path.join(dossier, "progression") if dossier else ""
    out = []
    for f in sorted(os.listdir(p)) if p and os.path.isdir(p) else []:
        ch = os.path.join(p, f)
        if not FICHIER_PROG_RE.match(f) or not os.path.isfile(ch):
            continue
        d = _lire(ch, {})
        d = d if isinstance(d, dict) else {}
        pct = d.get("pct") if isinstance(d.get("pct"), (int, float)) else None
        try:
            age = (t - os.path.getmtime(ch)) / 3600
        except OSError:
            continue
        out.append({"fichier": f, "pct": pct, "age_h": round(age, 1), "poste": str(d.get("poste") or "")})
    return out


def construire_plan(agents, fiches_orphelines=(), anciens=(), maintenant=None, anglais=False, inactif_h=INACTIF_H,
                    consignes=None, progressions=None, dossier=None):
    """agents : [{id, nom, genre: fixe|recrue|studio, role?, metiers?, etat?, progression?, depuis? (epoch du dernier
    changement d'état), occupe?: raison}] ; fiches_orphelines : [nom de fichier .md] ; anciens : noms déjà renvoyés.
    consignes / progressions : lus dans `dossier` (par défaut celui de ce module) s'ils ne sont pas donnés ; les barres
    ne sont inventoriées que si des consignes existent (sinon le plan reste celui du calcul seul)."""
    t = int(maintenant or time.time())
    tx = lambda fr, en: _tx(fr, en, anglais)
    if consignes is None:
        consignes = lire_consignes(dossier or os.path.dirname(os.path.abspath(__file__)))
    cs = consignes if isinstance(consignes, dict) else {}
    if progressions is None:
        progressions = progressions_de(dossier or os.path.dirname(os.path.abspath(__file__)), t) if cs else []
    nu = lambda i: str(i).split("r-", 1)[-1] if str(i).startswith("r-") else str(i)
    jamais = {nu(i) for i in cs.get("jamais") or [] if isinstance(i, str)}
    garder = {nu(i) for i in cs.get("garder") or [] if isinstance(i, str)}
    inv = []
    for a in agents:
        if not isinstance(a, dict) or not a.get("id"):
            continue
        pct = a.get("progression")
        occupe = a.get("occupe") or (a.get("etat") in ("travaille", "bloque") and tx("au travail", "at work")) \
            or (isinstance(pct, (int, float)) and 0 < pct < 100 and a.get("etat") not in LIBRES and tx(f"progression {int(pct)} %", f"progress {int(pct)}%"))
        depuis = a.get("depuis") if isinstance(a.get("depuis"), (int, float)) else None
        inv.append({"id": a["id"], "nom": str(a.get("nom") or a["id"]), "genre": a.get("genre") or "recrue", "metier": metier_de(a), "metier_au_nom": bool(metier_de(a, True)),
                    "etat": a.get("etat") or "", "progression": pct, "occupe": occupe or "",
                    "libre_h": round((t - depuis) / 3600, 1) if depuis and a.get("etat") in LIBRES else 0,
                    "protege": protege(a) or nu(a["id"]) in jamais, "role": str(a.get("role") or "")[:160]})
    renvois, renommages, ranger, remarques = [], [], [], []
    partants = set()

    def renvoyer(x, raison):
        partants.add(x["id"])
        renvois.append({"id": x["id"], "nom": x["nom"], "raison": raison, "apres_tache": bool(x["occupe"]),
                        "occupe": x["occupe"] or ""})
    par_id = {}
    for x in inv:
        par_id.setdefault(x["id"], x)
        par_id.setdefault(nu(x["id"]), x)
    # 0. renvois décidés par l'auditeur (jamais un agent protégé ni un poste de base : le serveur les refuse)
    for c in cs.get("renvois") or []:
        x = par_id.get(str((c or {}).get("id") or "")) or par_id.get(nu((c or {}).get("id") or ""))
        if not x or x["id"] in partants:
            continue
        if x["protege"] or x["genre"] != "recrue":
            remarques.append(tx(f"« {x['nom']} » : renvoi demandé mais refusé (agent protégé ou poste de base)",
                                f"“{x['nom']}”: let-go asked but refused (protected agent or base desk)"))
            continue
        renvoyer(x, str(c.get("raison") or tx("décision de l'auditeur", "auditor's decision"))[:300])
    # 1. doublons de métier : un seul agent garde le poste (poste de base d'abord, puis celui qui travaille, puis le plus actif)
    groupes = {}
    for x in inv:
        if x["metier"] and not x["protege"] and x["id"] not in partants and nu(x["id"]) not in garder:
            groupes.setdefault(x["metier"], []).append(x)
    for m, g in groupes.items():
        if len(g) < 2:
            continue
        g.sort(key=lambda x: (x["genre"] != "fixe", "interim" in x["id"], not x["metier_au_nom"], not x["occupe"], x["libre_h"]))
        garde = g[0]
        for x in g[1:]:
            if x["genre"] == "recrue":
                renvoyer(x, tx(f"doublon de « {garde['nom']} » (métier : {TITRES[m][0].lower()})", f"duplicate of “{garde['nom']}” (trade: {TITRES[m][1].lower()})"))
            else:
                remarques.append(tx(f"« {x['nom']} » et « {garde['nom']} » ont le même métier : deux postes de base, à fusionner à la main si besoin",
                                    f"“{x['nom']}” and “{garde['nom']}” share a trade: two base desks, merge by hand if needed"))
    # 2. recrues sans travail depuis longtemps, intérimaires finis
    for x in inv:
        if x["id"] in partants or x["genre"] != "recrue" or x["protege"] or nu(x["id"]) in garder:
            continue
        if "interim" in x["id"] and not x["occupe"]:
            renvoyer(x, tx("intérimaire : sa part est finie", "temp: their part is done"))
        elif x["libre_h"] >= inactif_h:
            renvoyer(x, tx(f"sans travail depuis {int(x['libre_h'])} h", f"no work for {int(x['libre_h'])} h"))
    # 3. organigramme cible et noms clairs (un nom de métier, unique)
    restent = [x for x in inv if x["id"] not in partants]
    vus = {}
    for x in restent:
        vus[x["nom"].lower()] = vus.get(x["nom"].lower(), 0) + 1
    pris = {x["nom"].lower() for x in restent}
    voulus = {}                                                  # renommages décidés par l'auditeur : {id nu: (nom, raison)}
    for c in cs.get("renommages") or []:
        nouveau = re.sub(r"\s+", " ", str((c or {}).get("nouveau") or "")).strip()[:40]
        if nouveau and (c or {}).get("id"):
            voulus[nu(c["id"])] = (nouveau, str(c.get("raison") or tx("nom de métier clair", "clear trade name"))[:300])
    affiches = {nu(k): str(v)[:60] for k, v in (cs.get("metiers") or {}).items() if isinstance(v, str)} if isinstance(cs.get("metiers"), dict) else {}
    organigramme = []
    for x in restent:
        cible = x["nom"]
        voulu = voulus.get(nu(x["id"]))
        if voulu and x["protege"]:
            remarques.append(tx(f"« {x['nom']} » : renommage demandé mais refusé (agent protégé)", f"“{x['nom']}”: rename asked but refused (protected agent)"))
        elif voulu and voulu[0].lower() != x["nom"].lower() and voulu[0].lower() in pris:
            remarques.append(tx(f"« {x['nom']} » → « {voulu[0]} » : nom déjà pris, renommage écarté", f"“{x['nom']}” → “{voulu[0]}”: name taken, rename dropped"))
        elif voulu and voulu[0] != x["nom"]:
            cible = voulu[0]
            pris.add(cible.lower())
            renommages.append({"id": x["id"], "ancien": x["nom"], "nouveau": cible, "raison": voulu[1]})
        pourquoi = None if voulu or x["protege"] or not x["metier"] else nom_pas_clair(x, vus)
        if pourquoi:
            titre = TITRES[x["metier"]][1 if anglais else 0]
            if titre.lower() not in pris and titre.lower() != x["nom"].lower():   # jamais un renommage en lui-même
                cible = titre
                pris.add(titre.lower())
                renommages.append({"id": x["id"], "ancien": x["nom"], "nouveau": titre,
                                   "raison": tx(pourquoi, {"nom = identifiant": "name = id", "étiquette technique dans le nom": "technical tag in the name",
                                                            "même nom qu'un autre agent": "same name as another agent", "nom trop long": "name too long"}.get(pourquoi, pourquoi))})
        organigramme.append({"id": x["id"], "nom": cible, "metier": affiches.get(nu(x["id"])) or ("studio" if x["protege"] else TITRES[x["metier"]][1 if anglais else 0] if x["metier"] else tx("autre", "other")),
                             "genre": x["genre"]})
    organigramme.sort(key=lambda o: (o["genre"] == "studio", o["metier"], o["nom"]))
    # 4. fiches d'agent sans poste (écrites par le studio) : rangées dans _anciens, jamais supprimées
    for f in fiches_orphelines:
        ranger.append({"fichier": f, "raison": tx("fiche d'agent sans poste dans l'équipe", "agent file with no desk in the team")})
    # 5. barres de progression à archiver (progression/_archives, jamais supprimées) : consignes d'abord, puis chantiers finis
    archiver, vus_f = [], set()
    progs = {p["fichier"]: p for p in progressions or [] if isinstance(p, dict) and FICHIER_PROG_RE.match(str(p.get("fichier") or ""))}

    def archive(f, raison, vers=""):
        if f in vus_f or f not in progs:
            return
        vus_f.add(f)
        p = progs[f]
        en_cours = not (isinstance(p.get("pct"), (int, float)) and p["pct"] >= 100) and (p.get("age_h") or 0) < EN_COURS_H
        archiver.append({"fichier": f, "raison": raison[:300], "vers": str(vers or "")[:60], "pct": p.get("pct"),
                         "apres_tache": en_cours, "occupe": tx(f"chantier en cours ({p.get('pct')} %)", f"work in progress ({p.get('pct')}%)") if en_cours else ""})
    for c in cs.get("archiver") or []:
        if isinstance(c, dict) and c.get("fichier"):
            archive(os.path.basename(str(c["fichier"])), str(c.get("raison") or tx("barre sans agent", "bar with no agent")), c.get("vers"))
    if cs:
        restants = {nu(x["id"]) for x in restent} | PROTEGES | jamais
        finis_h = cs.get("archiver_finis_h") if isinstance(cs.get("archiver_finis_h"), (int, float)) else 12
        for f, p in sorted(progs.items()):
            nom = f[:-5]
            fini = isinstance(p.get("pct"), (int, float)) and p["pct"] >= 100
            if nom in restants or not fini:
                continue
            if nom in {nu(i) for i in partants} or nom in set(anciens):
                archive(f, tx("barre d'un agent renvoyé", "bar of a let-go agent"))
            elif (p.get("age_h") or 0) >= finis_h:
                archive(f, tx(f"chantier fini, sans nouvelle depuis {int(p['age_h'])} h", f"finished work, silent for {int(p['age_h'])} h"))
    for r in cs.get("remarques") or []:
        if isinstance(r, str) and r.strip():
            remarques.append(r.strip()[:600])
    plan = {"id": time.strftime("restructuration-%Y%m%d-%H%M%S", time.localtime(t)), "cree_le": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t)),
            "statut": "ouverte", "inventaire": inv, "organigramme": organigramme, "renvois": renvois, "renommages": renommages,
            "ranger": ranger, "archiver": archiver, "remarques": remarques, "anciens": list(anciens)[:40], "anglais": bool(anglais),
            "consignes": bool(cs)}
    plan["resume"] = tx(f"{len(inv)} agents : {len(renvois)} renvoi(s), {len(renommages)} renommage(s), {len(ranger)} fiche(s) à ranger"
                        + (f", {len(archiver)} barre(s) à archiver" if archiver else "") + f" ; {len(organigramme)} après le plan.",
                        f"{len(inv)} agents: {len(renvois)} let go, {len(renommages)} renamed, {len(ranger)} file(s) to store"
                        + (f", {len(archiver)} bar(s) to archive" if archiver else "") + f"; {len(organigramme)} after the plan.")
    return plan


def _changements(plan):
    return bool(plan.get("renvois") or plan.get("renommages") or plan.get("ranger") or plan.get("archiver"))


def texte_plan(plan):
    """Le détail lisible du plan (une ligne par changement, avec sa raison)."""
    en = plan.get("anglais")
    tx = lambda fr, e: e if en else fr
    l = [plan.get("resume", "")]
    if plan.get("renvois"):
        l.append(tx("Renvois (fiche rangée dans _anciens, réembauche possible) :", "Let go (file kept in _anciens, can be hired back):"))
        l += [f"- {r['nom']} : {r['raison']}" + (tx(" — après sa tâche (", " — after their task (") + r["occupe"] + ")" if r.get("apres_tache") else "") for r in plan["renvois"]]
    if plan.get("renommages"):
        l.append(tx("Renommages :", "Renamed:"))
        l += [f"- {r['ancien']} → {r['nouveau']} : {r['raison']}" for r in plan["renommages"]]
    if plan.get("ranger"):
        l.append(tx("Fiches d'agent rangées dans _anciens :", "Agent files stored in _anciens:"))
        l += [f"- {r['fichier']} : {r['raison']}" for r in plan["ranger"]]
    if plan.get("archiver"):
        l.append(tx("Barres archivées dans progression/_archives (rien n'est supprimé) :", "Bars archived in progression/_archives (nothing deleted):"))
        l += [f"- {r['fichier']} : {r['raison']}" + (tx(" (travail repris par ", " (work taken over by ") + r["vers"] + ")" if r.get("vers") else "")
              + (tx(" — après la fin du chantier", " — once the work is finished") if r.get("apres_tache") else "") for r in plan["archiver"]]
    l.append(tx("Organigramme après le plan :", "Team after the plan:"))
    l += [f"- {o['nom']} ({o['metier']})" for o in plan.get("organigramme") or []]
    l += ["! " + r for r in plan.get("remarques") or []]
    if not _changements(plan):
        l.append(tx("Rien à changer : l'équipe est déjà en ordre.", "Nothing to change: the team is already in order."))
    return "\n".join(x for x in l if x)


def decision(plan):
    """Décision sous la cloche (champs des deux studios : titre/explication/choix et question/contexte/options)."""
    en = plan.get("anglais")
    tx = lambda fr, e: e if en else fr
    rien = not _changements(plan)
    choix = [{"id": "appliquer", "libelle": tx("Appliquer le plan", "Apply the plan"), "detail": tx("réversible : réembauche et anciens noms possibles", "reversible: hire back and old names possible")},
             {"id": "modifier", "libelle": tx("Modifier", "Change it"), "detail": tx("écris ce qu'il faut changer : l'auditeur refait le plan", "write what to change: the auditor redoes the plan")},
             {"id": "rien", "libelle": tx("Ne rien faire", "Do nothing"), "detail": tx("le plan est classé, rien ne change", "the plan is filed, nothing changes")}]
    titre = tx("Plan de restructuration de l'équipe", "Team restructuring plan")
    detail = texte_plan(plan)
    return {"id": plan["id"], "type": "restructuration", "titre": titre, "question": titre, "explication": detail, "contexte": detail,
            "choix": choix, "options": choix, "recommande": "rien" if rien else "appliquer", "cree_le": plan.get("cree_le"),
            "statut": "ouverte", "origine": "restructuration"}


# ------------------------------------------------------------------ fichiers
# C4 : jsonio.py (à côté de ce fichier) quand il est là ; ce fichier est commun aux jumeaux, et un jumeau qui n'a pas
# encore jsonio.py garde l'écriture d'avant (temporaire puis os.replace).
if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import jsonio
except ImportError:
    jsonio = None


def _lire(chemin, defaut):
    if jsonio:
        return jsonio.lire(chemin, defaut)
    try:
        with open(chemin, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defaut


def _ecrire(chemin, donnees):
    if jsonio:
        jsonio.ecrire(chemin, donnees, newline="\n")
        return
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=1)
    os.replace(tmp, chemin)


def plans(dossier):
    d = _lire(os.path.join(dossier, FICHIER), {})
    p = d.get("plans") if isinstance(d, dict) else None
    return [x for x in p if isinstance(x, dict) and x.get("id")] if isinstance(p, list) else []


def enregistrer(dossier, plan):
    """Le plan en tête de restructuration.json (remplace celui du même id ; un plan ouvert plus ancien passe « remplace »)."""
    autres = [x for x in plans(dossier) if x["id"] != plan["id"]]
    if plan.get("statut") == "ouverte":
        for x in autres:
            if x.get("statut") == "ouverte":
                x["statut"] = "remplace"
    _ecrire(os.path.join(dossier, FICHIER), {"plans": ([plan] + autres)[:10]})


def plan_par_id(dossier, ident):
    return next((x for x in plans(dossier) if x["id"] == ident), None)


def plan_ouvert(dossier):
    return next((x for x in plans(dossier) if x.get("statut") == "ouverte"), None)


def noter(dossier, plan, quoi, qui, ok, detail=""):
    j = _lire(os.path.join(dossier, JOURNAL), [])
    j = j if isinstance(j, list) else []
    j.append({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "plan": plan["id"], "action": quoi, "agent": qui, "ok": bool(ok), "detail": str(detail)[:200]})
    _ecrire(os.path.join(dossier, JOURNAL), j[-300:])


# ------------------------------------------------------------------ application (après « Appliquer le plan » seulement)
def _renvoi(dossier, plan, r, ops):
    ok, err = ops["renvoyer"](r["id"], "plan de restructuration " + plan["id"] + " : " + r["raison"])
    if ok:
        r.update(fait=True, apres_tache=False, fait_le=time.strftime("%Y-%m-%dT%H:%M:%S"))
        noter(dossier, plan, "renvoi", r["id"], True, r["raison"])
    else:
        r.update(apres_tache=True, occupe=str(err or "")[:120])        # refusé (tâche en cours) : repris après sa tâche
        noter(dossier, plan, "renvoi_apres_tache", r["id"], False, err)
    return ok


def archiver_barre(dossier, fichier, maintenant=None):
    """progression/<fichier> -> progression/_archives/ (jamais supprimé). Refus si le chantier est en cours
    (barre pas finie et bougée depuis moins de EN_COURS_H heures). Renvoie (ok, erreur, chemin d'archive relatif)."""
    f = os.path.basename(str(fichier or ""))
    src = os.path.join(dossier, "progression", f)
    if not FICHIER_PROG_RE.match(f) or not os.path.isfile(src):
        return False, "barre absente", ""
    d = _lire(src, {})
    pct = d.get("pct") if isinstance(d, dict) and isinstance(d.get("pct"), (int, float)) else None
    try:
        age_h = ((maintenant or time.time()) - os.path.getmtime(src)) / 3600
    except OSError:
        return False, "barre illisible", ""
    if not (pct is not None and pct >= 100) and age_h < EN_COURS_H:
        return False, f"en cours ({pct} %)", ""
    rel = os.path.join("_archives", f)
    if os.path.exists(os.path.join(dossier, "progression", rel)):
        rel = os.path.join("_archives", f[:-5] + time.strftime("-%Y%m%d-%H%M%S") + ".json")
    os.makedirs(os.path.join(dossier, "progression", "_archives"), exist_ok=True)
    os.replace(src, os.path.join(dossier, "progression", rel))
    return True, None, rel.replace(os.sep, "/")


def _archive(dossier, plan, r, ops):
    if ops.get("archiver"):
        ok, err = ops["archiver"](r["fichier"])
        rel = os.path.join("_archives", os.path.basename(r["fichier"])) if ok else ""
    else:
        ok, err, rel = archiver_barre(dossier, r["fichier"])
    if ok:
        r.update(fait=True, apres_tache=False, archive=rel.replace(os.sep, "/"), fait_le=time.strftime("%Y-%m-%dT%H:%M:%S"))
        noter(dossier, plan, "barre_archivee", r["fichier"], True, "→ progression/" + r["archive"])
    elif str(err or "").startswith("en cours"):
        if not r.get("note_attente"):                                 # noté une fois, pas à chaque passage de suite()
            noter(dossier, plan, "archive_apres_tache", r["fichier"], True, err)
        r.update(apres_tache=True, occupe=str(err)[:120], note_attente=True)
    else:
        r.update(fait=False, annule=True, occupe=str(err or "")[:120])                 # barre déjà partie : rien à faire
        noter(dossier, plan, "archive_sans_objet", r["fichier"], False, err)
    return ok


def appliquer(dossier, ident, ops, absent=False):
    """ops : renvoyer(id, motif) -> (ok, erreur), renommer(id, nom) -> (ok, erreur), occupe(id) -> raison ou "",
    ranger(fichier) -> (ok, erreur). Renvois : jamais un agent occupé (gardé « après sa tâche ») ; en mode absent,
    tous gardés pour le retour."""
    plan = plan_par_id(dossier, ident)
    if not plan:
        return {"ok": False, "erreur": "plan inconnu"}
    if plan.get("statut") not in ("ouverte", "a_modifier"):
        return {"ok": True, "deja": True, "plan": plan}
    plan.update(statut="en_cours", accepte_le=time.strftime("%Y-%m-%dT%H:%M:%S"))
    for r in plan.get("renommages") or []:
        ok, err = ops["renommer"](r["id"], r["nouveau"])
        r["fait"] = bool(ok)
        noter(dossier, plan, "renommage", r["id"], ok, f"{r['ancien']} → {r['nouveau']}" + (f" ({err})" if err else ""))
    for r in plan.get("ranger") or []:
        ok, err = ops["ranger"](r["fichier"])
        r["fait"] = bool(ok)
        noter(dossier, plan, "fiche_rangee", r["fichier"], ok, err or "→ _anciens")
    for r in plan.get("archiver") or []:                              # les barres ne sont que de l'affichage : même en mode absent
        _archive(dossier, plan, r, ops)
    for r in plan.get("renvois") or []:
        occ = ops["occupe"](r["id"])
        if absent:
            r.update(apres_tache=True, garde_absent=True)
            noter(dossier, plan, "renvoi_garde_absent", r["id"], True, "mode absent : gardé pour le retour")
        elif occ:
            r.update(apres_tache=True, occupe=str(occ)[:120])
            noter(dossier, plan, "renvoi_apres_tache", r["id"], True, occ)
        else:
            _renvoi(dossier, plan, r, ops)
    _clore_si_fini(plan)
    enregistrer(dossier, plan)
    return {"ok": True, "plan": plan}


def _clore_si_fini(plan):
    if not any(not r.get("fait") and not r.get("annule") for r in (plan.get("renvois") or []) + (plan.get("archiver") or [])):
        plan.update(statut="appliquee", applique_le=time.strftime("%Y-%m-%dT%H:%M:%S"))


def suite(dossier, ops, absent=False):
    """Renvois « après sa tâche » du plan en cours, repris quand l'agent a fini (jamais en mode absent)."""
    if absent:
        return {"ok": True, "attente": "mode absent"}
    faits = []
    for plan in plans(dossier):
        if plan.get("statut") != "en_cours":
            continue
        for r in plan.get("renvois") or []:
            if r.get("fait") or r.get("annule"):
                continue
            if not ops["existe"](r["id"]):
                r.update(annule=True)                                        # parti entre-temps (renvoyé à la main) : rien à faire
                continue
            if ops["occupe"](r["id"]):
                continue
            r.pop("garde_absent", None)
            if _renvoi(dossier, plan, r, ops):
                faits.append(r["id"])
        for r in plan.get("archiver") or []:                          # barres « après la fin du chantier »
            if not r.get("fait") and not r.get("annule") and _archive(dossier, plan, r, ops):
                faits.append(r["fichier"])
        _clore_si_fini(plan)
        enregistrer(dossier, plan)
    return {"ok": True, "renvoyes": faits}


def defaire(dossier, ident, ops):
    """Réembauche les renvoyés du plan et remet les anciens noms (rien n'est effacé, le journal le garde)."""
    plan = plan_par_id(dossier, ident)
    if not plan or plan.get("statut") not in ("en_cours", "appliquee"):
        return {"ok": False, "erreur": "plan non appliqué"}
    for r in plan.get("renvois") or []:
        if r.get("fait"):
            ok, err = ops["reembaucher"](r["id"])
            noter(dossier, plan, "reembauche", r["id"], ok, err or "")
            r["fait"] = not ok
        r["annule"] = True
    for r in plan.get("renommages") or []:
        if r.get("fait"):
            ok, err = ops["renommer"](r["id"], r["ancien"])
            noter(dossier, plan, "nom_remis", r["id"], ok, f"{r['nouveau']} → {r['ancien']}")
            r["fait"] = not ok
    for r in plan.get("archiver") or []:                              # barres remises en place (sauf si une nouvelle existe)
        if r.get("fait") and r.get("archive"):
            src = os.path.join(dossier, "progression", r["archive"])
            dst = os.path.join(dossier, "progression", os.path.basename(r["fichier"]))
            ok = os.path.isfile(src) and not os.path.exists(dst)
            if ok:
                os.replace(src, dst)
            noter(dossier, plan, "barre_remise", r["fichier"], ok, "" if ok else "archive absente ou barre recréée")
            r["fait"] = not ok
    plan.update(statut="defait", defait_le=time.strftime("%Y-%m-%dT%H:%M:%S"))
    enregistrer(dossier, plan)
    return {"ok": True, "plan": plan}


def classer(dossier, ident, statut, texte=""):
    """« Ne rien faire » (statut « classe ») ou « Modifier » (statut « a_modifier », avec ce qu'il faut changer)."""
    plan = plan_par_id(dossier, ident)
    if not plan:
        return None
    if plan.get("statut") in ("ouverte", "a_modifier"):
        plan.update(statut=statut, repondu_le=time.strftime("%Y-%m-%dT%H:%M:%S"))
        if texte:
            plan["a_changer"] = texte[:2000]
        enregistrer(dossier, plan)
    return plan


def consigne(plan, anglais=False):
    """Texte de la demande déposée pour l'auditeur (ou le coordinateur) : relire, corriger, ne jamais appliquer."""
    if anglais:
        return (f"Restructuring plan {plan['id']} is waiting under the bell ({FICHIER} in the studio folder). Review it impartially: "
                "inventory, duplicates, idle agents, target team, names. If a name or a reason is wrong, rewrite that plan in the "
                "file (same id, status \"ouverte\", keep the field structure). Never apply it yourself: only the user's \"Apply the "
                "plan\" does, through the studio server (let-go and renames go through /api/renvoyer and /api/agent).")
    return (f"Plan de restructuration {plan['id']} en attente sous la cloche ({FICHIER} dans le dossier du studio). Relis-le avec "
            "impartialité : inventaire, doublons, agents sans travail, organigramme cible, noms. Si un nom ou une raison est faux, "
            "réécris ce plan dans le fichier (même id, statut « ouverte », mêmes champs). Ne l'applique jamais toi-même : seul "
            "« Appliquer le plan » de l'utilisateur le fait, par le serveur du studio (renvois et renommages par les routes existantes).")
