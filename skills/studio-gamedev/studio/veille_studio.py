"""Veille de l'alimentation du studio gamedev (Python 3.10+, bibliothèque standard seulement).

Lancer :  python -I -B veille_studio.py --projet <dossier du projet> [--donnees <dossier>] [--intervalle 10]

Lance studio_etat.py sans limite de durée et le relance :
  - s'il s'arrête (erreur, fermeture) : après 5 s (30 s s'il s'est arrêté 3 fois de suite en moins d'une minute) ;
  - s'il est figé (etat.json pas réécrit depuis 3 min) : l'arrête et le relance.
Si une autre alimentation tient déjà le projet (etat.json frais, verrou d'un autre processus), la veille attend sans
rien lancer. Une seule veille par projet (.studio/veille_studio.verrou). Journal : .studio/veille_studio.log.
Ne concerne pas le serveur web (serveur_studio.py). Aucune commande reçue de la page : la seule commande lancée
est studio_etat.py du skill, avec des arguments fixes.
"""
import argparse
import os
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ICI = os.path.dirname(os.path.abspath(__file__))
FIGE_S = 180


def vivant(pid):
    """Le processus pid tourne-t-il encore ? (sans jamais lui envoyer de signal sous Windows)"""
    if not pid or pid == os.getpid():
        return False
    if os.name == "nt":
        try:
            import ctypes
            k = ctypes.windll.kernel32
            h = k.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return False
            code = ctypes.c_ulong()
            k.GetExitCodeProcess(h, ctypes.byref(code))
            k.CloseHandle(h)
            return code.value == 259                # STILL_ACTIVE
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def lire_pid(chemin):
    try:
        with open(chemin, encoding="utf-8") as f:
            return int(f.read().strip() or 0)
    except (OSError, ValueError):
        return 0


def age_s(chemin):
    try:
        return time.time() - os.path.getmtime(chemin)
    except OSError:
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Veille de l'alimentation du studio : relance studio_etat.py s'il s'arrête ou se fige.")
    ap.add_argument("--projet", required=True)
    ap.add_argument("--donnees", default=None)
    ap.add_argument("--intervalle", type=float, default=10)
    a = ap.parse_args(argv)
    studio = os.path.join(os.path.abspath(a.projet), ".studio")
    if not os.path.isdir(studio):
        raise SystemExit(f"pas de dossier .studio dans {a.projet}")
    verrou, journal = os.path.join(studio, "veille_studio.verrou"), os.path.join(studio, "veille_studio.log")
    etat, verrou_alim = os.path.join(studio, "etat.json"), os.path.join(studio, "studio_etat.verrou")

    def note(msg):
        try:
            with open(journal, "a", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
        except OSError:
            pass

    if vivant(lire_pid(verrou)):
        raise SystemExit("une veille tourne déjà pour ce projet")
    with open(verrou, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))
    cmd = [sys.executable, "-I", "-B", os.path.join(ICI, "studio_etat.py"), "--projet", os.path.abspath(a.projet),
           "--duree-h", "0", "--intervalle", str(a.intervalle), "--forcer"]
    if a.donnees:
        cmd += ["--donnees", a.donnees]
    print(f"veille du studio : {studio}", flush=True)
    note("veille démarrée")
    rapides = 0
    while True:
        autre = lire_pid(verrou_alim)
        if autre and vivant(autre) and (age_s(etat) or 1e9) < FIGE_S:
            time.sleep(15)          # une autre alimentation tient le projet et elle vit : on ne double pas
            continue
        debut = time.time()
        enfant = subprocess.Popen(cmd, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        note(f"studio_etat.py lancé (pid {enfant.pid})")
        while enfant.poll() is None:
            time.sleep(15)
            age = age_s(etat)
            if age is not None and age > FIGE_S and time.time() - debut > FIGE_S:
                note(f"etat.json figé depuis {int(age)} s : relance")
                enfant.kill()
                break
        enfant.wait()
        note(f"studio_etat.py arrêté (code {enfant.returncode})")
        rapides = rapides + 1 if time.time() - debut < 60 else 0
        time.sleep(30 if rapides >= 3 else 5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
