"""Arrête le studio d'un projet (« arrête le studio ») : la veille, l'alimentation, puis le serveur.

  python -I -B arreter.py --projet <dossier du projet>

Ne vise que les processus notés par le studio lui-même : .studio/veille_studio.verrou, .studio/studio_etat.verrou et
.studio/serveur.json (le serveur est d'abord interrogé sur /api/qui : il doit servir ce projet et porter ce pid).
Les fichiers restent ; relancer le serveur et la veille reprend où on en était. Code 0 : arrêté (ou rien ne tournait).
"""
import argparse
import json
import os
import signal
import sys
import time
import urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ICI))
from veille_studio import lire_pid, verrou_vivant, vivant  # noqa: E402
for _flux in (sys.stdout, sys.stderr):                 # S6 : sortie en UTF-8, même redirigée (Windows)
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def tuer(pid):
    if not pid or pid == os.getpid() or not vivant(pid):
        return False
    try:
        os.kill(pid, signal.SIGTERM)            # sous Windows : TerminateProcess
    except OSError:
        return False
    for _ in range(20):
        if not vivant(pid):
            return True
        time.sleep(0.1)
    return not vivant(pid)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Arrête la veille, l'alimentation et le serveur du studio d'un projet.")
    ap.add_argument("--projet", required=True)
    a = ap.parse_args(argv)
    projet = os.path.abspath(a.projet)
    studio = os.path.join(projet, ".studio")
    if not os.path.isdir(studio):
        raise SystemExit(f"pas de dossier .studio dans {projet}")
    fait = []
    for nom, f in (("veille", "veille_studio.verrou"), ("alimentation", "studio_etat.verrou")):   # la veille d'abord : elle relancerait l'alimentation
        v = os.path.join(studio, f)
        if tuer(verrou_vivant(v)):              # seulement si le PID est encore bien notre processus (F2)
            fait.append(nom)
        try:
            if not verrou_vivant(v) and os.path.exists(v):
                os.remove(v)                     # verrou périmé ou processus arrêté : on l'efface
        except OSError:
            pass
    info = os.path.join(studio, "serveur.json")
    try:
        with open(info, encoding="utf-8-sig") as h:
            d = json.load(h)
        port, pid = int(d.get("port") or 0), int(d.get("pid") or 0)
    except (OSError, ValueError, TypeError, AttributeError):
        port = pid = 0
    if port:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/qui", timeout=2) as r:
                q = json.loads(r.read().decode("utf-8"))
            if q.get("pid") == pid and os.path.normcase(str(q.get("projet") or "")) == os.path.normcase(projet) and tuer(pid):
                fait.append(f"serveur (port {port})")
        except Exception:
            pass
        if not vivant(pid):
            try:
                os.remove(info)
            except OSError:
                pass
    print("arrêté : " + ", ".join(fait) if fait else "rien ne tournait pour ce projet")


if __name__ == "__main__":
    main()
