"""Installe (ou retire) le crochet « Stop » du studio dans <projet>/.claude/settings.local.json.

Usage (seulement avec l'accord de l'utilisateur) :
  python -I -B installer_crochet.py --projet <projet>            installe (fusion avec l'existant, jamais d'écrasement)
  python -I -B installer_crochet.py --projet <projet> --retirer  retire seulement l'entrée du studio
Le crochet (crochet_journal.py) recopie chaque réponse de l'assistant dans .studio/journal_assistant.json.
Une copie de sauvegarde settings.local.json.bak est faite avant toute modification. Bibliothèque standard seulement."""
import argparse
import json
import os
import shutil
import sys
for _flux in (sys.stdout, sys.stderr):                 # S6 : sortie en UTF-8, même redirigée (Windows)
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ICI = os.path.dirname(os.path.abspath(__file__))
MARQUE = "crochet_journal.py"


def copie_locale(projet):
    """Copie du crochet dans <projet>/.studio/outils/ (bibliothèque standard seule) : il ne dépend plus du dossier de version du plugin."""
    dest = os.path.join(projet, ".studio", "outils")
    os.makedirs(dest, exist_ok=True)
    cible = os.path.join(dest, MARQUE)
    shutil.copyfile(os.path.join(ICI, MARQUE), cible + ".tmp")
    os.replace(cible + ".tmp", cible)
    return cible


def commande(script):
    exe = sys.executable or "python"
    return f'"{exe}" -I -B "{script}"'


def lire(chemin):
    if not os.path.exists(chemin):
        return {}
    with open(chemin, encoding="utf-8-sig") as f:
        d = json.load(f)                      # un fichier illisible fait échouer l'installation : on n'écrase rien
    if not isinstance(d, dict):
        raise SystemExit("settings.local.json n'est pas un objet JSON : rien n'est modifié")
    return d


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--projet", required=True)
    a.add_argument("--retirer", action="store_true")
    o = a.parse_args()
    projet = os.path.abspath(o.projet)
    dossier = os.path.join(projet, ".claude")
    chemin = os.path.join(dossier, "settings.local.json")
    try:
        d = lire(chemin)
    except json.JSONDecodeError as e:
        raise SystemExit(f"settings.local.json illisible ({e}) : rien n'est modifié")
    hooks = d.setdefault("hooks", {})
    stop = hooks.setdefault("Stop", [])
    if not isinstance(stop, list):
        raise SystemExit("hooks.Stop n'est pas une liste : rien n'est modifié")
    deja = [g for g in stop if isinstance(g, dict) and any(MARQUE in str(h.get("command", "")) for h in g.get("hooks", []) if isinstance(h, dict))]
    if o.retirer:
        if not deja:
            print("rien à retirer")
            return
        hooks["Stop"] = [g for g in stop if g not in deja]
        if not hooks["Stop"]:
            del hooks["Stop"]
        if not hooks:
            del d["hooks"]
        msg = "crochet du studio retiré"
    else:
        cmd = commande(copie_locale(projet))
        if deja and all(h.get("command") == cmd for g in deja for h in g.get("hooks", []) if isinstance(h, dict) and MARQUE in str(h.get("command", ""))):
            print("déjà installé (copie du crochet mise à jour)")
            return
        hooks["Stop"] = [g for g in stop if g not in deja] + [{"hooks": [{"type": "command", "command": cmd, "timeout": 20}]}]
        msg = "crochet du studio mis à jour" if deja else "crochet du studio installé"
    os.makedirs(dossier, exist_ok=True)
    if os.path.exists(chemin):
        shutil.copyfile(chemin, chemin + ".bak")
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, chemin)
    print(f"{msg} : {chemin}")


if __name__ == "__main__":
    main()
