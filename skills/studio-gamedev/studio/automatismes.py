"""S37 : les automatismes du studio tournent dans l'alimentation (studio_etat.py), sans aucun onglet ouvert.

Fin de tâche (attribution après 2 min, 30 s avec la tyrannie), tyrannie (inactifs, diagnostic des bloqués, rôle temporaire,
renvoi d'une recrue sans travail), embauche automatique. Mêmes règles que la page d'avant : la page ne fait plus qu'afficher
(etat.json → "automatismes"). Toutes les actions passent par le serveur du studio (routes /api/confier, /api/demande,
/api/recruter, /api/renvoyer) : il garde les plafonds (6 attributions par heure, une en attente par poste, refus si une tâche
est en cours). État gardé dans .studio/automatismes.json. Rien ne part si les réglages sont coupés, en pause ou si la
machine sature. Relecteur autonome : libre, il prend lui-même une relecture utile (commits, branches, tests, tests creux,
roadmap et doc), une toutes les 20 min au plus ; dernier commit relu dans .studio/relecteur.json. Relecture partagée :
plus de 60 min prévues → la moitié du lot à un relecteur libre, sinon à un « Relecteur (intérim) » (2 au plus), renvoyé à
la fin de sa part sauf relecture à faire dans les 30 min. Variable STUDIO_ESSAI_SANS_ENVOI : rien n'est envoyé (essais).
"""
import http.client
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jsonio                                 # C4 : lecture (BOM) et écriture atomique communes

DELAI_FIN_S, DELAI_FIN_TYRAN_S = 120, 30
# A1 : attribution de fin de tâche pas aboutie : serveur injoignable → nouvel essai après 60 s ; plafond du serveur (429) → après 5 min
REESSAI_SERVEUR_S, REESSAI_PLAFOND_S = 60, 300
QUI_CACHE_S = 30                             # G4 : le port reconnu par /api/qui reste valable 30 s
TOUR_TYRAN_S = 60
ECART_DIAG_S = 15 * 60
RENVOI_S = 30 * 60
TEMPO_S = 3600
EXCLUE_RE = re.compile(r"\b(sorti|sortie|écart|ecart|abandonn|hors v1|hors version|remplac|report|retir|dropped|removed|postponed|out of scope|replaced)", re.I)
MOTEUR_RE = re.compile(r"\b(moteur|engine|compil|build|shader)\b", re.I)
ERREUR_RE = re.compile(r"erreur|error|échec|failed|exception|traceback|crash", re.I)
FICHIER_RE = re.compile(r"(?:attend|manque|introuvable|absent|missing|waiting for)\w*\s+(?:le |la |les |l'|the )?(?:fichier\s+|file\s+)?[`«\"]?([\w./\\-]+\.(?:json|png|fbx|glb|gltf|tscn|unity|uasset|csv|md|txt|blend|wav|ogg))", re.I)
NOM_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,39}$")
# Relecteur autonome : libre (rien à relire, rien en attente) → il prend lui-même une relecture utile, une à la fois,
# au plus une toutes les 20 min. Priorité : commits récents de la branche principale pas encore relus, branches prêtes
# à intégrer pas encore relues, tests du projet, tests creux, roadmap et doc face au code. État : .studio/relecteur.json.
RELECT_ECART_S = 20 * 60
RELECT_BRANCHE_CALME_S = 30 * 60          # une branche dont le dernier commit a moins de 30 min est encore en travail
RELECT_BRANCHE_AGE_S = 7 * 86400          # au-delà d'une semaine sans commit : abandonnée, pas « prête »
RELECT_RE = re.compile(r"relect|relu|relir|revue|review|\bqa\b", re.I)
RELECT_ROTATION = ("tests", "tests_creux", "doc")
# Relecture partagée (règle du studio) : une relecture estimée à plus de 60 min (restant_min de sa progression)
# est coupée en deux ; la moitié va d'abord à un autre relecteur libre, sinon à un « Relecteur (intérim) » embauché pour
# l'occasion (2 au plus en même temps, 6 partages par heure au plus). À la fin de sa part, l'intérimaire est renvoyé
# (« mission d'intérim finie »), sauf s'il reste une relecture à faire : on le garde alors 30 min au plus.
PARTAGE_SEUIL_MIN = 60
INTERIM_MAX = 2
PARTAGE_PAR_HEURE = 6
INTERIM_GARDE_S = 30 * 60
INTERIM_PREFIXE = "relecteur-interim-"
ELEMENT_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(\S.*)$")

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
    "rl_commits_t": ("Relecture des commits {a}..{b} ({n})", "Review of commits {a}..{b} ({n})"),
    "rl_commits": ("Relis les commits de {br} pas encore relus ({n}) :\n{liste}\nCherche les bugs, les régressions, ce qui manque de test. "
                   "Pour chaque problème : fichier, ligne, scénario qui casse. Corrige sur une branche à part ce qui est sûr ; rien ne va dans {br} sans tests verts.",
                   "Review the commits on {br} not reviewed yet ({n}):\n{liste}\nLook for bugs, regressions, missing tests. "
                   "For each problem: file, line, failing scenario. Fix what is safe on a separate branch; nothing goes into {br} without green tests."),
    "rl_branche_t": ("Relecture de la branche {b}", "Review of branch {b}"),
    "rl_branche": ("Relis la branche {b} ({n} commit(s) d'avance sur {br}, prête à intégrer) : diff contre {br}, tests, ce qui casse. "
                   "Verdict : à verser, à corriger (liste précise) ou à écarter.",
                   "Review branch {b} ({n} commit(s) ahead of {br}, ready to merge): diff against {br}, tests, what breaks. "
                   "Verdict: merge, fix (precise list) or drop."),
    "rl_tests_t": ("Relance des tests du projet", "Re-run of the project tests"),
    "rl_tests": ("Relance les tests du projet et cherche ce qui casse. Tests sans moteur d'abord ; ceux du moteur seulement s'il est libre "
                 "et que la chaîne moteur te donne la main, sinon lis le dernier passage archivé. Pour chaque test rouge ou instable : cause et correction proposée.",
                 "Re-run the project tests and find what breaks. Engine-free tests first; engine tests only if the engine is free "
                 "and the engine chain hands it over, otherwise read the last archived run. For each red or flaky test: cause and proposed fix."),
    "rl_creux_t": ("Chasse aux tests creux", "Hunt for hollow tests"),
    "rl_creux": ("Traque les tests qui ne vérifient rien de réel : appels directs de fonctions internes au lieu des vraies entrées "
                 "(touches, clics, événements du jeu), assertions toujours vraies, tests sans assertion, valeurs recopiées. "
                 "Liste-les et propose, sur une branche à part, la version qui passe par les vraies entrées.",
                 "Hunt for tests that check nothing real: direct calls to internal functions instead of real inputs "
                 "(keys, clicks, game events), always-true assertions, tests without assertions, copied values. "
                 "List them and propose, on a separate branch, a version that goes through the real inputs."),
    "rl_doc_t": ("Roadmap et doc face au code", "Roadmap and docs against the code"),
    "rl_doc": ("Vérifie que la roadmap et la doc collent au code : tâches marquées faites sans code ni test qui le prouve, "
               "code versé que la roadmap ne mentionne pas, docs périmées. Liste les écarts et corrige la doc sur une branche à part.",
               "Check that the roadmap and docs match the code: tasks marked done with no code or test proving it, "
               "merged code the roadmap does not mention, stale docs. List the gaps and fix the docs on a separate branch."),
    "rl_fin": ("\nAttribuée automatiquement : le relecteur était libre (rien à relire, rien en attente).",
               "\nAssigned automatically: the reviewer was free (nothing to review, nothing pending)."),
    "it_nom": ("Relecteur (intérim) {n}", "Reviewer (temp) {n}"),
    "it_role": ("Relecteur (intérim) : relecture partagée, renvoyé à la fin de sa part", "Reviewer (temp): shared review, let go when the part is done"),
    "it_titre": ("Relecture partagée · {n} élément(s) de {de}", "Shared review · {n} item(s) from {de}"),
    "it_mission": ("Relecture partagée avec {de} (sa relecture était estimée à {m} min). Relis seulement ces éléments ({n}) :\n{liste}\n"
                   "Pour chaque problème : fichier, ligne, scénario qui casse. Écris ta progression (pct, restant_min) ; à 100 %, ta part est finie.",
                   "Review shared with {de} (their review was estimated at {m} min). Review only these items ({n}):\n{liste}\n"
                   "For each problem: file, line, failing scenario. Write your progress (pct, restant_min); at 100 % your part is done."),
    "it_garde": ("Relecture partagée (estimée à {m} min, plus d'une heure) : {avec} relit {n} élément(s) :\n{liste_av}\nTu gardes seulement :\n{liste}",
                 "Review shared (estimated at {m} min, over an hour): {avec} reviews {n} item(s):\n{liste_av}\nYou keep only:\n{liste}"),
    "it_bulle": ("je partage ma relecture avec un intérimaire", "I'm sharing my review with a temp"),
    "it_bulle_libre": ("je partage ma relecture avec {n}", "I'm sharing my review with {n}"),
    "it_motif": ("mission d'intérim finie", "temp assignment done"),
}


def tx(cle, en, **k):
    s = TXT[cle][1 if en else 0]
    return s.format(**k) if k else s


def lire(chemin, defaut):
    return jsonio.lire(chemin, defaut)


def ecrire(chemin, donnees, deja=None):
    """Écrit le JSON ; renvoie le texte écrit. O7 : rien n'est réécrit si le texte est celui d'avant (deja) et que le fichier est là."""
    texte = json.dumps(donnees, ensure_ascii=False, indent=1)
    if texte == deja and os.path.exists(chemin):
        return texte
    jsonio.ecrire_texte(chemin, texte)
    return texte


def deja_repondue(dec, reps):
    """Même règle que cloche.deja_repondue : une réponse plus ancienne que la décision (même id reposé) ne la ferme pas."""
    i = str(dec.get("id"))
    if i not in reps:
        return False
    cree, rep = str(dec.get("cree_le") or ""), reps[i]
    return not (cree and rep and rep < cree)


def elements_de(texte):
    """Éléments d'un lot de relecture : les lignes en liste (« - x », « * x », « 1. x ») d'une mission."""
    return [m.group(1).strip()[:200] for m in (ELEMENT_RE.match(l) for l in str(texte or "").splitlines()) if m]


class Automatismes:
    def __init__(self, studio):
        self.s = studio                      # l'objet Studio de studio_etat.py (chemins, langue)
        self.chemin = studio.f("automatismes.json")
        d = lire(self.chemin, {})
        self.d = d if isinstance(d, dict) else {}
        for k, v in (("fins", {}), ("traites", []), ("confiees", []), ("temporaires", {}), ("tyr", {}), ("sans_metier", {}), ("renvois", [])):
            self.d.setdefault(k, v)
        for f in self.d["fins"].values():    # G5 : ancien drapeau « tentée » gardé dans automatismes.json : la fin redevient ouverte
            if isinstance(f, dict):
                f.pop("tente", None)
        self.ecrit = None                    # O7 : dernier texte écrit dans automatismes.json
        self.qui = {}                        # G4 : {"port", "t"} du dernier /api/qui qui a reconnu ce projet

    # ---------- G4 : le port de serveur.json sert-il bien ce projet ?
    def serveur_reconnu(self, port):
        """True si /api/qui sur ce port répond avec ce projet (gardé 30 s). serveur.json peut rester après un arrêt brutal
        et un autre projet peut avoir repris le port : on n'y envoie alors rien."""
        maintenant = time.time()
        if self.qui.get("port") == port and maintenant - self.qui.get("t", 0) < QUI_CACHE_S:
            return True
        self.qui = {}
        projet = getattr(self.s, "projet", None) or os.path.dirname(os.path.abspath(self.s.dossier))
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/qui", timeout=3) as r:
                q = json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException):
            return False
        if not isinstance(q, dict) or not q.get("projet"):
            return False
        def memes(x, y):                     # même dossier, même vu par une jonction ou un lien symbolique
            return (os.path.normcase(os.path.abspath(x)) == os.path.normcase(os.path.abspath(y))
                    or os.path.normcase(os.path.realpath(x)) == os.path.normcase(os.path.realpath(y)))
        if not memes(str(q["projet"]), projet):
            return False
        self.qui = {"port": port, "t": maintenant}
        return True

    # ---------- envoi au serveur du studio
    def poster(self, route, corps):
        if os.environ.get("STUDIO_ESSAI_SANS_ENVOI"):
            self.d.setdefault("essai_envois", []).append({"route": route, "corps": corps, "t": int(time.time())})
            self.d["essai_envois"] = self.d["essai_envois"][-50:]
            return {"ok": True, "essai": True}
        # A1 : un serveur arrêté ou absent ne lève jamais : code 0 = « injoignable », l'appelant réessaie au passage suivant
        try:
            port = int((lire(self.s.f("serveur.json"), {}) or {}).get("port") or 0)
        except (TypeError, ValueError, AttributeError):          # serveur.json abîmé (liste, texte, port non numérique)
            port = 0
        if not port:
            return {"ok": False, "code": 0, "erreur": "serveur du studio introuvable (.studio/serveur.json)"}
        if not self.serveur_reconnu(port):                      # G4 : code 0 = rien d'envoyé, nouvel essai plus tard
            return {"ok": False, "code": 0, "erreur": f"le port {port} de .studio/serveur.json ne sert pas ce projet (ou ne répond pas)"}
        base = f"http://127.0.0.1:{port}"
        req = urllib.request.Request(base + route, data=json.dumps(corps).encode("utf-8"), headers={"Content-Type": "application/json", "Origin": base})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                j = json.loads(r.read().decode("utf-8"))
            return j if isinstance(j, dict) else {"ok": False, "code": 0, "erreur": "réponse du serveur illisible"}
        except urllib.error.HTTPError as e:
            try:
                j = json.loads(e.read().decode("utf-8") or "{}")
            except (ValueError, OSError):
                j = {}
            return dict(j if isinstance(j, dict) else {}, ok=False, code=e.code)
        except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException) as e:   # refusé, coupé, délai dépassé, réponse illisible
            self.qui = {}                                       # G4 : serveur parti ; le port sera revérifié au prochain envoi
            return {"ok": False, "code": 0, "erreur": f"serveur du studio injoignable ({type(e).__name__})"}

    # ---------- données
    def contexte(self, conf, postes, r, progs, ouverts, chaine, sante):
        regl = lire(self.s.f("reglages.json"), {}) or {}
        taches = (lire(self.s.f("taches_disponibles.json"), {}) or {}).get("taches") or []
        decs = lire(self.s.f("decisions.json"), [])
        decs = decs if isinstance(decs, list) else (decs or {}).get("decisions") or []
        rl = lire(self.s.f("reponses.json"), [])
        reps = {str(x.get("id")): str(x.get("repondu_le") or "") for x in (rl if isinstance(rl, list) else []) if isinstance(x, dict) and x.get("id") not in (None, "")}
        ouvertes = [x for x in decs if isinstance(x, dict) and x.get("id") and not deja_repondue(x, reps) and (x.get("statut") or "ouverte") in ("ouverte", "en_attente")]
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
        """G6 : même règle que reglage() du serveur : reglages.json (page), sinon economie de la config, sinon coupé."""
        v = c["regl"].get(cle)
        if isinstance(v, bool):
            return v
        eco = c["conf"].get("economie") if isinstance(c["conf"].get("economie"), dict) else {}
        return eco.get(cle) is True

    def actif_tyran(self, c):
        return c["conf"].get("mode") == "travail" and self.auto(c, "tyrannie_auto") and not c["regl"].get("pause") and not c["sante"].get("bloquant", c["sante"].get("sature"))

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
        attribuer = c["conf"].get("mode") == "travail" and self.auto(c, "attribution_auto") and not c["regl"].get("pause") and not c["sante"].get("bloquant", c["sante"].get("sature"))
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
        interims = (self.d.get("interim") or {}).get("interimaires") or {}
        for pid, f in list(self.d["fins"].items()):
            if (f.get("tente") or not attribuer or maintenant - f["debut"] < delai or pid in interims
                    or maintenant < f.get("reessai", 0)):
                continue                                  # un intérimaire fini n'est pas réaffecté : partage_relecture le renvoie
            # G5 : « tentée » n'est jamais posé avant la réponse du serveur : une panne en cours de route laisse la fin ouverte
            # S31 : la fin de tâche ne confie jamais d'office une tâche marquée moteur (un seul chantier moteur à la fois :
            # c'est à l'utilisateur ou au coordinateur de la lancer), même dans le groupe « son métier »
            cand = next((x for x in self.candidats(c, pid) if x["sans_moteur"]), None)
            if not cand:
                self.clore(pid)
                continue
            r = self.confier(c, pid, cand, "auto:fin-de-tache")
            code = r.get("code")
            f["attribuee"] = {"t": int(maintenant), "titre": cand["titre"], "ok": bool(r.get("ok")), "refus": r.get("erreur"), "code": code}
            if not r.get("ok") and code in (0, 429):
                # A1 : jamais perdue. 0 = serveur arrêté ou absent ; 429 = plafond (une attribution en attente, N par heure).
                # La fin reste ouverte et repart plus tard ; clore() ne vient que du succès, d'un refus net ou du poste qui change d'état.
                f.pop("tente", None)                      # ancien état gardé dans automatismes.json : jamais bloqué
                f["reessai"] = maintenant + (REESSAI_SERVEUR_S if code == 0 else REESSAI_PLAFOND_S)
                f["essais"] = f.get("essais", 0) + 1
                if f["essais"] == 1:                      # une ligne au journal, pas une par essai
                    self.d.setdefault("journal", []).append({"t": int(maintenant), "type": "attribution", "poste": pid, "titre": cand["titre"],
                                                             "ok": False, "refus": r.get("erreur"), "code": code, "reessai": True})
                continue
            # succès, ou refus net (403 : attribution coupée côté serveur ; 400, 404…) : traité une fois pour toutes
            self.d.setdefault("journal", []).append({"t": int(maintenant), "type": "attribution", "poste": pid, "titre": cand["titre"], "ok": bool(r.get("ok")),
                                                     **({} if r.get("ok") else {"refus": r.get("erreur"), "code": code})})
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
        if c["sante"].get("bloquant", c["sante"].get("sature")):
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
                motif = re.sub(r"^(attend|waiting for)\s*", "", dg["raison"])  # hors f-string : Python 3.10/3.11
                dg["bulle"] = (f"{dg['nom']} {tx('attendait', en)} {motif}"
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
                or c["sante"].get("bloquant", c["sante"].get("sature")) or len(c["postes"]) >= 12 or maintenant - self.d.get("embauche_t", 0) < 3600):
            return
        ids = {q["id"] for q in c["postes"]}
        # F39 : une recrue renvoyée (recrues/_anciens) n'est jamais réembauchée d'office : on passe au métier manquant suivant
        tc = next((t for t in c["taches"] if t.get("statut") == "a_faire" and isinstance(t.get("poste"), str) and NOM_RE.match(t["poste"]) and t["poste"] not in ids
                   and not os.path.exists(self.s.f("recrues", "_anciens", t["poste"] + ".json"))), None)
        if not tc:
            return
        self.d["embauche_t"] = maintenant
        lot = [t for t in c["taches"] if t.get("poste") == tc["poste"]][:8]
        nom = tc["poste"].replace("-", " ").capitalize()
        import zlib
        r = self.poster("/api/recruter", {"nom": tc["poste"], "nom_affiche": nom[:40], "role": tx("role_emb", c["en"], n=nom),
                                          "mission": "\n".join(f"- {t['id']} : {t.get('titre', '')}" + (f" ({t['critere']})" if t.get("critere") else "") for t in lot)[:3900],
                                          "auto": True, "apparence": "aucune", "couleur": "#%06x" % (zlib.crc32(tc["poste"].encode()) & 0xFFFFFF)})
        if not r.get("ok") and r.get("code") == 0:      # A1 : serveur injoignable → l'embauche repart dans 60 s, pas dans une heure
            self.d["embauche_t"] = maintenant - 3600 + REESSAI_SERVEUR_S
            return
        self.d.setdefault("journal", []).append({"t": int(maintenant), "type": "embauche", "poste": tc["poste"], "ok": bool(r.get("ok")),
                                                 **({} if r.get("ok") else {"refus": r.get("erreur"), "code": r.get("code")})})

    # ---------- relecteur autonome : libre → il se trouve lui-même une relecture utile (une à la fois, une toutes les 20 min)
    def poste_relecteur(self, c):
        """Poste de relecture : studio.config.json → poste_relecture, sinon le premier poste dont l'id, le nom ou un métier parle de relecture."""
        ids = [q["id"] for q in c["postes"]]
        choisi = c["conf"].get("poste_relecture")
        if isinstance(choisi, str) and choisi in ids:
            return choisi
        for q in c["postes"]:
            ms = " ".join(str(m) for m in (c["metiers"].get(q["id"]) or []))
            if RELECT_RE.search(f"{q['id']} {q.get('nom') or ''} {ms}"):
                return q["id"]
        return None

    def git(self, *a):
        """git en lecture seule dans le projet ; None si pas de dépôt ou commande en échec."""
        projet = getattr(self.s, "projet", None)
        if not projet or not os.path.exists(os.path.join(projet, ".git")):
            return None
        env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0",
                   GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="core.fsmonitor", GIT_CONFIG_VALUE_0="false")
        try:
            r = subprocess.run(["git", "-C", projet, *a], env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception:
            return None
        return r.stdout if r.returncode == 0 else None

    def branche_principale(self, c):
        b = c["conf"].get("branche_principale")
        essais = ([b] if isinstance(b, str) and re.match(r"^[A-Za-z0-9._][A-Za-z0-9._/-]{0,99}$", b) else []) + ["main", "master"]
        return next((x for x in essais if self.git("rev-parse", "--verify", "--quiet", x + "^{commit}") is not None), None)

    def relecture_a_faire(self, c, rl, maintenant):
        """Prochaine relecture utile, par priorité : {genre, tache_id, titre, mission, marque} (jamais None : la rotation finit toujours)."""
        en = c["en"]
        br = self.branche_principale(c)
        if br:
            # 1. commits de la branche principale pas encore relus (premier passage : les 10 derniers)
            tete = (self.git("rev-parse", br) or "").strip()
            dernier = str(rl.get("dernier_commit") or "")
            if tete and tete != dernier:
                suite = bool(dernier) and re.match(r"^[0-9a-f]{7,64}$", dernier) and self.git("merge-base", "--is-ancestor", dernier, br) is not None
                lignes = [l.split("\x1f", 1) for l in (self.git("log", "-n", "30" if suite else "10", "--format=%h%x1f%s", f"{dernier}..{br}" if suite else br) or "").splitlines() if "\x1f" in l]
                if lignes:
                    liste = "\n".join(f"- {h} {s[:100]}" for h, s in lignes)
                    return {"genre": "commits", "tache_id": f"relecture-commits-{tete[:10]}",
                            "titre": tx("rl_commits_t", en, a=lignes[-1][0], b=lignes[0][0], n=len(lignes)),
                            "mission": tx("rl_commits", en, br=br, n=len(lignes), liste=liste), "marque": {"dernier_commit": tete}}
            # 2. branches prêtes à intégrer (d'avance sur la principale, calmes depuis 30 min, actives cette semaine) pas encore relues
            vues = rl.get("branches") if isinstance(rl.get("branches"), dict) else {}
            for l in (self.git("for-each-ref", "--sort=-committerdate", "--count=30", "--format=%(refname:short)%1f%(objectname)%1f%(committerdate:unix)", "refs/heads") or "").splitlines():
                p = l.split("\x1f")
                if len(p) != 3 or p[0] == br or not p[2].isdigit() or vues.get(p[0]) == p[1]:
                    continue
                age = maintenant - int(p[2])
                if age < RELECT_BRANCHE_CALME_S or age > RELECT_BRANCHE_AGE_S:
                    continue
                n = (self.git("rev-list", "--count", f"{br}..{p[1]}") or "").strip()
                if n.isdigit() and int(n) > 0:
                    return {"genre": "branche", "tache_id": ("relecture-branche-" + re.sub(r"[^A-Za-z0-9_.-]", ".", p[0]))[:69] + "-" + p[1][:10],
                            "titre": tx("rl_branche_t", en, b=p[0]), "mission": tx("rl_branche", en, b=p[0], n=int(n), br=br),
                            "marque": {"branche": [p[0], p[1]]}}
        # 3 à 5. rotation : tests du projet, tests creux, roadmap et doc ; le plus ancien d'abord (à égalité : cet ordre)
        rot = rl.get("rotation") if isinstance(rl.get("rotation"), dict) else {}
        g = min(RELECT_ROTATION, key=lambda x: rot.get(x, 0))
        cle = {"tests": "rl_tests", "tests_creux": "rl_creux", "doc": "rl_doc"}[g]
        return {"genre": g, "tache_id": f"relecture-{g}-{time.strftime('%Y%m%d%H%M', time.localtime(maintenant))}",
                "titre": tx(cle + "_t", en), "mission": tx(cle, en), "marque": {}}

    def relecteur(self, c, maintenant):
        chemin = self.s.f("relecteur.json")
        rl = lire(chemin, {})
        rl = rl if isinstance(rl, dict) else {}
        pid = self.poste_relecteur(c)
        res = {"poste": pid, "derniere": rl.get("derniere"), "raison": None, "prochaine_dans_s": None}
        regl, en = c["regl"], c["en"]
        q = next((x for x in c["postes"] if x["id"] == pid), None)
        f = self.d["fins"].get(pid) if pid else None
        raison = (("no review desk" if en else "aucun poste de relecture") if not q else
                  ("paused" if en else "en pause (Tout couper)") if c["conf"].get("mode") != "travail" or regl.get("pause") else
                  ("machine saturated" if en else "machine saturée") if c["sante"].get("bloquant", c["sante"].get("sature")) else
                  ("automatic assignment off" if en else "attribution automatique coupée") if not (self.auto(c, "attribution_auto") or self.auto(c, "tyrannie_auto")) else
                  ("busy" if en else "occupé") if q.get("etat") != "disponible" or q.get("demandes") else
                  ("end of task being handled" if en else "fin de tâche en cours") if f and not f.get("tente") and self.auto(c, "attribution_auto") else None)
        if not raison and maintenant - rl.get("t", 0) < RELECT_ECART_S:
            res["prochaine_dans_s"] = int(rl.get("t", 0) + RELECT_ECART_S - maintenant)
            raison = "one every 20 min" if en else "une toutes les 20 min"
        if raison:
            res["raison"] = raison
            return res
        cand = self.relecture_a_faire(c, rl, maintenant)
        rl["t"] = int(maintenant)                       # même un refus du serveur compte : jamais de boucle
        origine = "auto:fin-de-tache" if self.auto(c, "attribution_auto") else "auto:temporaire"
        r = self.confier(c, pid, dict(cand, mission=cand["mission"] + tx("rl_fin", en)), origine)
        if not r.get("ok") and r.get("code") == 0:      # A1 : serveur injoignable → nouvel essai dans 60 s, pas dans 20 min
            rl["t"] = int(maintenant - RELECT_ECART_S + REESSAI_SERVEUR_S)
        if r.get("ok"):
            mq = cand["marque"]
            if mq.get("dernier_commit"):
                rl["dernier_commit"] = mq["dernier_commit"]
            if mq.get("branche"):
                rl.setdefault("branches", {})[mq["branche"][0]] = mq["branche"][1]
                rl["branches"] = dict(list(rl["branches"].items())[-200:])
            if cand["genre"] in RELECT_ROTATION:
                rl.setdefault("rotation", {})[cand["genre"]] = int(maintenant)
            rl["derniere"] = {"t": int(maintenant), "genre": cand["genre"], "tache_id": cand["tache_id"], "titre": cand["titre"], "poste": pid,
                              "elements": elements_de(cand["mission"])[:60]}
        injoignable = not r.get("ok") and r.get("code") == 0
        dern_rl = next((j for j in reversed(self.d.get("journal") or []) if j.get("type") == "relecteur"), {})
        if not (injoignable and dern_rl.get("code") == 0):  # serveur arrêté : une ligne au journal, pas une par minute
            self.d.setdefault("journal", []).append({"t": int(maintenant), "type": "relecteur", "poste": pid, "titre": cand["titre"], "ok": bool(r.get("ok")),
                                                     **({} if r.get("ok") else {"code": r.get("code")})})
        ecrire(chemin, rl)
        res.update(derniere=rl.get("derniere"), prochaine_dans_s=REESSAI_SERVEUR_S if injoignable else RELECT_ECART_S, raison=None if r.get("ok") else str(r.get("erreur") or r.get("code") or "refus"))
        return res

    # ---------- relecture partagée : plus d'une heure prévue → la moitié à un relecteur libre ou à un intérimaire
    def relecteurs(self, c):
        """Postes de relecture : le poste désigné (poste_relecture) et tout poste dont l'id, le nom ou un métier parle de relecture."""
        out = []
        for q in c["postes"]:
            ms = " ".join(str(m) for m in (c["metiers"].get(q["id"]) or []))
            if q["id"] == c["conf"].get("poste_relecture") or RELECT_RE.search(f"{q['id']} {q.get('nom') or ''} {ms}"):
                out.append(q)
        return out

    def lot_relecture(self, c, q, rl):
        """Ce que le relecteur a devant lui : « lot » ou « restantes » de sa progression, sinon les lignes en liste de sa dernière
        demande, sinon celles de la dernière relecture que le relecteur autonome lui a confiée."""
        pr = self.prog(c, q["id"])
        for k in ("lot", "restantes"):
            if isinstance(pr.get(k), list) and len(pr[k]) >= 2:
                return [str(x)[:200] for x in pr[k] if str(x).strip()][:60]
        dossier = self.s.f("demandes")
        try:
            fichiers = sorted((os.path.join(dossier, f) for f in os.listdir(dossier) if f.endswith(".json") and f != "statuts.json"),
                              key=os.path.getmtime, reverse=True)[:40]
        except OSError:
            fichiers = []
        for f in fichiers:
            x = lire(f, None)
            if isinstance(x, dict) and q["id"] in (x.get("nom"), x.get("cible"), x.get("agent")):
                e = elements_de(x.get("mission") or x.get("texte"))
                if len(e) >= 2:
                    return e[:60]
                break
        d = rl.get("derniere") if isinstance(rl.get("derniere"), dict) else {}
        return list(d.get("elements") or [])[:60] if d.get("poste") == q["id"] else []

    def nom_interim(self, c):
        ids = {q["id"] for q in c["postes"]}
        for n in range(1, 100):
            nom = f"{INTERIM_PREFIXE}{n}"
            if nom not in ids and not any(os.path.exists(self.s.f("recrues", *p, nom + ".json")) for p in ((), ("_anciens",))):
                return n, nom
        return None, None

    def partage_relecture(self, c, maintenant):
        en, st = c["en"], self.d.setdefault("interim", {})
        for k, v in (("interimaires", {}), ("partages", []), ("lots", {})):
            st.setdefault(k, v)
        st["partages"] = [p for p in st["partages"] if maintenant - p.get("t", 0) < 6 * 3600][-20:]
        par_id = {q["id"]: q for q in c["postes"]}
        journal = self.d.setdefault("journal", [])
        rels = self.relecteurs(c)
        # relecture encore à faire (dans les 30 min) : tâche de relecture pas encore prise, ou relecteur au-delà d'une heure
        a_faire = any(t.get("statut") == "a_faire" and t["id"] not in c["deja"] and (RELECT_RE.search(str(t.get("metier") or ""))
                      or t.get("poste") in {q["id"] for q in rels}) for t in c["taches"]) or any(
            q["id"] not in st["interimaires"] and isinstance(q.get("restant_min"), (int, float)) and q["restant_min"] > PARTAGE_SEUIL_MIN
            and st["lots"].get(q["id"]) is None for q in rels)
        # 1. fin de part : renvoi de l'intérimaire (sauf relecture à faire : gardé 30 min au plus)
        for nom, it in list(st["interimaires"].items()):
            q = par_id.get(nom)
            if not q:                                           # déjà renvoyé (à la main ou par la tyrannie) ; pas encore vu : on attend
                if maintenant - it.get("t", 0) > 300 and not os.path.exists(self.s.f("recrues", nom + ".json")):
                    st["interimaires"].pop(nom, None)
                continue
            if q.get("etat") in ("travaille", "bloque"):
                it["a_travaille"] = True
            if not it.get("a_travaille") or q.get("etat") not in ("disponible", "fini") or q.get("demandes"):
                continue
            it.setdefault("fini_t", int(maintenant))
            if (a_faire and maintenant - it["fini_t"] < INTERIM_GARDE_S) or maintenant - it.get("essai_renvoi", 0) < 300:
                continue
            it["essai_renvoi"] = int(maintenant)
            r = self.poster("/api/renvoyer", {"nom": nom, "motif": tx("it_motif", en)})
            journal.append({"t": int(maintenant), "type": "renvoi_interim", "poste": nom, "ok": bool(r.get("ok"))})
            if r.get("ok"):
                st["interimaires"].pop(nom, None)
                self.d["renvois"] = (self.d["renvois"] + [{"t": int(maintenant), "nom": nom, "nom_affiche": q.get("nom") or nom,
                                                           "role": tx("it_motif", en)}])[-20:]
        # 2. partage
        actif = (c["conf"].get("mode") == "travail" and not c["regl"].get("pause") and not c["sante"].get("bloquant", c["sante"].get("sature"))
                 and any(self.auto(c, k) for k in ("attribution_auto", "tyrannie_auto", "embauche_auto")))
        if not actif:
            return {"interimaires": sorted(st["interimaires"]), "partages": st["partages"][-5:]}
        rl = lire(self.s.f("relecteur.json"), {})
        rl = rl if isinstance(rl, dict) else {}
        for q in rels:
            pid, reste = q["id"], q.get("restant_min")
            if pid in st["interimaires"] or pid.startswith(INTERIM_PREFIXE) or not isinstance(reste, (int, float)) or reste <= PARTAGE_SEUIL_MIN:
                if isinstance(reste, (int, float)) and reste <= PARTAGE_SEUIL_MIN:
                    st["lots"].pop(pid, None)                   # retombé sous l'heure : un prochain gros lot pourra être partagé
                continue
            lot = self.lot_relecture(c, q, rl)
            import zlib
            cle = f"{len(lot)}:{zlib.crc32(chr(10).join(lot).encode('utf-8')):08x}"     # stable d'un lancement à l'autre
            if len(lot) < 2 or st["lots"].get(pid) == cle:
                continue
            if sum(1 for p in st["partages"] if maintenant - p["t"] < 3600) >= PARTAGE_PAR_HEURE:
                break
            garde, part = lot[:len(lot) // 2], lot[len(lot) // 2:]
            de = q.get("nom") or pid
            mission = tx("it_mission", en, de=de, m=int(reste), n=len(part), liste="\n".join(f"- {x}" for x in part))
            titre = tx("it_titre", en, n=len(part), de=de)
            tid = f"relecture-partagee-{pid}-{cle.split(':')[1]}"[:80]
            libre = next((x for x in rels if x["id"] != pid and x.get("etat") == "disponible" and not x.get("demandes")), None)
            if libre:
                avec = libre.get("nom") or libre["id"]
                origine = "auto:fin-de-tache" if self.auto(c, "attribution_auto") else "auto:temporaire"
                r = self.confier(c, libre["id"], {"tache_id": tid, "mission": mission, "titre": titre}, origine)
                bulle = tx("it_bulle_libre", en, n=avec)
                if r.get("ok") and libre["id"] in st["interimaires"]:
                    st["interimaires"][libre["id"]].update(elements=part, pour=pid, a_travaille=False)   # intérimaire gardé : nouvelle part
                    st["interimaires"][libre["id"]].pop("fini_t", None)
            else:
                if len(st["interimaires"]) >= INTERIM_MAX or len(c["postes"]) >= 12:
                    st["lots"][pid] = cle
                    journal.append({"t": int(maintenant), "type": "partage", "poste": pid, "ok": False,
                                    "refus": f"{INTERIM_MAX} intérimaires au plus" if len(st["interimaires"]) >= INTERIM_MAX else "12 bureaux"})
                    continue
                n, nom = self.nom_interim(c)
                if not nom:
                    continue
                avec, bulle = tx("it_nom", en, n=n), tx("it_bulle", en)
                r =self.poster("/api/recruter", {"nom": nom, "nom_affiche": avec, "role": tx("it_role", en), "mission": mission[:3900],
                                                  "lancer": True, "apparence": "aucune", "couleur": "#%06x" % (zlib.crc32(nom.encode()) & 0xFFFFFF)})
                if r.get("ok"):
                    self.poster("/api/agent", {"id": nom, "metiers": ["relecture"]})
                    st["interimaires"][nom] = {"t": int(maintenant), "pour": pid, "elements": part, "a_travaille": False}
                journal.append({"t": int(maintenant), "type": "embauche_interim", "poste": nom, "pour": pid, "ok": bool(r.get("ok"))})
            st["lots"][pid] = cle                               # même un refus compte : jamais de boucle sur le même lot
            if r.get("ok"):
                self.poster("/api/demande", {"cible": pid, "texte": tx("it_garde", en, m=int(reste), avec=avec, n=len(part),
                                                                        liste_av="\n".join(f"- {x}" for x in part),
                                                                        liste="\n".join(f"- {x}" for x in garde))[:1990], "via": "ecrit"})
                st["partages"].append({"t": int(maintenant), "poste": pid, "avec": avec, "n": len(part), "garde": len(garde), "bulle": bulle})
            journal.append({"t": int(maintenant), "type": "partage", "poste": pid, "avec": avec, "n": len(part), "ok": bool(r.get("ok")),
                            "refus": r.get("erreur")})
        return {"interimaires": sorted(st["interimaires"]), "partages": st["partages"][-5:]}

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
            try:
                self.d["relecteur"] = self.relecteur(c, maintenant)
            except Exception as e:                              # le relecteur autonome ne fige jamais les autres automatismes
                self.d["relecteur"] = {"raison": f"{type(e).__name__} : {e}"[:200]}
            try:
                self.d["partage"] = self.partage_relecture(c, maintenant)
            except Exception as e:                              # la relecture partagée ne fige jamais les autres automatismes
                self.d["partage"] = {"erreur": f"{type(e).__name__} : {e}"[:200]}
            try:                                                # plan de restructuration accepté : renvois « après sa tâche »
                import restructuration                          # (le serveur vérifie la tâche finie et le mode absent)
                if maintenant - self.d.get("restru_t", 0) >= 120 and any(p.get("statut") == "en_cours" for p in restructuration.plans(self.s.dossier)):
                    self.d["restru_t"] = int(maintenant)
                    self.poster("/api/restructuration", {"action": "suite"})
            except Exception as e:
                self.d["restru_erreur"] = f"{type(e).__name__} : {e}"[:200]
        except Exception as e:                                  # un automatisme en panne ne fige jamais l'alimentation
            self.d["erreur"] = f"{type(e).__name__} : {e}"[:200]
        else:                                                   # A2 : un passage sans panne efface l'erreur d'avant
            self.d.pop("erreur", None)
        self.d["journal"] = (self.d.get("journal") or [])[-200:]       # lot E : une nuit d'absence tient dans le journal
        self.ecrit = ecrire(self.chemin, self.d, self.ecrit)     # O7 : pas de réécriture à l'identique
        dern = self.d.get("dernier") or {}
        return {"serveur": True, "tyrannie": dern, "fins": {k: {"debut": int(v["debut"]), "fini": v.get("fini", "")} for k, v in self.d["fins"].items()},
                "temporaires": {k: v for k, v in self.d["temporaires"].items() if maintenant - v.get("t", 0) < 6 * 3600},
                "renvois": [x for x in self.d["renvois"] if maintenant - x["t"] < 600], "remonter": [x["decision"] for x in dern.get("diagnostics") or [] if x.get("decision")],
                "relecteur": self.d.get("relecteur") or {}, "erreur": self.d.get("erreur"),
                "partages": [x for x in ((self.d.get("interim") or {}).get("partages") or []) if maintenant - x.get("t", 0) < 600],
                "interimaires": sorted((self.d.get("interim") or {}).get("interimaires") or {}),
                "historique": self.historique(maintenant)}

    def historique(self, maintenant):
        """Lot E : ce que les automatismes ont fait seuls depuis 24 h (attributions, relectures, partages, embauches, renvois),
        réussi seulement. La page en tire le résumé « Pendant ton absence » même si aucun onglet n'était ouvert."""
        j = [x for x in (self.d.get("journal") or []) if isinstance(x, dict) and x.get("ok") and maintenant - x.get("t", 0) < 86400]
        vus = {(x.get("t"), x.get("poste")) for x in j if x.get("type") == "renvoi_interim"}
        r = [{"t": x["t"], "type": "renvoi", "poste": x.get("nom"), "nom_affiche": x.get("nom_affiche")} for x in self.d.get("renvois") or []
             if isinstance(x, dict) and maintenant - x.get("t", 0) < 86400 and (x.get("t"), x.get("nom")) not in vus]
        return sorted(j + r, key=lambda x: x.get("t", 0))[-150:]
