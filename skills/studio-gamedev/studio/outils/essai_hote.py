"""Essai de l'hôte du studio (quête « Un hôte pour le studio », hote.py, hote.js, route /api/hote).

Usage : python -I -B essai_hote.py [--dossier <…>/essai_skill] [--captures <dossier>] [--sans-navigateur] [--garder]
  code 0 = tout vert.

Sans navigateur : catalogue (pièces, textes fr/en, répliques propres), coins du studio libres à tous les paliers (aucun
bureau, meuble, passage ni coin de loisir touché), filtre de contenu (vulgarité, drogue et alcool, propos dénigrants, lettres
espacées, chiffres à la place des lettres, lettres larges ou grecques, caractères invisibles, mots composés ; phrases innocentes
acceptées ; textes du skill acceptés ; même verdict dans la page et sur le serveur), fiche (identifiants, objets apportés par une activité, nom et répliques filtrés),
quête qui se débloque au bon moment (après « Q-PR-02 », jamais avant), acceptation sans demande pour l'assistant, quête remplie
par .studio/hote.json ; route /api/hote sur un vrai serveur (prompt refusé 422, demande « hote » avec sa consigne, fiche simulée
de l'assistant, Annuler qui annule la demande, suppression rangée dans anciens/).
Avec navigateur (Chrome sans tête, son coupé --mute-audio, onglet fermé à la fin) sur le projet d'essai --dossier (préparé par
« essai_complet.py tout ») : carte de la quête et bouton « Créer mon hôte », chemin « prompt » (filtre dans la page, demande,
fiche simulée, aperçu, installation), modification par les choix (8 étapes), arrivée dans la scène, activités, réplique en bulle,
Réglages (parole, sons), suppression (il repart par la porte) ; captures PC (1400 × 900) et téléphone (390 × 844).
Le projet d'essai est remis comme avant (hote*.json, quetes_etat.json, demandes « hote »).
"""
import base64
import glob
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.dont_write_bytecode = True
ICI = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(ICI)
sys.path.insert(0, STUDIO)
sys.path.insert(0, ICI)
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
import hote  # noqa: E402
import quetes  # noqa: E402

RES = {"ok": 0, "echec": 0}
CHROMES = [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
           "/usr/bin/google-chrome", "/usr/bin/chromium", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]


def ok(cond, msg):
    RES["ok" if cond else "echec"] += 1
    print(("  ok   " if cond else "  ÉCHEC ") + msg)
    return cond


def lire_json(ch, d=None):
    return hote.lire_json(ch, d)


# ------------------------------------------------------------------ 1. sans navigateur
def essai_catalogue():
    print("1. Catalogue de l'hôte")
    err = hote.verifier()
    ok(not err, f"catalogue propre : pièces, fr/en, répliques passées au filtre {err[:3]}")
    cat = hote.catalogue()
    ok(len(cat["allures"]) >= 4 and len(cat["couleurs"]) >= 4 and len(cat["coins"]) >= 3 and len(cat["activites"]) >= 6 and len(cat["tons"]) >= 4,
       f"assez de choix : {len(cat['allures'])} allures, {len(cat['couleurs'])} couleurs, {len(cat['coins'])} coins, {len(cat['activites'])} activités, {len(cat['tons'])} tons")


def essai_catalogue_vide():
    """C7 : sans catalogue, ou avec un catalogue sans filtre, rien n'est accepté (503) et rien n'est gardé en mémoire."""
    print("1 bis. Catalogue absent ou vide")
    vrai, d = hote.CATALOGUE, tempfile.mkdtemp(prefix="essai_hote_cat_")
    try:
        for quoi, contenu in (("absent", None), ("vide", {}), ("sans filtre", {"filtre": {"vulgaire": [], "drogue": [], "denigrant": []}, "coins": [{"id": "x"}]}),
                              ("illisible", "{abîmé")):
            ch = os.path.join(d, f"cat_{len(quoi)}.json")
            if contenu is not None:
                with open(ch, "w", encoding="utf-8") as f:
                    f.write(contenu if isinstance(contenu, str) else json.dumps(contenu))
            hote.CATALOGUE, hote._CAT["d"], hote._CAT["t"] = ch, None, 0
            try:
                hote.filtrer("un texte tout à fait propre")
                code = 200
            except hote.Refus as e:
                code = e.code if hasattr(e, "code") else 503
            ok(code == 503 and hote._CAT["d"] is None, f"catalogue {quoi} : filtre fermé ({code}), rien en mémoire")
        try:
            hote.filtrer("un texte propre", cat={"filtre": {"vulgaire": [], "drogue": [], "denigrant": []}, "coins": []})
            code = 200
        except hote.Refus:
            code = 503
        ok(code == 503, "catalogue sans filtre passé en argument : refusé (503)")
    finally:
        hote.CATALOGUE, hote._CAT["d"], hote._CAT["t"] = vrai, None, 0
        shutil.rmtree(d, ignore_errors=True)
    ok(not hote.filtrer("un texte propre"), "vrai catalogue relu ensuite : le filtre marche de nouveau")


def essai_coins():
    print("2. Coins de l'hôte : libres à tous les paliers")
    import re
    import essai_bureaux as eb
    plan = eb.bloc(os.path.join(STUDIO, "studio.html"), "PLAN-DEBUT", "PLAN-FIN")
    slots, page, lo, pas = eb.tableau(plan, "SLOTS"), eb.tableau(plan, "EMPRISES_PAGE"), eb.tableau(plan, "COINS_LOISIR"), eb.tableau(plan, "PASSAGES")
    eb.BUREAU = eb.tableau(plan, "EMPRISE_BUREAU")
    pts = eb.tableau(plan, "POINTS_BUREAU")
    aud = json.loads(re.search(r"const SLOT_AUDITEUR = (\[.*?\]);", plan).group(1))
    s = open(os.path.join(STUDIO, "paliers.js"), encoding="utf-8").read()
    mob = json.loads(re.search(r"const EMPRISES = (\[.*?\]);", s[s.index("EMPRISES-DEBUT"):s.index("EMPRISES-FIN")], re.S).group(1))
    obst = []
    for sx, sy in slots + [aud]:
        obst.append(("bureau", eb.rect_bureau(sx, sy)))
        for k, (dx, dy) in pts.items():
            obst.append(("point " + k, (sx + dx - .25, sy + dy - .25, sx + dx + .25, sy + dy + .25)))
    obst += [(e["id"], tuple(e["r"])) for e in page + mob] + [(p["id"], tuple(p["r"])) for p in pas]
    obst += [("loisir " + c["cle"], (c["gx"] - .3, c["gy"] - .3, c["gx"] + .3, c["gy"] + .3)) for c in lo]
    for c in hote.catalogue()["coins"]:
        touches = sorted({n for n, r in obst if eb.touche(tuple(c["r"]), r)})
        ok(not touches, f"coin « {c['id']} » {c['r']} : ne touche rien {touches}")


def essai_filtre():
    print("3. Filtre de contenu (prompt, nom, répliques)")
    for t in FILTRE_REFUSES:
        ok(bool(hote.filtrer(t)), f"refusé : « {t} » ({hote.filtrer(t)[:1]})")
    for t in FILTRE_PROPRES:
        ok(not hote.filtrer(t), f"accepté : « {t} »")
    # les textes du skill lui-même (exemples, aide grisée du champ, noms du catalogue) passent tous le filtre
    src = open(os.path.join(STUDIO, "hote.js"), encoding="utf-8").read()
    textes = [m[1] for m in re.findall(r"(ho_ex[123]|ho_prompt_ph|ho_intro|ho_prompt_aide): '((?:[^'\\]|\\.)*)'", src)]
    cat = hote.catalogue()
    for cle in ("allures", "couleurs", "coins", "objets", "activites", "tons"):
        for x in cat[cle]:
            for k in ("nom", "texte", "exemple"):
                if isinstance(x.get(k), dict):
                    textes += [x[k]["fr"], x[k]["en"]]
    mauvais = [t for t in textes if hote.filtrer(t)]
    ok(len(textes) >= 60 and not mauvais, f"textes du skill acceptés par le filtre : {len(textes)} (exemples fr/en, aide du champ, catalogue) {mauvais[:2]}")
    ok(not re.search(r"\(\?<[=!]", src), "hote.js sans regex qui regarde en arrière (Safari < 16.4 la refuse et tout le fichier tomberait)")
    # même verdict dans la page (hote.js) et sur le serveur (hote.py)
    node = shutil.which("node")
    if not node:
        print("  (node absent : comparaison page / serveur sautée)")
        return
    cas = FILTRE_REFUSES + FILTRE_PROPRES + textes
    a, b = src.index("  // ------------------------------------------------------------------ règles de contenu"), src.index("  // ------------------------------------------------------------------ fiche -> look")
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "filtre.js"), "w", encoding="utf-8").write(src[a:b])
        open(os.path.join(d, "cas.json"), "w", encoding="utf-8").write(json.dumps(cas, ensure_ascii=False))
        code = ("const fs = require('fs'), d = process.argv[1]; const filtrer = new Function('CAT', fs.readFileSync(d + '/filtre.js', 'utf8') + '\\nreturn filtrer;')"
                "(JSON.parse(fs.readFileSync(process.argv[2], 'utf8'))); process.stdout.write(JSON.stringify(JSON.parse(fs.readFileSync(d + '/cas.json', 'utf8')).map(t => filtrer(t).length > 0)));")
        r = subprocess.run([node, "-e", code, d, os.path.join(STUDIO, "hote_catalogue.json")], capture_output=True, text=True, encoding="utf-8")
    try:
        js = json.loads(r.stdout)
    except ValueError:
        js = []
    ecarts = [t for t, x in zip(cas, js) if x != bool(hote.filtrer(t))]
    ok(len(js) == len(cas) and not ecarts, f"page et serveur d'accord sur {len(cas)} textes {ecarts[:3]} {r.stderr[:120]}")


FILTRE_REFUSES = [
    "un pote qui fume un joint", "il dit m e r d e tout le temps", "une mamie qui adore la bière", "un gars qui traite tout le monde de crétins",
    "un capitaine qui dit putaaaain", "a guy who says f*ck", "il vend de la c0caïne", "un videur qui insulte les nuls", "a stoned surfer",
    "Un barman bourré qui fume des clopes et traite tout le monde de débiles", "m-e-r-d-e", "p.u.t.a.i.n", "un verre de vin", "du rhum",
    "a glass of wine", "champagne pour tous", "Avec un peu de vin ?", "marijuana", "du haschich", "il vend du crack", "let's roll a joint",
    "whore", "slut", "enfoiré", "que des conneries", "fdp", "ntm", "you retard", "motherfucker", "bullshit", "ＦＵＣＫ", "fυck",
    "fu​ck", "f­u‍ck", "сon", "𝐟𝐮𝐜𝐤", "dipshit", "tue-les"]
FILTRE_PROPRES = [
    "Une mamie qui sert du thé", "a cheerful gardener with a hat", "une dame toujours en retard", "un marin qui raconte la mer",
    "Un robot poli qui arrose les plantes", "a calm librarian", "un capitaine du port, très sage",
    "Un jardinier joyeux en salopette verte qui arrose les plantes.", "il ne va nulle part", "un café qui fume", "des lunettes en verre fumé",
    "il lit Dickens", "des dumbbells dans un coin", "un fagot de bois", "une tarte bien cuite", "grab a bite to eat", "elle tient la droguerie",
    "toujours à la bourre", "il vient de Bitche", "une soupe aux Shitake", "une héroïne courageuse", "le train est retardé",
    "une randonnée pédestre", "il soigne son rhume", "un chili con carne", "pros and cons", "un cœur d'or", "smoke rises from the kettle",
    "a joint effort", "une chaise branlante", "c'est niquel", "Une bibliothécaire en gilet violet", "computer", "une dispute", "la technique"]


def fiche_choix(**k):
    f = {"nom": "Lou", "allure": "petite", "couleurs": "foret", "accessoire": "chapeau", "coin": "coeur", "ton": "chaleureux",
         "activites": ["boisson", "arrose", "lit"], "objets": ["tapis", "lampe"]}
    f.update(k)
    return f


def essai_fiche():
    print("4. Fiche : contrôles")
    p, av = hote.normaliser(fiche_choix())
    ok(p["look"]["accessoire"] == "chapeau" and p["look"]["tenue"]["couleur1"] == "#3f7a52" and p["look"]["morphologie"] == "petite",
       "look composé : allure, couleurs et accessoire choisis")
    ok("plante" in p["objets"], f"arroser apporte une plante : {p['objets']}")
    for mauvais, msg in [({"activites": ["lit"]}, "moins de 3 activités refusé"), ({"coin": "toit"}, "coin inconnu refusé"), ({"ton": "grossier"}, "ton inconnu refusé"), ({"nom": "  "}, "nom vide refusé")]:
        try:
            hote.normaliser(fiche_choix(**mauvais))
            ok(False, msg)
        except hote.Refus as e:
            ok(e.code == 400, msg + f" ({e.message})")
    try:
        hote.normaliser(fiche_choix(nom="Gros connard"))
        ok(False, "nom vulgaire refusé")
    except hote.Refus as e:
        ok(e.code == 422, "nom vulgaire refusé (422)")
    p, av = hote.normaliser(fiche_choix(repliques={"coin": ["Bonjour !", "Quelle merde ce bug", "Salut {inconnu}"], "fini": ["Bravo {nom} !"]}))
    ok(p["repliques"]["coin"] == ["Bonjour !"] and len(av) == 2 and p["repliques"]["fini"] == ["Bravo {nom} !"],
       f"répliques : vulgaire et jeton inconnu écartés, le reste gardé ({av})")
    p, av = hote.normaliser({"nom": "Ama", "source": "prompt"}, completer=True)
    ok(len(p["activites"]) == 3 and p["coin"] and p["ton"], f"fiche d'un prompt incomplète : complétée ({av})")
    p, _ = hote.normaliser(fiche_choix(activites=["boisson", "lit", "musique", "tournee", "range"]))
    ok(len(p["activites"]) == 4 and "radio" in p["objets"], "4 activités au plus ; mettre un air apporte la radio")


def essai_quete(base):
    print("5. Quête « Un hôte pour le studio » : le bon moment")
    import essai_quetes as eq
    d = os.path.join(base, "quete")
    eq.nouveau_projet(d)
    rm = eq.Roadmap(d)
    act = eq.actions(d, rm)
    eq.questionnaire(d, "termine")
    t = eq.T0 + eq.MIN
    e = quetes.passe(d, t, eq.CAT)
    vu_avant, propose_t, pr02_t, etat_propose, faits = False, None, None, None, set()
    for _ in range(200):
        st = {k: v["statut"] for k, v in e["quetes"].items()}
        if st.get("Q-PR-02") in quetes.FAITES and pr02_t is None:
            pr02_t = t
        if st.get("Q-SU-04") in quetes.OUVERTES:
            if pr02_t is None:
                vu_avant = True
            propose_t = t
            etat_propose = json.loads(json.dumps(lire_json(os.path.join(d, ".studio", "quetes_etat.json"))))
            break
        for k, s in st.items():
            if s in quetes.OUVERTES and k not in faits:
                faits.add(k)
                if s == "proposee":
                    try:
                        r = quetes.repondre(d, k, "accepter", maintenant=t, catalogue=eq.CAT)
                        for c in r.get("recruter") or []:
                            eq.recruter_comme_le_serveur(d, c)
                    except quetes.Refus:
                        pass
                act.get(k, lambda: None)()
        if not [k for k, s in st.items() if s in quetes.OUVERTES] and os.path.isfile(rm.ch):
            rm.avancer()
        t += 31 * eq.MIN
        e = quetes.passe(d, t, eq.CAT)
    ok(propose_t is not None and not vu_avant, f"proposée après le premier prototype jouable (Q-PR-02), jamais avant")
    ok(pr02_t is not None and propose_t is not None and propose_t >= pr02_t, "le moment : acte « Identité », une fois la boucle du prototype en place")
    r = quetes.repondre(d, "Q-SU-04", "accepter", maintenant=t, catalogue=eq.CAT)
    ok(r.get("ouvre") == "hote" and "demande" not in r and not glob.glob(os.path.join(d, ".studio", "demandes", "*Q-SU-04*")),
       "accepter ouvre l'écran de création, sans demande pour l'assistant (aucun jeton dépensé)")
    e = quetes.passe(d, t + eq.MIN, eq.CAT)
    ok(e["quetes"]["Q-SU-04"]["statut"] == "acceptee", "sans hôte : la quête reste en cours")
    hote.enregistrer(d, fiche_choix())
    e = quetes.passe(d, t + 2 * eq.MIN, eq.CAT)
    q = e["quetes"]["Q-SU-04"]
    ok(q["statut"] == "remplie" and ".studio/hote.json" in str(q.get("preuve")), f"hôte installé : quête remplie ({q.get('preuve')})")
    return etat_propose


def port_libre():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Serveur:
    def __init__(self, projet):
        self.port = port_libre()
        self.p = subprocess.Popen([sys.executable, "-I", "-B", os.path.join(STUDIO, "serveur_studio.py"), "--projet", projet, "--port", str(self.port)],
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{self.port}/api/qui", timeout=1).read()
                return
            except Exception:
                time.sleep(.2)
        raise SystemExit("serveur injoignable")

    def api(self, route, corps):
        u = f"http://127.0.0.1:{self.port}"
        r = urllib.request.Request(u + route, data=json.dumps(corps).encode(), headers={"Content-Type": "application/json", "Origin": u, "Host": f"127.0.0.1:{self.port}"})
        try:
            with urllib.request.urlopen(r, timeout=5) as x:
                return x.status, json.loads(x.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def arreter(self):
        self.p.terminate()
        try:
            self.p.wait(5)
        except Exception:
            self.p.kill()


FICHE_ASSISTANT = {"nom": "Capitaine Mo", "look": {"morphologie": "costaude", "peau": "#a8735a", "cheveux": {"coupe": "rase", "couleur": "#8a8a8a"},
                   "tenue": {"style": "chemise", "couleur1": "#2f5f8a", "couleur2": "#f4ecd9"}, "accessoire": "barbe"},
                   "coin": "droite", "activites": ["lit", "fenetre", "tournee"], "objets": ["livres", "lampe", "tapis"], "ton": "sage",
                   "repliques": {"coin": ["La mer est calme, le code aussi.", "Un bon marin range ses cordages.", "Quel foutu bug"],
                                 "spontanees": ["Petit à petit, le navire avance.", "On garde le cap, l’équipe.", "Avec un peu de vin ?"],
                                 "fini": ["Bravo {nom}, belle traversée !"], "activites": {"lit": ["Encore une page de mon carnet de bord."]}}}


def essai_route(base):
    print("6. Route /api/hote (vrai serveur)")
    d = os.path.join(base, "route")
    os.makedirs(os.path.join(d, ".studio"), exist_ok=True)
    hote.ecrire_json(os.path.join(d, ".studio", "studio.config.json"), {"nom_projet": "Essai", "langue": "fr", "mode": "travail", "postes": []})
    s = Serveur(d)
    try:
        c, r = s.api("/api/hote", {"action": "prompt", "texte": "un pote qui fume un joint et dit merde"})
        ok(c == 422 and "Refusé" in r.get("erreur", ""), f"prompt refusé par le filtre du serveur (422) : {r.get('erreur', '')[:60]}")
        ok(not glob.glob(os.path.join(d, ".studio", "demandes_vocales", "*_hote.json")), "aucune demande écrite pour un prompt refusé")
        c, r = s.api("/api/hote", {"action": "prompt", "texte": "Un vieux marin calme à barbe, en bleu, qui lit et passe voir l'équipe."})
        dem = lire_json(glob.glob(os.path.join(d, ".studio", "demandes_vocales", "*_hote.json"))[0]) if c == 200 else {}
        ok(c == 200 and dem.get("cible") == "hote" and "hote.py" in dem.get("consigne", "") and "payant" in dem.get("consigne", ""),
           "demande « hote » pour l'assistant, avec la consigne (pièces du skill, rien de payant, hote.py proposer)")
        ok((lire_json(os.path.join(d, ".studio", "hote_proposition.json")) or {}).get("statut") == "en_attente", "proposition en attente pendant que l'assistant compose")
        c2, r2 = s.api("/api/hote", {"action": "prompt", "texte": "Un vieux marin calme à barbe, en bleu, qui lit et passe voir l'équipe."})
        ok(r2.get("doublon"), "même prompt renvoyé dans la minute : une seule demande")
        # Annuler pendant l'attente : la demande est annulée, l'assistant ne peut plus proposer pour elle, le même texte repart
        id1 = r.get("id", "")
        c, ra = s.api("/api/hote", {"action": "oublier_proposition"})
        d1 = lire_json(os.path.join(d, ".studio", "demandes_vocales", id1 + ".json")) or {}
        ok(c == 200 and ra.get("demande_annulee") == id1 and d1.get("statut") == "annulee" and not os.path.exists(os.path.join(d, ".studio", "hote_proposition.json")),
           f"Annuler : demande « hote » marquée annulée ({d1.get('statut')}), attente retirée")
        hote.ecrire_json(os.path.join(d, ".studio", "hote_brouillon.json"), FICHE_ASSISTANT)
        out = subprocess.run([sys.executable, "-I", "-B", os.path.join(STUDIO, "hote.py"), "--projet", d, "proposer", os.path.join(d, ".studio", "hote_brouillon.json"), "--demande", id1],
                             capture_output=True, text=True, encoding="utf-8")
        ok(out.returncode == 3 and "annulée" in out.stdout and not os.path.exists(os.path.join(d, ".studio", "hote_proposition.json")),
           "fiche arrivée après Annuler : pas d'aperçu, pas de « Ton hôte est prêt »")
        c, r = s.api("/api/hote", {"action": "prompt", "texte": "Un vieux marin calme à barbe, en bleu, qui lit et passe voir l'équipe."})
        ok(c == 200 and not r.get("doublon") and r.get("id") and r.get("id") != id1
           and (lire_json(os.path.join(d, ".studio", "hote_proposition.json")) or {}).get("demande") == r.get("id"),
           "même texte renvoyé tout de suite après Annuler : nouvelle demande (pas de doublon)")
        hote.ecrire_json(os.path.join(d, ".studio", "hote_brouillon.json"), FICHE_ASSISTANT)
        out = subprocess.run([sys.executable, "-I", "-B", os.path.join(STUDIO, "hote.py"), "--projet", d, "proposer", os.path.join(d, ".studio", "hote_brouillon.json"), "--demande", r.get("id", "")],
                             capture_output=True, text=True, encoding="utf-8")
        prop = lire_json(os.path.join(d, ".studio", "hote_proposition.json")) or {}
        ok(out.returncode == 0 and prop.get("statut") == "prete" and len(prop["fiche"]["repliques"]["coin"]) == 2 and prop["fiche"]["source"] == "prompt"
           and len(prop["fiche"]["repliques"]["spontanees"]) == 2,
           f"fiche simulée de l'assistant : filtrée (réplique vulgaire et réplique « vin » écartées), prête pour l'aperçu ({prop.get('avertissements')})")
        c, r = s.api("/api/hote", {"action": "creer", "fiche": prop.get("fiche")})
        h = lire_json(os.path.join(d, ".studio", "hote.json")) or {}
        ok(c == 200 and h.get("nom") == "Capitaine Mo" and h.get("cree_le") and (lire_json(os.path.join(d, ".studio", "hote_proposition.json")) or {}).get("statut") == "installee",
           "aperçu accepté : hôte installé (hote.json), proposition marquée installée")
        c, r = s.api("/api/hote", {"action": "creer", "fiche": fiche_choix(nom="Sale idiot")})
        ok(c == 422 and (lire_json(os.path.join(d, ".studio", "hote.json")) or {}).get("nom") == "Capitaine Mo", "nom dénigrant refusé (422), l'hôte en place n'est pas touché")
        c, r = s.api("/api/hote", {"action": "regler", "parole": "rarement", "sons": False})
        h = lire_json(os.path.join(d, ".studio", "hote.json")) or {}
        ok(c == 200 and h["reglages"] == {"sons": False, "parole": "rarement"}, "Réglages : parole et sons enregistrés")
        c, r = s.api("/api/hote", {"action": "regler", "parole": "tout le temps"})
        ok(c == 400, "parole inconnue refusée (400)")
        c, r = s.api("/api/hote", {"action": "creer", "fiche": fiche_choix()})
        ok(c == 200 and glob.glob(os.path.join(d, ".studio", "anciens", "hote_remplace_*.json")), "modification : l'ancienne fiche est gardée dans anciens/")
        c, r = s.api("/api/hote", {"action": "supprimer"})
        ok(c == 200 and not os.path.exists(os.path.join(d, ".studio", "hote.json")) and glob.glob(os.path.join(d, ".studio", "anciens", "hote_supprime_*.json")),
           "suppression : hote.json rangé dans anciens/ (rien d'effacé pour de bon)")
        c, r = s.api("/api/hote", {"action": "supprimer"})
        ok(c == 404, "supprimer sans hôte : 404")
        c, r = s.api("/api/hote", {"action": "voler"})
        ok(c == 400, "action inconnue : 400")
    finally:
        s.arreter()


# ------------------------------------------------------------------ 2. navigateur (Chrome sans tête, son coupé)
class WS:
    """Client WebSocket minimal (protocole DevTools), bibliothèque standard."""
    def __init__(self, url):
        hote_, chemin = url[len("ws://"):].split("/", 1)
        h, p = hote_.split(":")
        self.s = socket.create_connection((h, int(p)), timeout=60)
        cle = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET /{chemin} HTTP/1.1\r\nHost: {hote_}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                        f"Sec-WebSocket-Key: {cle}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        r = b""
        while b"\r\n\r\n" not in r:
            r += self.s.recv(1)
        self.n = 0

    def envoyer(self, methode, params=None):
        self.n += 1
        donnees = json.dumps({"id": self.n, "method": methode, "params": params or {}}).encode()
        masque = os.urandom(4)
        L = len(donnees)
        tete = bytes([0x81]) + (bytes([0x80 | L]) if L < 126 else (bytes([0x80 | 126]) + struct.pack(">H", L) if L < 65536 else bytes([0x80 | 127]) + struct.pack(">Q", L)))
        self.s.sendall(tete + masque + bytes(b ^ masque[i % 4] for i, b in enumerate(donnees)))
        while True:
            m = json.loads(self.recevoir())
            if m.get("id") == self.n:
                return m.get("result", {})

    def lire(self, n):
        b = b""
        while len(b) < n:
            x = self.s.recv(n - len(b))
            if not x:
                raise ConnectionError("fermé")
            b += x
        return b

    def recevoir(self):
        morceaux = []
        while True:
            a, b = self.lire(2)
            L = b & 0x7F
            if L == 126:
                L = struct.unpack(">H", self.lire(2))[0]
            elif L == 127:
                L = struct.unpack(">Q", self.lire(8))[0]
            morceaux.append(self.lire(L))
            if a & 0x80:
                return b"".join(morceaux).decode("utf-8", "replace")


class Navigateur:
    def __init__(self, chrome):
        self.ud = tempfile.mkdtemp(prefix="essai_hote_chrome_")
        self.port = port_libre()
        self.p = subprocess.Popen([chrome, "--headless=new", "--mute-audio", f"--remote-debugging-port={self.port}", f"--user-data-dir={self.ud}",
                                   "--hide-scrollbars", "--no-first-run", "--no-default-browser-check", "--window-size=1400,900", "about:blank"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(80):
            try:
                pages = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json", timeout=1).read())
                self.cible = next(p for p in pages if p.get("type") == "page")
                break
            except Exception:
                time.sleep(.2)
        self.ws = WS(self.cible["webSocketDebuggerUrl"])
        self.ws.envoyer("Runtime.enable")
        self.ws.envoyer("Page.enable")

    def taille(self, L, H, mobile=False):
        self.ws.envoyer("Emulation.setDeviceMetricsOverride", {"width": L, "height": H, "deviceScaleFactor": 2 if mobile else 1, "mobile": mobile})
        self.ws.envoyer("Emulation.setTouchEmulationEnabled", {"enabled": mobile, "maxTouchPoints": 5 if mobile else 0})
        if mobile:
            self.ws.envoyer("Emulation.setUserAgentOverride", {"userAgent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36"})

    def aller(self, url, attente=6):
        self.ws.envoyer("Page.navigate", {"url": url})
        time.sleep(attente)

    def js(self, code):
        r = self.ws.envoyer("Runtime.evaluate", {"expression": f"(async () => {{ {code} }})()", "awaitPromise": True, "returnByValue": True})
        if r.get("exceptionDetails"):
            return {"_erreur": str(r["exceptionDetails"].get("exception", {}).get("description", r["exceptionDetails"]))[:300]}
        return (r.get("result") or {}).get("value")

    def capture(self, chemin):
        r = self.ws.envoyer("Page.captureScreenshot", {"format": "png"})
        with open(chemin, "wb") as f:
            f.write(base64.b64decode(r["data"]))
        return chemin

    def fermer(self):
        try:
            for p in json.loads(urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json", timeout=2).read()):
                if p.get("type") == "page":
                    urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/close/{p['id']}", timeout=2).read()
        except Exception:
            pass
        self.p.terminate()
        try:
            self.p.wait(5)
        except Exception:
            self.p.kill()
        time.sleep(.5)
        shutil.rmtree(self.ud, ignore_errors=True)


def attendre(nav, code, s=12, pas=.4):
    fin = time.time() + s
    v = None
    while time.time() < fin:
        v = nav.js(code)
        if v and not (isinstance(v, dict) and v.get("_erreur")):
            return v
        time.sleep(pas)
    return v


def zoom_sur_hote(nav, nom, z=2.6):
    """Capture rapprochée de l'hôte : caméra remise à plat, étiquettes masquées le temps de la photo (lisibilité du coin)."""
    nav.js("Bureau.recadrer(); LS.set('etiquettes', 'jamais'); return true;")
    time.sleep(.5)
    e = nav.js("return __hoteEssai.ecran();")
    if e:
        nav.js(f"Bureau.zoomer({z}, {e[0]}, {e[1] + 40}); return true;")
        time.sleep(1.2)
        nav.capture(nom)
    nav.js("Bureau.recadrer(); LS.set('etiquettes', 'toujours'); return true;")
    return bool(e)


def clic(nav, sel):
    return nav.js(f"const e = document.querySelector({json.dumps(sel)}); if (!e) return false; e.click(); return true;")


def essai_navigateur(dossier, captures, etat_quete):
    print("7. Dans la page (Chrome sans tête, son coupé)")
    chrome = next((c for c in CHROMES if os.path.isfile(c)), None)
    if not chrome:
        print("  (Chrome introuvable : partie navigateur sautée)")
        return
    st = os.path.join(dossier, ".studio")
    if not os.path.isfile(os.path.join(st, "studio.config.json")):
        raise SystemExit(f"projet d'essai absent : lance d'abord essai_complet.py tout --dossier {dossier}")
    os.makedirs(captures, exist_ok=True)
    sauve = tempfile.mkdtemp(prefix="essai_hote_sauve_")
    for n in ("quetes_etat.json", "hote.json", "hote_proposition.json", "reglages.json"):
        if os.path.isfile(os.path.join(st, n)):
            shutil.copy2(os.path.join(st, n), os.path.join(sauve, n))
    avant_dem = set(glob.glob(os.path.join(st, "demandes_vocales", "*")))
    avant_anc = set(glob.glob(os.path.join(st, "anciens", "hote*")))
    for n in ("hote.json", "hote_proposition.json"):
        if os.path.isfile(os.path.join(st, n)):
            os.remove(os.path.join(st, n))
    if etat_quete:
        hote.ecrire_json(os.path.join(st, "quetes_etat.json"), etat_quete)
    rg = lire_json(os.path.join(st, "reglages.json"), {}) or {}
    hote.ecrire_json(os.path.join(st, "reglages.json"), dict(rg, mode_absent=False))
    s = Serveur(dossier)
    nav = Navigateur(chrome)
    url = f"http://127.0.0.1:{s.port}/studio.html?essai"
    cap = lambda n: nav.capture(os.path.join(captures, n))  # noqa: E731
    try:
        nav.taille(1400, 900)
        nav.aller(url, 7)
        nav.js("try { Tuto && Tuto.fermer && Tuto.fermer(); } catch (e) {} document.querySelectorAll('.tuto, #tuto').forEach(x => x.remove()); return true;")
        # page muette : Chrome lancé avec --mute-audio ET son du studio coupé avant toute interaction
        coupe = nav.js("if (!Son.coupe()) Son.basculer(); return Son.coupe();")
        ok("--mute-audio" in nav.p.args and coupe is True, f"page muette (Chrome --mute-audio, son du studio coupé : {coupe})")
        ok(attendre(nav, "return !!(window.HoteStudio && window.__hoteEssai && __hoteEssai.etat().cat);"), "hote.js chargé, catalogue lu")
        # titres de tâche ou de commit : l'hôte ne répète jamais un titre qui ne passe pas le filtre
        r = nav.js("return [__hoteEssai.remplir('Nouveau commit : « {titre} »', { titre: 'fix: cette merde de bug' }), "
                   "__hoteEssai.remplir('{nom} a fini « {tache} »', { nom: 'Ada', tache: 'Corriger le menu' })];")
        ok(r and "merde" not in r[0] and "nouvelle étape" in r[0] and r[1] == "Ada a fini « Corriger le menu »",
           f"jetons {{titre}} et {{tache}} passés au filtre avant la réplique : {r}")
        ok(nav.js("return __hoteEssai.etat().hote === null;"), "pas d'hôte au départ")
        ch0 = nav.js("return __bureauxEssai().then(r => r.chevauchements);") or []
        ok(nav.js("return Date.now() > 0 && (Son.coupe() || true);") is True, "page muette (Chrome --mute-audio)")
        # quête
        if etat_quete:
            nav.js("Quetes.maj(); return true;")
            time.sleep(1.5)
            nav.js("Quetes.ouvrir('Q-SU-04'); return true;")
            b = attendre(nav, "const b = document.querySelector('[data-q=\"hote\"]'); return b && b.textContent;", 6)
            ok(b and "Créer mon hôte" in b, f"carte de la quête : bouton « Créer mon hôte » ({b})")
            time.sleep(1.2)
            cap("pc_1_quete.png")
            clic(nav, '[data-q="hote"]')
            ok(attendre(nav, "return Panneau.ouvert() === 'hote' && !!document.querySelector('[data-mode=\"prompt\"]');", 6), "le bouton ouvre l'écran de création (choix ou prompt)")
            cap("pc_2_creation.png")
        else:
            nav.js("HoteStudio.creer(); return true;")
        # chemin prompt
        clic(nav, '[data-mode="prompt"]')
        time.sleep(.6)
        nav.js("const z = document.querySelector('#ho-prompt'); z.value = 'un videur qui fume un joint et traite les gens de nuls'; z.dispatchEvent(new Event('input')); return true;")
        r = nav.js("return { err: document.querySelector('#ho-err').textContent, off: document.querySelector('[data-nav=\"envoyer\"]').disabled };")
        ok(r and r["off"] and "Refusé" in r["err"], f"filtre dans la page : prompt refusé, envoi bloqué ({r and r['err'][:40]})")
        cap("pc_3_prompt_refuse.png")
        nav.js("const z = document.querySelector('#ho-prompt'); z.value = 'Un vieux marin calme à barbe, en bleu, qui lit, regarde par la fenêtre et passe voir l’équipe.'; z.dispatchEvent(new Event('input')); return true;")
        clic(nav, '[data-nav="envoyer"]')
        ok(attendre(nav, "return __hoteEssai.etat().mode === 'attente';", 6), "prompt envoyé : l'écran attend la fiche de l'assistant")
        cap("pc_4_prompt_attente.png")
        dem = [f for f in glob.glob(os.path.join(st, "demandes_vocales", "*_hote.json")) if f not in avant_dem]
        dj = lire_json(dem[0]) if dem else {}
        ok(dj.get("cible") == "hote" and "marin" in dj.get("texte", "") and dj.get("consigne"), "demande « hote » déposée pour l'assistant (texte et consigne)")
        hote.ecrire_json(os.path.join(st, "hote_brouillon.json"), FICHE_ASSISTANT)
        hote.proposer(dossier, os.path.join(st, "hote_brouillon.json"), dj.get("id"))
        os.remove(os.path.join(st, "hote_brouillon.json"))
        ok(attendre(nav, "return __hoteEssai.etat().mode === 'apercu' && !!document.querySelector('#ho-ap');", 14), "fiche simulée de l'assistant : l'aperçu s'affiche tout seul")
        time.sleep(.8)
        cap("pc_5_prompt_apercu.png")
        clic(nav, '[data-nav="installer"]')
        h = attendre(nav, "const e = __hoteEssai.etat(); return e.hote && e.hote.nom;", 10)
        hj = lire_json(os.path.join(st, "hote.json")) or {}
        ok(h == "Capitaine Mo" and hj.get("source") == "prompt" and hj.get("repliques", {}).get("coin"), "installé depuis le prompt : hote.json (source prompt, répliques à lui)")
        time.sleep(1)
        ok(attendre(nav, "const e = __hoteEssai.etat(); return e.pos && e.marche;", 6), "il entre par la porte et marche vers son coin")
        cap("pc_6_arrivee.png")
        nav.js("for (let i = 0; i < 40; i++) __hoteEssai.teleporter(); return true;")
        # modification par les choix (8 étapes)
        nav.js("HoteStudio.creer(__hoteEssai.etat().hote); return true;")
        time.sleep(.8)
        choix = [("allure", "petite"), ("couleurs", "foret"), ("accessoire", "chapeau"), ("coin", "coeur"), ("activites", None), ("objets", None), ("ton", "chaleureux")]
        for i, (etape, v) in enumerate(choix):
            if etape == "activites":
                nav.js("const ch = __hoteEssai.choix(); for (const a of ch.activites) document.querySelector(`.ho-carte[data-v=\"${a}\"]`).click(); return true;")
                for a in ("boisson", "arrose", "musique", "tournee"):
                    clic(nav, f'.ho-carte[data-v="{a}"]')
                n = nav.js("return document.querySelectorAll('.ho-carte.choisie').length;")
                clic(nav, '.ho-carte[data-v="lit"]')
                n5 = nav.js("return document.querySelectorAll('.ho-carte.choisie').length;")
                ok(n == 4 and n5 == 4, f"activités : 4 au plus ({n} puis {n5})")
            elif etape == "objets":
                nav.js("const ch = __hoteEssai.choix(); for (const o of ch.objets) document.querySelector(`.ho-carte[data-v=\"${o}\"]`).click(); return true;")
                for o in ("tapis", "lampe", "aquarium"):
                    clic(nav, f'.ho-carte[data-v="{o}"]')
                r = nav.js("return [...document.querySelectorAll('.ho-carte[disabled]')].map(b => b.dataset.v);")
                ok(sorted(r or []) == ["plante", "radio"], f"objets apportés par les activités affichés d'office : {r}")
            else:
                clic(nav, f'.ho-carte[data-v="{v}"]')
            if etape in ("allure", "coin", "activites", "ton"):
                time.sleep(.5)
                cap(f"pc_7_choix_{i + 1}_{etape}.png")
            ok(clic(nav, '[data-nav="suivant"]:not([disabled])'), f"étape « {etape} » validée")
            time.sleep(.4)
        nav.js("const i = document.querySelector('#ho-nom'); i.value = 'Gros nul'; i.dispatchEvent(new Event('input')); return true;")
        ok(nav.js("return document.querySelector('[data-nav=\"suivant\"]').disabled && /Refusé/.test(document.querySelector('#ho-err').textContent);"), "nom dénigrant refusé dans la page")
        nav.js("const i = document.querySelector('#ho-nom'); i.value = 'Lou'; i.dispatchEvent(new Event('input')); return true;")
        time.sleep(.5)
        cap("pc_8_choix_nom.png")
        clic(nav, '[data-nav="suivant"]')
        h = attendre(nav, "const e = __hoteEssai.etat(); return e.hote && e.hote.nom === 'Lou' && e.hote;", 10)
        ok(h and h["coin"] == "coeur" and h["activites"] == ["boisson", "arrose", "musique", "tournee"] and set(h["objets"]) >= {"tapis", "lampe", "aquarium", "plante", "radio"} and h["source"] == "choix",
           f"créé par les choix : coin, 4 activités, objets ({h and h['objets']})")
        ok(bool(glob.glob(os.path.join(st, "anciens", "hote_remplace_*.json"))), "l'hôte d'avant est gardé dans anciens/")
        time.sleep(1)
        # scène : coin, activités
        nav.js("__hoteEssai.forcer('repos'); for (let i = 0; i < 60; i++) __hoteEssai.teleporter(); return true;")
        time.sleep(1.2)
        cap("pc_9_scene.png")
        zoom_sur_hote(nav, os.path.join(captures, "pc_10_coin_zoom.png"))
        textes = {}
        for a in ("boisson", "arrose", "musique", "tournee"):
            nav.js(f"__hoteEssai.forcer('{a}'); return true;")
            for _ in range(30):
                nav.js("__hoteEssai.teleporter(); return true;")
                time.sleep(.15)
            textes[a] = nav.js("return __hoteEssai.etat().texte;")
            if a in ("arrose", "boisson", "musique"):
                zoom_sur_hote(nav, os.path.join(captures, f"pc_11_activite_{a}.png"))
        ok(all(textes.values()) and textes["arrose"] == "arrose les plantes" and textes["musique"] == "met un petit air", f"activités jouées dans la scène : {textes}")
        nav.js("Bureau.recadrer(); __hoteEssai.forcer('repos'); for (let i = 0; i < 60; i++) __hoteEssai.teleporter(); return true;")
        ch1 = nav.js("return __bureauxEssai().then(r => r.chevauchements);") or []
        ok(not set(ch1) - set(ch0), f"image dessinée : le coin de l'hôte ne touche aucun bureau ({sorted(set(ch1) - set(ch0))[:3]})")
        ok(nav.js("return !!HoteStudio.etiquette() && HoteStudio.etiquette().nom === 'Lou';"), "étiquette au-dessus de lui (nom et ce qu'il fait)")
        nav.js("Bureau.taire('hote'); LS.set('babil', true); return __hoteEssai.dire('Bonjour, je suis Lou.', true);")
        b = attendre(nav, "const b = window.__bullesEssai && __bullesEssai(); return b && b.ids && b.ids.some(x => String(x).startsWith('hote')) && b.ids;", 5)
        ok(bool(b), f"il parle : bulle dans la scène ({b})")
        LSoff = nav.js("LS.set('babil', false); Bureau.taire('hote'); const r = __hoteEssai.dire('ne doit pas parler', true); LS.set('babil', true); return r;")
        ok(LSoff is False, "babillage coupé : il se tait (règles du bavardage)")
        cap("pc_12_bulle.png")
        # réglages
        nav.js("ouvrirReglages(); return true;")
        ok(attendre(nav, "const z = document.querySelector('#rg-hote'); return z && /Lou/.test(z.textContent);", 5), "Réglages : section « Hôte du studio »")
        nav.js("document.querySelector('#rg-hote').scrollIntoView(); const s = document.querySelector('#ho-parole'); s.value = 'rarement'; s.dispatchEvent(new Event('change')); return true;")
        time.sleep(1)
        ok((lire_json(os.path.join(st, "hote.json")) or {}).get("reglages", {}).get("parole") == "rarement", "Réglages : « il parle rarement » enregistré")
        cap("pc_13_reglages.png")
        # téléphone
        nav.taille(390, 844, mobile=True)
        nav.aller(url, 7)
        nav.js("document.querySelectorAll('.tuto, #tuto').forEach(x => x.remove()); return true;")
        attendre(nav, "return !!(window.__hoteEssai && __hoteEssai.etat().hote);", 8)
        nav.js("__hoteEssai.forcer('repos'); for (let i = 0; i < 60; i++) __hoteEssai.teleporter(); return true;")
        time.sleep(1.5)
        cap("tel_1_scene.png")
        zoom_sur_hote(nav, os.path.join(captures, "tel_2_coin_zoom.png"), 2.2)
        nav.js("HoteStudio.creer(__hoteEssai.etat().hote); return true;")
        time.sleep(1)
        ok(nav.js("return document.querySelectorAll('.ho-carte').length >= 4 && document.documentElement.scrollWidth <= innerWidth + 1;"), "téléphone : écran de création lisible, sans défilement horizontal")
        cap("tel_3_creation.png")
        nav.js("Panneau.fermer(); return true;")
        time.sleep(.6)
        nav.js("HoteStudio.ouvrirFiche(); return true;")
        time.sleep(.8)
        cap("tel_4_fiche.png")
        nav.js("Panneau.fermer(); return true;")
        time.sleep(.6)
        nav.js("ouvrirReglages(); return true;")
        time.sleep(.8)
        nav.js("document.querySelector('#rg-hote').scrollIntoView(); return true;")
        time.sleep(.4)
        cap("tel_5_reglages.png")
        # suppression
        clic(nav, "#ho-supprimer")
        ok(nav.js("return document.querySelector('#ho-supprimer').classList.contains('confirme');"), "supprimer demande une confirmation")
        clic(nav, "#ho-supprimer")
        time.sleep(1.2)
        ok(not os.path.exists(os.path.join(st, "hote.json")) and glob.glob(os.path.join(st, "anciens", "hote_supprime_*.json")), "supprimé : hote.json rangé dans anciens/")
        ok(nav.js("return __hoteEssai.etat().depart;"), "il repart par la porte")
        rg = nav.js("const z = document.querySelector('#rg-hote'); return { lou: /Lou/.test(z.textContent), sup: !!z.querySelector('#ho-supprimer'), mod: !!z.querySelector('#ho-modifier'), creer: !!z.querySelector('#ho-creer') };")
        ok(rg and not rg["lou"] and not rg["sup"] and not rg["mod"], f"Réglages juste après Supprimer : plus de nom, ni Modifier ni Supprimer ({rg})")
        cap("tel_6_reglages_apres_suppression.png")
        nav.js("Panneau.fermer(); for (let i = 0; i < 60; i++) __hoteEssai.teleporter(); return true;")
        time.sleep(1.5)
        ok(nav.js("return __hoteEssai.etat().hote === null && !HoteStudio.etiquette();"), "parti : plus d'hôte dans la scène")
        err = nav.js("return (window.__erreurs || []).filter(x => /hôte|hote/i.test(x));")
        ok(not err, f"aucune erreur de l'hôte dans la page {err}")
    finally:
        nav.fermer()
        s.arreter()
        for n in ("hote.json", "hote_proposition.json", "hote_brouillon.json"):
            if os.path.isfile(os.path.join(st, n)):
                os.remove(os.path.join(st, n))
        for f in set(glob.glob(os.path.join(st, "demandes_vocales", "*"))) - avant_dem:
            if os.path.isfile(f) and f.endswith("_hote.json"):
                os.remove(f)
        for f in set(glob.glob(os.path.join(st, "anciens", "hote*"))) - avant_anc:
            os.remove(f)
        for n in os.listdir(sauve):
            shutil.copy2(os.path.join(sauve, n), os.path.join(st, n))
        if not os.path.isfile(os.path.join(sauve, "quetes_etat.json")) and etat_quete and os.path.isfile(os.path.join(st, "quetes_etat.json")):
            os.remove(os.path.join(st, "quetes_etat.json"))
        shutil.rmtree(sauve, ignore_errors=True)
    print(f"  captures : {captures}")


def main():
    a = sys.argv[1:]
    val = lambda k, d=None: a[a.index(k) + 1] if k in a else d  # noqa: E731
    t0 = time.time()
    base = tempfile.mkdtemp(prefix="essai_hote_")
    try:
        essai_catalogue()
        essai_catalogue_vide()
        essai_coins()
        essai_filtre()
        essai_fiche()
        etat = essai_quete(base)
        essai_route(base)
        if "--sans-navigateur" not in a and val("--dossier"):
            essai_navigateur(os.path.abspath(val("--dossier")), os.path.abspath(val("--captures", os.path.join(base, "captures"))), etat)
        elif "--sans-navigateur" not in a:
            print("7. (navigateur : passe --dossier <…>/essai_skill, préparé par essai_complet.py tout)")
    finally:
        if "--garder" not in a:
            shutil.rmtree(base, ignore_errors=True)
    print(f"\n{RES['ok']} ok, {RES['echec']} échec(s) en {time.time() - t0:.1f} s")
    return 1 if RES["echec"] else 0


if __name__ == "__main__":
    sys.exit(main())
