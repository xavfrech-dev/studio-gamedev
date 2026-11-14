"""Cloche du studio : déposer ce qui attend l'utilisateur, pour qu'il le règle d'un clic (Python standard uniquement).

Studios jumeaux : ce fichier a un jumeau dans l'autre studio (ici : studio/outils/cloche.py). Dossier visé : --dossier <dossier des fichiers du studio> ; sinon, avec
--projet <projet>, <projet>/.studio ; sinon le dossier de ce script s'il contient decisions.json ou etat.json.

  python -I cloche.py afaire  --id fab-arbres --titre "Ajouter le pack d'arbres depuis Fab" --genre fab --lien https://www.fab.com/… [--detail …] [--option id=libellé …] [--recommande id]
  python -I cloche.py depense --id tripo-credits --question "Racheter 1000 crédits Tripo ?" --montant 10 --service Tripo --pourquoi "…" [--devise €]
  python -I cloche.py attend  --cle <clé de demandes/statuts.json> --question "Je garde l'ancien ciel ou le nouveau ?"
  python -I cloche.py fait    --id fab-arbres             (à-faire réglé : il quitte la cloche)
  python -I cloche.py liste                                (ce qui attend encore, en JSON)

Où ça va :
  afaire  -> a_faire.json         [{id, titre, detail, genre: fab|reconnexion|ecoute|autre, lien, options, recommande, statut: a_faire, cree_le}]
                                   la réponse arrive dans reponses.json avec l'id « afaire:<id> » : agis, puis « fait ».
  depense -> decisions.json       décision « ouverte » avec depense {montant, devise, service, pourquoi} : jamais d'étoile,
                                   rien n'est dépensé sans « J'accepte » (réponse dans reponses.json, id de la décision).
  attend  -> demandes/statuts.json statut « attend_utilisateur » + question : « <agent> attend ta réponse » sous la cloche.
                                   Repasse le statut à « lancé » ou « fini » dès que la réponse est là.
Écriture atomique ; rien n'est effacé ; une entrée de même id est remplacée.
"""
import argparse
import json
import os
import sys
import tempfile
import time

GENRES = ("fab", "reconnexion", "ecoute", "autre")


def maintenant():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def lire(chemin, defaut):
    try:
        with open(chemin, encoding="utf-8-sig") as f:
            return json.load(f)
    except FileNotFoundError:
        return defaut
    except Exception as e:
        sys.exit(f"{chemin} illisible ({e}) : rien n'est écrit")


def ecrire(chemin, donnees):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(chemin), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=1)
    for essai in range(6):
        try:
            os.replace(tmp, chemin)
            return
        except PermissionError:
            time.sleep(0.15 * (essai + 1))
    os.replace(tmp, chemin)


def dossier(a):
    if a.dossier:
        return a.dossier
    if a.projet:
        return os.path.join(a.projet, ".studio")
    ici = os.path.dirname(os.path.abspath(__file__))
    if any(os.path.exists(os.path.join(ici, x)) for x in ("decisions.json", "etat.json")):
        return ici
    sys.exit("dossier du studio inconnu : --dossier <dossier> ou --projet <projet>")


def liste_de(v, cle):
    return v if isinstance(v, list) else (v.get(cle) if isinstance(v, dict) and isinstance(v.get(cle), list) else [])


def options(brut):
    out = []
    for o in brut or []:
        i, _, l = o.partition("=")
        if not i.strip():
            sys.exit(f"option invalide : {o!r} (forme id=libellé)")
        out.append({"id": i.strip(), "libelle": (l or i).strip()})
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description="Déposer ce qui attend l'utilisateur sous la cloche du studio.")
    p.add_argument("--dossier")
    p.add_argument("--projet")
    s = p.add_subparsers(dest="quoi", required=True)
    a = s.add_parser("afaire")
    a.add_argument("--id", required=True)
    a.add_argument("--titre", required=True)
    a.add_argument("--detail", default="")
    a.add_argument("--genre", choices=GENRES, default="autre")
    a.add_argument("--lien", default="")
    a.add_argument("--option", action="append")
    a.add_argument("--recommande", default="")
    d = s.add_parser("depense")
    d.add_argument("--id", required=True)
    d.add_argument("--question", required=True)
    d.add_argument("--montant", required=True)
    d.add_argument("--devise", default="€")
    d.add_argument("--service", required=True)
    d.add_argument("--pourquoi", required=True)
    d.add_argument("--contexte", default="")
    t = s.add_parser("attend")
    t.add_argument("--cle", required=True)
    t.add_argument("--question", required=True)
    f = s.add_parser("fait")
    f.add_argument("--id", required=True)
    s.add_parser("liste")
    a_ = p.parse_args(argv)
    racine = dossier(a_)
    af_ch, dec_ch, st_ch = (os.path.join(racine, "a_faire.json"), os.path.join(racine, "decisions.json"),
                            os.path.join(racine, "demandes", "statuts.json"))
    if a_.quoi == "afaire":
        if a_.lien and not a_.lien.startswith(("https://", "http://")):
            sys.exit("lien : http(s) seulement")
        l = [x for x in liste_de(lire(af_ch, []), "a_faire") if isinstance(x, dict) and x.get("id") != a_.id]
        e = {"id": a_.id, "titre": a_.titre, "detail": a_.detail, "genre": a_.genre, "statut": "a_faire", "cree_le": maintenant()}
        if a_.lien:
            e["lien"] = a_.lien
        o = options(a_.option)
        if o:
            e["options"] = o
            if a_.recommande:
                if a_.recommande not in [x["id"] for x in o]:
                    sys.exit("--recommande doit être l'id d'une --option")
                e["recommande"] = a_.recommande
        ecrire(af_ch, l + [e])
        print(json.dumps({"ok": True, "a_faire": e}, ensure_ascii=False))
    elif a_.quoi == "depense":
        brut = lire(dec_ch, [])
        l = [x for x in liste_de(brut, "decisions") if not (isinstance(x, dict) and x.get("id") == a_.id)]
        try:
            m = float(str(a_.montant).replace(",", "."))
        except ValueError:
            sys.exit("--montant : un nombre")
        e = {"id": a_.id, "question": a_.question, "titre": a_.question, "contexte": a_.contexte or a_.pourquoi,
             "explication": a_.contexte or a_.pourquoi, "type": "depense",
             "depense": {"montant": int(m) if m == int(m) else m, "devise": a_.devise, "service": a_.service, "pourquoi": a_.pourquoi},
             "options": [{"id": "accepter", "libelle": "J'accepte la dépense"}, {"id": "refuser", "libelle": "Je refuse"}],
             "statut": "ouverte", "cree_le": maintenant()}
        ecrire(dec_ch, (dict(brut, decisions=l + [e]) if isinstance(brut, dict) else l + [e]))
        print(json.dumps({"ok": True, "decision": e}, ensure_ascii=False))
    elif a_.quoi == "attend":
        st = lire(st_ch, {})
        if not isinstance(st, dict):
            sys.exit("statuts.json n'est pas un objet : rien n'est écrit")
        v = st.get(a_.cle) if isinstance(st.get(a_.cle), dict) else {}
        st[a_.cle] = dict(v, statut="attend_utilisateur", question=a_.question, maj=maintenant())
        ecrire(st_ch, st)
        print(json.dumps({"ok": True, "statut": {a_.cle: st[a_.cle]}}, ensure_ascii=False))
    elif a_.quoi == "fait":
        brut = lire(af_ch, [])
        l = liste_de(brut, "a_faire")
        trouve = False
        for x in l:
            if isinstance(x, dict) and x.get("id") == a_.id:
                x["statut"], x["fait_le"], trouve = "fait", maintenant(), True
        if not trouve:
            sys.exit(f"à-faire « {a_.id} » introuvable")
        ecrire(af_ch, dict(brut, a_faire=l) if isinstance(brut, dict) else l)
        print(json.dumps({"ok": True}, ensure_ascii=False))
    else:
        af = [x for x in liste_de(lire(af_ch, []), "a_faire") if isinstance(x, dict) and x.get("statut", "a_faire") not in ("fait", "annule")]
        dec = [x for x in liste_de(lire(dec_ch, []), "decisions") if isinstance(x, dict) and x.get("statut", "ouverte") == "ouverte"]
        st = lire(st_ch, {})
        att = {k: v for k, v in (st.items() if isinstance(st, dict) else []) if isinstance(v, dict) and str(v.get("statut", "")).startswith("attend_")}
        print(json.dumps({"a_faire": af, "decisions_ouvertes": len(dec), "depenses": [x for x in dec if x.get("depense") or x.get("type") == "depense"],
                          "agents_qui_attendent": att}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
