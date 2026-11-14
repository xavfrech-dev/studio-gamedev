"""Veille de l'alimentation du studio gamedev (Python 3.10+, bibliothèque standard seulement).

Lancer :  python -I -B veille_studio.py --projet <dossier du projet> [--donnees <dossier>] [--intervalle 10]

Lance studio_etat.py sans limite de durée et le relance :
  - s'il s'arrête (erreur, fermeture) : après 5 s (30 s s'il s'est arrêté 3 fois de suite en moins d'une minute) ;
  - s'il est figé : etat.json pas réécrit depuis 3 min (processus arrêté net), ou dernier passage TERMINÉ
    (champ « passage_fini » d'etat.json) vieux de plus de 11 min alors que le battement republie encore etat.json
    (boucle principale bloquée) : l'arrête et le relance.
Si une autre alimentation tient déjà le projet (etat.json frais, verrou d'un autre processus), la veille attend sans
rien lancer. Une seule veille par projet (.studio/veille_studio.verrou). Journal : .studio/veille_studio.log (1 Mo au plus,
l'ancien gardé en .log.1).
Ne concerne pas le serveur web (serveur_studio.py). Aucune commande reçue de la page : la seule commande lancée
est studio_etat.py du skill, avec des arguments fixes.
"""
import argparse
import json
import os
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ICI = os.path.dirname(os.path.abspath(__file__))
if ICI not in sys.path:
    sys.path.insert(0, ICI)
import jsonio  # noqa: E402  (C4 : lecture avec BOM, écriture atomique communes)
FIGE_S = 180
FIGE_PASSAGE_S = 660        # C3 : passage pas fini depuis 11 min (le battement de studio_etat.py s'arrête à 10 min)
JOURNAL_MAX = 1024 * 1024   # O13 : rotation du journal à 1 Mo


def age_passage(chemin):
    """Âge (s) du dernier passage terminé, d'après « passage_fini » d'etat.json ; None si inconnu (ancienne version,
    fichier en cours d'écriture) : on juge alors sur la date du fichier seule."""
    try:
        t = jsonio.lire_strict(chemin).get("passage_fini")
        return time.time() - t if isinstance(t, (int, float)) and not isinstance(t, bool) else None
    except Exception:
        return None


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


def heure_creation(pid):
    """Heure de création du processus (texte comparable), ou None : après un redémarrage, un PID repris par un autre
    programme a une autre heure de création ; on ne le prend donc jamais pour le nôtre."""
    if not pid:
        return None
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            k = ctypes.windll.kernel32
            h = k.OpenProcess(0x1000, False, pid)
            if not h:
                return None
            c, e, ke, u = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
            ok = k.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(ke), ctypes.byref(u))
            k.CloseHandle(h)
            return str((c.dwHighDateTime << 32) | c.dwLowDateTime) if ok else None
        if os.path.exists(f"/proc/{pid}/stat"):
            with open(f"/proc/{pid}/stat", encoding="utf-8", errors="replace") as f:
                return f.read().rsplit(")", 1)[1].split()[19]
        import subprocess
        r = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or None
    except Exception:
        return None


def lire_verrou(chemin):
    """(pid, heure de création) écrits dans un verrou ; (0, None) s'il est absent ou illisible."""
    try:
        with open(chemin, encoding="utf-8") as f:
            parts = f.read().split()
        return (int(parts[0]) if parts else 0), (parts[1] if len(parts) > 1 else None)
    except (OSError, ValueError):
        return 0, None


def lire_pid(chemin):
    return lire_verrou(chemin)[0]


def verrou_vivant(chemin):
    """PID du verrou s'il est encore NOTRE processus (vivant et même heure de création), sinon 0 (verrou périmé)."""
    pid, cree = lire_verrou(chemin)
    if not vivant(pid):
        return 0
    if cree is not None and heure_creation(pid) not in (None, cree):
        return 0                                   # PID repris par un autre programme
    return pid


def ecrire_verrou(chemin):
    """Écrit « pid heure_de_création » d'un coup (fichier temporaire puis remplacement) et l'efface à la sortie."""
    import atexit
    jsonio.ecrire_texte(chemin, f"{os.getpid()} {heure_creation(os.getpid()) or ''}".strip())

    def effacer():
        try:
            if lire_pid(chemin) == os.getpid():
                os.remove(chemin)
        except OSError:
            pass
    atexit.register(effacer)


def age_s(chemin):
    try:
        return time.time() - os.path.getmtime(chemin)
    except OSError:
        return None


def main(argv=None):
    for flux in (sys.stdout, sys.stderr):                # G16 : sortie redirigée (cp1252 sous Windows) : jamais de plantage d'accent
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
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
            if os.path.getsize(journal) > JOURNAL_MAX:     # O13 : le journal ne grossit plus sans fin
                os.replace(journal, journal + ".1")
        except OSError:
            pass
        try:
            with open(journal, "a", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
        except OSError:
            pass

    if verrou_vivant(verrou):
        raise SystemExit("une veille tourne déjà pour ce projet")
    ecrire_verrou(verrou)
    cmd = [sys.executable, "-I", "-B", os.path.join(ICI, "studio_etat.py"), "--projet", os.path.abspath(a.projet),
           "--duree-h", "0", "--intervalle", str(a.intervalle), "--forcer"]
    if a.donnees:
        cmd += ["--donnees", a.donnees]
    print(f"veille du studio : {studio}", flush=True)
    note("veille démarrée")
    rapides = 0
    while True:
        autre = verrou_vivant(verrou_alim)
        age_e, age_p = age_s(etat), age_passage(etat)
        fige_autre = (age_e is None or age_e >= FIGE_S) or (age_p is not None and age_p >= FIGE_PASSAGE_S)
        if autre and not fige_autre:
            time.sleep(15)          # une autre alimentation tient le projet et elle vit : on ne double pas
            continue
        if autre:                   # S35 : une alimentation à nous, vivante mais figée : on l'arrête avant d'en lancer une autre
            try:
                import signal
                os.kill(autre, signal.SIGTERM)
                note(f"alimentation figée arrêtée (pid {autre})")
                time.sleep(2)
            except OSError:
                pass
        debut = time.time()
        enfant = subprocess.Popen(cmd, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        note(f"studio_etat.py lancé (pid {enfant.pid})")
        while enfant.poll() is None:
            time.sleep(15)
            age, vie = age_s(etat), time.time() - debut
            if age is not None and age > FIGE_S and vie > FIGE_S:
                note(f"etat.json figé depuis {int(age)} s : relance")
                enfant.kill()
                break
            age_p = age_passage(etat)                   # C3 : le battement ne masque plus une boucle bloquée
            if age_p is not None and age_p > FIGE_PASSAGE_S and vie > FIGE_PASSAGE_S:
                note(f"aucun passage terminé depuis {int(age_p)} s (battement seul) : relance")
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
