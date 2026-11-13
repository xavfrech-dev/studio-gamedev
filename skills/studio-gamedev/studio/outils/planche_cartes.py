# -*- coding: utf-8 -*-
"""Planche de contrôle des illustrations : une page HTML (toutes les cartes,
avec leur nom), puis un PNG rendu par un navigateur Chromium sans tête
(Edge ou Chrome) s'il est trouvé.

    python -I -B studio/outils/planche_cartes.py <dossier_sortie>

Contact sheet of every card illustration (HTML, plus PNG via headless Edge/Chrome).
"""
import os
import shutil
import subprocess
import sys
for _flux in (sys.stdout, sys.stderr):                 # S6 : sortie en UTF-8, même redirigée (Windows)
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
sys.dont_write_bytecode = True   # jamais de __pycache__ dans le dossier du skill

ICI = os.path.dirname(os.path.abspath(__file__))
CARTES = os.path.join(os.path.dirname(ICI), "cartes")
COLS = 12

NAVIGATEURS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def main():
    sortie = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
    os.makedirs(sortie, exist_ok=True)
    noms = sorted(f[:-4] for f in os.listdir(CARTES) if f.endswith(".svg"))
    cellules = "".join(
        '<figure><img src="%s"><figcaption>%s</figcaption></figure>'
        % ("file:///" + os.path.join(CARTES, nm + ".svg").replace("\\", "/"), nm) for nm in noms)
    rangs = (len(noms) + COLS - 1) // COLS
    html = ("<!doctype html><meta charset='utf-8'><style>"
            "body{margin:0;padding:16px;background:#e4d9c3;font:11px/1.2 sans-serif;color:#2a241d}"
            "h1{font-size:16px;margin:0 0 10px}"
            ".g{display:grid;grid-template-columns:repeat(%d,160px);gap:8px}"
            "figure{margin:0}img{display:block;width:160px;height:120px}"
            "figcaption{text-align:center;padding-top:2px}</style>"
            "<h1>studio-gamedev : %d illustrations de cartes</h1><div class='g'>%s</div>") % (COLS, len(noms), cellules)
    page = os.path.join(sortie, "planche_cartes.html")
    with open(page, "w", encoding="utf-8") as f:
        f.write(html)
    largeur = 32 + COLS * 168
    hauteur = 60 + rangs * 146
    nav = next((p for p in NAVIGATEURS if os.path.exists(p)), shutil.which("msedge") or shutil.which("google-chrome") or shutil.which("chromium"))
    if not nav:
        print("Page écrite (pas de navigateur trouvé pour le PNG) :", page)
        return
    png = os.path.join(sortie, "planche_cartes.png")
    subprocess.run([nav, "--headless", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                    "--screenshot=" + png, "--window-size=%d,%d" % (largeur, hauteur), "file:///" + page.replace("\\", "/")],
                   check=False, timeout=120, capture_output=True)
    print(png if os.path.exists(png) else "Échec du rendu PNG ; page : " + page)


if __name__ == "__main__":
    main()
