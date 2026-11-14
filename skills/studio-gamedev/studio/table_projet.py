"""studio/table_projet.py : ce que la TABLE au milieu du bureau montre pour CE projet (paquet S4).

La table matérialise toujours le projet développé dans le studio : une maquette / un diorama de SON jeu (son monde,
son lieu phare, son personnage, son genre), jamais celui d'un autre projet. Elle est tirée des données du projet :
réponses du questionnaire, GDD (docs/GDD.md ou docs/GDD.studio.md), DA validée (.studio/da.json), roadmap, captures du
jeu si elles existent. Elle évolue : plus détaillée à chaque jalon fini (5 niveaux de détail), elle adopte la palette
de la DA dès qu'elle est validée, et s'anime quand c'est utile (eau qui coule, brume, lumières, petites unités).
Sans données : une maquette neutre et belle.

Sortie : <projet>/.studio/table_projet.json
  theme, description {fr,en}, detail (1-5), palette, elements[] (plateau normalisé 0..1, hauteurs en unités de table,
  matériau, animation), animations[], sprites_a_produire[] (ce qu'il faut dessiner ou pré-rendre, avec l'outil conseillé),
  references[] (captures du jeu), signature (le dessin n'est refait que si elle change).
Le dessin (canevas isométrique de paliers.js) lit ce fichier ; il respecte prefers-reduced-motion (animations figées).

Python standard. Lecture seule hors de <projet>/.studio/.
Ligne de commande : python table_projet.py <projet> [--ecrire]
"""
import hashlib
import json
import os
import random
import re
import sys
import unicodedata

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import jsonio  # noqa: E402  (C4)
import style_paliers  # noqa: E402

FAITS = ("verse", "ecart")


def T(fr, en):
    return {"fr": fr, "en": en}


# Thèmes génériques : mots (FR/EN, sans accents), genres et climats du questionnaire qui y mènent.
THEMES = {
    "vallee_chateau": dict(nom=T("Vallée et château", "Valley and castle"), mots=["chateau", "castle", "forteresse", "fortress", "royaume", "kingdom", "medieval", "chevalier", "knight", "seigneur", "vallee", "valley"],
                           genres=["rpg", "action_aventure"], climats=[], phare=T("un château sur son éperon", "a castle on its spur"),
                           unites=T("cavaliers et villageois", "riders and villagers"), eau="riviere"),
    "ville": dict(nom=T("Ville", "City"), mots=["ville", "city", "urbain", "urban", "rue", "street", "metro", "quartier", "district", "gang", "police", "building", "immeuble"],
                  genres=["gestion", "simulation"], climats=["ville"], phare=T("un îlot d'immeubles et sa tour", "a city block and its tower"),
                  unites=T("voitures et passants", "cars and passers-by"), eau="canal"),
    "vaisseau": dict(nom=T("Vaisseau", "Starship"), mots=["vaisseau", "spaceship", "starship", "station", "espace", "space", "galaxie", "galaxy", "planete", "planet", "orbite", "orbit", "alien"],
                     genres=[], climats=["espace"], phare=T("un vaisseau posé sur son pas de tir", "a starship on its launch pad"),
                     unites=T("drones et navettes", "drones and shuttles"), eau=None),
    "donjon": dict(nom=T("Donjon", "Dungeon"), mots=["donjon", "dungeon", "crypte", "crypt", "caverne", "cavern", "grotte", "cave", "souterrain", "catacombe", "labyrinthe", "maze"],
                   genres=["roguelike", "horreur"], climats=["souterrain"], phare=T("des salles en coupe et leurs torches", "cut-away rooms and their torches"),
                   unites=T("héros et monstres", "heroes and monsters"), eau="lave"),
    "circuit": dict(nom=T("Circuit", "Race track"), mots=["course", "race", "racing", "circuit", "voiture", "car", "kart", "drift", "pilote", "driver", "rallye", "rally"],
                    genres=["course", "sport"], climats=[], phare=T("une boucle de circuit et ses tribunes", "a track loop and its stands"),
                    unites=T("bolides", "racers"), eau=None),
    "plateau_cartes": dict(nom=T("Plateau de cartes", "Card board"), mots=["carte a jouer", "jeu de cartes", "card game", "deck", "plateau", "board game", "jeton", "token"],
                           genres=["cartes", "strategie"], climats=[], phare=T("un plateau, ses cartes et ses jetons", "a board, its cards and tokens"),
                           unites=T("pions", "pawns"), eau=None),
    "ile": dict(nom=T("Île", "Island"), mots=["ile", "island", "tropical", "plage", "beach", "pirate", "archipel", "lagon", "lagoon"],
                genres=[], climats=["tropical"], phare=T("une île, son phare et son ponton", "an island, its lighthouse and pier"),
                unites=T("barques et oiseaux", "boats and birds"), eau="mer"),
    "foret": dict(nom=T("Forêt", "Forest"), mots=["foret", "forest", "bois", "woods", "camp", "survie", "survival", "cabane", "cabin", "chasse", "hunt"],
                  genres=["survie"], climats=["foret"], phare=T("un camp et son feu au cœur des arbres", "a camp and its fire among the trees"),
                  unites=T("animaux et survivants", "animals and survivors"), eau="riviere"),
    "montagne": dict(nom=T("Montagne", "Mountain"), mots=["montagne", "mountain", "neige", "snow", "sommet", "summit", "glacier", "col", "alpin", "alpine"],
                     genres=[], climats=["montagne"], phare=T("un sommet enneigé et son refuge", "a snowy peak and its hut"),
                     unites=T("grimpeurs", "climbers"), eau="torrent"),
    "desert": dict(nom=T("Désert", "Desert"), mots=["desert", "dune", "oasis", "sable", "sand", "canyon"],
                   genres=[], climats=["desert"], phare=T("une oasis entre les dunes", "an oasis between the dunes"),
                   unites=T("caravane", "caravan"), eau="oasis"),
    "ocean": dict(nom=T("Océan", "Ocean"), mots=["ocean", "mer", "sea", "bateau", "ship", "sous-marin", "submarine", "navire", "port", "harbour", "harbor"],
                  genres=[], climats=["mer"], phare=T("un navire sur une mer en relief", "a ship on a sculpted sea"),
                  unites=T("bateaux et poissons", "boats and fish"), eau="mer"),
    "arene": dict(nom=T("Arène", "Arena"), mots=["arene", "arena", "versus", "duel", "colisee", "colosseum", "gladiateur", "gladiator", "tournoi", "tournament"],
                  genres=["fps"], climats=[], phare=T("une arène et ses gradins", "an arena and its stands"),
                  unites=T("combattants", "fighters"), eau=None),
    "plateforme": dict(nom=T("Plateformes", "Platforms"), mots=["plateforme", "platform", "platformer", "saut", "jump", "sauter"],
                       genres=["plateforme", "puzzle", "rythme"], climats=[], phare=T("des blocs suspendus et un drapeau d'arrivée", "floating blocks and a finish flag"),
                       unites=T("le héros qui saute", "the jumping hero"), eau="cascade"),
    "ferme": dict(nom=T("Ferme et village", "Farm and village"), mots=["ferme", "farm", "village", "cozy", "potager", "garden", "champ", "field", "recolte", "harvest"],
                  genres=["gestion", "bac_a_sable"], climats=[], phare=T("une ferme, ses champs et son moulin", "a farm, its fields and its mill"),
                  unites=T("animaux de la ferme", "farm animals"), eau="riviere"),
    "neutre": dict(nom=T("Maquette neutre", "Neutral model"), mots=[], genres=[], climats=["imaginaire"],
                   phare=T("une tour-balise au milieu de reliefs sculptés", "a beacon tower amid sculpted terrain"),
                   unites=T("lucioles", "fireflies"), eau="bassin"),
}

PALETTES_REPONSE = {   # même famille que paliers.js PALETTES (da.palette du questionnaire), sans DA validée
    "chaude": dict(sol="#b08a5a", relief="#8f6a44", eau="#4f8fb0", vegetation="#7d8f3c", phare="#d9893b", toit="#c4543a", lumiere="#ffcf8a"),
    "froide": dict(sol="#8a97a3", relief="#6b7884", eau="#4f8cc9", vegetation="#4f7f6a", phare="#d6dee4", toit="#4f8cc9", lumiere="#e3efff"),
    "contrastee": dict(sol="#6b6560", relief="#4a4440", eau="#2f7fb0", vegetation="#3f7a52", phare="#ecebe6", toit="#e2483a", lumiere="#fff1d6"),
    "sourde": dict(sol="#a39a88", relief="#857c6c", eau="#7f9aa3", vegetation="#7d8a6a", phare="#d9d3c5", toit="#b08a6e", lumiere="#f3e3c4"),
    "vive": dict(sol="#9bc46a", relief="#6fa257", eau="#2fbfd6", vegetation="#3fae5e", phare="#f3ede1", toit="#ef5d8f", lumiere="#ffe3a8"),
    "defaut": dict(sol="#a3a29b", relief="#86857e", eau="#6f9fb8", vegetation="#7f9a72", phare="#e9e6dc", toit="#b98532", lumiere="#ffd59a"),
}
CARTON = dict(sol="#d8d2c4", relief="#c4bdac", eau="#b9c6cc", vegetation="#bfc2b0", phare="#ece7da", toit="#cfc6b4", lumiere="#fff4dc")
DETAIL_NOMS = {1: T("maquette en carton", "cardboard model"), 2: T("relief et eau", "terrain and water"),
               3: T("lieu phare", "landmark"), 4: T("décor et chemins", "props and paths"), 5: T("vivante : unités, lumières, brume", "alive: units, lights, mist")}


def sans_accent(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s or "").lower()) if unicodedata.category(c) != "Mn")


def lire(ch, n=40000):
    try:
        with open(ch, encoding="utf-8-sig", errors="replace") as f:
            return f.read(n)
    except OSError:
        return ""


def lire_json(ch, defaut):
    return jsonio.lire(ch, defaut)


def donnees(projet):
    st = os.path.join(projet, ".studio")
    rq = lire_json(os.path.join(st, "reponses_questionnaire.json"), {})
    rep = {k: (v.get("valeur") if isinstance(v, dict) else v) for k, v in (rq.get("reponses") or {}).items()} if isinstance(rq, dict) else {}
    gdd = ""
    for n in ("docs/GDD.md", "docs/GDD.studio.md", "docs/gdd.md"):
        gdd = lire(os.path.join(projet, *n.split("/")))
        if gdd:
            break
    an = lire_json(os.path.join(st, "analyse_projet.json"), {})          # projet adopté : déductions et pitch du README
    if isinstance(an, dict):
        ded = an.get("deductions") if isinstance(an.get("deductions"), dict) else {}
        for groupe in ("sures", "probables"):
            for k, v in (ded.get(groupe) or {}).items():
                if rep.get(k) is None and isinstance(v, dict):
                    rep[k] = v.get("valeur")
        if not rep.get("vision.pitch") and an.get("pitch_readme"):
            rep["vision.pitch"] = an["pitch_readme"]
    rm = lire_json(os.path.join(st, "roadmap.json"), None)
    conf = lire_json(os.path.join(st, "studio.config.json"), {})
    if not conf.get("nom_projet") and isinstance(an, dict) and isinstance(an.get("projet"), dict) and an["projet"].get("nom"):
        conf = dict(conf, nom_projet=an["projet"]["nom"])
    da, _ = style_paliers.lire_da(projet)
    return rep, gdd, rm, conf, da


def choisir_theme(rep, gdd, nom_projet=""):
    """(thème, scores, raisons). Questionnaire d'abord (poids 3), puis pitch et lieu (2), puis GDD (1, plafonné)."""
    scores, raisons = {k: 0.0 for k in THEMES}, {k: [] for k in THEMES}
    genre, climat, struct = rep.get("genre.principal"), rep.get("monde.climat"), rep.get("monde.structure")
    for k, t in THEMES.items():
        if genre in t["genres"]:
            scores[k] += 3
            raisons[k].append(f"genre {genre}")
        if climat in t["climats"]:
            scores[k] += 3.5
            raisons[k].append(f"climat {climat}")
    if struct == "arene":
        scores["arene"] += 2
        raisons["arene"].append("monde en arène")
    textes = [(sans_accent(" ".join(str(rep.get(c) or "") for c in ("vision.pitch", "monde.lieu", "vision.references"))), 2.0, 6),
              (sans_accent(gdd), 1.0, 4), (sans_accent(nom_projet), 1.0, 2)]
    for txt, poids, plafond in textes:
        if not txt.strip():
            continue
        for k, t in THEMES.items():
            n = sum(len(re.findall(r"\b" + re.escape(m) + r"s?\b", txt)) for m in t["mots"])
            if n:
                scores[k] += poids * min(plafond, n)
                raisons[k].append(f"{n} mot(s) du thème")
    meilleur = max(scores, key=lambda k: (scores[k], k == "neutre"))
    if scores[meilleur] < 2:
        meilleur = "neutre"
    return meilleur, {k: v for k, v in scores.items() if v}, raisons[meilleur]


def niveau_detail(rm):
    """1 (carton) à 5 (vivante) : 1 + jalons finis hors J0 ; repli sur l'avancement si la roadmap n'a pas de jalons fermés."""
    if not isinstance(rm, dict) or not isinstance(rm.get("jalons"), list):
        return 1
    jal = [j for j in rm["jalons"] if isinstance(j, dict) and str(j.get("id", "")).upper() != "J0"]
    finis = sum(1 for j in jal if j.get("taches") and all(isinstance(t, dict) and t.get("statut") in FAITS for t in j["taches"]))
    taches = [t for j in jal for t in (j.get("taches") or []) if isinstance(t, dict)]
    pct = 100 * sum(1 for t in taches if t.get("statut") in FAITS) / len(taches) if taches else 0
    return max(1, min(5, max(1 + finis, 1 + int(pct // 25))))


def palette_table(rep, da, detail):
    if style_paliers.da_valide(da) and da.get("palette"):
        p, b = da["palette"], da["palette"].get("bureau") or {}
        sol = b.get("sol") or style_paliers.mix(p.get("surface") or p["fond"], p["accent"], 0.25)
        pal = dict(sol=sol, relief=style_paliers.mix(sol, "#000000", 0.18), eau=p.get("accent2") or style_paliers.mix(p["accent"], "#3a7fb0", 0.6),
                   vegetation=p.get("succes") or style_paliers.mix(sol, "#3f7a52", 0.6), phare=b.get("mur") or style_paliers.mix(p["texte"], sol, 0.2),
                   toit=p["accent"], lumiere=b.get("lumiere") or style_paliers.mix(p["accent"], "#ffffff", 0.6))
        return pal, "da"
    if detail == 1:
        return dict(CARTON), "carton"
    return dict(PALETTES_REPONSE.get(rep.get("da.palette")) or PALETTES_REPONSE["defaut"]), ("questionnaire" if rep.get("da.palette") else "neutre")


def el(type_, x, y, w, h, z, couleur, detail, anim=None, **k):
    d = {"type": type_, "x": round(x, 3), "y": round(y, 3), "w": round(w, 3), "h": round(h, 3), "z": round(z, 3),
         "couleur": couleur, "detail": detail}
    if anim:
        d["anime"] = anim
    d.update(k)
    return d


def composer(theme, pal, detail, alea):
    """Éléments du diorama sur un plateau 0..1 (x vers la droite, y vers le fond), z = hauteur."""
    E = [el("socle", 0, 0, 1, 1, 0.06, "#3a3330", 1, materiau="bois_sombre"),
         el("terrain", 0.04, 0.04, 0.92, 0.92, 0.02, pal["sol"], 1, materiau="carton" if detail == 1 else "peint")]
    t = THEMES[theme]
    # relief commun : collines placées au hasard stable du projet
    for i in range(3 + alea.randint(0, 2)):
        x, y = alea.uniform(0.08, 0.7), alea.uniform(0.08, 0.7)
        if theme in ("circuit", "plateau_cartes", "arene"):
            break
        E.append(el("relief", x, y, alea.uniform(0.14, 0.24), alea.uniform(0.12, 0.2), alea.uniform(0.04, 0.12), pal["relief"], 2))
    eau = t["eau"]
    if eau in ("riviere", "torrent", "canal"):
        pts = [(0.0, alea.uniform(0.55, 0.75))]
        for k in range(1, 6):
            pts.append((k / 5, max(0.1, min(0.9, pts[-1][1] + alea.uniform(-0.12, 0.12)))))
        E.append(el("eau", 0, 0, 1, 0.08, 0.01, pal["eau"], 2, "ecoulement", trace=[[round(a, 3), round(b, 3)] for a, b in pts], forme=eau))
    elif eau in ("mer", "lave"):
        E.append(el("eau", 0, 0.62, 1, 0.38, 0.005, "#c4542a" if eau == "lave" else pal["eau"], 2, "vagues" if eau == "mer" else "bouillonne", forme=eau))
    elif eau in ("oasis", "bassin"):
        E.append(el("eau", 0.58, 0.58, 0.16, 0.12, 0.005, pal["eau"], 2, "reflets", forme=eau))
    elif eau == "cascade":
        E.append(el("eau", 0.78, 0.1, 0.06, 0.5, 0.25, pal["eau"], 2, "chute", forme=eau))
    # lieu phare (détail 3)
    P = {"vallee_chateau": [el("phare", 0.42, 0.3, 0.18, 0.16, 0.28, pal["phare"], 3, forme="chateau", tours=4, toit=pal["toit"])],
         "ville": [el("phare", 0.4 + i * 0.07, 0.35, 0.06, 0.06, 0.12 + 0.05 * (i % 3), pal["phare"], 3, forme="immeuble", toit=pal["toit"]) for i in range(5)]
                  + [el("phare", 0.47, 0.25, 0.07, 0.07, 0.42, pal["phare"], 3, forme="tour", toit=pal["toit"])],
         "vaisseau": [el("phare", 0.36, 0.34, 0.3, 0.14, 0.12, pal["phare"], 3, forme="vaisseau", toit=pal["toit"])],
         "donjon": [el("phare", 0.2 + (i % 3) * 0.22, 0.2 + (i // 3) * 0.26, 0.18, 0.2, 0.08, pal["phare"], 3, forme="salle") for i in range(6)],
         "circuit": [el("phare", 0.12, 0.18, 0.76, 0.6, 0.01, "#4a4a4a", 3, forme="piste_boucle"), el("phare", 0.2, 0.08, 0.6, 0.08, 0.1, pal["phare"], 3, forme="tribune", toit=pal["toit"])],
         "plateau_cartes": [el("phare", 0.18, 0.18, 0.64, 0.64, 0.02, pal["phare"], 3, forme="plateau")]
                           + [el("phare", 0.24 + i * 0.1, 0.7, 0.07, 0.1, 0.03, pal["toit"], 3, forme="carte") for i in range(5)],
         "ile": [el("phare", 0.3, 0.25, 0.36, 0.3, 0.05, pal["sol"], 3, forme="ile"), el("phare", 0.55, 0.3, 0.04, 0.04, 0.32, pal["phare"], 3, forme="phare_marin", toit=pal["toit"])],
         "foret": [el("phare", 0.45, 0.42, 0.1, 0.1, 0.06, pal["phare"], 3, forme="camp"), el("lumiere", 0.49, 0.47, 0.02, 0.02, 0.05, pal["lumiere"], 3, "flamme", forme="feu")],
         "montagne": [el("phare", 0.32, 0.22, 0.36, 0.34, 0.4, pal["relief"], 3, forme="sommet", neige="#f4f6f8"), el("phare", 0.62, 0.5, 0.07, 0.06, 0.08, pal["phare"], 3, forme="refuge", toit=pal["toit"])],
         "desert": [el("phare", 0.5, 0.5, 0.26, 0.22, 0.06, pal["vegetation"], 3, forme="oasis")],
         "ocean": [el("phare", 0.38, 0.66, 0.22, 0.08, 0.1, pal["phare"], 3, "tangage", forme="navire", toit=pal["toit"])],
         "arene": [el("phare", 0.2, 0.2, 0.6, 0.6, 0.1, pal["phare"], 3, forme="arene", toit=pal["toit"])],
         "plateforme": [el("phare", 0.12 + i * 0.15, 0.3 + (i % 2) * 0.15, 0.1, 0.06, 0.12 + i * 0.05, pal["phare"], 3, "flottement", forme="bloc") for i in range(5)]
                       + [el("phare", 0.85, 0.35, 0.02, 0.02, 0.45, pal["toit"], 3, "drapeau", forme="drapeau")],
         "ferme": [el("phare", 0.4, 0.3, 0.14, 0.1, 0.12, pal["phare"], 3, forme="ferme", toit=pal["toit"]), el("phare", 0.6, 0.25, 0.05, 0.05, 0.22, pal["phare"], 3, "rotation", forme="moulin")]
                  + [el("phare", 0.2 + i * 0.12, 0.6, 0.1, 0.14, 0.01, pal["vegetation"], 3, forme="champ") for i in range(3)],
         "neutre": [el("phare", 0.46, 0.4, 0.08, 0.08, 0.34, pal["phare"], 3, forme="tour_balise", toit=pal["toit"]),
                    el("lumiere", 0.49, 0.43, 0.02, 0.02, 0.36, pal["lumiere"], 3, "pulsation", forme="balise")]}
    E += P[theme]
    # décor et chemins (détail 4)
    if theme not in ("plateau_cartes", "circuit", "arene", "ocean"):
        for _ in range(8 + alea.randint(0, 6)):
            forme = {"desert": "cactus", "ile": "palmier", "montagne": "sapin", "donjon": "pilier", "vaisseau": "antenne", "ville": "lampadaire"}.get(theme, "arbre")
            E.append(el("vegetation", alea.uniform(0.06, 0.9), alea.uniform(0.06, 0.9), 0.04, 0.04, alea.uniform(0.05, 0.1), pal["vegetation"], 4, forme=forme))
        E.append(el("route", 0.1, 0.5, 0.8, 0.03, 0.002, style_paliers.mix(pal["sol"], "#000000", 0.25), 4, forme="chemin"))
    # vivante (détail 5) : unités qui bougent, lumières, brume
    for i in range(4):
        E.append(el("unite", alea.uniform(0.15, 0.85), alea.uniform(0.15, 0.85), 0.015, 0.015, 0.02, pal["toit"], 5, "patrouille",
                    vitesse=round(alea.uniform(0.02, 0.06), 3)))
    E.append(el("lumiere", 0.0, 0.0, 1, 1, 0.5, pal["lumiere"], 5, "scintillement", forme="lumieres_fenetres"))
    if theme in ("vallee_chateau", "foret", "montagne", "donjon", "neutre", "ocean", "ile"):
        E.append(el("brume", 0, 0.3, 1, 0.4, 0.1, "#ffffff", 5, "derive", opacite=0.18))
    if theme == "vaisseau":
        E.append(el("etoiles", 0, 0, 1, 1, 0.6, "#ffffff", 5, "scintillement"))
    return [e for e in E if e["detail"] <= detail]


def sprites(theme, detail, rep):
    style = rep.get("da.style") or ""
    img = rep.get("ia.images")
    m3d = rep.get("ia.modeles_3d")
    pre_rendu = style in ("realiste", "low_poly", "voxel") and detail >= 4
    outil = "blender" if pre_rendu else "canvas"
    if pre_rendu and m3d == "non":
        outil = "canvas"
    t = THEMES[theme]
    out = [{"id": "lieu_phare", "description": t["phare"], "taille_px": [256, 256], "vue": "isométrique 2:1",
            "outil": outil, "des_detail": 3},
           {"id": "unites", "description": t["unites"], "taille_px": [32, 32], "images": 4, "vue": "isométrique 2:1",
            "outil": "canvas", "des_detail": 5}]
    if img == "valide":
        out.append({"id": "texture_terrain", "description": T("texture du terrain dans la DA du jeu", "terrain texture in the game's art direction"),
                    "taille_px": [512, 512], "outil": "generation_image", "condition": T("licence et DA validées par l'utilisateur", "licence and art direction approved by the user"),
                    "des_detail": 4})
    return out


def references(projet, n=3):
    """Captures du jeu (lecture seule) : dossiers usuels, images récentes d'abord."""
    out = []
    for d in ("captures", "screenshots", "docs/captures", "docs/images", "press", "store"):
        ch = os.path.join(projet, *d.split("/"))
        if os.path.isdir(ch) and not os.path.islink(ch):
            for f in sorted(os.listdir(ch)):
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    out.append(d + "/" + f)
    return out[:n]


def calculer(projet):
    rep, gdd, rm, conf, da = donnees(projet)
    nom = str(conf.get("nom_projet") or os.path.basename(os.path.abspath(projet)))
    theme, scores, raisons = choisir_theme(rep, gdd, nom)
    detail = niveau_detail(rm)
    pal, source_pal = palette_table(rep, da, detail)
    graine = int(hashlib.sha256((nom + theme).encode("utf-8")).hexdigest()[:8], 16)
    elements = composer(theme, pal, detail, random.Random(graine))
    t = THEMES[theme]
    anims = sorted({e["anime"] for e in elements if e.get("anime")})
    desc = T(f"Maquette « {t['nom']['fr']} » : {t['phare']['fr']} ; détail {detail}/5 ({DETAIL_NOMS[detail]['fr']}).",
             f"\"{t['nom']['en']}\" model: {t['phare']['en']}; detail {detail}/5 ({DETAIL_NOMS[detail]['en']}).")
    res = {"version": 1, "theme": theme, "nom_theme": t["nom"], "description": desc, "detail": detail,
           "detail_nom": DETAIL_NOMS[detail], "prochain_detail": DETAIL_NOMS.get(detail + 1),
           "palette": pal, "source_palette": source_pal, "elements": elements, "animations": anims,
           "mouvement_reduit": "animations figées si prefers-reduced-motion", "sprites_a_produire": sprites(theme, detail, rep),
           "references": references(projet), "pourquoi": raisons, "scores": scores}
    res["signature"] = hashlib.sha256(json.dumps([theme, detail, pal, elements], sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return res


def ecrire(projet, res):
    ch = os.path.join(projet, ".studio", "table_projet.json")
    jsonio.ecrire(ch, res, newline="\n")


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if not a or a[0].startswith("-"):
        print(__doc__)
        return 2
    res = calculer(os.path.abspath(a[0]))
    if "--ecrire" in a:
        ecrire(os.path.abspath(a[0]), res)
    print(json.dumps({k: v for k, v in res.items() if k != "elements"}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
