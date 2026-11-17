"""Essai (17/11, retours d'un utilisateur) : cloche groupée et version téléphone, sur PC et au téléphone.

Usage : python -I -B essai_retours_ami.py [--captures <dossier>] [--garder]
  code 0 = tout vert.

Faux projet jetable, vrai serveur_studio.py sur un port libre, Chrome sans tête (son coupé : --mute-audio et son du studio
coupé avant toute interaction ; onglets et Chrome fermés à la fin), profil neuf.
Vérifie :
  Cloche (PC 1400 × 900) : un clic sur un choix le retient seulement (aria-pressed, ✓, bandeau « N choix prêts »), rien
  n'arrive dans reponses.json ; un 2e clic l'enlève ; trois choix retenus partent ensemble à la fermeture (×), en une rafale ;
  un choix retenu survit au rechargement et part à la fermeture suivante (Échap) ; un choix dont la question a disparu
  est oublié ; remplacer la cloche par un autre panneau envoie aussi.
  Téléphone (390 × 844) : rappuyer sur l'onglet ouvert le referme ; 390 × 300 (clavier ouvert, plus large que haut) ne passe
  pas en rail vertical ; menu ⋯ au-dessus du voile ; brouillon gardé (fermer / rouvrir, rechargement), effacé à l'envoi ;
  Entrée va à la ligne (enterkeyhint « enter ») et n'envoie pas ; en-tête de la conversation sur une ligne, croix à droite ;
  bulles jusqu'à 94 % ; au PC, Entrée envoie toujours.
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
_spec = importlib.util.spec_from_file_location("essai_hote", os.path.join(ICI, "essai_hote.py"))
EH = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(EH)

ERREURS = []


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


def projet(dossier):
    st = os.path.join(dossier, ".studio")
    conf = lire(os.path.join(SKILL, "modeles", "studio.config.json"), {}) or {}
    conf.update({"mode": "travail", "nom_projet": "Essai retours", "langue": "fr"})
    ecrire(os.path.join(st, "studio.config.json"), conf)
    ecrire(os.path.join(st, "reglages.json"), {"mode_absent": False})
    hier = (datetime.datetime.now() - datetime.timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%S")
    ecrire(os.path.join(st, "decisions.json"), [
        {"id": f"q{i}", "titre": f"Question {i} ?", "explication": "essai", "choix": ["a", "b"], "recommande": "a",
         "statut": "ouverte", "cree_le": hier} for i in range(1, 6)])
    ecrire(os.path.join(st, "reponses.json"), [])
    return st


def reponses(st):
    return {x.get("id"): x.get("choix") for x in (lire(os.path.join(st, "reponses.json"), []) or []) if isinstance(x, dict)}


def preparer(nav, url, L, H, mobile, attente=7):
    nav.taille(L, H, mobile)
    nav.aller(url, attente)
    coupe = nav.js("if (!Son.coupe()) Son.basculer(); return Son.coupe();")
    verifie(coupe is True, f"page muette ({L} × {H})")
    nav.js("try { Tuto && Tuto.fermer && Tuto.fermer(); } catch (e) {} document.querySelectorAll('.tuto, #tuto').forEach(x => x.remove()); return true;")
    verifie(bool(EH.attendre(nav, "return DECISIONS.length >= 5 || null;", 15)), "décisions lues")


CLIC = "const b = document.querySelector('#pn-corps [data-cl-cle=\"dec:%s\"][data-cl-issue=\"choix:%s\"]'); if (!b) return false; b.click(); return true;"
ETAT_CL = """const p = document.querySelector('#pn-corps .cl-prets');
return { ouvert: Panneau.ouvert(), retenus: __clocheChoix(), prets: p ? p.textContent : '',
  presses: [...document.querySelectorAll('#pn-corps .cl-issue[aria-pressed="true"]')].map(b => b.dataset.clCle + '=' + b.dataset.clIssue),
  coches: document.querySelectorAll('#pn-corps .cl-retenu .cl-coche').length };"""


def essai_cloche(nav, url, st, captures):
    print("1. Cloche : les choix partent ensemble à la fermeture (PC 1400 × 900)")
    preparer(nav, url, 1400, 900, False)
    nav.js("ouvrirCloche(); return true;")
    verifie(bool(EH.attendre(nav, "return document.querySelector('#pn-corps [data-cl-cle=\"dec:q1\"]') ? true : null;", 8)), "cloche ouverte, questions listées")
    for q, c in (("q1", "a"), ("q2", "b"), ("q3", "a")):
        nav.js(CLIC % (q, c))
        time.sleep(.3)
    time.sleep(1.5)
    e = nav.js("return (() => {" + ETAT_CL + "})();")
    verifie(e["retenus"] == {"dec:q1": "choix:a", "dec:q2": "choix:b", "dec:q3": "choix:a"}, f"3 choix retenus ({e['retenus']})")
    verifie(len(e["presses"]) == 3 and e["coches"] == 3, f"marques : aria-pressed et ✓ ({e['presses']}, {e['coches']})")
    verifie("3 choix prêts" in e["prets"] and "fermes la cloche" in e["prets"], f"bandeau « {e['prets']} »")
    verifie(reponses(st) == {}, "rien n'est parti tant que la cloche est ouverte")
    if captures:
        nav.capture(os.path.join(captures, "apres_pc_cloche_choix_retenus.png"))
    nav.js(CLIC % ("q3", "a"))
    time.sleep(.6)
    e = nav.js("return (() => {" + ETAT_CL + "})();")
    verifie("dec:q3" not in e["retenus"] and "2 choix prêts" in e["prets"], f"2e clic : choix enlevé ({e['retenus']})")
    nav.js("document.querySelector('#panneau .x').click(); return true;")
    r = EH.attendre(nav, "return null;", 1)
    t0 = time.time()
    while time.time() - t0 < 10 and len(reponses(st)) < 2:
        time.sleep(.3)
    rep = reponses(st)
    verifie(rep == {"q1": "a", "q2": "b"}, f"fermeture (×) : les 2 choix partent ensemble ({rep})")
    e = nav.js("return __clocheChoix();")
    verifie(e == {}, f"plus rien de retenu après l'envoi ({e})")
    # 2. retenu, rechargement, Échap
    nav.js("ouvrirCloche(); return true;")
    EH.attendre(nav, "return document.querySelector('#pn-corps [data-cl-cle=\"dec:q4\"]') ? true : null;", 8)
    nav.js(CLIC % ("q4", "b"))
    time.sleep(.6)
    nav.aller(url, 7)
    nav.js("if (!Son.coupe()) Son.basculer(); try { Tuto && Tuto.fermer && Tuto.fermer(); } catch (e) {} document.querySelectorAll('.tuto, #tuto').forEach(x => x.remove()); return true;")
    EH.attendre(nav, "return DECISIONS.length >= 5 || null;", 15)
    e = nav.js("return __clocheChoix();")
    verifie(e == {"dec:q4": "choix:b"}, f"rechargement : le choix retenu est gardé ({e})")
    verifie("q4" not in reponses(st), "rechargement : rien n'est parti")
    nav.js("ouvrirCloche(); return true;")
    EH.attendre(nav, "return document.querySelector('#pn-corps .cl-prets') ? true : null;", 8)
    e = nav.js("return (() => {" + ETAT_CL + "})();")
    verifie("1 choix prêt" in e["prets"] and e["presses"] == ["dec:q4=choix:b"], f"rouverte : marque et bandeau ({e['prets']})")
    nav.js("document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); return true;")
    t0 = time.time()
    while time.time() - t0 < 10 and "q4" not in reponses(st):
        time.sleep(.3)
    verifie(reponses(st).get("q4") == "b", "Échap : le choix part")
    # 3. choix d'une question disparue : oublié ; remplacement par un autre panneau : envoi
    nav.js("LS.set('cloche_choix', { 'dec:inconnue': 'choix:a' }); Object.assign(__clocheChoix, {}); return true;")
    nav.aller(url, 7)
    nav.js("if (!Son.coupe()) Son.basculer(); try { Tuto && Tuto.fermer && Tuto.fermer(); } catch (e) {} document.querySelectorAll('.tuto, #tuto').forEach(x => x.remove()); return true;")
    EH.attendre(nav, "return DECISIONS.length >= 5 || null;", 15)
    nav.js("ouvrirCloche(); return true;")
    EH.attendre(nav, "return document.querySelector('#pn-corps [data-cl-cle=\"dec:q5\"]') ? true : null;", 8)
    nav.js(CLIC % ("q5", "a"))
    time.sleep(.5)
    nav.js("ouvrirReglages(); return true;")
    t0 = time.time()
    while time.time() - t0 < 10 and "q5" not in reponses(st):
        time.sleep(.3)
    verifie(reponses(st).get("q5") == "a", "cloche remplacée par les Réglages : le choix part")
    time.sleep(1)
    e = nav.js("return __clocheChoix();")
    verifie(e == {}, f"choix d'une question disparue oublié ({e})")
    nav.js("Panneau.fermer(); return true;")


def essai_pc_entree(nav, url):
    print("2. PC : Entrée envoie toujours la conversation")
    preparer(nav, url, 1400, 900, False, 6)
    nav.js("document.documentElement.dataset.essai = 'sans-envoi'; Conv.ouvrir(true); return true;")
    EH.attendre(nav, "return document.querySelector('#conv-texte') ? true : null;", 6)
    e = nav.js("""const ta = document.querySelector('#conv-texte'); ta.value = 'bonjour PC';
      ta.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true }));
      return { hint: ta.getAttribute('enterkeyhint'), envoi: document.documentElement.dataset.dernierEnvoi || '', reste: ta.value };""")
    verifie(e["hint"] == "send" and "bonjour PC" in e["envoi"] and e["reste"] == "", f"PC : Entrée envoie ({e})")
    nav.js("Panneau.fermer(); return true;")


def essai_telephone(nav, url, captures):
    print("3. Téléphone (390 × 844)")
    preparer(nav, url, 390, 844, True)
    nav.js("document.documentElement.dataset.essai = 'sans-envoi'; return true;")
    onglet = "document.querySelector('#onglets-app [data-onglet=\"%s\"]').click(); return true;"
    nav.js(onglet % "conv")
    verifie(bool(EH.attendre(nav, "return Panneau.ouvert() === 'conv' || null;", 5)), "onglet Conversation : ouvert")
    if captures:
        time.sleep(.8)
        nav.capture(os.path.join(captures, "apres_tel_conversation.png"))
    g = nav.js("""const h = document.querySelector('#panneau.conv-app h2'), x = document.querySelector('#panneau .feuille > .x');
      const rh = h.getBoundingClientRect(), rx = x.getBoundingClientRect(), f = document.querySelector('#panneau .feuille').getBoundingClientRect();
      const lh = parseFloat(getComputedStyle(h).lineHeight) || 22;
      return { hh: rh.height, lignes: Math.round(rh.height / lh), xDroite: f.right - rx.right, xHaut: rx.top - f.top, memeRangee: Math.abs((rx.top + rx.bottom) / 2 - (rh.top + rh.bottom) / 2) };""")
    verifie(g["hh"] <= 48 and g["xDroite"] <= 24 and g["memeRangee"] <= 14, f"en-tête sur une ligne, croix à droite ({g})")
    # bulles et marges
    nav.js("Conv.envoye('essai-1', 'assistant', 'Un long message de test pour mesurer la largeur de la bulle de la conversation au téléphone, il doit prendre presque toute la largeur.'); return true;")
    time.sleep(.6)
    b = nav.js("""const m = document.querySelector('#panneau [data-fil] .msg.moi'); const f = document.querySelector('#panneau [data-fil]');
      if (!m) return null; return { mw: getComputedStyle(m).maxWidth, part: m.getBoundingClientRect().width / f.clientWidth,
      pad: parseFloat(getComputedStyle(document.querySelector('#panneau .feuille')).paddingLeft) };""")
    verifie(b and b["mw"] == "94%" and b["pad"] <= 9, f"bulles 94 %, marges 8 px ({b})")
    # Entrée au téléphone, brouillon
    e = nav.js("""const ta = document.querySelector('#conv-texte'); ta.focus(); ta.value = 'ligne 1'; ta.dispatchEvent(new Event('input', { bubbles: true }));
      const ev = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true }); ta.dispatchEvent(ev);
      return { hint: ta.getAttribute('enterkeyhint'), empeche: ev.defaultPrevented, envoi: document.documentElement.dataset.dernierEnvoi || '' };""")
    verifie(e["hint"] == "enter" and not e["empeche"] and not e["envoi"], f"Entrée ne fait qu'aller à la ligne ({e})")
    nav.js("document.activeElement && document.activeElement.blur(); " + onglet % "conv")
    time.sleep(.6)
    verifie(nav.js("return Panneau.ouvert();") is None, "rappuyer sur l'onglet Conversation le referme")
    a = nav.js("return document.querySelector('#onglets-app button.actif') && document.querySelector('#onglets-app button.actif').dataset.onglet;")
    verifie(a == "equipe", f"retour à la vue de l'équipe (onglet actif : {a})")
    nav.js(onglet % "conv")
    EH.attendre(nav, "return document.querySelector('#conv-texte') ? true : null;", 5)
    verifie(nav.js("return document.querySelector('#conv-texte').value;") == "ligne 1", "brouillon gardé après fermer / rouvrir")
    nav.aller(url, 7)
    nav.js("if (!Son.coupe()) Son.basculer(); document.documentElement.dataset.essai = 'sans-envoi'; document.querySelectorAll('.tuto, #tuto').forEach(x => x.remove()); Conv.ouvrir(true); return true;")
    EH.attendre(nav, "return document.querySelector('#conv-texte') ? true : null;", 6)
    verifie(nav.js("return document.querySelector('#conv-texte').value;") == "ligne 1", "brouillon gardé après un rechargement")
    nav.js("document.querySelector('#panneau [data-envoyer]').click(); return true;")
    time.sleep(.5)
    e = nav.js("return { envoi: document.documentElement.dataset.dernierEnvoi || '', reste: document.querySelector('#conv-texte').value, ls: LS.get('conv_brouillon', '') };")
    verifie("ligne 1" in e["envoi"] and e["reste"] == "" and not e["ls"], f"« Envoyer » envoie et efface le brouillon ({e})")
    # rappuyer sur la cloche
    nav.js(onglet % "cloche")
    time.sleep(.6)
    nav.js(onglet % "cloche")
    time.sleep(.6)
    verifie(nav.js("return Panneau.ouvert();") is None, "rappuyer sur l'onglet Cloche la referme")
    # petite fenêtre « Écrire à l'assistant »
    e = nav.js("""if (typeof ouvrirChat !== 'function') return null; ouvrirChat(); const ta = document.querySelector('#chat-texte'); ta.value = 'x';
      const ev = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true }); ta.dispatchEvent(ev);
      const r = { hint: ta.getAttribute('enterkeyhint'), empeche: ev.defaultPrevented }; document.querySelector('#chat-fermer').click(); return r;""")
    verifie(e and e["hint"] == "enter" and not e["empeche"], f"« Écrire à l'assistant » : Entrée va à la ligne ({e})")
    # menu ⋯ au-dessus du voile
    nav.js("document.getElementById('bt-plus-app').click(); return true;")
    time.sleep(.5)
    m = nav.js("""const b = [...document.querySelectorAll('#entete nav.outils .bt')].find(x => x.offsetParent !== null); if (!b) return null;
      const r = b.getBoundingClientRect(), el = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return { dessus: !!el && (el === b || b.contains(el)), sous: el ? (el.id || el.className) : '' };""")
    verifie(m and m["dessus"], f"menu ⋯ : le bouton est au-dessus du voile ({m})")
    if captures:
        nav.capture(os.path.join(captures, "apres_tel_menu.png"))
    nav.js("document.getElementById('voile-actions').click(); return true;")
    # clavier ouvert : 390 × 300 (plus large que haut)
    nav.taille(390, 300, True)
    time.sleep(1)
    r = nav.js("const o = document.getElementById('onglets-app').getBoundingClientRect(); return { l: o.width, h: o.height, app: document.body.classList.contains('app') };")
    verifie(r["app"] and r["l"] > 300, f"390 × 300 : pas de rail vertical, barre du bas gardée ({r})")
    nav.taille(844, 390, True)
    time.sleep(1)
    r = nav.js("const o = document.getElementById('onglets-app').getBoundingClientRect(); return { l: o.width, h: o.height };")
    verifie(r["l"] < 120, f"vrai téléphone couché (844 × 390) : rail vertical gardé ({r})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--captures", default="")
    ap.add_argument("--garder", action="store_true")
    a = ap.parse_args()
    chrome = next((c for c in EH.CHROMES if os.path.isfile(c)), None)
    if not chrome:
        print("Chrome introuvable : essai impossible")
        return 2
    dossier = tempfile.mkdtemp(prefix="essai_retours_")
    st = projet(dossier)
    if a.captures:
        os.makedirs(a.captures, exist_ok=True)
    s = EH.Serveur(dossier)
    url = f"http://127.0.0.1:{s.port}/studio.html?essai"
    try:
        nav = EH.Navigateur(chrome)
        try:
            essai_cloche(nav, url, st, a.captures)
            essai_pc_entree(nav, url)
        finally:
            nav.fermer()
        nav = EH.Navigateur(chrome)
        try:
            essai_telephone(nav, url, a.captures)
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
