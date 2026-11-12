"""Essai complet du studio gamedev : projet jetable, réponses fictives, roadmap.json conforme, serveur local.

Usage (Python 3.10+, bibliothèque standard) :
  python -I -B essai_complet.py preparer  [--dossier D]   crée le projet jetable (.studio/ : config, profil, progression)
  python -I -B essai_complet.py deduire   [--dossier D]   écrit deductions.json (comme Claude après le pitch)
  python -I -B essai_complet.py remplir   [--dossier D]   complète reponses_questionnaire.json avec des réponses fictives (★)
  python -I -B essai_complet.py roadmap   [--dossier D]   écrit .studio/roadmap.json et docs/ROADMAP.md depuis les réponses, puis vérifie
  python -I -B essai_complet.py verser J0 [--dossier D]   passe toutes les tâches du jalon à « verse » (le succès se débloque)
  python -I -B essai_complet.py verifier  [--dossier D]   vérifie roadmap.json (schéma, identifiants, dépendances, boucles)
  python -I -B essai_complet.py serveur   [--dossier D] [--port 8810]   lance serveur_studio.py (premier port libre, jamais 8790)
  python -I -B essai_complet.py tout      [--dossier D]   preparer + remplir + roadmap + verifier (sans serveur)
  python -I -B essai_complet.py travail   [--dossier D]   passe le studio en mode travail, avec 3 images d'essai pour le mur
  python -I -B essai_complet.py etat      [--dossier D]   un passage de studio_etat.py (etat.json, suggestions.json, taches_disponibles.json)
  python -I -B essai_complet.py progresser <poste> <pct> [--texte T] [--restant N]   écrit progression/<poste>.json
  python -I -B essai_complet.py rapport   [--dossier D]   écrit rapport_assistant.json (le rapport plein cadre s'ouvre)
  python -I -B essai_complet.py recrue <nom> [--dossier D]   vérifie la recrue : demande, fiche, définition d'agent
Le serveur de l'essai lance aussi studio_etat.py en boucle (--intervalle, 5 s par défaut) et l'arrête en sortant.

Le dossier par défaut est passé par --dossier ou la variable STUDIO_ESSAI ; le script refuse d'effacer
un dossier qui ne s'appelle pas « essai_skill ».
"""
import argparse
import datetime as dt
import json
import os
import shutil
import socket
import subprocess
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(ICI)
SKILL = os.path.dirname(STUDIO)
sys.dont_write_bytecode = True   # jamais de __pycache__ dans le dossier du skill
for _flux in (sys.stdout, sys.stderr):   # console Windows sans UTF-8 : « ★ » ne doit pas faire planter --help
    try:
        _flux.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass
PORTS_INTERDITS = {8790}   # port par défaut du vrai studio : l'essai ne le prend jamais (mémoire du navigateur séparée)


def ecrire(chemin, donnees):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        if isinstance(donnees, str):
            f.write(donnees)
        else:
            json.dump(donnees, f, ensure_ascii=False, indent=1)
    os.replace(tmp, chemin)


def lire(chemin, defaut=None):
    try:
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return defaut


def maintenant():
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def port_libre(p):
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", p))
            return True
        except OSError:
            return False


def choisir_port(p):
    for x in range(p, p + 60):
        if x not in PORTS_INTERDITS and port_libre(x):
            return x
    raise SystemExit("aucun port libre")


# ---------------------------------------------------------------------------- preparer
POSTES = [
    {"id": "direction", "nom": "Direction", "role": "Coordinateur : roadmap, décisions, versements", "couleur": "#b98532", "apparence": "casquette", "skills": ["gamedev:router"]},
    {"id": "integration-moteur", "nom": "Intégration moteur", "role": "La seule chaîne moteur : intègre, compile, teste, verse", "couleur": "#4d6f9c", "apparence": "casque", "skills": ["gamedev:godot-gdscript"]},
    {"id": "code-gameplay", "nom": "Code gameplay", "role": "Prépare la logique sans moteur, avec ses tests", "couleur": "#3f7a52", "apparence": "lunettes", "skills": ["gamedev:platformer"]},
    {"id": "art-da", "nom": "Art et DA", "role": "Bible de style, images cibles, assets", "couleur": "#a8432e", "apparence": "beret", "skills": ["gamedev:create-game-assets"]},
    {"id": "son", "nom": "Son", "role": "Ambiances, bruitages, musique", "couleur": "#7a5aa0", "apparence": "casque_audio", "skills": ["gamedev:audio-design"]},
]


def preparer(d, port):
    if os.path.basename(os.path.normpath(d)) != "essai_skill":
        raise SystemExit("refus : le dossier d'essai doit s'appeler essai_skill")
    if os.path.isdir(d):
        shutil.rmtree(d)
    st = os.path.join(d, ".studio")
    for sous in ("progression", "demandes", "demandes_vocales", "docs"):
        os.makedirs(os.path.join(st if sous != "docs" else d, sous), exist_ok=True)
    conf = lire(os.path.join(SKILL, "modeles", "studio.config.json"), {})
    conf.update({"mode": "accueil", "nom_projet": "Essai Lanterne", "langue": "fr", "dossier_projet": d.replace("\\", "/"),
                 "dossier_studio": (st).replace("\\", "/"), "dossier_donnees": (d + "/donnees").replace("\\", "/"),
                 "dossier_agents": (d + "/.claude/agents").replace("\\", "/"), "port": port, "postes": POSTES,
                 "theme": {"accent": "#b98532", "sol": "#8a6a48", "sol2": "#7d5f40", "mur": "#d9c9a6", "bois": "#a0744a"},
                 "sources_images": []})
    ecrire(os.path.join(st, "studio.config.json"), conf)
    profil = json.loads(open(os.path.join(SKILL, "modeles", "profil.json"), encoding="utf-8").read()
                        .replace("{{nom_maitre}}", "").replace("{{nom_assistant}}", ""))
    ecrire(os.path.join(st, "profil.json"), profil)
    # progression des postes : un qui travaille (temps donné), un qui travaille (fin à heure fixe), un fini sans étape restante
    fin = (dt.datetime.now() + dt.timedelta(minutes=50)).strftime("%H:%M")
    ecrire(os.path.join(st, "progression", "integration-moteur.json"), {"pct": 35, "texte": "Projet moteur et scène grise", "restant_min": 25})
    ecrire(os.path.join(st, "progression", "code-gameplay.json"), {"pct": 60, "texte": "Contrôles du personnage, tests", "fin": fin,
                                                                    "restantes": ["Saut et gravité", "Tests de collision"]})
    ecrire(os.path.join(st, "progression", "son.json"), {"pct": 100, "texte": "Bible sonore écrite"})
    ecrire(os.path.join(st, "demandes", "statuts.json"), {"art-da": {"statut": "en attente", "maj": maintenant(), "texte": "attend la bible de style"}})
    ecrire(os.path.join(st, "decisions.json"), [{"id": "dec-001", "titre": "Résolution de référence pour le prototype ?", "explication": "Elle fixe la taille des sprites et de l'interface.",
                                                 "choix": [{"id": "1080p", "libelle": "1920 × 1080"}, {"id": "720p", "libelle": "1280 × 720"}], "recommande": "1080p", "cree_le": maintenant()}])
    print("projet d'essai prêt :", d)


# ---------------------------------------------------------------------------- deduire
def deduire(d):
    ecrire(os.path.join(d, ".studio", "deductions.json"), {
        "maj": maintenant(),
        "recommandes": {"genre.principal": "plateforme", "camera.dimension": "2d", "camera.vue": "cote", "gameplay.verbe": "explorer", "moteur.nom": "godot", "da.style": "dessin_main"},
        "fixes": {},
        "propositions": {"vision.piliers": ["Lumière fragile", "Saut précis", "Forêt qui respire"], "assistant.nom": ["Lucette", "Bidule", "Mèche"]},
        "message_assistant": "Une luciole dans une forêt de nuit, j'adore. J'ai préparé quelques idées : dis-moi si je me trompe."})
    print("deductions.json écrit")


# ---------------------------------------------------------------------------- remplir
def remplir(d):
    """Complète les réponses manquantes avec le ★ (questions rapides), marquées « a_confirmer »."""
    chemin = os.path.join(d, ".studio", "reponses_questionnaire.json")
    q = lire(chemin, None) or {"version": 1, "etat": "en_cours", "mode": "rapide", "langue": "fr", "cree_le": maintenant(), "reponses": {}}
    questions = lire(os.path.join(STUDIO, "questions.fr.json"))["questions"]
    ded = lire(os.path.join(d, ".studio", "deductions.json"), {}) or {}
    fictives = {"accueil.nom": "Alex", "vision.pitch": "Une luciole traverse une forêt de nuit pour rallumer les lanternes de son village.", "assistant.nom": "Lucette"}
    for x in questions:
        if not x.get("rapide") or x["id"] in q["reponses"] or x["type"] == "personnage":
            continue
        v = fictives.get(x["id"], (ded.get("recommandes") or {}).get(x["id"], x.get("recommande")))
        if x["id"] == "accueil.mode":
            v = "rapide"
        q["reponses"][x["id"]] = {"valeur": v, "source": "utilisateur" if x["id"] in fictives else "a_confirmer", "via": "ecrit" if x["id"] in fictives else "passer", "t": maintenant()}
    q["maj"] = maintenant()
    ecrire(chemin, q)
    print(len(q["reponses"]), "réponses dans", chemin)


# ---------------------------------------------------------------------------- roadmap
def tache(jid, n, titre, critere, poste, moteur, h, dep, statut="a_faire"):
    return {"id": f"{jid}-{n:02d}", "titre": titre, "critere": critere, "poste": poste, "moteur": moteur, "estimation_h": h, "depend_de": dep, "statut": statut}


def generer_roadmap(d):
    rep = (lire(os.path.join(d, ".studio", "reponses_questionnaire.json"), {}) or {}).get("reponses", {})
    v = lambda k, df=None: (rep.get(k) or {}).get("valeur") or df
    moteur, verbe, style = v("moteur.nom", "godot"), v("gameplay.verbe", "explorer"), v("da.style", "stylise")
    taille = v("ambition.taille", "petit")
    hps = {"quelques_heures": 6, "soirs": 12, "plein": 35, "jam": 48}.get(v("ambition.temps", "soirs"), 12)
    debut = dt.date.today()
    t0 = maintenant()
    jalons = [
        ("J0", "Cadrage", "Le projet est décrit et le studio tourne.", "GDD, roadmap et décisions écrits ; studio en mode travail.", [],
         [("Questionnaire et documents", "GDD, ROADMAP et DECISIONS écrits", "direction", False, 1, []),
          ("Structure du dépôt", "dossiers et .gitignore du moteur en place", "direction", False, .5, ["J0-01"]),
          ("Projet moteur vide", f"le projet {moteur} s'ouvre sans erreur", "integration-moteur", True, 1, ["J0-02"]),
          ("Bible de style courte", f"style « {style} » décrit avec 3 images cibles validées", "art-da", False, 2, ["J0-01"]),
          ("Bible sonore courte", "ambiance et 5 sons clés décrits", "son", False, 1, ["J0-01"])],
         {"titre": "Les plans sont sur la table", "description": "Questionnaire fini, roadmap écrite.", "icone": "cartes/carnet.svg", "son": "moyen"}),
        ("J1", "Prototype jouable", f"Le verbe « {verbe} » est jouable dans une scène grise.", f"On peut {verbe} pendant 1 minute sans bug bloquant.", ["J0"],
         [("Scène grise", "une scène se lance avec sol et obstacles", "integration-moteur", True, 3, ["J0-03"]),
          ("Contrôles et caméra", "déplacement clavier et manette, test court", "code-gameplay", True, 6, ["J1-01"]),
          (f"Mécanique « {verbe} »", "la mécanique marche, 3 tests passent", "code-gameplay", False, 6, ["J1-02"]),
          ("Retour visuel minimal", "placeholders lisibles pour joueur et décor", "art-da", False, 3, ["J0-04"]),
          ("Sons de base", "pas, saut et ambiance jouent", "son", True, 2, ["J0-05", "J1-01"]),
          ("Version à essayer", "build lancée et guide « quoi regarder »", "integration-moteur", True, 1, ["J1-03", "J1-04", "J1-05"])],
         {"titre": "Ça bouge !", "description": "Premier prototype jouable.", "icone": "cartes/manette.svg", "son": "grand"}),
        ("J2", "Boucle centrale", "La boucle de jeu complète tourne.", "Une partie se joue du début à la fin en 5 minutes.", ["J1"],
         [("Objectif et victoire", "on peut gagner et perdre", "code-gameplay", False, 5, ["J1-03"]),
          ("Interface de jeu", "vie, objectif et pause affichés", "art-da", True, 4, ["J1-04"]),
          ("Sauvegarde", "la partie reprend après fermeture", "code-gameplay", False, 4, ["J2-01"]),
          ("Musique adaptative", "la musique change selon la tension", "son", True, 4, ["J1-05"]),
          ("Version à essayer", "build et guide", "integration-moteur", True, 1, ["J2-02", "J2-03", "J2-04"])],
         {"titre": "La boucle est bouclée", "description": "Une partie complète se joue.", "icone": "cartes/boucle.svg", "son": "grand"}),
    ]
    if taille not in ("prototype",):
        jalons.append(("J3", "Contenu et finition", "Assez de contenu pour une vraie partie, polie.", "3 niveaux finis, aucun bug bloquant connu.", ["J2"],
                       [("Niveaux 1 à 3", "3 niveaux jouables de bout en bout", "code-gameplay", True, 12, ["J2-01"]),
                        ("Assets finaux", "décors et personnage au style validé", "art-da", True, 14, ["J2-02"]),
                        ("Mixage", "volumes réglés, options son", "son", True, 3, ["J2-04"]),
                        ("Réglages et accessibilité", "touches remappables, sous-titres", "code-gameplay", True, 4, ["J3-01"]),
                        ("Version candidate", "build finale et guide", "integration-moteur", True, 2, ["J3-02", "J3-03", "J3-04"])],
                       {"titre": "Prêt à montrer", "description": "Le jeu tient debout.", "icone": "cartes/trophee.svg", "son": "grand"}))
    rm_jalons, fin = [], debut
    for jid, titre, but, critere, dep, taches, succes in jalons:
        tt = [tache(jid, i + 1, *x) for i, x in enumerate(taches)]
        fin = fin + dt.timedelta(days=max(1, round(7 * sum(x["estimation_h"] for x in tt) / hps)))
        succes = dict(succes, id=f"jalon-{jid}")
        rm_jalons.append({"id": jid, "titre": titre, "but": but, "critere_fin": critere, "depend_de": dep, "fin_visee": fin.isoformat(), "succes": succes, "taches": tt})
    # J0-01 est fait au moment où la roadmap est écrite
    rm_jalons[0]["taches"][0].update(statut="verse", preuve="essai", fait_le=t0)
    rm = {"version": 1, "langue": "fr", "projet": "Essai Lanterne", "cree_le": t0, "maj": t0,
          "sources": {"questionnaire": ".studio/reponses_questionnaire.json", "document": "docs/ROADMAP.md"},
          "rythme": {"heures_par_semaine": hps, "debut": debut.isoformat()},
          "niveau": {"xp_par_tache": 100, "xp_par_jalon": 500, "rangs": [{"niveau": 1, "nom": "Garage"}, {"niveau": 5, "nom": "Atelier de quartier"}, {"niveau": 10, "nom": "Studio indé"}, {"niveau": 16, "nom": "Studio AA"}, {"niveau": 24, "nom": "Studio AAA"}]},
          "jalons": rm_jalons,
          "succes_final": {"id": "roadmap-finie", "titre": "Le jeu est sorti", "description": "Tous les jalons sont terminés.", "icone": "cartes/trophee.svg", "son": "grand"}}
    return rm


def roadmap_md(rm):
    l = [f"# Roadmap : {rm['projet']}", "", f"Rythme : {rm['rythme']['heures_par_semaine']} h par semaine, début {rm['rythme']['debut']}.", ""]
    for j in rm["jalons"]:
        l += [f"## {j['id']} {j['titre']} (fin visée {j['fin_visee']})", "", f"But : {j['but']}", f"Fini quand : {j['critere_fin']}",
              f"Succès : {j['succes']['titre']}", "", "| Tâche | Critère | Poste | Moteur | h | Après | Statut |", "|---|---|---|---|---|---|---|"]
        l += [f"| {t['id']} {t['titre']} | {t['critere']} | {t['poste']} | {'oui' if t['moteur'] else 'non'} | {t['estimation_h']} | {', '.join(t['depend_de']) or '—'} | {t['statut']} |" for t in j["taches"]]
        l.append("")
    return "\n".join(l)


def verifier(rm):
    err = []
    for k in ("version", "langue", "projet", "cree_le", "maj", "sources", "rythme", "niveau", "jalons", "succes_final"):
        if k not in rm:
            err.append("champ manquant : " + k)
    statuts = {"a_faire", "en_cours", "pret", "verse", "ecart"}
    jids, tids, deps_t = set(), {}, {}
    for j in rm.get("jalons", []):
        for k in ("id", "titre", "but", "critere_fin", "depend_de", "fin_visee", "succes", "taches"):
            if k not in j:
                err.append(f"{j.get('id')} : champ {k} manquant")
        if j["id"] in jids:
            err.append("jalon en double : " + j["id"])
        jids.add(j["id"])
        s = j.get("succes") or {}
        if not all(s.get(k) for k in ("id", "titre", "icone", "son")):
            err.append(f"{j['id']} : succès incomplet")
        if not (5 <= len(j["taches"]) <= 12):
            err.append(f"{j['id']} : {len(j['taches'])} tâches (5 à 12 attendues)")
        for t in j["taches"]:
            for k in ("id", "titre", "critere", "poste", "moteur", "estimation_h", "depend_de", "statut"):
                if k not in t:
                    err.append(f"{t.get('id')} : champ {k} manquant")
            if t["id"] in tids:
                err.append("tâche en double : " + t["id"])
            tids[t["id"]] = j["id"]
            deps_t[t["id"]] = t["depend_de"]
            if t["statut"] not in statuts:
                err.append(f"{t['id']} : statut inconnu")
            if not (isinstance(t["estimation_h"], (int, float)) and t["estimation_h"] > 0):
                err.append(f"{t['id']} : estimation absente")
    for j in rm.get("jalons", []):
        for x in j["depend_de"]:
            if x not in jids:
                err.append(f"{j['id']} dépend d'un jalon inconnu {x}")
    for tid, deps in deps_t.items():
        for x in deps:
            if x not in tids:
                err.append(f"{tid} dépend d'une tâche inconnue {x}")
    # boucles
    etat = {}

    def visite(n, pile):
        if etat.get(n) == 1:
            err.append("boucle : " + " → ".join(pile + [n]))
            return
        if etat.get(n) == 2:
            return
        etat[n] = 1
        for x in deps_t.get(n, []):
            if x in deps_t:
                visite(x, pile + [n])
        etat[n] = 2
    for n in deps_t:
        visite(n, [])
    return err


def ecrire_roadmap(d, rm):
    err = verifier(rm)
    if err:
        raise SystemExit("roadmap non conforme :\n- " + "\n- ".join(err))
    ecrire(os.path.join(d, ".studio", "roadmap.json"), rm)
    ecrire(os.path.join(d, "docs", "ROADMAP.md"), roadmap_md(rm))


def cmd_roadmap(d):
    rm = generer_roadmap(d)
    ecrire_roadmap(d, rm)
    n = sum(len(j["taches"]) for j in rm["jalons"])
    print(f"roadmap.json écrit : {len(rm['jalons'])} jalons, {n} tâches, {sum(t['estimation_h'] for j in rm['jalons'] for t in j['taches'])} h ; conforme")


def cmd_verser(d, jid):
    chemin = os.path.join(d, ".studio", "roadmap.json")
    rm = lire(chemin)
    if not rm:
        raise SystemExit("pas de roadmap.json")
    j = next((x for x in rm["jalons"] if x["id"] == jid), None)
    if not j:
        raise SystemExit("jalon inconnu : " + jid)
    for t in j["taches"]:
        if t["statut"] not in ("verse", "ecart"):
            t.update(statut="verse", preuve="essai", fait_le=maintenant())
    rm["maj"] = maintenant()
    ecrire_roadmap(d, rm)
    print(f"{jid} versé ({len(j['taches'])} tâches) : le succès « {j['succes']['titre']} » doit s'afficher")


def png(chemin, w, h, c1, c2):
    """PNG dégradé (bibliothèque standard) : images d'essai du mur."""
    import struct
    import zlib
    lignes = b""
    for y in range(h):
        k = y / max(1, h - 1)
        px = bytes(int(c1[i] + (c2[i] - c1[i]) * k) for i in range(3))
        lignes += b"\x00" + px * w

    def bloc(t, data):
        return struct.pack(">I", len(data)) + t + data + struct.pack(">I", zlib.crc32(t + data) & 0xffffffff)
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + bloc(b"IDAT", zlib.compress(lignes, 9)) + bloc(b"IEND", b""))


def cmd_travail(d):
    conf_ch = os.path.join(d, ".studio", "studio.config.json")
    conf = lire(conf_ch, {})
    conf.update(mode="travail", moteur={"nom": "Godot", "processus": ["godot", "godot_v4"], "poste": "integration-moteur"},
                sources_images=[{"libelle": "Capture du jeu", "poste": "integration-moteur", "motif": "donnees/captures/*.png"},
                                {"libelle": "Image cible", "poste": "art-da", "motif": "donnees/art/cibles/*.png"}])
    ecrire(conf_ch, conf)
    png(os.path.join(d, "donnees", "captures", "scene_grise.png"), 320, 200, (40, 60, 90), (190, 150, 90))
    png(os.path.join(d, "donnees", "captures", "luciole_nuit.png"), 320, 200, (12, 18, 40), (230, 200, 90))
    png(os.path.join(d, "donnees", "art", "cibles", "foret_cible.png"), 320, 200, (30, 70, 40), (170, 210, 150))
    png(os.path.join(d, "donnees", "art", "cibles", "foret_N.png"), 64, 64, (128, 128, 255), (128, 128, 255))   # texture technique : écartée
    print("studio en mode travail ; 3 images d'essai (et une normale à écarter) dans donnees/")


def cmd_etat(d):
    subprocess.check_call([sys.executable, "-I", "-B", os.path.join(STUDIO, "studio_etat.py"), "--projet", d, "--une-fois"])


def cmd_progresser(d, poste, pct, texte, restant):
    import re
    if not re.match(r"^[a-z0-9][a-z0-9-]{0,39}$", poste or ""):
        raise SystemExit("poste invalide")
    p = {"pct": max(0, min(100, int(pct))), "texte": texte or ("Fini" if int(pct) >= 100 else f"Essai : {pct} %")}
    if restant is not None:
        p["restant_min"] = restant
    ecrire(os.path.join(d, ".studio", "progression", poste + ".json"), p)
    print(f"progression/{poste}.json : {p}")


def cmd_rapport(d):
    ecrire(os.path.join(d, ".studio", "rapport_assistant.json"), {
        "heure": dt.datetime.now().strftime("%Y-%m-%dT%H:%M"),
        "blague": "La luciole a demandé une augmentation. On lui a répondu qu'elle brillait déjà assez.",
        "tableau": [{"chantier": "Scène grise", "etape": "sol et obstacles", "pct": 35, "reste": "≈ 25 min"},
                    {"chantier": "Contrôles", "etape": "saut et gravité", "pct": 60, "reste": "≈ 50 min"},
                    {"chantier": "Bible de style", "etape": "3 images cibles", "pct": 10, "reste": "ce soir"}],
        "fini": ["Questionnaire et documents (J0-01)", "Bible sonore écrite"],
        "a_decider": [{"id": "dec-001", "titre": "Résolution de référence pour le prototype ?"}, "Garder la musique au piano ?"]})
    print("rapport_assistant.json écrit")


def cmd_recrue(d, nom):
    import glob
    err = []
    st = os.path.join(d, ".studio")
    fiche = lire(os.path.join(st, "recrues", nom + ".json"))
    if not fiche:
        err.append("fiche recrues/%s.json absente" % nom)
    idx = lire(os.path.join(st, "recrues", "index.json"), [])
    if nom not in (idx or []):
        err.append("absente de recrues/index.json")
    dem = [lire(f) for f in glob.glob(os.path.join(st, "demandes", "*_" + nom + ".json"))]
    dem = [x for x in dem if isinstance(x, dict) and x.get("type") == "recrutement"]
    if not dem:
        err.append("aucune demande de recrutement dans .studio/demandes/")
    agent = os.path.join(d, ".claude", "agents", nom + ".md")
    if not os.path.isfile(agent):
        err.append("définition d'agent absente : " + agent)
    else:
        txt = open(agent, encoding="utf-8").read()
        for attendu in ("name: " + nom, "## Ta mission", "progression/" + nom + ".json"):
            if attendu not in txt:
                err.append(f"agent : « {attendu} » manquant")
        if "{{" in txt.split("## Ta mission")[0]:
            err.append("agent : gabarit non rempli")
    if err:
        raise SystemExit("recrue non conforme :\n- " + "\n- ".join(err))
    print(f"recrue « {nom} » conforme : fiche, index, {len(dem)} demande(s), agent {agent}")
    print("  demande :", json.dumps(dem[-1], ensure_ascii=False)[:400])


def cmd_serveur(d, port, intervalle):
    port = choisir_port(port)
    conf_ch = os.path.join(d, ".studio", "studio.config.json")
    conf = lire(conf_ch, {})
    conf["port"] = port
    ecrire(conf_ch, conf)
    print(f"serveur : http://127.0.0.1:{port}/studio.html", flush=True)
    alim = subprocess.Popen([sys.executable, "-I", "-B", os.path.join(STUDIO, "studio_etat.py"), "--projet", d, "--intervalle", str(intervalle), "--forcer"])
    try:
        subprocess.call([sys.executable, "-I", "-B", os.path.join(STUDIO, "serveur_studio.py"), "--projet", d, "--port", str(port)])
    finally:
        alim.terminate()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("commande", choices=["preparer", "deduire", "remplir", "roadmap", "verser", "verifier", "serveur", "tout",
                                         "travail", "etat", "progresser", "rapport", "recrue"])
    ap.add_argument("jalon", nargs="?", help="jalon (verser), poste (progresser) ou nom (recrue)")
    ap.add_argument("pct", nargs="?", type=int, help="progresser : pourcentage")
    ap.add_argument("--texte", default="")
    ap.add_argument("--restant", type=float, default=None)
    ap.add_argument("--intervalle", type=float, default=5, help="serveur : secondes entre deux passages de studio_etat.py")
    ap.add_argument("--dossier", default=os.environ.get("STUDIO_ESSAI", ""))
    ap.add_argument("--port", type=int, default=8810)
    a = ap.parse_args()
    if not a.dossier:
        raise SystemExit("--dossier obligatoire (ou variable STUDIO_ESSAI)")
    d = os.path.abspath(a.dossier)
    if a.port in PORTS_INTERDITS:
        raise SystemExit("le port 8790 est celui du vrai studio : choisis-en un autre pour l'essai")
    if a.commande == "preparer":
        preparer(d, a.port)
    elif a.commande == "deduire":
        deduire(d)
    elif a.commande == "remplir":
        remplir(d)
    elif a.commande == "roadmap":
        cmd_roadmap(d)
    elif a.commande == "verser":
        cmd_verser(d, a.jalon or "J0")
    elif a.commande == "verifier":
        rm = lire(os.path.join(d, ".studio", "roadmap.json"))
        err = verifier(rm) if rm else ["pas de roadmap.json"]
        print("conforme" if not err else "\n".join(err))
        sys.exit(1 if err else 0)
    elif a.commande == "serveur":
        cmd_serveur(d, a.port, a.intervalle)
    elif a.commande == "travail":
        cmd_travail(d)
    elif a.commande == "etat":
        cmd_etat(d)
    elif a.commande == "progresser":
        if not a.jalon or a.pct is None:
            raise SystemExit("usage : progresser <poste> <pct>")
        cmd_progresser(d, a.jalon, a.pct, a.texte, a.restant)
    elif a.commande == "rapport":
        cmd_rapport(d)
    elif a.commande == "recrue":
        if not a.jalon:
            raise SystemExit("usage : recrue <nom>")
        cmd_recrue(d, a.jalon)
    elif a.commande == "tout":
        preparer(d, a.port)
        deduire(d)
        remplir(d)
        cmd_roadmap(d)


if __name__ == "__main__":
    main()
