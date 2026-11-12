"""Essai complet du studio gamedev : projet jetable, réponses fictives, roadmap.json conforme, serveur local.

Usage (Python 3.10+, bibliothèque standard) :
  python -I -B essai_complet.py preparer  [--dossier D]   crée le projet jetable (.studio/ : config, profil, progression)
  python -I -B essai_complet.py deduire   [--dossier D]   écrit deductions.json (comme Claude après le pitch)
  python -I -B essai_complet.py remplir   [--dossier D]   complète reponses_questionnaire.json avec des réponses fictives (★)
  python -I -B essai_complet.py roadmap   [--dossier D]   écrit .studio/roadmap.json et docs/ROADMAP.md depuis les réponses, puis vérifie
  python -I -B essai_complet.py verser J0 [--dossier D]   passe toutes les tâches du jalon à « verse » (le succès se débloque)
  python -I -B essai_complet.py verifier  [--dossier D]   vérifie roadmap.json (schéma, identifiants, dépendances, boucles)
  python -I -B essai_complet.py serveur   [--dossier D] [--port 8810]   lance serveur_studio.py (premier port libre, jamais 8790)
  python -I -B essai_complet.py tout      [--dossier D] [--port N]   preparer + remplir + roadmap + verifier, puis « fonctions »
  python -I -B essai_complet.py fonctions [--dossier D] [--port N]   mode travail sans navigateur, serveur sur un port libre :
                                          bulles de décision (décision rattachée à un poste), fil (messages dans etat.json,
                                          demandes au nom unique, doublon 60 s, une optimisation en attente), fin de tâche
                                          (seulement après un vrai calme), attribution et embauche automatiques (refusées
                                          tant que le réglage est coupé, puis garde-fous), renvoi / réembauche, renvoi
                                          proposé sous la cloche, fichier fautif signalé, tâche sortie jamais proposée
  python -I -B essai_complet.py travail   [--dossier D]   passe le studio en mode travail, avec 3 images d'essai pour le mur
  python -I -B essai_complet.py etat      [--dossier D]   un passage de studio_etat.py (etat.json, suggestions.json, taches_disponibles.json)
  python -I -B essai_complet.py progresser <poste> <pct> [--texte T] [--restant N]   écrit progression/<poste>.json
  python -I -B essai_complet.py rapport   [--dossier D]   écrit rapport_assistant.json (le rapport plein cadre s'ouvre)
  python -I -B essai_complet.py recrue <nom> [--dossier D]   vérifie la recrue : demande, fiche, définition d'agent
  python -I -B essai_complet.py adoption --dossier D/essai_adoption   adoption d'un projet existant : projet Godot fictif
                                          (scènes, scripts, README, CLAUDE.md, docs/ROADMAP.md, git), analyse, questionnaire
                                          raccourci, roadmap J0 « Ce qui existe déjà », livrables à côté ; vérifie par
                                          empreintes avant / après qu'aucun fichier existant n'est modifié
Le serveur de l'essai lance aussi studio_etat.py en boucle (--intervalle, 5 s par défaut) et l'arrête en sortant.

Le dossier par défaut est passé par --dossier ou la variable STUDIO_ESSAI ; le script refuse d'effacer
un dossier qui ne s'appelle pas « essai_skill » (« essai_adoption » pour l'essai de l'adoption).
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


# ---------------------------------------------------------------------------- fonctions du mode travail (sans navigateur)
def cmd_fonctions(d, port):
    """Bulles de décision, fil de conversation, fin de tâche, renvoi et réembauche, embauche automatique, garde-fous :
    serveur réel sur un port libre + passages de studio_etat.py ; vérifie les fichiers écrits. Projet : celui de « tout »."""
    import re
    import time
    import urllib.error
    import urllib.request
    st = os.path.join(d, ".studio")
    if not os.path.isfile(os.path.join(st, "roadmap.json")):
        raise SystemExit("lance d'abord « tout » (projet, réponses, roadmap)")
    cmd_travail(d)
    etapes = []

    def ok(msg):
        etapes.append(msg)
        print("  ✓", msg, flush=True)

    def echec(msg):
        raise SystemExit("ÉCHEC : " + msg)

    def vieillir(chemin, minutes):
        t = time.time() - minutes * 60
        os.utime(chemin, (t, t))

    def etat_une_fois():
        subprocess.run([sys.executable, "-I", "-B", os.path.join(STUDIO, "studio_etat.py"), "--projet", d, "--une-fois", "--forcer"],
                       check=True, capture_output=True)
        return lire(os.path.join(st, "etat.json"), {})

    def poste_de(e, pid):
        return next((q for q in e.get("postes", []) if q.get("id") == pid), None)

    # décisions : une pour un poste (bulle au-dessus de lui), une pour l'assistant ; une réponse finissant par une question
    decs = lire(os.path.join(st, "decisions.json"), []) or []
    decs = [x for x in decs if x.get("id") != "dec-002"] + [{"id": "dec-002", "poste": "art-da", "titre": "Palette d'automne ou d'hiver ?",
            "explication": "Pour la bible de style.", "choix": [{"id": "automne", "libelle": "Automne"}, {"id": "hiver", "libelle": "Hiver"}],
            "recommande": "automne", "cree_le": maintenant()}]
    ecrire(os.path.join(st, "decisions.json"), decs)
    ecrire(os.path.join(st, "reponses_assistant.json"), [{"id": "rep-essai-1", "a_propos": "", "texte": "La scène grise est prête. On garde la caméra fixe ?", "cree_le": maintenant()}])

    port = choisir_port(port)
    srv = subprocess.Popen([sys.executable, "-I", "-B", os.path.join(STUDIO, "serveur_studio.py"), "--projet", d, "--port", str(port)],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    base = f"http://127.0.0.1:{port}"

    def api(route, corps, attendu=200):
        req = urllib.request.Request(base + route, data=json.dumps(corps).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json", "Origin": base, "Host": f"127.0.0.1:{port}"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                code, rep = r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            code, rep = e.code, json.loads(e.read().decode("utf-8") or "{}")
        if code != attendu:
            echec(f"{route} {json.dumps(corps, ensure_ascii=False)[:120]} : code {code} au lieu de {attendu} ({rep.get('erreur')})")
        return rep

    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(base + "/studio.html", timeout=1).read()
                break
            except Exception:
                time.sleep(0.2)
        else:
            echec("le serveur ne répond pas")
        page = urllib.request.urlopen(base + "/studio.html", timeout=5).read().decode("utf-8")
        for f in ("function bullesDecision", "const Conv =", "const FinTache =", "function apresRenvoi", "function decisionDe",
                  "function ouvrirReglages", "function embaucheAuto", "function majBandeauEtat", "bt-conv"):
            if f not in page:
                echec(f"studio.html : « {f} » absent")
        ok("page servie : bulles de décision, conversation, fin de tâche, renvoi, réglages, embauche auto, bandeau d'état")

        # fil : demandes au nom unique, jamais écrasées ; même texte en moins de 60 s = une seule demande
        r1 = api("/api/demande", {"cible": "assistant", "texte": "Ajoute un écran titre.", "via": "ecrit"})
        r2 = api("/api/demande", {"cible": "assistant", "texte": "Ajoute un écran titre.", "via": "ecrit"})
        r3 = api("/api/demande", {"cible": "assistant", "texte": "Et une musique de menu.", "via": "voix"})
        if not r2.get("doublon") or r2["id"] != r1["id"] or r3["id"] == r1["id"] or not re.match(r"^\d{8}-\d{6}-\d{3}[0-9a-f]{4}_assistant$", r3["id"]):
            echec(f"demandes : doublon ou nom unique incorrect ({r1['id']}, {r2.get('id')}, {r3['id']})")
        if len([f for f in os.listdir(os.path.join(st, "demandes_vocales")) if f.endswith(".json")]) != 2:
            echec("demandes_vocales : 2 fichiers attendus (le doublon n'est pas réécrit)")
        api("/api/demande", {"cible": "assistant", "texte": "Optimise le projet.", "sujet": "optimisation"})
        api("/api/demande", {"cible": "assistant", "texte": "Optimise encore.", "sujet": "optimisation"}, 429)
        ok("demandes : nom unique (ms + code) en mode exclusif, doublon de moins de 60 s ignoré, une seule optimisation en attente")

        # recrue, puis fin de tâche après un vrai calme
        api("/api/recruter", {"nom": "renfort-essai", "nom_affiche": "Renfort", "role": "Aide polyvalente", "mission": "Tâches sans moteur.", "lancer": False})
        statuts = lire(os.path.join(st, "demandes", "statuts.json"), {}) or {}
        statuts["renfort-essai"] = {"statut": "pas lancé", "maj": maintenant()}   # ce que Claude note pour lancer: false (SKILL.md)
        ecrire(os.path.join(st, "demandes", "statuts.json"), statuts)
        prog =os.path.join(st, "progression", "renfort-essai.json")
        ecrire(prog, {"pct": 100, "texte": "Liste des sons écrite"})
        vieillir(prog, 2)
        q = poste_de(etat_une_fois(), "renfort-essai")
        if not q or q["etat"] != "disponible" or q.get("fin_de_tache"):
            echec(f"fin de tâche déclarée trop tôt (calme de 2 min) : {q}")
        vieillir(prog, 10)
        e = etat_une_fois()
        q = poste_de(e, "renfort-essai")
        if not q or not q.get("fin_de_tache") or "Liste des sons" not in q.get("fini", ""):
            echec(f"fin de tâche absente après 10 min de calme : {q}")
        msgs = [m["texte"] for m in e.get("messages", [])]
        if "Ajoute un écran titre." not in msgs or "Et une musique de menu." not in msgs:
            echec(f"etat.json : messages du fil absents ({msgs})")
        ok("fin de tâche : rien à 2 min de calme, « fin_de_tache » après 10 min (100 %, rien devant lui) ; fil : messages dans etat.json")

        # attribution : automatique refusée tant que le réglage est coupé (défaut), puis garde-fous
        auto = {"agent": "renfort-essai", "mission": "Tâche J1-02 : contrôles.", "titre": "J1-02 · Contrôles", "tache_id": "J1-02", "origine": "auto:fin-de-tache"}
        api("/api/confier", auto, 403)
        if (lire(os.path.join(st, "reglages.json"), {}) or {}).get("attribution_auto") is not None:
            echec("reglages.json : attribution_auto ne doit pas exister avant un choix")
        api("/api/reglages", {"attribution_auto": True})
        rc = api("/api/confier", auto)
        api("/api/confier", dict(auto, mission="Une autre tâche.", tache_id="J1-03"), 429)
        api("/api/confier", {"agent": "renfort-essai", "mission": "Tâche J1-04 à la main.", "tache_id": "J1-04", "origine": "tache:J1-04"})
        api("/api/confier", {"agent": "inconnu-essai", "mission": "x"}, 404)
        dem = lire(os.path.join(d, ".studio", rc["demande"]), {})
        if dem.get("origine") != "auto:fin-de-tache" or dem.get("lancer") is not True or dem.get("tache_id") != "J1-02":
            echec(f"demande confiée incorrecte : {dem}")
        ok("attribution : refusée réglage coupé (403), permise une fois activée, une seule en attente par poste (429), tâche confiée à la main permise")

        # renvoi : refusé tant qu'une demande n'est pas finie ; archivage ; réembauche
        api("/api/renvoyer", {"nom": "renfort-essai"}, 409)
        api("/api/renvoyer", {"nom": "direction"}, 403)
        statuts = lire(os.path.join(st, "demandes", "statuts.json"), {}) or {}
        for f in os.listdir(os.path.join(st, "demandes")):
            if f.endswith("_renfort-essai.json"):
                statuts[f] = {"statut": "fini", "maj": maintenant()}
        ecrire(os.path.join(st, "demandes", "statuts.json"), statuts)
        api("/api/renvoyer", {"nom": "renfort-essai", "motif": "essai"})
        agent = os.path.join(d, ".claude", "agents", "renfort-essai.md")
        if os.path.exists(agent) or os.path.exists(os.path.join(st, "recrues", "renfort-essai.json")):
            echec("renvoi : la fiche ou l'agent sont encore en place")
        if not os.path.isfile(os.path.join(st, "recrues", "_anciens", "renfort-essai.json")) or not os.path.isfile(os.path.join(st, "anciens", "agents", "renfort-essai.md")):
            echec("renvoi : archives absentes")
        if "renfort-essai" in (lire(os.path.join(st, "recrues", "index.json"), []) or []) or "renfort-essai" not in (lire(os.path.join(st, "recrues", "_anciens", "index.json"), []) or []):
            echec("renvoi : index non mis à jour")
        api("/api/reembaucher", {"nom": "renfort-essai"})
        if not os.path.isfile(agent) or (lire(os.path.join(st, "recrues", "renfort-essai.json"), {}) or {}).get("lancer") is not False:
            echec("réembauche : agent ou fiche absents (lancer doit valoir false)")
        ok("renvoi : refusé avec une tâche en cours (409) et pour un poste de base (403), archivage sans rien effacer, réembauche")

        # embauche automatique : coupée par défaut, puis une par heure ; jamais un ancien renvoyé
        emb = {"nom": "metier-essai", "nom_affiche": "Métier", "role": "Poste « métier »", "mission": "- J2-01 : essai", "auto": True}
        api("/api/recruter", emb, 403)
        api("/api/reglages", {"embauche_auto": True})
        r = api("/api/recruter", emb)
        if r["fiche"].get("origine") != "auto:embauche" or r["fiche"].get("lancer") is not False:
            echec(f"embauche auto : fiche incorrecte {r['fiche']}")
        api("/api/recruter", dict(emb, nom="metier-essai-2"), 429)
        ok("embauche automatique : refusée réglage coupé (403), permise une fois activée (lancer: false), une par heure (429)")

        # proposition de renvoi sous la cloche : recrue libre depuis 24 h, rien pour son poste
        for f in os.listdir(os.path.join(st, "demandes")):
            if f.endswith("_metier-essai.json") or f.endswith("_renfort-essai.json"):
                statuts[f] = {"statut": "fini", "maj": maintenant()}
        ecrire(os.path.join(st, "demandes", "statuts.json"), statuts)
        etat_une_fois()
        e = lire(os.path.join(st, "etat.json"), {})
        q = poste_de(e, "renfort-essai")
        if not q or q["etat"] != "disponible":
            echec(f"renfort-essai devrait être disponible : {q}")
        q["depuis"] = int(time.time()) - 25 * 3600
        ecrire(os.path.join(st, "etat.json"), e)
        etat_une_fois()
        dstu = lire(os.path.join(st, "decisions_studio.json"), []) or []
        prop = next((x for x in dstu if x.get("nom") == "renfort-essai" and x.get("type") == "renvoi"), None)
        if not prop or [c["id"] for c in prop["choix"]] != ["renvoyer", "garder"] or os.path.isfile(os.path.join(st, "recrues", "_anciens", "renfort-essai.json")):
            echec(f"decisions_studio.json : proposition de renvoi absente ou appliquée seule ({dstu})")
        ok("renvoi proposé sous la cloche (decisions_studio.json, Renvoyer / Garder), jamais appliqué seul")

        # fichier fautif ignoré et signalé ; tâche sortie jamais proposée
        casse = os.path.join(st, "progression", "casse.json")
        ecrire(casse, "{pas du json")
        vieillir(casse, 1)
        rm_ch = os.path.join(st, "roadmap.json")
        rm = lire(rm_ch)
        prets = {t["id"] for t in (lire(os.path.join(st, "taches_disponibles.json"), {}) or {}).get("taches", [])}
        cible = next((t for j in rm["jalons"] for t in j["taches"] if t["id"] in prets), None)
        if not cible:
            echec("aucune tâche prête dans taches_disponibles.json")
        cible["note"] = "sortie de la version 1"
        ecrire(rm_ch, rm)
        e = etat_une_fois()
        if not any(a.get("fichier") == "progression/casse.json" for a in e.get("anomalies", [])) or len(e.get("postes", [])) < 5:
            echec(f"anomalie non signalée ou studio arrêté : {e.get('anomalies')}")
        sug = lire(os.path.join(st, "suggestions.json"), {}) or {}
        if not any(s["id"].startswith("illisible-") for s in sug.get("suggestions", [])):
            echec("suggestions.json : alerte « fichier illisible » absente")
        dispo = [t["id"] for t in (lire(os.path.join(st, "taches_disponibles.json"), {}) or {}).get("taches", [])]
        if cible["id"] in dispo:
            echec(f"tâche sortie {cible['id']} encore proposée")
        os.remove(casse)
        del cible["note"]
        ecrire(rm_ch, rm)
        ok(f"fichier fautif ignoré et signalé (anomalies + alerte), le reste continue ; tâche sortie ({cible['id']}) jamais proposée")

        # réponse à une décision : rien n'est écrit si reponses.json est illisible
        rep_ch = os.path.join(st, "reponses.json")
        ecrire(rep_ch, "[ cassé")
        api("/api/repondre", {"id": "dec-002", "choix": "automne"}, 503)
        if open(rep_ch, encoding="utf-8").read() != "[ cassé":
            echec("reponses.json illisible a été réécrit")
        os.remove(rep_ch)
        api("/api/repondre", {"id": "dec-002", "choix": "automne"})
        ok("décision : réponse refusée (503) sans rien écrire si reponses.json est illisible, puis acceptée")
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=10)
        except Exception:
            srv.kill()
    # la page relit l'essai à l'état « travail » : réglages remis comme au départ (coupés)
    ecrire(os.path.join(st, "reglages.json"), {"attribution_auto": False, "embauche_auto": False, "maj": maintenant()})
    print(f"ESSAI DES FONCTIONS RÉUSSI ({len(etapes)} étapes) : {d}")


# ---------------------------------------------------------------------------- adoption d'un projet existant
TSCN = '[gd_scene load_steps=2 format=3]\n\n[ext_resource type="Script" path="res://scripts/{script}.gd" id="1"]\n\n[node name="{nom}" type="{type}"]\nscript = ExtResource("1")\n{enfants}'
FICTIF = {
    "project.godot": '; Engine configuration file.\nconfig_version=5\n\n[application]\n\nconfig/name="Petit Renard"\nrun/main_scene="res://scenes/main.tscn"\n'
                     'config/features=PackedStringArray("4.3", "GL Compatibility")\n\n[autoload]\n\nGameState="*res://scripts/game_state.gd"\n\n'
                     '[input]\n\nmove_left={\n"deadzone": 0.5,\n"events": []\n}\nmove_right={\n"deadzone": 0.5,\n"events": []\n}\njump={\n"deadzone": 0.5,\n"events": []\n}\n\n'
                     '[rendering]\n\ntextures/canvas_textures/default_texture_filter=0\n',
    "export_presets.cfg": '[preset.0]\n\nname="Windows Desktop"\nplatform="Windows Desktop"\n\n[preset.1]\n\nname="Web"\nplatform="Web"\n',
    "scenes/main.tscn": TSCN.format(script="main", nom="Main", type="Node2D", enfants=""),
    "scenes/player.tscn": TSCN.format(script="player", nom="Player", type="CharacterBody2D", enfants='\n[node name="Camera2D" type="Camera2D" parent="."]\n'),
    "scenes/enemy.tscn": TSCN.format(script="enemy", nom="Enemy", type="CharacterBody2D", enfants=""),
    "scenes/levels/level_1.tscn": TSCN.format(script="main", nom="Level1", type="Node2D", enfants='\n[node name="Tiles" type="TileMapLayer" parent="."]\n'),
    "scenes/levels/level_2.tscn": TSCN.format(script="main", nom="Level2", type="Node2D", enfants=""),
    "scenes/ui/hud.tscn": TSCN.format(script="hud", nom="HUD", type="CanvasLayer", enfants='\n[node name="Coins" type="Label" parent="."]\n'),
    "scripts/main.gd": "extends Node2D\n\n\nfunc _ready() -> void:\n\tGameState.load_game()\n",
    "scripts/player.gd": "extends CharacterBody2D\n\nconst SPEED := 140.0\nconst JUMP_VELOCITY := -320.0\nvar gravity: float = ProjectSettings.get_setting(\"physics/2d/default_gravity\")\n\n\n"
                         "func _physics_process(delta: float) -> void:\n\tif not is_on_floor():\n\t\tvelocity.y += gravity * delta\n"
                         "\tif Input.is_action_just_pressed(\"jump\") and is_on_floor():\n\t\tvelocity.y = JUMP_VELOCITY\n"
                         "\tvelocity.x = Input.get_axis(\"move_left\", \"move_right\") * SPEED\n\tmove_and_slide()\n\t# TODO: coyote time pour le saut\n",
    "scripts/enemy.gd": "extends CharacterBody2D\n\n# Patrouille simple entre deux points\nvar direction := 1.0\n\n\nfunc _physics_process(_delta: float) -> void:\n"
                        "\tvelocity.x = 40.0 * direction\n\tif is_on_wall():\n\t\tdirection = -direction\n\tmove_and_slide()\n",
    "scripts/game_state.gd": "extends Node\n\nvar coins := 0\nconst SAVE_PATH := \"user://save.cfg\"\n\n\nfunc save_game() -> void:\n\tvar cfg := ConfigFile.new()\n"
                             "\tcfg.set_value(\"jeu\", \"coins\", coins)\n\tcfg.save(SAVE_PATH)\n\n\nfunc load_game() -> void:\n\tvar cfg := ConfigFile.new()\n"
                             "\tif cfg.load(SAVE_PATH) == OK:\n\t\tcoins = cfg.get_value(\"jeu\", \"coins\", 0)\n\t# FIXME: version du format de sauvegarde\n",
    "scripts/hud.gd": "extends CanvasLayer\n\n\nfunc _process(_delta: float) -> void:\n\t$Coins.text = str(GameState.coins)\n",
    "README.md": "# Petit Renard\n\nUn petit jeu de plateforme 2D où un renard ramasse des pièces dans une forêt d'automne.\n\n## Lancer\n\nOuvrir le dossier avec Godot 4.3.\n",
    "CLAUDE.md": "# Petit Renard\n\nRègles du projet : GDScript typé, tabulations, une scène par objet.",   # sans fin de ligne : cas limite du bloc
    "docs/ROADMAP.md": "# Ma liste\n\n- [x] le renard bouge et saute\n- [ ] un boss\n",
    ".gitignore": ".godot/\n*.translation\n",
}


def wav(chemin):
    import struct
    donnees = b"\x00\x00" * 800
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 36 + len(donnees)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, 8000, 16000, 2, 16) + b"data" + struct.pack("<I", len(donnees)) + donnees)


def creer_projet_fictif(d):
    if os.path.basename(os.path.normpath(d)) != "essai_adoption":
        raise SystemExit("refus : le dossier d'essai de l'adoption doit s'appeler essai_adoption")
    if os.path.isdir(d):
        reessai = lambda f, p, _e: (os.chmod(p, 0o700), f(p))   # fichiers en lecture seule de .git sous Windows
        shutil.rmtree(d, **({"onexc": reessai} if sys.version_info >= (3, 12) else {"onerror": reessai}))
    for rel, txt in FICTIF.items():
        ch = os.path.join(d, *rel.split("/"))
        os.makedirs(os.path.dirname(ch), exist_ok=True)
        with open(ch, "w", encoding="utf-8", newline="\n") as f:
            f.write(txt)
    png(os.path.join(d, "assets", "sprites", "renard.png"), 32, 32, (200, 90, 30), (240, 160, 80))
    png(os.path.join(d, "assets", "sprites", "tuiles.png"), 64, 32, (60, 90, 40), (120, 80, 40))
    wav(os.path.join(d, "assets", "sons", "saut.wav"))
    # un petit historique git (identité neutre, dates fixes) : « quelques heures de travail »
    git = shutil.which("git")
    if not git:
        return "git absent : projet sans historique"
    env = dict(os.environ, GIT_AUTHOR_NAME="essai", GIT_AUTHOR_EMAIL="essai@example.invalid", GIT_COMMITTER_NAME="essai", GIT_COMMITTER_EMAIL="essai@example.invalid")
    lots = [("2026-11-01T14:00:00", ["project.godot", "scenes/main.tscn", "scenes/player.tscn", "scripts/main.gd", "scripts/player.gd", ".gitignore"], "Projet Godot et renard qui saute"),
            ("2026-11-01T15:40:00", ["scenes/enemy.tscn", "scripts/enemy.gd", "scenes/levels", "assets"], "Ennemi qui patrouille, deux niveaux"),
            ("2026-11-03T20:10:00", ["."], "Pièces, sauvegarde et HUD")]
    try:
        subprocess.run([git, "init", "-q", d], check=True, env=env, capture_output=True)
        for date, chemins, msg in lots:
            e = dict(env, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
            subprocess.run([git, "-C", d, "add", "--", *chemins], check=True, env=e, capture_output=True)
            subprocess.run([git, "-C", d, "commit", "-q", "-m", msg], check=True, env=e, capture_output=True)
    except subprocess.CalledProcessError as x:
        return "git : historique non créé (" + (x.stderr or b"").decode("utf-8", "replace").strip()[:120] + ")"
    return "3 commits sur 2 jours"


def empreintes_essai(d, avec_git=True):
    import hashlib
    out = {}
    for racine, dossiers, fichiers in os.walk(d):
        rel_r = os.path.relpath(racine, d).replace("\\", "/")
        dossiers[:] = [x for x in dossiers if x != ".studio" and (avec_git or x != ".git")]
        for f in fichiers:
            ch = os.path.join(racine, f)
            r = f if rel_r == "." else rel_r + "/" + f
            with open(ch, "rb") as fh:
                out[r] = hashlib.sha256(fh.read()).hexdigest()
    return out


def adoption_py(d, *args, attendu=0):
    r = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", os.path.join(ICI, "adoption.py"), args[0], "--projet", d, *args[1:]], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != attendu:
        raise SystemExit(f"adoption.py {args[0]} : code {r.returncode} (attendu {attendu})\n{r.stdout}\n{r.stderr}")
    return r.stdout


DEF_POSTES = {p["id"]: p for p in POSTES}
DEF_POSTES.update({
    "qualite-tests": {"id": "qualite-tests", "nom": "Qualité et tests", "role": "Tests, TODO, bugs : le projet reste sain", "couleur": "#5b6b2e", "apparence": "lunettes", "skills": ["gamedev:godot-gdscript-headless-testing"]},
    "reseau": {"id": "reseau", "nom": "Réseau", "role": "Multijoueur, synchronisation, tests à 2", "couleur": "#2e5b6b", "apparence": "casque", "skills": ["gamedev:godot-multiplayer"]},
    "narration": {"id": "narration", "nom": "Narration", "role": "Histoire, dialogues, textes", "couleur": "#6b2e5b", "apparence": "chapeau", "skills": ["gamedev:dialogue-systems"]},
})


def a_cote(d, rel):
    """Cible d'écriture d'un document : le fichier lui-même s'il n'existe pas, sinon son voisin *.studio.md."""
    return rel[:-3] + ".studio.md" if os.path.exists(os.path.join(d, rel)) else rel


def generer_roadmap_adoption(d, a):
    rep = (lire(os.path.join(d, ".studio", "reponses_questionnaire.json"), {}) or {}).get("reponses", {})
    v = lambda k, df=None: (rep.get(k) or {}).get("valeur") or df
    postes = set(a["postes_proposes"])
    po = lambda p: p if p in postes else ("code-gameplay" if "code-gameplay" in postes else "direction")
    k = a["calibrage"]["facteur"]
    h = lambda x: max(0.5, round(x * k * 2) / 2)   # estimations calibrées sur le rythme observé, au demi-heure
    hps = {"quelques_heures": 5, "soirs": 12, "plein": 35, "jam": 48}.get(v("ambition.temps"), 0) or a["calibrage"]["heures_par_semaine_observees"] or 5
    t0, debut = maintenant(), dt.date.today()
    doc = a_cote(d, "docs/ROADMAP.md")
    # J0 : ce qui existe déjà, versé avec sa preuve (fichier ou commit)
    j0 = [{"titre": e["titre"], "critere": "existe dans le projet (" + (e["preuve"] or "constaté à l'analyse") + ")", "poste": po(e["poste"]), "moteur": e["moteur"],
           "estimation_h": max(0.5, e["estimation_standard_h"]), "preuve": e["preuve"] or "analyse"} for e in a["existant"][:10]]
    j0 += [{"titre": "Analyse du projet (adoption)", "critere": "inventaire écrit sans rien modifier", "poste": "direction", "moteur": False, "estimation_h": 0.5, "preuve": ".studio/analyse_projet.json"},
           {"titre": "Roadmap à partir de l'existant", "critere": "roadmap écrite à côté des documents existants", "poste": "direction", "moteur": False, "estimation_h": 0.5, "preuve": doc}]
    verbe = v("gameplay.verbe", "jouer")
    sys_ids = {s["id"] for s in a["systemes"]}
    j1 = [("Le projet se lance sans erreur", "ouverture et lancement court sans erreur dans la console", "integration-moteur", True, 1),
          ("Tests de base" if not a["tests"]["present"] else "Tests existants verts", "3 tests sans moteur passent" if not a["tests"]["present"] else "tous les tests passent", "qualite-tests", False, 3),
          (f"TODO prioritaires ({a['todo']['nombre']})", "les TODO bloquants traités ou notés en écart", "qualite-tests", False, 2),
          (f"Le verbe « {verbe} » tient 1 minute", f"on peut {verbe} 1 minute sans bug bloquant", "code-gameplay", True, 2),
          ("Version à essayer", "build lancée et guide « quoi regarder »", "integration-moteur", True, 1)]
    j2 = [("Objectif et victoire", "on peut gagner et perdre", "code-gameplay", False, 5)]
    if "sauvegarde" not in sys_ids:
        j2.append(("Sauvegarde", "la partie reprend après fermeture", "code-gameplay", False, 4))
    else:
        j2.append(("Sauvegarde versionnée", "le format de sauvegarde porte une version", "code-gameplay", False, 1.5))
    j2.append(("Interface de jeu", "vie, objectif et pause affichés", "art-da", True, 4 if "interface" not in sys_ids else 2))
    j2.append(("Sons et ambiance", "5 sons clés et une ambiance jouent", "son", True, 4 if not a["assets"]["audio"] else 2))
    j2.append(("Version à essayer", "build et guide", "integration-moteur", True, 1))
    jalons = [("J0", "Ce qui existe déjà", "Ce que tu as déjà construit, reconnu et compté.", "L'existant est inventorié, avec ses preuves.", [], None, j0,
               {"titre": "Je reprends ton projet", "description": "Le studio connaît ton jeu.", "icone": "cartes/loupe.svg", "son": "moyen"}),
              ("J1", "Reprise en main", "Le projet est sain et se lance.", "Lancement sans erreur, tests de base verts.", ["J0"], "J0", j1,
               {"titre": "Sur de bonnes bases", "description": "Le projet tient debout.", "icone": "cartes/valide.svg", "son": "moyen"}),
              ("J2", "Boucle complète", "Une partie se joue du début à la fin.", "Une partie complète en 5 minutes.", ["J1"], "J1", j2,
               {"titre": "La boucle est bouclée", "description": "Une partie complète se joue.", "icone": "cartes/boucle.svg", "son": "grand"})]
    if v("ambition.taille", "petit") != "prototype":
        jalons.append(("J3", "Contenu et finition", "Assez de contenu pour une vraie partie, polie.", f"{max(3, len(a['scenes']['niveaux']) + 2)} niveaux finis, aucun bug bloquant connu.", ["J2"], "J2",
                       [("Niveaux supplémentaires", "les nouveaux niveaux se jouent de bout en bout", "code-gameplay", True, 10),
                        ("Assets finaux", "décors et personnages au style validé (image validée d'abord)", "art-da", True, 12),
                        ("Mixage", "volumes réglés, options son", "son", True, 3),
                        ("Réglages et accessibilité", "touches remappables, sous-titres", "code-gameplay", True, 4),
                        ("Version candidate", "build finale et guide", "integration-moteur", True, 2)],
                       {"titre": "Prêt à montrer", "description": "Le jeu tient debout.", "icone": "cartes/trophee.svg", "son": "grand"}))
    rm_jalons, fin = [], debut
    for jid, titre, but, critere, dep, prec, taches, succes in jalons:
        tt = []
        for i, x in enumerate(taches):
            if isinstance(x, dict):   # J0 : versé
                t = tache(jid, i + 1, x["titre"], x["critere"], x["poste"], x["moteur"], x["estimation_h"], [], "verse")
                t.update(preuve=x["preuve"], fait_le=t0)
            else:
                ti, cr, p, m, e = x
                deps = [f"{prec}-01"] if i == 0 else [f"{jid}-{i:02d}"]
                if i == len(taches) - 1:
                    deps = [f"{jid}-{n:02d}" for n in range(1, len(taches))]
                t = tache(jid, i + 1, ti, cr, po(p), m, h(e), deps)
            tt.append(t)
        if jid != "J0":
            fin = fin + dt.timedelta(days=max(1, round(7 * sum(x["estimation_h"] for x in tt) / hps)))
        rm_jalons.append({"id": jid, "titre": titre, "but": but, "critere_fin": critere, "depend_de": dep, "fin_visee": (debut if jid == "J0" else fin).isoformat(),
                          "succes": dict(succes, id=f"jalon-{jid}"), "taches": tt})
    return {"version": 1, "langue": "fr", "projet": a["projet"]["nom"], "cree_le": t0, "maj": t0, "mode": "adoption",
            "sources": {"questionnaire": ".studio/reponses_questionnaire.json", "document": doc, "analyse": ".studio/analyse_projet.json"},
            "rythme": {"heures_par_semaine": hps, "debut": debut.isoformat(), "facteur_calibrage": k},
            "niveau": {"xp_par_tache": 100, "xp_par_jalon": 500, "rangs": [{"niveau": 1, "nom": "Garage"}, {"niveau": 5, "nom": "Atelier de quartier"}, {"niveau": 10, "nom": "Studio indé"}, {"niveau": 16, "nom": "Studio AA"}, {"niveau": 24, "nom": "Studio AAA"}]},
            "jalons": rm_jalons,
            "succes_final": {"id": "roadmap-finie", "titre": "Le jeu est sorti", "description": "Tous les jalons sont terminés.", "icone": "cartes/trophee.svg", "son": "grand"}}


def cmd_adoption(d, port):
    """Essai complet de l'adoption : projet Godot fictif déjà commencé, analyse, questionnaire raccourci, roadmap, garde-fous."""
    ok = lambda m: print("  ok  " + m)
    print("1. projet fictif :", creer_projet_fictif(d))
    avant = empreintes_essai(d)
    print(f"   {len(avant)} fichiers (dont .git) photographiés")

    print("2. analyse (lecture seule)")
    print("   " + adoption_py(d, "analyser").strip().replace("\n", "\n   "))
    apres = empreintes_essai(d)
    diff = sorted(f for f in set(avant) | set(apres) if avant.get(f) != apres.get(f))
    if diff:
        raise SystemExit("ÉCHEC : l'analyse a modifié le projet : " + ", ".join(diff[:10]))
    ok(f"aucun fichier modifié par l'analyse ({len(avant)} empreintes identiques, .git compris)")
    a = lire(os.path.join(d, ".studio", "analyse_projet.json"))
    err = []
    if (a["moteur"]["nom"], a["moteur"]["version"], a["moteur"]["langage"]) != ("godot", "4.3", "gdscript"):
        err.append(f"moteur : {a['moteur']}")
    if a["scenes"]["nombre"] != 6 or len(a["scenes"]["niveaux"]) != 2:
        err.append(f"scènes : {a['scenes']['nombre']} / niveaux {a['scenes']['niveaux']}")
    ids = {s["id"] for s in a["systemes"]}
    for attendu in ("joueur", "saut", "camera", "ennemis", "sauvegarde", "interface", "economie"):
        if attendu not in ids:
            err.append("système non reconnu : " + attendu)
    if a["deductions"]["sures"].get("camera.dimension", {}).get("valeur") != "2d":
        err.append("dimension 2D non déduite")
    if a["deductions"]["probables"].get("genre.principal", {}).get("valeur") != "plateforme":
        err.append("genre plateforme non proposé")
    if a["todo"]["nombre"] != 2:
        err.append(f"TODO : {a['todo']['nombre']} au lieu de 2")
    prot = {p["chemin"]: p["cible"] for p in a["fichiers_proteges"]}
    for f, c in (("docs/ROADMAP.md", "docs/ROADMAP.studio.md"), ("README.md", "README.studio.md"), ("CLAUDE.md", "CLAUDE.md"), (".gitignore", ".gitignore")):
        if prot.get(f) != c:
            err.append(f"fichier protégé {f} → {prot.get(f)}")
    if a["git"].get("depot") and a["git"].get("commits") != 3:
        err.append(f"git : {a['git'].get('commits')} commits")
    if len(a["resume"]) != 5:
        err.append("résumé : 5 lignes attendues")
    if err:
        raise SystemExit("ÉCHEC analyse :\n- " + "\n- ".join(err))
    c = a["calibrage"]
    ok(f"inventaire juste : Godot 4.3, 6 scènes (2 niveaux), {len(ids)} systèmes, {a['todo']['nombre']} TODO, docs protégés ; "
       f"≈ {c['heures_deja_estimees']} h déjà faites, facteur {c['facteur']}, postes {', '.join(a['postes_proposes'])}")

    print("3. questionnaire raccourci")
    adoption_py(d, "preremplir")
    q = lire(os.path.join(d, ".studio", "reponses_questionnaire.json"))
    ded = lire(os.path.join(d, ".studio", "deductions.json"))
    r_m = q["reponses"].get("moteur.nom", {})
    if q.get("mode") != "adoption" or r_m.get("source") != "deduit" or "déduit du projet" not in r_m.get("raison", ""):
        raise SystemExit("ÉCHEC : réponses pré-remplies non conformes")
    if "Je reprends ton projet" not in ded.get("message_assistant", ""):
        raise SystemExit("ÉCHEC : message d'accueil absent")
    questions = lire(os.path.join(STUDIO, "questions.fr.json"))["questions"]
    restantes = [x["id"] for x in questions if x.get("rapide") and x["id"] not in q["reponses"] and x["id"] not in ded["fixes"] and x["type"] != "personnage"]
    rapides = [x["id"] for x in questions if x.get("rapide") and x["type"] != "personnage"]
    ok(f"mode adoption ; {len(q['reponses'])} réponses déduites du projet ; {len(ded['recommandes'])} ★ proposées ; "
       f"{len(restantes)} questions sur {len(rapides)} restent pour l'utilisateur : {', '.join(restantes)}")
    remplir(d)   # l'utilisateur répond au reste (réponses fictives) ; les réponses déduites ne bougent pas
    q = lire(os.path.join(d, ".studio", "reponses_questionnaire.json"))
    if q["reponses"]["moteur.nom"]["source"] != "deduit" or q.get("mode") != "adoption":
        raise SystemExit("ÉCHEC : une réponse déduite a été remplacée")
    q.update(etat="termine", maj=maintenant())
    ecrire(os.path.join(d, ".studio", "reponses_questionnaire.json"), q)

    print("4. roadmap à partir de l'existant")
    rm = generer_roadmap_adoption(d, a)
    err = verifier(rm)
    j0 = rm["jalons"][0]
    if j0["titre"] != "Ce qui existe déjà" or any(t["statut"] != "verse" or not t.get("preuve") for t in j0["taches"]):
        err.append("J0 : toutes les tâches doivent être versées avec une preuve")
    if err:
        raise SystemExit("ÉCHEC roadmap :\n- " + "\n- ".join(err))
    ecrire(os.path.join(d, ".studio", "roadmap.json"), rm)
    ecrire(os.path.join(d, rm["sources"]["document"]), roadmap_md(rm).replace("# Roadmap :", "# Roadmap du studio :", 1))
    n = sum(len(j["taches"]) for j in rm["jalons"])
    reste = sum(t["estimation_h"] for j in rm["jalons"][1:] for t in j["taches"])
    ok(f"{len(rm['jalons'])} jalons, {n} tâches (J0 : {len(j0['taches'])} versées avec preuve) ; reste {reste} h calibrées ×{rm['rythme']['facteur_calibrage']} ; écrite dans {rm['sources']['document']}")

    print("5. livrables sans rien écraser")
    ecrits = []
    for rel, contenu in (("docs/GDD.md", f"# {a['projet']['nom']} : GDD\n\n{a['pitch_readme']}\n"),
                         ("docs/DECISIONS.md", "# Décisions\n\n- D001 Adoption : on garde le moteur, les conventions et la structure du projet existant.\n"),
                         ("README.md", "# Studio gamedev\n\nCe projet est suivi par le studio : voir docs/ROADMAP.studio.md.\n")):
        cible = a_cote(d, rel)
        ecrire(os.path.join(d, *cible.split("/")), contenu)
        ecrits.append(cible)
    bloc = ("## Studio gamedev\n\n- Roadmap du studio : `" + rm["sources"]["document"] + "` et `.studio/roadmap.json`.\n"
            "- Conventions du projet gardées : " + ", ".join(f"{k} {v}" for k, v in a["conventions"].items() if isinstance(v, str)) + ".\n"
            "- Une seule chaîne moteur ; aucun push sans accord.\n")
    ecrire(os.path.join(d, ".studio", "propositions", "CLAUDE.bloc.md"), bloc)
    print("   " + adoption_py(d, "gitignore").strip())
    print("   " + adoption_py(d, "gitignore").strip())
    conf = lire(os.path.join(SKILL, "modeles", "studio.config.json"), {})
    conf.update({"mode": "accueil", "nom_projet": a["projet"]["nom"], "langue": "fr", "port": port, "sources_images": [],
                 "postes": [DEF_POSTES[p] for p in a["postes_proposes"] if p in DEF_POSTES]})
    ecrire(os.path.join(d, ".studio", "studio.config.json"), conf)
    ok("écrits : " + ", ".join(ecrits) + " ; bloc CLAUDE.md proposé dans .studio/propositions/ (en attente d'accord) ; studio : " + ", ".join(p["id"] for p in conf["postes"]))

    print("6. contrôle : aucun fichier existant modifié")
    fin = empreintes_essai(d, avec_git=False)
    av = {f: h for f, h in avant.items() if not f.startswith(".git/")}
    modifies = sorted(f for f in av if fin.get(f) != av[f])
    if modifies != [".gitignore"]:
        raise SystemExit("ÉCHEC : fichiers existants modifiés : " + ", ".join(modifies))
    gi = open(os.path.join(d, ".gitignore"), encoding="utf-8").read()
    if not gi.startswith(FICTIF[".gitignore"]) or gi.count(".studio/*") != 1:
        raise SystemExit("ÉCHEC : .gitignore réécrit au lieu d'être complété")
    print("   " + adoption_py(d, "verifier").strip().replace("\n", "\n   "))
    ok(f"{len(av) - 1} fichiers existants identiques ; .gitignore seulement complété (bloc .studio/ une fois) ; nouveaux : {len(set(fin) - set(av))}")

    print("7. bloc CLAUDE.md après accord (simulé)")
    contenu = os.path.join(d, ".studio", "propositions", "CLAUDE.bloc.md")
    adoption_py(d, "bloc", "--fichier", "CLAUDE.md", "--contenu", contenu)
    une = open(os.path.join(d, "CLAUDE.md"), "rb").read()
    adoption_py(d, "bloc", "--fichier", "CLAUDE.md", "--contenu", contenu)
    deux = open(os.path.join(d, "CLAUDE.md"), "rb").read()
    if not une.startswith(FICTIF["CLAUDE.md"].encode("utf-8")) or une != deux or une.count(b"<!-- studio-gamedev -->") != 1:
        raise SystemExit("ÉCHEC : le bloc CLAUDE.md n'est pas un simple ajout idempotent")
    adoption_py(d, "verifier", attendu=1)                      # sans accord noté : refusé
    adoption_py(d, "verifier", "--accord", "CLAUDE.md")        # avec accord : permis
    ok("CLAUDE.md : texte d'origine intact, bloc délimité ajouté une seule fois (2e passage sans effet) ; refusé par verifier sans --accord, accepté avec")
    print(f"ESSAI ADOPTION RÉUSSI : {d}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("commande", choices=["preparer", "deduire", "remplir", "roadmap", "verser", "verifier", "serveur", "tout",
                                         "travail", "etat", "progresser", "rapport", "recrue", "adoption", "fonctions"])
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
    elif a.commande == "adoption":
        cmd_adoption(d, a.port)
    elif a.commande == "fonctions":
        cmd_fonctions(d, a.port)
    elif a.commande == "tout":
        preparer(d, a.port)
        deduire(d)
        remplir(d)
        cmd_roadmap(d)
        cmd_fonctions(d, a.port)


if __name__ == "__main__":
    main()
