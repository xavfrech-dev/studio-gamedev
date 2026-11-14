"""Essai de Santé du PC « vrai agent » (sante_machine.py), sans navigateur ni élévation, sans toucher à la vraie corbeille.

python -I -B essai_sante.py [--dossier D]

Faux projet Unreal (caches, builds, fichiers temporaires), dépôt git avec trois worktrees (fusionné et propre, non fusionné,
fusionné mais sale), FAUX DISQUE PRESQUE PLEIN : l'agent doit proposer un ménage chiffré (décision sous la cloche) sans rien
effacer ; « Pas maintenant » reporte ; « Faire ce ménage » efface seulement ce qui est permis (les 2 dernières builds,
le worktree non fusionné, le worktree sale, le projet et un dossier hors du projet glissé dans la proposition restent) ;
journal écrit. Températures lues d'un faux relevé (valeur ACPI figée = non disponible). Route /api/sante : refus sans clic,
refus à distance ; aucune élévation n'est jamais demandée par l'essai.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ICI = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(ICI)
sys.path.insert(0, STUDIO)
sys.dont_write_bytecode = True
import sante_machine as S  # noqa: E402

VIEUX = time.time() - 3 * 86400
MO = 1024 * 1024
ERREURS = []


def verifie(cond, msg):
    print(("  ok    " if cond else "  ÉCHEC ") + msg)
    if not cond:
        ERREURS.append(msg)


def fichier(p, octets=2 * MO, vieux=True):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(os.urandom(1024) * (octets // 1024))
    if vieux:
        os.utime(p, (VIEUX, VIEUX))


def vieillir(racine):
    for r, ds, fs in os.walk(racine):
        for n in fs + ds:
            try:
                os.utime(os.path.join(r, n), (VIEUX, VIEUX))
            except OSError:
                pass
    os.utime(racine, (VIEUX, VIEUX))


def git(d, *a):
    r = subprocess.run(["git", "-C", d, *a], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, GIT_AUTHOR_NAME="essai", GIT_AUTHOR_EMAIL="essai@exemple.invalid",
                                GIT_COMMITTER_NAME="essai", GIT_COMMITTER_EMAIL="essai@exemple.invalid"))
    if r.returncode:
        raise SystemExit(f"git {' '.join(a)} : {r.stderr}")
    return r.stdout


def preparer(base):
    if os.path.exists(base):
        shutil.rmtree(base, ignore_errors=True)
    P = os.path.join(base, "Jeu")
    os.makedirs(os.path.join(P, ".studio"))
    open(os.path.join(P, "Jeu.uproject"), "w").write("{}")
    open(os.path.join(P, ".gitignore"), "w").write("DerivedDataCache/\nIntermediate/\nSaved/\nBuilds/\n.studio/\n")
    fichier(os.path.join(P, "Content", "carte.umap"), vieux=False)
    git(P, "init", "-q", "-b", "main")
    git(P, "add", "-A")
    git(P, "commit", "-q", "-m", "départ")
    fichier(os.path.join(P, "DerivedDataCache", "a.ddp"), 3 * MO)
    fichier(os.path.join(P, "Intermediate", "b.obj"))
    fichier(os.path.join(P, "Saved", "Logs", "Jeu.log"))
    for i in range(1, 5):                                   # b4 la plus récente : b3 et b4 gardées
        d = os.path.join(P, "Builds", f"b{i}")
        fichier(os.path.join(d, "Jeu.pak"))
        t = VIEUX + i * 3600
        os.utime(os.path.join(d, "Jeu.pak"), (t, t))
        os.utime(d, (t, t))
    fichier(os.path.join(P, ".studio", "vieux.tmp"))
    W = os.path.join(base, "wts")
    for nom, br in (("wt_fusion", "f1"), ("wt_libre", "f2"), ("wt_sale", "f3")):
        git(P, "worktree", "add", "-q", "-b", br, os.path.join(W, nom))
        fichier(os.path.join(W, nom, "Content", f"{br}.uasset"), vieux=False)
        git(os.path.join(W, nom), "add", "-A")
        git(os.path.join(W, nom), "commit", "-q", "-m", br)
    git(P, "merge", "-q", "--no-edit", "f1")
    git(P, "merge", "-q", "--no-edit", "f3")
    fichier(os.path.join(W, "wt_sale", "brouillon.txt"), 64 * 1024)   # non suivi : jamais retiré
    for nom in ("wt_fusion", "wt_libre", "wt_sale"):
        vieillir(os.path.join(W, nom))
        gd = git(os.path.join(W, nom), "rev-parse", "--absolute-git-dir").strip()
        vieillir(gd)
    dehors = os.path.join(base, "dehors_du_projet")
    fichier(os.path.join(dehors, "precieux.bin"))
    return P, W, dehors


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--dossier", default=os.path.join(tempfile.gettempdir(), "essai_sante_studio"), help="dossier d'essai (vidé au départ)")
    a = ap.parse_args()
    base = os.path.abspath(a.dossier)
    print("Préparation :", base)
    P, W, dehors = preparer(base)
    sante = os.path.join(P, ".studio", "sante")
    cfg = {"projets": [P], "depots": [P], "builds": [os.path.join(P, "Builds")], "temporaires": [(os.path.join(P, ".studio"), r"\.tmp$")],
           "corbeille": False, "seuil_go": 30, "min_go": 0.001, "langue": "fr",
           "caches_partages": False}   # JAMAIS les caches réels de la machine (DDC partagé d'Unreal…) dans un essai
    vrais = S.disques(P)
    verifie(any(d["projet"] for d in vrais), f"disques : {len(vrais)} disque(s) fixe(s), celui du projet repéré")
    verifie(all({"lettre", "nom", "total_go", "libre_go", "libre_pct", "temp_c"} <= set(d) for d in vrais), "disques : lettre, nom, total, libre, %, température")
    faux = [dict(d, libre_go=2.0, libre_pct=1) for d in vrais]   # FAUX DISQUES PRESQUE PLEINS (le projet peut passer par un lien vers un autre disque)

    print("1) disque presque plein : proposition, rien n'est effacé")
    m = S.Menage(sante, cfg)
    res = m.passer(faux, False, {}, synchrone=True)
    verifie(res["statut"] == "propose", f"statut « propose » ({res['statut']})")
    prop = json.load(open(os.path.join(sante, "menage_propose.json"), encoding="utf-8"))
    chemins = {os.path.normcase(os.path.realpath(l["chemin"])): l for l in prop["lignes"] if l["type"] != "corbeille"}

    def a(p):
        return os.path.normcase(os.path.realpath(p)) in chemins
    verifie(a(os.path.join(P, "DerivedDataCache")) and a(os.path.join(P, "Intermediate")) and a(os.path.join(P, "Saved", "Logs")), "caches du moteur proposés")
    verifie(a(os.path.join(P, "Builds", "b1")) and a(os.path.join(P, "Builds", "b2")), "vieilles builds b1, b2 proposées")
    verifie(not a(os.path.join(P, "Builds", "b3")) and not a(os.path.join(P, "Builds", "b4")), "les 2 dernières builds (b3, b4) gardées")
    verifie(a(os.path.join(W, "wt_fusion")), "worktree fusionné et propre proposé")
    verifie(not a(os.path.join(W, "wt_libre")), "worktree non fusionné jamais proposé")
    verifie(not a(os.path.join(W, "wt_sale")), "worktree sale jamais proposé")
    verifie(a(os.path.join(P, ".studio")), "fichiers temporaires de l'outil proposés")
    verifie(all(l.get("taille_go") is not None and l.get("risque") for l in prop["lignes"]), "chaque ligne : chemin, taille, risque")
    reel = os.path.normcase(os.path.realpath(base))
    verifie(all(l["type"] == "corbeille" or os.path.normcase(os.path.realpath(l["chemin"])).startswith(reel) for l in prop["lignes"]),
            "aucune ligne hors du dossier d'essai (aucun vrai cache de la machine)")
    verifie(not any(l["type"] == "corbeille" for l in prop["lignes"]), "corbeille absente (non permise dans l'essai)")
    verifie(os.path.isdir(os.path.join(P, "DerivedDataCache")) and os.path.isdir(os.path.join(W, "wt_fusion")) and os.path.isdir(os.path.join(P, "Builds", "b1")),
            "RIEN n'a été effacé par la proposition")
    dec = m.decision()
    verifie(bool(dec) and dec["id"] == prop["id"] and [c["id"] for c in dec["choix"]] == ["faire", "plus_tard"] and dec["choix"][0]["libelle"] == "Faire ce ménage",
            "décision sous la cloche : « Faire ce ménage » / « Pas maintenant »")
    verifie(bool(dec) and dec.get("question") and dec.get("options") and dec.get("lignes"), "décision lisible par les deux studios (question/options/lignes)")

    # la décision arrive dans decisions_studio.json par l'alimentation du skill
    import studio_etat
    st = studio_etat.Studio(P)
    st.menage_srv = m
    st.decisions_studio([], [])
    ds = json.load(open(os.path.join(P, ".studio", "decisions_studio.json"), encoding="utf-8"))
    verifie(any(x.get("id") == prop["id"] for x in ds), "décision écrite dans decisions_studio.json (cloche)")

    print("2) moteur ouvert : caches du moteur jamais proposés")
    m2 = S.Menage(os.path.join(base, "sante_moteur"), cfg)
    m2.passer(faux, True, {}, synchrone=True)
    p2 = json.load(open(os.path.join(base, "sante_moteur", "menage_propose.json"), encoding="utf-8"))
    verifie(not any(l["type"] == "cache" for l in p2["lignes"]), "aucun cache du moteur pendant que le moteur est ouvert")

    print("3) « Faire ce ménage » : seulement le permis, journal écrit")
    prop["lignes"].append({"n": 99, "type": "cache", "chemin": dehors, "octets": 2 * MO, "taille_go": 0.0, "risque": "faible", "detail": "glissé"})
    prop["lignes"].append({"n": 100, "type": "build", "chemin": P, "octets": 2 * MO, "taille_go": 0.0, "risque": "faible", "detail": "glissé"})
    json.dump(prop, open(os.path.join(sante, "menage_propose.json"), "w", encoding="utf-8"))
    res = m.passer(faux, False, {prop["id"]: {"choix": "faire"}}, synchrone=True)
    verifie(not os.path.exists(os.path.join(P, "DerivedDataCache")), "DerivedDataCache effacé")
    verifie(not os.path.exists(os.path.join(P, "Builds", "b1")) and os.path.isdir(os.path.join(P, "Builds", "b4")), "b1 effacée, b4 gardée")
    verifie(not os.path.exists(os.path.join(W, "wt_fusion")) and "f1" in git(P, "branch", "--format=%(refname:short)").split(), "worktree fusionné retiré, branche f1 gardée")
    verifie(os.path.isdir(os.path.join(W, "wt_libre")) and os.path.isfile(os.path.join(W, "wt_sale", "brouillon.txt")), "worktrees non fusionné et sale intacts")
    verifie(not os.path.exists(os.path.join(P, ".studio", "vieux.tmp")), "fichier temporaire effacé")
    verifie(os.path.isfile(os.path.join(dehors, "precieux.bin")), "dossier hors du projet glissé dans la proposition : intact")
    verifie(os.path.isfile(os.path.join(P, "Jeu.uproject")) and os.path.isfile(os.path.join(P, "Content", "carte.umap")), "le projet lui-même : intact")
    j = json.load(open(os.path.join(sante, "menage_journal.json"), encoding="utf-8"))
    verifie(any(x["chemin"] == dehors and not x["efface"] and "refus" in x["resultat"] for x in j), "journal : la ligne hors du projet est refusée")
    for x in j:
        print("      journal :", x["type"], x["chemin"], "->", x["resultat"])
    verifie(sum(1 for x in j if x["efface"]) >= 5, f"journal : {sum(1 for x in j if x['efface'])} effacement(s) notés")
    verifie(m.decision() is None, "plus de décision ouverte après le ménage")

    print("4) « Pas maintenant » : report de 12 h")
    open(os.path.join(sante, "analyser.demande"), "w").write("essai")
    fichier(os.path.join(P, "DerivedDataCache", "c.ddp"), 3 * MO)
    m.passer(faux, False, {}, synchrone=True)
    p3 = json.load(open(os.path.join(sante, "menage_propose.json"), encoding="utf-8"))
    verifie(p3["statut"] == "ouverte" and p3["id"] != prop["id"], "nouvelle analyse demandée : nouvelle proposition")
    res = m.passer(faux, False, {p3["id"]: {"choix": "plus_tard"}}, synchrone=True)
    verifie(res["statut"] == "reporte" and os.path.isdir(os.path.join(P, "DerivedDataCache")), "reportée, rien d'effacé")

    print("5) températures")
    tf = os.path.join(base, "temperatures.json")
    json.dump({"maj": "x", "cpu": {"c": 27.85, "source": "acpi"}, "disques": {"C": {"temp": 38}}}, open(tf, "w"))
    if os.name == "nt":
        t = S.temperatures(sante, fichier=tf)
        verifie(t["etat"] == "active" and t["disques"].get("C") == 38, "disque C : 38 °C lu")
        verifie(t["cpu_c"] is None and "figée" in (t["cpu_note"] or ""), "processeur : valeur ACPI figée dite non disponible")
        json.dump({"maj": "x", "cpu": {"c": 55.0, "source": "LibreHardwareMonitor"}, "disques": {}}, open(tf, "w"))
        t = S.temperatures(sante, fichier=tf)
        verifie(t["cpu_c"] == 55 and t["cpu_source"] == "LibreHardwareMonitor", "processeur : capteur fiable lu (55 °C)")
        os.utime(tf, (VIEUX, VIEUX))
        json.dump({"etat": "refuse", "t": int(time.time())}, open(os.path.join(sante, "temperatures_activation.json"), "w"))
        t = S.temperatures(sante, fichier=tf)
        verifie(t["etat"] == "refuse", "activation refusée : état « refuse »")
        json.dump({"etat": "echec", "cause": "windows_refuse", "etape": "tache", "message": "Accès refusé"},
                  open(os.path.join(sante, "temperatures_activation.json"), "w", encoding="utf-8"))
        t = S.temperatures(sante, fichier=tf)
        j = S.jauges(temps=t)
        verifie(t["etat"] == "pas_active" and j["cause"] == "Windows a refusé" and "Accès refusé" in j["message"] and j["activer"],
                "échec : cause en clair (« Windows a refusé ») sur la fiche, bouton « Activer » reproposé")
        os.remove(os.path.join(sante, "temperatures_activation.json"))
        t = S.temperatures(sante, fichier=os.path.join(base, "absent.json"))
        verifie(t["etat"] == "pas_active" and t["activable"], "pas activé : bouton « Activer » proposé")
        try:                                                  # script absent : échec écrit en clair, rien n'est lancé
            S.lancer_activation("installer", sante, os.path.join(base, "absent.ps1"))
            verifie(False, "script absent : refus attendu")
        except FileNotFoundError:
            a = json.load(open(os.path.join(sante, "temperatures_activation.json"), encoding="utf-8"))
            verifie(a["etat"] == "echec" and a["cause"] == "script_absent", "script absent : « script d'activation absent » écrit")
            os.remove(os.path.join(sante, "temperatures_activation.json"))
        # script réel en essai à sec : sans élévation, rien de modifié, tâche validée par le planificateur sans être créée
        jr = os.path.join(base, "journal.json")
        r = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
                            os.path.join(ICI, "temperatures_windows.ps1"), "-Action", "Installer", "-Journal", jr, "-EssaiASec"],
                           capture_output=True, text=True, timeout=120, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        jj = json.load(open(jr, encoding="utf-8-sig")) if os.path.exists(jr) else {}
        verifie(r.returncode == 0 and jj.get("ok") is True and jj.get("etape") == "fini",
                f"temperatures_windows.ps1 -EssaiASec : relevé et tâche valides (code {r.returncode}, {jj.get('message') or r.stderr[-200:]})")
    else:
        t = S.temperatures(sante)
        verifie(t["etat"] in ("active", "non_disponible"), f"hors Windows : {t['etat']} sans planter")

    print("6) route /api/sante : jamais d'élévation sans clic, jamais à distance")
    import serveur_studio as SV
    SV.Etat.projet, SV.Etat.studio = P, os.path.join(P, ".studio")
    for corps, code in (({"action": "activer_temperatures"}, 400), ({"action": "activer_temperatures", "via": "clic", "_local": False}, 403),
                        ({"action": "rien"}, 400)):
        try:
            SV.route_sante(corps)
            verifie(False, f"refus attendu pour {corps}")
        except SV.Refus as e:
            verifie(e.code == code, f"refus {e.code} pour {corps}")
    r = SV.route_sante({"action": "analyser_menage"})
    verifie(r.get("ok") and os.path.exists(os.path.join(sante, "analyser.demande")), "analyser_menage : demande d'analyse déposée")

    print()
    print("ESSAI SANTÉ : " + ("VERT" if not ERREURS else f"ROUGE ({len(ERREURS)} échec(s))"))
    return 1 if ERREURS else 0


if __name__ == "__main__":
    sys.exit(main())
