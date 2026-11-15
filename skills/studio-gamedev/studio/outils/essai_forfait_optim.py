"""Essai de « Optimiser le forfait » (studio/optimiseur_forfait.py, interrupteur de la barre du forfait).
Test of the "Optimize the plan" switch.

1. Calcul (sans serveur) : rythme et projection, ajout sous 90 % projeté, retrait au-dessus de 95 %, retrait à 85 % utilisés
   avec plus de 20 min avant la remise à zéro, hebdo épuisé (pas d'ajout, retrait au-delà de 100 %), chaîne critique jamais
   retirée, interrupteur coupé ou « Tout couper » : aucune consigne active ; historique (un relevé par « maj », remise à zéro).
2. Fichiers : ecrire_forfait.py note le relevé et écrit forfait_consigne.json ; optimiseur_forfait.py --projet l'affiche.
3. Serveur (port libre, jamais 8790) : /api/reglages garde forfait_optimise (true / false), refuse une valeur non booléenne,
   et l'état survit à un autre réglage et à un redémarrage du serveur.
4. Page (Chrome sans tête, --mute-audio, son du studio coupé avant toute interaction, onglet fermé à la fin ; sauté sans Chrome
   ou avec --sans-navigateur) : rôle switch, aria-checked, étiquette, gris coupé / vert actif, clic et clavier (Espace,
   Entrée), état gardé après rechargement, ligne de l'optimiseur.

python -I -B essai_forfait_optim.py [--sans-navigateur] [--garder]      code 0 = tout vert
"""
import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(ICI)
sys.path.insert(0, STUDIO)
sys.path.insert(0, ICI)
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
import optimiseur_forfait as O  # noqa: E402

ECHECS = []


def ok(cond, quoi):
    print(("  ok   " if cond else "  ÉCHEC ") + quoi)
    if not cond:
        ECHECS.append(quoi)


def iso(t):
    return dt.datetime.fromtimestamp(t).astimezone().isoformat(timespec="seconds")


def forfait(t, pct_c, raz_c, pct_l=None, raz_l=None):
    fen = [{"nom": "Session (5 h)", "pct_utilise": pct_c, "remise_a_zero": iso(raz_c)}]
    if pct_l is not None:
        fen.append({"nom": "Hebdo", "pct_utilise": pct_l, "remise_a_zero": iso(raz_l)})
    return {"maj": iso(t), "source": "essai toutes les 15 min", "fenetres": fen}


def histo2(t0, t1, c0, c1, l0=None, l1=None):
    h = O.noter_releve([], forfait(t0, c0, t0 + 3 * 3600, l0, t0 + 3 * 86400) if l0 is not None else forfait(t0, c0, t0 + 3 * 3600))
    return O.noter_releve(h, forfait(t1, c1, t0 + 3 * 3600, l1, t0 + 3 * 86400) if l1 is not None else forfait(t1, c1, t0 + 3 * 3600))


CONF = {"mode": "travail", "postes": [{"id": "direction"}, {"id": "code"}, {"id": "art"}, {"id": "son"}, {"id": "moteur"}],
        "outils_lourds": [{"nom": "Godot", "processus": ["godot.exe"], "poste": "moteur"}], "chaine_critique": ["code"]}


def postes(travail, libres=()):
    out = [{"id": p, "etat": "travaille", "genre": "recrue" if p.startswith("recrue") else "fixe"} for p in travail]
    out += [{"id": p, "etat": "disponible", "genre": "fixe"} for p in libres]
    return out


def essai_calcul():
    print("1. Calcul")
    t0 = 1_800_000_000.0
    t1 = t0 + 1800                             # 30 min plus tard
    h = histo2(t0, t1, 20, 25)                 # 10 points / h
    ok(abs(O.rythme(h, "Session (5 h)") - 10.0) < 1e-6, f"rythme : 10 points/h ({O.rythme(h, 'Session (5 h)')})")
    raz = t0 + 3 * 3600                        # 2 h 30 après t1
    ok(abs(O.projection(25, 10, raz, t1) - 50.0) < 1e-6, "projection : 25 % + 10 × 2,5 h = 50 %")
    h_bis = O.noter_releve(h, forfait(t1, 25, raz))
    ok(len(h_bis) == 2, "même « maj » : relevé noté une seule fois")
    h_raz = O.noter_releve(h, forfait(t1 + 1800, 3, raz + 5 * 3600))
    ok(O.rythme(h_raz, "Session (5 h)") is None, "après une remise à zéro (le % baisse) : pas de rythme")
    regl = {"forfait_optimise": True}
    # ajout : 50 % projeté
    c = O.calculer(forfait(t1, 25, raz), h, postes(["direction", "art"], ["son", "moteur"]), CONF, regl, None, t1)
    ok(c["decision"] == "ajouter" and c["delta"] >= 1 and c["delta"] <= 3, f"ajout sous 90 % projeté : {c['decision']} {c['delta']} ({c['ligne']})")
    ok(c["ligne"].startswith("+") and "50 % projeté à la remise à zéro" in c["ligne"] and c["ligne_en"].startswith("+"), f"ligne lisible : {c['ligne']} / {c['ligne_en']}")
    ok(c["ajouter"][:1] == ["son"] or c["ajouter"][:1] == ["moteur"], f"postes libres proposés, les plus prioritaires d'abord : {c['ajouter']}")
    ok(c["cible"] == c["actifs"] + c["delta"], "cible = actifs + delta")
    big = O.calculer(forfait(t1, 25, raz), h, postes(["direction"]), CONF, regl, None, t1)
    ok(big["delta"] <= O.PAS_MAX and big["a_recruter"] == big["delta"], f"pas plus de {O.PAS_MAX} par relevé, sans poste libre : à recruter ({big['a_recruter']})")
    # retrait : 97 % projeté
    h2 = histo2(t0, t1, 60, 75)                # 30 points / h → 75 + 75 = 150 %
    trav = ["direction", "code", "moteur", "art", "son", "recrue-a"]
    c = O.calculer(forfait(t1, 75, raz), h2, postes(trav), CONF, regl, {"poste": "son"}, t1)
    ok(c["decision"] == "retirer" and c["ligne"].startswith("−"), f"retrait au-dessus de 95 % projeté : {c['ligne']}")
    crit = set(c["proteges"])
    ok({"direction", "code", "moteur", "son"} <= crit, f"chaîne critique : session, chaine_critique, outil lourd, chaîne active ({sorted(crit)})")
    ok(not (set(c["retirer"]) & crit) and c["retirer"][0] == "recrue-a", f"chaîne protégée, recrue retirée la première : {c['retirer']}")
    ok(c["retirer"] == ["recrue-a", "art"], f"jamais plus que les postes non protégés : {c['retirer']}")
    seul = O.calculer(forfait(t1, 75, raz), h2, postes(["direction", "code", "moteur"]), CONF, regl, None, t1)
    ok(seul["decision"] == "garder" and not seul["retirer"], f"seule la chaîne critique travaille : rien de retiré ({seul['ligne']})")
    # 85 % utilisés, remise dans plus de 20 min, rythme faible
    h3 = histo2(t0, t1, 86, 86.5)
    c = O.calculer(forfait(t1, 86.5, t1 + 3600), h3, postes(["direction", "art"]), CONF, regl, None, t1)
    ok(c["decision"] == "retirer" and c["retirer"] == ["art"], f"85 % utilisés à 60 min de la remise à zéro : retrait ({c['ligne']})")
    c = O.calculer(forfait(t1, 86.5, t1 + 600), h3, postes(["direction", "art"]), CONF, regl, None, t1)
    ok(c["decision"] != "retirer", f"85 % utilisés à 10 min de la remise à zéro : pas de retrait ({c['ligne']})")
    # hebdo
    h4 = histo2(t0, t1, 20, 25, 98.0, 99.2)
    c = O.calculer(forfait(t1, 25, raz, 99.2, t0 + 3 * 86400), h4, postes(["direction", "art"], ["son"]), CONF, regl, None, t1)
    ok(c["decision"] == "retirer" and "Hebdo" in c["raison"], f"hebdo projeté au-delà de 100 % : retrait ({c['ligne']})")
    h5 = histo2(t0, t1, 20, 25, 50.0, 50.1)
    c = O.calculer(forfait(t1, 25, raz, 50.1, t0 + 3 * 86400), h5, postes(["direction", "art"], ["son"]), CONF, regl, None, t1)
    ok(c["decision"] == "ajouter", f"hebdo loin de la limite : ajout ({c['ligne']})")
    # fin de semaine : l'hebdo vise 99 %, l'ajout est limité par lui
    h6 = histo2(t0, t1, 20, 25, 90.0, 92.0)    # hebdo +4 / h, remise dans 3 j : 92 + 4 × 71,5 → bien au-delà
    c = O.calculer(forfait(t1, 25, raz, 92.0, t1 + 1800), h6, postes(["direction", "art"], ["son"]), CONF, regl, None, t1)
    ok(c["decision"] in ("garder", "ajouter") and c["projection"]["Hebdo"] < 100, f"hebdo à 30 min de sa remise à zéro, 94 % projeté : {c['decision']} ({c['ligne']})")
    # garder entre 90 et 95
    h7 = histo2(t0, t1, 50, 66)                # 32 points / h → 66 + 80 = 146 ; on prend un autre cas
    h7 = histo2(t0, t1, 70, 78)                # 16 points / h → 78 + 16 × 0,9 h ≈ 92 %
    c = O.calculer(forfait(t1, 78, t1 + 0.9 * 3600), h7, postes(["direction", "art"]), CONF, regl, None, t1)
    ok(c["decision"] == "garder" and "Garder" in c["ligne"], f"entre 90 et 95 % projetés : on garde ({c['ligne']})")
    # coupé, pause, un seul relevé
    c = O.calculer(forfait(t1, 25, raz), h, postes(["art"]), CONF, {}, None, t1)
    ok(c["actif"] is False and c["decision"] == "coupe" and not c["ajouter"] and not c["retirer"], "interrupteur coupé (défaut) : aucune consigne")
    c = O.calculer(forfait(t1, 25, raz), h, postes(["art"]), CONF, {"forfait_optimise": True, "pause": True}, None, t1)
    ok(c["decision"] == "attendre" and not c["ajouter"], "« Tout couper » : optimiseur en attente")
    c = O.calculer(forfait(t1, 25, raz), O.noter_releve([], forfait(t1, 25, raz)), postes(["art"]), CONF, regl, None, t1)
    ok(c["decision"] == "attendre" and "2e relevé" in c["ligne"], f"un seul relevé : attend le deuxième ({c['ligne']})")


def ecrire(chemin, d):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)


def lire(chemin, defaut=None):
    try:
        with open(chemin, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defaut


def lancer(*args):
    p = subprocess.run([sys.executable, "-I", "-B", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    return p.returncode, p.stdout, p.stderr


def essai_fichiers(racine):
    print("2. Fichiers")
    projet = os.path.join(racine, "fichiers")
    st = os.path.join(projet, ".studio")
    ecrire(os.path.join(st, "studio.config.json"), dict(CONF, langue="fr"))
    ecrire(os.path.join(st, "reglages.json"), {"forfait_optimise": True})
    ecrire(os.path.join(st, "etat.json"), {"postes": postes(["direction", "art"], ["son"])})
    t = time.time()
    hist = [{"t": t - 1800, "fenetres": {"Session": 20.0}}]
    ecrire(os.path.join(st, "forfait_historique.json"), hist)
    c, o, e = lancer(os.path.join(ICI, "ecrire_forfait.py"), "--projet", projet, "--fenetre", "Session", "25", "+2h30", "--source", "essai toutes les 15 min")
    ok(c == 0 and "Traceback" not in e, f"ecrire_forfait.py : code {c} {e.strip()[:200]}")
    cons = lire(os.path.join(st, "forfait_consigne.json"), {})
    ok(cons.get("actif") is True and cons.get("decision") == "ajouter", f"consigne écrite au relevé : {cons.get('decision')} ({cons.get('ligne')})")
    ok("optimiseur : +" in o, f"ecrire_forfait.py affiche la consigne : {o.strip().splitlines()[-1] if o.strip() else ''}")
    ok(len(lire(os.path.join(st, "forfait_historique.json"), [])) == 2, "relevé ajouté à l'historique")
    c, o, e = lancer(os.path.join(STUDIO, "optimiseur_forfait.py"), "--projet", projet)
    ok(c == 0 and o.startswith("+") and "ajouter : son" in o, f"optimiseur_forfait.py --projet : {o.strip()[:160]}")
    c, o, e = lancer(os.path.join(STUDIO, "optimiseur_forfait.py"), "--projet", projet, "--json")
    ok(c == 0 and json.loads(o).get("decision") == "ajouter", "--json : consigne brute")
    ecrire(os.path.join(st, "reglages.json"), {"forfait_optimise": False})
    c, o, e = lancer(os.path.join(STUDIO, "optimiseur_forfait.py"), "--projet", projet)
    ok(lire(os.path.join(st, "forfait_consigne.json"), {}).get("actif") is False, "interrupteur coupé : consigne inactive")


def port_libre():
    import socket
    for p in range(8995, 9095):
        if p == 8790:
            continue
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise SystemExit("aucun port libre")


def teinte(css):
    """« vert », « gris » ou la couleur brute (thème clair ou sombre : seules les teintes comptent)."""
    try:
        r, g, b = (int(x) for x in css[css.index("(") + 1:css.index(")")].split(",")[:3])
    except (ValueError, AttributeError):
        return css
    if g - r > 40 and g - b > 30:
        return "vert"
    if max(r, g, b) - min(r, g, b) < 32:
        return "gris"
    return css


class Serveur:
    def __init__(self, projet):
        self.port = port_libre()
        self.base = f"http://127.0.0.1:{self.port}"
        self.p = subprocess.Popen([sys.executable, "-I", "-B", os.path.join(STUDIO, "serveur_studio.py"), "--projet", projet, "--port", str(self.port)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(75):
            try:
                urllib.request.urlopen(self.base + "/api/qui", timeout=1).read()
                return
            except Exception:
                time.sleep(.2)
        raise SystemExit("serveur injoignable")

    def api(self, route, corps):
        r = urllib.request.Request(self.base + route, data=json.dumps(corps).encode(), headers={"Content-Type": "application/json", "Origin": self.base})
        try:
            with urllib.request.urlopen(r, timeout=10) as x:
                return x.status, json.loads(x.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def arreter(self):
        self.p.terminate()
        try:
            self.p.wait(5)
        except Exception:
            self.p.kill()


def projet_page(racine):
    projet = os.path.join(racine, "page")
    st = os.path.join(projet, ".studio")
    ecrire(os.path.join(st, "studio.config.json"), dict(CONF, version=1, nom_projet="Essai forfait", langue="fr", dossier_agents=".claude/agents"))
    t = time.time()
    ecrire(os.path.join(st, "forfait.json"), forfait(t, 40, t + 2 * 3600, 30, t + 3 * 86400))
    ecrire(os.path.join(st, "etat.json"), {"postes": [], "horodatage": int(t), "forfait_optim": {"actif": True, "ligne": "+2 postes : 62 % projeté à la remise à zéro",
                                                                                            "ligne_en": "+2 desks: 62% projected at reset", "raison": "essai", "raison_en": "test"}})
    return projet


def essai_serveur(projet):
    print("3. Serveur")
    st = os.path.join(projet, ".studio")
    s = Serveur(projet)
    try:
        ok(not (lire(os.path.join(st, "reglages.json"), {}) or {}).get("forfait_optimise"), "désactivé par défaut")
        c, r = s.api("/api/reglages", {"forfait_optimise": True})
        ok(c == 200 and lire(os.path.join(st, "reglages.json"), {}).get("forfait_optimise") is True, f"allumé : reglages.json ({c})")
        c, r = s.api("/api/reglages", {"forfait_optimise": "oui"})
        ok(c == 400, f"valeur non booléenne refusée ({c})")
        c, r = s.api("/api/reglages", {"blague": False})
        ok(lire(os.path.join(st, "reglages.json"), {}).get("forfait_optimise") is True, "un autre réglage ne le change pas")
    finally:
        s.arreter()
    s = Serveur(projet)
    try:
        ok(lire(os.path.join(st, "reglages.json"), {}).get("forfait_optimise") is True, "état gardé après redémarrage du serveur")
        c, r = s.api("/api/reglages", {"forfait_optimise": False})
        ok(c == 200 and lire(os.path.join(st, "reglages.json"), {}).get("forfait_optimise") is False, "coupé : reglages.json")
    finally:
        s.arreter()


def essai_navigateur(projet):
    print("4. Page (Chrome sans tête, son coupé)")
    try:
        import essai_hote as EH
    except Exception as e:
        print(f"  (outils du navigateur indisponibles : {e} ; partie sautée)")
        return
    chrome = next((c for c in EH.CHROMES if os.path.isfile(c)), None)
    if not chrome:
        print("  (Chrome introuvable : partie navigateur sautée)")
        return
    st = os.path.join(projet, ".studio")
    ecrire(os.path.join(st, "reglages.json"), {"forfait_optimise": False})
    s = Serveur(projet)
    nav = EH.Navigateur(chrome)
    url = f"{s.base}/studio.html?essai"
    try:
        nav.taille(1600, 900)
        nav.aller(url, 7)
        coupe = nav.js("if (!Son.coupe()) Son.basculer(); return Son.coupe();")
        ok("--mute-audio" in nav.p.args and coupe is True, f"page muette (Chrome --mute-audio, son du studio coupé avant toute interaction : {coupe})")
        nav.js("try { Tuto && Tuto.fermer && Tuto.fermer(); } catch (e) {} document.querySelectorAll('.tuto, #tuto').forEach(x => x.remove()); return true;")
        e = EH.attendre(nav, "const r = window.__forfaitOptimEssai && __forfaitOptimEssai(); return r && !document.querySelector('#forfait').hidden ? r : null;", 15)
        ok(isinstance(e, dict) and e.get("role") == "switch" and e.get("coche") == "false" and e.get("nom") == "Optimiser le forfait",
           f"interrupteur : rôle switch, aria-checked false, étiquette FR ({e})")
        time.sleep(.5)
        gris = nav.js("return __forfaitOptimEssai().couleur;")
        ok(teinte(gris) == "gris", f"gris quand il est coupé ({gris})")
        ok(not (e or {}).get("ligne"), "coupé : pas de ligne de l'optimiseur")
        nav.js("document.querySelector('#forfait-optim').click(); return true;")
        e = EH.attendre(nav, "const r = __forfaitOptimEssai(); return r.coche === 'true' ? r : null;", 6)
        time.sleep(.5)
        vert = nav.js("return __forfaitOptimEssai().couleur;")
        ok(isinstance(e, dict) and teinte(vert) == "vert", f"clic : aria-checked true, vert ({vert})")
        for theme in ("sombre", "clair"):
            nav.js(f"document.documentElement.dataset.theme = '{theme}'; return true;")
            time.sleep(.5)
            v = nav.js("return __forfaitOptimEssai().couleur;")
            ok(teinte(v) == "vert", f"vert aussi en thème {theme} ({v})")
        ok(isinstance(e, dict) and e.get("ligne") == "+2 postes : 62 % projeté à la remise à zéro", f"ligne de l'optimiseur : {e and e.get('ligne')}")
        time.sleep(1)
        ok(lire(os.path.join(st, "reglages.json"), {}).get("forfait_optimise") is True, "clic enregistré dans reglages.json")
        nav.aller(url, 7)
        nav.js("if (!Son.coupe()) Son.basculer(); return true;")
        e = EH.attendre(nav, "const r = window.__forfaitOptimEssai && __forfaitOptimEssai(); return r && r.coche === 'true' ? r : null;", 15)
        ok(isinstance(e, dict), "état gardé après rechargement de la page")
        # clavier : Espace puis Entrée sur le bouton qui a le focus
        def touche(cle, code, kc):
            nav.js("document.querySelector('#forfait-optim').focus(); return document.activeElement.id;")
            for t in ("keyDown", "keyUp"):
                nav.ws.envoyer("Input.dispatchKeyEvent", {"type": t, "key": cle, "code": code, "windowsVirtualKeyCode": kc, "nativeVirtualKeyCode": kc,
                                                          **({"text": " " if cle == " " else "\r"} if t == "keyDown" else {})})
            time.sleep(1)
            return nav.js("return __forfaitOptimEssai().coche;")
        ok(touche(" ", "Space", 32) == "false", "clavier : Espace coupe l'interrupteur")
        ok(touche("Enter", "Enter", 13) == "true", "clavier : Entrée le rallume")
        time.sleep(1)
        ok(lire(os.path.join(st, "reglages.json"), {}).get("forfait_optimise") is True, "clavier enregistré dans reglages.json")
        nav.js("LANGUE = 'en'; traduirePage(); return true;")
        e = nav.js("return __forfaitOptimEssai();")
        ok(e and e.get("nom") == "Optimize the plan" and e.get("ligne", "").startswith("+2 desks"), f"étiquette et ligne en anglais ({e and e.get('nom')}, {e and e.get('ligne')})")
        ok(nav.js("return document.querySelector('#forfait-optim').tagName === 'BUTTON' && document.querySelector('#forfait-optim').tabIndex === 0;") is True,
           "atteignable au clavier (bouton natif)")
    finally:
        nav.fermer()
        s.arreter()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sans-navigateur", action="store_true")
    ap.add_argument("--garder", action="store_true")
    a = ap.parse_args(argv)
    racine = tempfile.mkdtemp(prefix="essai_forfait_optim_")
    try:
        essai_calcul()
        essai_fichiers(racine)
        projet = projet_page(racine)
        essai_serveur(projet)
        if not a.sans_navigateur:
            essai_navigateur(projet)
    finally:
        if a.garder:
            print("dossier gardé :", racine)
        else:
            shutil.rmtree(racine, ignore_errors=True)
    print("RÉUSSI" if not ECHECS else f"ÉCHECS : {len(ECHECS)}")
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    sys.exit(main())
