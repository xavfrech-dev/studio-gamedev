"""Adoption d'un projet de jeu déjà commencé : analyse sans rien modifier, pré-remplissage, garde-fous.

Usage (Python 3.10+, bibliothèque standard) :
  python -I -B adoption.py analyser   --projet P [--sec] [--nouvelle-photo]
                                                          inventaire du projet → .studio/analyse_projet.json, analyse_projet.md,
                                                          empreintes_adoption.json (--sec : affiche seulement, n'écrit rien)
  python -I -B adoption.py preremplir --projet P           .studio/reponses_questionnaire.json ("mode": "adoption", réponses
                                                          déduites du projet) et .studio/deductions.json (fixes, ★, accueil)
  python -I -B adoption.py verifier   --projet P [--accord CLAUDE.md ...]
                                                          compare le projet aux empreintes prises à l'analyse : code 1 si un
                                                          fichier existant a été modifié ou supprimé hors des ajouts permis
  python -I -B adoption.py gitignore  --projet P           ajoute le bloc .studio/ au .gitignore seulement s'il n'y est pas
  python -I -B adoption.py bloc       --projet P --fichier CLAUDE.md --contenu <fichier>
                                                          ajoute (ou remplace) le bloc délimité <!-- studio-gamedev --> ;
                                                          seulement après l'accord de l'utilisateur ; le reste du fichier
                                                          n'est jamais touché

Règles : l'analyse ne lit que le projet (pas de lien symbolique suivi, dossiers générés ignorés) et n'écrit que dans
<projet>/.studio/. Rien n'est jamais réécrit : un document existant reçoit un fichier voisin *.studio.md, ou un bloc
délimité après accord ; le code du jeu n'est jamais touché pendant l'adoption.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass

IGNORES = {".git", ".studio", ".godot", ".import", "node_modules", "Library", "Temp", "Obj", "obj", "Logs", "UserSettings",
           "Intermediate", "Binaries", "Saved", "DerivedDataCache", "target", "dist", "build", "export", "__pycache__",
           ".venv", "venv", ".mono", ".vs", ".idea", ".vscode", ".cache"}
MAX_FICHIERS = 20000
MAX_LECTURE = 1_000_000
DEBUT_BLOC, FIN_BLOC = "<!-- studio-gamedev -->", "<!-- /studio-gamedev -->"
BLOC_GITIGNORE = ("# Studio gamedev : données locales (profil, dictées, images, état de la machine)\n"
                  ".studio/*\n!.studio/roadmap.json\n!.studio/studio.config.json\n")
# documents que le skill écrit d'habitude : s'ils existent, on écrit à côté ou par bloc délimité, jamais par-dessus
PROTEGES = [("docs/ROADMAP.md", "a_cote"), ("docs/GDD.md", "a_cote"), ("docs/DECISIONS.md", "a_cote"),
            ("docs/CHANGELOG.md", "a_cote"), ("docs/ASSETS.md", "a_cote"), ("README.md", "a_cote"),
            ("CLAUDE.md", "bloc"), (".gitignore", "bloc_gitignore")]

EXT_CODE = {".gd": "gdscript", ".cs": "csharp", ".cpp": "cpp", ".h": "cpp", ".hpp": "cpp", ".ts": "typescript",
            ".js": "javascript", ".mjs": "javascript", ".rs": "rust", ".lua": "lua", ".luau": "luau", ".py": "python",
            ".go": "go", ".gdshader": "shader", ".shader": "shader", ".hlsl": "shader", ".glsl": "shader"}
EXT_SCENES = {".tscn": "godot", ".scn": "godot", ".umap": "unreal", ".unity": "unity", ".rbxl": "roblox"}
EXT_ASSETS = {"images": (".png", ".jpg", ".jpeg", ".webp", ".svg", ".tga", ".psd", ".aseprite", ".bmp", ".exr", ".hdr"),
              "modeles_3d": (".glb", ".gltf", ".fbx", ".obj", ".blend", ".dae", ".uasset"),
              "audio": (".wav", ".ogg", ".mp3", ".flac"),
              "polices": (".ttf", ".otf", ".woff", ".woff2")}

# systèmes reconnus dans le code (mots cherchés en minuscules) ; carte = id de la carte de gameplay.systemes
SYSTEMES = [
    ("joueur", "Contrôles du joueur", ["characterbody2d", "characterbody3d", "move_and_slide", "input.get_vector", "input.get_axis", "playercontroller", "charactercontroller"], None, "code-gameplay", 4),
    ("saut", "Saut et gravité", ["is_on_floor", "jump_velocity", "jump", "gravity"], "physique", "code-gameplay", 2),
    ("camera", "Caméra", ["camera2d", "camera3d", "springarm", "cinemachine"], None, "code-gameplay", 2),
    ("ennemis", "Ennemis et IA", ["enemy", "ennemi", "patrol", "patrouille", "navigationagent", "chase"], "ia_ennemie", "code-gameplay", 4),
    ("combat", "Combat et dégâts", ["take_damage", "damage", "hitbox", "hurtbox", "attack", "weapon"], "combat", "code-gameplay", 4),
    ("inventaire", "Inventaire", ["inventory", "inventaire", "item_slot"], "inventaire", "code-gameplay", 5),
    ("fabrication", "Fabrication", ["craft", "recipe", "recette"], "fabrication", "code-gameplay", 5),
    ("dialogues", "Dialogues", ["dialogue", "dialog"], "dialogues", "narration", 4),
    ("sauvegarde", "Sauvegarde", ["save_game", "savegame", "sauvegard", "configfile", "user://", "playerprefs", "localstorage"], "sauvegarde", "code-gameplay", 3),
    ("interface", "Interface (HUD, menus)", ["hud", "main_menu", "pause_menu", "canvaslayer"], None, "art-da", 3),
    ("audio", "Sons et musique", ["audiostreamplayer", "play_sound", "audiosource", "sfx"], None, "son", 2),
    ("procedural", "Génération procédurale", ["fastnoiselite", "procedural", "generate_level", "generate_map"], "procedural", "code-gameplay", 6),
    ("meteo", "Météo", ["weather", "meteo"], "meteo", "code-gameplay", 4),
    ("economie", "Économie (pièces, boutique)", ["coins", "currency", "shop", "boutique"], "economie", "code-gameplay", 4),
    ("reseau", "Multijoueur en réseau", ["multiplayerspawner", "multiplayersynchronizer", "enetmultiplayerpeer", "@rpc", "websocketpeer", "netcode"], None, "reseau", 8),
]
GENRES = {
    "plateforme": ["jump", "is_on_floor", "platform", "plateforme", "coyote"],
    "fps": ["shoot", "bullet", "recoil", "ammo", "first_person"],
    "survie": ["hunger", "faim", "thirst", "survival", "survie", "craft"],
    "rpg": ["quest", "quete", "level_up", "experience", "stats"],
    "puzzle": ["puzzle", "match3", "grid_solve"],
    "course": ["vehicle", "lap", "checkpoint_race", "drift"],
    "tower_defense": ["tower", "wave_spawner", "next_wave"],
    "cartes": ["deck", "card", "hand_size"],
    "strategie": ["rts", "select_units", "fog_of_war"],
}
VERBE_DU_GENRE = {"plateforme": "explorer", "fps": "combattre", "survie": "survivre", "rpg": "explorer", "puzzle": "resoudre",
                  "course": "conduire", "tower_defense": "gerer", "cartes": "collectionner", "strategie": "gerer"}


def maintenant():
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def rel(projet, chemin):
    return os.path.relpath(chemin, projet).replace("\\", "/")


def lire_texte(chemin, maxi=MAX_LECTURE):
    try:
        with open(chemin, "rb") as f:
            return f.read(maxi).decode("utf-8-sig", "replace")
    except OSError:
        return ""


def lire_json(chemin, defaut=None):
    try:
        with open(chemin, encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return defaut


def ecrire(chemin, donnees):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(donnees if isinstance(donnees, str) else json.dumps(donnees, ensure_ascii=False, indent=1))
    os.replace(tmp, chemin)


def dans_projet(projet, chemin):
    p, c = os.path.realpath(projet), os.path.realpath(chemin)
    return c == p or c.startswith(p.rstrip("\\/") + os.sep)


# ---------------------------------------------------------------------------- parcours
def parcourir(projet):
    """Fichiers du projet (relatifs), sans suivre de lien, sans les dossiers générés ni .studio/."""
    out = []
    for racine, dossiers, fichiers in os.walk(projet, followlinks=False):
        dossiers[:] = sorted(x for x in dossiers if x not in IGNORES and not os.path.islink(os.path.join(racine, x)))
        for f in sorted(fichiers):
            ch = os.path.join(racine, f)
            if os.path.islink(ch) or f.endswith(".tmp"):
                continue
            out.append(rel(projet, ch))
            if len(out) >= MAX_FICHIERS:
                return out, True
    return out, False


def empreinte(chemin, longueur=None):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        if longueur is None:
            for bloc in iter(lambda: f.read(1 << 20), b""):
                h.update(bloc)
        else:
            reste = longueur
            while reste > 0:
                b = f.read(min(1 << 20, reste))
                if not b:
                    break
                h.update(b)
                reste -= len(b)
    return h.hexdigest()


def prendre_empreintes(projet, fichiers):
    return {f: {"sha256": empreinte(os.path.join(projet, f)), "taille": os.path.getsize(os.path.join(projet, f))} for f in fichiers}


# ---------------------------------------------------------------------------- git (lecture seule)
def git(projet, *a):
    try:
        r = subprocess.run(["git", "--no-optional-locks", "-C", projet, *a], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


def analyser_git(projet):
    if not os.path.exists(os.path.join(projet, ".git")):
        return {"depot": False}
    out = {"depot": True, "branche": (git(projet, "rev-parse", "--abbrev-ref", "HEAD") or "").strip()}
    log = git(projet, "log", "--format=%h|%aI|%s", "-n", "2000") or ""
    commits = []
    for ligne in log.splitlines():
        p = ligne.split("|", 2)
        if len(p) == 3:
            try:
                commits.append((p[0], dt.datetime.fromisoformat(p[1]), p[2][:120]))
            except ValueError:
                pass
    out["commits"] = len(commits)
    st = git(projet, "status", "--porcelain")
    out["fichiers_modifies"] = len([x for x in (st or "").splitlines() if x.strip() and ".studio/" not in x])
    ga = lire_texte(os.path.join(projet, ".gitattributes"), 200_000)
    out["lfs"] = "filter=lfs" in ga
    if commits:
        dates = sorted(c[1] for c in commits)
        out["premier"], out["dernier"] = dates[0].date().isoformat(), dates[-1].date().isoformat()
        out["jours_actifs"] = len({d.date() for d in dates})
        out["derniers"] = [{"hash": h, "date": d.date().isoformat(), "sujet": s} for h, d, s in commits[:15]]
        # sessions de travail : commits à moins de 3 h d'écart ; une session = durée + 1 h (le travail avant le 1er commit)
        heures, debut, prec = 0.0, dates[0], dates[0]
        for d in dates[1:] + [None]:
            if d is None or (d - prec).total_seconds() > 3 * 3600:
                heures += (prec - debut).total_seconds() / 3600 + 1
                if d is not None:
                    debut = d
            if d is not None:
                prec = d
        out["heures_sessions"] = round(heures, 1)
        out["semaines"] = max(1, round(((dates[-1] - dates[0]).days + 1) / 7))
    return out


# ---------------------------------------------------------------------------- moteur
def ini_valeur(txt, cle):
    m = re.search(r"^\s*" + re.escape(cle) + r"\s*=\s*(.+)$", txt, re.M)
    return m.group(1).strip() if m else None


def detecter_moteur(projet, fichiers):
    fs = set(fichiers)
    exts = {}
    for f in fichiers:
        e = os.path.splitext(f)[1].lower()
        exts[e] = exts.get(e, 0) + 1
    if "project.godot" in fs or any(f.endswith("/project.godot") for f in fichiers):
        pg = "project.godot" if "project.godot" in fs else next(f for f in fichiers if f.endswith("/project.godot"))
        txt = lire_texte(os.path.join(projet, pg))
        feats = ini_valeur(txt, "config/features") or ""
        version = (re.findall(r'"(\d+\.\d+)"', feats) or [None])[0]
        nom = (ini_valeur(txt, "config/name") or "").strip('"')
        principale = (ini_valeur(txt, "run/main_scene") or "").strip('"')
        autoload = re.findall(r'^\s*(\w+)\s*=\s*"\*?res://', txt.split("[autoload]")[1].split("\n[")[0], re.M) if "[autoload]" in txt else []
        actions = re.findall(r"^(\w+)\s*=\s*\{", txt.split("[input]")[1].split("\n[")[0], re.M) if "[input]" in txt else []
        nearest = ini_valeur(txt, "textures/canvas_textures/default_texture_filter") == "0"
        langage = "csharp" if exts.get(".cs", 0) > exts.get(".gd", 0) else "gdscript"
        exports = []
        if "export_presets.cfg" in fs:
            exports = sorted(set(re.findall(r'^platform="([^"]+)"', lire_texte(os.path.join(projet, "export_presets.cfg")), re.M)))
        return {"nom": "godot", "version": version, "langage": langage, "preuve": pg, "nom_projet": nom,
                "details": {"scene_principale": principale, "autoload": autoload, "actions": actions[:40],
                            "filtre_pixel": nearest, "exports": exports}}
    up = [f for f in fichiers if f.endswith(".uproject")]
    if up:
        d = lire_json(os.path.join(projet, up[0]), {}) or {}
        cpp = any(f.lower().endswith((".cpp", ".h")) and "/source/" in "/" + f.lower() for f in fichiers)
        return {"nom": "unreal", "version": d.get("EngineAssociation"), "langage": "blueprints_cpp" if cpp else "blueprints",
                "preuve": up[0], "nom_projet": os.path.splitext(os.path.basename(up[0]))[0], "details": {"modules": [m.get("Name") for m in d.get("Modules", []) if isinstance(m, dict)][:10]}}
    if "ProjectSettings/ProjectVersion.txt" in fs:
        v = ini_valeur(lire_texte(os.path.join(projet, "ProjectSettings/ProjectVersion.txt")).replace(":", "="), "m_EditorVersion")
        return {"nom": "unity", "version": v, "langage": "csharp", "preuve": "ProjectSettings/ProjectVersion.txt", "nom_projet": "", "details": {}}
    if "default.project.json" in fs or exts.get(".luau") or exts.get(".rbxl"):
        return {"nom": "roblox", "version": None, "langage": "luau", "preuve": "default.project.json" if "default.project.json" in fs else "*.luau", "nom_projet": "", "details": {}}
    if "package.json" in fs:
        pj = lire_json(os.path.join(projet, "package.json"), {}) or {}
        deps = {**(pj.get("dependencies") or {}), **(pj.get("devDependencies") or {})}
        for paquet, nom in (("phaser", "phaser"), ("three", "threejs"), ("pixi.js", "pixijs"), ("excalibur", "maison"), ("kaboom", "maison")):
            if paquet in deps:
                return {"nom": nom, "version": str(deps[paquet]).lstrip("^~"), "langage": "typescript" if exts.get(".ts") else "javascript",
                        "preuve": "package.json", "nom_projet": pj.get("name", ""), "details": {"scripts": sorted((pj.get("scripts") or {}).keys())[:12]}}
    if "Cargo.toml" in fs:
        c = lire_texte(os.path.join(projet, "Cargo.toml"))
        m = re.search(r'^\s*bevy\s*=\s*(?:"([^"]+)"|\{[^}]*version\s*=\s*"([^"]+)")', c, re.M)
        if m:
            return {"nom": "bevy", "version": m.group(1) or m.group(2), "langage": "impose", "preuve": "Cargo.toml", "nom_projet": "", "details": {}}
    if "go.mod" in fs and "ebiten" in lire_texte(os.path.join(projet, "go.mod")):
        return {"nom": "ebitengine", "version": None, "langage": "impose", "preuve": "go.mod", "nom_projet": "", "details": {}}
    if "game.project" in fs:
        return {"nom": "defold", "version": None, "langage": "impose", "preuve": "game.project", "nom_projet": "", "details": {}}
    if "main.lua" in fs and ("conf.lua" in fs or "love." in lire_texte(os.path.join(projet, "main.lua"), 200_000)):
        return {"nom": "love", "version": None, "langage": "impose", "preuve": "main.lua", "nom_projet": "", "details": {}}
    if exts.get(".py") and any("import pygame" in lire_texte(os.path.join(projet, f), 200_000) for f in fichiers if f.endswith(".py")):
        return {"nom": "pygame", "version": None, "langage": "impose", "preuve": "*.py (import pygame)", "nom_projet": "", "details": {}}
    return {"nom": None, "version": None, "langage": None, "preuve": None, "nom_projet": "", "details": {}}


# ---------------------------------------------------------------------------- analyse
def type_racine_tscn(txt):
    m = re.search(r'^\[node name="[^"]*" type="(\w+)"', txt, re.M)
    if m:
        return m.group(1)
    return "instance" if re.search(r'^\[node name="[^"]*" instance=', txt, re.M) else None


def dimension_type(t):
    if not t:
        return None
    if t.endswith("3D") or t in ("Spatial", "WorldEnvironment"):
        return "3d"
    if t.endswith("2D") or t in ("Control", "CanvasLayer", "TileMap", "TileMapLayer") or t.startswith(("Panel", "Label", "Button", "Margin", "VBox", "HBox")):
        return "2d"
    return None


def premier_titre(txt):
    m = re.search(r"^#\s+(.+)$", txt, re.M)
    return m.group(1).strip()[:120] if m else ""


def premier_paragraphe(txt):
    for bloc in re.split(r"\n\s*\n", txt):
        b = bloc.strip()
        if b and not b.startswith(("#", "```", "-", "*", "|", "<", ">", "!")):
            return re.sub(r"\s+", " ", b)[:400]
    return ""


def analyser(projet):
    fichiers, tronque = parcourir(projet)
    moteur = detecter_moteur(projet, fichiers)
    git_inf = analyser_git(projet)

    # scènes
    scenes = []
    for f in fichiers:
        e = os.path.splitext(f)[1].lower()
        if e in EXT_SCENES:
            racine = type_racine_tscn(lire_texte(os.path.join(projet, f), 400_000)) if e == ".tscn" else None
            scenes.append({"chemin": f, "racine": racine, "dim": dimension_type(racine)})
    niveaux = [s for s in scenes if re.search(r"(level|niveau|world|monde|stage|map)[_\-]?\d*", s["chemin"].lower())]

    # code
    langs, scripts, lignes_tot, todo = {}, [], 0, []
    contenus = {}
    for f in fichiers:
        e = os.path.splitext(f)[1].lower()
        if e not in EXT_CODE:
            continue
        if e == ".js" and ("/node_modules/" in f or f.endswith(".min.js")):
            continue
        txt = lire_texte(os.path.join(projet, f))
        n = txt.count("\n") + (1 if txt and not txt.endswith("\n") else 0)
        l = langs.setdefault(EXT_CODE[e], {"fichiers": 0, "lignes": 0})
        l["fichiers"] += 1
        l["lignes"] += n
        lignes_tot += n
        scripts.append(f)
        contenus[f] = txt
        for i, ligne in enumerate(txt.splitlines(), 1):
            m = re.search(r"\b(TODO|FIXME|HACK|XXX|A FAIRE)\b[:\s]*(.*)", ligne)
            if m and len(todo) < 200:
                todo.append({"ou": f"{f}:{i}", "texte": (m.group(1) + " " + m.group(2)).strip()[:120]})
    scenes_txt = {s["chemin"]: lire_texte(os.path.join(projet, s["chemin"]), 400_000).lower() for s in scenes if s["chemin"].endswith(".tscn")}

    # systèmes
    systemes = []
    NOMS = {"joueur": ("player", "joueur", "hero", "heros"), "ennemis": ("enemy", "ennemi", "mob", "monster"), "camera": ("camera", "player"),
            "sauvegarde": ("save", "sauvegarde", "state"), "interface": ("hud", "ui", "menu"), "audio": ("audio", "sound", "son", "music")}
    for sid, titre, mots, carte, poste, std in SYSTEMES:
        preuve = None
        indices = NOMS.get(sid, ())
        candidats = sorted(list(contenus.items()) + list(scenes_txt.items()), key=lambda x: (not any(n in os.path.basename(x[0]).lower() for n in indices), x[0] not in contenus, x[0]))   # nom parlant, puis code avant scènes
        for f, txt in candidats:
            low = txt.lower() if f in contenus else txt
            nom = f.lower()
            if any(m in low for m in mots) or (sid == "interface" and re.search(r"(^|/)(ui|hud|menu)s?(/|_|\.)", nom)):
                preuve = f
                break
        if preuve:
            systemes.append({"id": sid, "titre": titre, "preuve": preuve, "carte": carte, "poste": poste, "estimation_standard_h": std})

    # assets
    assets = {k: 0 for k in EXT_ASSETS}
    taille = 0
    for f in fichiers:
        e = os.path.splitext(f)[1].lower()
        for k, ex in EXT_ASSETS.items():
            if e in ex:
                assets[k] += 1
                try:
                    taille += os.path.getsize(os.path.join(projet, f))
                except OSError:
                    pass
    assets["taille_mo"] = round(taille / 1e6, 2)

    # docs
    docs = []
    for f in fichiers:
        b = os.path.basename(f).lower()
        if (b.endswith((".md", ".txt", ".rst")) and (f.count("/") == 0 or f.lower().startswith(("docs/", "doc/")))) and not b.startswith("license"):
            t = lire_texte(os.path.join(projet, f), 400_000)
            docs.append({"chemin": f, "titre": premier_titre(t), "lignes": t.count("\n") + 1})
    readme = next((d["chemin"] for d in docs if os.path.basename(d["chemin"]).lower().startswith("readme")), None)
    pitch_readme = premier_paragraphe(lire_texte(os.path.join(projet, readme))) if readme else ""

    # conventions
    conv = {}
    if scripts:
        tabs = sum(1 for t in contenus.values() if re.search(r"^\t", t, re.M))
        espaces = sum(1 for t in contenus.values() if re.search(r"^ {2,}\S", t, re.M))
        conv["indentation"] = "tabulations" if tabs >= espaces else "espaces"
        noms = [os.path.splitext(os.path.basename(f))[0] for f in scripts]
        snake = sum(1 for n in noms if re.match(r"^[a-z0-9_]+$", n))
        pascal = sum(1 for n in noms if re.match(r"^[A-Z][A-Za-z0-9]+$", n))
        conv["noms_fichiers"] = "snake_case" if snake >= pascal else "PascalCase"
        gd = [t for f, t in contenus.items() if f.endswith(".gd")]
        if gd:
            funcs = sum(len(re.findall(r"^\s*func\s", t, re.M)) for t in gd)
            typees = sum(len(re.findall(r"^\s*func\s[^\n]*\)\s*->", t, re.M)) for t in gd)
            conv["gdscript_typage"] = f"{typees}/{funcs} fonctions typées"
            conv["class_name"] = sum(1 for t in gd if re.search(r"^class_name\s", t, re.M))
        cfg = [f for f in fichiers if os.path.basename(f) in (".editorconfig", ".gdlintrc", "gdlintrc", ".eslintrc", ".eslintrc.json", "eslint.config.js", ".prettierrc", "rustfmt.toml", ".clang-format", "pyproject.toml")]
        if cfg:
            conv["fichiers_de_style"] = cfg
        com = " ".join(re.findall(r"#\s*([^\n]{3,80})", " ".join(gd)[:50000])) if gd else ""
        if com:
            fr = len(re.findall(r"\b(le|la|les|des|une|pour|avec|quand)\b", com.lower()))
            en = len(re.findall(r"\b(the|and|for|with|when|this)\b", com.lower()))
            conv["langue_commentaires"] = "fr" if fr > en else "en" if en > fr else "?"

    # tests
    tfich = [f for f in fichiers if re.search(r"(^|/)(tests?|spec)/", f.lower()) or re.search(r"(^|/)(test_[^/]+|[^/]+_test|[^/]+\.test|[^/]+\.spec)\.\w+$", f.lower())]
    cadre = None
    if any(f.startswith("addons/gut/") for f in fichiers):
        cadre = "GUT"
    elif any(f.startswith("addons/gdUnit4/") for f in fichiers):
        cadre = "gdUnit4"
    elif "package.json" in fichiers and "test" in ((lire_json(os.path.join(projet, "package.json"), {}) or {}).get("scripts") or {}):
        cadre = "npm test"
    elif moteur["nom"] == "bevy":
        cadre = "cargo test"
    tests = {"present": bool(tfich), "cadre": cadre, "fichiers": [f for f in tfich if not f.startswith("addons/")][:30]}

    # déductions
    sures, probables = {}, {}
    pr = lambda texte: "déduit du projet : " + texte
    if moteur["nom"]:
        sures["moteur.nom"] = {"valeur": moteur["nom"], "raison": pr(moteur["preuve"])}
        if moteur["langage"]:
            sures["moteur.langage"] = {"valeur": moteur["langage"], "raison": pr(f"{langs and max(langs, key=lambda k: langs[k]['lignes']) or moteur['langage']} majoritaire")}
        if moteur["version"]:
            sures["moteur.version"] = {"valeur": "precise", "raison": pr(f"version {moteur['version']} ({moteur['preuve']})")}
    if git_inf.get("depot"):
        sures["moteur.versionnage"] = {"valeur": "git_lfs" if git_inf.get("lfs") else "git", "raison": pr(".git" + (" + LFS dans .gitattributes" if git_inf.get("lfs") else ""))}
    dims = [s["dim"] for s in scenes if s["dim"]]
    if dims:
        d2, d3 = dims.count("2d"), dims.count("3d")
        dim = "2d" if d2 >= d3 else "3d"
        (sures if max(d2, d3) >= 0.8 * len(dims) else probables)["camera.dimension"] = {"valeur": dim, "raison": pr(f"{max(d2, d3)}/{len(dims)} scènes en {dim.upper()}")}
    tout_code = " ".join(contenus.values()).lower() + " " + " ".join(scenes_txt.values())
    scores = {g: sum(tout_code.count(m) for m in mots) for g, mots in GENRES.items()}
    genre = max(scores, key=scores.get) if scores and max(scores.values()) > 0 else None
    if genre:
        probables["genre.principal"] = {"valeur": genre, "raison": pr(f"mots du code ({scores[genre]} indices)")}
        verbe = "combattre" if any(s["id"] == "combat" for s in systemes) and genre not in ("plateforme",) else VERBE_DU_GENRE.get(genre)
        if verbe:
            probables["gameplay.verbe"] = {"valeur": verbe, "raison": pr("genre et systèmes codés")}
    dim_v = (sures.get("camera.dimension") or probables.get("camera.dimension") or {}).get("valeur")
    if dim_v == "2d":
        vue = "cote" if genre == "plateforme" or "is_on_floor" in tout_code else "dessus"
        probables["camera.vue"] = {"valeur": vue, "raison": pr("2D " + ("avec gravité et saut" if vue == "cote" else "sans gravité"))}
    elif dim_v == "3d" and ("first_person" in tout_code or "fps" in tout_code):
        probables["camera.vue"] = {"valeur": "premiere_personne", "raison": pr("caméra à la 1re personne dans le code")}
    cartes = [s["carte"] for s in systemes if s["carte"] and s["carte"] != "physique"]
    if cartes:
        probables["gameplay.systemes"] = {"valeur": cartes, "raison": pr("systèmes déjà codés")}
    reseau = any(s["id"] == "reseau" for s in systemes)
    probables["multijoueur.mode"] = {"valeur": "coop_ligne" if reseau else "solo", "raison": pr("code réseau trouvé" if reseau else "aucun code réseau")}
    exp = (moteur.get("details") or {}).get("exports") or []
    cibles = sorted({{"Windows Desktop": "pc", "Linux": "mac_linux", "Linux/X11": "mac_linux", "macOS": "mac_linux", "Web": "web", "Android": "mobile", "iOS": "mobile"}.get(x, "pc") for x in exp})
    if cibles:
        probables["plateforme.cibles"] = {"valeur": cibles, "raison": pr("export_presets.cfg")}
    if len(niveaux) >= 2:
        probables["monde.structure"] = {"valeur": "niveaux", "raison": pr(f"{len(niveaux)} scènes de niveau")}
    if (moteur.get("details") or {}).get("filtre_pixel"):
        probables["da.style"] = {"valeur": "pixel", "raison": pr("filtre de texture « nearest »")}

    # existant (jalon J0 de la roadmap) et calibrage
    existant = []
    if moteur["nom"]:
        existant.append({"titre": f"Projet {moteur['nom']} {moteur['version'] or ''} en place".replace("  ", " "), "preuve": moteur["preuve"], "poste": "integration-moteur", "moteur": True, "estimation_standard_h": 1})
    if scenes:
        principale = ((moteur.get("details") or {}).get("scene_principale") or "").replace("res://", "")
        preuve_scene = principale if any(s["chemin"] == principale for s in scenes) else (niveaux or scenes)[0]["chemin"]   # la scène lancée par le jeu d'abord
        existant.append({"titre": f"{len(scenes)} scènes" + (f" dont {len(niveaux)} niveaux" if niveaux else ""), "preuve": preuve_scene, "poste": "integration-moteur", "moteur": True, "estimation_standard_h": round(0.75 * len(scenes), 1)})
    for s in systemes:
        existant.append({"titre": s["titre"], "preuve": s["preuve"], "poste": s["poste"], "moteur": False, "estimation_standard_h": s["estimation_standard_h"]})
    n_assets = assets["images"] + assets["modeles_3d"] + assets["audio"]
    if n_assets:
        premier_asset = next((f for f in fichiers if os.path.splitext(f)[1].lower() in sum(EXT_ASSETS.values(), ())), "")
        existant.append({"titre": f"{n_assets} assets (images {assets['images']}, 3D {assets['modeles_3d']}, sons {assets['audio']})", "preuve": premier_asset, "poste": "art-da", "moteur": False, "estimation_standard_h": min(8, round(0.3 * n_assets, 1))})
    if tests["present"]:
        existant.append({"titre": "Tests" + (f" ({tests['cadre']})" if tests["cadre"] else ""), "preuve": (tests["fichiers"] or ["addons/"])[0], "poste": "code-gameplay", "moteur": False, "estimation_standard_h": 2})
    for d in docs:
        if os.path.basename(d["chemin"]).lower() in ("readme.md", "claude.md"):
            existant.append({"titre": f"Document {d['chemin']}", "preuve": d["chemin"], "poste": "direction", "moteur": False, "estimation_standard_h": 0.5})
    autres_docs = [d["chemin"] for d in docs if os.path.basename(d["chemin"]).lower() not in ("readme.md", "claude.md")]
    if autres_docs:   # notes, idées, design : une seule ligne pour tous
        existant.append({"titre": f"Notes et documents ({len(autres_docs)})", "preuve": autres_docs[0], "poste": "direction", "moteur": False, "estimation_standard_h": min(2, 0.5 * len(autres_docs))})
    for e in existant:
        if not e["preuve"] and git_inf.get("derniers"):
            e["preuve"] = "commit " + git_inf["derniers"][0]["hash"]
    std = sum(e["estimation_standard_h"] for e in existant) or 1
    h_code = round(lignes_tot / 25 + 0.5 * len(scenes), 1)
    h_git = git_inf.get("heures_sessions")
    deja = h_git if h_git and h_git >= 1 else h_code
    facteur = max(0.6, min(1.8, round(deja / std, 1)))
    hps = round(deja / git_inf["semaines"], 1) if h_git and git_inf.get("semaines") else None
    calibrage = {"heures_deja_estimees": deja, "methode": "sessions git (commits à moins de 3 h, +1 h par session)" if h_git and h_git >= 1 else "lignes de code ÷ 25 + 0,5 h par scène",
                 "heures_standard_de_l_existant": round(std, 1), "facteur": facteur, "heures_par_semaine_observees": hps,
                 "lecture": "estimations du studio × facteur (borné 0,6 à 1,8) : >1 = l'auteur va plus lentement que la norme, <1 = plus vite"}
    if hps:
        probables["ambition.temps"] = {"valeur": "quelques_heures" if hps < 8 else "soirs" if hps < 20 else "plein", "raison": pr(f"≈ {hps} h par semaine d'après git")}

    # ce qui manque, postes
    manques = []
    if not tests["present"]:
        manques.append("aucun test")
    if not any(s["id"] == "sauvegarde" for s in systemes):
        manques.append("pas de sauvegarde")
    if not assets["audio"]:
        manques.append("aucun son")
    if not any(s["id"] == "interface" for s in systemes):
        manques.append("pas d'interface")
    if not any(os.path.basename(d["chemin"]).lower() in ("gdd.md", "design.md") for d in docs):
        manques.append("pas de document de conception (GDD)")
    postes = ["direction"]
    if moteur["nom"]:
        postes.append("integration-moteur")
    if scripts:
        postes.append("code-gameplay")
    postes.append("art-da")
    if assets["audio"] or "aucun son" in manques:
        postes.append("son")
    if not tests["present"] or todo:
        postes.append("qualite-tests")
    if reseau:
        postes.append("reseau")
    if any(s["id"] == "dialogues" for s in systemes):
        postes.append("narration")
    postes = postes[:8]

    fs = set(fichiers)
    proteges = []
    for ch, action in PROTEGES:
        if ch in fs:
            cible = ch[:-3] + ".studio.md" if action == "a_cote" else ch
            proteges.append({"chemin": ch, "action": action, "cible": cible})
    agents = [f for f in fichiers if f.startswith(".claude/agents/") and f.endswith(".md")]

    nom = moteur.get("nom_projet") or (premier_titre(lire_texte(os.path.join(projet, readme))) if readme else "") or os.path.basename(os.path.abspath(projet))
    moteur_txt = f"{moteur['nom'] or 'moteur non reconnu'} {moteur['version'] or ''}".strip()
    def pl(n, mot, mots=None):                 # « 1 scène », « 2 scènes »
        return f"{n} {mot if n in (0, 1) else (mots or mot + 's')}"
    resume = [
        f"Projet « {nom} » : {moteur_txt}" + (f", {moteur['langage']}" if moteur["langage"] else "") + ".",
        pl(len(scenes), "scène") + (f" ({pl(len(niveaux), 'niveau', 'niveaux')})" if niveaux else "") + f", {pl(len(scripts), 'script')} ({pl(lignes_tot, 'ligne')}), {pl(n_assets, 'asset')}.",
        "Déjà codé : " + (", ".join(s["titre"].lower() for s in systemes[:8]) or "rien de reconnu") + ".",
        ("Historique : " + f"{pl(git_inf['commits'], 'commit')} sur {pl(git_inf.get('jours_actifs', 0), 'jour')}, ≈ {deja} h de travail" if git_inf.get("commits") else f"Pas d'historique git ; ≈ {deja} h de travail estimées") + (f" ; {len(todo)} TODO" if todo else "") + ".",
        "Docs déjà là : " + (", ".join(d["chemin"] for d in docs[:6]) or "aucune") + " ; je n'écrase rien (fichiers *.studio.md ou bloc délimité avec ton accord).",
    ]
    return {
        "version": 1, "outil": "adoption.py", "cree_le": maintenant(), "mode": "adoption",
        "projet": {"nom": nom, "fichiers": len(fichiers), "tronque": tronque},
        "moteur": moteur,
        "scenes": {"nombre": len(scenes), "niveaux": [s["chemin"] for s in niveaux][:30], "liste": scenes[:60], "principale": (moteur.get("details") or {}).get("scene_principale")},
        "code": {"fichiers": len(scripts), "lignes": lignes_tot, "langages": langs, "scripts": scripts[:60]},
        "systemes": systemes, "assets": assets, "docs": docs[:40], "pitch_readme": pitch_readme,
        "conventions": conv, "tests": tests, "todo": {"nombre": len(todo), "exemples": todo[:20]}, "git": git_inf,
        "calibrage": calibrage, "deductions": {"sures": sures, "probables": probables},
        "existant": existant, "manques": manques, "postes_proposes": postes,
        "fichiers_proteges": proteges, "agents_existants": agents, "resume": resume,
    }


def resume_md(a):
    l = ["# Analyse du projet (adoption)", "", f"Analyse du {a['cree_le']} ; rien n'a été modifié dans le projet.", "", "## En bref", ""]
    l += [f"- {x}" for x in a["resume"]]
    l += ["", "## Ce qui existe déjà (jalon J0)", "", "| Élément | Preuve | Poste |", "|---|---|---|"]
    l += [f"| {e['titre']} | `{e['preuve']}` | {e['poste']} |" for e in a["existant"]]
    l += ["", "## Déduit du projet", "", "| Question | Valeur | Sûr | Pourquoi |", "|---|---|---|---|"]
    for sorte, sur in (("sures", "oui"), ("probables", "★")):
        for k, v in a["deductions"][sorte].items():
            l.append(f"| `{k}` | {v['valeur'] if not isinstance(v['valeur'], list) else ', '.join(v['valeur'])} | {sur} | {v['raison']} |")
    c = a["calibrage"]
    l += ["", "## Calibrage des estimations", "", f"- Travail déjà fait : ≈ {c['heures_deja_estimees']} h ({c['methode']}).",
          f"- Même travail selon les estimations du studio : {c['heures_standard_de_l_existant']} h → facteur {c['facteur']}.",
          f"- Rythme observé : {c['heures_par_semaine_observees'] or '?'} h par semaine."]
    if a["conventions"]:
        l += ["", "## Conventions de code (à respecter)", ""] + [f"- {k} : {v}" for k, v in a["conventions"].items()]
    l += ["", "## Ce qui manque", ""] + [f"- {x}" for x in a["manques"] or ["rien d'évident"]]
    l += ["", "## Fichiers protégés", "", "| Fichier | Ce que fait le studio |", "|---|---|"]
    lib = {"a_cote": "écrit à côté : `{c}`", "bloc": "bloc délimité `<!-- studio-gamedev -->` ajouté à la fin, **après accord**", "bloc_gitignore": "bloc `.studio/` ajouté seulement s'il manque"}
    l += [f"| `{p['chemin']}` | {lib[p['action']].format(c=p['cible'])} |" for p in a["fichiers_proteges"]]
    if a["todo"]["exemples"]:
        l += ["", f"## TODO trouvés ({a['todo']['nombre']})", ""] + [f"- `{t['ou']}` {t['texte']}" for t in a["todo"]["exemples"][:10]]
    return "\n".join(l) + "\n"


def cmd_analyser(projet, sec, nouvelle_photo=False):
    a = analyser(projet)
    if not sec:
        st = os.path.join(projet, ".studio")
        fichiers, _ = parcourir(projet)
        ecrire(os.path.join(st, "analyse_projet.json"), a)
        ecrire(os.path.join(st, "analyse_projet.md"), resume_md(a))
        if nouvelle_photo or not os.path.isfile(os.path.join(st, "empreintes_adoption.json")):   # la première photo fait foi
            ecrire(os.path.join(st, "empreintes_adoption.json"), {"cree_le": maintenant(), "fichiers": prendre_empreintes(projet, fichiers)})
    print("\n".join(a["resume"]))
    return a


# ---------------------------------------------------------------------------- pré-remplissage
def cmd_preremplir(projet):
    st = os.path.join(projet, ".studio")
    a = lire_json(os.path.join(st, "analyse_projet.json"))
    if not a:
        raise SystemExit("lance d'abord : adoption.py analyser --projet <projet>")
    chemin = os.path.join(st, "reponses_questionnaire.json")
    q = lire_json(chemin) or {"version": 1, "etat": "en_cours", "langue": "fr", "cree_le": maintenant(), "reponses": {}}
    if q.get("etat") == "termine":
        raise SystemExit("questionnaire déjà terminé : rien à pré-remplir")
    q["mode"] = "adoption"
    q["analyse"] = ".studio/analyse_projet.json"
    rep = q.setdefault("reponses", {})
    t = maintenant()
    sures = dict(a["deductions"]["sures"])
    sures["accueil.mode"] = {"valeur": "rapide", "raison": "adoption d'un projet existant : questionnaire raccourci"}
    for k, v in sures.items():
        if k not in rep or rep[k].get("source") != "utilisateur":   # une réponse de l'utilisateur n'est jamais remplacée
            rep[k] = {"valeur": v["valeur"], "source": "deduit", "via": "analyse", "raison": v["raison"][:300], "t": t}
    q["maj"] = t
    ecrire(chemin, q)
    ded = lire_json(os.path.join(st, "deductions.json")) or {}
    ded.update({"maj": t,
                "fixes": {**(ded.get("fixes") or {}), **{k: {"valeur": v["valeur"], "raison": v["raison"]} for k, v in sures.items()}},
                "recommandes": {**(ded.get("recommandes") or {}), **{k: v["valeur"] for k, v in a["deductions"]["probables"].items()}},
                "message_assistant": "Je reprends ton projet ! J'ai lu ce qui existe (" + a["resume"][1].rstrip(".") + "). Je ne te demande que ce qui manque : ta vision, ton ambition, tes envies."})
    props = ded.setdefault("propositions", {})
    if a.get("pitch_readme"):
        props["vision.pitch"] = [a["pitch_readme"]]
    ecrire(os.path.join(st, "deductions.json"), ded)
    print(f"{len(sures)} réponses déduites (mode adoption), {len(a['deductions']['probables'])} ★ proposées ; message d'accueil écrit")


# ---------------------------------------------------------------------------- garde-fous
def bloc_remplace(texte, contenu, nl):
    bloc = DEBUT_BLOC + nl + contenu.strip("\r\n").replace("\r\n", "\n").replace("\n", nl) + nl + FIN_BLOC + nl
    i = texte.find(DEBUT_BLOC)
    if i >= 0:
        j = texte.find(FIN_BLOC, i)
        if j < 0:
            raise SystemExit("bloc studio-gamedev ouvert mais jamais fermé : corrige à la main")
        fin = j + len(FIN_BLOC)
        if texte[fin:fin + len(nl)] == nl:
            fin += len(nl)
        return texte[:i] + bloc + texte[fin:]
    if not texte:
        return bloc
    return texte + ("" if texte.endswith(("\n", "\r")) else nl) + nl + bloc


def fichier_sur(projet, nom):
    ch = os.path.join(projet, nom)
    if not dans_projet(projet, ch) or os.path.islink(ch):
        raise SystemExit("refus : fichier hors du projet ou lien symbolique")
    return ch


def cmd_bloc(projet, nom, contenu_fichier):
    ch = fichier_sur(projet, nom)
    with open(contenu_fichier, encoding="utf-8-sig") as f:
        contenu = f.read()
    if DEBUT_BLOC in contenu or FIN_BLOC in contenu:
        raise SystemExit("le contenu ne doit pas contenir les marques du bloc")
    brut = open(ch, "rb").read() if os.path.isfile(ch) else b""
    texte = brut.decode("utf-8")
    nl = "\r\n" if "\r\n" in texte else "\n"
    neuf = bloc_remplace(texte, contenu, nl)
    if neuf == texte:
        print(f"{nom} : bloc déjà à jour")
        return
    with open(ch + ".tmp", "wb") as f:
        f.write(neuf.encode("utf-8"))
    os.replace(ch + ".tmp", ch)
    print(f"{nom} : bloc studio-gamedev {'remplacé' if DEBUT_BLOC in texte else 'ajouté à la fin'} ; le reste du fichier est intact")


def cmd_gitignore(projet):
    ch = fichier_sur(projet, ".gitignore")
    texte = open(ch, "rb").read().decode("utf-8", "replace") if os.path.isfile(ch) else ""
    lignes = {x.strip() for x in texte.splitlines()}
    if ".studio/*" in lignes or ".studio/" in lignes or ".studio" in lignes:
        print(".gitignore : bloc .studio/ déjà présent, rien à faire")
        return
    nl = "\r\n" if "\r\n" in texte else "\n"
    ajout = ("" if not texte or texte.endswith("\n") else nl) + (nl if texte else "") + BLOC_GITIGNORE.replace("\n", nl)
    with open(ch, "ab") as f:
        f.write(ajout.encode("utf-8"))
    print(".gitignore : bloc .studio/ ajouté à la fin")


def cmd_verifier(projet, accords):
    st = os.path.join(projet, ".studio")
    ref = (lire_json(os.path.join(st, "empreintes_adoption.json")) or {}).get("fichiers")
    if ref is None:
        raise SystemExit("pas d'empreintes : lance d'abord adoption.py analyser")
    accords = {x.replace("\\", "/") for x in accords or []}
    actuels, _ = parcourir(projet)
    actuels = set(actuels)
    fautes, permis, nouveaux = [], [], []
    for f, e in ref.items():
        ch = os.path.join(projet, f)
        if f not in actuels:
            fautes.append(f"supprimé : {f}")
            continue
        if empreinte(ch) == e["sha256"]:
            continue
        taille = os.path.getsize(ch)
        prefixe = taille >= e["taille"] and empreinte(ch, e["taille"]) == e["sha256"]
        ajout = open(ch, "rb").read()[e["taille"]:].decode("utf-8", "replace") if prefixe else ""
        if prefixe and f == ".gitignore" and ajout.strip().replace("\r\n", "\n") == BLOC_GITIGNORE.strip():
            permis.append(f"{f} : bloc .studio/ ajouté")
        elif prefixe and ajout.strip().startswith(DEBUT_BLOC) and ajout.strip().endswith(FIN_BLOC) and ajout.count(DEBUT_BLOC) == 1:
            (permis if f in accords else fautes).append(f"{f} : bloc délimité ajouté" + ("" if f in accords else " SANS accord noté (--accord)"))
        else:
            fautes.append(f"modifié : {f}")
    for f in sorted(actuels - set(ref)):
        nouveaux.append(f)
    print(f"{len(ref)} fichiers existants comparés ; {len(fautes)} faute(s), {len(permis)} ajout(s) permis, {len(nouveaux)} fichier(s) nouveau(x)")
    for x in permis:
        print("  ok  ", x)
    for x in nouveaux:
        print("  neuf", x)
    for x in fautes:
        print("  NON ", x)
    return not fautes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("commande", choices=["analyser", "preremplir", "verifier", "gitignore", "bloc"])
    ap.add_argument("--projet", required=True)
    ap.add_argument("--sec", action="store_true", help="analyser : affiche seulement, n'écrit rien")
    ap.add_argument("--nouvelle-photo", action="store_true", help="analyser : reprend les empreintes (sinon la première photo fait foi)")
    ap.add_argument("--accord", nargs="*", default=[], help="verifier : fichiers où un bloc délimité a été accepté")
    ap.add_argument("--fichier", help="bloc : fichier du projet (ex. CLAUDE.md)")
    ap.add_argument("--contenu", help="bloc : fichier texte du contenu du bloc")
    a = ap.parse_args()
    projet = os.path.abspath(a.projet)
    if not os.path.isdir(projet):
        raise SystemExit("dossier du projet introuvable")
    if a.commande == "analyser":
        cmd_analyser(projet, a.sec, a.nouvelle_photo)
    elif a.commande == "preremplir":
        cmd_preremplir(projet)
    elif a.commande == "verifier":
        sys.exit(0 if cmd_verifier(projet, a.accord) else 1)
    elif a.commande == "gitignore":
        cmd_gitignore(projet)
    elif a.commande == "bloc":
        if not a.fichier or not a.contenu:
            raise SystemExit("usage : bloc --fichier CLAUDE.md --contenu <fichier>")
        cmd_bloc(projet, a.fichier, a.contenu)


if __name__ == "__main__":
    main()
