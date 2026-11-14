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
  /api/demande        {cible, texte, via, sujet?, en_reponse_a?, brouillon?, perimetre?}  -> .studio/demandes_vocales/<horodatage>_<cible>.json
                      cible : assistant, un poste, controleur-modeles (« Le bon modèle pour chacun ») ou auditeur (si activé) ;
                      brouillon : pièces jointes rangées dans demandes_vocales/pieces/<id du message>/, chemins absolus listés
  /api/piece          corps brut, ?brouillon=<id>&nom=<fichier>    -> demandes_vocales/pieces/_brouillons/<id>/ (20 Mo, 10 fichiers, 60 Mo, types limités)
  /api/piece_retirer  {brouillon, nom}                             -> retire une pièce du brouillon
  /api/modele         {id, modele?, effort?, raison?, par?, demande?} -> frontmatter model:/effort: de <dossier_agents>/<id>.md s'il existe,
                      fiche du studio (recrues/<id>.json ou reglages.json) et .studio/modeles_journal.json
  GET /api/modeles                                                 -> modèle et effort de chaque agent, journal des changements
  /api/repondre       {id, choix?, texte_libre?}                   -> .studio/reponses.json (décision ou question de suivi)
  /api/cloche         {action: reporter|confier|remettre, cle}     -> .studio/cloche_memo.json (« plus tard » 24 h et « confié », communs au PC et au téléphone)
  /api/reglages       {frequence_rapport_min?, attribution_auto?, embauche_auto?, auditeur?, controle_modeles?}  -> .studio/reglages.json
  /api/confier        {agent, mission, titre?, tache_id?, origine?}  -> .studio/demandes/<horodatage>_<agent>.json (tâche confiée)
  /api/renvoyer       {nom, motif?}                                -> recrue archivée : .studio/recrues/_anciens/, .studio/anciens/agents/
  /api/reembaucher    {nom}                                        -> remet une recrue archivée dans l'équipe (lancer: false)
  /api/recruter       {nom, nom_affiche?, role, mission, poste?, couleur?, apparence?, skills?, lancer?, remplacer?, via?}
                      -> <dossier_agents>/<nom>.md (définition d'agent, dans le projet seulement),
                         .studio/recrues/<nom>.json (+ recrues/index.json), .studio/demandes/<horodatage>_<nom>.json
  /api/sante          {action: activer_temperatures|desinstaller_temperatures (via: clic, depuis le PC)|analyser_menage}
                      -> .studio/sante/ (températures : élévation demandée à Windows sur ce clic seulement)
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
from urllib.parse import parse_qs, unquote, urlsplit
for _flux in (sys.stdout, sys.stderr):                 # S6 : sortie en UTF-8, même redirigée (Windows)
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ICI = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True   # jamais de __pycache__ dans le dossier du skill
PORT_DEFAUT = 8790
MARQUE_RECRUE = "<!-- studio-gamedev : recrue -->"
OUTILS_AGENT = "Read, Grep, Glob, Edit, Write, Bash, Skill"
MODELES_AGENT = {"haiku", "sonnet", "opus", "fable", "inherit"}
EFFORTS = {"low", "medium", "high", "xhigh", "max"}
PAR_MODELE = {"utilisateur", "controleur-modeles", "optimisation", "auditeur", "assistant"}
CIBLES_SPECIALES = {"controleur-modeles", "auditeur"}           # demandes traitées par Claude avec une consigne (pas des postes)
PERIMETRES = ("projet", "studio", "version", "session")
PIECE_MAX = 20 * 1024 * 1024                                     # pièces jointes : 20 Mo par fichier
PIECES_MAX_N, PIECES_MAX_TOTAL = 10, 60 * 1024 * 1024            # 10 fichiers et 60 Mo par message
PIECES_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".heic", ".pdf", ".txt", ".md", ".json", ".log", ".csv",
              ".yaml", ".yml", ".ini", ".xml", ".zip", ".glb", ".gltf", ".fbx", ".obj", ".mp3", ".wav", ".ogg", ".m4a", ".mp4", ".webm", ".mov"}
BROUILLON_RE = re.compile(r"^[a-z0-9]{8,40}$")
MAX_CORPS = 64 * 1024
MAX_AUDIO = 8 * 1024 * 1024
VERROU = threading.Lock()

EXTENSIONS = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
              ".json": "application/json; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
              ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif", ".ogg": "audio/ogg", ".mp3": "audio/mpeg",
              ".wav": "audio/wav", ".woff2": "font/woff2", ".woff": "font/woff", ".otf": "font/otf", ".webmanifest": "application/manifest+json", ".ttf": "font/ttf", ".txt": "text/plain; charset=utf-8", ".md": "text/plain; charset=utf-8"}

# pièces jointes servies au fil (demandes_vocales/pieces/<id>/) : les types que EXTENSIONS ne sert pas ; texte brut pour ce qui
# s'affiche (jamais interprété : XML et journaux en text/plain), téléchargement pour le reste (Content-Disposition: attachment)
TYPES_PIECES = {".pdf": "application/pdf", ".bmp": "image/bmp", ".heic": "image/heic", ".log": "text/plain; charset=utf-8",
                ".csv": "text/plain; charset=utf-8", ".yaml": "text/plain; charset=utf-8", ".yml": "text/plain; charset=utf-8",
                ".ini": "text/plain; charset=utf-8", ".xml": "text/plain; charset=utf-8", ".m4a": "audio/mp4", ".mp4": "video/mp4",
                ".webm": "video/webm", ".mov": "video/quicktime", ".zip": "application/octet-stream", ".glb": "application/octet-stream",
                ".gltf": "application/octet-stream", ".fbx": "application/octet-stream", ".obj": "application/octet-stream"}

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
ORIGINE_RE = re.compile(r"^(page|tache:[A-Za-z0-9_.:-]{1,80}|auto:fin-de-tache|auto:temporaire)$")
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
    for essai in range(5):                       # Windows : la page ou un agent peut tenir le fichier un court instant
        try:
            os.replace(tmp, chemin)
            return
        except PermissionError:
            time.sleep(0.1 * (essai + 1))
    try:
        os.replace(tmp, chemin)
    except PermissionError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise Refus(503, f"fichier occupé ({os.path.basename(chemin)}), réessaie dans un instant")


MIS_DE_COTE = []          # fichiers illisibles mis de côté depuis le démarrage (montrés par /api/qui)


def lire_ou_mettre_de_cote(chemin, defaut):
    """Pour une route qui va réécrire le fichier : absent → « defaut » ; illisible → 3 nouvelles lectures (une écriture est
    peut-être en cours) ; toujours illisible → copie <nom>.corrompu-<date>.json, rien n'est écrit (503) et la page le dit."""
    if not os.path.exists(chemin):
        return defaut
    erreur = None
    for essai in range(4):
        try:
            with open(chemin, encoding="utf-8-sig") as f:
                return json.load(f)
        except FileNotFoundError:
            return defaut
        except Exception as e:
            erreur = e
            time.sleep(.15 * (essai + 1))
    base, ext = os.path.splitext(chemin)
    cible = f"{base}.corrompu-{time.strftime('%Y%m%d-%H%M%S')}{ext}"
    try:
        if not any(x.get("fichier") == os.path.basename(chemin) and time.time() - x.get("t", 0) < 600 for x in MIS_DE_COTE):
            import shutil
            shutil.copyfile(chemin, cible)
            MIS_DE_COTE.append({"fichier": os.path.basename(chemin), "copie": os.path.basename(cible), "quand": maintenant(), "t": time.time()})
    except OSError:
        pass
    raise Refus(503, f"{os.path.basename(chemin)} est illisible ({type(erreur).__name__}) : rien n'est écrit pour ne rien perdre. "
                     f"Une copie est gardée ({os.path.basename(cible)}) ; demande à l'assistant de le réparer.")


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
    port = 0


def creer_unique(dossier, suffixe, donnees, preparer=None, annuler=None):
    """Fichier au nom unique (horodatage, millisecondes + code au hasard), créé en mode exclusif : jamais d'écrasement.
    preparer(ident, contenu) -> contenu : appelé AVANT l'écriture (pièces jointes rangées), pour que la demande soit écrite une
    seule fois et complète ; annuler(ident) défait ce que preparer a fait si l'écriture échoue. Écrit d'abord sous un nom
    caché (.<id>.tmp, jamais lu comme une demande), puis renommé : un lecteur ne voit jamais une demande à moitié écrite."""
    os.makedirs(dossier, exist_ok=True)
    for _ in range(20):
        t = time.time()
        ident = time.strftime("%Y%m%d-%H%M%S", time.localtime(t)) + f"-{int(t * 1000) % 1000:03d}{os.urandom(2).hex()}_{suffixe}"
        chemin = os.path.join(dossier, ident + ".json")
        if os.path.exists(chemin):
            continue
        contenu = dict(donnees, id=ident)
        if preparer:
            contenu = preparer(ident, contenu)
        tmp = os.path.join(dossier, "." + ident + ".tmp")
        try:
            with open(tmp, "x", encoding="utf-8") as f:
                json.dump(contenu, f, ensure_ascii=False, indent=1)
            if os.path.exists(chemin):
                raise FileExistsError(chemin)
            os.rename(tmp, chemin)                       # Windows : FileExistsError si le nom existe déjà (jamais d'écrasement)
            return ident
        except FileExistsError:
            for x in (tmp,):
                try:
                    os.remove(x)
                except OSError:
                    pass
            if annuler:
                annuler(ident)
            continue
        except BaseException:
            try:
                os.remove(tmp)
            except OSError:
                pass
            if annuler:
                annuler(ident)
            raise
    raise Refus(503, "impossible de créer la demande")


# -------------------------------------------------------------------- pièces jointes de la conversation
def dossier_pieces():
    return os.path.join(Etat.studio, "demandes_vocales", "pieces")


def nom_piece(brut):
    """Nom de fichier nettoyé : sans dossier, lettres sans accents, chiffres, « . _ - » ; 80 caractères au plus ; extension permise."""
    import unicodedata
    n = str(brut or "").replace("\\", "/").split("/")[-1].strip()
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode("ascii")
    n = re.sub(r"[^A-Za-z0-9._-]+", "_", n).strip("._-") or "piece"
    base, ext = os.path.splitext(n)
    ext = ext.lower()
    if ext not in PIECES_EXT:
        raise Refus(415, "type de fichier refusé (images, PDF, texte, JSON, ZIP, 3D, son ou vidéo)")
    base = base.strip("._-")[:70] or "piece"
    if base.upper() in {"CON", "PRN", "AUX", "NUL"} or re.fullmatch(r"(?i)(COM|LPT)\d", base):
        base = "_" + base
    return base + ext


def signature_ok(ext, debut):
    """Contrôle léger : les premiers octets doivent correspondre au format annoncé (images, PDF, ZIP, GLB).
    Ce n'est pas une analyse complète ; texte, son, vidéo et 3D texte ne sont contrôlés que par l'extension."""
    if ext == ".webp":
        return debut[:4] == b"RIFF" and debut[8:12] == b"WEBP"
    if ext == ".heic":
        return debut[4:8] == b"ftyp" and debut[8:12] in (b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1")
    sig = {".png": [b"\x89PNG\r\n\x1a\n"], ".jpg": [b"\xff\xd8\xff"], ".jpeg": [b"\xff\xd8\xff"], ".gif": [b"GIF87a", b"GIF89a"],
           ".pdf": [b"%PDF-"], ".zip": [b"PK\x03\x04", b"PK\x05\x06"], ".glb": [b"glTF"], ".bmp": [b"BM"]}.get(ext)
    return sig is None or any(debut.startswith(s) for s in sig)


_VERROUS_B = {}                  # brouillon -> [verrou, nombre de fils qui le tiennent ou l'attendent]
_VERROUS_B_GARDE = threading.Lock()
_RESERVES = {}                   # brouillon -> {chemin du .part: taille annoncée} : le quota compte ce qui arrive, pas 0 octet
PART_ABANDON_S = 120             # un .part qu'aucun fil ne tient (serveur redémarré) et vieux de 2 min : effacé


class verrou_brouillon:
    """Verrou court propre à un brouillon (quotas, choix du nom) : n'arrête jamais les autres routes. Compté : retiré de la
    table quand plus aucun fil ne le tient ni ne l'attend (jamais deux verrous pour un même brouillon)."""

    def __init__(self, b):
        self.b = b

    def __enter__(self):
        with _VERROUS_B_GARDE:
            e = _VERROUS_B.setdefault(self.b, [threading.Lock(), 0])
            e[1] += 1
        self.e = e
        e[0].acquire()
        return self

    def __exit__(self, *exc):
        self.e[0].release()
        with _VERROUS_B_GARDE:
            self.e[1] -= 1
            if self.e[1] <= 0 and _VERROUS_B.get(self.b) is self.e:
                del _VERROUS_B[self.b]
        return False


def parts_vivants(dossier, b):
    """.part en cours du brouillon (sous son verrou) ; un .part orphelin de plus de 2 min est effacé."""
    vivants, tenus = [], _RESERVES.get(b, {})
    for f in os.listdir(dossier):
        if not f.endswith(".part"):
            continue
        c = os.path.join(dossier, f)
        if c in tenus:
            vivants.append(c)
            continue
        try:
            if time.time() - os.path.getmtime(c) > PART_ABANDON_S:
                os.remove(c)
            else:
                vivants.append(c)
        except OSError:
            pass
    return vivants


def nettoyer_brouillons():
    """Brouillons de pièces jointes abandonnés (plus de 24 h) : effacés."""
    racine = os.path.join(dossier_pieces(), "_brouillons")
    if not os.path.isdir(racine):
        return
    import shutil
    for b in os.listdir(racine):
        d = os.path.join(racine, b)
        try:
            if os.path.isdir(d) and time.time() - os.path.getmtime(d) > 24 * 3600:
                shutil.rmtree(d, ignore_errors=True)
        except OSError:
            pass


def menage_brouillons_fond():
    """Fil de fond : ménage des brouillons au démarrage puis toutes les heures."""
    while True:
        try:
            nettoyer_brouillons()
        except Exception as e:
            sys.stderr.write(f"ménage des brouillons : {e}\n")
        time.sleep(3600)


def route_piece_retirer(d):
    b, nom = texte(d, "brouillon", 40, True), texte(d, "nom", 90, True)
    if not BROUILLON_RE.match(b) or nom != os.path.basename(nom) or nom.startswith(".") or "\\" in nom or "/" in nom:
        raise Refus(400, "pièce invalide")
    c = os.path.join(dossier_pieces(), "_brouillons", b, nom)
    if os.path.isfile(c):
        os.remove(c)
    return {"ok": True, "retire": nom}


# -------------------------------------------------------------------- modèles des agents (onglet « Modèles »)
def frontmatter(chemin):
    """(model, effort) lus dans l'en-tête YAML d'une définition d'agent ; None si absents."""
    try:
        with open(chemin, encoding="utf-8-sig") as f:
            s = f.read().replace("\r\n", "\n")
    except OSError:
        return None, None
    if not s.startswith("---\n"):
        return None, None
    fm = s[4:].split("\n---", 1)[0]
    m = re.search(r"(?m)^model:\s*([A-Za-z0-9_.\[\]-]+)\s*$", fm)
    e = re.search(r"(?m)^effort:\s*([A-Za-z]+)\s*$", fm)
    return (m.group(1) if m else None), (e.group(1) if e else None)


def ecrire_frontmatter(chemin, modele, effort):
    """Écrit model: et effort: dans l'en-tête d'une définition d'agent (le reste ne bouge pas, fins de ligne gardées).
    effort "" : ligne retirée (effort par défaut)."""
    with open(chemin, encoding="utf-8-sig", newline="") as f:
        brut = f.read()
    crlf = "\r\n" in brut
    s = brut.replace("\r\n", "\n")
    if not s.startswith("---\n") or "\n---" not in s[3:]:
        raise Refus(409, f"{os.path.basename(chemin)} : en-tête YAML introuvable, rien n'est écrit")
    fin = s.index("\n---", 3)
    lignes, reste = s[4:fin].split("\n"), s[fin:]

    def poser(cle, valeur):
        i = next((k for k, l in enumerate(lignes) if re.match(rf"^{cle}:", l)), None)
        if valeur:
            if i is None:
                j = next((k for k, l in enumerate(lignes) if l.startswith("model:")), None)
                if j is None:
                    j = next((k for k, l in enumerate(lignes) if l.startswith("description:")), len(lignes) - 1)
                lignes.insert(j + 1, f"{cle}: {valeur}")
            else:
                lignes[i] = f"{cle}: {valeur}"
        elif i is not None:
            del lignes[i]
    if modele:
        poser("model", modele)
    if effort is not None:
        poser("effort", effort)
    sortie = "---\n" + "\n".join(lignes) + reste
    with open(chemin + ".tmp", "w", encoding="utf-8", newline="") as f:
        f.write(sortie.replace("\n", "\r\n") if crlf else sortie)
    os.replace(chemin + ".tmp", chemin)


def journal_modeles():
    return os.path.join(Etat.studio, "modeles_journal.json")


def lire_modeles():
    """Modèle et effort de chaque agent : définitions d'agents du projet (ce que lit Claude Code), recrues, réglages des postes ; journal."""
    conf = lire_json(os.path.join(Etat.studio, "studio.config.json"), {}) or {}
    agents = dossier_agents(conf)
    fiches = {}
    if os.path.isdir(agents):
        for f in sorted(os.listdir(agents)):
            c = os.path.join(agents, f)
            if f.endswith(".md") and os.path.isfile(c) and not os.path.islink(c):
                m, e = frontmatter(c)
                fiches[f[:-3]] = {"modele": m, "effort": e, "chemin": c}
    recrues = {}
    dos = os.path.join(Etat.studio, "recrues")
    for f in (sorted(os.listdir(dos)) if os.path.isdir(dos) else []):
        if f.endswith(".json") and f != "index.json":
            x = lire_json(os.path.join(dos, f), {}) or {}
            if isinstance(x, dict) and x.get("nom"):
                recrues[x["nom"]] = {"modele": x.get("modele"), "effort": x.get("effort")}
    r = lire_json(os.path.join(Etat.studio, "reglages.json"), {}) or {}
    journal = lire_json(journal_modeles(), []) or []
    eco = conf.get("economie") if isinstance(conf.get("economie"), dict) else {}
    return {"ok": True, "fiches": fiches, "recrues": recrues,
            "postes": {"modeles": r.get("modeles_postes") or {}, "efforts": r.get("efforts_postes") or {}},
            "defaut": eco.get("modele_agents") if eco.get("modele_agents") in MODELES_AGENT else "sonnet",
            "journal": journal[-200:] if isinstance(journal, list) else [], "controle_modeles": controle_modeles_actif(r)}


def route_modele(d):
    """Modèle et/ou effort d'un agent : frontmatter de <dossier_agents>/<id>.md s'il existe, fiche du studio
    (recrues/<id>.json, ou reglages.json pour un poste de la config et l'auditeur) et une ligne au journal.
    Vaut pour la prochaine tâche de l'agent (une tâche en cours garde son modèle)."""
    conf = lire_json(os.path.join(Etat.studio, "studio.config.json"), {}) or {}
    nom = texte(d, "id", 40, True).lower()
    if not CIBLE_RE.match(nom):
        raise Refus(400, "id invalide")
    modele = texte(d, "modele", 10)
    if modele and modele not in MODELES_AGENT:
        raise Refus(400, "modèle : haiku, sonnet, opus, fable ou inherit")
    effort = d.get("effort")
    if effort is not None:
        effort = texte(d, "effort", 10)
        if effort and effort not in EFFORTS:
            raise Refus(400, "effort : low, medium, high, xhigh ou max")
    if not modele and effort is None:
        raise Refus(400, "rien à changer")
    raison = texte(d, "raison", 300).replace("\n", " ")
    par = texte(d, "par", 30) or "utilisateur"
    if par not in PAR_MODELE:
        raise Refus(400, "par : " + ", ".join(sorted(PAR_MODELE)))
    dem = texte(d, "demande", 120)
    if dem and not re.match(r"^[A-Za-z0-9_.:+-]{1,120}$", dem):
        raise Refus(400, "demande invalide")
    base = {p.get("id") for p in (conf.get("postes") or []) if isinstance(p, dict)}
    fiche_p = os.path.join(Etat.studio, "recrues", nom + ".json")
    recrue = os.path.isfile(fiche_p)
    if not recrue and nom not in base and nom != "auditeur":
        raise Refus(404, f"agent « {nom} » inconnu")
    md = os.path.join(dossier_agents(conf), nom + ".md")
    a_md = os.path.isfile(md) and not os.path.islink(md)
    chemin_r = os.path.join(Etat.studio, "reglages.json")
    r = lire_ou_mettre_de_cote(chemin_r, {}) or {}
    av_m, av_e = frontmatter(md) if a_md else (None, None)
    fiche = (lire_json(fiche_p, {}) or {}) if recrue else None
    if recrue:
        av_m, av_e = av_m or fiche.get("modele"), av_e or fiche.get("effort")
    else:
        av_m = av_m or (r.get("modeles_postes") or {}).get(nom)
        av_e = av_e or (r.get("efforts_postes") or {}).get(nom)
    eco = conf.get("economie") if isinstance(conf.get("economie"), dict) else {}
    av_m = av_m or (eco.get("modele_agents") if eco.get("modele_agents") in MODELES_AGENT else "sonnet")   # comme la fiche de l'agent
    if a_md:
        ecrire_frontmatter(md, modele, effort)
    if recrue:
        if modele:
            fiche["modele"] = modele
        if effort is not None:
            if effort:
                fiche["effort"] = effort
            else:
                fiche.pop("effort", None)
        fiche["modifie_le"] = maintenant()
        ecrire_json(fiche_p, fiche)
    else:
        if modele:
            r.setdefault("modeles_postes", {})[nom] = modele
        if effort is not None:
            if effort:
                r.setdefault("efforts_postes", {})[nom] = effort
            else:
                (r.get("efforts_postes") or {}).pop(nom, None)
        r["maj"] = maintenant()
        ecrire_json(chemin_r, r)
    apres = {"modele": modele or av_m, "effort": (effort if effort is not None else av_e) or None}
    ligne = {"quand": maintenant(), "agent": nom, "avant": {"modele": av_m, "effort": av_e}, "apres": apres, "raison": raison, "par": par,
             "fiche": chemin_projet(md) if a_md else None}
    if dem:
        ligne["demande"] = dem
    journal = lire_json(journal_modeles(), []) or []
    if not isinstance(journal, list):
        journal = []
    journal.append(ligne)
    ecrire_json(journal_modeles(), journal[-300:])
    return {"ok": True, "agent": nom, "avant": ligne["avant"], "apres": apres, "fiche": ligne["fiche"]}


def chemin_projet(c):
    """Chemin relatif au projet (projet derrière un lien vers un autre disque compris) ; absolu si impossible."""
    try:
        r = os.path.relpath(os.path.realpath(c), os.path.realpath(Etat.projet))
        return c if r.startswith("..") else r.replace("\\", "/")
    except ValueError:
        return c


def curl_modele(par, en):
    port = Etat.port or PORT_DEFAUT
    return (f'curl -s -X POST http://127.0.0.1:{port}/api/modele -H "Origin: http://127.0.0.1:{port}" -H "Content-Type: application/json" '
            '-d \'{"id": "<' + ("agent id" if en else "id de l’agent") + '>", "modele": "<haiku|sonnet|opus|fable|inherit>", '
            '"effort": "<low|medium|high|xhigh|max>", "raison": "<' + ("short reason" if en else "raison courte") + '>", '
            f'"par": "{par}", "demande": "<' + ("id of this request" if en else "id de cette demande") + '>"}\'')


def consigne_controleur(en):
    if en:
        return ("Model controller: for each listed agent, check that its model and effort fit its task (haiku or sonnet for simple, "
                "repetitive work; opus or fable for design, review and hard code; higher effort where it matters). Never interrupt a "
                "task in progress: the setting applies to the agent's next task. \"ultracode\" is a session mode: never set it per agent. "
                "Change a setting through the studio server, which writes the model:/effort: frontmatter of the agent definition "
                "(if any), the studio card and .studio/modeles_journal.json: " + curl_modele("controleur-modeles", True) + ". "
                "An agent left as is: nothing to post. Then answer in reponses_assistant.json with \"a_propos\" = the id of this "
                "request: what changed, for whom and why, in short sentences.")
    return ("Contrôleur des modèles : pour chaque agent listé, vérifie que le modèle et l'effort conviennent à sa tâche (haiku ou "
            "sonnet pour le simple et le répétitif ; opus ou fable pour la conception, la relecture et le code difficile ; effort plus "
            "haut là où ça compte). N'interromps aucune tâche en cours : le réglage vaut pour la prochaine tâche de l'agent. "
            "« ultracode » est un mode de la session : ne le règle jamais par agent. Change un réglage par le serveur du studio, qui "
            "écrit le frontmatter model:/effort: de la définition d'agent (si elle existe), la fiche du studio et "
            ".studio/modeles_journal.json : " + curl_modele("controleur-modeles", False) + ". Un agent laissé tel quel : rien à "
            "poster. Réponds ensuite dans reponses_assistant.json avec « a_propos » = l'id de cette demande : ce qui a changé, pour "
            "qui et pourquoi, en phrases courtes.")


def consigne_optim_modeles(en):
    if en:
        return ("Discreet model check (setting \"controle_modeles\", Models tab): while you are at it, check that each agent's model "
                "and effort fit its task; change only what is clearly unsuitable, never during a task in progress: "
                + curl_modele("optimisation", True) + ".")
    return ("Contrôle discret des modèles (réglage « controle_modeles », onglet Modèles) : au passage, regarde si le modèle et l'effort "
            "de chaque agent conviennent à sa tâche ; ne change que ce qui est nettement inadapté, jamais pendant une tâche en cours : "
            + curl_modele("optimisation", False) + ".")


def consigne_auditeur(en, modele, effort):
    if en:
        s = ("Studio auditor: IMPARTIAL audit of the requested scope (project, studio = <project>/.studio and its settings, latest "
             "version, current session). You defend nobody: verified findings, evidence (file, line, screenshot), severity "
             "grave / moyen / faible. Put the result at the top of .studio/audit.json (keep the older ones): "
             '{"audits": [{"id": "<id of this request>", "date": "YYYY-MM-DDTHH:MM:SS", "perimetre": [...], "resume": "...", '
             '"constats": [{"titre": "...", "detail": "...", "gravite": "grave|moyen|faible", "domaine": "projet|studio|version|session", '
             '"suite": "fixed in the studio|sent to the coordinator|noted", "correction": "..."}], '
             '"corrige_studio": ["..."], "envoye_coordinateur": ["..."]}]}. '
             "What belongs to the studio (.studio/: settings, cards, roadmap, requests): fix it yourself, carefully (the studio must "
             "never become unreachable). What belongs to the project: send it to the coordinator (POST /api/demande, cible "
             "\"assistant\", quoting this audit id); never change the project yourself. Finally answer in reponses_assistant.json with "
             "\"a_propos\" = the id of this request: summary and number of findings per severity.")
        return s + (f" Auditor setting (Models tab): model \"{modele}\"" + (f", effort \"{effort}\"" if effort else "")
                    + "; run the audit in a sub-agent with this model (Agent tool model parameter; inherit = the session's) and effort, "
                    "and say in your answer which model and effort it ran with.")
    s = ("Auditeur du studio : audit IMPARTIAL du périmètre demandé (projet, studio = <projet>/.studio et ses réglages, dernière "
         "version, session en cours). Tu ne défends personne : constats vérifiés, preuves (fichier, ligne, capture), gravité "
         "grave / moyen / faible. Range le résultat en tête de .studio/audit.json (garde les anciens) : "
         '{"audits": [{"id": "<id de cette demande>", "date": "AAAA-MM-JJTHH:MM:SS", "perimetre": [...], "resume": "...", '
         '"constats": [{"titre": "...", "detail": "...", "gravite": "grave|moyen|faible", "domaine": "projet|studio|version|session", '
         '"suite": "corrigé dans le studio|envoyé au coordinateur|noté", "correction": "..."}], '
         '"corrige_studio": ["..."], "envoye_coordinateur": ["..."]}]}. '
         "Ce qui relève du studio (.studio/ : réglages, fiches, roadmap, demandes) : corrige-le toi-même, prudemment (le studio ne "
         "doit jamais devenir inaccessible). Ce qui relève du projet : envoie-le au coordinateur (POST /api/demande, cible "
         "« assistant », en citant l'id de cet audit) ; ne modifie jamais le projet toi-même. Réponds enfin dans "
         "reponses_assistant.json avec « a_propos » = l'id de cette demande : résumé et nombre de constats par gravité.")
    return s + (f" Réglage de l'auditeur (onglet Modèles) : modèle « {modele} »" + (f", effort « {effort} »" if effort else "")
                + " ; lance l'audit avec un sous-agent à ce modèle (paramètre model de l'outil Agent ; inherit = celui de la session) "
                "et à cet effort, et dis dans ta réponse avec quel modèle et quel effort il a tourné.")


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
        h = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if RESEAU["ip"]:
            h.add(f"{RESEAU['ip']}:{port}")
        return h

    def cle_ok(self):
        """Clé du réseau de la maison : ?cle= (la réponse pose un cookie) ou cookie studio_cle."""
        import hmac
        if not RESEAU["cle"]:
            return False
        donnee = (parse_qs(urlsplit(self.path).query).get("cle") or [""])[0]
        if donnee and hmac.compare_digest(donnee, RESEAU["cle"]):
            self._poser_cookie = True
            return True
        for morceau in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = morceau.strip().partition("=")
            if k == "studio_cle" and hmac.compare_digest(v.strip(), RESEAU["cle"]):
                return True
        return False

    def acces_ok(self):
        """Hôte connu ; toute requête qui ne vient pas de 127.0.0.1 (option --reseau) arrive par l'IP locale et porte la clé."""
        hote = self.headers.get("Host", "")
        if hote not in self.hotes_permis():
            return False
        if self.client_address[0] != "127.0.0.1":
            return bool(RESEAU["ip"]) and hote == f"{RESEAU['ip']}:{self.server.server_address[1]}" and self.cle_ok()
        return True

    def end_headers(self):
        if getattr(self, "_poser_cookie", False):
            self._poser_cookie = False
            self.send_header("Set-Cookie", f"studio_cle={RESEAU['cle']}; Path=/; HttpOnly; SameSite=Strict; Max-Age=31536000")
        super().end_headers()

    def repondre_type(self, code, corps, type_):
        self.send_response(code)
        self.send_header("Content-Type", type_)
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(corps)

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
        piece = rel.startswith("demandes_vocales/pieces/") and not rel.startswith("demandes_vocales/pieces/_") and rel.count("/") == 3 and ext in PIECES_EXT
        if (ext not in EXTENSIONS and not piece) or os.path.basename(rel).lower() in ("cle_reseau.txt", "adresse_telephone.txt"):
            return None
        if ".illisible-" in rel or ".corrompu-" in rel or rel.lower().endswith((".bak", ".tmp")) or rel.startswith(("outils/", "_")):
            return None                                   # copies mises de côté, sauvegardes, temporaires, crochet copié : jamais servis
        for base in (Etat.studio, ICI):
            if not base:
                continue
            base_r = os.path.realpath(base)
            p = os.path.realpath(os.path.join(base_r, *rel.split("/")))
            if p.startswith(base_r + os.sep) and os.path.isfile(p):
                # le code du serveur et ses notes ne sont jamais servis depuis le dossier du skill
                if base == ICI and (rel.startswith("outils/") or ext in (".md",)):
                    return None
                if piece:                                 # pièce jointe : jamais depuis le dossier du skill
                    if base != Etat.studio:
                        return None
                    return p, EXTENSIONS.get(ext) if ext in EXTENSIONS else TYPES_PIECES.get(ext, "application/octet-stream")
                if ext not in EXTENSIONS:
                    return None
                return p, EXTENSIONS[ext]
        return None

    def do_GET(self):
        if not self.acces_ok():
            self.repondre(403, {"ok": False, "erreur": "hôte refusé"})
            return
        if urlsplit(self.path).path == "/api/transcrire":   # dictée locale disponible ? (la page choisit Whisper d'emblée)
            self.repondre(200, {"ok": True, "disponible": whisper_installe(), **_INFOS})
            return
        if urlsplit(self.path).path == "/manifest.webmanifest":   # application installable : nom du projet, icône du studio
            conf = lire_json(os.path.join(Etat.studio, "studio.config.json"), {})
            nom = str(conf.get("nom_projet") or os.path.basename(Etat.projet))[:40]
            lg = str(conf.get("langue") or "fr")[:2]
            self.repondre_type(200, json.dumps({"name": nom + " · Studio", "short_name": "Studio", "start_url": "/studio.html?app=1", "scope": "/",
                                                "display": "fullscreen", "display_override": ["fullscreen", "standalone"], "orientation": "portrait",
                                                "background_color": "#1a1612", "theme_color": "#2b241c", "lang": lg,
                                                "icons": [{"src": "icone-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                                                          {"src": "icone-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}]},
                                               ensure_ascii=False).encode("utf-8"), "application/manifest+json")
            return
        if urlsplit(self.path).path == "/api/conversation":   # conversation de Claude Code : lecture seule, en flux, en local
            try:
                if ICI not in sys.path:
                    sys.path.insert(0, ICI)
                import transcript_cc
                from urllib.parse import parse_qs
                q = parse_qs(urlsplit(self.path).query)
                depuis = int(q["depuis"][0]) if q.get("depuis") and q["depuis"][0].isdigit() else None
                conf = lire_json(os.path.join(Etat.studio, "studio.config.json"), {})
                dos = conf.get("dossier_session") if isinstance(conf.get("dossier_session"), str) and conf.get("dossier_session") not in ("", "auto") else None
                dos = dos or os.path.join(os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude"), "projects", transcript_cc.slug(Etat.projet))   # S13
                f = transcript_cc.session_active(dos)
                r = transcript_cc.lire(f, depuis)
                if depuis is not None and r.get("fichier") and q.get("fichier") and q["fichier"][0] != r["fichier"]:
                    r = transcript_cc.lire(f, None)
                self.repondre(200, dict(r, ok=True))
            except Exception as e:
                self.repondre(500, {"ok": False, "erreur": f"{type(e).__name__} : {e}"[:200]})
            return
        if urlsplit(self.path).path == "/api/instantane":   # P6 : tous les JSON d'un cycle en une requête, ETag commun (304 si rien n'a changé)
            from urllib.parse import parse_qs
            noms = [n for n in (parse_qs(urlsplit(self.path).query).get("f", [""])[0]).split(",") if n.endswith(".json")][:80]
            trouves, marques = {}, []
            for n in noms:
                t = self.trouver("/" + n)              # mêmes règles que la lecture d'un fichier seul (jamais les copies mises de côté)
                if not t:
                    trouves[n] = None
                    marques.append(n + ":-")
                    continue
                try:
                    st = os.stat(t[0])
                    trouves[n] = t[0]
                    marques.append(f"{n}:{int(st.st_mtime_ns):x}-{st.st_size:x}")
                except OSError:
                    trouves[n] = None
                    marques.append(n + ":-")
            import hashlib
            etag = '"' + hashlib.sha1("|".join(marques).encode("utf-8")).hexdigest()[:20] + '"'
            if self.headers.get("If-None-Match") == etag:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                return
            fichiers = {}
            for n, chemin in trouves.items():
                try:
                    fichiers[n] = open(chemin, encoding="utf-8").read() if chemin else None
                except (OSError, UnicodeDecodeError):
                    fichiers[n] = None
            corps = json.dumps({"ok": True, "fichiers": fichiers}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(corps)
            return
        if urlsplit(self.path).path == "/api/modeles":      # onglet « Modèles » : modèle et effort de chaque agent, journal
            try:
                self.repondre(200, lire_modeles())
            except Exception as e:
                self.repondre(500, {"ok": False, "erreur": f"{type(e).__name__} : {e}"[:200]})
            return
        if urlsplit(self.path).path == "/api/qui":          # reprise et arrêt : qui sert ce port ?
            self.repondre(200, {"ok": True, "pid": os.getpid(), "projet": Etat.projet, "port": self.server.server_address[1], "mis_de_cote": MIS_DE_COTE[-5:]})
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
        try:                                       # ETag (date et taille) : 304 quand rien n'a changé, sans relire le fichier
            st = os.stat(chemin)
            etag = f'"{int(st.st_mtime_ns):x}-{st.st_size:x}"'
        except OSError:
            etag = None
        if etag and self.headers.get("If-None-Match") == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            return
        try:
            with open(chemin, "rb") as f:
                corps = f.read()
        except OSError:
            self.repondre(404, {"ok": False, "erreur": "illisible"})
            return
        self.send_response(200)
        self.send_header("Content-Type", type_)
        self.send_header("Content-Length", str(len(corps)))
        if etag:
            self.send_header("ETag", etag)
        self.send_header("Cache-Control", "no-cache" if type_.startswith(("application/json", "text/html", "text/javascript", "text/css")) else "max-age=300")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if type_ == "application/octet-stream":       # pièce jointe sans aperçu possible : téléchargée, jamais ouverte dans la page
            self.send_header("Content-Disposition", "attachment")
        self.end_headers()
        try:
            self.wfile.write(corps)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass                                       # page quittée pendant l'envoi (navigation, rechargement) : rien à signaler

    def do_HEAD(self):
        """Existence d'un fichier servi (le fil vérifie qu'une pièce jointe est toujours là), sans corps ; les routes /api/ : 405."""
        chemin = urlsplit(self.path).path
        trouve = None if (not self.acces_ok() or chemin.startswith("/api/")) else self.trouver(self.path)
        code = 403 if not self.acces_ok() else 405 if chemin.startswith("/api/") else 200 if trouve else 404
        self.send_response(code)
        if trouve:
            try:
                taille = os.path.getsize(trouve[0])
            except OSError:
                taille = 0
            self.send_header("Content-Type", trouve[1])
            self.send_header("Content-Length", str(taille))
        else:
            self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()

    # ---------------------------------------------------------------- pièces jointes (corps brut)
    def piece(self, n):
        """Une pièce jointe déposée dans un brouillon : POST /api/piece?brouillon=<id>&nom=<nom du fichier>, corps = le fichier."""
        q = parse_qs(urlsplit(self.path).query)
        b = (q.get("brouillon") or [""])[0]
        if not BROUILLON_RE.match(b):
            raise Refus(400, "brouillon invalide")
        nom = nom_piece((q.get("nom") or [""])[0])
        if n <= 0:
            raise Refus(400, "fichier vide")
        if n > PIECE_MAX:
            raise Refus(413, f"fichier trop gros ({n // (1024 * 1024)} Mo ; {PIECE_MAX // (1024 * 1024)} Mo au plus)")
        dossier = os.path.join(dossier_pieces(), "_brouillons", b)
        if not os.path.isdir(dossier):
            nettoyer_brouillons()                        # premier fichier d'un brouillon : ménage des abandonnés au passage

        def controler():
            os.makedirs(dossier, exist_ok=True)
            parts = parts_vivants(dossier, b)
            prets = [f for f in os.listdir(dossier) if os.path.isfile(os.path.join(dossier, f)) and not f.endswith(".part")]
            res = _RESERVES.get(b, {})
            orphelins = [c for c in parts if c not in res]
            if len(prets) + len(parts) >= PIECES_MAX_N:
                raise Refus(413, f"{PIECES_MAX_N} pièces jointes au plus par message")
            poids = sum(os.path.getsize(os.path.join(dossier, f)) for f in prets) + sum(res.values()) + sum(os.path.getsize(c) for c in orphelins)
            if poids + n > PIECES_MAX_TOTAL:
                raise Refus(413, f"{PIECES_MAX_TOTAL // (1024 * 1024)} Mo au plus par message")
        base, ext = os.path.splitext(nom)
        tmp = os.path.join(dossier, f".{os.urandom(6).hex()}.part")    # caché, unique : jamais servi ni compté comme pièce prête
        with verrou_brouillon(b):
            controler()
            open(tmp, "wb").close()
            _RESERVES.setdefault(b, {})[tmp] = n         # place réservée à sa taille annoncée
        ancien_delai = self.connection.gettimeout()
        self._corps_lu = True
        try:
            reste, debut = n, b""
            self.connection.settimeout(30)               # 30 s sans un octet : envoi abandonné, .part effacé
            with open(tmp, "r+b") as f:
                while reste:
                    try:
                        morceau = self.rfile.read(min(reste, 256 * 1024))
                    except OSError:
                        self.close_connection = True
                        raise Refus(408, "envoi interrompu (plus rien reçu depuis 30 s)")
                    if not morceau:
                        self.close_connection = True
                        raise Refus(400, "envoi interrompu")
                    if len(debut) < 16:
                        debut += morceau[:16 - len(debut)]
                    f.write(morceau)
                    reste -= len(morceau)
            if not signature_ok(ext, debut):
                raise Refus(415, f"le contenu ne ressemble pas à un fichier {ext}")
            with verrou_brouillon(b):
                final, k = nom, 2
                while os.path.exists(os.path.join(dossier, final)):
                    final, k = f"{base}-{k}{ext}", k + 1
                os.replace(tmp, os.path.join(dossier, final))
        except BaseException:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise
        finally:
            with verrou_brouillon(b):
                r = _RESERVES.get(b, {})
                r.pop(tmp, None)
                if not r:
                    _RESERVES.pop(b, None)
            try:
                self.connection.settimeout(ancien_delai)
            except OSError:
                pass
        return {"ok": True, "nom": final, "taille": n, "brouillon": b}

    def vider(self, reste):
        """Corps d'une pièce refusée avant lecture : lu et jeté (20 Mo au plus, 30 s sans octet = abandon), connexion fermée ensuite."""
        self.close_connection = True
        if reste <= 0 or reste > PIECE_MAX:
            return
        ancien = self.connection.gettimeout()
        try:
            self.connection.settimeout(30)
            while reste > 0:
                m = self.rfile.read(min(reste, 256 * 1024))
                if not m:
                    break
                reste -= len(m)
        except OSError:
            pass
        finally:
            try:
                self.connection.settimeout(ancien)
            except OSError:
                pass

    # ---------------------------------------------------------------- POST
    def do_POST(self):
        try:
            if not self.acces_ok():
                raise Refus(403, "hôte refusé")
            origine = self.headers.get("Origin", "")
            if origine not in {"http://" + h for h in self.hotes_permis()} or origine != "http://" + self.headers.get("Host", ""):
                raise Refus(403, "origine refusée")
            route = urlsplit(self.path).path
            try:
                n = int(self.headers.get("Content-Length", "0") or 0)
            except ValueError:
                raise Refus(400, "Content-Length invalide")
            if n < 0:
                raise Refus(400, "Content-Length invalide")
            if route == "/api/transcrire":
                if n <= 0 or n > MAX_AUDIO:
                    raise Refus(413, "audio vide ou trop long")
                type_ = self.headers.get("Content-Type", "")
                if not type_.startswith(("audio/", "video/webm", "application/octet-stream")):
                    raise Refus(415, "audio attendu")
                audio = self.rfile.read(n)
                direct = "direct=1" in urlsplit(self.path).query.split("&")   # aperçu pendant la dictée
                self.repondre(200, transcrire(audio, direct=direct))
                return
            if route == "/api/piece":
                self._corps_lu = False
                try:
                    res = self.piece(n)                   # verrou court par brouillon : un envoi lent ne bloque aucune autre route
                except Refus:
                    if not self._corps_lu:
                        self.vider(n)                     # refus avant lecture : corps lu et jeté (sinon la page ne voit pas le refus)
                    raise
                self.repondre(200, res)
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
                      "/api/repondre": route_repondre, "/api/reglages": route_reglages, "/api/couper": route_couper, "/api/relancer": route_relancer,
                      "/api/recruter": route_recruter, "/api/confier": route_confier,
                      "/api/renvoyer": route_renvoyer, "/api/reembaucher": route_reembaucher, "/api/agent": route_agent,
                      "/api/meneur": route_meneur, "/api/quete": route_quete, "/api/sante": route_sante, "/api/modele": route_modele,
                      "/api/piece_retirer": route_piece_retirer, "/api/demande_annuler": route_demande_annuler,
                      "/api/cloche": route_cloche}.get(route)
            if not action:
                raise Refus(404, "route inconnue")
            if route == "/api/sante":
                d["_local"] = self.client_address[0] == "127.0.0.1"      # l'élévation se demande devant le PC, jamais à distance
            with VERROU:
                try:
                    rep = action(d)
                except (TypeError, AttributeError, KeyError) as e:   # F22 / F23 : une valeur du mauvais type → 400, pas 500
                    sys.stderr.write(f"donnée invalide sur {route} : {e!r}\n")
                    raise Refus(400, "donnée invalide (type inattendu)")
                self.repondre(200, rep)
        except Refus as e:
            self.repondre(e.code, {"ok": False, "erreur": refus_langue(str(e))})
        except Exception as e:  # jamais de trace détaillée vers la page
            sys.stderr.write(f"erreur interne : {e!r}\n")
            self.repondre(500, {"ok": False, "erreur": "erreur interne"})


# -------------------------------------------------------------------- routes
ONGLETS = {}                # S37 : onglets ouverts (identifiant → dernier signe de vie) ; le plus ancien encore vivant agit
ONGLETS_VERROU = threading.Lock()


QUETE_ID_RE = re.compile(r"^Q-[A-Z]{2}-\d{2}$")


def route_quete(d):
    """S4 : réponse à une quête (accepter, plus_tard, refuser, suivre, preuve). Accepter embauche les agents proposés
    choisis (même logique que /api/recruter, lancer: false, mêmes plafonds) : rien n'est lancé ; l'assistant montre la fiche."""
    if ICI not in sys.path:
        sys.path.insert(0, ICI)
    import quetes
    id_ = texte(d, "id", 20, True)
    if not QUETE_ID_RE.match(id_):
        raise Refus(400, "id de quête invalide")
    action = texte(d, "action", 12, True)
    agents = d.get("agents")
    if agents is not None and (not isinstance(agents, list) or len(agents) > 6 or not all(isinstance(a, str) and NOM_RE.match(a) for a in agents)):
        raise Refus(400, "agents : liste de noms (6 au plus)")
    chemin = texte(d, "chemin", 300) or None
    try:
        r = quetes.repondre(Etat.projet, id_, action, agents=agents, chemin=chemin)
    except quetes.Refus as e:
        raise Refus(e.code, e.message)
    embauches, refus = [], []
    for corps in r.get("recruter") or []:
        if not isinstance(corps, dict):
            continue
        try:
            f = route_recruter(dict(corps, lancer=False, via="ecrit"))
            embauches.append({"nom": f["fiche"]["nom"], "nom_affiche": f["fiche"]["nom_affiche"], "agent": f["agent"]})
        except Refus as e:
            refus.append({"nom": corps.get("nom"), "raison": str(e)})
    actives = []
    for cle in r.get("activer") or []:      # agents de soutien que la page dessine déjà (auditeur, contrôleur des modèles) : un réglage les active
        if cle in ("auditeur", "controle_modeles"):
            route_reglages({cle: True})
            actives.append(cle)
    r.update(embauches=embauches, refus_embauche=refus, actives=actives)
    return r


def route_meneur(d):
    """Un seul onglet (PC ou téléphone) fait tourner les automatismes : le plus ancien qui a donné signe de vie depuis 25 s."""
    oid = str(d.get("onglet") or "")[:40]
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,40}", oid):
        raise Refus(400, "onglet invalide")
    maintenant = time.time()
    with ONGLETS_VERROU:
        for k in [k for k, v in ONGLETS.items() if maintenant - v["vu"] > 25]:
            ONGLETS.pop(k, None)
        o = ONGLETS.setdefault(oid, {"depuis": maintenant, "vu": maintenant})
        o["vu"] = maintenant
        if len(ONGLETS) > 50:                                 # garde-fou : jamais plus de 50 onglets suivis
            for k in sorted(ONGLETS, key=lambda k: ONGLETS[k]["vu"])[:len(ONGLETS) - 50]:
                ONGLETS.pop(k, None)
        meneur = min(ONGLETS, key=lambda k: (ONGLETS[k]["depuis"], k))
    return {"ok": True, "meneur": meneur == oid, "onglets": len(ONGLETS)}


def route_questionnaire(d):
    chemin = os.path.join(Etat.studio, "reponses_questionnaire.json")
    q = lire_ou_mettre_de_cote(chemin, None)
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
    p = lire_ou_mettre_de_cote(chemin, None)
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
    if cible != "assistant" and cible not in CIBLES_SPECIALES:
        if cible not in ids_postes():
            raise Refus(404, "poste inconnu")
    brouillon = texte(d, "brouillon", 40)
    if brouillon and not BROUILLON_RE.match(brouillon):
        raise Refus(400, "brouillon invalide")
    dossier_b = os.path.join(dossier_pieces(), "_brouillons", brouillon) if brouillon else None
    if dossier_b and not os.path.isdir(dossier_b):
        raise Refus(410, "pièces jointes introuvables (brouillon expiré) : joins-les de nouveau")
    conf = lire_json(os.path.join(Etat.studio, "studio.config.json"), {}) or {}
    en = str(conf.get("langue") or "fr")[:2].lower() != "fr"
    txt_ecrit = texte(d, "texte", 2000, not dossier_b)
    txt = txt_ecrit or ("(attachments)" if en else "(pièces jointes)")
    extra = {}
    if cible == "auditeur":
        r = lire_json(os.path.join(Etat.studio, "reglages.json"), {}) or {}
        if not r.get("auditeur"):
            raise Refus(403, "l'auditeur est désactivé (Réglages)")
        per = d.get("perimetre") or list(PERIMETRES)
        if not isinstance(per, list) or not per or len(per) > 4 or any(x not in PERIMETRES for x in per):
            raise Refus(400, "périmètre : projet, studio, version, session")
        m_a = (r.get("modeles_postes") or {}).get("auditeur") or "inherit"
        e_a = (r.get("efforts_postes") or {}).get("auditeur")
        extra = {"perimetre": per, "modele": m_a, "effort": e_a, "consigne": consigne_auditeur(en, m_a, e_a)}
    elif cible == "controleur-modeles":
        extra = {"consigne": consigne_controleur(en)}
    via = texte(d, "via", 10) or "ecrit"
    if via not in ("voix", "ecrit"):
        raise Refus(400, "via : voix ou ecrit")
    sujet = texte(d, "sujet", 20)
    if sujet not in ("", "optimisation"):
        raise Refus(400, "sujet : optimisation ou rien")
    en_rep = texte(d, "en_reponse_a", 120)       # réponse écrite sous une réponse de l'assistant (id de l'entrée)
    if en_rep and not re.match(r"^[A-Za-z0-9_.:+-]{1,120}$", en_rep):
        raise Refus(400, "en_reponse_a invalide")
    if sujet == "optimisation" and controle_modeles_actif():
        c_o = consigne_optim_modeles(en)                 # complète la consigne déjà posée (auditeur, contrôleur), sans l'écraser
        extra = dict(extra, consigne=(extra["consigne"] + "\n\n" + c_o) if extra.get("consigne") else c_o)
    cle = ("demande", cible, sujet, " ".join(txt.split()).lower(), brouillon)
    deja = doublon(cle)
    if deja:
        return dict(deja, doublon=True)
    dossier = os.path.join(Etat.studio, "demandes_vocales")
    if sujet == "optimisation":
        garde_optimisation(dossier)
    donnees = dict({"cible": cible, "texte": txt, "via": via, "cree_le": maintenant(), "statut": "nouvelle"}, **extra)
    if sujet:
        donnees["sujet"] = sujet
    if en_rep:
        donnees["en_reponse_a"] = en_rep
    pieces = []

    def preparer(ident, contenu):
        """Pièces jointes rangées dans demandes_vocales/pieces/<id>/ AVANT l'écriture de la demande ; chemins absolus listés pour Claude."""
        if dossier_b:
            final = os.path.join(dossier_pieces(), ident)
            with verrou_brouillon(brouillon):
                if parts_vivants(dossier_b, brouillon):
                    raise Refus(409, "une pièce jointe est encore en cours d'envoi : réessaie dans un instant")
                if not txt_ecrit and not any(os.path.isfile(os.path.join(dossier_b, x)) and not x.startswith(".") for x in os.listdir(dossier_b)):
                    raise Refus(400, "message vide : ni texte, ni pièce jointe")
                try:
                    os.replace(dossier_b, final)
                except OSError:
                    raise Refus(503, "pièces jointes impossibles à ranger : message non déposé, réessaie")
            pieces[:] = [os.path.abspath(os.path.join(final, x)) for x in sorted(os.listdir(final))
                         if os.path.isfile(os.path.join(final, x)) and not x.startswith(".")]
            contenu["pieces"] = list(pieces)
            contenu["texte"] = contenu["texte"] + ("\n\nAttachments (" if en else "\n\nPièces jointes (") + str(len(pieces)) + ("):\n" if en else ") :\n") + "\n".join("- " + x for x in pieces)
        return contenu

    def annuler(ident):
        final = os.path.join(dossier_pieces(), ident)
        if dossier_b and os.path.isdir(final) and not os.path.exists(dossier_b):
            try:
                os.replace(final, dossier_b)                 # pièces rendues au brouillon : rien d'orphelin
            except OSError:
                pass
    ident = creer_unique(dossier, cible, donnees, preparer, annuler)
    return doublon(cle, {"ok": True, "id": ident, "pieces": pieces})


def route_demande_annuler(d):
    """Annule une demande à l'auditeur ou au contrôleur des modèles restée sans réponse (statut « annulee » : Claude l'ignore)."""
    ident = texte(d, "id", 120, True)
    if not re.match(r"^[A-Za-z0-9_.:+-]{1,120}$", ident):
        raise Refus(400, "id invalide")
    c = os.path.join(Etat.studio, "demandes_vocales", ident + ".json")
    x = lire_json(c, None) if os.path.isfile(c) else None
    if not isinstance(x, dict):
        raise Refus(404, "demande inconnue")
    if x.get("cible") not in CIBLES_SPECIALES:
        raise Refus(403, "seules les demandes à l'auditeur ou au contrôleur des modèles s'annulent ici")
    if str(x.get("statut") or "nouvelle") not in ("nouvelle", "prise"):
        return {"ok": True, "id": ident, "statut": x.get("statut"), "deja": True}
    x["statut"], x["annulee_le"] = "annulee", maintenant()
    ecrire_json(c, x)
    return {"ok": True, "id": ident, "statut": "annulee"}


def controle_modeles_actif(r=None):
    """Contrôleur des modèles : agent de soutien qui arrive par une quête (S4). Allumé seulement quand reglages.json dit
    true (quête acceptée ou case cochée). Si les quêtes sont coupées, il reste allumé tant que reglages.json ne dit pas false."""
    if r is None:
        r = lire_json(os.path.join(Etat.studio, "reglages.json"), {})
    r = r if isinstance(r, dict) else {}
    v = r.get("controle_modeles")
    return v is True or (v is None and r.get("quetes_actives") is False)


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


def dossier_relatif():
    try:
        r = os.path.relpath(Etat.studio, Etat.projet).replace("\\", "/")
    except ValueError:
        r = ".studio"
    return r if not r.startswith("..") else ".studio"


def definition_agent(conf, v):
    """Remplit modeles/agent.md (sinon le gabarit intégré) en un seul passage :
    des accolades doubles écrites par l'utilisateur ne sont jamais réinterprétées."""
    gab = None
    en = str(conf.get("langue") or "fr")[:2].lower() != "fr"           # projet en anglais (ou autre langue) : gabarit anglais
    for chemin in ([os.path.join(os.path.dirname(ICI), "modeles", "en", "agent.md")] if en else []) + [os.path.join(os.path.dirname(ICI), "modeles", "agent.md")]:
        try:
            with open(chemin, encoding="utf-8-sig") as f:
                gab = f.read()
            break
        except OSError:
            pass
    gab = gab or GABARIT_AGENT
    # règles de la config (qui peut venir d'un dépôt cloné) : 20 au plus, une ligne de 200 caractères chacune
    regles = [re.sub(r"\s+", " ", x).strip()[:200] for x in (conf.get("regles_agent") or []) if isinstance(x, str)]
    regles = [r.lstrip("#>-* ") for r in regles if r.strip("#>-* ")] or ["Write in the project language, in short sentences." if en else "Écris dans la langue du projet, en phrases courtes."]
    eco = conf.get("economie") if isinstance(conf.get("economie"), dict) else {}
    modele = eco.get("modele_agents") if eco.get("modele_agents") in MODELES_AGENT else "sonnet"
    valeurs = {"id": v["nom"], "nom_affiche": v["nom_affiche"], "nom_projet": str(conf.get("nom_projet") or os.path.basename(Etat.projet)),
               "poste": v["poste"] or ("new desk" if en else "nouveau bureau"), "role": v["role"], "mission": v["mission"],
               "skills": "\n".join("- `" + s + "`" for s in v["skills"]) or ("- `gamedev:router` if installed (it picks the right skill)" if en else "- `gamedev:router` s'il est installé (il choisit le bon skill)"),
               "regles_agent": "\n".join("- " + r for r in regles[:20]), "dossier_studio": dossier_relatif(),   # relatif au projet : aucun chemin de la machine dans un fichier qu'on peut versionner
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
    if not os.path.exists(os.path.join(Etat.studio, "recrues", nom + ".json")) and nb_bureaux(conf) >= NB_BUREAUX:
        raise Refus(409, f"{NB_BUREAUX} bureaux occupés : renvoie une recrue avant d'en embaucher une autre")
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
                 agent=os.path.relpath(os.path.realpath(chemin_agent), os.path.realpath(Etat.projet)).replace("\\", "/"))   # projet derrière un lien vers un autre disque
    ecrire_json(os.path.join(Etat.studio, "recrues", nom + ".json"), fiche)
    idx_ch = os.path.join(Etat.studio, "recrues", "index.json")
    idx = index_lisible(idx_ch)
    idx = [x for x in idx if x != nom][-40:] + [nom]
    ecrire_json(idx_ch, idx)
    ident = creer_unique(os.path.join(Etat.studio, "demandes"), nom, dict(fiche, type="recrutement", statut="nouvelle"))
    return {"ok": True, "fiche": fiche, "demande": "demandes/" + ident + ".json", "agent": fiche["agent"]}


def nb_bureaux(conf):
    base = [p for p in (conf.get("postes") or []) if isinstance(p, dict) and p.get("id")][:9]
    ids = {p["id"] for p in base}
    idx = index_lisible(os.path.join(Etat.studio, "recrues", "index.json"))
    return len(base) + len([x for x in idx if x not in ids])


def garde_embauche_auto(conf, nom):
    """Embauche décidée par le studio : réglage activé, une par heure, 12 bureaux, jamais un ancien renvoyé."""
    if not reglage("embauche_auto") and not reglage("tyrannie_auto"):
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
        # rôle temporaire d'un agent qui attend : permis par la tyrannie seule (mêmes plafonds)
        if not reglage("attribution_auto") and not (origine == "auto:temporaire" and reglage("tyrannie_auto")):
            raise Refus(403, "attribution automatique coupée (Réglages ou economie.attribution_auto)")
        autos = [(x, st) for _, x, st in demandes_du_poste(agent) if str(x.get("origine", "")).startswith("auto:")]
        if sum(1 for _, st in autos if not st.startswith(FINIS)) >= AUTO_ATTENTE_MAX:
            raise Refus(429, f"« {agent} » a déjà une attribution automatique en attente")
        plafond = 6 if reglage("tyrannie_auto") else AUTO_PAR_HEURE
        if sum(1 for x, _ in autos if time.time() - iso_t(x.get("cree_le")) < 3600) >= plafond:
            raise Refus(429, f"{plafond} attributions automatiques par heure au plus pour « {agent} »")
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


def index_lisible(chemin):
    """recrues/index.json, ou, s'il est illisible, la liste reconstruite depuis les fiches recrues/*.json (F6 : aucune recrue perdue)."""
    idx = lire_json(chemin, None) if os.path.exists(chemin) else []
    if isinstance(idx, list):
        return [x for x in idx if isinstance(x, str)]
    dossier = os.path.dirname(chemin)
    fiches = []
    for f in os.listdir(dossier):
        if f.endswith(".json") and f != "index.json" and ".corrompu-" not in f and ".illisible-" not in f:
            x = lire_json(os.path.join(dossier, f), None)
            if isinstance(x, dict) and isinstance(x.get("nom"), str):
                fiches.append((x.get("cree_le") or "", x["nom"]))
    return [n for _, n in sorted(fiches)]


def index_noms(chemin, ajouter=None, retirer=None):
    idx = [x for x in index_lisible(chemin) if x not in (ajouter, retirer)]
    if ajouter:
        idx.append(ajouter)
    ecrire_json(chemin, idx[-60:])


METIERS_PERMIS = {"code", "relecture", "art", "son", "ia", "doc", "design", "test", "moteur", "studio"}


def route_agent(d):
    """Fiche d'un agent : nom affiché, métiers (liste) et rôle libre. Recrue : recrues/<nom>.json et sa définition d'agent
    (description, nom, section « Métiers » ; le reste n'est pas touché). Poste de la config : reglages.json
    (noms_postes, roles_postes, metiers_postes). La tyrannie et l'attribution choisissent les tâches d'après ces métiers."""
    conf = lire_json(os.path.join(Etat.studio, "studio.config.json"), {})
    nom = texte(d, "id", 40, True).lower()
    if not ID_RE.match(nom):
        raise Refus(400, "id invalide")
    affiche = texte(d, "nom_affiche", 40)
    role = texte(d, "role", 200).replace("\n", " ")
    metiers = d.get("metiers")
    if metiers is not None and (not isinstance(metiers, list) or len(metiers) > 6 or any(m not in METIERS_PERMIS for m in metiers)):
        raise Refus(400, "métiers : " + ", ".join(sorted(METIERS_PERMIS)))
    modele = texte(d, "modele", 10)
    if modele and modele not in MODELES_AGENT:
        raise Refus(400, "modèle : haiku, sonnet, opus, fable ou inherit")
    fiche_ch = os.path.join(Etat.studio, "recrues", nom + ".json")
    if os.path.isfile(fiche_ch):
        fiche = lire_json(fiche_ch, {}) or {}
        if affiche:
            fiche["nom_affiche"] = affiche
        if role:
            fiche["role"] = role
        if metiers is not None:
            fiche["metiers"] = metiers
        if modele:
            fiche["modele"] = modele
        ecrire_json(fiche_ch, fiche)
        md = os.path.join(dossier_agents(conf), nom + ".md")
        if os.path.isfile(md):
            with open(md, encoding="utf-8") as f:
                t = f.read()
            if role:
                t = re.sub(r"(?m)^description: .*$", lambda m: 'description: "' + yaml_chaine(role) + '"', t, count=1)
            if modele:                                   # frontmatter « model: » (vaut au prochain lancement de l'agent)
                if re.search(r"(?m)^model: .*$", t.split("\n---", 1)[0]):
                    t = re.sub(r"(?m)^model: .*$", "model: " + modele, t, count=1)
                else:
                    t = re.sub(r"(?m)^(description: .*)$", lambda m: m.group(1) + "\nmodel: " + modele, t, count=1)
            en = str(conf.get("langue") or "fr")[:2].lower() != "fr"
            if role:                                     # F24 : la section du rôle suit aussi (« Ton rôle » / « Your role »)
                t = re.sub(r"(\n## (?:Ton rôle|Your role)\n).*?(?=\n## |\Z)", lambda m: m.group(1) + role + "\n", t, count=1, flags=re.S)
            if metiers is not None:
                t = re.sub(r"\n## (?:Métiers|Trades)\n.*?(?=\n## |\Z)", "", t, flags=re.S)
                if metiers:
                    t = t.rstrip("\n") + "\n\n## " + ("Trades" if en else "Métiers") + "\n" + ", ".join(metiers) + "\n"
            with open(md + ".tmp", "w", encoding="utf-8", newline="\n") as f:
                f.write(t)
            os.replace(md + ".tmp", md)
        return {"ok": True, "fiche": fiche}
    if nom not in {p.get("id") for p in (conf.get("postes") or []) if isinstance(p, dict)}:
        raise Refus(404, f"agent « {nom} » inconnu")
    chemin = os.path.join(Etat.studio, "reglages.json")
    r = lire_ou_mettre_de_cote(chemin, {}) or {}
    if affiche:
        r.setdefault("noms_postes", {})[nom] = affiche
    if role:
        r.setdefault("roles_postes", {})[nom] = role
    if metiers is not None:
        r.setdefault("metiers_postes", {})[nom] = metiers
    if modele:
        r.setdefault("modeles_postes", {})[nom] = modele
    r["maj"] = maintenant()
    ecrire_json(chemin, r)
    return {"ok": True}


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


# Cloche : « plus tard » (caché 24 h) et « confié à un agent » tenus ici, pour que le PC et le téléphone voient la même liste.
# Fichier : {"plus_tard": {cle: fin en ms}, "confies": {cle: moment en ms}} ; les entrées périmées partent à chaque écriture.
CLE_CLOCHE_RE = re.compile(r"^[^\x00-\x1f<>]{1,200}$")


def memo_cloche(chemin, d, lire, ecrire):
    action = d.get("action")
    if action not in ("reporter", "confier", "remettre"):
        raise Refus(400, "action : reporter, confier ou remettre")
    cle = d.get("cle")
    if not isinstance(cle, str) or not CLE_CLOCHE_RE.match(cle):
        raise Refus(400, "clé invalide")
    m = lire(chemin, {})
    m = m if isinstance(m, dict) else {}
    n = time.time() * 1000
    jour = 864e5
    def propre(x, garde):
        x = x if isinstance(x, dict) else {}
        o = {k: v for k, v in x.items() if isinstance(k, str) and isinstance(v, (int, float)) and garde(v)}
        return dict(sorted(o.items(), key=lambda kv: kv[1])[-400:])
    pt = propre(m.get("plus_tard"), lambda v: v > n)
    cf = propre(m.get("confies"), lambda v: v > n - jour)
    if action == "reporter":
        pt[cle] = n + jour
    elif action == "confier":
        cf[cle] = n
    else:
        pt.pop(cle, None)
        cf.pop(cle, None)
    ecrire(chemin, {"plus_tard": pt, "confies": cf})
    return {"ok": True, "plus_tard": pt, "confies": cf}


def route_cloche(d):
    return memo_cloche(os.path.join(Etat.studio, "cloche_memo.json"), d, lire_json, ecrire_json)


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


AUTOS_COUPER = ("attribution_auto", "embauche_auto", "enchainement_auto", "point_auto", "optimisation_auto", "tyrannie_auto", "sante_auto")


def route_sante(d):
    """Santé du PC (sante_machine.py). action :
      activer_temperatures / desinstaller_temperatures : sur le CLIC de l'utilisateur (via « clic »), depuis le PC lui-même :
        lance outils/temperatures_windows.ps1 avec élévation ; Windows demande « Oui » (jamais d'élévation sans ce clic).
        Résultat dans .studio/sante/temperatures_activation.json (active / refuse / echec / desinstalle), montré par etat.json.
      analyser_menage : l'agent analyse tout de suite ce qui prend de la place (proposition sous la cloche, rien n'est effacé).
    Le ménage lui-même ne s'exécute que par la réponse « faire » à sa décision (/api/repondre)."""
    action = d.get("action")
    if action not in ("activer_temperatures", "desinstaller_temperatures", "analyser_menage"):
        raise Refus(400, "action : activer_temperatures, desinstaller_temperatures ou analyser_menage")
    if ICI not in sys.path:
        sys.path.insert(0, ICI)
    import sante_machine
    dossier = os.path.join(Etat.studio, "sante")
    os.makedirs(dossier, exist_ok=True)
    if action == "analyser_menage":
        with open(os.path.join(dossier, "analyser.demande"), "w", encoding="utf-8") as f:
            f.write(maintenant())
        return {"ok": True, "quoi": "analyse demandée : la proposition arrive sous la cloche"}
    if d.get("via") != "clic":
        raise Refus(400, "activation seulement sur un clic de l'utilisateur (via : clic)")
    if not d.get("_local"):
        raise Refus(403, "à faire depuis le PC lui-même : Windows y demande « Oui »")
    if os.name != "nt":
        raise Refus(501, "rien à activer hors de Windows (Linux : lecture directe ; macOS : non disponible)")
    try:
        return sante_machine.lancer_activation("installer" if action == "activer_temperatures" else "desinstaller", dossier,
                                               os.path.join(ICI, "outils", "temperatures_windows.ps1"))
    except (OSError, RuntimeError, ValueError) as e:
        raise Refus(500, f"activation impossible : {e}")


def route_relancer(d):
    """Bouton « Relancer » du bandeau : relance l'alimentation du studio par sa veille (rien d'autre n'est lancé)."""
    sys.path.insert(0, ICI) if ICI not in sys.path else None
    from veille_studio import lire_pid, vivant
    verrou = os.path.join(Etat.studio, "veille_studio.verrou")
    if vivant(lire_pid(verrou)):
        alim = lire_pid(os.path.join(Etat.studio, "studio_etat.verrou"))
        if vivant(alim):
            try:
                import signal
                os.kill(alim, signal.SIGTERM)             # alimentation figée : la veille la relance aussitôt
            except OSError:
                pass
        return {"ok": True, "quoi": "alimentation relancée par la veille"}
    import subprocess
    drapeaux = (getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0
    subprocess.Popen([sys.executable, "-I", "-B", os.path.join(ICI, "veille_studio.py"), "--projet", Etat.projet],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=drapeaux,
                     start_new_session=os.name != "nt", close_fds=True)
    return {"ok": True, "quoi": "veille lancée"}


def route_couper(d):
    """« Tout couper » : tous les automatismes à false, l'état d'avant gardé (avant_pause) ; « Tout rallumer » le remet."""
    action = d.get("action")
    if action not in ("couper", "rallumer"):
        raise Refus(400, "action : couper ou rallumer")
    chemin = os.path.join(Etat.studio, "reglages.json")
    r = lire_ou_mettre_de_cote(chemin, {})
    if not isinstance(r, dict):
        r = {}
    if action == "couper":
        if not r.get("pause"):
            r["avant_pause"] = {k: r.get(k) for k in AUTOS_COUPER}     # None = la clé n'existait pas (valeur de la config)
        r.update({k: False for k in AUTOS_COUPER}, pause=True, pause_depuis=maintenant())
    else:
        avant = r.pop("avant_pause", None)
        if isinstance(avant, dict):
            for k, v in avant.items():
                if k not in AUTOS_COUPER:
                    continue
                if v is None:
                    r.pop(k, None)                               # on rend la main à la config
                else:
                    r[k] = bool(v)
        r["pause"] = False
        r.pop("pause_depuis", None)
    r["maj"] = maintenant()
    ecrire_json(chemin, r)
    return {"ok": True, "reglages": r}


# F25 : refus dans la langue du projet (les messages sont écrits en français ; un projet non français les reçoit en anglais)
REFUS_EN = [
    ('^« (.+) » a une tâche en cours : (.*)$', '“\\1” has a task in progress: \\2'),
    ('^attribution automatique coupée.*$', 'automatic assignment is off (Settings or economie.attribution_auto)'),
    ('^embauches automatiques coupées.*$', 'automatic hiring is off (Settings or economie.embauche_auto)'),
    ('^les postes de base du studio ne se renvoient pas$', "the studio's base desks cannot be let go"),
    ('^« (.+) » a été renvoyé : seule une réembauche à la main le fait revenir$', '“\\1” was let go: only a manual rehire brings them back'),
    ('^« (.+) » est déjà un poste du studio : choisis un autre nom$', '“\\1” is already a studio desk: pick another name'),
    ("^« (.+) » existe déjà dans l'équipe$", '“\\1” is already in the team'),
    ("^l'agent « (.+) » existe déjà \\(coche « remplacer » pour remplacer une recrue du studio\\)$", 'agent “\\1” already exists (tick “replace” to replace a studio recruit)'),
    ("^l'agent « (.+) » n'a pas été recruté par le studio.*$", 'agent “\\1” was not hired by the studio (written by hand?): it is never replaced, pick another name'),
    ('^le studio a déjà (\\d+) bureaux$', 'the studio already has \\1 desks'),
    ("^(\\d+) bureaux occupés : renvoie une recrue avant d'en embaucher une autre$", '\\1 desks taken: let a recruit go before hiring another'),
    ('^une embauche automatique par heure au plus$', 'at most one automatic hire per hour'),
    ('^une transcription est déjà en cours : réessaie dans un instant$', 'a transcription is already running: try again in a moment'),
    ("^la demande d'optimisation d'il y a (\\d+) min attend encore sa réponse$", 'the optimization request from \\1 min ago is still waiting for an answer'),
    ('^optimisation déjà demandée il y a (\\d+) min \\(une toutes les (\\d+) min au plus\\)$', 'optimization already requested \\1 min ago (at most one every \\2 min)'),
    ('^(\\d+) attributions automatiques par heure au plus pour « (.+) »$', 'at most \\1 automatic assignments per hour for “\\2”'),
    ('^« (.+) » a déjà une attribution automatique en attente$', '“\\1” already has an automatic assignment waiting'),
    ('^transcription locale absente.*$', 'local transcription missing: install faster-whisper (pip install faster-whisper) or use a browser with speech recognition; you can always type your answer'),
    ('^choisir une option ou écrire une réponse$', 'pick an option or write an answer'),
    ('^fichier occupé \\((.+)\\), réessaie dans un instant$', 'file busy (\\1), try again in a moment'),
    ('^reponses\\.json illisible.*$', 'reponses.json is unreadable: nothing is written (repair or rename it)'),
    ('^activation seulement sur un clic.*$', 'enabling only on a user click (via: clic)'),
    ('^à faire depuis le PC lui-même.*$', 'to do from the PC itself: Windows asks “Yes” there'),
    ('^rien à activer hors de Windows.*$', 'nothing to enable outside Windows (Linux: direct reading; macOS: not available)'),
    ('^action : activer_temperatures.*$', 'action: activer_temperatures, desinstaller_temperatures or analyser_menage'),
    ("^(.+) est illisible \\((.+)\\) : rien n'est écrit pour ne rien perdre\\..*$", '\\1 is unreadable (\\2): nothing is written so nothing is lost.'),
    ('^nom : 3 à 40 caractères.*$', 'name: 3 to 40 characters among a-z, 0-9 and - (starting with a letter or digit)'),
    ('^audio illisible \\((.*)\\)$', 'unreadable audio (\\1)'),
    ('^audio vide ou trop long$', 'audio empty or too long'),
    ('^recrue « (.+) » inconnue$', 'unknown recruit “\\1”'),
    ('^ancien « (.+) » inconnu$', 'unknown former member “\\1”'),
    ('^agent « (.+) » inconnu$', 'unknown agent “\\1”'),
    ('^poste inconnu$', 'unknown desk'),
    ('^donnée invalide \\(type inattendu\\)$', 'invalid data (unexpected type)'),
    ("^type de fichier refusé.*$", 'file type refused (images, PDF, text, JSON, ZIP, 3D, sound or video)'),
    ('^fichier trop gros \\((\\d+) Mo ; (\\d+) Mo au plus\\)$', 'file too big (\\1 MB; \\2 MB at most)'),
    ('^(\\d+) pièces jointes au plus par message$', 'at most \\1 attachments per message'),
    ('^(\\d+) Mo au plus par message$', 'at most \\1 MB per message'),
    ('^le contenu ne ressemble pas à un fichier (.+)$', 'the content does not look like a \\1 file'),
    ('^envoi interrompu.*$', 'upload interrupted'),
    ('^fichier vide$', 'empty file'),
    ("^pièces jointes introuvables.*$", 'attachments not found (draft expired): attach them again'),
    ("^une pièce jointe est encore en cours d'envoi.*$", 'an attachment is still uploading: try again in a moment'),
    ("^pièces jointes impossibles à ranger.*$", 'attachments could not be stored: message not sent, try again'),
    ("^l'auditeur est désactivé.*$", 'the auditor is off (Settings)'),
    ('^périmètre : .*$', 'scope: projet, studio, version, session'),
    ('^modèle : haiku, sonnet, opus, fable ou inherit$', 'model: haiku, sonnet, opus, fable or inherit'),
    ('^effort : low, medium, high, xhigh ou max$', 'effort: low, medium, high, xhigh or max'),
    ('^rien à changer$', 'nothing to change'),
    ("^(.+) : en-tête YAML introuvable, rien n'est écrit$", '\\1: YAML header not found, nothing written'),
]


def refus_langue(msg):
    try:
        conf = lire_json(os.path.join(Etat.studio, "studio.config.json"), {}) if Etat.studio else {}
        if str((conf or {}).get("langue") or "fr")[:2].lower() == "fr":
            return msg
    except Exception:
        return msg
    for motif, rempl in REFUS_EN:
        if re.match(motif, msg):
            return re.sub(motif, rempl, msg)
    return msg


def route_reglages(d):
    f = d.get("frequence_rapport_min")
    bascules = {k: d[k] for k in ("attribution_auto", "embauche_auto", "enchainement_auto", "point_auto", "optimisation_auto", "tyrannie_auto", "mode_absent", "sante_auto", "blague", "auditeur", "controle_modeles",
                                  "quetes_actives", "quetes_secondaires", "quetes_son", "habillage_sons_ui") if k in d}
    bascules.update({k: v for k, v in d.items() if isinstance(k, str) and re.fullmatch(r"soutien\.[a-z0-9][a-z0-9-]{2,39}", k)})   # S4 : agents de soutien
    habillage = d.get("habillage_mode")
    if habillage is not None and habillage not in ("progressif", "atelier", "jeu"):
        raise Refus(400, "habillage_mode : progressif, atelier ou jeu")
    ordre = d.get("ordre_equipe")
    if ordre is not None and (not isinstance(ordre, list) or len(ordre) > 60 or any(not isinstance(x, str) or not ID_RE.match(x) for x in ordre)):
        raise Refus(400, "ordre_equipe : liste d'identifiants")
    if any(not isinstance(v, bool) for v in bascules.values()):
        raise Refus(400, "réglage marche / arrêt : true ou false")
    if f is None and not bascules and ordre is None and habillage is None:
        raise Refus(400, "aucun réglage")
    if f is not None and f not in (15, 30, 60, 120):
        raise Refus(400, "fréquence : 15, 30, 60 ou 120")
    chemin = os.path.join(Etat.studio, "reglages.json")
    r = lire_ou_mettre_de_cote(chemin, {})
    if not isinstance(r, dict):
        r = {}
    if f is not None:
        r["frequence_rapport_min"] = f
    if "mode_absent" in bascules:                 # mode nuit / absent : silence vers l'utilisateur, le studio continue
        if bascules["mode_absent"] and not r.get("mode_absent"):
            r["mode_absent_depuis"] = maintenant()
        elif not bascules["mode_absent"] and r.get("mode_absent"):
            r["absence_derniere"] = {"debut": r.get("mode_absent_depuis"), "fin": maintenant()}
            r.pop("mode_absent_depuis", None)
    if ordre is not None:
        r["ordre_equipe"] = ordre
    if habillage is not None:
        r["habillage_mode"] = habillage
    if any(v for k, v in bascules.items() if k in AUTOS_COUPER) and r.get("pause"):
        avant = r.pop("avant_pause", None)
        if isinstance(avant, dict):                        # F8 : les autres automatismes reviennent comme avant la pause
            for k, v in avant.items():
                if k in AUTOS_COUPER and k not in bascules:
                    if v is None:
                        r.pop(k, None)
                    else:
                        r[k] = bool(v)
        r["pause"] = False
        r.pop("pause_depuis", None)
    r.update(bascules, maj=maintenant())
    ecrire_json(chemin, r)
    return {"ok": True, "reglages": r}


# -------------------------------------------------------------------- transcription locale (facultative)
_MODELE, _VERROU_MODELE = None, threading.Lock()
_UNE_TRANSCRIPTION = threading.Semaphore(1)        # une transcription à la fois : la machine ne rame pas pendant le moteur


def whisper_installe():
    try:
        import importlib.util
        return importlib.util.find_spec("faster_whisper") is not None
    except Exception:
        return False


def transcrire(audio, direct=False):
    """direct=True : aperçu pendant la dictée (faisceau 1, jamais d'attente : si une transcription tourne, on passe)."""
    if not _UNE_TRANSCRIPTION.acquire(timeout=0 if direct else 20):
        if direct:
            return {"ok": True, "texte": None, "occupe": True, **_INFOS}
        raise Refus(429, "une transcription est déjà en cours : réessaie dans un instant")
    try:
        return _transcrire(audio, direct)
    finally:
        _UNE_TRANSCRIPTION.release()


def _transcrire(audio, direct=False):
    """Transcription locale avec faster-whisper si installé (pip install faster-whisper). Sinon 501."""
    try:
        from faster_whisper import WhisperModel  # noqa: import facultatif
    except ImportError:
        raise Refus(501, "transcription locale absente : installe faster-whisper (pip install faster-whisper) "
                         "ou utilise un navigateur avec reconnaissance vocale ; tu peux toujours écrire ta réponse")
    profil = lire_json(os.path.join(Etat.studio, "profil.json"), {})
    conf = lire_json(os.path.join(Etat.studio, "studio.config.json"), {})
    langue = str(((profil.get("voix") or {}).get("langue_reconnaissance") or conf.get("langue") or "fr"))[:2].lower()   # langue du projet par défaut
    t0 = time.time()
    signal, decodeur, erreurs = decoder(audio)
    if signal is None:
        raise Refus(422, "audio illisible (" + " ; ".join(erreurs)[:300] + ")")
    t_decodage = time.time() - t0
    m = modele(WhisperModel)
    t1 = time.time()
    invite = vocabulaire(conf)
    try:
        txt = _transcrire_avec(m, signal, langue, invite, direct)
    except RuntimeError as e:
        # bibliothèques CUDA absentes au moment du calcul : on repasse sur le processeur
        if not any(x in str(e).lower() for x in ("cuda", "cublas", "cudnn")):
            raise
        m = modele(WhisperModel, forcer_cpu=True)
        txt = _transcrire_avec(m, signal, langue, invite, direct)
    return {"ok": True, "texte": txt[:4000], "decodeur": decodeur, "decodage_s": round(t_decodage, 2),
            "duree_s": round(time.time() - t1, 2), "audio_s": round(len(signal) / 16000, 1), **_INFOS}


_INFOS = {}
# Phrases que Whisper invente sur du silence (« Sous-titrage ST' 501 ») : dictee_propre.est_hallucination, qui ne jette
# un segment que s'il EST une de ces phrases (avant : le mot « sous-titrage » seul jetait toute la phrase, B1 du 13/11).


def vocabulaire(conf):
    """Invite initiale de Whisper : nom du projet + mots du projet (studio.config.json « vocabulaire »). Sans elle,
    les noms propres du projet sont écrits au son (« Nanite » → « Nanny »)."""
    mots = [str(conf.get("nom_projet") or os.path.basename(Etat.projet or ""))]
    v = conf.get("vocabulaire") or []
    mots += [str(x) for x in (v if isinstance(v, list) else str(v).split(","))]
    mots += ["Claude", "studio", "roadmap", "Unreal", "Godot", "Unity", "Blender"]
    vus, out = set(), []
    for m in (x.strip() for x in mots):
        if m and m.lower() not in vus:
            vus.add(m.lower()); out.append(m)
    return (", ".join(out)[:600] + ".") if out else None


def _transcrire_avec(m, signal, langue, invite=None, direct=False):
    segments, _ = m.transcribe(signal, language=langue, beam_size=1 if direct else 5, vad_filter=True,
                               vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 300},
                               initial_prompt=invite, condition_on_previous_text=False)
    try:
        if ICI not in sys.path:
            sys.path.insert(0, ICI)
        import dictee_propre
    except Exception:
        dictee_propre = None
    morceaux = []
    for x in segments:
        t = x.text.strip()
        if not t or (x.no_speech_prob > 0.6 and x.avg_logprob < -0.8) or (dictee_propre and dictee_propre.est_hallucination(t)):
            continue
        morceaux.append(t)
    if dictee_propre is None:
        return " ".join(x for x in morceaux if x).strip()
    # segments qui se recouvrent, débuts de phrase répétés : une seule fois ; noms du projet remis à leur orthographe
    return dictee_propre.corriger_vocabulaire(dictee_propre.propre(morceaux), invite or "")


def precharger_dictee():
    """Modèle de dictée chargé et chauffé dès le démarrage s'il est déjà sur le disque (jamais de téléchargement ici) :
    le premier clic sur un micro ne paie ni le chargement ni la première passe GPU."""
    if not whisper_installe():
        return
    try:
        from faster_whisper import WhisperModel
        import numpy as np
        m = modele(WhisperModel, local_seulement=True)
        t0 = time.time()
        list(m.transcribe(np.zeros(16000, dtype=np.float32), beam_size=1)[0])
        _INFOS.update(chauffe_s=round(time.time() - t0, 2))
    except Exception:
        pass                                       # modèle absent : téléchargé à la première dictée, comme avant


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


def modele(WhisperModel, forcer_cpu=False, local_seulement=False):
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
                    _MODELE = WhisperModel(nom, device="cuda", compute_type="float16", download_root=racine, local_files_only=local_seulement)
                    _INFOS.update(appareil="cuda")
                except Exception as e:
                    _MODELE = None
                    _INFOS.update(raison_cpu=str(e)[:160])
            if _MODELE is None or forcer_cpu:
                _MODELE = WhisperModel(nom, device="cpu", compute_type="int8", download_root=racine, local_files_only=local_seulement)
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
            r = subprocess.run([ffmpeg, "-nostdin", "-loglevel", "error", "-protocol_whitelist", "pipe", "-i", "pipe:0", "-f", "f32le", "-ac", "1", "-ar", "16000", "pipe:1"],
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


def serveur_deja_la(studio, projet):
    """Port du serveur déjà lancé pour ce projet (.studio/serveur.json, vérifié par /api/qui), sinon 0."""
    d = lire_json(os.path.join(studio, "serveur.json"), {})
    try:
        port = int(d.get("port") or 0)
    except (TypeError, ValueError):
        return 0
    if not 1024 <= port <= 65535:
        return 0
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/qui", timeout=2) as r:
            q = json.loads(r.read().decode("utf-8"))
        return port if os.path.normcase(str(q.get("projet") or "")) == os.path.normcase(projet) else 0
    except Exception:
        return 0


RESEAU = {"ip": None, "cle": None}   # option --reseau (coupée par défaut) : IP locale servie aussi, clé exigée


def ip_locale():
    """IP de cette machine sur le réseau local (aucun paquet n'est envoyé)."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as so:
            so.connect(("192.168.1.1", 9))
            ip = so.getsockname()[0]
        if re.match(r"^(192\.168|10\.|172\.(1[6-9]|2\d|3[01]))\.", ip):
            return ip
    except OSError:
        pass
    return None


def cle_reseau(studio):
    import secrets
    f = os.path.join(studio, "cle_reseau.txt")
    try:
        with open(f, encoding="utf-8") as h:
            c = h.read().strip()
        if re.fullmatch(r"[0-9a-f]{32}", c):
            return c
    except OSError:
        pass
    c = secrets.token_hex(16)
    with open(f, "w", encoding="utf-8") as h:
        h.write(c + "\n")
    return c


def main(argv=None):
    ap = argparse.ArgumentParser(description="Serveur local du studio gamedev (127.0.0.1 seulement).")
    ap.add_argument("--projet", required=True, help="dossier du projet (le studio lit et écrit dans <projet>/.studio)")
    ap.add_argument("--port", type=int, default=0, help=f"port local (défaut : studio.config.json, sinon {PORT_DEFAUT} ; s'il est pris, le premier libre après)")
    ap.add_argument("--reseau", action="store_true", help="aussi sur l'IP locale (téléphone sur le Wi-Fi de la maison), avec une clé secrète exigée")
    ap.add_argument("--ip", default=None, help="IP locale à servir avec --reseau (sinon détectée)")
    a = ap.parse_args(argv)
    Etat.projet = os.path.abspath(a.projet)
    Etat.studio = os.path.join(Etat.projet, ".studio")
    os.makedirs(Etat.studio, exist_ok=True)
    conf = lire_json(os.path.join(Etat.studio, "studio.config.json"), {})
    deja = serveur_deja_la(Etat.studio, Etat.projet)
    if deja and (not a.port or a.port == deja):          # reprise : le serveur de ce projet répond déjà, on le réutilise
        print(f"studio sur http://127.0.0.1:{deja}/studio.html (projet : {Etat.projet}) : déjà lancé, réutilisé", flush=True)
        return
    try:
        port = int(conf.get("port") or PORT_DEFAUT)
    except (TypeError, ValueError):
        port = PORT_DEFAUT
    if not 1024 <= port <= 65000:
        port = PORT_DEFAUT
    if a.port:
        port = a.port
        if not port_libre(port):
            raise SystemExit(f"le port {port} est déjà pris par un autre programme (ou un autre studio) : choisis un autre --port, ou lance sans --port")
    else:
        try:                                              # F11 : reprise après un arrêt brutal : le même port que la dernière fois
            ancien = int((lire_json(os.path.join(Etat.studio, "serveur.json"), {}) or {}).get("port") or 0)
        except (TypeError, ValueError, AttributeError):
            ancien = 0
        if 1024 <= ancien <= 65535 and port_libre(ancien):
            port = ancien
        libre = next((p for p in range(port, port + 50) if port_libre(p)), 0)
        if not libre:
            raise SystemExit(f"aucun port libre entre {port} et {port + 49} : relance avec --port N")
        port = libre
    ThreadingHTTPServer.allow_reuse_address = os.name != "nt"     # Windows : SO_REUSEADDR laisserait un 2e serveur sur le même port
    srv = ThreadingHTTPServer(("127.0.0.1", port), Studio)
    srv.daemon_threads = True
    Etat.port = port
    threading.Thread(target=menage_brouillons_fond, daemon=True).start()
    print(f"studio sur http://127.0.0.1:{port}/studio.html (projet : {Etat.projet})", flush=True)
    if a.reseau:
        ip = a.ip or ip_locale()
        if not ip or not re.match(r"^(192\.168|10\.|172\.(1[6-9]|2\d|3[01]))\.\d+\.\d+$", ip):
            raise SystemExit("--reseau : adresse locale introuvable ou pas privée (préciser --ip=192.168.x.y)")
        RESEAU["ip"], RESEAU["cle"] = ip, cle_reseau(Etat.studio)
        srv_reseau = ThreadingHTTPServer((ip, port), Studio)
        srv_reseau.daemon_threads = True
        threading.Thread(target=srv_reseau.serve_forever, daemon=True).start()
        adresse = f"http://{ip}:{port}/studio.html?cle={RESEAU['cle']}"
        with open(os.path.join(Etat.studio, "adresse_telephone.txt"), "w", encoding="utf-8") as h:
            h.write(adresse + "\n")
        print(f"réseau de la maison : {ip}:{port}, clé exigée ; adresse du téléphone dans .studio/adresse_telephone.txt", flush=True)
    threading.Thread(target=precharger_dictee, daemon=True).start()   # dictée prête avant le premier clic
    info = os.path.join(Etat.studio, "serveur.json")
    try:
        ecrire_json(info, {"port": port, "pid": os.getpid(), "depuis": maintenant()})
    except Exception:
        pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        try:
            if lire_json(info, {}).get("pid") == os.getpid():
                os.remove(info)
        except OSError:
            pass


if __name__ == "__main__":
    main()
