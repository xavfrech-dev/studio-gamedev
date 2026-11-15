# -*- coding: utf-8 -*-
"""Essai du questionnaire adaptatif (retour d'un utilisateur, 15/11 : « quand on a répondu à une question, les suivantes
doivent être orientées et garder en mémoire ce qu'on a répondu, pour ne pas avoir de répétition »).

Vérifie, sans navigateur ni serveur lancé :
- données : questions.fr.json et questions.en.json portent le même bloc « adaptation » (règles, mots du pitch, rappel)
  et les mêmes variantes ; le générateur ne trouve aucune erreur (clés, valeurs, opérateurs) ;
- déductions : un pitch « jeu de cartes 2D sur navigateur avec Phaser » tranche genre, 2D, plateforme, moteur, puis les
  règles tranchent la caméra ; un pitch ambigu (deux genres) ne tranche rien ; une réponse de l'utilisateur n'est jamais
  remplacée ; une déduction dont la cause change disparaît ;
- pas de répétition : questionnaire joué de bout en bout (rapide, complet, plusieurs pitchs), aucune question posée deux
  fois, aucune question déjà déduite posée, la caméra n'est pas demandée pour un jeu de cartes ; mêmes questions qu'on
  avance pas à pas (page) ou qu'on reparte à chaque fois du début (repli conversation) ;
- reformulation (titre selon les choix) et rappel « Déjà acquis » ;
- reprise : outils/questionnaire.py interrompu puis relancé reprend où il en était, sans répétition ;
- serveur : /api/questionnaire accepte via regle / pitch et n'efface qu'une réponse déduite ;
- page : le bloc ADAPTATION de studio.html, exécuté sous Node, rend exactement les mêmes résultats que studio/adaptation.py ;
  le questionnaire de la page s'en sert (suivante, déductions, titre, rappel).

Usage : python -I -B essai_questionnaire.py [--garder]      code 0 = tout vert
"""
import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile

for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
sys.dont_write_bytecode = True
ICI = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(ICI)
sys.path.insert(0, STUDIO)
sys.path.insert(0, ICI)
import adaptation  # noqa: E402
import construire_questions  # noqa: E402

RES = {"ok": 0, "echec": 0}


def ok(cond, msg):
    RES["ok" if cond else "echec"] += 1
    print(("  ok   " if cond else "  ÉCHEC ") + msg)
    return cond


def lire_qf(lg):
    with open(os.path.join(STUDIO, "questions.%s.json" % lg), encoding="utf-8") as f:
        return json.load(f)


PITCHS = {
    "cartes": "Un jeu de cartes en 2D sur navigateur, fait avec Phaser : on bâtit un deck de sorts.",
    "tir": "Un jeu de tir nerveux sur PC avec Unreal, en solo, dans une station spatiale.",
    "fps": "Un FPS nerveux sur PC avec Unreal.",
    "ambigu": "Un roguelike de survie, on verra pour le reste.",
    "roblox": "Un obby sur Roblox avec des amis.",
    "vide": "Je ne sais pas encore.",
}


def rep_utilisateur(v):
    return {"valeur": v, "source": "utilisateur", "via": "clic", "t": "2026-11-15T20:00:00"}


def reponse_bot(qf, q, rep, pitch, mode):
    """Ce qu'un joueur pressé répond : la ★ visible, sinon la première carte ; un texte bref ; le pitch donné."""
    if q["id"] == "accueil.mode":
        return mode
    if q["id"] == "vision.pitch":
        return pitch
    t = q.get("type")
    if t in ("choix", "multi"):
        vis = [c["id"] for c in q.get("choix", []) if adaptation.cond(c.get("si"), rep)]
        r = q.get("recommande")
        if t == "multi":
            l = [x for x in (r if isinstance(r, list) else [r] if r else []) if x in vis]
            return l or vis[:1]
        return r if r in vis else vis[0]
    if t == "curseur":
        return q.get("defaut", q.get("min", 0))
    if t == "personnage":
        return "choisi"
    return "essai"


def jouer(qf, pitch, mode, pas_a_pas=True, arret=None, rq=None):
    """Joue le questionnaire. pas_a_pas : comme la page (suivante depuis la question courante) ; sinon comme le
    repli conversation (première question non tranchée à chaque fois). Rend (questions posées, rq)."""
    rq = rq if rq is not None else {"version": 1, "etat": "en_cours", "reponses": {}}
    posees, prec = [], None
    for _ in range(200):
        m = adaptation.mode_de(rq)
        q = adaptation.suivante(qf, rq["reponses"], m, (), prec if pas_a_pas else None)
        if q is None and prec is None:
            break
        if q is None or q["id"] == "fin.valider":
            break
        if arret is not None and len(posees) >= arret:
            break
        posees.append(q["id"])
        v = reponse_bot(qf, q, rq["reponses"], pitch, mode)
        rq["reponses"][q["id"]] = rep_utilisateur(v)
        if q["id"] == "accueil.mode":
            rq["mode"] = v
        adaptation.appliquer(qf, rq)
        prec = q["id"]
    return posees, rq


def essai_donnees():
    print("Données et générateur")
    fr, en = lire_qf("fr"), lire_qf("en")
    ok(not construire_questions.verifier(), "construire_questions.verifier() : aucune erreur (" + "; ".join(construire_questions.verifier()[:3]) + ")")
    ok("adaptation" in fr and "adaptation" in en, "bloc « adaptation » dans les deux fichiers de questions")
    ok([r["id"] for r in fr["adaptation"]["regles"]] == [r["id"] for r in en["adaptation"]["regles"]]
       and [r["fixe"] for r in fr["adaptation"]["regles"]] == [r["fixe"] for r in en["adaptation"]["regles"]],
       "mêmes règles en FR et en EN (%d)" % len(fr["adaptation"]["regles"]))
    ok(fr["adaptation"]["pitch"] == en["adaptation"]["pitch"], "mêmes mots du pitch en FR et en EN (%d)" % len(fr["adaptation"]["pitch"]))
    vfr = {q["id"]: [v["si"] for v in q.get("variantes", [])] for q in fr["questions"]}
    ven = {q["id"]: [v["si"] for v in q.get("variantes", [])] for q in en["questions"]}
    ok(vfr == ven and sum(map(len, vfr.values())) >= 15, "mêmes variantes (conditions) en FR et en EN (%d)" % sum(map(len, vfr.values())))
    gen = {lg: construire_questions.construire(lg) for lg in ("fr", "en")}
    ok(gen["fr"] == fr and gen["en"] == en, "questions.*.json à jour avec construire_questions.py")


def essai_deductions(qf):
    print("Déductions (règles et pitch)")
    rep = {"vision.pitch": rep_utilisateur(PITCHS["cartes"])}
    d = adaptation.deduire(qf, rep)
    v = {k: r["valeur"] for k, r in d.items()}
    ok(v.get("genre.principal") == "cartes" and v.get("camera.dimension") == "2d" and v.get("plateforme.cibles") == ["web"]
       and v.get("moteur.nom") == "phaser", "pitch cartes : genre, 2D, navigateur, Phaser déduits (%s)" % v)
    ok(v.get("camera.vue") == "ecran_fixe" and v.get("camera.controle") == "guidee" and v.get("plateforme.machine") == "petite",
       "puis les règles : écran fixe, caméra guidée, petite config")
    ok(all(r["source"] == "deduit" and r["via"] in ("pitch", "regle") and r["raison"] for r in d.values()),
       "chaque déduction : source deduit, via pitch ou regle, une raison")
    d2 = adaptation.deduire(qf, {"vision.pitch": rep_utilisateur(PITCHS["ambigu"])})
    ok("genre.principal" not in d2, "pitch ambigu (roguelike et survie) : le genre n'est pas tranché")
    d3 = adaptation.deduire(qf, {"vision.pitch": rep_utilisateur(PITCHS["vide"])})
    ok(d3 == {}, "pitch sans indice : rien de déduit")
    rep4 = {"genre.principal": rep_utilisateur("cartes"), "camera.dimension": rep_utilisateur("3d")}
    d4 = adaptation.deduire(qf, rep4)
    ok("camera.dimension" not in d4 and "camera.vue" not in d4 and d4.get("camera.controle", {}).get("valeur") == "guidee",
       "réponse de l'utilisateur (3D) jamais remplacée ; l'écran fixe (2D) n'est pas déduit")
    rq = {"reponses": {"genre.principal": rep_utilisateur("cartes")}}
    adaptation.appliquer(qf, rq)
    ok(rq["reponses"]["camera.dimension"]["valeur"] == "2d", "genre cartes : 2D écrit dans les réponses")
    rq["reponses"]["genre.principal"] = rep_utilisateur("rpg")
    ecr, ret = adaptation.appliquer(qf, rq)
    ok(set(ret) >= {"camera.dimension", "camera.vue", "camera.controle"} and "camera.dimension" not in rq["reponses"],
       "le genre change (RPG) : les déductions du jeu de cartes disparaissent (%s)" % sorted(ret))
    d5 = adaptation.deduire(qf, {"moteur.nom": rep_utilisateur("roblox")})
    ok(d5.get("plateforme.cibles", {}).get("valeur") == ["roblox"] and d5.get("moteur.langage", {}).get("valeur") == "luau",
       "Roblox : plateforme et langage déduits (règle R1)")
    d6 = adaptation.deduire(qf, {"ia.autorises": rep_utilisateur(["code"])})
    ok(d6.get("budget.generation_par_jalon", {}).get("valeur") == "aucun", "IA pour le code seulement : pas de budget de génération (R10)")
    d7 = adaptation.deduire(qf, {"vision.pitch": rep_utilisateur(PITCHS["cartes"])}, exclure=["moteur.nom"])
    ok("moteur.nom" not in d7, "une clé « fixes » de deductions.json n'est jamais déduite")


def essai_repetition(qf):
    print("Pas de répétition, saut des questions déduites")
    for nom in ("cartes", "tir", "ambigu", "roblox", "vide"):
        for mode in ("rapide", "complet"):
            posees, rq = jouer(qf, PITCHS[nom], mode)
            deduites = {k for k, r in rq["reponses"].items() if r.get("source") == "deduit"}
            ok(len(posees) == len(set(posees)), "%s / %s : %d questions, aucune posée deux fois" % (nom, mode, len(posees)))
            ok(not (deduites & set(posees)), "%s / %s : aucune des %d déductions n'a été demandée" % (nom, mode, len(deduites)))
            restante = adaptation.suivante(qf, rq["reponses"], mode, ())
            ok(restante is not None and restante["id"] == "fin.valider", "%s / %s : on finit sur le récapitulatif" % (nom, mode))
            conv, _ = jouer(qf, PITCHS[nom], mode, pas_a_pas=False)
            ok(conv == posees, "%s / %s : mêmes questions pas à pas (page) et en reprenant du début (conversation)" % (nom, mode))
    posees, rq = jouer(qf, PITCHS["cartes"], "complet")
    ok(not {"camera.dimension", "camera.vue", "camera.controle", "genre.principal", "moteur.nom", "plateforme.cibles"} & set(posees),
       "jeu de cartes (complet) : ni genre, ni 2D/3D, ni caméra, ni plateforme, ni moteur redemandés")
    posees, rq = jouer(qf, PITCHS["tir"], "complet")
    ok("camera.vue" in posees and "camera.dimension" not in posees and "gameplay.verbe" not in posees,
       "jeu de tir : la 3D et le verbe sont déduits, la caméra (1re ou 3e personne) reste posée")
    d = adaptation.deduire(qf, {"vision.pitch": rep_utilisateur(PITCHS["fps"])})
    ok(d.get("camera.vue", {}).get("valeur") == "premiere_personne" and d.get("genre.principal", {}).get("valeur") == "fps",
       "« FPS » dans le pitch : tir à la 1re personne, plus de question sur la caméra")
    # passer (« à confirmer ») puis repasser en mode complet : les « à confirmer » reviennent, le reste non
    rq = {"mode": "rapide", "reponses": {"genre.principal": dict(rep_utilisateur("rpg"), source="a_confirmer", via="passer"),
                                         "accueil.nom": rep_utilisateur("Alex")}}
    q = adaptation.suivante(qf, rq["reponses"], "complet", (), None, revoir=True)
    ok(q is not None and q["id"] != "accueil.nom", "mode complet depuis le récapitulatif : une réponse donnée n'est pas reposée")
    l = []
    prec = None
    for _ in range(120):
        q = adaptation.suivante(qf, rq["reponses"], "complet", (), prec, revoir=True)
        if not q or q["id"] == "fin.valider":
            break
        l.append(q["id"])
        rq["reponses"][q["id"]] = rep_utilisateur(reponse_bot(qf, q, rq["reponses"], PITCHS["vide"], "complet"))
        adaptation.appliquer(qf, rq)
        prec = q["id"]
    ok("genre.principal" in l and "accueil.nom" not in l and len(l) == len(set(l)),
       "… et la réponse « à confirmer » revient une fois")


def essai_titres(qf):
    print("Reformulation et rappel des acquis")
    q = adaptation.question(qf, "camera.vue")
    base = q["titre"]
    t3 = adaptation.titre(qf, q, {"camera.dimension": rep_utilisateur("3d")})
    t2 = adaptation.titre(qf, q, {"camera.dimension": rep_utilisateur("2d")})
    ok(t3 != base and "3D" in t3, "camera.vue en 3D : « %s »" % t3)
    ok(t2 != base and t2 != t3 and "2D" in t2, "camera.vue en 2D : « %s »" % t2)
    tf = adaptation.titre(qf, q, {"genre.principal": rep_utilisateur("fps"), "camera.dimension": rep_utilisateur("3d")})
    ok("tir" in tf.lower(), "camera.vue pour un jeu de tir : « %s »" % tf)
    qm = adaptation.question(qf, "moteur.nom")
    tm = adaptation.titre(qf, qm, {"camera.dimension": rep_utilisateur("2d"), "plateforme.cibles": rep_utilisateur(["web"])})
    ok("2D" in tm and "Navigateur" in tm, "moteur.nom : « %s »" % tm)
    ok(adaptation.titre(qf, qm, {}) == qm["titre"], "sans réponse, le titre d'origine")
    qv = adaptation.question(qf, "gameplay.verbe")
    tv = adaptation.titre(qf, qv, {"genre.principal": rep_utilisateur("survie")})
    ok("Survie" in tv, "gameplay.verbe : « %s »" % tv)
    _, rq = jouer(qf, PITCHS["cartes"], "rapide", arret=12)
    a = adaptation.acquis(qf, rq["reponses"])
    vals = [x["valeur"] for x in a]
    ok(any("cartes" in v for v in vals) and "2D" in vals and 1 <= len(a) <= 6, "rappel « Déjà acquis » : %s" % " · ".join(vals))
    ok(any(x["source"] == "deduit" and x["raison"] for x in a), "le rappel marque les déductions et garde leur raison")
    ok(all(x["cle"] != "genre.principal" for x in adaptation.acquis(qf, rq["reponses"], sauf="genre.principal")),
       "le rappel ne répète pas la question en cours")
    fen = lire_qf("en")
    ten = adaptation.titre(fen, adaptation.question(fen, "camera.vue"), {"camera.dimension": rep_utilisateur("3d")})
    ok(ten.startswith("In 3D"), "EN : « %s »" % ten)


def lancer_cli(*args):
    r = subprocess.run([sys.executable, "-I", "-B", os.path.join(ICI, "questionnaire.py"), *args],
                       capture_output=True, timeout=60)
    return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")


def essai_reprise(qf, tmp):
    print("Reprise (repli conversation, outils/questionnaire.py)")
    projet = os.path.join(tmp, "Mon jeu [v2]")
    os.makedirs(projet)
    attendu, _ = jouer(qf, PITCHS["cartes"], "rapide")
    posees = []
    for tour in range(2):                        # deux « sessions » : le script est relancé de zéro
        rc, out, err = lancer_cli("suivante", "--projet", projet)
        ok(rc == 0, "session %d : suivante (code %d %s)" % (tour + 1, rc, err.strip()[:200]))
        for _ in range(12 if tour == 0 else 60):
            d = json.loads(out)
            if d.get("fin") or d["question"]["id"] == "fin.valider":
                break
            q = d["question"]
            posees.append(q["id"])
            qq = adaptation.question(qf, q["id"])
            fr_ = os.path.join(projet, ".studio", "reponses_questionnaire.json")
            rep = {}
            if os.path.exists(fr_):
                with open(fr_, encoding="utf-8") as f:
                    rep = json.load(f)["reponses"]
            v = reponse_bot(qf, qq, rep, PITCHS["cartes"], "rapide")
            rc, out, err = lancer_cli("repondre", "--projet", projet, "--cle", q["id"], "--valeur", json.dumps(v, ensure_ascii=False), "--json")
            if rc:
                ok(False, "repondre %s (code %d %s)" % (q["id"], rc, err.strip()[:200]))
                break
    ok(posees == attendu, "interrompu après 12 questions puis relancé : mêmes questions qu'en une fois (%d), aucune répétée" % len(posees))
    rc, out, _ = lancer_cli("suivante", "--projet", projet)
    d = json.loads(out)
    ok(rc == 0 and d["question"]["id"] == "fin.valider", "relancé à la fin : il propose le récapitulatif")
    with open(os.path.join(projet, ".studio", "reponses_questionnaire.json"), encoding="utf-8") as f:
        rq = json.load(f)
    ok(rq["reponses"]["camera.vue"]["via"] == "regle" and rq["reponses"]["genre.principal"]["via"] == "pitch",
       "les déductions sont écrites dans reponses_questionnaire.json (via regle / pitch)")
    projet2 = os.path.join(tmp, "p2")
    os.makedirs(os.path.join(projet2, ".studio"))
    with open(os.path.join(projet2, ".studio", "deductions.json"), "w", encoding="utf-8") as f:
        json.dump({"fixes": {"moteur.nom": {"valeur": "godot", "raison": "projet Godot"}}, "recommandes": {"genre.principal": "rpg"}}, f)
    rc, out, _ = lancer_cli("repondre", "--projet", projet2, "--cle", "vision.pitch", "--valeur", PITCHS["cartes"])
    d = json.loads(out)
    ok(rc == 0 and "moteur.nom" not in d["deduites_nouvelles"] and d["deduites_nouvelles"].get("genre.principal") == "cartes",
       "repondre : déductions nouvelles listées, une clé « fixes » de deductions.json respectée")
    rc, out, err = lancer_cli("repondre", "--projet", projet2, "--cle", "inconnue.cle", "--valeur", "x")
    ok(rc == 2, "clé inconnue refusée (code 2)")


def essai_serveur(tmp):
    print("Serveur (/api/questionnaire)")
    import serveur_studio as S
    st = os.path.join(tmp, "srv", ".studio")
    os.makedirs(st)
    S.Etat.studio = st
    S.route_questionnaire({"cle": "genre.principal", "valeur": "cartes", "source": "utilisateur", "via": "clic"})
    S.route_questionnaire({"cle": "camera.dimension", "valeur": "2d", "source": "deduit", "via": "regle", "raison": "plateau"})
    S.route_questionnaire({"cle": "moteur.nom", "valeur": "phaser", "source": "deduit", "via": "pitch", "raison": "pitch"})
    with open(os.path.join(st, "reponses_questionnaire.json"), encoding="utf-8") as f:
        r = json.load(f)["reponses"]
    ok(r["camera.dimension"]["via"] == "regle" and r["moteur.nom"]["via"] == "pitch", "via regle et pitch acceptés")
    S.route_questionnaire({"cle": "camera.dimension", "effacer": True})
    S.route_questionnaire({"cle": "genre.principal", "effacer": True})
    with open(os.path.join(st, "reponses_questionnaire.json"), encoding="utf-8") as f:
        r = json.load(f)["reponses"]
    ok("camera.dimension" not in r and "genre.principal" in r, "effacer : retire la déduction, jamais la réponse de l'utilisateur")


def essai_page(qf, tmp):
    print("Page : bloc ADAPTATION de studio.html sous Node, comparé au Python")
    with open(os.path.join(STUDIO, "studio.html"), encoding="utf-8") as f:
        page = f.read()
    a, b = page.find("// ADAPTATION debut"), page.find("// ADAPTATION fin")
    if not ok(a >= 0 and b > a, "bloc ADAPTATION présent"):
        return
    quest = page[page.find("const Quest = (() => {"):]
    ok("Adaptation.suivante(QF, R(), mode(), fixes()" in quest and "suivreDeductions()" in quest
       and "Adaptation.titre(QF, q, R())" in quest and "acquisHtml(q)" in quest,
       "le questionnaire de la page s'en sert : prochaine question, déductions, titre reformulé, rappel")
    ok("l.find(q => !(q.id in R()))" not in quest, "plus de prochaine question tirée sans regarder les déductions")
    # scénarios joués en Python, rejoués par le JS
    cas = []
    for nom in ("cartes", "tir", "ambigu", "roblox"):
        for mode in ("rapide", "complet"):
            posees, rq = jouer(qf, PITCHS[nom], mode)
            cas.append({"nom": "%s/%s" % (nom, mode), "pitch": PITCHS[nom], "mode": mode, "posees": posees,
                        "reponses": {k: {kk: vv for kk, vv in v.items() if kk != "t"} for k, v in rq["reponses"].items()}})
    tests_deduire = [{"vision.pitch": rep_utilisateur(p)} for p in PITCHS.values()] + [
        {"genre.principal": rep_utilisateur("cartes"), "camera.dimension": rep_utilisateur("3d")},
        {"moteur.nom": rep_utilisateur("roblox")}, {"ia.autorises": rep_utilisateur(["code"])},
        {"plateforme.cibles": rep_utilisateur(["mobile"])}, {"plateforme.cibles": rep_utilisateur(["mobile", "pc"])},
        {"ia.images": rep_utilisateur("non"), "ia.son": rep_utilisateur("non")}]
    titres = []
    for r in tests_deduire + [c["reponses"] for c in cas]:
        for q in qf["questions"]:
            if q.get("variantes"):
                titres.append([q["id"], r])
    attendu = {
        "deduire": [adaptation.deduire(qf, r) for r in tests_deduire],
        "titres": [adaptation.titre(qf, adaptation.question(qf, i), r) for i, r in titres],
        "acquis": [adaptation.acquis(qf, c["reponses"]) for c in cas],
    }
    script = r"""
const fs = require('fs');
const page = fs.readFileSync(process.argv[2], 'utf8');
const a = page.indexOf('// ADAPTATION debut'), b = page.indexOf('// ADAPTATION fin');
const Adaptation = new Function(page.slice(a, b) + '; return Adaptation;')();
const ent = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const QF = ent.qf, bot = ent.bot;
function jouer(c, pasAPas) {
  const rq = { reponses: {} }, posees = []; let prec = null;
  for (let i = 0; i < 200; i++) {
    const m = rq.mode || 'rapide';
    const q = Adaptation.suivante(QF, rq.reponses, m, [], pasAPas ? prec : null, false);
    if (!q || q.id === 'fin.valider') break;
    posees.push(q.id);
    const v = bot(q, rq.reponses, c);
    rq.reponses[q.id] = { valeur: v, source: 'utilisateur', via: 'clic' };
    if (q.id === 'accueil.mode') rq.mode = v;
    const { ecrire, retirer } = Adaptation.difference(QF, rq.reponses, []);
    for (const k of retirer) delete rq.reponses[k];
    Object.assign(rq.reponses, ecrire);
    prec = q.id;
  }
  return { posees, reponses: rq.reponses };
}
const sortie = {
  deduire: ent.deduire.map(r => Adaptation.deduire(QF, r, [])),
  titres: ent.titres.map(([id, r]) => Adaptation.titre(QF, QF.questions.find(q => q.id === id), r)),
  acquis: ent.cas.map(c => Adaptation.acquis(QF, c.reponses)),
  jeux: ent.cas.map(c => { const p = jouer(c, true), s = jouer(c, false); return { posees: p.posees, conv: s.posees, reponses: p.reponses }; }),
};
console.log(JSON.stringify(sortie));
"""
    # le joueur pressé, en JS (mêmes choix que reponse_bot)
    bot_js = """(q, rep, c) => {
      if (q.id === 'accueil.mode') return c.mode;
      if (q.id === 'vision.pitch') return c.pitch;
      const t = q.type;
      if (t === 'choix' || t === 'multi') {
        const vis = (q.choix || []).filter(x => Adaptation.cond(x.si, rep)).map(x => x.id), r = q.recommande;
        if (t === 'multi') { const l = (Array.isArray(r) ? r : r ? [r] : []).filter(x => vis.includes(x)); return l.length ? l : vis.slice(0, 1); }
        return vis.includes(r) ? r : vis[0];
      }
      if (t === 'curseur') return q.defaut !== undefined ? q.defaut : (q.min || 0);
      if (t === 'personnage') return 'choisi';
      return 'essai';
    }"""
    script = script.replace("const QF = ent.qf, bot = ent.bot;", "const QF = ent.qf, bot = " + bot_js + ";")
    sj = os.path.join(tmp, "essai_adaptation.js")
    ej = os.path.join(tmp, "entree.json")
    with open(sj, "w", encoding="utf-8") as f:
        f.write(script)
    with open(ej, "w", encoding="utf-8") as f:
        json.dump({"qf": qf, "deduire": tests_deduire, "titres": titres, "cas": cas}, f, ensure_ascii=False)
    try:
        r = subprocess.run(["node", sj, os.path.join(STUDIO, "studio.html"), ej], capture_output=True, timeout=120)
    except FileNotFoundError:
        ok(False, "Node introuvable : la comparaison page / Python ne peut pas tourner")
        return
    if not ok(r.returncode == 0, "bloc ADAPTATION exécuté sous Node (%s)" % r.stderr.decode("utf-8", "replace").strip()[:300]):
        return
    js = json.loads(r.stdout.decode("utf-8"))
    ok(js["deduire"] == attendu["deduire"], "déductions identiques page / Python (%d cas)" % len(tests_deduire))
    ok(js["titres"] == attendu["titres"], "titres reformulés identiques page / Python (%d cas)" % len(titres))
    ok(js["acquis"] == attendu["acquis"], "rappels « Déjà acquis » identiques page / Python (%d cas)" % len(cas))
    for c, j in zip(cas, js["jeux"]):
        ok(j["posees"] == c["posees"] and j["conv"] == c["posees"] and j["reponses"] == c["reponses"],
           "%s : la page pose les mêmes %d questions et garde les mêmes réponses que le Python" % (c["nom"], len(c["posees"])))
        ok(len(j["posees"]) == len(set(j["posees"])), "%s : aucune répétition côté page" % c["nom"])


def main(argv=None):
    ap = argparse.ArgumentParser(description="Essai du questionnaire adaptatif (code 0 = tout vert).")
    ap.add_argument("--garder", action="store_true", help="garde le dossier temporaire")
    a = ap.parse_args(argv)
    qf = lire_qf("fr")
    tmp = tempfile.mkdtemp(prefix="essai_questionnaire_")
    try:
        essai_donnees()
        essai_deductions(copy.deepcopy(qf))
        essai_repetition(qf)
        essai_titres(qf)
        essai_reprise(qf, tmp)
        essai_serveur(tmp)
        essai_page(qf, tmp)
    finally:
        if a.garder:
            print("dossier gardé : " + tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    print("questionnaire adaptatif : %d ok, %d échec(s)" % (RES["ok"], RES["echec"]))
    return 0 if RES["echec"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
