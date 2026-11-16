"""Essai : les questions déjà réglées quittent la conversation et la cloche, sur PC comme au téléphone.

Usage : python -I -B essai_questions_reglees.py [--captures <dossier>] [--garder]
  code 0 = tout vert.

Faux projet jetable (dossier temporaire neuf), vrai serveur_studio.py sur un port libre, Chrome sans tête (son coupé :
--mute-audio et son du studio coupé avant toute interaction ; onglets et Chrome fermés à la fin), profil de navigateur neuf
à chaque passage (un autre appareil : rien dans le stockage local, l'état vient du serveur).
decisions.json : une question ouverte datée dans le futur, une à répondre depuis le fil, une « tranchee_par_claude », une
« repondu », une « ouverte » qui porte déjà sa réponse, une réglée datée dans le futur, une ouverte dont la réponse est
déjà dans reponses.json (donnée sur un autre appareil).
Vérifie : seules les questions ouvertes ont une carte dans le fil ; l'heure future est ramenée à maintenant ; toutes les
réglées sont dans le repli « réglées » en tête, absentes de la cloche ; le badge de la cloche égale le nombre d'éléments ;
le repli reste ouvert d'un rendu à l'autre ; une réponse donnée depuis le fil garde sa carte, fait baisser la cloche de 1 et
part dans reponses.json du serveur ; sur un second appareil (téléphone 390 × 844, profil neuf), cette question est réglée.
"""
import argparse
import datetime
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ICI = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(ICI)
SKILL = os.path.dirname(STUDIO)
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
sys.path.insert(0, STUDIO)
sys.path.insert(0, ICI)
_spec = importlib.util.spec_from_file_location("essai_hote", os.path.join(ICI, "essai_hote.py"))
EH = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(EH)   # Serveur, Navigateur, attendre, CHROMES (client DevTools en bibliothèque standard)

ERREURS = []
OUVERTES = {"ouverte-futur", "a-repondre"}
REGLEES = {"tranchee", "repondu", "fiche-reponse", "reglee-futur", "srv-repondue"}


def verifie(cond, msg):
    print(("  ok    " if cond else "  ÉCHEC ") + msg)
    if not cond:
        ERREURS.append(msg)


def ecrire(chemin, donnees):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=1)


def lire(chemin, defaut=None):
    try:
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defaut


def projet(dossier, futur):
    st = os.path.join(dossier, ".studio")
    conf = lire(os.path.join(SKILL, "modeles", "studio.config.json"), {}) or {}
    conf.update({"mode": "travail", "nom_projet": "Essai questions", "langue": "fr"})
    ecrire(os.path.join(st, "studio.config.json"), conf)
    ecrire(os.path.join(st, "reglages.json"), {"mode_absent": False})
    hier = (datetime.datetime.now() - datetime.timedelta(hours=20)).strftime("%Y-%m-%dT%H:%M:%S")

    def d(id_, titre, **plus):
        x = {"id": id_, "titre": titre, "explication": "essai", "choix": ["a", "b"], "recommande": "a", "statut": "ouverte", "cree_le": hier}
        x.update(plus)
        return x
    ecrire(os.path.join(st, "decisions.json"), [
        d("ouverte-futur", "Question ouverte datée dans le futur ?", cree_le=futur),
        d("a-repondre", "Question à régler depuis le fil ?"),
        d("tranchee", "Question tranchée par l'assistant ?", statut="tranchee_par_claude", reponse="a", decide_le=hier),
        d("repondu", "Question au statut « repondu » ?", statut="repondu"),
        d("fiche-reponse", "Question ouverte qui porte sa réponse ?", reponse="b", repondue_le=hier),
        d("reglee-futur", "Question réglée datée dans le futur ?", statut="repondue", reponse="a", cree_le=futur, repondu_le=futur),
        d("srv-repondue", "Question répondue sur un autre appareil ?"),
    ])
    ecrire(os.path.join(st, "reponses.json"), [{"id": "srv-repondue", "choix": "b", "texte_libre": "", "repondu_le": hier}])


ETAT_JS = """
  const f = document.querySelector('#panneau [data-fil]'); if (!f) return null;
  const cartes = [...f.querySelectorAll('.msg.question')].map(x => ({ id: x.dataset.dec, heure: (x.querySelector('small') || {}).textContent || '' }));
  const rp = f.querySelector('#fil-reglees'), li = rp ? [...rp.querySelectorAll('li')].map(x => x.dataset.filId.replace(/^d:/, '')) : [];
  const cl = __cloche(), p = document.getElementById('nb-decisions');
  return { cartes, reglees: li, resume: rp ? rp.querySelector('summary').textContent : '', ouvertRepli: !!(rp && rp.open), premier: f.firstElementChild && f.firstElementChild.id,
           ouvertes: decisionsOuvertes().map(d => d.id), cloche: cl.actifs.map(x => x.cle), nb: clNb(), badge: p && !p.hidden ? +p.textContent : 0 };
"""


def preparer(nav, url, L, H, mobile):
    nav.taille(L, H, mobile)
    nav.aller(url, 7)
    coupe = nav.js("if (!Son.coupe()) Son.basculer(); return Son.coupe();")
    verifie("--mute-audio" in nav.p.args and coupe is True, f"page muette (Chrome --mute-audio, son du studio coupé : {coupe})")
    nav.js("try { Tuto && Tuto.fermer && Tuto.fermer(); } catch (e) {} document.querySelectorAll('.tuto, #tuto').forEach(x => x.remove()); return true;")
    verifie(bool(EH.attendre(nav, "return DECISIONS.length >= 7;", 15)), "décisions lues depuis le serveur")
    nav.js("Conv.ouvrir(true); return true;")
    return EH.attendre(nav, ETAT_JS, 10)


def controler(e, nom, ouvertes, reglees, futur_hm):
    ids = {c["id"] for c in e["cartes"]}
    verifie(ids == ouvertes, f"{nom} : seules les questions ouvertes ont une carte dans le fil ({sorted(ids)})")
    verifie(not (ids & reglees), f"{nom} : aucune question réglée en carte")
    verifie(set(e["reglees"]) == reglees, f"{nom} : toutes les réglées sont dans le repli ({sorted(e['reglees'])})")
    verifie(e["premier"] == "fil-reglees", f"{nom} : le repli est en tête du fil ({e['premier']})")
    verifie(str(len(reglees)) in e["resume"] and "réglée" in e["resume"], f"{nom} : résumé du repli « {e['resume']} »")
    c = next((x for x in e["cartes"] if x["id"] == "ouverte-futur"), None)
    verifie(c is not None and futur_hm not in c["heure"], f"{nom} : heure future ramenée à maintenant (carte « {c and c['heure']} », futur {futur_hm})")
    verifie(set(e["ouvertes"]) == ouvertes and not ({"dec:" + i for i in reglees} & set(e["cloche"])), f"{nom} : la cloche n'a que les ouvertes ({e['cloche']})")
    verifie(e["badge"] == e["nb"] == len(e["cloche"]), f"{nom} : badge juste ({e['badge']} = {e['nb']} = {len(e['cloche'])})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--captures", default="")
    ap.add_argument("--garder", action="store_true")
    a = ap.parse_args()
    chrome = next((c for c in EH.CHROMES if os.path.isfile(c)), None)
    if not chrome:
        print("Chrome introuvable : essai impossible")
        return 2
    dossier = tempfile.mkdtemp(prefix="essai_questions_")
    futur_dt = datetime.datetime.now() + datetime.timedelta(hours=2, minutes=17)
    futur, futur_hm = futur_dt.strftime("%Y-%m-%dT%H:%M:%S"), futur_dt.strftime("%H:%M")
    projet(dossier, futur)
    if a.captures:
        os.makedirs(a.captures, exist_ok=True)
    s = EH.Serveur(dossier)
    url = f"http://127.0.0.1:{s.port}/studio.html?essai"
    try:
        print("1. PC (1400 × 900), profil neuf")
        nav = EH.Navigateur(chrome)
        try:
            e = preparer(nav, url, 1400, 900, False)
            verifie(bool(e), "conversation ouverte")
            if e:
                controler(e, "PC", OUVERTES, REGLEES, futur_hm)
                # le repli reste ouvert d'un rendu à l'autre
                nav.js("const r = document.getElementById('fil-reglees'); r.open = true; return true;")
                time.sleep(.5)
                nav.js("Conv.ouvrir(true); return true;")
                e2 = EH.attendre(nav, ETAT_JS, 6)
                verifie(bool(e2) and e2["ouvertRepli"], "PC : le repli reste ouvert après un nouveau rendu")
                if a.captures:
                    nav.capture(os.path.join(a.captures, "pc_conversation.png"))
                nb0 = e["nb"]
                ok_clic = nav.js("const b = document.querySelector('#panneau [data-dec=\"a-repondre\"] [data-c=\"a\"]'); if (!b) return false; b.click(); return true;")
                verifie(ok_clic is True, "PC : bouton de réponse dans la carte")
                e3 = EH.attendre(nav, "const e = (() => {" + ETAT_JS + "})(); return e && e.nb < " + str(nb0) + " ? e : null;", 10)
                verifie(bool(e3), "PC : la cloche baisse après la réponse")
                if e3:
                    verifie(e3["nb"] == nb0 - 1 and e3["badge"] == e3["nb"], f"PC : cloche {nb0} -> {e3['nb']}, badge {e3['badge']}")
                    verifie(any(c["id"] == "a-repondre" for c in e3["cartes"]), "PC : la carte répondue reste visible (2 min)")
                rep = lire(os.path.join(dossier, ".studio", "reponses.json"), []) or []
                verifie(any(x.get("id") == "a-repondre" and x.get("choix") == "a" for x in rep), "réponse gardée par le serveur (reponses.json)")
        finally:
            nav.fermer()
        print("2. Téléphone (390 × 844), autre profil neuf : l'état vient du serveur")
        t0 = time.time()
        try:
            import urllib.request
            urllib.request.urlopen(f"http://127.0.0.1:{s.port}/api/qui", timeout=30).read()
            print(f"  (serveur répond en {time.time() - t0:.1f} s)")
        except Exception as x:
            print(f"  (serveur muet : {x!r} après {time.time() - t0:.1f} s)")
        nav = EH.Navigateur(chrome)
        try:
            e = preparer(nav, url, 390, 844, True)
            verifie(bool(e), "téléphone : conversation ouverte")
            if e:
                controler(e, "téléphone", {"ouverte-futur"}, REGLEES | {"a-repondre"}, futur_hm)
                if a.captures:
                    nav.capture(os.path.join(a.captures, "tel_conversation.png"))
                    nav.js("const r = document.getElementById('fil-reglees'); if (r) r.open = true; return true;")
                    time.sleep(.4)
                    nav.capture(os.path.join(a.captures, "tel_conversation_repli.png"))
        finally:
            nav.fermer()
    finally:
        s.arreter()
        if not a.garder:
            shutil.rmtree(dossier, ignore_errors=True)
    print("TOUT EST BON" if not ERREURS else f"{len(ERREURS)} ÉCHEC(S)")
    return 0 if not ERREURS else 1


if __name__ == "__main__":
    sys.exit(main())
