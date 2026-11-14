"""studio/quetes.py : les quêtes du studio (paquet S4), évaluateur.

Tout au long du projet, le studio propose de petites quêtes au bon moment. Chacune propose des agents à recruter
et des skills de game dev utiles, et donne une récompense (XP, succès, objet de décor, palier d'habillage, déblocage
d'un agent de soutien et de son bouton). Rien n'est jamais lancé : accepter une quête prépare des recrues
`lancer: false` et une demande pour l'assistant, qui montre la fiche et attend l'accord.

Principes :
- Lu dans l'état réel : réponses du questionnaire, roadmap, fichiers du projet (index borné), git (lecture seule),
  analyse d'adoption, équipe (config + recrues), da.json, skills.json. Jamais « l'assistant pense que ».
- Fini vérifié par le studio : un critère de fichier, de roadmap, de git ou de da.json ; ou une preuve déposée
  (chemin) que le studio contrôle. Jamais une simple phrase.
- Au bon moment, pas en rafale : 1 principale et 2 secondaires ouvertes au plus, 30 min entre deux propositions,
  rien pendant le questionnaire (sauf Fondations), en mode absent ou la nuit, ni dans la minute d'un jalon fini.
- Projet existant : au premier passage, les quêtes déjà remplies passent à `deja_faite` (XP comptée, une seule bannière).
- Générique et bilingue : tous les textes du catalogue en fr et en.

Fichiers (tous dans <projet>/.studio/) :
  lit    : reponses_questionnaire.json, roadmap.json, studio.config.json, reglages.json, recrues/*.json,
           analyse_projet.json, da.json, skills.json, etat.json, quetes_reponses.json
  écrit  : quetes_etat.json, quetes_index.json, habillage.json, da/ (copies bornées), table_projet.json,
           demandes/<horodatage>_quete_<id>.json (acceptation), quetes_reponses.json (réponses de la page)

Ligne de commande :
  python quetes.py <projet> [--une-fois] [--json]          un passage (écrit quetes_etat.json)
  python quetes.py <projet> --expliquer <id>              pourquoi la quête est (ou n'est pas) proposée / remplie
  python quetes.py <projet> --repondre <id> <action> [--agents a,b] [--chemin x]
                                                          accepter | plus_tard | refuser | suivre | preuve
  python quetes.py --verifier-catalogue [--mots-interdits fichier]
Code de sortie : 0 ; 1 si le catalogue a une erreur ; 2 usage ; 3 refus d'une réponse.
"""
import fnmatch
import glob
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import jsonio  # noqa: E402  (C4 : lecture avec BOM, écriture atomique communes)
import style_paliers  # noqa: E402
import table_projet  # noqa: E402

CATALOGUE = os.path.join(ICI, "quetes.json")
CARTES = os.path.join(ICI, "cartes")
FAITS = ("verse", "ecart")
FAITES = ("remplie", "deja_faite")
OUVERTES = ("proposee", "acceptee")
POIDS_AV = {"verse": 1, "ecart": 1, "pret": 0.7, "en_cours": 0.35, "a_faire": 0}
OPS = ("eq", "ne", "ge", "le", "dans", "pas_dans", "contient", "existe")
ACTIONS = ("accepter", "plus_tard", "refuser", "suivre", "preuve")
NOM_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,39}$")
NB_BUREAUX = 12
# agents de soutien que la page dessine déjà (bureau dans un coin, bouton de la barre du haut) : un réglage de la page
# les active ; ils ne prennent pas de bureau de recrue. agent -> (clé de reglages.json, poste)
PAGE_SOUTIEN = {"auditeur": ("auditeur", "audit"), "controleur-modeles": ("controle_modeles", "modeles")}
INDEX_MAX_CHEMINS = 2000      # par passage (repris au suivant)
INDEX_MAX_S = 2.0
INDEX_TOTAL_MAX = 60000
EXCLUS_DOSSIERS = {".studio", ".git", "node_modules", "addons", "plugins", "library", "intermediate", "saved", ".godot",
                   "__pycache__", ".import", "deriveddatacache", ".vs", ".idea", ".venv", "venv"}
EXT = {"image": "png,jpg,jpeg,webp,svg", "police": "ttf,otf,woff,woff2", "audio": "ogg,wav,mp3,flac"}
SCENES = {"godot": "tscn,scn", "unity": "unity,prefab", "unreal": "umap,uasset", "phaser": "html,js,ts,json",
          "threejs": "html,js,ts,json", "pixijs": "html,js,ts,json", "web": "html,js,ts,json", "bevy": "rs,ron"}
CODE_EXT = (".gd", ".cs", ".cpp", ".h", ".hpp", ".py", ".js", ".ts", ".rs", ".lua", ".luau", ".tscn", ".gdshader", ".java", ".kt")
PREUVE_TYPES = {"image": (".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"), "doc": (".md", ".txt", ".pdf", ".odt", ".docx", ".html"),
                "scene": None, "export": (".exe", ".pck", ".apk", ".aab", ".zip", ".app", ".wasm", ".html", ".dmg", ".appimage")}
DEFAUTS = {"quetes_actives": True, "quetes_secondaires": True, "quetes_frequence_min": 30, "quetes_max_ouvertes": 3,
           "quetes_son": True, "habillage_mode": "progressif", "habillage_sons_ui": False}
SUBPROC = {"capture_output": True, "text": True, "timeout": 20, "encoding": "utf-8", "errors": "replace"}
# Skills reconnus par la vérification du catalogue (en plus de ceux cités dans references/routage_skills.md)
SKILLS_CONNUS = set("""
gamedev:router gamedev:godot-gdscript gamedev:godot-nodes-scenes gamedev:godot-signals-groups gamedev:godot-2d-movement
gamedev:godot-tilemap gamedev:godot-physics gamedev:godot-ui-control gamedev:godot-animation gamedev:godot-shaders
gamedev:godot-3d-essentials gamedev:godot-resources gamedev:godot-audio gamedev:godot-multiplayer gamedev:godot-export
gamedev:godot-csharp gamedev:godot-gdscript-headless-testing gamedev:unity-csharp-scripting gamedev:unity-input-system
gamedev:unity-physics gamedev:unity-animation gamedev:unity-scriptableobjects gamedev:unity-tilemap-2d gamedev:unity-navmesh
gamedev:unity-build-pipeline gamedev:unreal-blueprints gamedev:unreal-cpp-gameplay gamedev:unreal-enhanced-input
gamedev:unreal-behavior-trees gamedev:unreal-niagara gamedev:unreal-packaging gamedev:ebitengine-game gamedev:phaser-core
gamedev:phaser-arcade-physics gamedev:pixijs-rendering gamedev:threejs-scene-setup gamedev:threejs-gltf-loading
gamedev:threejs-materials-lighting gamedev:bevy-ecs gamedev:pygame-core gamedev:love2d-core gamedev:defold-core
gamedev:roblox-luau gamedev:roblox-datastores gamedev:roblox-ui gamedev:roblox-networking gamedev:roblox-characters
gamedev:roblox-physics gamedev:roblox-studio-workflow gamedev:roblox-simulator-economy gamedev:create-game-assets
gamedev:game-ai gamedev:procedural-gen gamedev:dialogue-systems gamedev:save-systems gamedev:audio-design
gamedev:shader-programming gamedev:physics-tuning gamedev:level-design gamedev:input-systems gamedev:game-feel
gamedev:game-ui-ux gamedev:camera-systems gamedev:performance-optimization gamedev:ai-behavior-trees-utility-ai
gamedev:platformer gamedev:roguelike gamedev:rpg gamedev:fps-shooter gamedev:tower-defense gamedev:card-game
gamedev:visual-novel gamedev:survival-crafting gamedev:puzzle gamedev:game-jam gamedev:prototype-fast
gamedev:steam-publish gamedev:itch-publish
ecc:blueprint ecc:git-workflow ecc:tdd-workflow ecc:verification-loop ecc:code-review ecc:harness-audit ecc:model-route
ecc:cost-tracking ecc:token-budget-advisor ecc:i18n-sync ecc:accessibility ecc:csharp-testing ecc:cpp-testing
ecc:rust-testing ecc:python-testing ecc:e2e-testing ecc:security-review ecc:video-editing
""".split())


# ------------------------------------------------------------------ outils
def lire_json(chemin, defaut):
    return jsonio.lire(chemin, defaut)              # un fichier fautif ne bloque jamais le studio


def ecrire_json(chemin, donnees):
    jsonio.ecrire(chemin, donnees, newline="\n")


def lire_protege(chemin, defaut):
    """Pour un fichier qu'on va réécrire : absent → defaut ; illisible → 3 nouvelles lectures (écriture en cours ?) ;
    toujours illisible → copie <nom>.corrompu-<date>.json gardée (jamais écrasée), puis defaut. L'historique n'est jamais perdu."""
    if not os.path.exists(chemin):
        return defaut
    for essai in range(4):
        try:
            return jsonio.lire_strict(chemin)
        except FileNotFoundError:
            return defaut
        except (OSError, ValueError):
            time.sleep(.1 * (essai + 1))
    base, ext = os.path.splitext(chemin)
    t = time.time()
    for i in range(50):
        cible = f"{base}.corrompu-{time.strftime('%Y%m%d-%H%M%S', time.localtime(t))}{'-%d' % i if i else ''}{ext}"
        if not os.path.exists(cible):
            try:
                os.replace(chemin, cible)
            except OSError:                             # fichier verrouillé : une copie suffit ; sans copie, rien n'est écrasé
                try:
                    shutil.copyfile(chemin, cible)
                except OSError:
                    break
            return defaut
    raise Refus(503, f"{os.path.basename(chemin)} illisible et impossible à mettre de côté : rien n'est écrit")


def numero(r, position):
    """Numéro croissant d'une réponse (champ n) ; une réponse ancienne sans n garde sa position (1, 2, 3…)."""
    n = r.get("n") if isinstance(r, dict) else None
    return n if isinstance(n, int) and not isinstance(n, bool) else position + 1


def creer_demande(dossier, suffixe, donnees, t):
    """Demande au nom unique (horodatage, millisecondes + code au hasard) avec son champ id, créée en mode exclusif : jamais
    d'écrasement, jamais lue à moitié écrite (nom caché .<id>.tmp puis renommage). Même forme que creer_unique du serveur."""
    os.makedirs(dossier, exist_ok=True)
    for _ in range(20):
        ident = time.strftime("%Y%m%d-%H%M%S", time.localtime(t)) + f"-{int(t * 1000) % 1000:03d}{os.urandom(2).hex()}_{suffixe}"
        chemin = os.path.join(dossier, ident + ".json")
        if os.path.exists(chemin):
            continue
        tmp = os.path.join(dossier, "." + ident + ".tmp")
        try:
            with open(tmp, "x", encoding="utf-8", newline="\n") as f:
                json.dump(dict(donnees, id=ident), f, ensure_ascii=False, indent=1)
            if os.path.exists(chemin):
                raise FileExistsError(chemin)
            os.rename(tmp, chemin)
            return ident
        except FileExistsError:
            try:
                os.remove(tmp)
            except OSError:
                pass
            continue
        except BaseException:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise
    raise OSError("impossible de créer une demande au nom unique")


def iso(t):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t))


def iso_vers_t(s):
    try:
        return time.mktime(time.strptime(str(s)[:10], "%Y-%m-%d"))
    except (ValueError, TypeError, OverflowError):
        return None


def charger_catalogue(chemin=CATALOGUE):
    c = lire_json(chemin, None)
    if not isinstance(c, dict) or not isinstance(c.get("quetes"), list):
        raise ValueError(f"catalogue illisible : {chemin}")
    c["_par_id"] = {q["id"]: q for q in c["quetes"]}
    return c


def texte(t, langue):
    return t.get(langue) or t.get("fr") if isinstance(t, dict) else t


def conditions(o):
    if isinstance(o, dict):
        if "signal" in o:
            yield o
        for v in o.values():
            yield from conditions(v)
    elif isinstance(o, list):
        for v in o:
            yield from conditions(v)


# ------------------------------------------------------------------ index des fichiers du projet (borné, repris)
class Index:
    """Parcours borné du projet : 2 000 chemins ou 2 s par passage ; repris au passage suivant.
    Les dossiers générés et .studio/ sont exclus ; build*/ est indexé mais réservé aux motifs qui le nomment."""

    def __init__(self, projet):
        self.projet = projet
        self.chemin = os.path.join(projet, ".studio", "quetes_index.json")
        d = lire_json(self.chemin, {})
        self.fichiers = d.get("fichiers") if isinstance(d.get("fichiers"), list) else []
        self.complet_t = d.get("complet_t")
        self.en_cours = d.get("en_cours") if isinstance(d.get("en_cours"), dict) else None
        self.systemes = d.get("systemes") if isinstance(d.get("systemes"), dict) else {}
        self.vient_de_finir = False

    def avancer(self, maintenant, max_chemins=INDEX_MAX_CHEMINS, max_s=INDEX_MAX_S, frais_s=55):
        if self.en_cours is None:
            if self.complet_t and maintenant - self.complet_t < frais_s:
                return
            self.en_cours = {"pile": [""], "trouves": []}
        pile, trouves = self.en_cours["pile"], self.en_cours["trouves"]
        debut, vus = time.perf_counter(), 0
        while pile and vus < max_chemins and time.perf_counter() - debut < max_s and len(trouves) < INDEX_TOTAL_MAX:
            rel = pile.pop()
            try:
                with os.scandir(os.path.join(self.projet, rel) if rel else self.projet) as it:
                    for e in it:
                        vus += 1
                        r = (rel + "/" + e.name) if rel else e.name
                        try:
                            if e.is_symlink():
                                continue
                            if e.is_dir():
                                if e.name.lower() not in EXCLUS_DOSSIERS:
                                    pile.append(r)
                            elif e.is_file():
                                trouves.append(r)
                        except OSError:
                            continue
            except OSError:
                continue
        if not pile or len(trouves) >= INDEX_TOTAL_MAX:
            self.fichiers, self.complet_t, self.en_cours = sorted(trouves), maintenant, None
            self.vient_de_finir = True

    @property
    def complet(self):
        return self.complet_t is not None and self.en_cours is None

    def tous(self):
        if self.en_cours and self.fichiers:
            return sorted(set(self.fichiers) | set(self.en_cours["trouves"]))
        return self.fichiers or (self.en_cours or {}).get("trouves", [])

    def sauver(self):
        ecrire_json(self.chemin, {"version": 1, "complet_t": self.complet_t, "fichiers": self.fichiers,
                                  "en_cours": self.en_cours, "systemes": self.systemes})


def motif_regex(motif, moteur):
    m = motif.replace("{scene}", "{" + SCENES.get(moteur, "*") + "}")
    for k, v in EXT.items():
        m = m.replace("{" + k + "}", "{" + v + "}")
    out, i, prof = [], 0, 0
    while i < len(m):
        c = m[i]
        if m.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
            continue
        if m.startswith("**", i):
            out.append(".*")
            i += 2
            continue
        if c == "*":
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        elif c == "{":
            prof += 1
            out.append("(?:")
        elif c == "}" and prof:
            prof -= 1
            out.append(")")
        elif c == "," and prof:
            out.append("|")
        else:
            out.append(re.escape(c))
        i += 1
    return re.compile("".join(out) + r"\Z", re.I)


def sous_build(rel):
    return any(p.lower().startswith("build") for p in rel.split("/")[:-1])


# ------------------------------------------------------------------ contexte d'un passage : tout ce qui est lu
class Contexte:
    def __init__(self, projet, catalogue, maintenant, etat, index):
        self.projet, self.cat, self.t, self.etat, self.index = projet, catalogue, maintenant, etat, index
        self.st = os.path.join(projet, ".studio")
        self._cache, self._motifs = {}, {}
        rq = lire_json(os.path.join(self.st, "reponses_questionnaire.json"), {})
        self.rq = rq if isinstance(rq, dict) else {}
        self.reponses = self.rq.get("reponses") if isinstance(self.rq.get("reponses"), dict) else {}
        self.conf = lire_json(os.path.join(self.st, "studio.config.json"), {})
        if not isinstance(self.conf, dict):
            self.conf = {}
        self.roadmap = self._roadmap()
        self.da, self.da_problemes = style_paliers.lire_da(projet)
        m = self.conf.get("moteur") if isinstance(self.conf.get("moteur"), dict) else {}
        self.moteur = str(m.get("nom") or self.reponse("moteur.nom") or "").lower()
        self.langue = str(self.conf.get("langue") or self.rq.get("langue") or "fr")[:2]
        self.fichiers = index.tous()

    # ---- sources
    def reponse(self, cle):
        r = self.reponses.get(cle)
        return r.get("valeur") if isinstance(r, dict) else r

    def _roadmap(self):
        r = lire_json(os.path.join(self.st, "roadmap.json"), None)
        if not isinstance(r, dict) or not isinstance(r.get("jalons"), list):
            return None
        jal = []
        for j in r["jalons"]:
            if isinstance(j, dict) and j.get("id"):
                j = dict(j, taches=[t for t in (j.get("taches") if isinstance(j.get("taches"), list) else []) if isinstance(t, dict) and t.get("id")])
                jal.append(j)
        r["jalons"] = jal
        return r if any(j["taches"] for j in jal) else None

    def jalons_hors_j0(self):
        return [j for j in (self.roadmap or {}).get("jalons", []) if str(j["id"]).upper() != "J0"]

    def taches(self):
        return [t for j in (self.roadmap or {}).get("jalons", []) for t in j["taches"]]

    def pct_roadmap(self):
        tot = av = 0.0
        for t in self.taches():
            st = t.get("statut") if t.get("statut") in POIDS_AV else "a_faire"
            h = t.get("estimation_h") if isinstance(t.get("estimation_h"), (int, float)) and not isinstance(t.get("estimation_h"), bool) else 0
            w = h if h > 0 else 1
            tot += w
            av += w * POIDS_AV[st]
        return round(100 * av / tot, 1) if tot else 0.0

    def jalons_finis(self):
        return sum(1 for j in self.jalons_hors_j0() if j["taches"] and all(t.get("statut") in FAITS for t in j["taches"]))

    def xp_roadmap(self):
        r = self.roadmap or {}
        reg = r.get("niveau") if isinstance(r.get("niveau"), dict) else {}
        xt = reg.get("xp_par_tache", 100) if isinstance(reg.get("xp_par_tache"), (int, float)) else 100
        xj = reg.get("xp_par_jalon", 500) if isinstance(reg.get("xp_par_jalon"), (int, float)) else 500
        faites = sum(1 for t in self.taches() if t.get("statut") in FAITS)
        fermes = sum(1 for j in r.get("jalons", []) if j["taches"] and all(t.get("statut") in FAITS for t in j["taches"]))
        return int(faites * xt + fermes * xj)

    def equipe(self):
        if "equipe" not in self._cache:
            out = []
            for p in self.conf.get("postes") or []:
                if isinstance(p, dict) and p.get("id"):
                    out.append({"nom": str(p["id"]), "poste": str(p.get("poste") or p.get("metier") or p["id"]),
                                "skills": [s for s in (p.get("skills") or []) if isinstance(s, str)], "source": "config"})
            for f in glob.glob(os.path.join(glob.escape(self.st), "recrues", "*.json")):
                if os.path.basename(f) == "index.json":
                    continue
                r = lire_json(f, None)
                if isinstance(r, dict) and r.get("nom"):
                    out.append({"nom": str(r["nom"]), "poste": str(r.get("poste") or ""), "skills": [s for s in (r.get("skills") or []) if isinstance(s, str)],
                                "source": "recrue"})
            page = lire_json(os.path.join(self.st, "reglages.json"), {})
            for agent, (cle, poste) in PAGE_SOUTIEN.items():
                if isinstance(page, dict) and page.get(cle) is True and not any(x["nom"] == agent for x in out):
                    out.append({"nom": agent, "poste": poste, "skills": [], "source": "reglage"})
            self._cache["equipe"] = out
        return self._cache["equipe"]

    def git(self, *a):
        if not os.path.isdir(os.path.join(self.projet, ".git")):
            return None
        cle = ("git",) + a
        if cle not in self._cache:
            env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0",
                       GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="core.fsmonitor", GIT_CONFIG_VALUE_0="false")
            try:
                r = subprocess.run(["git", "-C", self.projet, *a], env=env, **SUBPROC)
                self._cache[cle] = r.stdout.strip() if r.returncode == 0 else ""
            except Exception:  # noqa
                self._cache[cle] = ""
        return self._cache[cle]

    def correspond(self, motifs):
        """Fichiers du projet qui collent à un des motifs (glob, {scene}, {image}, {police}, {audio})."""
        res = []
        for m in motifs:
            cle = (m, self.moteur)
            if cle not in self._motifs:
                rx = motif_regex(m, self.moteur)
                build = m.lower().startswith("build")
                self._motifs[cle] = [f for f in self.fichiers if rx.match(f) and (build or not sous_build(f))]
            res += [f for f in self._motifs[cle] if f not in res]
        return res

    def systemes(self):
        if "systemes" not in self._cache:
            s = {}
            a = lire_json(os.path.join(self.st, "analyse_projet.json"), {})
            for x in (a.get("systemes") if isinstance(a, dict) else None) or []:
                if isinstance(x, dict) and x.get("id"):
                    s[x["id"]] = x.get("preuve") or "analyse_projet.json"
            for k, v in (self.index.systemes or {}).items():
                s.setdefault(k, v)
            self._cache["systemes"] = s
        return self._cache["systemes"]

    def skills_installes(self):
        d = lire_json(os.path.join(self.st, "skills.json"), None)
        return set(d.get("installes") or []) if isinstance(d, dict) else None

    def mode_projet(self):
        if self.rq.get("mode") == "adoption" or os.path.isfile(os.path.join(self.st, "analyse_projet.json")):
            return "adoption"
        return "nouveau"

    # ---- signaux : (valeur, preuve)
    def signal(self, c):
        s = c["signal"]
        if s == "questionnaire":
            return self.rq.get("etat") or "absent", None
        if s == "reponse":
            return self.reponse(c.get("cle")), ".studio/reponses_questionnaire.json"
        if s == "mode_projet":
            return self.mode_projet(), None
        if s == "roadmap.existe":
            return self.roadmap is not None, ".studio/roadmap.json" if self.roadmap else None
        if s == "roadmap.pct":
            return self.pct_roadmap(), ".studio/roadmap.json"
        if s == "roadmap.jalon_pct":
            jal = self.jalons_hors_j0()
            j = next((x for x in jal if x["id"] == c.get("id")), None) if c.get("id") else (jal[c.get("rang", 1) - 1] if 0 < c.get("rang", 1) <= len(jal) else None)
            if not j or not j["taches"]:
                return 0, None
            return round(100 * sum(1 for t in j["taches"] if t.get("statut") in FAITS) / len(j["taches"])), f"roadmap {j['id']}"
        if s == "roadmap.jalons_finis":
            return self.jalons_finis(), ".studio/roadmap.json"
        if s == "roadmap.tag":
            ts = [t for t in self.taches() if c.get("tag") in (t.get("tags") or [])]
            faites = [t for t in ts if t.get("statut") in FAITS]
            mesure = c.get("mesure", "verse")
            v = len(ts) if mesure == "existe" else len(faites) if mesure == "verse" else (round(100 * len(faites) / len(ts)) if ts else 0)
            return v, ("tâche " + faites[0]["id"]) if faites else None
        if s == "fichier":
            f = self.correspond(c.get("motifs") or [])
            return len(f), (f[0] if f else None)
        if s == "fichier_contient":
            mots = [str(m).lower() for m in c.get("mots") or []]
            for f in self.correspond(c.get("motifs") or [])[:200]:
                ch = os.path.join(self.projet, *f.split("/"))
                try:
                    if os.path.getsize(ch) > 256 * 1024:
                        continue
                    with open(ch, encoding="utf-8", errors="replace") as h:
                        txt = h.read().lower()
                except OSError:
                    continue
                if any(m in txt for m in mots):
                    return True, f
            return False, None
        if s == "doc_section":
            ch = os.path.join(self.projet, *str(c.get("fichier", "")).split("/"))
            try:
                with open(ch, encoding="utf-8", errors="replace") as h:
                    ok = any(l.startswith("#") and str(c.get("titre", "")).lower() in l.lower() for l in h.read(512 * 1024).splitlines())
            except OSError:
                ok = False
            return ok, c.get("fichier") if ok else None
        if s == "git.depot":
            return os.path.isdir(os.path.join(self.projet, ".git")), ".git" if os.path.isdir(os.path.join(self.projet, ".git")) else None
        if s == "git.commits":
            n = self.git("rev-list", "--count", "HEAD")
            n = int(n) if n and n.isdigit() else 0
            return n, ("commit " + self.git("rev-parse", "--short", "HEAD")) if n else None
        if s == "git.tag":
            tags = [t for t in (self.git("tag", "-l") or "").splitlines() if fnmatch.fnmatchcase(t, c.get("motif", "*"))]
            return len(tags), ("tag " + tags[0]) if tags else None
        if s == "systeme":
            p = self.systemes().get(c.get("id"))
            return bool(p), p
        if s == "equipe":
            eq = self.equipe()
            if c.get("poste"):
                l = [a for a in eq if c["poste"] in (a["poste"], a["nom"])]
            elif c.get("skill"):
                l = [a for a in eq if c["skill"] in a["skills"]]
            else:
                l = eq
            return len(l), ("agent " + l[0]["nom"]) if l else None
        if s == "da":
            ch = c.get("champ", "")
            if ch == "valide_par_utilisateur":
                v = style_paliers.da_valide(self.da)
            elif ch == "source":
                v = bool(self.da and self.da.get("source"))
            else:
                v = bool(style_paliers.da_valide(self.da) and style_paliers.champ(self.da, ch))
            return v, (".studio/da.json#" + ch) if v else None
        if s == "habillage":
            return (self.etat.get("habillage") or {}).get("palier", 1), None
        if s == "quete":
            return (self.etat["quetes"].get(c.get("id")) or {}).get("statut", "cachee"), None
        if s == "niveau":
            return self.etat.get("niveau", 1), None
        if s == "skill_installe":
            inst = self.skills_installes()
            v = bool(inst and c.get("nom") in inst)
            return v, ".studio/skills.json" if v else None
        if s == "jours":
            d = iso_vers_t(((self.roadmap or {}).get("rythme") or {}).get("debut"))
            return int((self.t - d) // 86400) if d else 0, None
        if s == "hote":                                  # hôte du studio créé par l'utilisateur (hote.py, .studio/hote.json)
            h = lire_json(os.path.join(self.st, "hote.json"), None)
            v = isinstance(h, dict) and bool(str(h.get("nom") or "").strip()) and isinstance(h.get("activites"), list)
            return v, ".studio/hote.json" if v else None
        if s == "mur.images":
            e = lire_json(os.path.join(self.st, "etat.json"), {})
            imgs = e.get("images") if isinstance(e, dict) else None
            return len(imgs) if isinstance(imgs, list) else len(self.correspond(["**/*.{image}"])), None
        raise ValueError(f"signal inconnu : {s}")


def comparer(op, v, ref):
    if op == "existe":
        return v not in (None, False, 0, "", [], {}, "absent")
    if op == "eq":
        return v == ref
    if op == "ne":
        return v != ref
    if op in ("ge", "le"):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            v = int(bool(v)) if isinstance(v, bool) else 0
        return v >= ref if op == "ge" else v <= ref
    if op == "dans":
        return (v in ref) if not isinstance(v, list) else any(x in ref for x in v)
    if op == "pas_dans":
        return (v not in ref) if not isinstance(v, list) else not any(x in ref for x in v)
    if op == "contient":
        return isinstance(v, (list, str)) and ref in v
    raise ValueError(f"opérateur inconnu : {op}")


def evaluer(noeud, ctx, trace=None, preuves=None):
    """Vrai/faux d'une condition (tous, un_de, aucun, feuille). trace et preuves se remplissent au passage."""
    trace = [] if trace is None else trace
    preuves = [] if preuves is None else preuves
    if noeud is None:
        return True
    if "signal" in noeud:
        v, p = ctx.signal(noeud)
        ok = comparer(noeud.get("op", "existe"), v, noeud.get("valeur"))
        trace.append({"signal": noeud["signal"], "parametres": {k: x for k, x in noeud.items() if k not in ("signal", "op", "valeur")},
                      "lu": v, "op": noeud.get("op", "existe"), "attendu": noeud.get("valeur"), "ok": ok})
        if ok and p:
            preuves.append(p)
        return ok
    if "tous" in noeud:
        return all([evaluer(x, ctx, trace, preuves) for x in noeud["tous"]])
    if "un_de" in noeud:
        return any([evaluer(x, ctx, trace, preuves) for x in noeud["un_de"]])
    if "aucun" in noeud:
        return not any([evaluer(x, ctx, trace, preuves) for x in noeud["aucun"]])
    raise ValueError(f"condition sans signal ni combinaison : {noeud}")


# ------------------------------------------------------------------ réglages
def reglages(projet):
    st = os.path.join(projet, ".studio")
    conf = lire_json(os.path.join(st, "studio.config.json"), {})
    r = dict(DEFAUTS)
    if isinstance(conf, dict) and isinstance(conf.get("quetes"), dict):
        r.update({k: v for k, v in conf["quetes"].items() if k in DEFAUTS or k == "soutien"})
    page = lire_json(os.path.join(st, "reglages.json"), {})
    if isinstance(page, dict):
        r.update({k: v for k, v in page.items() if k in DEFAUTS or k in ("soutien", "mode_absent", "mode_nuit")})
        for k, v in page.items():
            if k.startswith("soutien.") and isinstance(v, bool):
                r.setdefault("soutien", {})
                r["soutien"] = dict(r["soutien"], **{k[8:]: v})
        for agent, (cle, _poste) in PAGE_SOUTIEN.items():
            if page.get(cle) is False:                       # coupé dans les Réglages de la page : son bouton disparaît
                r.setdefault("soutien", {})
                r["soutien"] = dict(r["soutien"], **{agent: False})
    if not isinstance(r.get("soutien"), dict):
        r["soutien"] = {}
    return r


# ------------------------------------------------------------------ le passage
def etat_vide():
    return {"version": 1, "maj": None, "premier_passage": None, "quetes": {}, "xp": 0, "xp_quetes": 0, "xp_actes": 0,
            "niveau": 1, "habillage": {"palier": 1, "mode": "progressif", "ajustements": []}, "suivie": None,
            "derniere_proposition_t": None, "prochaine_proposition": None, "annonces": [], "deblocages": {"boutons": [], "agents": []},
            "actes_finis": [], "jalons_finis": 0, "fete_jusqu_a": 0, "reponses_lues": 0}


def annonce(etat, t, type_, **k):
    n = len(etat["annonces"]) and etat["annonces"][-1].get("n", 0) + 1 or 1
    etat["annonces"].append(dict({"n": n, "type": type_, "t": int(t), "le": iso(t)}, **k))
    etat["annonces"] = etat["annonces"][-40:]


def est_fichier(p):
    return isinstance(p, str) and bool(p) and not p.startswith(("commit ", "tag ", "tâche ", "agent ", "roadmap ", ".studio/da.json#"))         and p not in ("analyse_projet.json", ".git")


def preuve_deposee(projet, chemin, type_):
    """Le chemin est dans le projet, existe et colle au type attendu. (ok, raison)"""
    reel = style_paliers.chemin_sur(projet, chemin)
    if not reel:
        return False, "chemin hors du projet, absent ou refusé"
    exts = PREUVE_TYPES.get(type_ or "", None)
    if type_ == "scene":
        exts = tuple("." + e for v in SCENES.values() for e in v.split(","))
    if exts and not reel.lower().endswith(exts):
        return False, f"type attendu : {type_}"
    return True, ""


def appliquer_reponses(projet, etat, cat, t, jalons_finis):
    rep = lire_json(os.path.join(projet, ".studio", "quetes_reponses.json"), [])
    if not isinstance(rep, list):
        return
    # Curseur = numéro de la dernière réponse appliquée (champ n), plus la position : la liste est coupée à 500 et une
    # position resterait bloquée à 500 pour toujours. Un état ancien sans « reponse_n » reprend sa position lue.
    cur = etat.get("reponse_n")
    if not isinstance(cur, int) or isinstance(cur, bool):
        cur = etat.get("reponses_lues") if isinstance(etat.get("reponses_lues"), int) else 0
    nums = [numero(r, i) for i, r in enumerate(rep)]
    if nums and max(nums) < cur:                        # fichier remis à zéro à la main : tout est relu
        cur = 0
    etat["reponse_n"] = etat["reponses_lues"] = cur
    for n, r in zip(nums, rep):
        if n <= cur:
            continue
        cur = n
        etat["reponse_n"] = etat["reponses_lues"] = cur
        if not isinstance(r, dict) or r.get("id") not in cat["_par_id"]:
            continue
        q, e = cat["_par_id"][r["id"]], etat["quetes"].setdefault(r["id"], {"statut": "cachee"})
        a = r.get("action")
        if a == "suivre":
            etat["suivie"] = r["id"]
        elif a == "accepter" and e["statut"] in ("proposee", "plus_tard"):
            e.update(statut="acceptee", accepte_t=int(t), accepte_le=iso(t), agents_acceptes=r.get("agents") or [])
            etat["suivie"] = etat["suivie"] or r["id"]
        elif a == "plus_tard" and e["statut"] in OUVERTES:
            e.update(statut="plus_tard", retour_t=int(t + 3600 * cat.get("rythme", {}).get("plus_tard_h", 24)), jalons_au_report=jalons_finis)
        elif a == "refuser" and e["statut"] in OUVERTES + ("plus_tard",) and (q["type"] != "principale" or e.get("rattrapage")):
            e.update(statut="refusee", refuse_t=int(t), si_au_refus=True)
        elif a == "preuve" and e["statut"] not in FAITES:
            ok, raison = preuve_deposee(projet, r.get("chemin"), q.get("preuve_type"))
            if ok:
                e["preuve_deposee"] = str(r["chemin"]).replace("\\", "/")
            else:
                e["preuve_refusee"] = raison


def resoudre_propositions(q, ctx, cat):
    """Agents (recruter / confier / bureaux pleins), skills (installé ou à installer), tâche (déjà dans la roadmap ?)."""
    eq = ctx.equipe()
    nb = len(eq)
    inst = ctx.skills_installes()
    agents = []
    for a in q["propositions"].get("agents", []):
        fiche = cat["agents"].get(a["agent"], {})
        meme = next((x for x in eq if x["nom"] == a["agent"]), None) or next((x for x in eq if x["poste"] == fiche.get("poste") and not fiche.get("soutien")), None)
        d = {"agent": a["agent"], "nom_affiche": fiche.get("nom_affiche"), "poste": fiche.get("poste"), "role": fiche.get("role"),
             "mission": a.get("mission"), "skills": fiche.get("skills", [])}
        if a["agent"] in PAGE_SOUTIEN:
            d.update(action="activer", reglage=PAGE_SOUTIEN[a["agent"]][0], deja_actif=bool(meme))
        elif meme:
            d.update(action="confier", confier_a=meme["nom"])
        elif nb >= NB_BUREAUX:
            d.update(action="bureaux_pleins")
        else:
            d.update(action="recruter", corps_recruter={
                "nom": a["agent"], "nom_affiche": texte(fiche.get("nom_affiche", {}), ctx.langue), "role": texte(fiche.get("role", {}), ctx.langue),
                "mission": texte(a.get("mission", {}), ctx.langue), "poste": fiche.get("poste", ""), "skills": fiche.get("skills", [])[:12],
                "lancer": False, "via": "ecrit"})
        agents.append(d)
    noms = list(q["propositions"].get("skills", []))
    for a in agents:
        noms += [s for s in a["skills"] if s not in noms]
    noms += [s for s in (q["propositions"].get("skills_par_moteur") or {}).get(ctx.moteur, []) if s not in noms]
    noms += [s for s in (q["propositions"].get("skills_par_genre") or {}).get(ctx.reponse("genre.principal"), []) if s not in noms]
    skills = [{"nom": s, "installe": (s in inst) if inst is not None else None} for s in noms[:12]]
    tache = q["propositions"].get("tache")
    if tache:
        tags = set(tache.get("tags") or [])
        tache = dict(tache, deja_dans_roadmap=any(tags & set(t.get("tags") or []) for t in ctx.taches()))
    return {"agents": agents, "skills": skills, "tache": tache}


def deblocages(etat, cat, ctx, regl):
    out = {"boutons": [], "agents": []}
    eq = ctx.equipe()
    for qid, e in etat["quetes"].items():
        q = cat["_par_id"].get(qid)
        if not q or e.get("statut") not in FAITES or not q["recompense"].get("deblocage"):
            continue
        d = q["recompense"]["deblocage"]
        poste = cat["agents"].get(d["agent"], {}).get("poste")
        embauche = any(a["nom"] == d["agent"] or (poste and a["poste"] == poste) for a in eq)
        actif = regl["soutien"].get(d["agent"], True) is not False
        out["agents"].append({"agent": d["agent"], "quete": qid, "bureau": d.get("bureau", "coin"), "embauche": embauche,
                              "actif": actif, "reglage": d.get("reglage"), "bouton": d.get("bouton")})
        if d.get("bouton") and embauche and actif:
            b = dict(cat.get("deblocages", {}).get("boutons", {}).get(d["bouton"], {}), id=d["bouton"])
            out["boutons"].append(b)
    return out


def ordre_actes(cat):
    return {a["id"]: i for i, a in enumerate(cat.get("actes", []))}


def passe(projet, maintenant=None, catalogue=None, absent=False, nuit=False, index_complet=False, ecrire=True):
    """Un passage complet. Rend l'état (aussi écrit dans .studio/quetes_etat.json)."""
    t = time.time() if maintenant is None else maintenant
    cat = catalogue or charger_catalogue()
    st = os.path.join(projet, ".studio")
    etat = lire_json(os.path.join(st, "quetes_etat.json"), None)
    if not isinstance(etat, dict) or not isinstance(etat.get("quetes"), dict):
        etat = etat_vide()
    for k, v in etat_vide().items():
        etat.setdefault(k, v)
    regl = reglages(projet)
    absent = absent or regl.get("mode_absent") is True
    nuit = nuit or regl.get("mode_nuit") is True

    idx = Index(projet)
    idx.avancer(t)
    while index_complet and not idx.complet:
        idx.avancer(t, max_chemins=10 ** 9, max_s=60)
    if idx.vient_de_finir:
        idx.systemes = detecter_systemes(projet, idx.fichiers)
    ctx = Contexte(projet, cat, t, etat, idx)
    jf = ctx.jalons_finis()
    appliquer_reponses(projet, etat, cat, t, jf)

    premier = etat["premier_passage"] is None
    if premier and not idx.complet:          # premier passage : on attend l'index complet (pas de fanfare à tort)
        if ecrire:
            idx.sauver()
            ecrire_json(os.path.join(st, "quetes_etat.json"), dict(etat, maj=iso(t), index_partiel=True))
        return etat
    if jf > etat.get("jalons_finis", 0):
        etat["fete_jusqu_a"] = int(t + 60)
    etat["jalons_finis"] = jf

    # 1. existence, fini, preuves
    nouvelles = []
    for q in sorted(cat["quetes"], key=lambda x: x["ordre"]):
        e = etat["quetes"].setdefault(q["id"], {"statut": "cachee"})
        si = evaluer(q.get("si"), ctx)
        if q["type"] == "secondaire" and regl.get("quetes_secondaires") is False and e["statut"] not in FAITES:
            si = False
        e["existe"] = si
        if e["statut"] == "refusee":
            if not si:
                e["si_au_refus"] = False
            elif e.get("si_au_refus") is False:
                e["statut"] = "cachee"        # son « si » a changé : elle peut revenir
        if e["statut"] in FAITES:
            p = e.get("preuve")
            if est_fichier(p):          # une preuve qui disparaît ne retire rien : on le signale seulement
                e["preuve_introuvable"] = not os.path.exists(os.path.join(projet, *p.split("/")))
            continue
        if not si:
            continue
        preuves = []
        fini = evaluer(q["fini"], ctx, [], preuves)
        if not fini and e.get("preuve_deposee"):
            fini, preuves = True, [e["preuve_deposee"]]
        if fini:
            e.update(statut="deja_faite" if premier else "remplie", remplie_t=int(t), remplie_le=iso(t),
                     preuve=preuves[0] if preuves else None)
            e.pop("preuve_refusee", None)
            nouvelles.append(q)

    # 2. récompenses : XP, succès, actes finis
    for q in nouvelles:
        r = q["recompense"]
        if premier:
            continue
        annonce(etat, t, "quete_remplie", quete=q["id"], titre=r["succes"]["titre"], icone=r["succes"]["icone"],
                son=r["succes"].get("son", "moyen"), xp=r["xp"], decor=r.get("decor"), habillage=r.get("habillage"),
                deblocage=r.get("deblocage"), titre_maitre=r.get("titre"), proposee_avant=etat["quetes"][q["id"]].get("propose_t") is not None)
        if etat.get("suivie") == q["id"]:
            etat["suivie"] = None
    if premier and nouvelles:
        annonce(etat, t, "deja_faites", n=len(nouvelles), quetes=[q["id"] for q in nouvelles], son="moyen",
                titre={"fr": f"Ton projet remplit déjà {len(nouvelles)} quête(s)", "en": f"Your project already completes {len(nouvelles)} quest(s)"},
                xp=sum(q["recompense"]["xp"] for q in nouvelles))
    for a in cat.get("actes", []):
        if a["id"] in etat["actes_finis"]:
            continue
        pr = [q for q in cat["quetes"] if q["acte"] == a["id"] and q["type"] == "principale" and etat["quetes"][q["id"]].get("existe")]
        if pr and all(etat["quetes"][q["id"]]["statut"] in FAITES for q in pr):
            etat["actes_finis"].append(a["id"])
            if not premier:
                annonce(etat, t, "acte_fini", acte=a["id"], titre=a["titre"], xp=a.get("xp_fin", 300), son="grand", icone="cartes/medaille.svg")
    xp_q = sum(cat["_par_id"][k]["recompense"]["xp"] for k, v in etat["quetes"].items() if v.get("statut") in FAITES and k in cat["_par_id"])
    xp_a = sum(a.get("xp_fin", 300) for a in cat.get("actes", []) if a["id"] in etat["actes_finis"])
    etat["xp_quetes"], etat["xp_actes"], etat["xp"] = xp_q, xp_a, xp_q + xp_a
    xp_total = ctx.xp_roadmap() + etat["xp"]
    etat["niveau"] = int((max(0, xp_total) / 100) ** 0.55) + 1
    etat["xp_roadmap"] = xp_total - etat["xp"]

    # 3. habillage (la DA du jeu habille le studio) et table du bureau
    statuts = {k: v.get("statut") for k, v in etat["quetes"].items()}
    hab = style_paliers.calculer(projet, statuts, regl.get("habillage_mode", "progressif"), regl, cat, copier_fichiers=True)
    avant = (etat.get("habillage") or {}).get("palier", 1)
    etat["habillage"] = {"palier": hab["palier"], "nom": hab["nom"], "mode": hab["mode"], "theme": hab["theme"],
                         "ajustements": hab["ajustements"], "brouillon": hab["brouillon"], "refus": hab["refus"]}
    if hab["palier"] > avant and hab["mode"] != "atelier":
        annonce(etat, t, "coup_de_peinture", de=avant, a=hab["palier"], titre=hab["nom"], son="grand" if not premier else "moyen",
                duree_s=1.8, mouvement_reduit="aucune animation si prefers-reduced-motion")
    tab = table_projet.calculer(projet)
    etat["table"] = {"theme": tab["theme"], "detail": tab["detail"], "signature": tab["signature"]}

    # 4. déblocages (agents de soutien et leurs boutons)
    etat["deblocages"] = deblocages(etat, cat, ctx, regl)

    # 5. propositions au bon moment
    ao = ordre_actes(cat)
    acte_max = max([ao.get(cat["_par_id"][k]["acte"], 0) for k, v in etat["quetes"].items() if v.get("statut") in FAITES and k in cat["_par_id"]] or [0])
    adoption = ctx.mode_projet() == "adoption"

    def prioritaire(q):
        return adoption and any(c["signal"] == "mode_projet" for c in conditions(q.get("si")))

    def type_effectif(q):
        if adoption and q["type"] == "principale" and ao.get(q["acte"], 0) < acte_max and not prioritaire(q):
            return "secondaire"       # rattrapage d'un acte passé
        return q["type"]
    ouvertes = [cat["_par_id"][k] for k, v in etat["quetes"].items() if v.get("statut") in OUVERTES and k in cat["_par_id"]]
    n_p = sum(1 for q in ouvertes if type_effectif(q) == "principale")
    n_s = len(ouvertes) - n_p
    ryt = cat.get("rythme", {})
    freq = 60 * float(regl.get("quetes_frequence_min", ryt.get("frequence_min", 30)))
    pret_rythme = etat["derniere_proposition_t"] is None or t - etat["derniere_proposition_t"] >= freq
    bloque = []
    if regl.get("quetes_actives") is False:
        bloque.append("quêtes coupées")
    if absent:
        bloque.append("mode absent")
    if nuit:
        bloque.append("nuit")
    if t < etat.get("fete_jusqu_a", 0):
        bloque.append("jalon qui vient de finir")
    if not pret_rythme:
        bloque.append("délai entre deux propositions")
    questionnaire_fini = ctx.rq.get("etat") == "termine"
    candidate = None
    # en adoption, « Habille ton studio avec ton jeu » (si : mode_projet adoption) passe en premier
    for q in sorted(cat["quetes"], key=lambda x: (not prioritaire(x), x["ordre"])):
        e = etat["quetes"][q["id"]]
        if not e.get("existe") or e["statut"] in FAITES + OUVERTES + ("refusee",):
            continue
        if e["statut"] == "plus_tard" and t < e.get("retour_t", 0) and jf <= e.get("jalons_au_report", jf):
            continue
        if q["acte"] != "fondations" and not questionnaire_fini:
            continue
        if not all(etat["quetes"].get(p, {}).get("statut") in FAITES for p in q.get("prerequis", [])):
            continue
        if not evaluer(q["declencheur"], ctx):
            e["pret"] = False
            continue
        e["pret"] = True
        te = type_effectif(q)
        if te == "principale" and n_p >= ryt.get("principales_max", 1):
            continue
        if te == "secondaire" and n_s >= ryt.get("secondaires_max", 2):
            continue
        if n_p + n_s >= int(regl.get("quetes_max_ouvertes", 3)):
            continue
        candidate = (q, te)
        break
    if candidate and not bloque:
        q, te = candidate
        e = etat["quetes"][q["id"]]
        e.update(statut="proposee", propose_t=int(t), propose_le=iso(t), rattrapage=(te != q["type"]))
        etat["derniere_proposition_t"] = int(t)
        annonce(etat, t, "quete_proposee", quete=q["id"], titre=q["titre"], son="petit")
        if etat.get("suivie") is None:
            etat["suivie"] = q["id"]
    etat["attente"] = bloque if candidate else []
    etat["prochaine_proposition"] = iso(etat["derniere_proposition_t"] + freq) if etat["derniere_proposition_t"] else None

    # 6. propositions détaillées des quêtes ouvertes
    for k, v in etat["quetes"].items():
        if v.get("statut") in OUVERTES and k in cat["_par_id"]:
            v["propositions"] = resoudre_propositions(cat["_par_id"][k], ctx, cat)
        else:
            v.pop("propositions", None)
    if premier:
        etat["premier_passage"] = iso(t)
    etat["maj"] = iso(t)
    etat.pop("index_partiel", None)
    if ecrire:
        idx.sauver()
        ecrire_json(os.path.join(st, "quetes_etat.json"), etat)
        style_paliers.ecrire(projet, hab)
        ancienne = lire_json(os.path.join(st, "table_projet.json"), {})
        if ancienne.get("signature") != tab["signature"]:
            table_projet.ecrire(projet, tab)
    return etat


def detecter_systemes(projet, fichiers, max_fichiers=400, max_octets=20 * 1024 * 1024):
    """Même détecteur que l'adoption (outils/adoption.py, SYSTEMES), sur les fichiers de code de l'index."""
    try:
        spec = importlib.util.spec_from_file_location("_adoption_studio", os.path.join(ICI, "outils", "adoption.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        table = mod.SYSTEMES
    except Exception:  # noqa: sans adoption.py, aucun système détecté par le code
        return {}
    code = [f for f in fichiers if f.lower().endswith(CODE_EXT) and not sous_build(f)][:max_fichiers]
    out, lu = {}, 0
    for f in code:
        ch = os.path.join(projet, *f.split("/"))
        try:
            if os.path.getsize(ch) > 256 * 1024 or lu > max_octets:
                continue
            with open(ch, encoding="utf-8", errors="replace") as h:
                txt = h.read().lower()
            lu += len(txt)
        except OSError:
            continue
        for sid, _titre, mots, *_ in table:
            if sid not in out and any(m in txt for m in mots):
                out[sid] = f
    return out


# ------------------------------------------------------------------ réponses de la page (future route POST /api/quete)
class Refus(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


def repondre(projet, id_, action, agents=None, chemin=None, maintenant=None, catalogue=None):
    """Enregistre une réponse (accepter, plus_tard, refuser, suivre, preuve). Refus(404|403|409|400).
    accepter : écrit la demande demandes/<horodatage>_quete_<id>.json (type quete, lancer: false) avec les corps prêts
    pour /api/recruter des agents choisis. Aucun lancement ici."""
    t = time.time() if maintenant is None else maintenant
    cat = catalogue or charger_catalogue()
    if action not in ACTIONS:
        raise Refus(400, "action inconnue")
    q = cat["_par_id"].get(id_)
    st = os.path.join(projet, ".studio")
    etat = lire_json(os.path.join(st, "quetes_etat.json"), {})
    e = (etat.get("quetes") or {}).get(id_) if isinstance(etat, dict) else None
    if not q or not e:
        raise Refus(404, "quête inconnue")
    statut = e.get("statut")
    if action in ("accepter", "plus_tard", "refuser") and statut not in OUVERTES + (("plus_tard",) if action != "plus_tard" else ()):
        raise Refus(404, "quête non proposée")
    if action == "accepter" and statut == "acceptee":
        raise Refus(409, "quête déjà acceptée")
    if action == "refuser" and q["type"] == "principale" and not e.get("rattrapage"):
        raise Refus(403, "une quête principale ne se refuse pas : « plus tard » seulement")
    if action == "suivre" and statut in FAITES:
        raise Refus(409, "quête déjà remplie")
    if action == "preuve":
        ok, raison = preuve_deposee(projet, chemin, q.get("preuve_type"))
        if not ok:
            raise Refus(400, raison)
    ch = os.path.join(st, "quetes_reponses.json")
    liste = lire_protege(ch, [])
    liste = liste if isinstance(liste, list) else []
    for i, x in enumerate(liste):                       # réponses anciennes : leur position devient leur numéro, une fois
        if isinstance(x, dict) and "n" not in x:
            x["n"] = numero(x, i)
    deja = [numero(x, i) for i, x in enumerate(liste)]
    cur = etat.get("reponse_n") if isinstance(etat, dict) else None
    cur = cur if isinstance(cur, int) and not isinstance(cur, bool) else (etat.get("reponses_lues") if isinstance(etat, dict) and isinstance(etat.get("reponses_lues"), int) else 0)
    if any(isinstance(r, dict) and r.get("id") == id_ and r.get("action") == action and t - r.get("t", 0) < 60 for r in liste[-20:]):
        raise Refus(409, "doublon (moins de 60 s)")
    proposes = [a["agent"] for a in q["propositions"].get("agents", [])]
    agents = [a for a in (agents if agents is not None else proposes) if a in proposes]
    r = {"n": max(deja + [cur]) + 1, "id": id_, "action": action, "agents": agents, "chemin": chemin, "t": int(t), "le": iso(t)}
    liste.append(r)
    ecrire_json(ch, liste[-500:])
    sortie = {"ok": True, "reponse": r}
    if action == "accepter" and q.get("ouvre"):        # quête qui se joue dans la page (créer l'hôte) : aucune demande pour l'assistant
        sortie.update(ouvre=q["ouvre"], recruter=[], confier=[], activer=[])
    elif action == "accepter":
        props = (e.get("propositions") or {}).get("agents") or []
        corps = [p.get("corps_recruter") for p in props if p.get("agent") in agents and p.get("action") == "recruter"]
        confier = [{"agent": p["agent"], "confier_a": p.get("confier_a"), "mission": p.get("mission")} for p in props if p.get("agent") in agents and p.get("action") == "confier"]
        activer = [p["reglage"] for p in props if p.get("agent") in agents and p.get("action") == "activer" and p.get("reglage")]
        d = {"type": "quete", "quete": id_, "titre": q["titre"], "lancer": False, "statut": "nouvelle", "cree_le": iso(t),
             "recruter": [c for c in corps if c], "confier": confier, "tache": q["propositions"].get("tache"),
             "skills": [s["nom"] for s in (e.get("propositions") or {}).get("skills", [])],
             "consigne": {"fr": "Montre la fiche dans la conversation et attends l'accord ; respecte agents_max. Rien n'est lancé seul.",
                          "en": "Show the sheet in the conversation and wait for approval; respect agents_max. Nothing starts on its own."}}
        nom = creer_demande(os.path.join(st, "demandes"), "quete_" + re.sub(r"[^\w.-]", "_", id_), d, t) + ".json"
        sortie.update(demande="demandes/" + nom, recruter=d["recruter"], confier=confier, activer=activer)
    return sortie


# ------------------------------------------------------------------ explication et résumé
def expliquer(projet, id_, maintenant=None, catalogue=None):
    t = time.time() if maintenant is None else maintenant
    cat = catalogue or charger_catalogue()
    q = cat["_par_id"].get(id_)
    if not q:
        raise Refus(404, "quête inconnue")
    etat = lire_json(os.path.join(projet, ".studio", "quetes_etat.json"), None) or etat_vide()
    for k, v in etat_vide().items():
        etat.setdefault(k, v)
    idx = Index(projet)
    if not idx.complet:
        idx.avancer(t, max_chemins=10 ** 9, max_s=10)
    ctx = Contexte(projet, cat, t, etat, idx)
    out = {"id": id_, "titre": q["titre"], "statut": (etat["quetes"].get(id_) or {}).get("statut", "cachee")}
    for part in ("si", "declencheur", "fini"):
        tr, pv = [], []
        out[part] = {"ok": evaluer(q.get(part), ctx, tr, pv), "conditions": tr, "preuves": pv}
    out["prerequis"] = {p: (etat["quetes"].get(p) or {}).get("statut", "cachee") for p in q.get("prerequis", [])}
    return out


def resume(etat):
    """Bloc à ajouter à etat.json (studio_etat.py) : la page l'affiche, Claude le lit à chaque point."""
    qs = etat.get("quetes", {})
    return {"proposees": sorted(k for k, v in qs.items() if v.get("statut") == "proposee"),
            "en_cours": sorted(k for k, v in qs.items() if v.get("statut") == "acceptee"),
            "remplies": sum(1 for v in qs.values() if v.get("statut") in FAITES),
            "total": sum(1 for v in qs.values() if v.get("existe")), "suivie": etat.get("suivie"),
            "xp": etat.get("xp", 0), "habillage": (etat.get("habillage") or {}).get("palier", 1),
            "boutons": [b["id"] for b in (etat.get("deblocages") or {}).get("boutons", [])]}


# ------------------------------------------------------------------ vérification du catalogue
def verifier_catalogue(chemin=CATALOGUE, mots_interdits=()):
    err = []
    try:
        cat = charger_catalogue(chemin)
    except Exception as e:  # noqa
        return [f"catalogue illisible : {e}"]
    Q = cat["quetes"]
    ids = [x.get("id") for x in Q]
    if len(ids) != len(set(ids)):
        err.append("ids en double")
    sig = set(cat.get("signaux", []))
    tags = set(cat.get("tags_roadmap", []))
    actes = {a["id"] for a in cat.get("actes", [])}
    connus = set(SKILLS_CONNUS)
    try:
        with open(os.path.join(ICI, "..", "references", "routage_skills.md"), encoding="utf-8") as f:
            connus |= set(re.findall(r"(?:gamedev|ecc):[a-z0-9-]+", f.read()))
    except OSError:
        pass

    def bilingue(o, ch):
        if isinstance(o, dict):
            if set(o) == {"fr", "en"}:
                if not (str(o["fr"]).strip() and str(o["en"]).strip()):
                    err.append(f"texte vide {ch}")
                return
            if ("fr" in o) != ("en" in o):
                err.append(f"fr/en incomplet {ch}")
            for k, v in o.items():
                bilingue(v, ch + "." + k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                bilingue(v, f"{ch}[{i}]")

    def skill_ok(s):
        return isinstance(s, str) and (s in connus or re.fullmatch(r"/[a-z0-9-]+", s))
    for nom, a in cat.get("agents", {}).items():
        if not NOM_RE.match(nom) or a.get("nom") != nom:
            err.append(f"nom d'agent {nom}")
        if len(a.get("skills", [])) > 12 or not all(skill_ok(s) for s in a.get("skills", [])):
            err.append(f"skills de l'agent {nom}")
    paliers = {}
    boutons = cat.get("deblocages", {}).get("boutons", {})
    for x in Q:
        for k in ("id", "acte", "type", "ordre", "titre", "pitch", "objectif", "declencheur", "fini", "preuve_attendue", "propositions", "recompense"):
            if k not in x:
                err.append(f"{x.get('id')} champ manquant {k}")
        if x.get("acte") not in actes:
            err.append(f"{x['id']} acte inconnu")
        if x.get("type") not in ("principale", "secondaire"):
            err.append(f"{x['id']} type")
        for c in conditions([x.get("si"), x.get("declencheur"), x.get("fini")]):
            if c["signal"] not in sig:
                err.append(f"{x['id']} signal inconnu {c['signal']}")
            if c.get("op", "existe") not in OPS:
                err.append(f"{x['id']} opérateur {c.get('op')}")
            if c["signal"] == "quete" and c.get("id") not in ids:
                err.append(f"{x['id']} vise {c.get('id')} inconnue")
            if c["signal"] == "roadmap.tag" and c.get("tag") not in tags:
                err.append(f"{x['id']} tag inconnu {c.get('tag')}")
        for p in x.get("prerequis", []):
            if p not in ids:
                err.append(f"{x['id']} prérequis {p}")
        pr = x.get("propositions", {})
        for a in pr.get("agents", []):
            if a.get("agent") not in cat.get("agents", {}):
                err.append(f"{x['id']} agent {a.get('agent')}")
        tous = list(pr.get("skills", [])) + [s for v in (pr.get("skills_par_moteur") or {}).values() for s in v] + \
            [s for v in (pr.get("skills_par_genre") or {}).values() for s in v]
        for s in tous:
            if not skill_ok(s):
                err.append(f"{x['id']} skill inconnu {s}")
        if pr.get("tache"):
            for tg in pr["tache"].get("tags", []):
                if tg not in tags:
                    err.append(f"{x['id']} tag de tâche {tg}")
        r = x.get("recompense", {})
        if not isinstance(r.get("xp"), int) or r["xp"] <= 0:
            err.append(f"{x['id']} xp")
        ic = str(r.get("succes", {}).get("icone", "")).split("/")[-1]
        if not os.path.isfile(os.path.join(CARTES, ic)):
            err.append(f"{x['id']} icône absente {ic}")
        if r.get("habillage"):
            paliers.setdefault(r["habillage"], []).append(x["id"])
        d = r.get("deblocage")
        if d:
            if d.get("agent") not in cat.get("agents", {}):
                err.append(f"{x['id']} déblocage : agent {d.get('agent')}")
            if d.get("bouton") and d["bouton"] not in boutons:
                err.append(f"{x['id']} déblocage : bouton {d['bouton']}")
        bilingue(x, x["id"])
    if sorted(paliers) != [2, 3, 4, 5] or any(len(v) != 1 for v in paliers.values()):
        err.append(f"paliers d'habillage {paliers}")
    bilingue(cat.get("actes"), "actes")
    bilingue(cat.get("agents"), "agents")
    bilingue(cat.get("deblocages"), "deblocages")
    dep = {x["id"]: set(x.get("prerequis", [])) | {c["id"] for c in conditions(x.get("declencheur")) if c["signal"] == "quete"} for x in Q}
    vu = {}

    def visite(n, pile=()):
        if vu.get(n) == 2:
            return
        if vu.get(n) == 1:
            err.append("boucle " + " > ".join(pile + (n,)))
            return
        vu[n] = 1
        for m in dep.get(n, ()):
            visite(m, pile + (n,))
        vu[n] = 2
    for n in dep:
        visite(n)
    txt = json.dumps({k: v for k, v in cat.items() if k != "_par_id"}, ensure_ascii=False).lower()
    for m in mots_interdits:
        if m and m.lower() in txt:
            err.append(f"mot interdit : {m}")
    return err


# ------------------------------------------------------------------ ligne de commande
def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if "--verifier-catalogue" in a:
        mots = []
        if "--mots-interdits" in a:
            with open(a[a.index("--mots-interdits") + 1], encoding="utf-8") as f:
                mots = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        err = verifier_catalogue(mots_interdits=mots)
        cat = charger_catalogue()
        print(json.dumps({"quetes": len(cat["quetes"]), "xp_total": sum(q["recompense"]["xp"] for q in cat["quetes"]),
                          "erreurs": err}, ensure_ascii=False, indent=1))
        return 1 if err else 0
    if not a or a[0].startswith("-"):
        print(__doc__)
        return 2
    projet = os.path.abspath(a[0])
    try:
        if "--repondre" in a:
            i = a.index("--repondre")
            agents = a[a.index("--agents") + 1].split(",") if "--agents" in a else None
            chemin = a[a.index("--chemin") + 1] if "--chemin" in a else None
            print(json.dumps(repondre(projet, a[i + 1], a[i + 2], agents, chemin), ensure_ascii=False, indent=1))
            return 0
        if "--expliquer" in a:
            print(json.dumps(expliquer(projet, a[a.index("--expliquer") + 1]), ensure_ascii=False, indent=1, default=str))
            return 0
    except Refus as e:
        print(json.dumps({"ok": False, "code": e.code, "erreur": e.message}, ensure_ascii=False))
        return 3
    etat = passe(projet, index_complet="--index-complet" in a)
    if "--json" in a:
        print(json.dumps(etat, ensure_ascii=False, indent=1))
    else:
        print(json.dumps(resume(etat), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
