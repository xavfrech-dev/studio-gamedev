"""Santé du PC, partie « vrai agent » (Python 3.10+, bibliothèque standard seulement). Module partagé par studio_etat.py
(alimentation), serveur_studio.py (activation des températures) et le studio jumeau (copie jumelle).

1) disques()        : tous les disques fixes (lettre ou point de montage, nom, total, libre, %), Windows, Linux, macOS.
2) temperatures()   : processeur et disques.
     Windows : sans droits d'administrateur, Windows ne donne ni l'une ni l'autre. Activation EN UN CLIC (serveur,
       route /api/sante) : outils/temperatures_windows.ps1 est lancé avec élévation (Windows demande « Oui » une fois ;
       jamais d'élévation sans ce clic). Il crée une tâche planifiée (compte SYSTEM, toutes les 2 min) qui écrit
       %ProgramData%\\StudioGamedev\\temperatures.json (dossier réservé aux administrateurs en écriture).
       Processeur : LibreHardwareMonitor / OpenHardwareMonitor s'ils tournent (capteur « CPU Package »), sinon zone
       thermique ACPI ; une valeur figée (27,8 °C typique des cartes mères) est dite « non fiable », jamais affichée
       comme la température du processeur.
     Linux : lecture directe de /sys/class/hwmon (coretemp, k10temp, nvme, drivetemp) : rien à activer.
     macOS : « non disponible » (pas de source sans outil tiers).
3) Menage           : quand un disque qui porte le projet (ou ses caches, builds, worktrees) passe sous un seuil, l'agent
     ANALYSE ce qui prend de la place et PROPOSE un ménage chiffré (une décision sous la cloche). RIEN n'est effacé sans
     la réponse « faire » de l'utilisateur. Jamais hors des dossiers du projet et de ses caches. Journal de chaque effacement.
     Lignes possibles : fichiers temporaires du projet et de l'outil, caches régénérables du moteur (Unreal : DerivedDataCache,
     Intermediate, Saved/ShaderDebugInfo, Saved/Logs, Saved/Crashes ; Godot : .godot/imported, .godot/shader_cache ;
     Unity : Library, Temp, Logs, obj ; cache DDC partagé d'Unreal), vieilles builds (les 2 dernières gardées), worktrees git
     dont la branche est déjà fusionnée et propres (git worktree remove, sans --force ; la branche reste), corbeille du disque.
     Caches du moteur ignorés tant que le moteur est ouvert ; tout ce qui a bougé depuis 2 h est ignoré.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

GO = 2 ** 30
TACHE_WINDOWS = "Studio gamedev - temperatures"
SUBPROC = {"capture_output": True, "text": True, "timeout": 60, "encoding": "utf-8", "errors": "replace",
           "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
RECENT_S = 2 * 3600             # ce qui a bougé depuis 2 h n'est jamais proposé (build en cours, worktree en usage)
BUDGET_TAILLE_S = 60            # temps maximal pour mesurer les tailles d'une analyse (le reste est « au moins »)
REPORT_S = 12 * 3600            # « Pas maintenant » : plus de proposition pendant 12 h


def _lire(chemin, defaut):
    try:
        with open(chemin, encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return defaut


def _ecrire(chemin, donnees):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    tmp = f"{chemin}.{os.getpid()}.{threading.get_ident()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=1)
    for essai in range(5):
        try:
            os.replace(tmp, chemin)
            return
        except PermissionError:
            time.sleep(0.1 * (essai + 1))
    os.replace(tmp, chemin)


def _norm(p):
    return os.path.normcase(os.path.realpath(os.path.abspath(p)))


def dans(p, racine):
    p, r = _norm(p), _norm(racine)
    return p == r or p.startswith(r.rstrip("\\/") + os.sep)


# ------------------------------------------------------------------ 1) disques
_FS_REELS = {"ext2", "ext3", "ext4", "xfs", "btrfs", "zfs", "f2fs", "ntfs", "ntfs3", "vfat", "exfat", "fuseblk", "apfs", "hfs", "jfs", "reiserfs", "bcachefs"}


def _points_montage():
    """[(point, nom)] des disques fixes."""
    if os.name == "nt":
        import ctypes
        k = ctypes.windll.kernel32
        out = []
        masque = k.GetLogicalDrives()
        for i in range(26):
            if not masque & (1 << i):
                continue
            racine = chr(65 + i) + ":\\"
            if k.GetDriveTypeW(racine) != 3:            # 3 = disque fixe (ni lecteur réseau, ni clé, ni CD)
                continue
            buf = ctypes.create_unicode_buffer(261)
            nom = buf.value if k.GetVolumeInformationW(racine, buf, 261, None, None, None, None, 0) else ""
            out.append((racine, nom))
        return out
    if sys.platform == "darwin":
        out = [("/", "Macintosh HD")]
        try:
            for n in sorted(os.listdir("/Volumes")):
                p = os.path.join("/Volumes", n)
                if os.path.ismount(p) and os.path.realpath(p) != "/":
                    out.append((p, n))
        except OSError:
            pass
        return out
    out, vus = [], set()
    try:
        with open("/proc/mounts", encoding="utf-8", errors="replace") as f:
            for l in f:
                p = l.split()
                if len(p) < 3 or not p[0].startswith("/dev/") or p[2] not in _FS_REELS or p[0] in vus:
                    continue
                vus.add(p[0])
                point = p[1].replace("\\040", " ")
                out.append((point, os.path.basename(p[0])))
    except OSError:
        out = [("/", "/")]
    return out


def disques(projet=None, temps=None):
    """[{lettre, point, nom, total_go, libre_go, libre_pct, utilise_pct, temp_c, projet}] ; temps : {lettre ou point: °C}."""
    temps = temps or {}
    out = []
    try:
        points = _points_montage()
    except Exception:
        points = [("C:\\", "")] if os.name == "nt" else [("/", "/")]
    for point, nom in points:
        try:
            u = shutil.disk_usage(point)
        except OSError:
            continue
        if not u.total:
            continue
        lettre = point[0].upper() if os.name == "nt" else point
        t = temps.get(lettre)
        out.append({"lettre": lettre, "point": point, "nom": nom, "total_go": round(u.total / GO, 1), "libre_go": round(u.free / GO, 1),
                    "libre_pct": round(100 * u.free / u.total), "utilise_pct": round(100 - 100 * u.free / u.total),
                    "temp_c": t if isinstance(t, (int, float)) else None,
                    "projet": bool(projet) and disque_de(projet, [{"point": point}]) is not None})
    # sous Linux, plusieurs points peuvent mener au même disque : un seul « projet », le plus précis
    if projet and sum(1 for d in out if d["projet"]) > 1:
        meilleur = disque_de(projet, out)
        for d in out:
            d["projet"] = d is meilleur
    return out


def disque_de(chemin, liste):
    """Le disque (élément de liste, clé « point ») qui porte ce chemin : le point de montage le plus long qui le contient."""
    try:
        p = os.path.normcase(os.path.realpath(os.path.abspath(chemin)))   # derrière un lien : le disque où il est vraiment
    except Exception:
        return None
    meilleur = None
    for d in liste:
        pt = os.path.normcase(os.path.abspath(d.get("point") or ""))
        if p == pt or p.startswith(pt.rstrip("\\/") + os.sep) or pt in ("/", "\\") or (os.name == "nt" and len(pt) <= 3 and p[:2] == pt[:2]):
            if meilleur is None or len(pt) > len(os.path.normcase(meilleur.get("point") or "")):
                meilleur = d
    return meilleur


# ------------------------------------------------------------------ 2) températures
def fichier_temperatures_windows():
    return os.path.join(os.environ.get("ProgramData") or r"C:\ProgramData", "StudioGamedev", "temperatures.json")


_CPU_ACPI = []          # (t, valeur) : une zone ACPI qui ne bouge jamais n'est pas la température du processeur


def _linux_hwmon():
    cpu, autres = None, []
    base = "/sys/class/hwmon"
    try:
        noms = sorted(os.listdir(base))
    except OSError:
        return None, []
    for h in noms:
        d = os.path.join(base, h)
        try:
            nom = open(os.path.join(d, "name")).read().strip()
        except OSError:
            continue
        vals = []
        for f in os.listdir(d):
            if re.match(r"temp\d+_input$", f):
                try:
                    vals.append(int(open(os.path.join(d, f)).read().strip()) / 1000)
                except (OSError, ValueError):
                    pass
        if not vals:
            continue
        if nom in ("coretemp", "k10temp", "zenpower", "cpu_thermal"):
            cpu = max(vals + ([cpu] if cpu is not None else []))
        elif nom in ("nvme", "drivetemp"):
            autres.append({"capteur": f"{nom} ({h})", "temp_c": round(max(vals))})
    return (round(cpu) if cpu is not None else None), autres


def temperatures(dossier_sante, en=False, fichier=None):
    """{etat, cpu_c, cpu_source, cpu_note, disques: {lettre: °C}, autres: [...], maj, message, activable}.
    etat : active | pas_active | en_attente | refuse | en_panne | non_disponible."""
    tx = (lambda fr, en_: en_ if en else fr)
    act = _lire(os.path.join(dossier_sante, "temperatures_activation.json"), {}) if dossier_sante else {}
    act = act if isinstance(act, dict) else {}
    res = {"etat": "pas_active", "cpu_c": None, "cpu_source": None, "cpu_note": None, "disques": {}, "autres": [], "maj": None,
           "activable": os.name == "nt", "activation": act or None}
    if os.name != "nt":
        if sys.platform == "darwin":
            res.update(etat="non_disponible", message=tx("macOS ne donne pas les températures sans outil tiers : non disponible.",
                                                          "macOS gives no temperatures without a third-party tool: not available."))
            return res
        cpu, autres = _linux_hwmon()
        res.update(etat="active" if (cpu is not None or autres) else "non_disponible", cpu_c=cpu, cpu_source="hwmon" if cpu is not None else None,
                   autres=autres, maj=time.strftime("%Y-%m-%dT%H:%M:%S"),
                   message=None if (cpu is not None or autres) else tx("aucun capteur lisible (/sys/class/hwmon) : non disponible.",
                                                                        "no readable sensor (/sys/class/hwmon): not available."))
        if cpu is None:
            res["cpu_note"] = tx("processeur : non disponible", "CPU: not available")
        return res
    chemin = fichier or fichier_temperatures_windows()
    d = _lire(chemin, None)
    try:
        age = time.time() - os.path.getmtime(chemin)
    except OSError:
        age = None
    if isinstance(d, dict) and age is not None and age < 10 * 60:
        res["etat"], res["maj"] = "active", d.get("maj")
        for k, v in ((d.get("disques") or {}) if isinstance(d.get("disques"), dict) else {}).items():
            t = v.get("temp") if isinstance(v, dict) else v
            if isinstance(t, (int, float)) and 0 < t < 120:
                res["disques"][str(k).upper()[:1]] = int(round(t))
        c = d.get("cpu") if isinstance(d.get("cpu"), dict) else {}
        val, src = c.get("c"), c.get("source")
        if isinstance(val, (int, float)) and 0 < val < 125:
            if src == "acpi":
                _CPU_ACPI.append((time.time(), round(float(val), 1)))
                del _CPU_ACPI[:-12]
                figee = 27.0 <= val <= 28.5 or (len(_CPU_ACPI) >= 5 and _CPU_ACPI[-1][0] - _CPU_ACPI[0][0] >= 480 and len({v for _, v in _CPU_ACPI}) == 1)
                if figee:
                    res["cpu_note"] = tx(f"processeur : non disponible (la carte mère renvoie une valeur ACPI figée, {val:.1f} °C, pas la vraie température ; "
                                         "LibreHardwareMonitor ouvert la donnerait)",
                                         f"CPU: not available (the motherboard returns a frozen ACPI value, {val:.1f} °C, not the real temperature; "
                                         "a running LibreHardwareMonitor would provide it)")
                else:
                    res.update(cpu_c=int(round(val)), cpu_source="acpi",
                               cpu_note=tx("zone thermique ACPI de la carte mère (approximative)", "motherboard ACPI thermal zone (approximate)"))
            else:
                res.update(cpu_c=int(round(val)), cpu_source=src or "capteur")
        else:
            res["cpu_note"] = tx("processeur : non disponible (aucune source fiable sur cette machine)", "CPU: not available (no reliable source on this machine)")
        if not res["disques"]:
            res["message"] = tx("disques : Windows ne donne pas de température pour ces disques.", "disks: Windows reports no temperature for these disks.")
        return res
    etat_act = act.get("etat")
    t_act = act.get("t") or 0
    if etat_act == "en_attente_oui" and time.time() - t_act < 5 * 60:
        res["etat"] = "en_attente"
        res["message"] = tx("Windows demande « Oui » (fenêtre de contrôle de compte) : réponds-y pour activer.",
                            "Windows asks for “Yes” (account control window): answer it to enable.")
    elif etat_act == "refuse":
        res["etat"] = "refuse"
        res["message"] = tx("activation refusée (« Non » à Windows) : rien n'a été installé. Le bouton « Activer » la repropose.",
                            "enabling refused (“No” to Windows): nothing was installed. The “Enable” button offers it again.")
    elif etat_act in ("active", "en_attente_oui") and isinstance(d, dict):
        res["etat"] = "en_panne"
        res["message"] = tx("la tâche planifiée n'écrit plus le relevé depuis plus de 10 min (désinstaller puis réactiver).",
                            "the scheduled task has not written the reading for over 10 min (uninstall then enable again).")
    elif etat_act == "echec":
        res["etat"] = "pas_active"
        res["message"] = tx(f"échec de l'activation : {act.get('message') or 'inconnu'}", f"enabling failed: {act.get('message') or 'unknown'}")
    else:
        res["message"] = tx("Windows ne donne les températures qu'avec les droits d'administrateur : bouton « Activer » (un « Oui » à Windows, une fois).",
                            "Windows gives temperatures only with administrator rights: “Enable” button (one “Yes” to Windows, once).")
    return res


def lancer_activation(action, dossier_sante, script, en=False):
    """Appelé par le serveur sur le CLIC de l'utilisateur seulement. action : installer | desinstaller.
    Lance PowerShell non élevé qui demande l'élévation (Start-Process -Verb RunAs) : Windows affiche sa fenêtre « Oui / Non ».
    Retourne tout de suite ; le résultat (active / refuse / echec / desinstalle) est écrit dans temperatures_activation.json."""
    if os.name != "nt":
        raise RuntimeError("rien à activer hors de Windows (Linux : lecture directe ; macOS : non disponible)")
    if action not in ("installer", "desinstaller"):
        raise ValueError("action : installer ou desinstaller")
    if not os.path.isfile(script):
        raise FileNotFoundError(script)
    chemin = os.path.join(dossier_sante, "temperatures_activation.json")
    ancien = _lire(chemin, {}) or {}
    if ancien.get("etat") == "en_attente_oui" and time.time() - (ancien.get("t") or 0) < 3 * 60:
        return {"ok": True, "deja": True, "etat": "en_attente_oui"}
    _ecrire(chemin, {"etat": "en_attente_oui", "action": action, "t": int(time.time()), "quand": time.strftime("%Y-%m-%dT%H:%M:%S")})
    commande = ("$ErrorActionPreference='Stop'; try { $p = Start-Process -FilePath 'powershell.exe' -Verb RunAs -Wait -PassThru -WindowStyle Hidden "
                "-ArgumentList ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"' + $env:STUDIO_SANTE_PS1 + '\" -Action ' + $env:STUDIO_SANTE_ACTION); "
                "exit $p.ExitCode } catch { $e = $_.Exception; while ($e) { if ($e.NativeErrorCode -eq 1223) { exit 1223 }; $e = $e.InnerException }; "
                "if ($_.Exception.Message -match 'annul|cancel') { exit 1223 }; [Console]::Error.WriteLine($_.Exception.Message); exit 2 }")
    env = dict(os.environ, STUDIO_SANTE_PS1=os.path.abspath(script), STUDIO_SANTE_ACTION="Installer" if action == "installer" else "Desinstaller")

    def attendre():
        try:
            r = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", commande], env=env,
                               **dict(SUBPROC, timeout=15 * 60))
            code, err = r.returncode, (r.stderr or "").strip()[-300:]
        except Exception as e:  # noqa
            code, err = -1, f"{type(e).__name__} : {e}"
        if code == 0:
            etat = "active" if action == "installer" else "desinstalle"
            msg = None
        elif code == 1223:
            etat, msg = "refuse", None
        else:
            etat, msg = "echec", err or f"code {code}"
        _ecrire(chemin, {"etat": etat, "action": action, "t": int(time.time()), "quand": time.strftime("%Y-%m-%dT%H:%M:%S"), "message": msg, "code": code})
    threading.Thread(target=attendre, daemon=True).start()
    return {"ok": True, "etat": "en_attente_oui"}


# ------------------------------------------------------------------ 3) ménage proposé
def taille_dossier(p, limite_t):
    """(octets, complet) sans suivre les liens ni les jonctions ; s'arrête à limite_t (time.time())."""
    total, pile = 0, [p]
    while pile:
        if time.time() > limite_t:
            return total, False
        d = pile.pop()
        try:
            with os.scandir(d) as it:
                for e in it:
                    try:
                        if e.is_symlink() or _est_jonction(e.path):
                            continue
                        if e.is_dir(follow_symlinks=False):
                            pile.append(e.path)
                        else:
                            total += e.stat(follow_symlinks=False).st_size
                    except OSError:
                        pass
        except OSError:
            pass
    return total, True


def _est_jonction(p):
    try:
        return bool(getattr(os.path, "isjunction", lambda _: False)(p))
    except Exception:
        return False


def _lien(p):
    return os.path.islink(p) or _est_jonction(p)


def _recent(p, s=RECENT_S):
    """Vrai si le dossier (ou ses premiers niveaux) a bougé depuis s secondes."""
    lim = time.time() - s
    try:
        if os.path.getmtime(p) > lim:
            return True
        with os.scandir(p) as it:
            for i, e in enumerate(it):
                if i > 200:
                    break
                try:
                    if e.stat(follow_symlinks=False).st_mtime > lim:
                        return True
                except OSError:
                    pass
    except OSError:
        return False
    return False


def corbeille_taille(racine):
    """Octets dans la corbeille de ce disque (Windows : SHQueryRecycleBinW ; Linux : ~/.local/share/Trash ; macOS : ~/.Trash)."""
    if os.name == "nt":
        try:
            import ctypes

            class Q(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_ulong), ("i64Size", ctypes.c_longlong), ("i64NumItems", ctypes.c_longlong)]
            q = Q()
            q.cbSize = ctypes.sizeof(Q)
            if ctypes.windll.shell32.SHQueryRecycleBinW(ctypes.c_wchar_p(racine), ctypes.byref(q)) == 0:
                return int(q.i64Size), int(q.i64NumItems)
        except Exception:
            pass
        return 0, 0
    d = os.path.expanduser("~/.Trash" if sys.platform == "darwin" else "~/.local/share/Trash/files")
    if not os.path.isdir(d):
        return 0, 0
    t, _ = taille_dossier(d, time.time() + 10)
    try:
        n = len(os.listdir(d))
    except OSError:
        n = 0
    return t, n


def vider_corbeille(racine):
    if os.name == "nt":
        import ctypes
        r = ctypes.windll.shell32.SHEmptyRecycleBinW(None, ctypes.c_wchar_p(racine), 0x1 | 0x2 | 0x4)  # sans confirmation, sans fenêtre, sans son
        if r not in (0, -2147418113):     # E_UNEXPECTED : corbeille déjà vide
            raise OSError(f"SHEmptyRecycleBinW : {r}")
        return
    base = os.path.expanduser("~/.Trash" if sys.platform == "darwin" else "~/.local/share/Trash")
    for sous in (["."] if sys.platform == "darwin" else ["files", "info"]):
        d = os.path.join(base, sous)
        for n in os.listdir(d) if os.path.isdir(d) else []:
            p = os.path.join(d, n)
            if os.path.isdir(p) and not _lien(p):
                shutil.rmtree(p, ignore_errors=True)
            else:
                try:
                    os.remove(p)
                except OSError:
                    pass


def _effacer_arbre(p):
    """Efface un dossier sans jamais suivre un lien ou une jonction (le lien est retiré, pas sa cible)."""
    if _lien(p):
        raise OSError("lien ou jonction : jamais suivi")
    erreurs = []

    def surerreur(fonc, chemin, exc):
        try:
            os.chmod(chemin, 0o700)
            fonc(chemin)
        except Exception as e:  # noqa
            erreurs.append(f"{os.path.basename(chemin)} : {e}")
    if sys.version_info >= (3, 12):
        shutil.rmtree(p, onexc=surerreur)
    else:
        shutil.rmtree(p, onerror=lambda f, c, e: surerreur(f, c, e[1]))
    if os.path.exists(p):
        raise OSError("effacement partiel" + (f" ({erreurs[0]})" if erreurs else ""))


CACHES_MOTEUR = {
    # moteur : [(chemin relatif au projet, risque, détail fr, détail en)]
    "unreal": [("DerivedDataCache", "faible", "cache régénéré par Unreal (première ouverture plus lente)", "regenerated by Unreal (slower first open)"),
               ("Saved/ShaderDebugInfo", "faible", "infos de débogage des shaders", "shader debug info"),
               ("Saved/Logs", "faible", "anciens journaux", "old logs"),
               ("Saved/Crashes", "faible", "rapports de plantage", "crash reports"),
               ("Intermediate", "moyen", "fichiers intermédiaires : recompilation à la prochaine ouverture", "intermediate files: rebuild on next open")],
    "godot": [(".godot/shader_cache", "faible", "cache de shaders régénéré", "regenerated shader cache"),
              (".godot/imported", "moyen", "réimport complet des ressources à la prochaine ouverture", "full asset reimport on next open")],
    "unity": [("Temp", "faible", "fichiers temporaires d'Unity", "Unity temp files"), ("Logs", "faible", "anciens journaux", "old logs"),
              ("obj", "faible", "fichiers de compilation", "build objects"),
              ("Library", "moyen", "cache d'import : réimport long à la prochaine ouverture", "import cache: long reimport on next open")],
}


def moteur_du(projet):
    try:
        noms = os.listdir(projet)
    except OSError:
        return None
    if any(n.lower().endswith(".uproject") for n in noms):
        return "unreal"
    if "project.godot" in noms:
        return "godot"
    if "Assets" in noms and "ProjectSettings" in noms:
        return "unity"
    return None


MOTEURS_EXE = ("unrealeditor", "unrealeditor-cmd", "ue4editor", "unity", "godot")


def _sous(chemin, racine):
    try:
        c, r = os.path.normcase(os.path.realpath(chemin)), os.path.normcase(os.path.realpath(racine))
        return c == r or c.startswith(r.rstrip("/" + chr(92)) + os.sep)
    except Exception:
        return False


def moteur_en_marche():
    """Vrai si un éditeur de moteur tourne en ce moment (relevé direct des processus, en cas de doute : vrai)."""
    try:
        if os.name == "nt":
            r = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            noms = [l.split('","')[0].strip('"').lower() for l in r.stdout.splitlines() if l]
        else:
            r = subprocess.run(["ps", "-A", "-o", "comm="], capture_output=True, text=True, errors="replace", timeout=20)
            noms = [os.path.basename(l.strip()).lower() for l in r.stdout.splitlines()]
        if r.returncode != 0:
            return True
        return any((n[:-4] if n.endswith(".exe") else n).startswith(MOTEURS_EXE) for n in noms)
    except Exception:
        return True


def caches_partages(moteur):
    """Caches du moteur hors du projet (jamais d'autre dossier) : DDC partagé d'Unreal."""
    out = []
    if moteur == "unreal":
        base = os.environ.get("LOCALAPPDATA") if os.name == "nt" else os.path.expanduser("~/.config/Epic" if sys.platform != "darwin" else "~/Library/Application Support/Epic")
        if base:
            out.append((os.path.join(base, "UnrealEngine", "Common", "DerivedDataCache"), "faible",
                        "cache DDC partagé d'Unreal, régénéré (premières ouvertures plus lentes)", "Unreal shared DDC, regenerated (slower first opens)"))
    return out


class Menage:
    """Analyse et propose ; n'efface qu'après la réponse « faire » (reponses : {id: {choix}}).

    cfg : {projets: [racines de projet où chercher les caches du moteur], depots: [dépôts git dont on retire les worktrees
           fusionnés], builds: [dossiers de builds], temporaires: [(dossier, motif regex)], principale: 'main' (facultatif),
           corbeille: True, seuil_go: 30, seuil_pct: 8, min_go: 1, langue: 'fr', prefixe_id: 'menage'}
    """

    def __init__(self, dossier_sante, cfg):
        self.dossier = dossier_sante
        self.cfg = cfg
        self.verrou = threading.Lock()
        self.fil = None
        self.f_prop = os.path.join(dossier_sante, "menage_propose.json")
        self.f_etat = os.path.join(dossier_sante, "menage_etat.json")
        self.f_journal = os.path.join(dossier_sante, "menage_journal.json")
        self.f_demande = os.path.join(dossier_sante, "analyser.demande")

    def en(self):
        return str(self.cfg.get("langue") or "fr").lower().startswith("en")

    def tx(self, fr, en):
        return en if self.en() else fr

    # ---------------- git
    def _git(self, depot, *a):
        env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
        return subprocess.run(["git", "-C", depot, *a], env=env, **SUBPROC)

    def principale(self, depot):
        if self.cfg.get("principale"):
            return self.cfg["principale"]
        for b in ("main", "master"):
            if self._git(depot, "rev-parse", "--verify", "--quiet", "refs/heads/" + b).returncode == 0:
                return b
        return None

    def worktrees(self, depot):
        """[{chemin, branche, fusionnee, propre, verrouille, recent, admin}] (hors worktree principal)."""
        r = self._git(depot, "worktree", "list", "--porcelain")
        if r.returncode:
            return []
        blocs, cur = [], {}
        for l in r.stdout.splitlines():
            if not l.strip():
                if cur:
                    blocs.append(cur)
                cur = {}
                continue
            k, _, v = l.partition(" ")
            cur[k] = v or True
        if cur:
            blocs.append(cur)
        princ = self.principale(depot)
        fusionnees = set()
        if princ:
            m = self._git(depot, "branch", "--merged", princ, "--format=%(refname:short)")
            fusionnees = {x.strip() for x in m.stdout.splitlines() if x.strip()}
        out = []
        for b in blocs[1:]:
            chemin = os.path.normpath(str(b.get("worktree", "")))
            br = str(b.get("branch", "")).replace("refs/heads/", "") if isinstance(b.get("branch"), str) else ""
            out.append({"chemin": chemin, "branche": br, "fusionnee": bool(br) and br in fusionnees and br != princ,
                        "verrouille": "locked" in b, "prunable": "prunable" in b, "principale": princ})
        return out

    def wt_recent(self, chemin):
        """Worktree utilisé depuis moins de 2 h : son dossier, ou son index / HEAD / journal git (un agent qui y travaille les touche)."""
        if _recent(chemin):
            return True
        r = self._git(chemin, "rev-parse", "--absolute-git-dir")
        gd = r.stdout.strip() if r.returncode == 0 else ""
        lim = time.time() - RECENT_S
        for f in ("index", "HEAD", os.path.join("logs", "HEAD")):
            try:
                if gd and os.path.getmtime(os.path.join(gd, f)) > lim:
                    return True
            except OSError:
                pass
        return False

    def wt_propre(self, depot, chemin):
        r = self._git(chemin, "status", "--porcelain", "--untracked-files=normal")
        return r.returncode == 0 and not r.stdout.strip()

    # ---------------- racines permises (recalculées à chaque exécution)
    def racines(self):
        r = [p for p in (self.cfg.get("projets") or []) + (self.cfg.get("builds") or []) if p]
        r += [d for d, _ in self.cfg.get("temporaires") or []]
        for depot in self.cfg.get("depots") or []:
            r += [w["chemin"] for w in self.worktrees(depot)]
        if self.cfg.get("caches_partages", True):
            for p in self.cfg.get("projets") or []:
                r += [c for c, *_ in caches_partages(moteur_du(p))]
        return [x for x in r if x]

    def permis(self, chemin, type_):
        """Un chemin effaçable : dans une racine permise, jamais une racine de projet ni un dépôt, jamais .git, jamais un lien."""
        if not chemin or not os.path.isabs(chemin) or _lien(chemin):
            return False
        n = _norm(chemin)
        if type_ != "temporaires":        # un ménage de fichiers temporaires ne retire que des fichiers, jamais le dossier
            for p in (self.cfg.get("projets") or []) + (self.cfg.get("depots") or []) + (self.cfg.get("builds") or []):
                if p and n == _norm(p):
                    return False          # jamais le projet, le dépôt ou le dossier des builds lui-même
        if os.sep + ".git" + os.sep in n + os.sep and type_ != "worktree":
            return False
        if type_ == "worktree":
            return any(n == _norm(w["chemin"]) for d in self.cfg.get("depots") or [] for w in self.worktrees(d))
        return any(dans(chemin, r) for r in self.racines())

    # ---------------- analyse
    def analyser(self, disques_bas, moteur_ouvert):
        """Lignes proposées (rien n'est effacé ici). disques_bas : [{point, lettre, libre_go}]."""
        lignes, ignores = [], []
        limite = time.time() + BUDGET_TAILLE_S
        tous = disques_bas

        def sur_disque_bas(p):
            return disque_de(p, tous) is not None

        def ajoute(type_, chemin, risque, detail, octets=None, complet=True, extra=None):
            if octets is None:
                if os.path.isdir(chemin):
                    octets, complet = taille_dossier(chemin, limite)
                else:
                    try:
                        octets = os.path.getsize(chemin)
                    except OSError:
                        octets = 0
            if octets < 1024 * 1024:
                return
            d = disque_de(chemin, tous) or {}
            lignes.append(dict({"type": type_, "chemin": os.path.normpath(chemin), "octets": int(octets), "taille_go": round(octets / GO, 2),
                                "complet": complet, "risque": risque, "detail": detail, "disque": d.get("lettre")}, **(extra or {})))

        # fichiers temporaires du projet et de l'outil (*.tmp vieux de plus d'une heure, motifs donnés)
        for dossier, motif in self.cfg.get("temporaires") or []:
            if not os.path.isdir(dossier) or not sur_disque_bas(dossier):
                continue
            rx = re.compile(motif)
            tot, n = 0, 0
            for racine, dirs, fichiers in os.walk(dossier):
                dirs[:] = [d for d in dirs if not _lien(os.path.join(racine, d)) and d != ".git"]
                for f in fichiers:
                    p = os.path.join(racine, f)
                    try:
                        if rx.search(f) and time.time() - os.path.getmtime(p) > 3600:
                            tot += os.path.getsize(p)
                            n += 1
                    except OSError:
                        pass
                if time.time() > limite:
                    break
            if n:
                ajoute("temporaires", dossier, "faible", self.tx(f"{n} fichier(s) temporaire(s) ({motif})", f"{n} temporary file(s) ({motif})"),
                       octets=tot, extra={"motif": motif})
        # caches du moteur
        for projet in self.cfg.get("projets") or []:
            m = moteur_du(projet)
            if not m:
                continue
            liste = [(os.path.join(projet, *rel.split("/")), r, fr, en) for rel, r, fr, en in CACHES_MOTEUR[m]] + (caches_partages(m) if self.cfg.get("caches_partages", True) else [])
            if m == "unreal":
                try:
                    for pl in os.listdir(os.path.join(projet, "Plugins")):
                        liste.append((os.path.join(projet, "Plugins", pl, "Intermediate"), "moyen", "fichiers intermédiaires du plugin", "plugin intermediate files"))
                except OSError:
                    pass
            for chemin, risque, fr, en in liste:
                if not os.path.isdir(chemin) or not sur_disque_bas(chemin):
                    continue
                if moteur_ouvert:
                    ignores.append({"chemin": chemin, "raison": self.tx("moteur ouvert", "engine open")})
                    continue
                if _lien(chemin):
                    continue
                ajoute("cache", chemin, risque, self.tx(fr, en))
        # vieilles builds : les 2 plus récentes gardées
        for bd in self.cfg.get("builds") or []:
            if not os.path.isdir(bd) or not sur_disque_bas(bd):
                continue
            sous = []
            for e in os.scandir(bd):
                if e.is_dir(follow_symlinks=False) and not _lien(e.path):
                    try:
                        sous.append((e.stat().st_mtime, e.path))
                    except OSError:
                        pass
            sous.sort(reverse=True)
            for _, p in sous[2:]:
                if _recent(p):
                    ignores.append({"chemin": p, "raison": self.tx("modifiée depuis moins de 2 h", "changed less than 2 h ago")})
                    continue
                ajoute("build", p, "moyen", self.tx("build ancienne (les 2 dernières sont gardées ; refabricable depuis le dépôt)",
                                                     "old build (the 2 latest are kept; rebuildable from the repository)"))
        # worktrees dont la branche est fusionnée
        for depot in self.cfg.get("depots") or []:
            for w in self.worktrees(depot):
                p = w["chemin"]
                if not w["fusionnee"] or w["verrouille"] or not os.path.isdir(p) or not sur_disque_bas(p):
                    continue
                if self.wt_recent(p):
                    ignores.append({"chemin": p, "raison": self.tx("utilisé depuis moins de 2 h", "used less than 2 h ago")})
                    continue
                if not self.wt_propre(depot, p):
                    ignores.append({"chemin": p, "raison": self.tx("changements non commités", "uncommitted changes")})
                    continue
                ajoute("worktree", p, "faible", self.tx(f"worktree de « {w['branche']} », déjà fusionnée dans {w['principale']} (la branche reste ; ses fichiers ignorés, Saved et caches, partent avec)",
                                                        f"worktree of “{w['branche']}”, already merged into {w['principale']} (the branch stays; its ignored files, Saved and caches, go with it)"),
                       extra={"depot": depot, "branche": w["branche"]})
        # corbeille
        if self.cfg.get("corbeille", True):
            for d in tous:
                octets, n = corbeille_taille(d.get("point"))
                if octets >= 64 * 1024 * 1024:
                    lignes.append({"type": "corbeille", "chemin": self.tx(f"Corbeille de {d.get('lettre')}", f"Recycle bin of {d.get('lettre')}"),
                                   "point": d.get("point"), "octets": octets, "taille_go": round(octets / GO, 2), "complet": True, "risque": "élevé" if not self.en() else "high",
                                   "detail": self.tx(f"{n} élément(s) supprimé(s) : effacement définitif", f"{n} deleted item(s): permanent"), "disque": d.get("lettre")})
        lignes.sort(key=lambda x: -x["octets"])
        for i, l in enumerate(lignes, 1):
            l["n"] = i
        return lignes, ignores

    # ---------------- passage (appelé par l'alimentation, ~ toutes les 60 s)
    def passer(self, liste_disques, moteur_ouvert, reponses, synchrone=False):
        """Retourne ce que l'état montre (etat.sante.menage)."""
        seuil_go = float(self.cfg.get("seuil_go") or 30)
        seuil_pct = float(self.cfg.get("seuil_pct") or 8)
        concernes = []
        for p in self.racines_surveillees():
            d = disque_de(p, liste_disques)
            if d and d not in concernes:
                concernes.append(d)
        bas = [d for d in concernes if d.get("libre_go") is not None and (d["libre_go"] < seuil_go or (d.get("libre_pct") or 100) < seuil_pct)]
        etat = _lire(self.f_etat, {}) or {}
        prop = _lire(self.f_prop, None)
        demande = os.path.exists(self.f_demande)
        maintenant = time.time()
        # 1) réponse à la proposition ouverte
        if isinstance(prop, dict) and prop.get("statut") == "ouverte":
            r = (reponses or {}).get(prop["id"])
            if r:
                if r.get("choix") == "faire":
                    prop["statut"], prop["repondu_le"] = "en_cours", time.strftime("%Y-%m-%dT%H:%M:%S")
                    _ecrire(self.f_prop, prop)
                    self._lancer(prop, moteur_ouvert, synchrone)
                else:
                    prop["statut"] = "reportee"
                    etat["reporte_jusqu"] = int(maintenant + REPORT_S)
                    _ecrire(self.f_prop, prop)
                    _ecrire(self.f_etat, etat)
        # 2) nouvelle analyse : disque bas (ou demande explicite), pas de proposition ouverte ni de ménage en cours,
        #    pas de report en cours ; une analyse toutes les 30 min au plus
        occupe = (self.fil is not None and self.fil.is_alive()) or (isinstance(prop, dict) and prop.get("statut") in ("ouverte", "en_cours"))
        reporte = (etat.get("reporte_jusqu") or 0) > maintenant and not demande
        recente = maintenant - (etat.get("analyse_t") or 0) < 30 * 60 and not demande
        if (bas or demande) and not occupe and not reporte and not recente:
            try:
                os.remove(self.f_demande)
            except OSError:
                pass
            cibles = bas or concernes
            etat["analyse_t"] = int(maintenant)
            etat["analyse_en_cours"] = True
            _ecrire(self.f_etat, etat)
            if synchrone:
                self._analyse_et_propose(cibles, moteur_ouvert)
            else:
                self.fil = threading.Thread(target=self._analyse_et_propose, args=(cibles, moteur_ouvert), daemon=True)
                self.fil.start()
        return self.resume(bas, seuil_go)

    def racines_surveillees(self):
        r = list(self.cfg.get("projets") or []) + list(self.cfg.get("builds") or []) + list(self.cfg.get("depots") or [])
        for depot in self.cfg.get("depots") or []:
            try:
                r += [w["chemin"] for w in self.worktrees(depot)]
            except Exception:
                pass
        return [x for x in r if x]

    def _analyse_et_propose(self, cibles, moteur_ouvert):
        try:
            lignes, ignores = self.analyser(cibles, moteur_ouvert)
        except Exception as e:  # noqa
            lignes, ignores = [], [{"chemin": "", "raison": f"{type(e).__name__} : {e}"[:200]}]
        etat = _lire(self.f_etat, {}) or {}
        etat["analyse_en_cours"] = False
        total = sum(l["octets"] for l in lignes)
        etat["derniere_analyse"] = {"quand": time.strftime("%Y-%m-%dT%H:%M:%S"), "total_go": round(total / GO, 1), "nb_lignes": len(lignes),
                                    "ignores": ignores[:20]}
        min_go = float(self.cfg.get("min_go") or 1)
        if lignes and total / GO >= min_go:
            ident = f"{self.cfg.get('prefixe_id') or 'menage'}-" + time.strftime("%Y%m%d-%H%M") + "-" + hashlib.sha1(
                "|".join(l["chemin"] for l in lignes).encode("utf-8")).hexdigest()[:6]
            prop = {"id": ident, "statut": "ouverte", "cree_le": time.strftime("%Y-%m-%dT%H:%M:%S"), "disques": [
                {"lettre": d.get("lettre"), "libre_go": d.get("libre_go"), "total_go": d.get("total_go")} for d in cibles],
                "total_go": round(total / GO, 1), "lignes": lignes, "ignores": ignores[:20]}
            _ecrire(self.f_prop, prop)
        _ecrire(self.f_etat, etat)

    # ---------------- exécution (après « faire » seulement)
    def _lancer(self, prop, moteur_ouvert, synchrone):
        if synchrone:
            self._executer(prop, moteur_ouvert)
        else:
            self.fil = threading.Thread(target=self._executer, args=(prop, moteur_ouvert), daemon=True)
            self.fil.start()

    def _executer(self, prop, moteur_ouvert):
        journal = _lire(self.f_journal, [])
        journal = journal if isinstance(journal, list) else []
        libere = 0
        for l in prop.get("lignes") or []:
            res, ok = self._executer_ligne(l, moteur_ouvert)
            libere += l.get("octets", 0) if ok else 0
            l["resultat"] = res
            journal.append({"quand": time.strftime("%Y-%m-%dT%H:%M:%S"), "decision": prop["id"], "type": l.get("type"), "chemin": l.get("chemin"),
                            "taille_go": l.get("taille_go"), "resultat": res, "efface": ok})
        prop["statut"], prop["fait_le"], prop["libere_go"] = "faite", time.strftime("%Y-%m-%dT%H:%M:%S"), round(libere / GO, 1)
        _ecrire(self.f_prop, prop)
        _ecrire(self.f_journal, journal[-300:])
        etat = _lire(self.f_etat, {}) or {}
        etat["analyse_t"] = 0                      # ré-analyse au passage suivant si le disque est encore bas
        _ecrire(self.f_etat, etat)

    def _executer_ligne(self, l, moteur_ouvert):
        tx = self.tx
        type_, chemin = l.get("type"), l.get("chemin") or ""
        try:
            if type_ == "corbeille":
                if not self.cfg.get("corbeille", True):
                    return tx("ignoré : corbeille non permise", "skipped: recycle bin not allowed"), False
                vider_corbeille(l.get("point"))
                return tx("corbeille vidée", "recycle bin emptied"), True
            if not os.path.exists(chemin):
                return tx("déjà absent", "already gone"), False
            if not self.permis(chemin, type_):
                return tx("refusé : hors des dossiers du projet et de ses caches", "refused: outside the project folders and caches"), False
            if type_ == "cache":
                dans_projet = any(_sous(chemin, p) for p in self.cfg.get("projets") or [])
                if moteur_ouvert or (not dans_projet and moteur_en_marche()):   # cache partagé : jamais si un éditeur tourne
                    return tx("ignoré : moteur ouvert", "skipped: engine open"), False
                _effacer_arbre(chemin)
                return tx("effacé", "deleted"), True
            if type_ == "build":
                if _recent(chemin):
                    return tx("ignoré : modifiée depuis moins de 2 h", "skipped: changed less than 2 h ago"), False
                _effacer_arbre(chemin)
                return tx("effacé", "deleted"), True
            if type_ == "temporaires":
                rx = re.compile(l.get("motif") or r"\.tmp$")
                n = 0
                for racine, dirs, fichiers in os.walk(chemin):
                    dirs[:] = [d for d in dirs if not _lien(os.path.join(racine, d)) and d != ".git"]
                    for f in fichiers:
                        p = os.path.join(racine, f)
                        try:
                            if rx.search(f) and time.time() - os.path.getmtime(p) > 3600 and not _lien(p):
                                os.remove(p)
                                n += 1
                        except OSError:
                            pass
                return tx(f"{n} fichier(s) effacé(s)", f"{n} file(s) deleted"), n > 0
            if type_ == "worktree":
                depot = l.get("depot") or ""
                w = next((w for w in self.worktrees(depot) if _norm(w["chemin"]) == _norm(chemin)), None)
                if not w or not w["fusionnee"] or w["verrouille"]:
                    return tx("refusé : branche plus fusionnée ou worktree verrouillé", "refused: branch no longer merged or worktree locked"), False
                if not self.wt_propre(depot, chemin):
                    return tx("refusé : changements non commités", "refused: uncommitted changes"), False
                if self.wt_recent(chemin):
                    return tx("ignoré : utilisé depuis moins de 2 h", "skipped: used less than 2 h ago"), False
                r = self._git(depot, "worktree", "remove", chemin)          # sans --force : git refuse un worktree sale
                if r.returncode:
                    return tx("échec git : ", "git failed: ") + (r.stderr or r.stdout).strip()[:200], False
                return tx(f"worktree retiré (branche « {w['branche']} » gardée)", f"worktree removed (branch “{w['branche']}” kept)"), True
            return tx("type inconnu : ignoré", "unknown type: skipped"), False
        except Exception as e:  # noqa
            return tx("échec : ", "failed: ") + f"{e}"[:200], False

    # ---------------- ce que voient l'état et la cloche
    def resume(self, bas, seuil_go):
        etat = _lire(self.f_etat, {}) or {}
        prop = _lire(self.f_prop, None)
        journal = _lire(self.f_journal, [])
        en_cours_fil = self.fil is not None and self.fil.is_alive()
        statut = "rien"
        if etat.get("analyse_en_cours") and en_cours_fil:
            statut = "analyse"
        elif isinstance(prop, dict) and prop.get("statut") == "ouverte":
            statut = "propose"
        elif isinstance(prop, dict) and prop.get("statut") == "en_cours":
            statut = "en_cours"
        elif (etat.get("reporte_jusqu") or 0) > time.time():
            statut = "reporte"
        elif isinstance(prop, dict) and prop.get("statut") == "faite" and time.time() - _iso_t(prop.get("fait_le")) < 6 * 3600:
            statut = "fait"
        out = {"statut": statut, "seuil_go": seuil_go, "disques_bas": [d.get("lettre") for d in bas],
               "derniere_analyse": etat.get("derniere_analyse"), "reporte_jusqu": etat.get("reporte_jusqu"),
               "journal": (journal if isinstance(journal, list) else [])[-8:]}
        if isinstance(prop, dict):
            out["proposition"] = {k: prop.get(k) for k in ("id", "statut", "cree_le", "total_go", "disques", "fait_le", "libere_go")}
            out["proposition"]["lignes"] = [{k: l.get(k) for k in ("n", "type", "chemin", "taille_go", "complet", "risque", "detail", "disque", "resultat")}
                                            for l in (prop.get("lignes") or [])[:40]]
        return out

    def decision(self):
        """La décision sous la cloche (format des deux studios : titre/explication/choix ET question/contexte/options)."""
        prop = _lire(self.f_prop, None)
        if not isinstance(prop, dict) or prop.get("statut") != "ouverte":
            return None
        tx = self.tx
        lettres = ", ".join(str(d.get("lettre")) + (":" if os.name == "nt" and len(str(d.get("lettre"))) == 1 else "") for d in prop.get("disques") or [])
        lignes = [{k: l.get(k) for k in ("n", "type", "chemin", "taille_go", "complet", "risque", "detail")} for l in prop["lignes"][:40]]
        resume = "; ".join(f"{l['n']}. {l['chemin']} : {l['taille_go']:g} Go ({l['risque']})" for l in lignes[:8])
        titre = tx(f"Faire de la place sur {lettres} (≈ {prop['total_go']:g} Go) ?", f"Free up space on {lettres} (≈ {prop['total_go']:g} GB)?")
        explication = tx(f"L'agent Santé du PC a trouvé {len(lignes)} élément(s) effaçable(s) dans le projet et ses caches : {resume}. "
                         "Rien n'est effacé sans ton clic ; tout est noté dans le journal du ménage.",
                         f"The PC Health agent found {len(lignes)} removable item(s) in the project and its caches: {resume}. "
                         "Nothing is deleted without your click; everything is logged.")
        choix = [{"id": "faire", "libelle": tx("Faire ce ménage", "Do this cleanup"), "detail": tx(f"libère ≈ {prop['total_go']:g} Go", f"frees ≈ {prop['total_go']:g} GB")},
                 {"id": "plus_tard", "libelle": tx("Pas maintenant", "Not now"), "detail": tx("plus de proposition pendant 12 h", "no new proposal for 12 h")}]
        return {"id": prop["id"], "type": "menage", "origine": "sante-pc", "titre": titre, "question": titre, "explication": explication, "contexte": explication,
                "choix": choix, "options": choix, "recommande": "faire", "cree_le": prop.get("cree_le"), "statut": "ouverte",
                "lignes": lignes, "total_go": prop["total_go"], "poste": "sante"}


def _iso_t(s):
    try:
        return time.mktime(time.strptime(str(s)[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return 0
