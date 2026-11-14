"""Essai des quêtes du studio (paquet S4), sans navigateur ni serveur.

Fait passer un projet d'essai par TOUTES les quêtes, du questionnaire à la version 1.0, avec une horloge simulée :
proposition au bon moment, acceptation (recrues prêtes, `lancer: false`, rien de lancé), fini vérifié par fichier,
roadmap, git ou da.json, récompenses (XP, succès, actes, habillage, déblocages). Puis les cas particuliers :
rythme (une principale à la fois, 30 min, plus tard 24 h, absent, nuit, jalon qui finit), réponses refusées (403, 404,
409, doublon), preuve déposée, habillage (brouillon, contraste, polices bornées, SVG actif, chemin `..`, mode Atelier,
thème clair), agents de soutien (bouton Audit, désactivable), adoption (quêtes déjà faites, une seule bannière,
aucun fichier existant touché), table du bureau (thème du projet, détail par jalon, DA adoptée), performance
(un passage sur 2 000 fichiers < 300 ms).

Usage : python -I -B essai_quetes.py [--garder]      code 0 = tout vert
Les projets d'essai sont créés dans un dossier temporaire, effacé à la fin (sauf --garder).
"""
import argparse
import importlib.util
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zlib

sys.dont_write_bytecode = True
ICI = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(ICI)
sys.path.insert(0, STUDIO)
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
import hote  # noqa: E402
import quetes  # noqa: E402
import style_paliers  # noqa: E402
import table_projet  # noqa: E402

T0 = time.mktime((2026, 11, 20, 10, 0, 0, 0, 0, -1))
MIN = 60
CAT = quetes.charger_catalogue()
RES = {"ok": 0, "echec": 0}
GIT_ENV = dict(os.environ, GIT_AUTHOR_NAME="essai", GIT_AUTHOR_EMAIL="essai@example.invalid",
               GIT_COMMITTER_NAME="essai", GIT_COMMITTER_EMAIL="essai@example.invalid", GIT_TERMINAL_PROMPT="0")


def ok(cond, msg):
    if cond:
        RES["ok"] += 1
        print("  ok   " + msg)
    else:
        RES["echec"] += 1
        print("  ÉCHEC " + msg)
    return cond


def ecrire(ch, contenu, binaire=False):
    os.makedirs(os.path.dirname(ch), exist_ok=True)
    with open(ch, "wb" if binaire else "w", **({} if binaire else {"encoding": "utf-8", "newline": "\n"})) as f:
        f.write(contenu)


def ecrire_json(ch, d):
    ecrire(ch, json.dumps(d, ensure_ascii=False, indent=1))


def lire_json(ch, defaut=None):
    try:
        with open(ch, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa
        return defaut


def png(ch, w=8, h=8, c=(120, 140, 160)):
    lignes = b"".join(b"\x00" + bytes(c) * w for _ in range(h))

    def bloc(t, data):
        return struct.pack(">I", len(data)) + t + data + struct.pack(">I", zlib.crc32(t + data) & 0xffffffff)
    ecrire(ch, b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) +
           bloc(b"IDAT", zlib.compress(lignes)) + bloc(b"IEND", b""), binaire=True)


def git(projet, *a):
    return subprocess.run(["git", "-C", projet, *a], env=GIT_ENV, capture_output=True, text=True)


def statuts(etat):
    return {k: v.get("statut") for k, v in etat["quetes"].items()}


# ------------------------------------------------------------------ projet d'essai (nouveau, Godot fictif)
REPONSES = {"genre.principal": "action_aventure", "monde.climat": "foret", "da.palette": "froide", "da.style": "stylise",
            "vision.pitch": "Un chevalier défend le château de sa vallée contre les ombres.", "moteur.nom": "godot",
            "gameplay.systemes": ["combat", "sauvegarde", "ia_ennemie", "dialogues"], "progression.duree": "5_10h",
            "son.musique": "adaptative", "multijoueur.mode": "coop_ligne", "monde.generation": "mixte",
            "histoire.place": "importante", "public.langues": "plus", "public.accessibilite": ["sous_titres", "touches"],
            "monetisation.publication": ["itch"], "ia.images": "non"}


def nouveau_projet(d, reponses=None, etat_q="en_cours"):
    st = os.path.join(d, ".studio")
    ecrire_json(os.path.join(st, "studio.config.json"), {"version": 1, "nom_projet": "Projet d'essai", "langue": "fr",
                                                         "moteur": {"nom": "godot"}, "postes": []})
    ecrire_json(os.path.join(st, "reponses_questionnaire.json"), {
        "version": 1, "etat": etat_q, "mode": "rapide", "langue": "fr",
        "reponses": {k: {"valeur": v, "source": "utilisateur", "via": "clic"} for k, v in (REPONSES if reponses is None else reponses).items()}})
    ecrire(os.path.join(d, "project.godot"), "config_version=5\n")


def questionnaire(d, etat_q):
    ch = os.path.join(d, ".studio", "reponses_questionnaire.json")
    q = lire_json(ch)
    q["etat"] = etat_q
    ecrire_json(ch, q)


def tache(jid, n, h=3, tags=None):
    t = {"id": f"{jid}-{n:02d}", "titre": f"Tâche {jid}-{n:02d}", "critere": "fait", "poste": "direction", "estimation_h": h,
         "depend_de": [], "statut": "a_faire"}
    if tags:
        t["tags"] = tags
    return t


def roadmap_essai():
    tags4 = ["sauvegarde", "feel", "ia", "reseau", "dialogues", "options", "accessibilite", "tutoriel", "perf"]
    return {"version": 1, "langue": "fr", "projet": "Projet d'essai", "rythme": {"heures_par_semaine": 10, "debut": "2026-11-20"},
            "niveau": {"xp_par_tache": 100, "xp_par_jalon": 500},
            "jalons": [{"id": "J0", "titre": "Cadrage", "taches": [tache("J0", 1, 1)]},
                       {"id": "J1", "titre": "Prototype", "taches": [tache("J1", i) for i in range(1, 4)]},
                       {"id": "J2", "titre": "Boucle", "taches": [tache("J2", i) for i in range(1, 5)]},
                       {"id": "J3", "titre": "Contenu", "taches": [tache("J3", i) for i in range(1, 4)]},
                       {"id": "J4", "titre": "Finition", "taches": [tache("J4", i + 1, 1, [tg]) for i, tg in enumerate(tags4)]},
                       {"id": "J5", "titre": "Sortie", "taches": [tache("J5", 1, 1, ["magasin"]), tache("J5", 2, 1, ["bande_annonce"])]}]}


class Roadmap:
    def __init__(self, d):
        self.ch = os.path.join(d, ".studio", "roadmap.json")

    def lire(self):
        return lire_json(self.ch)

    def verser(self, pred):
        r = self.lire()
        if not r:
            return None
        for j in r["jalons"]:
            for t in j["taches"]:
                if t["statut"] != "verse" and pred(j, t):
                    t["statut"] = "verse"
                    ecrire_json(self.ch, r)
                    return t["id"]
        return None

    def verser_tag(self, tag):
        return self.verser(lambda j, t: tag in (t.get("tags") or []))

    def verser_jalon(self, jid, n=99):
        for _ in range(n):
            if not self.verser(lambda j, t: j["id"] == jid):
                break

    def avancer(self):
        return self.verser(lambda j, t: not t.get("tags"))


def actions(d, rm):
    """Ce que l'équipe fait pour remplir chaque quête (fichiers, roadmap, git, da.json)."""
    st = os.path.join(d, ".studio")
    da_ch = os.path.join(st, "da.json")

    def da_maj(**k):
        da = lire_json(da_ch, {"version": 1, "source": "docs/DA.md"})
        da.update(k)
        da["valide_par_utilisateur"] = "2026-11-21T10:00:00"
        ecrire_json(da_ch, da)

    def commit():
        if not os.path.isdir(os.path.join(d, ".git")):
            git(d, "init", "-q")
        git(d, "add", "-A")
        git(d, "commit", "-q", "-m", "essai")

    def polices():
        ecrire(os.path.join(d, "assets/fonts/Titre.woff2"), b"wOF2" + b"\0" * 2000, binaire=True)
        ecrire(os.path.join(d, "assets/fonts/Interface.ttf"), b"\0\1\0\0" + b"\0" * 2000, binaire=True)
        da_maj(polices={"titre": {"fichier": "assets/fonts/Titre.woff2", "nom": "Titre", "licence": "OFL-1.1"},
                        "interface": {"fichier": "assets/fonts/Interface.ttf", "nom": "Interface", "licence": "OFL-1.1"}})

    def logo():
        ecrire(os.path.join(d, "assets/ui/logo.svg"), '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><circle cx="5" cy="5" r="4" fill="#f0a640"/></svg>')
        da_maj(logo={"fichier": "assets/ui/logo.svg"})

    def decor():
        ecrire(os.path.join(d, "docs/DA.md"), "# Direction artistique\n\n## Palette\nFroide.\n")
        png(os.path.join(d, "assets/ui/motif.png"))
        png(os.path.join(d, "captures/ecran_titre.png"), 16, 9)
        da_maj(decor={"motif": "assets/ui/motif.png", "affiches": ["captures/ecran_titre.png"]})

    def sons(n, dossier="assets/sons"):
        for i in range(n):
            ecrire(os.path.join(d, dossier, f"son_{i}.ogg"), b"OggS" + b"\0" * 64, binaire=True)

    return {
        "Q-FO-01": lambda: ecrire_json(rm.ch, roadmap_essai()),
        "Q-FO-02": commit,
        "Q-FO-03": lambda: ecrire_json(os.path.join(st, "skills.json"), {"maj": "2026-11-20", "installes": ["gamedev:router", "gamedev:game-feel"]}),
        "Q-FO-04": lambda: ecrire(os.path.join(d, "docs/GDD.md"), "# GDD\n\nUn chevalier, une vallée, un château à défendre.\n"),
        "Q-FO-05": lambda: rm.verser(lambda j, t: j["id"] == "J0"),
        "Q-PR-01": lambda: ecrire(os.path.join(d, "scenes/main.tscn"), "[gd_scene format=3]\n"),
        "Q-PR-02": lambda: rm.verser_jalon("J1", 2),
        "Q-PR-03": lambda: ecrire(os.path.join(d, "tests/test_joueur.gd"), "extends GutTest\n"),
        "Q-PR-04": lambda: ecrire(os.path.join(d, "docs/VERSIONS.md"), "# Versions\n\n- 0.1 : première version à essayer\n"),
        "Q-ID-01": lambda: png(os.path.join(d, "docs/da/planche_ambiance.png")),
        "Q-ID-02": lambda: da_maj(palette={"fond": "#16202a", "surface": "#223140", "texte": "#e9eef2", "accent": "#f0a640",
                                           "accent2": "#4fb0a4", "succes": "#6fae5e", "alerte": "#e2b866", "danger": "#c4543a",
                                           "bureau": {"mur": "#d6dee4", "sol": "#7d8790", "bois": "#8f7c68", "lumiere": "#e3efff"}}),
        "Q-ID-03": polices,
        "Q-ID-04": logo,
        "Q-ID-05": lambda: ecrire(os.path.join(d, "scenes/ui/menu_principal.tscn"), "[gd_scene format=3]\n"),
        "Q-ID-06": decor,
        "Q-SU-04": lambda: hote.enregistrer(d, {"nom": "Lou", "allure": "petite", "couleurs": "foret", "coin": "coeur", "ton": "chaleureux",
                                                "activites": ["boisson", "lit", "tournee"], "objets": ["tapis", "lampe"]}),
        "Q-ID-07": lambda: ecrire(os.path.join(d, "scenes/ui/hud.tscn"), "[gd_scene format=3]\n"),
        "Q-BO-01": lambda: rm.verser_jalon("J2"),
        "Q-BO-02": lambda: ecrire(os.path.join(d, "scripts/sauvegarde.gd"), "func save_game():\n\tvar f = ConfigFile.new()\n\tf.save(\"user://s.cfg\")\n"),
        "Q-BO-03": lambda: sons(5),
        "Q-BO-04": lambda: sons(1, "assets/music"),
        "Q-BO-05": lambda: rm.verser_tag("feel"),
        "Q-BO-06": lambda: rm.verser_tag("ia"),
        "Q-BO-07": lambda: rm.verser_tag("reseau"),
        "Q-CO-01": lambda: ecrire(os.path.join(d, "scenes/levels/niveau_1.tscn"), "[gd_scene format=3]\n"),
        "Q-CO-02": lambda: [ecrire(os.path.join(d, f"scenes/levels/niveau_{i}.tscn"), "[gd_scene format=3]\n") for i in (2, 3)],
        "Q-CO-03": lambda: rm.verser_tag("dialogues"),
        "Q-CO-04": lambda: ecrire(os.path.join(d, "scripts/generation.gd"), "var bruit = FastNoiseLite.new()\n"),
        "Q-CO-05": lambda: [ecrire(os.path.join(d, f"locales/{l}.po"), "msgid \"\"\n") for l in ("fr", "en")],
        "Q-FI-01": lambda: rm.verser_tag("options"),
        "Q-FI-02": lambda: rm.verser_tag("accessibilite"),
        "Q-FI-03": lambda: rm.verser_tag("tutoriel"),
        "Q-FI-04": lambda: rm.verser_tag("perf"),
        "Q-FI-05": lambda: ecrire(os.path.join(d, "docs/playtest_1.md"), "# Séance d'essai\n\nRetours : ...\n"),
        "Q-SO-01": lambda: ecrire(os.path.join(d, "build/windows/jeu.exe"), b"MZ" + b"\0" * 64, binaire=True),
        "Q-SO-02": lambda: rm.verser_tag("magasin"),
        "Q-SO-03": lambda: rm.verser_tag("bande_annonce"),
        "Q-SO-04": lambda: ecrire(os.path.join(d, "CREDITS.md"), "# Crédits\n\nPolices : OFL-1.1.\n"),
        "Q-SO-05": lambda: (commit(), git(d, "tag", "v1.0")),
    }


def recruter_comme_le_serveur(d, corps):
    """Ce que /api/recruter écrira après l'accord : la fiche de recrue (lancer: false)."""
    ecrire_json(os.path.join(d, ".studio", "recrues", corps["nom"] + ".json"),
                dict({k: corps[k] for k in ("nom", "nom_affiche", "role", "mission", "poste", "skills")}, lancer=False, via=corps["via"], origine="quete"))


# ------------------------------------------------------------------ 1. catalogue
def essai_catalogue():
    print("1. Catalogue")
    err = quetes.verifier_catalogue(mots_interdits=["projet perso d'essai"])
    ok(not err, f"catalogue valide ({len(CAT['quetes'])} quêtes, {sum(q['recompense']['xp'] for q in CAT['quetes'])} XP) {err[:3]}")
    ok(any(q["recompense"].get("deblocage", {}).get("bouton") == "audit" for q in CAT["quetes"]), "une quête débloque le bouton Audit (auditrice)")
    ok(sum(1 for q in CAT["quetes"] if q.get("soutien")) >= 3, "agents de soutien arrivés par quête : auditrice, contrôleur des modèles, optimiseur")


# ------------------------------------------------------------------ 2. la partie complète
def essai_partie(base):
    print("2. Un projet passe par toutes les quêtes")
    d = os.path.join(base, "partie")
    nouveau_projet(d)
    rm = Roadmap(d)
    act = actions(d, rm)
    t = T0
    e = quetes.passe(d, t, CAT)
    ok(not [k for k, v in e["quetes"].items() if v["statut"] in quetes.OUVERTES], "questionnaire en cours : aucune quête proposée")
    ok(e["habillage"]["palier"] == 1, "studio en maquette grise au départ (palier 1)")
    tab = lire_json(os.path.join(d, ".studio", "table_projet.json"))
    ok(tab and tab["detail"] == 1 and tab["source_palette"] == "carton", f"table : maquette en carton au départ ({tab and tab['theme']})")
    questionnaire(d, "termine")
    t += MIN
    e = quetes.passe(d, t, CAT)
    ouv = [k for k, v in e["quetes"].items() if v["statut"] in quetes.OUVERTES]
    ok(ouv == ["Q-FO-01"], f"questionnaire fini : « Pose ta roadmap » proposée seule ({ouv})")
    t += 10 * MIN
    e = quetes.passe(d, t, CAT)
    ok([k for k, v in e["quetes"].items() if v["statut"] in quetes.OUVERTES] == ["Q-FO-01"], "10 min plus tard : rien de plus (une principale à la fois)")

    vus_proposees, accepte_agents, demandes_ok, paliers, max_ouvertes = set(), 0, True, [1], 0
    xp_avant, faits, types_annonces = 0, set(), set()
    for tour in range(400):
        st = statuts(e)
        ouvertes = [k for k, v in st.items() if v in quetes.OUVERTES]
        max_ouvertes = max(max_ouvertes, len(ouvertes))
        for k in ouvertes:
            vus_proposees.add(k)
            q = e["quetes"][k]
            if q["statut"] == "proposee":
                agents = [a["agent"] for a in q["propositions"]["agents"]]
                r = quetes.repondre(d, k, "accepter", agents, maintenant=t, catalogue=CAT)
                if r.get("ouvre"):                       # quête jouée dans la page (l'hôte) : aucune demande pour l'assistant
                    demandes_ok &= "demande" not in r and r["ouvre"] == "hote"
                else:
                    dem = lire_json(os.path.join(d, ".studio", r["demande"]))
                    demandes_ok &= dem["type"] == "quete" and dem["lancer"] is False and all(c["lancer"] is False for c in dem["recruter"])
                for c in r["recruter"]:
                    recruter_comme_le_serveur(d, c)
                    accepte_agents += 1
                for cle in r.get("activer") or []:      # auditrice, contrôleur des modèles : la page les a déjà, un réglage les active
                    rg = lire_json(os.path.join(d, ".studio", "reglages.json"), {}) or {}
                    ecrire_json(os.path.join(d, ".studio", "reglages.json"), dict(rg, **{cle: True}))
                    accepte_agents += 1
            if k not in faits:
                faits.add(k)
                act.get(k, lambda: None)()   # quêtes de soutien : remplies par la recrue elle-même
        if not ouvertes and os.path.isfile(rm.ch):
            rm.avancer()          # le reste du travail avance la roadmap (tâches sans tag)
        t += 31 * MIN
        e = quetes.passe(d, t, CAT)
        if e["xp"] < xp_avant:
            ok(False, "l'XP ne baisse jamais")
        xp_avant = e["xp"]
        types_annonces.update(a["type"] for a in e["annonces"])
        if e["habillage"]["palier"] != paliers[-1]:
            paliers.append(e["habillage"]["palier"])
        restantes = [k for k, v in e["quetes"].items() if v.get("existe") and v["statut"] not in quetes.FAITES]
        if not restantes:
            break
    existantes = [k for k, v in e["quetes"].items() if v.get("existe")]
    restantes = [k for k in existantes if e["quetes"][k]["statut"] not in quetes.FAITES]
    ok(not restantes, f"toutes les quêtes du projet remplies : {len(existantes) - len(restantes)}/{len(existantes)} en {tour + 1} tours {restantes}")
    for k in restantes[:3]:
        print("       ", json.dumps(quetes.expliquer(d, k, t, CAT), ensure_ascii=False, default=str)[:600])
    cachees = [q["id"] for q in CAT["quetes"] if q["id"] not in existantes]
    ok(cachees == ["Q-ID-00"], f"seule la quête d'adoption n'existe pas pour un nouveau projet ({cachees})")
    ok(len(vus_proposees) >= len(existantes) - 4, f"quêtes proposées au bon moment avant d'être remplies : {len(vus_proposees)}/{len(existantes)}")
    ok(max_ouvertes <= 3, f"jamais plus de 3 quêtes ouvertes ensemble (max {max_ouvertes})")
    ok(demandes_ok and accepte_agents >= 10, f"acceptations : demandes « quete » lancer: false ; {accepte_agents} recrues prêtes, rien de lancé")
    ok(not os.path.isdir(os.path.join(d, ".claude", "agents")), "aucune définition d'agent écrite par les quêtes (le serveur le fera après accord)")
    xp_att = sum(CAT["_par_id"][k]["recompense"]["xp"] for k in existantes) + sum(a["xp_fin"] for a in CAT["actes"])
    ok(e["xp"] == xp_att and len(e["actes_finis"]) == 7, f"XP des quêtes et des 7 actes : {e['xp']} (attendu {xp_att}), niveau {e['niveau']}")
    ok(paliers == [1, 2, 3, 4, 5], f"habillage palier par palier : {paliers}")
    hab = lire_json(os.path.join(d, ".studio", "habillage.json"))
    ok(hab["jetons"]["--nuit"] == "#16202a" and len(hab["polices"]) == 2 and hab["logo"] and hab["decor"].get("motif"),
       "palier 5 : jetons de la palette, 2 polices copiées, logo, motif")
    ok(os.path.isfile(os.path.join(d, ".studio", "da", "habillage.css")) and "Jeu Texte" in open(os.path.join(d, ".studio", "da", "habillage.css"), encoding="utf-8").read(),
       "feuille .studio/da/habillage.css écrite (jetons + @font-face)")
    ok({"quete_proposee", "quete_remplie", "acte_fini", "coup_de_peinture"} <= types_annonces,
       f"annonces (file des succès) : {sorted(types_annonces)}")
    while rm.verser(lambda j, t: True):      # fin du projet : toute la roadmap versée
        pass
    bt = [b["id"] for b in e["deblocages"]["boutons"]]
    ok("audit" in bt and "modeles" in bt, f"boutons débloqués avec les boutons du haut : {bt}")
    aud = next(a for a in e["deblocages"]["agents"] if a["agent"] == "auditeur")
    ok(aud["bureau"] == "coin" and aud["embauche"], "l'auditrice a son bureau dans un coin")
    ok(lire_json(os.path.join(d, ".studio", "reglages.json"), {}).get("auditeur") is True and not os.path.isfile(os.path.join(d, ".studio", "recrues", "auditeur.json")),
       "auditrice : le réglage « auditeur » de la page est activé (son bureau du coin et son bouton Audit), pas de recrue en double")
    rg = lire_json(os.path.join(d, ".studio", "reglages.json"), {})
    ecrire_json(os.path.join(d, ".studio", "reglages.json"), dict(rg, soutien={"auditeur": False}))
    t += 31 * MIN
    e = quetes.passe(d, t, CAT)
    ok("audit" not in [b["id"] for b in e["deblocages"]["boutons"]], "auditrice désactivée dans les Réglages : le bouton Audit disparaît")
    ecrire_json(os.path.join(d, ".studio", "reglages.json"), dict(rg, auditeur=False))
    e = quetes.passe(d, t + 31 * MIN, CAT)
    ok("audit" not in [b["id"] for b in e["deblocages"]["boutons"]] and e["quetes"]["Q-SU-01"]["statut"] == "remplie",
       "auditrice renvoyée : bouton parti, la récompense reste")
    tab = lire_json(os.path.join(d, ".studio", "table_projet.json"))
    ok(tab["theme"] == "vallee_chateau" and tab["detail"] == 5 and tab["source_palette"] == "da" and "ecoulement" in tab["animations"],
       f"table : vallée et château de CE projet, détail 5/5, palette de la DA, animée ({tab['animations']})")
    res = quetes.resume(e)
    ok(res["remplies"] == len(existantes) and res["habillage"] == 5, f"résumé pour etat.json : {res}")


# ------------------------------------------------------------------ 3. rythme et réponses
def essai_rythme(base):
    print("3. Rythme, réponses, preuve déposée")
    d = os.path.join(base, "rythme")
    nouveau_projet(d, etat_q="termine")
    t = T0
    e = quetes.passe(d, t, CAT)
    ouv = [k for k, v in statuts(e).items() if v in quetes.OUVERTES]
    prets = [k for k, v in e["quetes"].items() if v.get("pret")]
    ok(len(ouv) == 1 and len(prets) >= 1, f"plusieurs quêtes prêtes, une seule principale proposée ({ouv})")
    try:
        quetes.repondre(d, "Q-FO-01", "refuser", maintenant=t, catalogue=CAT)
        ok(False, "refuser une principale doit être refusé")
    except quetes.Refus as x:
        ok(x.code == 403, "refuser une principale : 403 (« plus tard » seulement)")
    try:
        quetes.repondre(d, "Q-SO-05", "accepter", maintenant=t, catalogue=CAT)
        ok(False, "accepter une quête non proposée")
    except quetes.Refus as x:
        ok(x.code == 404, "accepter une quête non proposée : 404")
    quetes.repondre(d, "Q-FO-01", "plus_tard", maintenant=t, catalogue=CAT)
    try:
        quetes.repondre(d, "Q-FO-01", "plus_tard", maintenant=t + 5, catalogue=CAT)
        ok(False, "doublon")
    except quetes.Refus as x:
        ok(x.code in (404, 409), f"même réponse dans les 60 s : refusée ({x.code})")
    e = quetes.passe(d, t + 5 * MIN, CAT)
    ok(e["quetes"]["Q-FO-01"]["statut"] == "plus_tard", "« plus tard » noté")
    ok(not [k for k, v in statuts(e).items() if v == "proposee"], "5 min après : pas de nouvelle proposition (30 min entre deux)")
    e = quetes.passe(d, t + 31 * MIN, CAT, absent=True)
    ok(not [k for k, v in statuts(e).items() if v == "proposee"], "mode absent : rien de proposé")
    e = quetes.passe(d, t + 32 * MIN, CAT, nuit=True)
    ok(not [k for k, v in statuts(e).items() if v == "proposee"], "nuit : rien de proposé")
    e = quetes.passe(d, t + 33 * MIN, CAT)
    prop = [k for k, v in statuts(e).items() if v == "proposee"]
    ok(prop and prop[0] != "Q-FO-01", f"après 30 min : la suivante est proposée ({prop}), pas celle remise à plus tard")
    # preuve déposée (GDD dans un autre fichier)
    ecrire(os.path.join(d, "notes/conception_v1.md"), "# Mon document de conception\n")
    e["quetes"]["Q-FO-04"]["statut"] = "proposee"
    ecrire_json(os.path.join(d, ".studio", "quetes_etat.json"), e)
    try:
        quetes.repondre(d, "Q-FO-04", "preuve", chemin="../dehors.md", maintenant=t + 34 * MIN, catalogue=CAT)
        ok(False, "preuve hors projet")
    except quetes.Refus as x:
        ok(x.code == 400, "preuve « ../ » : refusée (400)")
    quetes.repondre(d, "Q-FO-04", "preuve", chemin="notes/conception_v1.md", maintenant=t + 34 * MIN, catalogue=CAT)
    e = quetes.passe(d, t + 35 * MIN, CAT)
    ok(e["quetes"]["Q-FO-04"]["statut"] == "remplie" and e["quetes"]["Q-FO-04"]["preuve"] == "notes/conception_v1.md",
       "preuve déposée vérifiée : quête remplie avec son chemin")
    os.remove(os.path.join(d, "notes/conception_v1.md"))
    e = quetes.passe(d, t + 36 * MIN, CAT)
    ok(e["quetes"]["Q-FO-04"]["statut"] == "remplie" and e["quetes"]["Q-FO-04"].get("preuve_introuvable"),
       "preuve disparue : « preuve introuvable », la récompense reste")
    e = quetes.passe(d, t + 25 * 3600, CAT)
    e = quetes.passe(d, t + 26 * 3600, CAT)
    ok(e["quetes"]["Q-FO-01"]["statut"] in ("proposee",) or any(v == "proposee" for v in statuts(e).values()),
       "après 24 h : la quête remise revient dans la file")
    # jalon qui vient de finir : on laisse passer la fête
    d2 = os.path.join(base, "fete")
    nouveau_projet(d2, etat_q="termine")
    r = roadmap_essai()
    ecrire_json(os.path.join(d2, ".studio", "roadmap.json"), r)
    quetes.passe(d2, T0, CAT)
    for tt in r["jalons"][1]["taches"]:
        tt["statut"] = "verse"
    ecrire_json(os.path.join(d2, ".studio", "roadmap.json"), r)
    e = quetes.passe(d2, T0 + 40 * MIN, CAT)
    ok(e["fete_jusqu_a"] > T0 + 40 * MIN and "jalon qui vient de finir" in (e.get("attente") or []), "jalon fini : aucune proposition pendant la minute de fête")
    # réglages
    d3 = os.path.join(base, "reglages")
    nouveau_projet(d3, etat_q="termine")
    ecrire_json(os.path.join(d3, ".studio", "reglages.json"), {"quetes_actives": False, "quetes_secondaires": False})
    e = quetes.passe(d3, T0, CAT)
    ok(not [k for k, v in statuts(e).items() if v in quetes.OUVERTES], "quetes_actives: false : rien de proposé")
    ok(not any(v.get("existe") for k, v in e["quetes"].items() if CAT["_par_id"][k]["type"] == "secondaire"), "quetes_secondaires: false : aucune secondaire")


# ------------------------------------------------------------------ 4. acceptation : poste déjà là, bureaux pleins
def essai_acceptation(base):
    print("4. Acceptation")
    d = os.path.join(base, "accepter")
    nouveau_projet(d, etat_q="termine")
    ecrire_json(os.path.join(d, ".studio", "roadmap.json"), roadmap_essai())
    ecrire_json(os.path.join(d, ".studio", "recrues", "maquettiste.json"), {"nom": "maquettiste", "poste": "integration-moteur", "skills": []})
    e = quetes.passe(d, T0, CAT)
    e["quetes"]["Q-PR-01"]["statut"] = "proposee"
    ecrire_json(os.path.join(d, ".studio", "quetes_etat.json"), e)
    e = quetes.passe(d, T0 + 31 * MIN, CAT)
    a = e["quetes"]["Q-PR-01"]["propositions"]["agents"][0]
    ok(a["action"] == "confier" and a["confier_a"] == "maquettiste", "un agent du même poste existe : « Confier à » lui, pas de recrue en double")
    r = quetes.repondre(d, "Q-PR-01", "accepter", maintenant=T0 + 32 * MIN, catalogue=CAT)
    ok(not r["recruter"] and r["confier"], "accepter : aucune recrue, la tâche lui est confiée")
    for i in range(12):
        ecrire_json(os.path.join(d, ".studio", "recrues", f"agent-{i:02d}.json"), {"nom": f"agent-{i:02d}", "poste": f"p{i}", "skills": []})
    e["quetes"]["Q-PR-03"] = dict(e["quetes"].get("Q-PR-03", {}), statut="proposee")
    ecrire_json(os.path.join(d, ".studio", "quetes_etat.json"), e)
    e = quetes.passe(d, T0 + 63 * MIN, CAT)
    a = e["quetes"]["Q-PR-03"]["propositions"]["agents"][0]
    ok(a["action"] == "bureaux_pleins", "12 bureaux pleins : la quête le dit et ne propose que la tâche")
    sk = e["quetes"]["Q-PR-03"]["propositions"]["skills"]
    ok(any(s["nom"] == "gamedev:godot-gdscript-headless-testing" for s in sk), "skills du moteur ajoutés (Godot : tests headless)")
    ok(all(s["installe"] is None for s in sk), "sans skills.json : installé / à installer inconnu (Claude le dira)")


# ------------------------------------------------------------------ 5. habillage
def essai_habillage(base):
    print("5. Habillage")
    d = os.path.join(base, "habillage")
    nouveau_projet(d, etat_q="termine")
    da_ch = os.path.join(d, ".studio", "da.json")
    ecrire_json(da_ch, {"version": 1, "palette": {"fond": "#16202a", "texte": "#e9eef2", "accent": "#f0a640"}})
    h = style_paliers.calculer(d, {}, "jeu")
    ok(h["palier"] == 1 and h["brouillon"] and h["jetons"]["--nuit"] == "#1b1c1e", "da.json brouillon (non validé) : rien n'est appliqué, palier 1")
    ecrire_json(da_ch, {"version": 1, "valide_par_utilisateur": "x", "palette": {"fond": "#16202a", "texte": "#e9eef2", "accent": "#f0a640"}})
    ok(style_paliers.calculer(d, {}, "jeu")["palier"] == 2, "validé avec palette (mode jeu) : palier 2")
    ok(style_paliers.calculer(d, {}, "progressif")["palier"] == 1, "mode progressif : palier 2 seulement quand la quête Palette est remplie")
    ok(style_paliers.calculer(d, {"Q-ID-02": "remplie"}, "progressif")["palier"] == 2, "quête Palette remplie : palier 2")
    ecrire_json(da_ch, {"version": 1, "valide_par_utilisateur": "x", "palette": {"fond": "#3a3a3a", "surface": "#444444", "texte": "#5a5a5a",
                                                                                "accent": "#f0a640", "succes": "#6fae5e", "alerte": "#6fb05f", "danger": "#c4543a"}})
    h = style_paliers.calculer(d, {}, "jeu")
    c1 = style_paliers.contraste(h["jetons"]["--texte"], "#3a3a3a")
    c2 = style_paliers.contraste(h["jetons"]["--texte"], "#444444")
    ok(c1 >= 4.5 and c2 >= 4.5 and any("lisibilité" in a["fr"] for a in h["ajustements"]), f"texte gris sur gris corrigé ({c1:.1f}:1, {c2:.1f}:1) et noté")
    ok(h["jetons"]["--sapin"] == style_paliers.ETATS_REFERENCE["succes"] and any("état" in a["fr"] for a in h["ajustements"]),
       "couleurs d'état trop proches : celles du studio de référence gardées")
    ecrire_json(da_ch, {"version": 1, "valide_par_utilisateur": "x", "palette": {"fond": "#f4f1ea", "texte": "#20242a", "accent": "#2f6fb0"}})
    ok(style_paliers.calculer(d, {}, "jeu")["theme"] == "clair", "fond clair : thème clair")
    ecrire(os.path.join(d, "assets/fonts/Lourde.ttf"), b"\0" * (5 * 1024 * 1024), binaire=True)
    ecrire(os.path.join(d, "assets/fonts/Ok.woff2"), b"wOF2" + b"\0" * 500, binaire=True)
    ecrire(os.path.join(d, "assets/ui/logo.svg"), '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script><rect width="5" height="5"/></svg>')
    da = {"version": 1, "valide_par_utilisateur": "x", "palette": {"fond": "#16202a", "texte": "#e9eef2", "accent": "#f0a640"},
          "polices": {"titre": {"fichier": "assets/fonts/Lourde.ttf", "nom": "Lourde"}, "interface": {"fichier": "assets/fonts/Ok.woff2", "nom": "Ok"}},
          "logo": {"fichier": "assets/ui/logo.svg"}, "decor": {"motif": "../dehors.png"}}
    ecrire_json(da_ch, da)
    h = style_paliers.calculer(d, {}, "jeu")
    ok(h["palier"] == 2 and any("Ko" in r["raison"] for r in h["refus"]), f"police de 5 Mo refusée : le studio reste au palier Palette ({h['palier']})")
    da["polices"]["titre"] = {"fichier": "assets/fonts/Ok.woff2", "nom": "Ok", "licence": "OFL-1.1"}
    ecrire_json(da_ch, da)
    h = style_paliers.calculer(d, {}, "jeu")
    lg = h["logo"]["fichier"]
    ok(h["palier"] == 4 and lg["insertion"] == "img" and lg.get("contenu_actif"), "logo SVG avec <script> : servi seulement en <img>, marqué")
    ok(os.path.isfile(os.path.join(d, ".studio", lg["url"])) and lg["url"].startswith("da/"), "fichiers copiés dans .studio/da/ (le serveur ne sert que ce dossier)")
    _, pb = style_paliers.lire_da(d)
    ok(any("decor" in p for p in pb) and h["palier"] < 5, "chemin « ../ » ignoré (décor non appliqué)")
    ok(any("licence" in a["fr"] for a in h["ajustements"]), "police sans licence notée : rappel avant la sortie")
    h = style_paliers.calculer(d, {}, "atelier")
    ok(h["jetons"] == style_paliers.ATELIER and h["rendu"] == "atelier", "habillage_mode atelier : jetons du style de référence même avec da.json")
    ecrire_json(os.path.join(d, ".studio", "reglages.json"), {"habillage_mode": "atelier"})
    e = quetes.passe(d, T0, CAT)
    ok(e["habillage"]["mode"] == "atelier", "réglage lu par quetes.py : mode Atelier")


# ------------------------------------------------------------------ 6. adoption
def charger_essai_complet():
    spec = importlib.util.spec_from_file_location("_essai_complet", os.path.join(ICI, "essai_complet.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def essai_adoption(base):
    print("6. Adoption d'un projet existant")
    ec = charger_essai_complet()
    d = os.path.join(base, "essai_adoption")
    print("   " + ec.creer_projet_fictif(d))
    png(os.path.join(d, "assets", "ui", "logo_renard.png"))     # le projet a déjà un logo : une DA existe
    ec.adoption_py(d, "analyser")
    ec.adoption_py(d, "preremplir")
    avant = ec.empreintes_essai(d)
    questionnaire(d, "termine")
    e = quetes.passe(d, T0, CAT)
    faites = sorted(k for k, v in statuts(e).items() if v == "deja_faite")
    attendues = {"Q-FO-02", "Q-PR-01", "Q-BO-02", "Q-ID-07"}
    ok(attendues <= set(faites), f"quêtes déjà faites : {faites}")
    ann = [a for a in e["annonces"]]
    ok(len(ann) <= 2 and sum(1 for a in ann if a["type"] == "deja_faites") == 1 and not any(a["type"] == "quete_remplie" for a in ann),
       f"une seule bannière « Ton projet remplit déjà {len(faites)} quêtes », pas de pluie de fanfares")
    ok(e["xp"] >= sum(CAT["_par_id"][k]["recompense"]["xp"] for k in faites), f"XP comptée en entier : {e['xp']} (niveau {e['niveau']})")
    e2 = quetes.passe(d, T0 + 31 * MIN, CAT)
    ok(all(e2["quetes"][k]["statut"] == "deja_faite" for k in faites), "jamais reproposées")
    ok(ec.empreintes_essai(d) == avant, "aucun fichier existant du projet touché (empreintes identiques)")
    out = ec.adoption_py(d, "verifier")
    ok(bool(out.strip()), "adoption.py verifier : code 0 (aucun fichier existant modifié)")
    prem = next((a for a in e["annonces"] if a["type"] == "quete_proposee"), {})
    ok(prem.get("quete") == "Q-ID-00", f"DA déjà présente : « Habille ton studio avec ton jeu » proposée en premier ({prem.get('quete')})")
    e3 = quetes.passe(d, T0 + 62 * MIN, CAT)
    rattr = [k for k, v in e3["quetes"].items() if v.get("rattrapage")]
    ok(bool(rattr), f"quêtes d'actes passés non remplies : proposées en rattrapage ({rattr})")
    tab = table_projet.calculer(d)
    ok(tab["theme"] in ("foret", "plateforme"), f"table d'un jeu de plateforme en forêt : {tab['theme']} ({tab['pourquoi']})")


# ------------------------------------------------------------------ 7. table du bureau
def essai_table(base):
    print("7. Table du bureau : le projet de CE studio")
    cas = [({}, "neutre"), ({"genre.principal": "course"}, "circuit"), ({"monde.climat": "espace", "vision.pitch": "Un vaisseau perdu."}, "vaisseau"),
           ({"monde.climat": "ville"}, "ville"), ({"genre.principal": "cartes"}, "plateau_cartes"),
           ({"vision.pitch": "Explorer un donjon et ses cryptes."}, "donjon")]
    for rep, attendu in cas:
        d = os.path.join(base, "table_" + attendu)
        nouveau_projet(d, rep, "termine")
        tab = table_projet.calculer(d)
        ok(tab["theme"] == attendu and tab["elements"] and tab["description"]["fr"] and tab["description"]["en"],
           f"{json.dumps(rep, ensure_ascii=False)[:60]} → {tab['theme']}")
    d = os.path.join(base, "table_neutre")
    r = roadmap_essai()
    details = []
    for jid in ("J1", "J2", "J3", "J4"):
        for tt in next(j for j in r["jalons"] if j["id"] == jid)["taches"]:
            tt["statut"] = "verse"
        ecrire_json(os.path.join(d, ".studio", "roadmap.json"), r)
        details.append(table_projet.calculer(d)["detail"])
    ok(details == sorted(details) and details[-1] == 5, f"plus détaillée à chaque jalon : {details}")
    tab = table_projet.calculer(d)
    ok(any(e["type"] == "unite" and e.get("anime") for e in tab["elements"]) and tab["sprites_a_produire"], "détail 5 : unités animées, sprites à produire listés")
    ok(all(s["outil"] != "generation_image" for s in tab["sprites_a_produire"]), "génération d'image seulement si l'utilisateur l'a permise")


# ------------------------------------------------------------------ 8. performance
def essai_perf(base):
    print("8. Performance")
    d = os.path.join(base, "perf")
    nouveau_projet(d, etat_q="termine")
    for i in range(2000):
        ecrire(os.path.join(d, "src", f"d{i // 100:02d}", f"f{i:04d}.txt"), "x")
    quetes.passe(d, T0, CAT)
    dt = []
    for k in range(1, 4):
        a = time.perf_counter()
        quetes.passe(d, T0 + k * 31 * MIN, CAT)
        dt.append(1000 * (time.perf_counter() - a))
    ok(min(dt) < 300, f"un passage sur 2 000 fichiers : {min(dt):.0f} ms (< 300 ms ; essais {', '.join(f'{x:.0f}' for x in dt)})")
    idx = lire_json(os.path.join(d, ".studio", "quetes_index.json"))
    ok(len(idx["fichiers"]) >= 2000 and idx["en_cours"] is None, "index complet, repris d'un passage à l'autre (.studio/quetes_index.json)")


# ------------------------------------------------------------------ 9. serveur et page (branchement S4)
def essai_serveur(base):
    print("9. Serveur et page")
    import socket
    import subprocess
    import urllib.error
    import urllib.request
    d = os.path.join(base, "serveur")
    nouveau_projet(d, etat_q="termine")
    st = os.path.join(d, ".studio")
    conf = lire_json(os.path.join(st, "studio.config.json"))
    conf.update(mode="travail", postes=[{"id": "direction", "nom": "Direction"}, {"id": "code", "nom": "Code"}, {"id": "art", "nom": "Art"}])
    ecrire_json(os.path.join(st, "studio.config.json"), conf)
    ecrire_json(os.path.join(st, "roadmap.json"), roadmap_essai())
    e = quetes.passe(d)
    for qid in ("Q-SU-01", "Q-FO-04"):
        e["quetes"][qid] = dict(e["quetes"].get(qid, {}), statut="proposee", existe=True)
    ecrire_json(os.path.join(st, "quetes_etat.json"), e)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    base_url = f"http://127.0.0.1:{port}"
    srv = subprocess.Popen([sys.executable, "-I", "-B", os.path.join(STUDIO, "serveur_studio.py"), "--projet", d, "--port", str(port)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def api(route, corps=None):
        req = urllib.request.Request(base_url + route, data=None if corps is None else json.dumps(corps).encode("utf-8"),
                                     headers={"Content-Type": "application/json", "Origin": base_url, "Host": f"127.0.0.1:{port}"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read().decode("utf-8") or "{}")
    try:
        for _ in range(50):
            try:
                if api("/api/qui")[0] == 200:
                    break
            except OSError:
                time.sleep(0.1)
        code, cat = api("/quetes.json")
        ok(code == 200 and len(cat.get("quetes", [])) >= 40, "le catalogue est servi à la page (/quetes.json)")
        e = quetes.passe(d)          # propositions détaillées des quêtes ouvertes
        ok(e["quetes"]["Q-SU-01"]["statut"] == "proposee", "quête de l'auditrice proposée (équipe de 3)")
        code, r = api("/api/quete", {"id": "Q-FO-04", "action": "refuser"})
        ok(code == 403, "refuser une quête principale : 403 (plus tard seulement)")
        code, r = api("/api/quete", {"id": "../Q-SU-01", "action": "accepter"})
        ok(code == 400, "id de quête mal formé : 400")
        code, r = api("/api/quete", {"id": "Q-XX-99", "action": "accepter"})
        ok(code == 404, "quête inconnue : 404")
        code, r = api("/api/quete", {"id": "Q-SU-01", "action": "accepter", "agents": ["auditeur"]})
        rg = lire_json(os.path.join(st, "reglages.json"), {})
        ok(code == 200 and r.get("actives") == ["auditeur"] and rg.get("auditeur") is True,
           "accepter : l'auditrice est activée (réglage « auditeur » : son bureau du coin et le bouton Audit de la page)")
        ok(not os.path.exists(os.path.join(st, "recrues", "auditeur.json")) and lire_json(os.path.join(st, r["demande"]), {}).get("lancer") is False,
           "pas de recrue en double ; demande « quete » lancer: false, rien de lancé")
        code, r = api("/api/quete", {"id": "Q-SU-01", "action": "accepter", "agents": ["auditeur"]})
        ok(code in (404, 409), "deuxième acceptation refusée (doublon ou déjà acceptée)")
        e = quetes.passe(d)
        ok(e["quetes"]["Q-SU-01"]["statut"] == "remplie" and [b["id"] for b in e["deblocages"]["boutons"]] == ["audit"], "quête remplie : le bouton « Audit » est débloqué")
        code, r = api("/api/reglages", {"auditeur": False})
        e = quetes.passe(d)
        ok(code == 200 and not e["deblocages"]["boutons"], "auditrice coupée dans les Réglages (« auditeur ») : le bouton disparaît")
        code, r = api("/api/reglages", {"auditeur": True, "habillage_mode": "atelier"})
        ok(code == 200 and r["reglages"].get("habillage_mode") == "atelier", "réglage habillage_mode (progressif, atelier, jeu) enregistré")
        code, r = api("/api/reglages", {"habillage_mode": "fluo"})
        ok(code == 400, "habillage_mode inconnu : 400")
        quetes.passe(d)
        code, h = api("/habillage.json")
        ok(code == 200 and h.get("mode") == "atelier", "habillage.json servi à la page")
        code, tb = api("/table_projet.json")
        ok(code == 200 and tb.get("elements"), "table_projet.json servi à la page (maquette du projet)")
        code, m = api("/api/modeles")
        ok(code == 200 and m.get("controle_modeles") is False, "contrôleur des modèles pas encore arrivé (réglage absent) : coupé, il arrive par sa quête")
        api("/api/reglages", {"controle_modeles": True})
        code, m = api("/api/modeles")
        ok(code == 200 and m.get("controle_modeles") is True, "quête acceptée (controle_modeles: true) : contrôleur allumé")
        api("/api/reglages", {"quetes_actives": False})
        rg = lire_json(os.path.join(st, "reglages.json"), {})
        rg.pop("controle_modeles", None)
        ecrire_json(os.path.join(st, "reglages.json"), rg)
        code, m = api("/api/modeles")
        ok(code == 200 and m.get("controle_modeles") is True, "quêtes coupées : le contrôleur reste allumé par défaut (comme avant)")
        api("/api/reglages", {"quetes_actives": True})
        # le moteur repasse tout de suite quand un réglage des quêtes change (mode du style), sans attendre 60 s
        sys.path.insert(0, STUDIO)
        import studio_etat
        se = studio_etat.Studio(d) if hasattr(studio_etat, "Studio") else None
        if se is not None and hasattr(se, "quetes"):
            se.quetes(tout=True)
            api("/api/reglages", {"habillage_mode": "progressif"})
            se.quetes()
            ok((lire_json(os.path.join(st, "habillage.json"), {}) or {}).get("mode") == "progressif",
               "studio_etat : mode du style changé, habillage.json réécrit au passage suivant (pas 60 s)")
            api("/api/reglages", {"habillage_mode": "atelier"})
            se.quetes()
            ok((lire_json(os.path.join(st, "habillage.json"), {}) or {}).get("mode") == "atelier", "studio_etat : retour à l'Atelier vu tout de suite")
        else:
            print("  (studio_etat.Studio absent : réaction immédiate non vérifiée ici)")
    finally:
        srv.terminate()
        try:
            srv.wait(10)
        except subprocess.TimeoutExpired:
            srv.kill()
    page = open(os.path.join(STUDIO, "studio.html"), encoding="utf-8").read()
    ok('<script src="quetes_page.js"></script>' in page and "Quetes.maj()" in page and "Quetes.themeBureau" in page
       and "TableProjet.dessiner" in page and "Quetes.bulle()" in page and "placeDe(i)" in page,
       "studio.html : module des quêtes chargé, cycle, thème du bureau, table, bulle « ! », bureau des agents de soutien")
    js = open(os.path.join(STUDIO, "quetes_page.js"), encoding="utf-8").read()
    ok(all(k in js for k in ("bt-quetes", "bt-soutien", "quete-suivie", "hab-maquette", "prefers-reduced-motion", "/api/quete")),
       "quetes_page.js : bouton Quêtes, boutons de soutien, quête suivie, maquette grise, mouvement réduit, route")
    ok(all(k in js for k in ("xp-fete", "xfRebond", "xfEtincelle", "xp-pulse", "xp_niveau", "xp_fete", "studio:roadmap", "Son.coupe()", "babil_son", "visibilitychange")),
       "quetes_page.js : gains d'XP (milieu de l'écran, rebond, étincelles, son muet/babillage, envol, niveau, réglage, groupés)")
    ok("modeLocal(" in js and "REG_BOUTON" in js and "bt-modeles" in js,
       "quetes_page.js : mode du style et boutons des agents de soutien appliqués tout de suite ; Modèles caché avant sa quête")
    try:
        r = subprocess.run(["node", "--check", os.path.join(STUDIO, "quetes_page.js")], capture_output=True, timeout=30)
        ok(r.returncode == 0, "quetes_page.js : syntaxe JavaScript valide (node --check)")
    except (OSError, subprocess.TimeoutExpired):
        print("  (node absent : syntaxe du module non vérifiée)")


def essai_500_reponses(base):
    """G2 : passé 500 réponses (liste coupée à 500), une nouvelle réponse s'applique encore ; un fichier abîmé est mis de côté."""
    print("Réponses aux quêtes : au-delà de 500, fichier abîmé")
    d = os.path.join(base, "q500")
    st = os.path.join(d, ".studio")
    os.makedirs(st, exist_ok=True)
    ids = [k for k in CAT["_par_id"]][:2]
    etat = {"quetes": {k: {"statut": "proposee"} for k in ids}, "suivie": None, "reponses_lues": 500}
    anciennes = [{"id": "inconnue", "action": "suivre", "t": int(T0) - 7200} for _ in range(500)]   # format ancien : sans « n »
    ecrire_json(os.path.join(st, "quetes_reponses.json"), anciennes)
    quetes.appliquer_reponses(d, etat, CAT, T0, [])
    ok(etat.get("suivie") is None and etat.get("reponse_n") == 500, f"500 réponses anciennes déjà lues : rien d'appliqué (curseur {etat.get('reponse_n')})")
    for i, k in enumerate(ids):
        ecrire_json(os.path.join(st, "quetes_etat.json"), etat)
        try:
            r = quetes.repondre(d, k, "suivre", maintenant=T0 + 60 * (i + 1), catalogue=CAT)["reponse"]
        except quetes.Refus as e:
            ok(False, f"réponse n° {501 + i} refusée : {e}")
            return
        liste = lire_json(os.path.join(st, "quetes_reponses.json"), [])
        quetes.appliquer_reponses(d, etat, CAT, T0 + 60 * (i + 1), [])
        ok(len(liste) == 500 and r.get("n") == 501 + i and etat.get("suivie") == k,
           f"réponse n° {501 + i} appliquée alors que la liste reste à {len(liste)} (suivie : {etat.get('suivie')})")
    ecrire(os.path.join(st, "quetes_reponses.json"), '[{"id": "abîmé"')
    ecrire_json(os.path.join(st, "quetes_etat.json"), etat)
    try:
        quetes.repondre(d, ids[0], "suivre", maintenant=T0 + 600, catalogue=CAT)
        repris = True
    except quetes.Refus:
        repris = False
    copies = [f for f in os.listdir(st) if f.startswith("quetes_reponses.corrompu-")]
    ok(repris and len(copies) == 1, f"quetes_reponses.json abîmé : mis de côté ({copies}), la réponse est quand même enregistrée")


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--garder", action="store_true", help="garder le dossier temporaire")
    garder = a.parse_args(argv).garder
    base = tempfile.mkdtemp(prefix="essai_quetes_")
    print(f"Essai des quêtes : {base}")
    debut = time.time()
    try:
        essai_catalogue()
        essai_partie(base)
        essai_rythme(base)
        essai_acceptation(base)
        essai_habillage(base)
        essai_adoption(base)
        essai_table(base)
        essai_perf(base)
        essai_serveur(base)
        essai_500_reponses(base)
    finally:
        if not garder:
            reessai = lambda f, p, _e: (os.chmod(p, 0o700), f(p))  # noqa: E731  fichiers en lecture seule de .git sous Windows
            shutil.rmtree(base, **({"onexc": reessai} if sys.version_info >= (3, 12) else {"onerror": reessai}))
    print(f"\n{RES['ok']} ok, {RES['echec']} échec(s) en {time.time() - debut:.1f} s")
    return 0 if RES["echec"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
