"""Toute l'équipe (bouton « Toute l'équipe ») : tout le monde au même endroit, même ceux qu'on ne voit pas dans le studio.
Module commun aux deux studios jumeaux (skill studio-gamedev et studio d'origine) : seuls les branchements changent.

L'inventaire des agents est celui du plan de restructuration (restructuration.py : postes, recrues, métier, agent protégé,
barres de progression) ; ce module ne fait qu'ajouter ce que le plan ne regarde pas et ranger le tout par groupes :
  postes        postes de base et agents du studio (coordinateur, atelier, santé…)
  recrues       recrues embauchées
  specialistes  spécialistes et intérimaires (recrues « specialiste-… », « interim-… »)
  chaines       agents des chaînes Claude en cours (journaux des workflows : étape lancée sans résultat), même ceux qui n'ont
                pas de bureau (« en sous-marin ») ; un agent qui a un bureau y est aussi marqué « dans une chaîne »
  fiches        fiches d'agent (.md) sans bureau
  barres        barres de progression qui ne sont pas un agent (chantiers)
  anciens       renvoyés (recrues/_anciens), fiches rangées (_anciens), barres archivées (progression/_archives)
Pour chacun : nom, métier, état (travail / libre / attente / fini), tâche en cours, depuis quand, modèle et effort, et ce
qu'on peut faire depuis le panneau (actions). Lecture seule : les changements passent par les routes existantes du serveur
(/api/agent, /api/noms, /api/modele, /api/renvoyer, /api/reembaucher, /api/restructuration action « archiver »).
Rien n'est jamais supprimé. Bibliothèque standard seulement.
"""
import glob
import json
import os
import re
import time

import restructuration as rs
import jsonio

# protégés : jamais renvoyés depuis le panneau (en plus de ceux du plan) ; « unreal » = Chef de chantier Unreal
PROTEGES = set(rs.PROTEGES) | {"unreal", "chef-unreal", "sante", "chinois", "tyrannie", "coordinateur", "atelier"}
SESSION = {"coordinateur", "chinois", "assistant", "__session"}   # la session Claude elle-même : /model, /effort
PAS_AGENTS = {"joueur", "wesh"}                                                      # personnages sans modèle
SPECIALISTE_RE = re.compile(r"(?:^|-)(?:specialiste|sp[eé]cialiste|interim|int[eé]rim|temp)(?:-|$)", re.I)
FENETRE_WF_H = 6            # journaux de workflows lus : bougés depuis moins de 6 h
SILENCE_S = 20 * 60         # étape ouverte sans écriture de l'agent depuis 20 min : en attente
ARRET_S = 90 * 60           # 90 min sans rien : chaîne arrêtée, plus listée
GROUPES = [
    ("postes", "Postes du studio", "Studio desks", "Postes de base et agents qui font tourner le studio.", "Base desks and the agents that run the studio."),
    ("recrues", "Recrues", "Hires", "Agents embauchés, chacun à son bureau.", "Hired agents, each at a desk."),
    ("specialistes", "Spécialistes et intérimaires", "Specialists and temps", "Embauchés pour une seule tâche.", "Hired for a single task."),
    ("chaines", "Dans les chaînes Claude", "In Claude chains", "Agents lancés par une chaîne de travail, même sans bureau dans le studio.",
     "Agents started by a work chain, even with no desk in the studio."),
    ("fiches", "Fiches d'agent sans bureau", "Agent files with no desk", "Définitions d'agent (.md) que Claude Code peut lancer, sans bureau dans le studio.",
     "Agent definitions (.md) Claude Code can start, with no desk in the studio."),
    ("barres", "Barres de chantier", "Work bars", "Barres de progression qui ne sont pas un agent.", "Progress bars that are not an agent."),
    ("anciens", "Anciens", "Former members", "Renvoyés, fiches rangées et barres archivées : rien n'est supprimé.",
     "Let go, stored files and archived bars: nothing is deleted."),
]
ETATS = {"travail": ("au travail", "at work"), "libre": ("libre", "free"), "attente": ("en attente", "waiting"), "fini": ("fini", "done")}
MODELE_RE = re.compile(r"(haiku|sonnet|opus|fable)", re.I)
GENERIQUES = {"", "general-purpose", "workflow-subagent"}   # types d'agent sans identité : rattachés au bureau dont la barre suit la chaîne


def _lire(chemin, defaut):
    return jsonio.lire(chemin, defaut)


def nu(i):
    i = str(i or "")
    return i[2:] if i.startswith("r-") else i


def iso(t):
    """epoch ou texte ISO -> « AAAA-MM-JJTHH:MM:SS » (heure locale), sinon ""."""
    if isinstance(t, (int, float)) and t > 0:
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t))
    s = str(t or "")
    return s[:19] if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", s) else ""


def frontmatter(chemin):
    """{name, description, model, effort} du frontmatter d'une fiche d'agent .md ({} si illisible)."""
    try:
        with open(chemin, encoding="utf-8-sig", errors="replace") as f:
            t = f.read(8192).replace("\r\n", "\n")
    except OSError:
        return {}
    if not t.startswith("---\n"):
        return {}
    tete = t[4:].split("\n---", 1)[0]
    out = {}
    for k in ("name", "description", "model", "effort"):
        m = re.search(r"(?m)^" + k + r":\s*(.*)$", tete)
        if m:
            out[k] = m.group(1).strip().strip("\"'")[:300]
    return out


def etat_de(etat, pct, occupe=False, attente=False):
    """travail / attente / fini / libre d'après l'état vu par le studio, la barre et la tâche en cours."""
    etat = str(etat or "")
    if attente or etat == "bloque":
        return "attente"
    if occupe or etat in ("travaille", "ronde", "appel"):
        return "travail"
    if isinstance(pct, (int, float)) and pct >= 100:
        return "fini"
    return "libre"


def modele_court(m):
    x = MODELE_RE.search(str(m or ""))
    return x.group(1).lower() if x else (str(m or "") or "")


def dossiers_workflows(projet, maison=None):
    """~/.claude/projects/<slug du projet>/<session>/subagents/workflows (toutes les sessions du projet)."""
    if not projet:
        return []
    slug = re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(projet))
    base = os.path.join(maison or os.path.expanduser("~"), ".claude", "projects", slug)
    try:
        return [d for d in glob.glob(os.path.join(glob.escape(base), "*", "subagents", "workflows")) if os.path.isdir(d)]
    except OSError:
        return []


def etapes_ouvertes(dossiers, maintenant=None):
    """Étapes des chaînes en cours : [{run, agent_id, type, label, depuis, silence_s, modele}] (lancée, sans résultat)."""
    t = maintenant or time.time()
    out = []
    for d in dossiers or []:
        try:
            runs = [r for r in os.listdir(d) if os.path.isfile(os.path.join(d, r, "journal.jsonl"))]
        except OSError:
            continue
        for run in runs:
            jr = os.path.join(d, run, "journal.jsonl")
            try:
                mt = os.path.getmtime(jr)
            except OSError:
                continue
            if t - mt > FENETRE_WF_H * 3600:
                continue
            ouverts, fini = {}, False
            try:
                with open(jr, encoding="utf-8", errors="replace") as f:
                    for ligne in f:
                        try:
                            e = json.loads(ligne)
                        except ValueError:
                            continue
                        ty, cle = e.get("type"), e.get("agentId") or e.get("key")
                        if ty == "started" and cle:
                            ouverts[cle] = e.get("label") or ""
                        elif ty == "result" and cle:
                            ouverts.pop(cle, None)
                        elif ty in ("finished", "completed", "failed", "cancelled", "stopped"):
                            fini = True
            except OSError:
                continue
            if fini:
                continue
            for cle, label in ouverts.items():
                base = os.path.join(d, run, f"agent-{cle}")
                meta = _lire(base + ".meta.json", {}) if re.match(r"^[A-Za-z0-9]{6,40}$", str(cle)) else {}
                meta = meta if isinstance(meta, dict) else {}
                try:
                    depuis = os.path.getmtime(base + ".meta.json")
                except OSError:
                    depuis = mt
                try:
                    silence = t - os.path.getmtime(base + ".jsonl")
                except OSError:
                    silence = None                       # pas encore de journal : étape en file
                if (silence if silence is not None else t - mt) > ARRET_S and t - mt > ARRET_S:
                    continue                             # chaîne immobile depuis 90 min : arrêtée
                out.append({"run": run, "agent_id": str(cle), "type": str(meta.get("agentType") or ""), "label": str(label)[:120],
                            "depuis": depuis, "silence_s": silence, "modele": modele_court(meta.get("pickedEffortModel") or meta.get("model"))})
    out.sort(key=lambda x: -x["depuis"])
    return out


def _barres(dossier, maintenant):
    """Barres progression/*.json (via restructuration.progressions_de) avec leur texte, leur source et « attente »."""
    out = {}
    for p in rs.progressions_de(dossier, maintenant):
        d = _lire(os.path.join(dossier, "progression", p["fichier"]), {})
        d = d if isinstance(d, dict) else {}
        out[p["fichier"][:-5]] = dict(p, texte=str(d.get("etape") or d.get("texte") or "")[:200], source=str(d.get("source") or "")[:80],
                                      attente=d.get("attente") is True, maj=iso(d.get("maj")) or iso(maintenant - p["age_h"] * 3600))
    return out


def construire(agents, dossier, *, postes_etat=(), modeles=None, dossiers_agents=(), dossiers_lecture=(), dossier_recrues=None,
               dossiers_anciens_agents=(), workflows=(), anglais=False, maintenant=None, occupe=None, modele_defaut="inherit"):
    """agents : l'inventaire du plan (serveur : _inventaire / inventaire_equipe) ; dossier : celui du studio (progression/) ;
    postes_etat : etat.json « postes » (tâche, texte, depuis, modèle) ; modeles : réponse de /api/modeles ;
    dossiers_agents : fiches .md modifiables (modèle, effort) ; dossiers_lecture : fiches .md montrées sans action ;
    dossier_recrues : recrues/ (pour recrues/_anciens) ; workflows : dossiers des workflows (dossiers_workflows) ;
    occupe(id) : raison d'une tâche en cours (le serveur refuse alors le renvoi)."""
    t = maintenant or time.time()
    tx = (lambda fr, en: en) if anglais else (lambda fr, en: fr)
    modeles = modeles if isinstance(modeles, dict) else {}
    fiches_m, recrues_m = modeles.get("fiches") or {}, modeles.get("recrues") or {}
    po = modeles.get("postes") or {}
    vus = {}
    for q in postes_etat or []:
        if isinstance(q, dict) and q.get("id"):
            vus.setdefault(q["id"], q)
            vus.setdefault(nu(q["id"]), q)
    barres = _barres(dossier, t)
    etapes = etapes_ouvertes(workflows, t)
    par_type = {}
    for e in etapes:
        par_type.setdefault(e["type"], []).append(e)
    membres, connus = [], set()
    # les fiches de recrues font foi tout de suite après une action du panneau (l'alimentation ne republie l'état
    # qu'après quelques secondes) : nom affiché à jour, réembauché visible, renvoyé retiré des recrues
    fiches_r = {}
    if dossier_recrues and os.path.isdir(dossier_recrues):
        for f in os.listdir(dossier_recrues):
            if f.endswith(".json") and f != "index.json" and re.match(r"^[\w.-]{1,80}\.json$", f):
                x = _lire(os.path.join(dossier_recrues, f), {})
                fiches_r[f[:-5]] = x if isinstance(x, dict) else {}
        ids_inv = {nu(a.get("id")) for a in agents or [] if isinstance(a, dict)}
        agents = [a for a in agents or [] if not (isinstance(a, dict) and a.get("genre") == "recrue" and nu(a.get("id")) not in fiches_r
                                                  and os.path.isfile(os.path.join(dossier_recrues, "_anciens", nu(a.get("id")) + ".json")))]
        agents += [{"id": "r-" + n, "nom": x.get("nom_affiche") or n, "genre": "recrue", "role": x.get("role") or "", "etat": "libre"}
                   for n, x in sorted(fiches_r.items()) if n not in ids_inv]

    def etat_lib(e):
        return ETATS[e][1 if anglais else 0]

    def titre_metier(a):
        m = rs.metier_de(a, nom_seul=a.get("genre") == "studio" or nu(a.get("id")) in PROTEGES)
        if not m and (a.get("genre") == "studio" or nu(a.get("id")) in PROTEGES):
            return tx("agent du studio", "studio agent")
        return rs.TITRES[m][1 if anglais else 0] if m else ""

    for a in agents or []:
        if not isinstance(a, dict) or not a.get("id"):
            continue
        i, n = str(a["id"]), nu(a["id"])
        connus.update({i, n})
        q = vus.get(i) or vus.get(n) or {}
        b = barres.get(n) or {}
        pct = a.get("progression") if isinstance(a.get("progression"), (int, float)) else q.get("progression") if isinstance(q.get("progression"), (int, float)) else b.get("pct")
        occ = a.get("occupe") or ""
        ch = par_type.get(n) or []
        source = b.get("source") if str(b.get("source") or "").startswith(("chaîne", "chaine", "chain")) and b.get("pct") is not None and b["pct"] < 100 else ""
        actif = any(e["silence_s"] is not None and e["silence_s"] < SILENCE_S for e in ch)
        etat = etat_de(a.get("etat") or q.get("etat"), pct, actif, b.get("attente"))
        if occ and etat in ("libre", "fini"):              # demande pas finie sans travail visible : en attente (tâche en cours)
            etat = "attente"
        genre = a.get("genre") or "recrue"
        groupe = "postes" if genre in ("fixe", "studio") else "specialistes" if SPECIALISTE_RE.search(n) else "recrues"
        fi, re_ = fiches_m.get(n) or {}, recrues_m.get(n) or {}
        modele = fi.get("modele") or re_.get("modele") or (po.get("modeles") or {}).get(i) or q.get("modele") or modele_defaut
        effort = fi.get("effort") or re_.get("effort") or (po.get("efforts") or {}).get(i) or ""
        prot = rs.protege(a) or n in PROTEGES
        session = n in SESSION or i in SESSION
        agent = i not in PAS_AGENTS and n not in PAS_AGENTS
        tache = str(q.get("tache") or b.get("texte") or q.get("texte") or a.get("role") or "")[:200]
        depuis = iso(a.get("depuis") or q.get("depuis")) or b.get("maj") or ""
        act = {}
        if agent:
            act["renommer"] = True
            act["metier"] = True
            if not session:
                act["modele"] = True
        if genre == "recrue" and agent:
            act["renvoyer"] = "protege" if prot else ("apres" if occ or etat == "travail" else True)
        nom_fiche = (fiches_r.get(n) or {}).get("nom_affiche") if genre == "recrue" else ""
        membres.append({"id": i, "cle": n, "nom": str(nom_fiche or a.get("nom") or q.get("nom") or i), "groupe": groupe, "genre": genre,
                        "metier": titre_metier(a), "role": str(a.get("role") or q.get("role") or "")[:200],
                        "etat": etat, "etat_lib": etat_lib(etat), "tache": tache, "depuis": depuis,
                        "progression": pct if isinstance(pct, (int, float)) else None,
                        "modele": "" if session or not agent else modele, "effort": "" if session or not agent else effort,
                        "session": session, "protege": prot, "occupe": occ or (tx("au travail", "at work") if etat == "travail" else ""),
                        "chaine": (ch[0]["label"] + " · " + ch[0]["run"]) if ch else source, "actions": act})
    # agents des chaînes en cours (les « sous-marins ») : chaque étape ouverte, avec son bureau s'il en a un
    noms = {m["cle"]: m["nom"] for m in membres}
    for e in etapes:
        ty = e["type"]
        bureau = noms.get(ty) or noms.get(nu(ty))
        if not bureau and ty in GENERIQUES:              # agent générique seulement : le bureau dont la barre suit cette chaîne
            for n_, b_ in barres.items():
                if e["run"] in str(b_.get("source") or "") and not (isinstance(b_.get("pct"), (int, float)) and b_["pct"] >= 100) and n_ in noms:
                    bureau = noms[n_]
                    break
        fm = {}
        for dos in list(dossiers_agents) + list(dossiers_lecture) + list(dossiers_anciens_agents or []):   # fiche rangée aussi (agent renvoyé relancé par une chaîne)
            if ty and re.match(r"^[\w.-]{1,80}$", ty) and os.path.isfile(os.path.join(dos, ty + ".md")):
                fm = frontmatter(os.path.join(dos, ty + ".md"))
                break
        anc = _lire(os.path.join(dossier_recrues, "_anciens", ty + ".json"), {}) if dossier_recrues and ty and re.match(r"^[\w.-]{1,80}$", ty) else {}
        anc = anc if isinstance(anc, dict) else {}
        sil = e["silence_s"]
        etat = "attente" if sil is None or sil >= SILENCE_S else "travail"
        membres.append({"id": e["run"] + ":" + e["agent_id"], "cle": ty, "nom": bureau or anc.get("nom_affiche") or fm.get("name") or ty or tx("agent sans nom", "unnamed agent"),
                        "groupe": "chaines", "genre": "chaine", "metier": tx("à son bureau aussi", "also at a desk") if bureau else tx("sans bureau", "no desk"),
                        "role": str(fm.get("description") or "")[:200], "etat": etat, "etat_lib": etat_lib(etat)
                        + ("" if sil is not None else tx(" (en file)", " (queued)")) + (tx(f" (rien écrit depuis {int(sil // 60)} min)", f" (silent for {int(sil // 60)} min)") if sil is not None and sil >= SILENCE_S else ""),
                        "tache": e["label"], "depuis": iso(e["depuis"]), "progression": None, "modele": e["modele"] or fm.get("model") or "",
                        "effort": fm.get("effort") or "", "session": False, "protege": True, "occupe": tx("dans une chaîne", "in a chain"),
                        "chaine": e["run"], "actions": {}})
    # fiches d'agent sans bureau
    vues = set()
    for dos, modifiable in [(d, True) for d in dossiers_agents] + [(d, False) for d in dossiers_lecture]:
        try:
            fichiers = sorted(os.listdir(dos)) if dos and os.path.isdir(dos) else []
        except OSError:
            fichiers = []
        for f in fichiers:
            ch = os.path.join(dos, f)
            n = f[:-3]
            if not f.endswith(".md") or n in connus or n in vues or not os.path.isfile(ch) or os.path.islink(ch):
                continue
            vues.add(n)
            fm = frontmatter(ch)
            ch_ = par_type.get(n) or []
            etat = "travail" if any(e["silence_s"] is not None and e["silence_s"] < SILENCE_S for e in ch_) else "attente" if ch_ else "libre"
            try:
                depuis = iso(os.path.getmtime(ch))
            except OSError:
                depuis = ""
            membres.append({"id": n, "cle": n, "nom": fm.get("name") or n, "groupe": "fiches", "genre": "fiche",
                            "metier": titre_metier({"id": n, "nom": fm.get("name") or n, "role": fm.get("description") or ""}),
                            "role": str(fm.get("description") or "")[:200], "etat": etat, "etat_lib": etat_lib(etat),
                            "tache": (ch_[0]["label"] if ch_ else tx("pas de tâche (lancée à la demande)", "no task (started on demand)")),
                            "depuis": depuis, "progression": None, "modele": fm.get("model") or "inherit", "effort": fm.get("effort") or "",
                            "session": False, "protege": False, "occupe": "", "chaine": ch_[0]["run"] if ch_ else "",
                            "fichier": ch.replace("\\", "/"), "actions": {"modele": True} if modifiable else {},
                            "note": "" if modifiable else tx("lecture seule ici : modèle et effort se règlent dans la fiche .md", "read only here: model and effort are set in the .md file")})
    # barres qui ne sont pas un agent (chantiers)
    agents_ids = connus | set(par_type) | vues
    anc_dir = os.path.join(dossier_recrues, "_anciens") if dossier_recrues else ""
    for n, b in sorted(barres.items()):
        if n in agents_ids:
            continue
        pct = b.get("pct")
        fini = isinstance(pct, (int, float)) and pct >= 100
        en_cours = not fini and (b.get("age_h") or 0) < rs.EN_COURS_H
        etat = "attente" if b.get("attente") else "fini" if fini else "travail" if en_cours else "libre"
        ancien = bool(anc_dir) and os.path.isfile(os.path.join(anc_dir, n + ".json"))   # barre restée d'un agent renvoyé
        membres.append({"id": "barre:" + b["fichier"], "cle": n, "nom": n, "groupe": "barres", "genre": "barre",
                        "metier": tx("barre d'un ancien agent", "bar of a former agent") if ancien else tx("chantier", "work"),
                        "role": b.get("source") or "", "etat": etat, "etat_lib": etat_lib(etat), "tache": b.get("texte") or "",
                        "depuis": b.get("maj") or "", "progression": pct if isinstance(pct, (int, float)) else None, "modele": "", "effort": "",
                        "session": False, "protege": False, "occupe": "", "chaine": b.get("source") or "", "fichier": b["fichier"],
                        "actions": {"archiver": "apres" if en_cours else True}})
    # anciens : renvoyés (fiche gardée), fiches rangées, barres archivées
    anc_r = os.path.join(dossier_recrues, "_anciens") if dossier_recrues else ""
    noms_anc = set()
    for f in sorted(os.listdir(anc_r)) if anc_r and os.path.isdir(anc_r) else []:
        if not f.endswith(".json") or f == "index.json" or ".corrompu-" in f or ".illisible-" in f:
            continue
        x = _lire(os.path.join(anc_r, f), {})
        x = x if isinstance(x, dict) else {}
        n = f[:-5]
        noms_anc.add(n)
        deja = n in connus
        membres.append({"id": "ancien:" + n, "cle": n, "nom": str(x.get("nom_affiche") or n), "groupe": "anciens", "genre": "ancien",
                        "metier": titre_metier({"id": n, "nom": x.get("nom_affiche") or n, "role": x.get("role") or ""}),
                        "role": str(x.get("role") or "")[:200], "etat": "fini", "etat_lib": tx("renvoyé", "let go"),
                        "tache": str(x.get("motif") or x.get("mission") or "")[:200], "depuis": iso(x.get("renvoye_le")), "progression": None,
                        "modele": str(x.get("modele") or ""), "effort": str(x.get("effort") or ""), "session": False, "protege": False, "occupe": "",
                        "chaine": "", "actions": {"reembaucher": "deja" if deja else True}})
    for dos in dossiers_anciens_agents or []:
        for f in sorted(os.listdir(dos)) if dos and os.path.isdir(dos) else []:
            n = f[:-3]
            if not f.endswith(".md") or n in noms_anc or n in connus:
                continue
            fm = frontmatter(os.path.join(dos, f))
            try:
                depuis = iso(os.path.getmtime(os.path.join(dos, f)))
            except OSError:
                depuis = ""
            membres.append({"id": "rangee:" + n, "cle": n, "nom": fm.get("name") or n, "groupe": "anciens", "genre": "ancien", "metier": "",
                            "role": str(fm.get("description") or "")[:200], "etat": "fini", "etat_lib": tx("fiche rangée", "file stored"),
                            "tache": "", "depuis": depuis, "progression": None, "modele": fm.get("model") or "", "effort": fm.get("effort") or "",
                            "session": False, "protege": False, "occupe": "", "chaine": "", "actions": {}})
    arch = os.path.join(dossier, "progression", "_archives") if dossier else ""
    try:
        archivees = sorted((f for f in os.listdir(arch) if f.endswith(".json")), key=lambda f: -os.path.getmtime(os.path.join(arch, f))) if arch and os.path.isdir(arch) else []
    except OSError:
        archivees = []
    if archivees:
        membres.append({"id": "archives", "cle": "", "nom": tx(f"{len(archivees)} barre(s) archivée(s)", f"{len(archivees)} archived bar(s)"),
                        "groupe": "anciens", "genre": "ancien", "metier": "", "role": "progression/_archives",
                        "etat": "fini", "etat_lib": tx("archivé", "archived"), "tache": ", ".join(f[:-5] for f in archivees[:8]) + (" …" if len(archivees) > 8 else ""),
                        "depuis": iso(os.path.getmtime(os.path.join(arch, archivees[0]))), "progression": None, "modele": "", "effort": "",
                        "session": False, "protege": False, "occupe": "", "chaine": "", "actions": {}})
    ordre = {"travail": 0, "attente": 1, "libre": 2, "fini": 3}
    groupes = []
    for g, fr, en, aide_fr, aide_en in GROUPES:
        l = [m for m in membres if m["groupe"] == g]
        l.sort(key=lambda m: (ordre.get(m["etat"], 9), m["nom"].lower()) if g != "anciens" else (m["id"] == "archives", m["nom"].lower()))
        groupes.append({"id": g, "titre": en if anglais else fr, "aide": aide_en if anglais else aide_fr, "membres": l})
    vivants = [m for m in membres if m["groupe"] not in ("anciens", "barres")]
    compte = {e: sum(1 for m in vivants if m["etat"] == e) for e in ETATS}
    resume = tx(f"{len(vivants)} agents : {compte['travail']} au travail, {compte['attente']} en attente, {compte['libre']} libres, {compte['fini']} finis"
                + (f" ; dont {sum(1 for m in vivants if m['groupe'] == 'chaines')} dans les chaînes" if etapes else ""),
                f"{len(vivants)} agents: {compte['travail']} at work, {compte['attente']} waiting, {compte['libre']} free, {compte['fini']} done"
                + (f"; {sum(1 for m in vivants if m['groupe'] == 'chaines')} in chains" if etapes else ""))
    return {"ok": True, "maj": iso(t), "resume": resume, "compte": compte, "total": len(vivants), "groupes": groupes, "anglais": bool(anglais)}
