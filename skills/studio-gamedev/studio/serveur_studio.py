"""Serveur local du studio gamedev (Python 3.10+, bibliothèque standard seulement).

Lancer :  python -I -B serveur_studio.py --projet <dossier du projet> [--port N]
          (sans --port : celui de <projet>/.studio/studio.config.json, sinon 8790 ; s'il est pris, le premier libre après)
Ouvrir :  http://127.0.0.1:<port>/studio.html

GET  : sert d'abord <projet>/.studio/ (config, profil, roadmap.json, progression/…), puis les fichiers
       du skill posés à côté de ce script (studio.html, roadmap.js, roadmap.css, questions.*.json, cartes/).
       Pas de liste de dossier ; extensions permises seulement ; jamais rien hors de ces deux dossiers.
POST : petite API JSON réservée à la page servie par ce même serveur :
  /api/questionnaire  {cle?, valeur?, source?, via?, texte_brut?, raison?, chapitre_courant?, chapitres_finis?, etat?, mode?, langue?}
                      -> .studio/reponses_questionnaire.json (fusion, écriture atomique)
  /api/profil         {maitre?, assistant?, voix?}                 -> .studio/profil.json (fusion, valeurs bornées)
  /api/demande        {cible, texte, via}                          -> .studio/demandes_vocales/<horodatage>_<cible>.json
  /api/repondre       {id, choix?, texte_libre?}                   -> .studio/reponses.json (décision ou question de suivi)
  /api/reglages       {frequence_rapport_min?, attribution_auto?, embauche_auto?}  -> .studio/reglages.json
  /api/confier        {agent, mission, titre?, tache_id?, origine?}  -> .studio/demandes/<horodatage>_<agent>.json (tâche confiée)
  /api/renvoyer       {nom, motif?}                                -> recrue archivée : .studio/recrues/_anciens/, .studio/anciens/agents/
  /api/reembaucher    {nom}                                        -> remet une recrue archivée dans l'équipe (lancer: false)
  /api/recruter       {nom, nom_affiche?, role, mission, poste?, couleur?, apparence?, skills?, lancer?, remplacer?, via?}
                      -> <dossier_agents>/<nom>.md (définition d'agent, dans le projet seulement),
                         .studio/recrues/<nom>.json (+ recrues/index.json), .studio/demandes/<horodatage>_<nom>.json
  /api/transcrire     audio brut (webm/ogg/wav, 8 Mo au plus)      -> {"ok", "texte"} ; 501 si faster-whisper absent

Sécurité : écoute 127.0.0.1 seulement ; en-têtes Host et Origin vérifiés (page du même serveur) ;
corps JSON ≤ 64 Ko ; champs bornés ; écriture seulement dans les fichiers ci-dessus ; aucune commande exécutée.
Demandes : nom unique (millisecondes + code au hasard) créé en mode exclusif, jamais d'écrasement ; la même demande
(même route, même cible, même texte) reçue deux fois en moins de 60 s n'est écrite qu'une fois.
Automatismes (attribution en fin de tâche, embauche) : refusés tant que le réglage n'est pas activé (economie ou
reglages.json, coupés par défaut) ; au plus une attribution automatique en attente par poste et 4 par heure ;
au plus une embauche automatique par heure, 12 bureaux. Un renvoi n'efface rien (archivage, réembauche possible).
Un recrutement n'exécute rien : il écrit une demande que Claude lit (SKILL.md, « Demandes ») avant de lancer l'agent.
« remplacer » n'écrase qu'une recrue écrite par ce studio (fiche recrues/<nom>.json + marque dans le fichier),
jamais un agent écrit à la main ni un lien ; les règles de la config injectées dans l'agent sont bornées (20 × 200 caractères).
JSON lus avec ou sans BOM.
"""
import argparse
import json
import os
import re
import socket
import sys
import tempfile
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

ICI = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True   # jamais de __pycache__ dans le dossier du skill
PORT_DEFAUT = 8790
MARQUE_RECRUE = "<!-- studio-gamedev : recrue -->"
OUTILS_AGENT = "Read, Grep, Glob, Edit, Write, Bash, Skill"
MODELES_AGENT = {"haiku", "sonnet", "opus", "inherit"}
MAX_CORPS = 64 * 1024
MAX_AUDIO = 8 * 1024 * 1024
VERROU = threading.Lock()

EXTENSIONS = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
              ".json": "application/json; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
              ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif", ".ogg": "audio/ogg", ".mp3": "audio/mpeg",
              ".wav": "audio/wav", ".woff2": "font/woff2", ".ttf": "font/ttf", ".txt": "text/plain; charset=utf-8", ".md": "text/plain; charset=utf-8"}

CLE_RE = re.compile(r"^(?:[a-z0-9_]{1,40}(?:\.[a-z0-9_]{1,40}){0,3}|suivi-[a-z0-9-]{1,40})$")
ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")
CIBLE_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
NOM_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,39}$")
SKILL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:_.-]{0,79}$")
APPARENCES = {"aucune", "casque", "casquette", "beret", "lunettes", "chapeau", "casque_audio", "barbe"}
NOMS_RESERVES = {"assistant", "maitre", "index", "statuts"}
COULEUR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
SOURCES = {"utilisateur", "deduit", "a_confirmer", "voix_a_interpreter"}
VIAS = {"clic", "ecrit", "voix", "passer", "analyse"}
ETATS = {"en_cours", "termine"}
MODES = {"rapide", "complet", "adoption"}
ORIGINE_RE = re.compile(r"^(page|tache:[A-Za-z0-9_.:-]{1,80}|auto:fin-de-tache)$")
NB_BUREAUX = 12
DOUBLON_S = 60
AUTO_ATTENTE_MAX = 1        # attribution automatique : une seule en attente par poste
AUTO_PAR_HEURE = 4          # … et 4 par heure et par poste au plus
EMBAUCHE_AUTO_DELAI_S = 3600
OPTIM_DELAI_MIN = 30
FINIS = ("fini", "faite", "écart", "ecart", "annul", "pas lancé")

# Valeurs permises de profil.json (references/questionnaire.md, « Format de profil.json »)
PERMIS = {
    "morphologie": {"mince", "moyenne", "costaude", "petite", "grande"},
    "coupe": {"courts", "longs", "boucles", "en_bataille", "queue", "rase", "aucune"},
    "style": {"sweat", "chemise", "bleu_de_travail", "heros", "tablier", "costume", "armure", "robe"},
    "accessoire": {"aucun", "casque", "casque_audio", "casquette", "beret", "chapeau", "lunettes", "barbe", "couronne", "bandeau", "capuche", "cornes"},
    "espece": {"humain", "robot", "animal", "creature"},
    "humour": {"aucun", "leger", "absurde", "geek", "noir"},
    "voix_haute": {"non", "oui", "cloche"},
}


class Refus(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def maintenant():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def ecrire_json(chemin, donnees):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(chemin), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=1)
    os.replace(tmp, chemin)


def lire_json(chemin, defaut):
    try:
        with open(chemin, encoding="utf-8-sig") as f:   # avec ou sans BOM
            return json.load(f)
    except Exception:
        return defaut


def texte(d, cle, maxi, requis=False):
    v = d.get(cle, "")
    if v is None:
        v = ""
    if not isinstance(v, str):
        raise Refus(400, f"{cle} : texte attendu")
    v = v.replace("\r", "").strip()
    if requis and not v:
        raise Refus(400, f"{cle} : obligatoire")
    if len(v) > maxi:
        raise Refus(400, f"{cle} : {maxi} caractères au plus")
    return v


def valeur_reponse(v):
    """Réponse au questionnaire : texte, nombre, booléen, null, ou liste courte de textes."""
    if v is None or isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        if not (-1e9 < v < 1e9):
            raise Refus(400, "valeur : nombre hors bornes")
        return v
    if isinstance(v, str):
        if len(v) > 4000:
            raise Refus(400, "valeur : 4 000 caractères au plus")
        return v.replace("\r", "").strip()
    if isinstance(v, list):
        if len(v) > 30 or not all(isinstance(x, str) and len(x) <= 200 for x in v):
            raise Refus(400, "valeur : liste de 30 textes courts au plus")
        return [x.strip() for x in v]
    raise Refus(400, "valeur : type non permis")


class Etat:
    projet = ""
    studio = ""  # <projet>/.studio


def creer_unique(dossier, suffixe, donnees):
    """Fichier au nom unique (horodatage, millisecondes + code au hasard), créé en mode exclusif : jamais d'écrasement."""
    os.makedirs(dossier, exist_ok=True)
    for _ in range(20):
        t = time.time()
        ident = time.strftime("%Y%m%d-%H%M%S", time.localtime(t)) + f"-{int(t * 1000) % 1000:03d}{os.urandom(2).hex()}_{suffixe}"
        try:
            with open(os.path.join(dossier, ident + ".json"), "x", encoding="utf-8") as f:
                json.dump(dict(donnees, id=ident), f, ensure_ascii=False, indent=1)
            return ident
        except FileExistsError:
            continue
    raise Refus(503, "impossible de créer la demande")


_RECENTS = {}


def doublon(cle, resultat=None):
    """Même demande (même route, même cible, même texte) en moins de 60 s : on renvoie le premier résultat."""
    t = time.time()
    for k in [k for k, (tk, _) in _RECENTS.items() if t - tk > DOUBLON_S]:
        del _RECENTS[k]
    if resultat is None:
        return _RECENTS.get(cle, (0, None))[1]
    _RECENTS[cle] = (t, resultat)
    return resultat


def reglage(nom):
    """Marche / arrêt d'un automatisme : reglages.json (page), sinon economie de la config, sinon coupé."""
    r = lire_json(os.path.join(Etat.studio, "reglages.json"), {})
    if isinstance(r, dict) and isinstance(r.get(nom), bool):
        return r[nom]
    conf = lire_json(os.path.join(Etat.studio, "studio.config.json"), {})
    eco = conf.get("economie") if isinstance(conf, dict) and isinstance(conf.get("economie"), dict) else {}
    return eco.get(nom) is True


def iso_t(s):
    try:
        return time.mktime(time.strptime(str(s)[:19], "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, OverflowError):
        return 0


class Studio(SimpleHTTPRequestHandler):
    server_version = "StudioGamedev/1.0"
    sys_version = ""

    def log_message(self, fmt, *args):  # discret : seulement les POST et les erreurs
        if self.command == "POST" or (len(args) > 1 and str(args[1])[:1] == "5"):
            sys.stderr.write("%s %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    def hotes_permis(self):
        port = self.server.server_address[1]
        return {f"127.0.0.1:{port}", f"localhost:{port}"}

    def repondre(self, code, donnees):
        corps = json.dumps(donnees, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(corps)

    # ---------------------------------------------------------------- GET
    def trouver(self, chemin_url):
        rel = unquote(urlsplit(chemin_url).path).lstrip("/") or "studio.html"
        if "\\" in rel or "\x00" in rel or any(p in ("", ".", "..") for p in rel.split("/")):
            return None
        ext = os.path.splitext(rel)[1].lower()
        if ext not in EXTENSIONS:
            return None
        for base in (Etat.studio, ICI):
            if not base:
                continue
            base_r = os.path.realpath(base)
            p = os.path.realpath(os.path.join(base_r, *rel.split("/")))
            if p.startswith(base_r + os.sep) and os.path.isfile(p):
                # le code du serveur et ses notes ne sont jamais servis depuis le dossier du skill
                if base == ICI and (rel.startswith("outils/") or ext in (".md",)):
                    return None
                return p, EXTENSIONS[ext]
        return None

    def do_GET(self):
        if self.headers.get("Host", "") not in self.hotes_permis():
            self.repondre(403, {"ok": False, "erreur": "hôte refusé"})
            return
        if urlsplit(self.path).path in ("", "/"):
            self.send_response(302)
            self.send_header("Location", "/studio.html")
            self.end_headers()
            return
        trouve = self.trouver(self.path)
        if not trouve:
            self.repondre(404, {"ok": False, "erreur": "introuvable"})
            return
        chemin, type_ = trouve
        try:
            with open(chemin, "rb") as f:
                corps = f.read()
        except OSError:
            self.repondre(404, {"ok": False, "erreur": "illisible"})
            return
        self.send_response(200)
        self.send_header("Content-Type", type_)
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("Cache-Control", "no-store" if type_.startswith(("application/json", "text/html", "text/javascript", "text/css")) else "max-age=300")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(corps)

    def do_HEAD(self):
        self.repondre(405, {"ok": False})

    # ---------------------------------------------------------------- POST
    def do_POST(self):
        try:
            if self.headers.get("Host", "") not in self.hotes_permis():
                raise Refus(403, "hôte refusé")
            origine = self.headers.get("Origin", "")
            if origine not in {"http://" + h for h in self.hotes_permis()}:
                raise Refus(403, "origine refusée")
            route = urlsplit(self.path).path
            n = int(self.headers.get("Content-Length", "0") or 0)
            if route == "/api/transcrire":
                if n <= 0 or n > MAX_AUDIO:
                    raise Refus(413, "audio vide ou trop long")
                type_ = self.headers.get("Content-Type", "")
                if not type_.startswith(("audio/", "video/webm", "application/octet-stream")):
                    raise Refus(415, "audio attendu")
                audio = self.rfile.read(n)
                self.repondre(200, transcrire(audio))
                return
            if "application/json" not in self.headers.get("Content-Type", ""):
                raise Refus(415, "JSON attendu")
            if n <= 0 or n > MAX_CORPS:
                raise Refus(413, "corps vide ou trop gros")
            try:
                d = json.loads(self.rfile.read(n).decode("utf-8"))
            except Exception:
                raise Refus(400, "JSON invalide")
            if not isinstance(d, dict):
                raise Refus(400, "objet JSON attendu")
            action = {"/api/questionnaire": route_questionnaire, "/api/profil": route_profil, "/api/demande": route_demande,
                      "/api/repondre": route_repondre, "/api/reglages": route_reglages,
                      "/api/recruter": route_recruter, "/api/confier": route_confier,
                      "/api/renvoyer": route_renvoyer, "/api/reembaucher": route_reembaucher}.get(route)
            if not action:
                raise Refus(404, "route inconnue")
            with VERROU:
                self.repondre(200, action(d))
        except Refus as e:
            self.repondre(e.code, {"ok": False, "erreur": str(e)})
        except Exception as e:  # jamais de trace détaillée vers la page
            sys.stderr.write(f"erreur interne : {e!r}\n")
            self.repondre(500, {"ok": False, "erreur": "erreur interne"})


# -------------------------------------------------------------------- routes
def route_questionnaire(d):
    chemin = os.path.join(Etat.studio, "reponses_questionnaire.json")
    q = lire_json(chemin, None)
    if not isinstance(q, dict):
        q = {"version": 1, "etat": "en_cours", "cree_le": maintenant(), "reponses": {}}
    if not isinstance(q.get("reponses"), dict):
        q["reponses"] = {}
    cle = texte(d, "cle", 80)
    if cle:
        if not CLE_RE.match(cle):
            raise Refus(400, "cle invalide")
        source = texte(d, "source", 30) or "utilisateur"
        via = texte(d, "via", 10) or "clic"
        if source not in SOURCES or via not in VIAS:
            raise Refus(400, "source ou via inconnus")
        r = {"valeur": valeur_reponse(d.get("valeur")), "source": source, "via": via, "t": maintenant()}
        for opt, maxi in (("texte_brut", 4000), ("raison", 300)):
            v = texte(d, opt, maxi)
            if v:
                r[opt] = v
        if len(q["reponses"]) >= 400 and cle not in q["reponses"]:
            raise Refus(413, "trop de réponses")
        q["reponses"][cle] = r
    if "chapitre_courant" in d:
        c = texte(d, "chapitre_courant", 40)
        if c and not re.match(r"^[a-z0-9_]{1,40}$", c):
            raise Refus(400, "chapitre invalide")
        q["chapitre_courant"] = c
    if "chapitres_finis" in d:
        l = d["chapitres_finis"]
        if not isinstance(l, list) or len(l) > 20 or not all(isinstance(x, str) and re.match(r"^[a-z0-9_]{1,40}$", x) for x in l):
            raise Refus(400, "chapitres_finis invalide")
        q["chapitres_finis"] = l
    for champ, permis in (("etat", ETATS), ("mode", MODES)):
        if champ in d:
            v = texte(d, champ, 20)
            if v not in permis:
                raise Refus(400, f"{champ} inconnu")
            q[champ] = v
    if "langue" in d:
        lg = texte(d, "langue", 5)
        if not re.match(r"^[a-z]{2}$", lg):
            raise Refus(400, "langue invalide")
        q["langue"] = lg
    q["maj"] = maintenant()
    ecrire_json(chemin, q)
    return {"ok": True, "maj": q["maj"], "etat": q.get("etat")}


def route_profil(d):
    chemin = os.path.join(Etat.studio, "profil.json")
    p = lire_json(chemin, None)
    if not isinstance(p, dict):
        p = {"version": 1}

    def apparence(a, dest):
        if not isinstance(a, dict):
            raise Refus(400, "apparence : objet attendu")
        if "morphologie" in a:
            if a["morphologie"] not in PERMIS["morphologie"]:
                raise Refus(400, "morphologie inconnue")
            dest["morphologie"] = a["morphologie"]
        if "peau" in a:
            if not isinstance(a["peau"], str) or not COULEUR_RE.match(a["peau"]):
                raise Refus(400, "peau : #rrggbb")
            dest["peau"] = a["peau"]
        if "accessoire" in a:
            if a["accessoire"] not in PERMIS["accessoire"]:
                raise Refus(400, "accessoire inconnu")
            dest["accessoire"] = a["accessoire"]
        for bloc, champ_liste, couleurs in (("cheveux", "coupe", ("couleur",)), ("tenue", "style", ("couleur1", "couleur2"))):
            if bloc in a:
                b = a[bloc]
                if not isinstance(b, dict):
                    raise Refus(400, f"{bloc} : objet attendu")
                out = dict(dest.get(bloc) or {})
                if champ_liste in b:
                    if b[champ_liste] not in PERMIS[champ_liste]:
                        raise Refus(400, f"{bloc}.{champ_liste} inconnu")
                    out[champ_liste] = b[champ_liste]
                for c in couleurs:
                    if c in b:
                        if not isinstance(b[c], str) or not COULEUR_RE.match(b[c]):
                            raise Refus(400, f"{bloc}.{c} : #rrggbb")
                        out[c] = b[c]
                dest[bloc] = out
        return dest

    for qui in ("maitre", "assistant"):
        if qui not in d:
            continue
        e = d[qui]
        if not isinstance(e, dict):
            raise Refus(400, f"{qui} : objet attendu")
        cible = p.setdefault(qui, {})
        for champ, maxi in (("nom", 40), ("titre", 60), ("appellation", 30), ("espece_detail", 60), ("personnalite", 120)):
            if champ in e:
                cible[champ] = texte(e, champ, maxi)
        if "langue" in e:
            lg = texte(e, "langue", 7)
            if lg and not re.match(r"^[a-z]{2}$|^projet$", lg):
                raise Refus(400, "langue invalide")
            cible["langue"] = lg
        for champ in ("espece", "humour", "voix_haute"):
            if champ in e:
                if e[champ] not in PERMIS[champ]:
                    raise Refus(400, f"{champ} inconnu")
                cible[champ] = e[champ]
        if "frequence_rapport_min" in e:
            if e["frequence_rapport_min"] not in (15, 30, 60, 120):
                raise Refus(400, "fréquence : 15, 30, 60 ou 120")
            cible["frequence_rapport_min"] = e["frequence_rapport_min"]
        if "apparence" in e:
            cible["apparence"] = apparence(e["apparence"], dict(cible.get("apparence") or {}))
    if "voix" in d:
        v = d["voix"]
        if not isinstance(v, dict):
            raise Refus(400, "voix : objet attendu")
        cible = p.setdefault("voix", {})
        if "micro_actif" in v:
            cible["micro_actif"] = v["micro_actif"] is True
        if "langue_reconnaissance" in v:
            lr = texte(v, "langue_reconnaissance", 12)
            if not re.match(r"^[a-z]{2}(-[A-Z]{2})?$", lr):
                raise Refus(400, "langue_reconnaissance invalide")
            cible["langue_reconnaissance"] = lr
    p["maj"] = maintenant()
    ecrire_json(chemin, p)
    return {"ok": True, "profil": p}


def route_demande(d):
    cible = texte(d, "cible", 40, True).lower()
    if not CIBLE_RE.match(cible):
        raise Refus(400, "cible invalide")
    if cible != "assistant":
        if cible not in ids_postes():
            raise Refus(404, "poste inconnu")
    txt = texte(d, "texte", 2000, True)
    via = texte(d, "via", 10) or "ecrit"
    if via not in ("voix", "ecrit"):
        raise Refus(400, "via : voix ou ecrit")
    sujet = texte(d, "sujet", 20)
    if sujet not in ("", "optimisation"):
        raise Refus(400, "sujet : optimisation ou rien")
    cle = ("demande", cible, sujet, " ".join(txt.split()).lower())
    deja = doublon(cle)
    if deja:
        return dict(deja, doublon=True)
    dossier = os.path.join(Etat.studio, "demandes_vocales")
    if sujet == "optimisation":
        garde_optimisation(dossier)
    donnees = {"cible": cible, "texte": txt, "via": via, "cree_le": maintenant(), "statut": "nouvelle"}
    if sujet:
        donnees["sujet"] = sujet
    ident = creer_unique(dossier, cible, donnees)
    return doublon(cle, {"ok": True, "id": ident})


def garde_optimisation(dossier):
    """Une seule demande d'optimisation en attente, et au moins 30 min entre deux."""
    for f in sorted(os.listdir(dossier) if os.path.isdir(dossier) else [], reverse=True):
        d = lire_json(os.path.join(dossier, f), None) if f.endswith(".json") else None
        if not isinstance(d, dict) or d.get("sujet") != "optimisation":
            continue
        age = (time.time() - (iso_t(d.get("cree_le")) or os.path.getmtime(os.path.join(dossier, f)))) / 60
        if age < OPTIM_DELAI_MIN:
            raise Refus(429, f"optimisation déjà demandée il y a {int(age)} min (une toutes les {OPTIM_DELAI_MIN} min au plus)")
        if d.get("statut") in ("nouvelle", "prise") and age < 6 * 60:
            raise Refus(429, f"la demande d'optimisation d'il y a {int(age)} min attend encore sa réponse")
        return


def ids_postes():
    """Postes de la config et recrues."""
    conf = lire_json(os.path.join(Etat.studio, "studio.config.json"), {})
    ids = {p.get("id") for p in (conf.get("postes") or []) if isinstance(p, dict)}
    idx = lire_json(os.path.join(Etat.studio, "recrues", "index.json"), [])
    return ids | {x for x in (idx if isinstance(idx, list) else []) if isinstance(x, str)}


def dossier_agents(conf):
    """<dossier_agents> de la config s'il est DANS le projet, sinon <projet>/.claude/agents (jamais ailleurs)."""
    defaut = os.path.join(Etat.projet, ".claude", "agents")
    d = conf.get("dossier_agents")
    if isinstance(d, str) and d and "{{" not in d:
        p = os.path.realpath(d if os.path.isabs(d) else os.path.join(Etat.projet, d))
        racine = os.path.realpath(Etat.projet)
        if p == racine or p.startswith(racine + os.sep):
            return p
    return defaut


def yaml_chaine(s):
    """Contenu d'une chaîne YAML entre guillemets doubles."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


GABARIT_AGENT = """---
name: {{id}}
description: "{{role}}"
tools: {{outils}}
model: {{modele}}
---
<!-- studio-gamedev : recrue -->

Tu es **{{nom_affiche}}**, agent du studio {{nom_projet}} (poste : {{poste}}).

## Ton rôle
{{role}}

## Ta mission
{{mission}}

## Skills à appeler
{{skills}}

## Règles du projet
{{regles_agent}}

## Suivi dans le studio
Écris ton avancement dans `{{dossier_studio}}/progression/{{id}}.json` :
{"pct": 0 à 100, "texte": "ce que tu fais en une ligne"}
Mets-le à jour à chaque étape importante ; à la fin, `pct` 100.
"""


def definition_agent(conf, v):
    """Remplit modeles/agent.md (sinon le gabarit intégré) en un seul passage :
    des accolades doubles écrites par l'utilisateur ne sont jamais réinterprétées."""
    gab = None
    try:
        with open(os.path.join(os.path.dirname(ICI), "modeles", "agent.md"), encoding="utf-8-sig") as f:
            gab = f.read()
    except OSError:
        pass
    gab = gab or GABARIT_AGENT
    # règles de la config (qui peut venir d'un dépôt cloné) : 20 au plus, une ligne de 200 caractères chacune
    regles = [re.sub(r"\s+", " ", x).strip()[:200] for x in (conf.get("regles_agent") or []) if isinstance(x, str)]
    regles = [r.lstrip("#>-* ") for r in regles if r.strip("#>-* ")] or ["Écris dans la langue du projet, en phrases courtes."]
    eco = conf.get("economie") if isinstance(conf.get("economie"), dict) else {}
    modele = eco.get("modele_agents") if eco.get("modele_agents") in MODELES_AGENT else "sonnet"
    valeurs = {"id": v["nom"], "nom_affiche": v["nom_affiche"], "nom_projet": str(conf.get("nom_projet") or os.path.basename(Etat.projet)),
               "poste": v["poste"] or "nouveau bureau", "role": v["role"], "mission": v["mission"],
               "skills": "\n".join("- `" + s + "`" for s in v["skills"]) or "- `gamedev:router` s'il est installé (il choisit le bon skill)",
               "regles_agent": "\n".join("- " + r for r in regles[:20]), "dossier_studio": Etat.studio.replace("\\", "/"),
               "outils": OUTILS_AGENT, "modele": modele}
    entete_fin = gab.find("\n---", 3)
    if MARQUE_RECRUE not in gab and entete_fin > 0:   # gabarit sans marque : on l'ajoute après l'en-tête
        fin_ligne = gab.find("\n", entete_fin + 1)
        if fin_ligne > 0:
            gab = gab[:fin_ligne + 1] + MARQUE_RECRUE + "\n" + gab[fin_ligne + 1:]

    def remplacer(m):
        cle = m.group(1)
        if cle in ("role", "nom_affiche", "id") and m.start() < entete_fin:   # en-tête YAML : chaîne échappée
            return yaml_chaine(valeurs[cle])
        return valeurs.get(cle, m.group(0))
    return re.sub(r"\{\{([a-z_]+)\}\}", remplacer, gab)


def route_recruter(d):
    conf = lire_json(os.path.join(Etat.studio, "studio.config.json"), {})
    nom = texte(d, "nom", 40, True).lower()
    if not NOM_RE.match(nom) or nom in NOMS_RESERVES:
        raise Refus(400, "nom : 3 à 40 caractères parmi a-z, 0-9 et - (commence par une lettre ou un chiffre)")
    if nom in {p.get("id") for p in (conf.get("postes") or []) if isinstance(p, dict)}:
        raise Refus(409, f"« {nom} » est déjà un poste du studio : choisis un autre nom")
    affiche = texte(d, "nom_affiche", 40) or nom.replace("-", " ").capitalize()
    role = texte(d, "role", 200, True).replace("\n", " ")
    mission = texte(d, "mission", 4000, True)
    poste = texte(d, "poste", 80).replace("\n", " ")
    couleur = texte(d, "couleur", 7) or "#6b8f71"
    if not COULEUR_RE.match(couleur):
        raise Refus(400, "couleur : #rrggbb")
    apparence = texte(d, "apparence", 20) or "aucune"
    if apparence not in APPARENCES:
        raise Refus(400, "apparence inconnue")
    skills = d.get("skills") or []
    if isinstance(skills, str):
        skills = [x.strip() for x in re.split(r"[,\s]+", skills) if x.strip()]
    if not isinstance(skills, list) or len(skills) > 12 or not all(isinstance(x, str) and SKILL_RE.match(x) for x in skills):
        raise Refus(400, "skills : 12 noms au plus (ex. gamedev:godot-gdscript)")
    via = texte(d, "via", 10) or "ecrit"
    if via not in ("voix", "ecrit"):
        raise Refus(400, "via : voix ou ecrit")
    lancer, remplacer = d.get("lancer") is True, d.get("remplacer") is True
    auto = d.get("auto") is True
    if auto:
        garde_embauche_auto(conf, nom)
        lancer, remplacer = False, False
    agents = dossier_agents(conf)
    chemin_agent = os.path.join(agents, nom + ".md")
    if os.path.islink(chemin_agent) or (os.path.exists(chemin_agent) and not os.path.isfile(chemin_agent)):
        raise Refus(409, f"« {nom}.md » n'est pas un fichier ordinaire : rien n'est écrit")
    if os.path.exists(chemin_agent):
        if not remplacer:
            raise Refus(409, f"l'agent « {nom} » existe déjà (coche « remplacer » pour remplacer une recrue du studio)")
        try:
            with open(chemin_agent, encoding="utf-8-sig", errors="replace") as f:
                marque = MARQUE_RECRUE in f.read(4096)
        except OSError:
            marque = False
        if not marque or not os.path.isfile(os.path.join(Etat.studio, "recrues", nom + ".json")):
            raise Refus(409, f"l'agent « {nom} » n'a pas été recruté par le studio (écrit à la main ?) : il n'est jamais remplacé, choisis un autre nom")
    os.makedirs(agents, exist_ok=True)
    v = {"nom": nom, "nom_affiche": affiche, "role": role, "mission": mission, "poste": poste, "skills": skills}
    with open(chemin_agent + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        f.write(definition_agent(conf, v))
    os.replace(chemin_agent + ".tmp", chemin_agent)
    t = maintenant()
    fiche = dict(v, couleur=couleur, apparence=apparence, lancer=lancer, via=via, cree_le=t, origine="auto:embauche" if auto else "page",
                 agent=os.path.relpath(chemin_agent, Etat.projet).replace("\\", "/"))
    ecrire_json(os.path.join(Etat.studio, "recrues", nom + ".json"), fiche)
    idx_ch = os.path.join(Etat.studio, "recrues", "index.json")
    idx = lire_json(idx_ch, [])
    idx = [x for x in (idx if isinstance(idx, list) else []) if isinstance(x, str) and x != nom][-40:] + [nom]
    ecrire_json(idx_ch, idx)
    ident = creer_unique(os.path.join(Etat.studio, "demandes"), nom, dict(fiche, type="recrutement", statut="nouvelle"))
    return {"ok": True, "fiche": fiche, "demande": "demandes/" + ident + ".json", "agent": fiche["agent"]}


def nb_bureaux(conf):
    base = [p for p in (conf.get("postes") or []) if isinstance(p, dict) and p.get("id")][:9]
    ids = {p["id"] for p in base}
    idx = lire_json(os.path.join(Etat.studio, "recrues", "index.json"), [])
    return len(base) + len([x for x in (idx if isinstance(idx, list) else []) if isinstance(x, str) and x not in ids])


def garde_embauche_auto(conf, nom):
    """Embauche décidée par le studio : réglage activé, une par heure, 12 bureaux, jamais un ancien renvoyé."""
    if not reglage("embauche_auto"):
        raise Refus(403, "embauches automatiques coupées (Réglages ou economie.embauche_auto)")
    if nb_bureaux(conf) >= NB_BUREAUX:
        raise Refus(409, f"le studio a déjà {NB_BUREAUX} bureaux")
    if os.path.exists(os.path.join(Etat.studio, "recrues", "_anciens", nom + ".json")):
        raise Refus(409, f"« {nom} » a été renvoyé : seule une réembauche à la main le fait revenir")
    dossier = os.path.join(Etat.studio, "recrues")
    for f in (os.listdir(dossier) if os.path.isdir(dossier) else []):
        x = lire_json(os.path.join(dossier, f), None) if f.endswith(".json") else None
        if isinstance(x, dict) and x.get("origine") == "auto:embauche" and time.time() - iso_t(x.get("cree_le")) < EMBAUCHE_AUTO_DELAI_S:
            raise Refus(429, "une embauche automatique par heure au plus")


def demandes_du_poste(agent):
    """[(fichier, demande, statut)] des demandes de .studio/demandes/ adressées à ce poste."""
    dossier = os.path.join(Etat.studio, "demandes")
    statuts = lire_json(os.path.join(dossier, "statuts.json"), {})
    statuts = statuts if isinstance(statuts, dict) else {}
    out = []
    for f in sorted(os.listdir(dossier) if os.path.isdir(dossier) else []):
        if not f.endswith(".json") or f == "statuts.json":
            continue
        x = lire_json(os.path.join(dossier, f), None)
        if isinstance(x, dict) and (x.get("nom") or x.get("cible")) == agent:
            st = statuts.get(f) if isinstance(statuts.get(f), dict) else {}
            out.append((f, x, str(st.get("statut") or x.get("statut") or "nouvelle").lower()))
    return out


def court_titre(s):
    s = " ".join(s.split())
    return s if len(s) <= 120 else s[:119] + "…"


def route_confier(d):
    """Tâche confiée à un poste (fiche du personnage, fin de tâche) : une demande que Claude lit, rien n'est lancé."""
    agent = texte(d, "agent", 40, True).lower()
    if not CIBLE_RE.match(agent) or agent not in ids_postes():
        raise Refus(404, "poste inconnu")
    mission = texte(d, "mission", 4000, True)
    titre = texte(d, "titre", 200).replace("\n", " ")
    tache = texte(d, "tache_id", 80)
    if tache and not ID_RE.match(tache):
        raise Refus(400, "tache_id invalide")
    origine = texte(d, "origine", 100) or ("tache:" + tache if tache else "page")
    if not ORIGINE_RE.match(origine):
        raise Refus(400, "origine invalide")
    cle = ("confier", agent, origine, " ".join(mission.split()).lower())
    deja = doublon(cle)
    if deja:
        return dict(deja, doublon=True)
    if origine.startswith("auto:"):
        if not reglage("attribution_auto"):
            raise Refus(403, "attribution automatique coupée (Réglages ou economie.attribution_auto)")
        autos = [(x, st) for _, x, st in demandes_du_poste(agent) if str(x.get("origine", "")).startswith("auto:")]
        if sum(1 for _, st in autos if not st.startswith(FINIS)) >= AUTO_ATTENTE_MAX:
            raise Refus(429, f"« {agent} » a déjà une attribution automatique en attente")
        if sum(1 for x, _ in autos if time.time() - iso_t(x.get("cree_le")) < 3600) >= AUTO_PAR_HEURE:
            raise Refus(429, f"{AUTO_PAR_HEURE} attributions automatiques par heure au plus pour « {agent} »")
    donnees = {"nom": agent, "type": "tache", "titre": titre or court_titre(mission), "mission": mission, "origine": origine,
               "lancer": True, "statut": "nouvelle", "cree_le": maintenant()}
    if tache:
        donnees["tache_id"] = tache
    ident = creer_unique(os.path.join(Etat.studio, "demandes"), agent, donnees)
    return doublon(cle, {"ok": True, "demande": "demandes/" + ident + ".json", "agent": agent})


def recrue_occupee(nom):
    """Raison pour laquelle une recrue ne peut pas partir (tâche en cours), sinon None."""
    for f, _, st in demandes_du_poste(nom):
        if not st.startswith(FINIS):
            return f"demande {f} pas finie ({st})"
    ch = os.path.join(Etat.studio, "progression", nom + ".json")
    p = lire_json(ch, None)
    if isinstance(p, dict) and isinstance(p.get("pct"), (int, float)) and p["pct"] < 100 and time.time() - os.path.getmtime(ch) < 30 * 60:
        return f"travaille encore ({p['pct']} %)"
    return None


def index_noms(chemin, ajouter=None, retirer=None):
    idx = lire_json(chemin, [])
    idx = [x for x in (idx if isinstance(idx, list) else []) if isinstance(x, str) and x not in (ajouter, retirer)]
    if ajouter:
        idx.append(ajouter)
    ecrire_json(chemin, idx[-60:])


def route_renvoyer(d):
    """Renvoi d'une recrue (jamais un poste de la config) : rien n'est effacé. La fiche va dans recrues/_anciens/,
    la définition d'agent (seulement si elle porte la marque des recrues) dans .studio/anciens/agents/ : hors du
    dossier des agents, elle n'est plus chargée ; « réembaucher » remet tout en place."""
    conf = lire_json(os.path.join(Etat.studio, "studio.config.json"), {})
    nom = texte(d, "nom", 40, True).lower()
    if nom in {p.get("id") for p in (conf.get("postes") or []) if isinstance(p, dict)}:
        raise Refus(403, "les postes de base du studio ne se renvoient pas")
    fiche_ch = os.path.join(Etat.studio, "recrues", nom + ".json")
    if not NOM_RE.match(nom) or nom in NOMS_RESERVES or not os.path.isfile(fiche_ch):
        raise Refus(404, f"recrue « {nom} » inconnue")
    occupe = recrue_occupee(nom)
    if occupe:
        raise Refus(409, f"« {nom} » a une tâche en cours : {occupe}")
    fiche = lire_json(fiche_ch, {}) or {}
    fiche.update(renvoye_le=maintenant(), motif=texte(d, "motif", 200))
    ecrire_json(os.path.join(Etat.studio, "recrues", "_anciens", nom + ".json"), fiche)
    os.remove(fiche_ch)
    agent = os.path.join(dossier_agents(conf), nom + ".md")
    if os.path.isfile(agent) and not os.path.islink(agent):
        try:
            with open(agent, encoding="utf-8-sig", errors="replace") as f:
                marque = MARQUE_RECRUE in f.read(4096)
        except OSError:
            marque = False
        if marque:
            os.makedirs(os.path.join(Etat.studio, "anciens", "agents"), exist_ok=True)
            os.replace(agent, os.path.join(Etat.studio, "anciens", "agents", nom + ".md"))
    index_noms(os.path.join(Etat.studio, "recrues", "index.json"), retirer=nom)
    index_noms(os.path.join(Etat.studio, "recrues", "_anciens", "index.json"), ajouter=nom)
    return {"ok": True, "renvoye": nom}


def route_reembaucher(d):
    conf = lire_json(os.path.join(Etat.studio, "studio.config.json"), {})
    nom = texte(d, "nom", 40, True).lower()
    anc_f = os.path.join(Etat.studio, "recrues", "_anciens", nom + ".json")
    if not NOM_RE.match(nom) or not os.path.isfile(anc_f):
        raise Refus(404, f"ancien « {nom} » inconnu")
    agent = os.path.join(dossier_agents(conf), nom + ".md")
    if os.path.exists(os.path.join(Etat.studio, "recrues", nom + ".json")) or os.path.exists(agent):
        raise Refus(409, f"« {nom} » existe déjà dans l'équipe")
    if nb_bureaux(conf) >= NB_BUREAUX:
        raise Refus(409, f"le studio a déjà {NB_BUREAUX} bureaux")
    fiche = lire_json(anc_f, {}) or {}
    fiche.pop("renvoye_le", None)
    fiche.update(reembauche_le=maintenant(), lancer=False)
    ecrire_json(os.path.join(Etat.studio, "recrues", nom + ".json"), fiche)
    os.remove(anc_f)
    anc_a = os.path.join(Etat.studio, "anciens", "agents", nom + ".md")
    if os.path.isfile(anc_a):
        os.makedirs(os.path.dirname(agent), exist_ok=True)
        os.replace(anc_a, agent)
    index_noms(os.path.join(Etat.studio, "recrues", "index.json"), ajouter=nom)
    index_noms(os.path.join(Etat.studio, "recrues", "_anciens", "index.json"), retirer=nom)
    return {"ok": True, "reembauche": nom, "fiche": fiche}


def route_repondre(d):
    id_ = texte(d, "id", 80, True)
    if not ID_RE.match(id_):
        raise Refus(400, "id invalide")
    choix = texte(d, "choix", 80)
    libre = texte(d, "texte_libre", 2000)
    if not choix and not libre:
        raise Refus(400, "choisir une option ou écrire une réponse")
    chemin = os.path.join(Etat.studio, "reponses.json")
    reponses = lire_json(chemin, None) if os.path.exists(chemin) else []
    if not isinstance(reponses, list):
        raise Refus(503, "reponses.json illisible : rien n'est écrit (répare-le ou renomme-le)")
    reponses = [r for r in reponses if not (isinstance(r, dict) and r.get("id") == id_)]
    r = {"id": id_, "choix": choix, "texte_libre": libre, "repondu_le": maintenant()}
    reponses.append(r)
    ecrire_json(chemin, reponses[-300:])
    return {"ok": True, "reponse": r}


def route_reglages(d):
    f = d.get("frequence_rapport_min")
    bascules = {k: d[k] for k in ("attribution_auto", "embauche_auto") if k in d}
    if any(not isinstance(v, bool) for v in bascules.values()):
        raise Refus(400, "réglage marche / arrêt : true ou false")
    if f is None and not bascules:
        raise Refus(400, "aucun réglage")
    if f is not None and f not in (15, 30, 60, 120):
        raise Refus(400, "fréquence : 15, 30, 60 ou 120")
    chemin = os.path.join(Etat.studio, "reglages.json")
    r = lire_json(chemin, {})
    if not isinstance(r, dict):
        r = {}
    if f is not None:
        r["frequence_rapport_min"] = f
    r.update(bascules, maj=maintenant())
    ecrire_json(chemin, r)
    return {"ok": True, "reglages": r}


# -------------------------------------------------------------------- transcription locale (facultative)
_MODELE, _VERROU_MODELE = None, threading.Lock()


def transcrire(audio):
    """Transcription locale avec faster-whisper si installé (pip install faster-whisper). Sinon 501."""
    try:
        from faster_whisper import WhisperModel  # noqa: import facultatif
    except ImportError:
        raise Refus(501, "transcription locale absente : installe faster-whisper (pip install faster-whisper) "
                         "ou utilise un navigateur avec reconnaissance vocale ; tu peux toujours écrire ta réponse")
    profil = lire_json(os.path.join(Etat.studio, "profil.json"), {})
    langue = str(((profil.get("voix") or {}).get("langue_reconnaissance") or "fr"))[:2]
    t0 = time.time()
    signal, decodeur, erreurs = decoder(audio)
    if signal is None:
        raise Refus(422, "audio illisible (" + " ; ".join(erreurs)[:300] + ")")
    t_decodage = time.time() - t0
    m = modele(WhisperModel)
    t1 = time.time()
    try:
        txt = _transcrire_avec(m, signal, langue)
    except RuntimeError as e:
        # bibliothèques CUDA absentes au moment du calcul : on repasse sur le processeur
        if not any(x in str(e).lower() for x in ("cuda", "cublas", "cudnn")):
            raise
        m = modele(WhisperModel, forcer_cpu=True)
        txt = _transcrire_avec(m, signal, langue)
    return {"ok": True, "texte": txt[:4000], "decodeur": decodeur, "decodage_s": round(t_decodage, 2),
            "duree_s": round(time.time() - t1, 2), "audio_s": round(len(signal) / 16000, 1), **_INFOS}


_INFOS = {}


def _transcrire_avec(m, signal, langue):
    segments, _ = m.transcribe(signal, language=langue, beam_size=1, vad_filter=True, condition_on_previous_text=False)
    return " ".join(s.text.strip() for s in segments).strip()


def _dll_cuda():
    """Rend visibles les DLL CUDA installées par pip (nvidia-cublas-cu12, nvidia-cudnn-cu12), sous Windows."""
    try:
        import glob
        import nvidia
        for d in glob.glob(os.path.join(list(nvidia.__path__)[0], "*", "bin")):
            os.add_dll_directory(d)
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
    except Exception:
        pass


def modele(WhisperModel, forcer_cpu=False):
    """Modèle chargé une seule fois : GPU (float16) si possible, sinon processeur (int8)."""
    global _MODELE
    with _VERROU_MODELE:
        if _MODELE is None or forcer_cpu:
            nom = os.environ.get("STUDIO_WHISPER", "small")
            racine = os.environ.get("STUDIO_WHISPER_DIR") or None
            t0 = time.time()
            if not forcer_cpu:
                _dll_cuda()
                try:
                    _MODELE = WhisperModel(nom, device="cuda", compute_type="float16", download_root=racine)
                    _INFOS.update(appareil="cuda")
                except Exception as e:
                    _MODELE = None
                    _INFOS.update(raison_cpu=str(e)[:160])
            if _MODELE is None or forcer_cpu:
                _MODELE = WhisperModel(nom, device="cpu", compute_type="int8", download_root=racine)
                _INFOS.update(appareil="cpu")
            _INFOS.update(modele=nom, chargement_s=round(time.time() - t0, 1))
        return _MODELE


def decoder(audio):
    """Audio brut (webm/opus, ogg, wav…) → signal 16 kHz mono float32.
    1) ffmpeg en ligne de commande s'il est dans le PATH ; 2) PyAV ; 3) le décodeur de faster-whisper.
    Renvoie (signal ou None, nom du décodeur, erreurs rencontrées). Aucune entrée de la page n'entre dans une commande."""
    import shutil
    import numpy as np
    erreurs = []
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        import subprocess
        try:
            r = subprocess.run([ffmpeg, "-nostdin", "-loglevel", "error", "-i", "pipe:0", "-f", "f32le", "-ac", "1", "-ar", "16000", "pipe:1"],
                               input=audio, capture_output=True, timeout=60, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if r.returncode == 0 and r.stdout:
                return np.frombuffer(r.stdout, dtype=np.float32), "ffmpeg", erreurs
            erreurs.append("ffmpeg : " + r.stderr.decode("utf-8", "replace").strip()[:120])
        except Exception as e:
            erreurs.append("ffmpeg : " + str(e)[:120])
    else:
        erreurs.append("ffmpeg absent du PATH")
    try:
        import io
        import av
        morceaux = []
        with av.open(io.BytesIO(audio), mode="r") as conteneur:
            reech = av.AudioResampler(format="flt", layout="mono", rate=16000)
            for trame in conteneur.decode(audio=0):
                for t in (reech.resample(trame) or []):
                    morceaux.append(t.to_ndarray().reshape(-1))
            for t in (reech.resample(None) or []):
                morceaux.append(t.to_ndarray().reshape(-1))
        if morceaux:
            return np.concatenate(morceaux).astype(np.float32), "pyav", erreurs
        erreurs.append("pyav : aucun son")
    except Exception as e:
        erreurs.append("pyav : " + str(e)[:120])
    try:
        from faster_whisper.audio import decode_audio
        fd, tmp = tempfile.mkstemp(suffix=".webm")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(audio)
            return decode_audio(tmp, sampling_rate=16000), "faster-whisper", erreurs
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
    except Exception as e:
        erreurs.append("faster-whisper : " + str(e)[:120])
    return None, "", erreurs


# -------------------------------------------------------------------- lancement
def port_libre(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def main(argv=None):
    ap = argparse.ArgumentParser(description="Serveur local du studio gamedev (127.0.0.1 seulement).")
    ap.add_argument("--projet", required=True, help="dossier du projet (le studio lit et écrit dans <projet>/.studio)")
    ap.add_argument("--port", type=int, default=0, help=f"port local (défaut : studio.config.json, sinon {PORT_DEFAUT} ; s'il est pris, le premier libre après)")
    a = ap.parse_args(argv)
    Etat.projet = os.path.abspath(a.projet)
    Etat.studio = os.path.join(Etat.projet, ".studio")
    os.makedirs(Etat.studio, exist_ok=True)
    conf = lire_json(os.path.join(Etat.studio, "studio.config.json"), {})
    try:
        port = int(conf.get("port") or PORT_DEFAUT)
    except (TypeError, ValueError):
        port = PORT_DEFAUT
    if not 1024 <= port <= 65000:
        port = PORT_DEFAUT
    if a.port:
        port = a.port
    else:
        libre = next((p for p in range(port, port + 50) if port_libre(p)), 0)
        if not libre:
            raise SystemExit(f"aucun port libre entre {port} et {port + 49} : relance avec --port N")
        port = libre
    srv = ThreadingHTTPServer(("127.0.0.1", port), Studio)
    srv.daemon_threads = True
    print(f"studio sur http://127.0.0.1:{port}/studio.html (projet : {Etat.projet})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
