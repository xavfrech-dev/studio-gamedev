"""S37 : les automatismes du studio tournent dans l'alimentation (studio_etat.py), sans aucun onglet ouvert.

Fin de tâche (attribution après 2 min, 30 s avec la tyrannie), tyrannie (inactifs, diagnostic des bloqués, rôle temporaire,
renvoi d'une recrue sans travail), embauche automatique. Mêmes règles que la page d'avant : la page ne fait plus qu'afficher
(etat.json → "automatismes"). Toutes les actions passent par le serveur du studio (routes /api/confier, /api/demande,
/api/recruter, /api/renvoyer) : il garde les plafonds (6 attributions par heure, une en attente par poste, refus si une tâche
est en cours). État gardé dans .studio/automatismes.json. Rien ne part si les réglages sont coupés, en pause ou si la
machine sature. Variable STUDIO_ESSAI_SANS_ENVOI : rien n'est envoyé (essais).
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

DELAI_FIN_S, DELAI_FIN_TYRAN_S = 120, 30
TOUR_TYRAN_S = 60
ECART_DIAG_S = 15 * 60
RENVOI_S = 30 * 60
TEMPO_S = 3600
EXCLUE_RE = re.compile(r"\b(sorti|sortie|écart|ecart|abandonn|hors v1|hors version|remplac|report|retir|dropped|removed|postponed|out of scope|replaced)", re.I)
MOTEUR_RE = re.compile(r"\b(moteur|engine|compil|build|shader)\b", re.I)
ERREUR_RE = re.compile(r"erreur|error|échec|failed|exception|traceback|crash", re.I)
FICHIER_RE = re.compile(r"(?:attend|manque|introuvable|absent|missing|waiting for)\w*\s+(?:le |la |les |l'|the )?(?:fichier\s+|file\s+)?[`«\"]?([\w./\\-]+\.(?:json|png|fbx|glb|gltf|tscn|unity|uasset|csv|md|txt|blend|wav|ogg))", re.I)
NOM_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,39}$")

TXT = {
    "mission_tache": ("Tâche {id} : {titre}. Critère de fait : {critere}.", "Task {id}: {titre}. Done when: {critere}."),
    "mission_prep": ("Préparer sans moteur (plans, données, tests ; rien n'est versé) la tâche {id} : {titre}. Critère visé : {critere}.",
                     "Prepare without the engine (plans, data, tests; nothing is merged) task {id}: {titre}. Target: {critere}."),
    "preparer": ("Préparer sans moteur", "Prepare without the engine"),
    "hors_metier": ("hors de son métier", "outside their trade"),
    "inactifs": ("Contremaître : agents inactifs à relancer : ", "Foreman: idle agents to restart: "),
    "bloques": ("Contremaître : agents bloqués (diagnostic et action proposée)\n", "Foreman: stuck agents (diagnosis and proposed action)\n"),
    "est_bloque": ("est bloqué", "is stuck"),
    "tempo": ("Rôle temporaire pendant que tu attends : {r}.\n", "Temporary role while you wait: {r}.\n"),
    "tempo_fin": ("\nTa tâche d'origine reste réservée pour toi : {o}. Reprends-la dès qu'elle se débloque.", "\nYour original task stays reserved for you: {o}. Resume it as soon as it is unblocked."),
    "tempo_titre": ("Rôle temporaire · ", "Temporary role · "),
    "confie": ("je lui confie ", "I give it "),
    "attendait": ("attendait", "was waiting for"),
    "depuis": (" depuis {m} min", " for {m} min"),
    "renvoi": ("renvoyé par le contremaître : plus de travail pour son poste", "let go by the foreman: no more work for this desk"),
    "role_emb": ("Poste « {n} » : tâches de la roadmap", "Trade “{n}”: roadmap tasks"),
}


def tx(cle, en, **k):
    s = TXT[cle][1 if en else 0]
    return s.format(**k) if k else s


def lire(chemin, defaut):
    try:
        with open(chemin, encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return defaut


def ecrire(chemin, donnees):
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=1)
    os.replace(tmp, chemin)


class Automatismes:
    def __init__(self, studio):
        self.s = studio                      # l'objet Studio de studio_etat.py (chemins, langue)
        self.chemin = studio.f("automatismes.json")
        d = lire(self.chemin, {})
        self.d = d if isinstance(d, dict) else {}
        for k, v in (("fins", {}), ("traites", []), ("confiees", []), ("temporaires", {}), ("tyr", {}), ("sans_metier", {}), ("renvois", [])):
            self.d.setdefault(k, v)

    # ---------- envoi au serveur du studio
    def poster(self, route, corps):
        if os.environ.get("STUDIO_ESSAI_SANS_ENVOI"):
            self.d.setdefault("essai_envois", []).append({"route": route, "corps": corps, "t": int(time.time())})
            self.d["essai_envois"] = self.d["essai_envois"][-50:]
            return {"ok": True, "essai": True}
        port = (lire(self.s.f("serveur.json"), {}) or {}).get("port")
        if not port:
            raise RuntimeError("serveur du studio introuvable (.studio/serveur.json)")
        base = f"http://127.0.0.1:{int(port)}"
        req = urllib.request.Request(base + route, data=json.dumps(corps).encode("utf-8"), headers={"Content-Type": "application/json", "Origin": base})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                j = json.loads(e.read().decode("utf-8") or "{}")
            except ValueError:
                j = {}
            return dict(j, ok=False, code=e.code)

    # ---------- données
    def contexte(self, conf, postes, r, progs, ouverts, chaine, sante):
        regl = lire(self.s.f("reglages.json"), {}) or {}
        taches = (lire(self.s.f("taches_disponibles.json"), {}) or {}).get("taches") or []
        decs = lire(self.s.f("decisions.json"), [])
        decs = decs if isinstance(decs, list) else (decs or {}).get("decisions") or []
        reps = {x.get("id") for x in (lire(self.s.f("reponses.json"), []) or []) if isinstance(x, dict)}
        ouvertes = [x for x in decs if isinstance(x, dict) and x.get("id") and x["id"] not in reps and (x.get("statut") or "ouverte") in ("ouverte", "en_attente")]
        mp = regl.get("metiers_postes") if isinstance(regl.get("metiers_postes"), dict) else {}
        metiers = {}
        for p in conf.get("postes") or []:
            if isinstance(p, dict) and p.get("id"):
                metiers[p["id"]] = mp.get(p["id"]) if isinstance(mp.get(p["id"]), list) else (p.get("metiers") or [])
        for rc in self.s.recrues():
            metiers[rc["nom"]] = rc.get("metiers") if isinstance(rc.get("metiers"), list) else []
        deja = set(self.d["confiees"])
        for q in postes:
            for dm in q.get("demandes") or []:
                if dm.get("tache_id"):
                    deja.add(dm["tache_id"])
        en = str(conf.get("langue") or "fr")[:2].lower() != "fr"
        return {"conf": conf, "postes": postes, "r": r or {"jalons": []}, "progs": progs, "ouverts": ouverts, "chaine": chaine, "sante": sante or {},
                "regl": regl, "taches": [t for t in taches if isinstance(t, dict) and t.get("id")], "ouvertes": ouvertes, "metiers": metiers,
                "deja": deja, "en": en}

    @staticmethod
    def auto(c, cle):
        return c["regl"].get(cle) is True

    def actif_tyran(self, c):
        return c["conf"].get("mode") == "travail" and self.auto(c, "tyrannie_auto") and not c["regl"].get("pause") and not c["sante"].get("sature")

    def prog(self, c, pid):
        v = c["progs"].get(pid)
        return (v[0] if isinstance(v[0], dict) else {}) if v else {}

    # ---------- candidats (même règle que la fiche : son métier, préparation, hors métier sans moteur)
    def candidats(self, c, pid):
        en, deja, ms = c["en"], c["deja"], c["metiers"].get(pid) or []
        libre = lambda t: t.get("id") and t["id"] not in deja
        pour = lambda t: t.get("poste") == pid or pid in (t.get("pour") or []) or (t.get("metier") and t.get("metier") in ms)
        crit = lambda t: t.get("critere") or "?"
        out, vus = [], set()

        def pousser(t, genre, mission, titre):
            if t["id"] not in vus:
                vus.add(t["id"])
                out.append({"tache_id": t["id"], "genre": genre, "mission": mission, "titre": titre, "sans_moteur": t.get("moteur") is not True and t.get("sans_moteur") is not False})
        for t in c["taches"]:
            if pour(t) and t.get("statut") == "a_faire" and libre(t):
                pousser(t, "metier", tx("mission_tache", en, id=t["id"], titre=t.get("titre", ""), critere=crit(t)), f"{t['id']} · {t.get('titre', '')}")
        ids = {t["id"] for t in c["taches"]}
        for j in c["r"].get("jalons") or []:
            for t in j.get("taches") or []:
                if (isinstance(t, dict) and t.get("id") and t.get("poste") == pid and t.get("statut") == "a_faire" and libre(t) and t["id"] not in ids
                        and not self.s.exclue(t)):
                    pousser(t, "preparation", tx("mission_prep", en, id=t["id"], titre=t.get("titre", ""), critere=crit(t)), f"{tx('preparer', en)} : {t['id']} · {t.get('titre', '')}")
        for t in c["taches"]:
            if not pour(t) and t.get("statut") == "a_faire" and t.get("sans_moteur") and t.get("origine") != "backlog" and libre(t):
                pousser(t, "hors", tx("mission_tache", en, id=t["id"], titre=t.get("titre", ""), critere=crit(t)), f"{t['id']} · {t.get('titre', '')} ({tx('hors_metier', en)})")
        return out[:12]

    def confier(self, c, pid, cand, origine, mission=None, titre=None):
        r = self.poster("/api/confier", {"agent": pid, "mission": (mission or cand["mission"])[:4000], "titre": (titre or cand["titre"])[:200],
                                         "tache_id": cand["tache_id"], "origine": origine})
        if r.get("ok"):
            c["deja"].add(cand["tache_id"])
            self.d["confiees"] = (self.d["confiees"] + [cand["tache_id"]])[-300:]
        return r

    # ---------- fin de tâche
    def fin_de_tache(self, c, maintenant):
        delai = DELAI_FIN_TYRAN_S if self.actif_tyran(c) else DELAI_FIN_S
        attribuer = c["conf"].get("mode") == "travail" and self.auto(c, "attribution_auto") and not c["regl"].get("pause") and not c["sante"].get("sature")
        ids = {q["id"] for q in c["postes"]}
        for q in c["postes"]:
            cle = f"{q['id']}:{q.get('depuis')}"
            f = self.d["fins"].get(q["id"])
            if q.get("fin_de_tache") and q.get("etat") == "disponible" and not f and cle not in self.d["traites"]:
                self.d["fins"][q["id"]] = {"cle": cle, "debut": maintenant, "fini": str(q.get("fini") or q.get("texte") or "")[:120]}
            elif f and (not q.get("fin_de_tache") or q.get("etat") != "disponible"):
                self.clore(q["id"])
        for pid in [p for p in self.d["fins"] if p not in ids]:
            self.d["fins"].pop(pid, None)
        for pid, f in list(self.d["fins"].items()):
            if f.get("tente") or not attribuer or maintenant - f["debut"] < delai:
                continue
            f["tente"] = True
            cand = (self.candidats(c, pid) or [None])[0]
            if not cand:
                self.clore(pid)
                continue
            r = self.confier(c, pid, cand, "auto:fin-de-tache")
            f["attribuee"] = {"t": int(maintenant), "titre": cand["titre"], "ok": bool(r.get("ok")), "refus": r.get("erreur")}
            self.d.setdefault("journal", []).append({"t": int(maintenant), "type": "attribution", "poste": pid, "titre": cand["titre"], "ok": bool(r.get("ok"))})
            self.clore(pid)

    def clore(self, pid):
        f = self.d["fins"].pop(pid, None)
        if f:
            self.d["traites"] = (self.d["traites"] + [f["cle"]])[-200:]

    # ---------- tyrannie
    def inactifs(self, c):
        out = []
        for q in c["postes"]:
            if q.get("etat") == "disponible":
                out.append(q)
            elif q.get("etat") == "attend" and not q.get("demandes") and (q.get("calme_min") is None or q["calme_min"] >= 10):
                out.append(q)
        return out

    def bloques(self, c):
        out = []
        for q in c["postes"]:
            pr = self.prog(c, q["id"])
            txt = " ".join(str(x) for x in (pr.get("etape"), pr.get("texte"), q.get("texte")) if x)
            pc, calme = q.get("progression"), q.get("calme_min")
            if isinstance(pc, (int, float)) and pc >= 100:
                continue                                  # 100 % : fini, en attente d'une tâche, jamais « bloqué »
            if pr.get("bloque"):
                out.append(q)
                continue
            if calme is not None and calme < 20:
                continue                                  # nouvelles depuis moins de 20 min : jamais « bloqué »
            if q.get("etat") == "bloque" or (pc is not None and calme is not None and q.get("etat") != "disponible") or re.search(r"bloqu|attend|blocked|waiting", txt, re.I):
                out.append(q)
        return out

    def diagnostic(self, c, q, file):
        en, pr = c["en"], self.prog(c, q["id"])
        txt = " ".join(str(x) for x in (pr.get("etape"), pr.get("texte"), pr.get("bloque_raison"), q.get("texte"), q.get("tache")) if x)
        bas = txt.lower()
        moi = {str(q["id"]).lower(), str(q.get("nom") or "").lower()}
        dec = next((d for d in c["ouvertes"] if any(str(d.get(k) or "").lower() in moi for k in ("poste", "agent", "pour", "qui"))), None)
        if not dec and re.search(r"\b(ta décision|ta réponse|ton avis|your decision|your answer)\b", txt, re.I) and c["ouvertes"]:
            dec = c["ouvertes"][0]
        if dec:
            t = str(dec.get("titre") or dec.get("question") or dec["id"])[:70]
            return {"type": "decision", "decision": dec["id"], "raison": f"waiting for your decision “{t}”" if en else f"attend ta décision « {t} »",
                    "action": "I move the question to the top of the bell and the chat" if en else "je remonte la question en haut de la cloche et du fil"}
        moteur = str((c["conf"].get("moteur") or {}).get("nom") or "").lower()
        if MOTEUR_RE.search(bas) or (moteur and moteur in bas):
            place = (file.index(q["id"]) + 1) if q["id"] in file else len(file) + 1
            occupe = bool(c["chaine"] or c["ouverts"])
            raison = (f"waiting for the engine (place {place} in the queue; {'it is busy' if occupe else 'it is free'})" if en
                      else f"attend le moteur (place {place} dans la file ; {'il est occupé' if occupe else 'il est libre'})")
            action = ("I keep it in the queue" if en else "je le laisse dans la file") if occupe else ("the engine is free: I ask to hand it over" if en else "le moteur est libre : je demande qu'on lui donne la main")
            return {"type": "moteur", "raison": raison, "action": action}
        lourd = next((o for o in c["ouverts"] if str(o.get("nom", "")).lower() in bas and o.get("poste") != q["id"]), None)
        if lourd:
            return {"type": "outil", "raison": f"waiting for {lourd['nom']} (already open: one at a time)" if en else f"attend {lourd['nom']} (déjà ouvert : un seul à la fois)",
                    "action": "it will go when it is free" if en else "il passera quand il sera libre"}
        for o in c["postes"]:
            if o["id"] == q["id"]:
                continue
            for n in {str(o["id"]), str(o.get("nom") or "")}:
                if len(n) >= 4 and re.search(r"(?:\battend(?:s|re|ent)?|\ben attente d[eu']?|\bbloqu[ée]e?s? par|\bwaiting for|\bblocked by)\s+(?:le |la |les |l'|du |de |the )?" + re.escape(n.lower()) + r"\b", bas):
                    nom = o.get("nom") or o["id"]
                    return {"type": "agent", "relancer": o["id"], "raison": f"waiting for {nom}" if en else f"attend {nom}", "action": f"I nudge {nom}" if en else f"je relance {nom}"}
        m = FICHIER_RE.search(txt)
        if m:
            return {"type": "fichier", "raison": f"waiting for file {m.group(1)}" if en else f"attend le fichier {m.group(1)}", "action": "I ask who should produce it" if en else "je demande qui doit le produire"}
        if c["sante"].get("sature"):
            a = str((c["sante"].get("alertes") or [""])[0])
            return {"type": "machine", "lien": "sante", "raison": ("machine saturated: " if en else "machine saturée : ") + a, "action": "see PC health" if en else "voir Santé du PC"}
        j = [str(x.get("t") or x.get("texte") or "") if isinstance(x, dict) else str(x) for x in (pr.get("journal") or [])[-5:]] + [txt]
        err = next((x for x in reversed(j) if ERREUR_RE.search(x)), None)
        if err:
            return {"type": "erreur", "raison": ("error: " if en else "erreur : ") + err[:110], "action": "I file the diagnosis so it gets fixed" if en else "je dépose le diagnostic pour qu'on corrige"}
        calme = q.get("calme_min")
        q_ = f"{calme} min" if calme is not None else ("a while" if en else "longtemps")
        return {"type": "silence", "raison": f"no news for {q_}, no known reason" if en else f"plus de nouvelles depuis {q_}, sans raison connue",
                "action": "I suggest restarting it" if en else "je propose de le relancer"}

    def diagnostics(self, c):
        bl = self.bloques(c)
        file = [q["id"] for q in bl if MOTEUR_RE.search(" ".join(str(x) for x in (self.prog(c, q["id"]).get("etape"), self.prog(c, q["id"]).get("texte")) if x))]
        return [dict(self.diagnostic(c, q, file), id=q["id"], nom=q.get("nom") or q["id"]) for q in bl]

    def tyrannie(self, c, maintenant):
        en, ty = c["en"], self.d["tyr"]
        res = {"active": self.actif_tyran(c), "diagnostics": [], "inactifs": [], "occupation": 0, "file_moteur": False}
        n = len(c["postes"]) or 1
        tous = self.inactifs(c)
        res["occupation"] = round(100 * (n - len(tous)) / n)
        if not res["active"]:
            return res
        l = [q for q in tous if self.candidats(c, q["id"])]
        res["inactifs"], res["file_moteur"] = [q["id"] for q in l], bool(tous) and not l
        diag = self.diagnostics(c)
        # rôle temporaire : attente longue (moteur, décision, agent, fichier, outil) → une autre tâche sans moteur ; une par agent et par heure
        for dg in diag:
            t0 = (self.d["temporaires"].get(dg["id"]) or {}).get("t", 0)
            if dg["type"] not in ("moteur", "decision", "agent", "fichier", "outil") or maintenant - t0 < TEMPO_S:
                continue
            pr = self.prog(c, dg["id"])
            cand = next((x for x in self.candidats(c, dg["id"]) if x["sans_moteur"] and x["tache_id"] != pr.get("tache")), None)
            if not cand:
                continue
            origine = str(pr.get("etape") or pr.get("texte") or "")[:90]
            mission = tx("tempo", en, r=dg["raison"]) + cand["mission"] + tx("tempo_fin", en, o=origine or "—")
            r = self.confier(c, dg["id"], cand, "auto:temporaire", mission=mission, titre=tx("tempo_titre", en) + cand["titre"])
            if r.get("ok"):
                calme = next((q.get("calme_min") for q in c["postes"] if q["id"] == dg["id"]), None)
                dg["action"] = tx("confie", en) + cand["titre"]
                dg["bulle"] = (f"{dg['nom']} {tx('attendait', en)} {re.sub(r'^(attend|waiting for)\s*', '', dg['raison'])}"
                               + (tx("depuis", en, m=calme) if calme is not None else "") + f" → {tx('confie', en)}{cand['titre']}")
                self.d["temporaires"][dg["id"]] = {"t": int(maintenant), "tache": cand["tache_id"], "titre": cand["titre"], "raison": dg["raison"], "origine": origine, "bulle": dg["bulle"]}
        res["diagnostics"] = diag
        # demande à l'assistant : diagnostics seulement si la liste change, au plus toutes les 15 min
        sd = ",".join(sorted(f"{x['id']}:{x['type']}" for x in diag))
        if diag and sd != ty.get("sig_diag") and maintenant - ty.get("diag_t", 0) >= ECART_DIAG_S:
            texte = tx("bloques", en) + "\n".join(f"- {x['nom']} {tx('est_bloque', en)} : {x['raison']} → {x['action']}" for x in diag)
            if self.poster("/api/demande", {"cible": "assistant", "texte": texte[:3900], "via": "ecrit"}).get("ok"):
                ty["sig_diag"], ty["diag_t"] = sd, maintenant
        s = ",".join(sorted(q["id"] for q in l))
        if l and (s != ty.get("sig") or maintenant - ty.get("derniere", 0) > ECART_DIAG_S):
            texte = tx("inactifs", en) + ", ".join(q.get("nom") or q["id"] for q in l)
            if self.poster("/api/demande", {"cible": "assistant", "texte": texte, "via": "ecrit"}).get("ok"):
                ty["sig"], ty["derniere"] = s, maintenant
        # renvoi d'une recrue à 100 % sans travail de son métier depuis 30 min (le serveur refuse si une tâche est en cours)
        for q in [x for x in c["postes"] if x.get("genre") == "recrue"]:
            ms = c["metiers"].get(q["id"]) or []
            travail = any(t.get("statut") != "verse" and (t.get("poste") == q["id"] or q["id"] in (t.get("pour") or []) or (t.get("metier") and t.get("metier") in ms)) for t in c["taches"])
            pc = q.get("progression")
            if travail or q.get("etat") != "disponible" or (isinstance(pc, (int, float)) and pc < 100):
                self.d["sans_metier"].pop(q["id"], None)
                continue
            self.d["sans_metier"].setdefault(q["id"], maintenant)
            if maintenant - self.d["sans_metier"][q["id"]] < RENVOI_S:
                continue
            r = self.poster("/api/renvoyer", {"nom": q["id"], "motif": tx("renvoi", en)})
            if r.get("ok"):
                self.d["sans_metier"].pop(q["id"], None)
                self.d["renvois"] = (self.d["renvois"] + [{"t": int(maintenant), "nom": q["id"], "nom_affiche": q.get("nom") or q["id"], "role": q.get("role", "")}])[-20:]
                break
        return res

    # ---------- embauche automatique : une tâche dont le poste n'a personne → une recrue de ce métier (une par heure)
    def embauche(self, c, maintenant):
        if (c["conf"].get("mode") != "travail" or not (self.auto(c, "embauche_auto") or self.actif_tyran(c)) or c["regl"].get("pause")
                or c["sante"].get("sature") or len(c["postes"]) >= 12 or maintenant - self.d.get("embauche_t", 0) < 3600):
            return
        ids = {q["id"] for q in c["postes"]}
        tc = next((t for t in c["taches"] if t.get("statut") == "a_faire" and isinstance(t.get("poste"), str) and NOM_RE.match(t["poste"]) and t["poste"] not in ids), None)
        if not tc:
            return
        self.d["embauche_t"] = maintenant
        lot = [t for t in c["taches"] if t.get("poste") == tc["poste"]][:8]
        nom = tc["poste"].replace("-", " ").capitalize()
        import zlib
        r = self.poster("/api/recruter", {"nom": tc["poste"], "nom_affiche": nom[:40], "role": tx("role_emb", c["en"], n=nom),
                                          "mission": "\n".join(f"- {t['id']} : {t.get('titre', '')}" + (f" ({t['critere']})" if t.get("critere") else "") for t in lot)[:3900],
                                          "auto": True, "apparence": "aucune", "couleur": "#%06x" % (zlib.crc32(tc["poste"].encode()) & 0xFFFFFF)})
        self.d.setdefault("journal", []).append({"t": int(maintenant), "type": "embauche", "poste": tc["poste"], "ok": bool(r.get("ok"))})

    # ---------- un passage (toutes les 10 s ; la tyrannie toutes les 60 s)
    def passer(self, conf, postes, r, progs, ouverts, chaine, sante):
        maintenant = time.time()
        try:
            c = self.contexte(conf, postes, r, progs, ouverts, chaine, sante)
            self.fin_de_tache(c, maintenant)
            self.embauche(c, maintenant)
            if maintenant - self.d["tyr"].get("tour", 0) >= TOUR_TYRAN_S or "dernier" not in self.d:
                self.d["tyr"]["tour"] = maintenant
                self.d["dernier"] = self.tyrannie(c, maintenant)
            elif not self.actif_tyran(c):
                self.d["dernier"] = dict(self.d.get("dernier") or {}, active=False)
        except Exception as e:                                  # un automatisme en panne ne fige jamais l'alimentation
            self.d["erreur"] = f"{type(e).__name__} : {e}"[:200]
        self.d["journal"] = (self.d.get("journal") or [])[-40:]
        ecrire(self.chemin, self.d)
        dern = self.d.get("dernier") or {}
        return {"serveur": True, "tyrannie": dern, "fins": {k: {"debut": int(v["debut"]), "fini": v.get("fini", "")} for k, v in self.d["fins"].items()},
                "temporaires": {k: v for k, v in self.d["temporaires"].items() if maintenant - v.get("t", 0) < 6 * 3600},
                "renvois": [x for x in self.d["renvois"] if maintenant - x["t"] < 600], "remonter": [x["decision"] for x in dern.get("diagnostics") or [] if x.get("decision")],
                "erreur": self.d.get("erreur")}
