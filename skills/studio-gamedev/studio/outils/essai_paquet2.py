"""Essai du paquet 2 (bibliothèque standard, sans navigateur) : pièces jointes de la conversation, onglet « Modèles »,
auditeur facultatif. Projet jetable dans un dossier temporaire, vrai serveur sur un port libre, tout est effacé à la fin.

Usage : python -I -B essai_paquet2.py [--garder]      code 0 = tout vert

Vérifie :
- /api/piece : nom nettoyé (accents, espaces, dossier), doublon renommé, type refusé (415), contenu qui ne ressemble pas
  au format annoncé (415), 10 pièces au plus (413), retrait (/api/piece_retirer) ;
- /api/demande avec « brouillon » : pièces rangées dans .studio/demandes_vocales/pieces/<id du message>/, chemins absolus
  listés dans la demande (« pieces » et fin du texte), aucune demande ni fichier temporaire laissé, brouillon vidé ;
  pièces servies au fil : .log en texte brut, .zip en téléchargement (attachment), brouillons jamais servis ; HEAD : 200 sans
  corps si la pièce est là, 404 sinon, 405 sur /api/ ;
  brouillon réutilisé : 410 ; message sans texte mais avec pièces : accepté ; studio_etat.py montre les pièces (etat.json) ;
- cibles spéciales : « auditeur » refusé tant que le réglage est coupé (403), puis demande avec périmètre, modèle, effort et
  consigne ; périmètre inconnu : 400 ; « controleur-modeles » : consigne avec la commande pour le bon port ;
  optimisation : pas de contrôle des modèles avant la quête (réglage absent), puis consigne du contrôle discret (ajoutée à celle de l'auditeur, sans l'écraser), absente quand
  « controle_modeles » est coupé ; brouillon vidé envoyé sans texte : 400 ;
- /api/demande_annuler : demande à l'auditeur annulée (statut « annulee »), deux fois sans effet, autres cibles 403, inconnue 404 ;
  etat.json garde la dernière demande à l'auditeur et au contrôleur même hors des 40 derniers messages ;
- /api/modele : frontmatter model:/effort: d'une définition d'agent (fins de ligne CRLF gardées, reste intact, effort retiré
  avec ""), fiche de la recrue, poste de la config et auditeur dans reglages.json, journal .studio/modeles_journal.json,
  refus (agent inconnu 404, modèle inconnu 400, rien à changer 400) ; GET /api/modeles.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(ICI)
sys.dont_write_bytecode = True
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
PORTS_INTERDITS = {8790, 8765, 8766, 8810, 8901, 8902}
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40
ECHECS = []


def ok(cond, quoi):
    print(("  ok   " if cond else "  ÉCHEC ") + quoi)
    if not cond:
        ECHECS.append(quoi)


def port_libre():
    for p in range(8920, 8990):
        if p in PORTS_INTERDITS:
            continue
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise SystemExit("aucun port libre")


def ecrire(chemin, donnees):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=1)


def lire(chemin, defaut=None):
    try:
        with open(chemin, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defaut


def main():
    garder = "--garder" in sys.argv
    d = tempfile.mkdtemp(prefix="essai_paquet2_")
    st = os.path.join(d, ".studio")
    port = port_libre()
    base = f"http://127.0.0.1:{port}"
    ecrire(os.path.join(st, "studio.config.json"), {"version": 1, "mode": "travail", "nom_projet": "Essai P2", "langue": "fr", "port": port,
                                                    "dossier_agents": ".claude/agents",
                                                    "postes": [{"id": "direction", "nom": "Direction", "role": "Coordinateur"},
                                                               {"id": "code", "nom": "Code", "role": "Code"}]})
    ecrire(os.path.join(st, "recrues", "narration.json"), {"nom": "narration", "nom_affiche": "Narration", "role": "Histoire", "mission": "x"})
    ecrire(os.path.join(st, "recrues", "index.json"), ["narration"])
    agents = os.path.join(d, ".claude", "agents")
    os.makedirs(agents)
    md = os.path.join(agents, "narration.md")
    with open(md, "wb") as f:
        f.write(b'---\r\nname: narration\r\ndescription: "Histoire"\r\ntools: Read\r\nmodel: sonnet\r\n---\r\n<!-- studio-gamedev : recrue -->\r\n\r\nTu es Narration.\r\n')
    srv = subprocess.Popen([sys.executable, "-I", "-B", os.path.join(STUDIO, "serveur_studio.py"), "--projet", d, "--port", str(port)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    def appel(route, corps=None, brut=None, type_="application/json", methode="POST"):
        donnees = brut if brut is not None else (json.dumps(corps).encode("utf-8") if corps is not None else None)
        req = urllib.request.Request(base + route, data=donnees, method=methode,
                                     headers={"Content-Type": type_, "Origin": base} if methode == "POST" else {})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read().decode("utf-8"))
            except Exception:
                return e.code, {}

    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(base + "/api/qui", timeout=1)
                break
            except Exception:
                time.sleep(.2)
        print("pièces jointes")
        b = "a1b2c3d4e5f6a7b8"
        s, r = appel(f"/api/piece?brouillon={b}&nom=" + urllib.request.quote("C:\\dossier\\Été capture.PNG"), brut=PNG, type_="image/png")
        ok(s == 200 and r.get("nom") == "Ete_capture.png", f"nom nettoyé : {r.get('nom')}")
        s, r = appel(f"/api/piece?brouillon={b}&nom=Ete_capture.png", brut=PNG, type_="image/png")
        ok(s == 200 and r.get("nom") == "Ete_capture-2.png", f"doublon renommé : {r.get('nom')}")
        s, r = appel(f"/api/piece?brouillon={b}&nom=notes.txt", brut="bonjour\n".encode("utf-8"), type_="text/plain")
        ok(s == 200, "texte accepté")
        s, r = appel(f"/api/piece?brouillon={b}&nom=virus.exe", brut=b"MZ....", type_="application/octet-stream")
        ok(s == 415, f"type refusé ({s})")
        s, r = appel(f"/api/piece?brouillon={b}&nom=faux.png", brut=b"pas une image du tout", type_="image/png")
        ok(s == 415, f"faux PNG refusé ({s})")
        s, r = appel("/api/piece?brouillon=../x&nom=a.png", brut=PNG, type_="image/png")
        ok(s == 400, f"brouillon invalide refusé ({s})")
        s, r = appel("/api/piece_retirer", {"brouillon": b, "nom": "Ete_capture-2.png"})
        ok(s == 200 and not os.path.exists(os.path.join(st, "demandes_vocales", "pieces", "_brouillons", b, "Ete_capture-2.png")), "pièce retirée")
        s, r = appel("/api/piece_retirer", {"brouillon": b, "nom": "../studio.config.json"})
        ok(s == 400, f"retrait hors du brouillon refusé ({s})")
        b2 = "f0e1d2c3b4a59687"
        n_ok = sum(1 for i in range(11) if appel(f"/api/piece?brouillon={b2}&nom=p{i}.txt", brut=b"x", type_="text/plain")[0] == 200)
        ok(n_ok == 10, f"10 pièces au plus par message ({n_ok} acceptées)")
        s, r = appel("/api/demande", {"cible": "assistant", "texte": "Regarde ça", "via": "ecrit", "brouillon": b})
        ok(s == 200 and len(r.get("pieces") or []) == 2, f"demande avec 2 pièces ({s}, {len(r.get('pieces') or [])})")
        ident = r.get("id", "")
        dem = lire(os.path.join(st, "demandes_vocales", ident + ".json"), {})
        final = os.path.join(st, "demandes_vocales", "pieces", ident)
        ok(all(os.path.isabs(x) and os.path.isfile(x) and os.path.dirname(x) == os.path.abspath(final) for x in dem.get("pieces") or []) and len(dem.get("pieces") or []) == 2,
           "pièces rangées à côté du message, chemins absolus listés")
        ok("Pièces jointes (2) :" in dem.get("texte", "") and all(x in dem["texte"] for x in dem.get("pieces") or []), "chemins aussi à la fin du texte (pour Claude)")
        ok(not os.path.exists(os.path.join(st, "demandes_vocales", "pieces", "_brouillons", b)), "brouillon vidé")
        ok(not [f for f in os.listdir(os.path.join(st, "demandes_vocales")) if f.endswith(".tmp")], "aucun fichier temporaire")
        s, r = appel("/api/demande", {"cible": "assistant", "texte": "encore", "via": "ecrit", "brouillon": b})
        ok(s == 410, f"brouillon déjà envoyé : 410 ({s})")
        s, r = appel("/api/demande", {"cible": "assistant", "texte": "", "via": "ecrit", "brouillon": b2})
        ok(s == 200 and len(r.get("pieces") or []) == 10, f"pièces sans texte acceptées ({s})")
        s, r = appel("/api/demande", {"cible": "assistant", "texte": "", "via": "ecrit"})
        ok(s == 400, f"ni texte ni pièce : 400 ({s})")
        b3 = "0a1b2c3d4e5f6a7b"
        appel(f"/api/piece?brouillon={b3}&nom=seul.txt", brut=b"x", type_="text/plain")
        appel("/api/piece_retirer", {"brouillon": b3, "nom": "seul.txt"})
        n_av = len(os.listdir(os.path.join(st, "demandes_vocales")))
        s, r = appel("/api/demande", {"cible": "assistant", "texte": "", "via": "ecrit", "brouillon": b3})
        ok(s == 400 and len(os.listdir(os.path.join(st, "demandes_vocales"))) == n_av, f"brouillon vidé et texte vide : 400, rien déposé ({s})")
        subprocess.call([sys.executable, "-I", "-B", os.path.join(STUDIO, "studio_etat.py"), "--projet", d, "--une-fois"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        msg = [m for m in (lire(os.path.join(st, "etat.json"), {}) or {}).get("messages") or [] if m.get("id") == ident]
        ok(bool(msg) and sorted(msg[0].get("pieces") or []) == ["Ete_capture.png", "notes.txt"], "etat.json : pièces du message (noms)")
        s, _ = (urllib.request.urlopen(f"{base}/demandes_vocales/pieces/{ident}/Ete_capture.png").status, None)
        ok(s == 200, "vignette servie au fil")
        b4 = "1a2b3c4d5e6f7a8b"
        appel(f"/api/piece?brouillon={b4}&nom=journal.log", brut=b"ligne 1\n<script>x</script>\n", type_="text/plain")
        appel(f"/api/piece?brouillon={b4}&nom=archive.zip", brut=b"PK\x03\x04" + b"\x00" * 30, type_="application/zip")
        s, r = appel("/api/demande", {"cible": "assistant", "texte": "Deux fichiers", "via": "ecrit", "brouillon": b4})
        id4 = r.get("id", "")

        def tete(chemin, methode="GET"):
            try:
                with urllib.request.urlopen(urllib.request.Request(base + chemin, method=methode), timeout=10) as rr:
                    return rr.status, dict(rr.headers), rr.read()
            except urllib.error.HTTPError as e:
                return e.code, dict(e.headers), e.read()
        s, h, c = tete(f"/demandes_vocales/pieces/{id4}/journal.log")
        ok(s == 200 and h.get("Content-Type", "").startswith("text/plain") and h.get("X-Content-Type-Options") == "nosniff", f"pièce .log servie en texte brut ({s}, {h.get('Content-Type')})")
        s, h, c = tete(f"/demandes_vocales/pieces/{id4}/archive.zip")
        ok(s == 200 and h.get("Content-Type") == "application/octet-stream" and h.get("Content-Disposition") == "attachment", f"pièce .zip servie en téléchargement ({s}, {h.get('Content-Disposition')})")
        s, h, c = tete(f"/demandes_vocales/pieces/{id4}/archive.zip", "HEAD")
        ok(s == 200 and c == b"" and h.get("Content-Length") == "34", f"HEAD : pièce présente, sans corps ({s}, {h.get('Content-Length')})")
        s, h, c = tete(f"/demandes_vocales/pieces/{id4}/absent.log", "HEAD")
        ok(s == 404 and c == b"", f"HEAD : pièce absente, 404 ({s})")
        ok(tete("/api/modeles", "HEAD")[0] == 405, "HEAD sur une route /api/ : 405")
        b5 = "9a8b7c6d5e4f3a2b"
        appel(f"/api/piece?brouillon={b5}&nom=brouillon.zip", brut=b"PK\x03\x04" + b"\x00" * 30, type_="application/zip")
        ok(tete(f"/demandes_vocales/pieces/_brouillons/{b5}/brouillon.zip")[0] == 404, "brouillon jamais servi")
        os.makedirs(os.path.join(st, "demandes_vocales", "x"), exist_ok=True)
        with open(os.path.join(st, "demandes_vocales", "x", "a.zip"), "wb") as f:
            f.write(b"PK\x03\x04")
        ok(tete("/demandes_vocales/x/a.zip")[0] == 404, "type de pièce servi seulement dans pieces/<id>/")

        print("auditeur et contrôleur des modèles")
        s, r = appel("/api/demande", {"cible": "auditeur", "texte": "Audit", "via": "ecrit"})
        ok(s == 403, f"auditeur coupé : 403 ({s})")
        appel("/api/reglages", {"auditeur": True})
        appel("/api/modele", {"id": "auditeur", "modele": "opus", "effort": "high"})
        s, r = appel("/api/demande", {"cible": "auditeur", "texte": "Audit", "via": "ecrit", "perimetre": ["projet", "studio"]})
        dem = lire(os.path.join(st, "demandes_vocales", r.get("id", "") + ".json"), {})
        ok(s == 200 and dem.get("perimetre") == ["projet", "studio"] and dem.get("modele") == "opus" and dem.get("effort") == "high"
           and "audit.json" in dem.get("consigne", "") and "opus" in dem.get("consigne", ""), "demande d'audit : périmètre, modèle, effort, consigne")
        s, r = appel("/api/demande", {"cible": "auditeur", "texte": "Audit 2", "via": "ecrit", "perimetre": ["tout"]})
        ok(s == 400, f"périmètre inconnu : 400 ({s})")
        s, r = appel("/api/demande", {"cible": "controleur-modeles", "texte": "Le bon modèle pour chacun", "via": "ecrit"})
        dem = lire(os.path.join(st, "demandes_vocales", r.get("id", "") + ".json"), {})
        ok(s == 200 and f"http://127.0.0.1:{port}/api/modele" in dem.get("consigne", "") and "ultracode" in dem.get("consigne", ""), "contrôleur : consigne et commande au bon port")
        s, r = appel("/api/demande", {"cible": "assistant", "texte": "Optimiser (avant la quête)", "via": "ecrit", "sujet": "optimisation"})
        dem = lire(os.path.join(st, "demandes_vocales", r.get("id", "") + ".json"), {})
        ok(s == 200 and "controle_modeles" not in dem.get("consigne", ""), "optimisation : contrôleur des modèles pas encore arrivé (quête), pas de contrôle")
        for f in os.listdir(os.path.join(st, "demandes_vocales")):          # la garde des 30 min ne compte pas pour l'essai
            c = os.path.join(st, "demandes_vocales", f)
            x = lire(c, None) if f.endswith(".json") else None
            if isinstance(x, dict) and x.get("sujet") == "optimisation":
                x["sujet"] = "optimisation_essai"
                ecrire(c, x)
        appel("/api/reglages", {"controle_modeles": True})                  # la quête Q-SU-02 acceptée l'allume
        s, r = appel("/api/demande", {"cible": "assistant", "texte": "Optimiser", "via": "ecrit", "sujet": "optimisation"})
        dem = lire(os.path.join(st, "demandes_vocales", r.get("id", "") + ".json"), {})
        ok(s == 200 and "controle_modeles" in dem.get("consigne", ""), "optimisation : contrôle discret des modèles")
        for f in os.listdir(os.path.join(st, "demandes_vocales")):          # la garde des 30 min ne compte pas pour l'essai
            c = os.path.join(st, "demandes_vocales", f)
            x = lire(c, None) if f.endswith(".json") else None
            if isinstance(x, dict) and x.get("sujet") == "optimisation":
                x["sujet"] = "optimisation_essai"
                ecrire(c, x)
        s, r = appel("/api/demande", {"cible": "auditeur", "texte": "Audit et optimisation", "via": "ecrit", "sujet": "optimisation", "perimetre": ["studio"]})
        dem = lire(os.path.join(st, "demandes_vocales", r.get("id", "") + ".json"), {})
        ok(s == 200 and "audit.json" in dem.get("consigne", "") and "controle_modeles" in dem.get("consigne", "") and dem.get("perimetre") == ["studio"] and dem.get("modele") == "opus",
           "optimisation + auditeur : consigne complétée, pas écrasée")
        aud_id = r.get("id", "")
        s, r = appel("/api/demande_annuler", {"id": aud_id})
        ok(s == 200 and (lire(os.path.join(st, "demandes_vocales", aud_id + ".json"), {}) or {}).get("statut") == "annulee", f"demande d'audit annulée ({s})")
        s, r = appel("/api/demande_annuler", {"id": aud_id})
        ok(s == 200 and r.get("deja") is True, "annulée deux fois : rien ne change")
        ok(appel("/api/demande_annuler", {"id": ident})[0] == 403, "message à l'assistant : pas annulable ici (403)")
        ok(appel("/api/demande_annuler", {"id": "20990101-000000-000abcd_auditeur"})[0] == 404, "demande inconnue : 404")
        ok(appel("/api/demande_annuler", {"id": "../reglages"})[0] == 400, "id invalide : 400")
        appel("/api/reglages", {"controle_modeles": False})
        for f in os.listdir(os.path.join(st, "demandes_vocales")):          # la garde des 30 min ne compte pas pour l'essai
            c = os.path.join(st, "demandes_vocales", f)
            x = lire(c, None) if f.endswith(".json") else None
            if isinstance(x, dict) and x.get("sujet") == "optimisation":
                x["sujet"] = "optimisation_essai"
                ecrire(c, x)
        s, r = appel("/api/demande", {"cible": "assistant", "texte": "Optimiser encore", "via": "ecrit", "sujet": "optimisation"})
        dem = lire(os.path.join(st, "demandes_vocales", r.get("id", "") + ".json"), {})
        ok(s == 200 and "consigne" not in dem, "contrôle discret coupé : pas de consigne")

        print("modèles")
        s, r = appel("/api/modele", {"id": "narration", "modele": "opus", "effort": "high", "raison": "histoire longue"})
        brut = open(md, "rb").read()
        ok(s == 200 and b"model: opus\r\neffort: high\r\n" in brut and b"\r\nTu es Narration.\r\n" in brut and b"\n" not in brut.replace(b"\r\n", b""), "frontmatter écrit, CRLF gardé, reste intact")
        ok((lire(os.path.join(st, "recrues", "narration.json"), {}) or {}).get("modele") == "opus", "fiche de la recrue suivie")
        s, r = appel("/api/modele", {"id": "narration", "effort": ""})
        ok(s == 200 and b"effort:" not in open(md, "rb").read() and r["apres"]["effort"] is None, "effort retiré (par défaut)")
        s, r = appel("/api/modele", {"id": "direction", "modele": "fable", "effort": "max"})
        rg = lire(os.path.join(st, "reglages.json"), {}) or {}
        ok(s == 200 and rg.get("modeles_postes", {}).get("direction") == "fable" and rg.get("efforts_postes", {}).get("direction") == "max", "poste de la config : reglages.json")
        ok(s == 200 and r["avant"]["modele"] == "sonnet", "avant : modèle par défaut (sonnet)")
        ok(appel("/api/modele", {"id": "inconnu", "modele": "opus"})[0] == 404, "agent inconnu : 404")
        ok(appel("/api/modele", {"id": "code", "modele": "gpt"})[0] == 400, "modèle inconnu : 400")
        ok(appel("/api/modele", {"id": "code"})[0] == 400, "rien à changer : 400")
        ok(appel("/api/modele", {"id": "code", "modele": "haiku", "par": "pirate"})[0] == 400, "« par » inconnu : 400")
        j = lire(os.path.join(st, "modeles_journal.json"), []) or []
        ok(len(j) == 4 and j[1]["agent"] == "narration" and j[1]["raison"] == "histoire longue" and j[1]["fiche"] == ".claude/agents/narration.md", f"journal des modèles ({len(j)} lignes)")
        dv = os.path.join(st, "demandes_vocales")
        for i in range(45):                                                  # 45 messages plus récents que la demande d'audit
            ecrire(os.path.join(dv, f"20990101-0000{i:02d}-000abcd_assistant.json"), {"id": f"20990101-0000{i:02d}-000abcd_assistant", "cible": "assistant", "texte": f"m{i}", "statut": "nouvelle"})
        subprocess.call([sys.executable, "-I", "-B", os.path.join(STUDIO, "studio_etat.py"), "--projet", d, "--une-fois"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        msgs = (lire(os.path.join(st, "etat.json"), {}) or {}).get("messages") or []
        ok(any(m.get("id") == aud_id and m.get("statut") == "annulee" for m in msgs) and any(m.get("cible") == "controleur-modeles" for m in msgs) and len(msgs) == 42,
           f"etat.json : dernière demande à l'auditeur et au contrôleur gardée hors des 40 derniers ({len(msgs)})")
        s, r = appel("/api/modeles", methode="GET")
        ok(s == 200 and r.get("fiches", {}).get("narration", {}).get("modele") == "opus" and r.get("postes", {}).get("modeles", {}).get("direction") == "fable"
           and len(r.get("journal") or []) == 4 and r.get("controle_modeles") is False, "GET /api/modeles")
    finally:
        srv.terminate()
        try:
            err = srv.communicate(timeout=10)[1].decode("utf-8", "replace")
        except Exception:
            err = ""
        ok("Traceback" not in err and "erreur interne" not in err, "serveur : aucune erreur interne")
        if not garder:
            shutil.rmtree(d, ignore_errors=True)
        else:
            print("projet gardé :", d)
    print("OK : tout est vert" if not ECHECS else f"ÉCHEC : {len(ECHECS)} point(s)")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
