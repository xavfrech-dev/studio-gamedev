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
  /api/reglages       {frequence_rapport_min}                      -> .studio/reglages.json
  /api/recruter       {nom, nom_affiche?, role, mission, poste?, couleur?, apparence?, skills?, lancer?, remplacer?, via?}
                      -> <dossier_agents>/<nom>.md (définition d'agent, dans le projet seulement),
                         .studio/recrues/<nom>.json (+ recrues/index.json), .studio/demandes/<horodatage>_<nom>.json
  /api/transcrire     audio brut (webm/ogg/wav, 8 Mo au plus)      -> {"ok", "texte"} ; 501 si faster-whisper absent

Sécurité : écoute 127.0.0.1 seulement ; en-têtes Host et Origin vérifiés (page du même serveur) ;
corps JSON ≤ 64 Ko ; champs bornés ; écriture seulement dans les fichiers ci-dessus ; aucune commande exécutée.
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
VIAS = {"clic", "ecrit", "voix", "passer"}
ETATS = {"en_cours", "termine"}
MODES = {"rapide", "complet"}

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
                      "/api/recruter": route_recruter}.get(route)
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
    dossier = os.path.join(Etat.studio, "demandes_vocales")
    ident = time.strftime("%Y%m%d-%H%M%S") + f"-{int(time.time() * 1000) % 1000:03d}_{cible}"
    ecrire_json(os.path.join(dossier, ident + ".json"),
                {"id": ident, "cible": cible, "texte": txt, "via": via, "cree_le": maintenant(), "statut": "nouvelle"})
    return {"ok": True, "id": ident}


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
    fiche = dict(v, couleur=couleur, apparence=apparence, lancer=lancer, via=via, cree_le=t,
                 agent=os.path.relpath(chemin_agent, Etat.projet).replace("\\", "/"))
    ecrire_json(os.path.join(Etat.studio, "recrues", nom + ".json"), fiche)
    idx_ch = os.path.join(Etat.studio, "recrues", "index.json")
    idx = lire_json(idx_ch, [])
    idx = [x for x in (idx if isinstance(idx, list) else []) if isinstance(x, str) and x != nom][-40:] + [nom]
    ecrire_json(idx_ch, idx)
    ident = time.strftime("%Y%m%d-%H%M%S") + f"-{int(time.time() * 1000) % 1000:03d}_{nom}"
    ecrire_json(os.path.join(Etat.studio, "demandes", ident + ".json"), dict(fiche, id=ident, type="recrutement", statut="nouvelle"))
    return {"ok": True, "fiche": fiche, "demande": "demandes/" + ident + ".json", "agent": fiche["agent"]}


def route_repondre(d):
    id_ = texte(d, "id", 80, True)
    if not ID_RE.match(id_):
        raise Refus(400, "id invalide")
    choix = texte(d, "choix", 80)
    libre = texte(d, "texte_libre", 2000)
    if not choix and not libre:
        raise Refus(400, "choisir une option ou écrire une réponse")
    chemin = os.path.join(Etat.studio, "reponses.json")
    reponses = lire_json(chemin, [])
    if not isinstance(reponses, list):
        reponses = []
    reponses = [r for r in reponses if not (isinstance(r, dict) and r.get("id") == id_)]
    r = {"id": id_, "choix": choix, "texte_libre": libre, "repondu_le": maintenant()}
    reponses.append(r)
    ecrire_json(chemin, reponses[-300:])
    return {"ok": True, "reponse": r}


def route_reglages(d):
    f = d.get("frequence_rapport_min")
    if f not in (15, 30, 60, 120):
        raise Refus(400, "fréquence : 15, 30, 60 ou 120")
    chemin = os.path.join(Etat.studio, "reglages.json")
    r = lire_json(chemin, {})
    if not isinstance(r, dict):
        r = {}
    r.update(frequence_rapport_min=f, maj=maintenant())
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
