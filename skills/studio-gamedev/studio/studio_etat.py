"""Alimentation du studio gamedev (Python 3.10+, bibliothèque standard seulement).

Lancer :  python -I -B studio_etat.py --projet <dossier du projet>            (boucle : toutes les 10 s, s'arrête seul après 12 h ;
                                                                              --duree-h 0 : sans limite, c'est ce que fait veille_studio.py)
          python -I -B studio_etat.py --projet <dossier du projet> --une-fois  (un seul passage, pour un essai)
          --donnees <dossier>  dossier de données hors du projet, choisi par l'utilisateur : les motifs
                               « {donnees}/… » de sources_images s'y résolvent (sinon ils sont ignorés)

Mur d'images : seulement des images DANS le projet ou dans --donnees (jamais ailleurs, même si un
studio.config.json venu d'un dépôt cloné le demande) ; liens symboliques suivis puis revérifiés.

Lit dans <projet>/.studio/ :
  studio.config.json (postes, moteur, outils_lourds, sources_images, seuils), progression/*.json, recrues/*.json,
  demandes/*.json et demandes/statuts.json, demandes_vocales/*.json, attentes.json, decisions.json, reponses.json,
  roadmap.json, reglages.json, profil.json, rapport_assistant.json.
Lit aussi, en lecture seule : l'état git du projet s'il en est un (branche, fichiers suivis modifiés, derniers commits),
  la liste des processus (outil lourd ouvert ?), l'espace disque, la date du journal de session Claude Code.
Écrit dans <projet>/.studio/ :
  etat.json                (toutes les 10 s)  ce que fait chaque poste, version 1, chaîne active, git, mur d'images…
  suggestions.json         (toutes les 60 s)  analyse continue : alertes et conseils
  taches_disponibles.json  (toutes les 60 s)  tâches de roadmap prêtes (dépendances faites), par poste
  mur/                     (toutes les 90 s)  copies des dernières images (sources_images), servies par le serveur
  decisions_studio.json    (toutes les 60 s)  propositions de renvoi (recrue libre depuis 24 h, plus rien pour son métier) :
                                              la page les montre sous la cloche ; rien n'est jamais renvoyé sans réponse

Règles (les mêmes que le studio d'origine) :
  - « disponible » seulement s'il ne reste rien à faire (ni étape restante, ni tâche de roadmap, ni demande, ni attente) ;
  - « occupé » (champ occupe) = le personnage est assis à son poste : il travaille vraiment (progression fraîche,
    demande lancée, ou outil lourd du poste ouvert) ;
  - la ligne du bandeau (ligne.picto + ligne.texte) n'est jamais vide : tâche en cours, attente, suite ou « libre » ;
  - le % de la version 1 est l'avancement de la roadmap pondéré par l'effort ;
  - l'alerte d'inactivité de l'outil lourd se tait tant qu'une chaîne est active ;
  - « fin de tâche » (champ fin_de_tache) seulement après un vrai calme : progression à 100 % immobile depuis 5 min,
    plus rien devant lui, aucune chaîne active à son nom, aucune demande lancée ;
  - les tâches sorties, écartées, abandonnées, reportées, remplacées ou retirées ne sont jamais proposées ;
  - un fichier d'agent illisible (progression, recrue, demande) est ignoré et signalé (anomalies), le reste continue ;
  - tous les JSON sont lus avec ou sans BOM.
Aucune commande reçue de la page n'est exécutée ; les seules commandes lancées sont fixes (git en lecture, liste des processus).
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

sys.dont_write_bytecode = True   # jamais de __pycache__ dans le dossier du skill
if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jsonio  # noqa: E402  (C4 : lecture avec BOM, écriture atomique communes)
import sante_machine  # noqa: E402  (Santé du PC : disques, températures, ménage proposé)
FAITS = ("verse", "ecart")
ICI = os.path.dirname(os.path.abspath(__file__))
POIDS_AV = {"verse": 1, "ecart": 1, "pret": 0.7, "en_cours": 0.35, "a_faire": 0}
RESTE = {"verse": 0, "ecart": 0, "pret": 0.3, "en_cours": 0.65, "a_faire": 1}
FRAIS_MIN = 30          # une progression plus vieille que ça n'est plus « en train de travailler »
CHAINE_MIN = 10         # chaîne active : une progression a bougé depuis 10 min (ou outil lourd ouvert, ou demande lancée récente)
IMAGES_MAX = 36
IMAGE_MAX_OCTETS = 12 * 1024 * 1024
TECHNIQUE = re.compile(r"(^|_)(N|ORM|BC|R|M|AO|H|GL|N_GL|ORM_GL|mask|masque|normal|rough)$", re.I)
CALME_FIN_MIN = 5       # fin de tâche : progression à 100 % immobile depuis 5 min
RENVOI_LIBRE_H = 24     # proposition de renvoi : recrue libre depuis 24 h sans rien pour son métier
# tâche qui ne se propose plus : statut hors liste, drapeau, ou mot dans la note / le titre
EXCLUS = re.compile(r"\b(sorti|sortie|écart|ecart|abandonn|hors v1|hors version|remplac|report|retir|dropped|removed|postponed|out of scope|replaced)", re.I)
SUBPROC = {"capture_output": True, "text": True, "timeout": 20, "encoding": "utf-8", "errors": "replace",
           "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}

# ------------------------------------------------------------------ outils
# -------------------------------------------------------------------- santé du PC (réglage sante_auto, coupé par défaut)
# psutil s'il est installé ; sinon repli léger : Windows (GetSystemTimes, GlobalMemoryStatusEx), Linux (/proc), macOS (os.getloadavg).
# Aucun processus n'est tué, aucun réglage du système n'est touché.
_CPU_HIST, _CPU_PREC = [], []


def _cpu_pct():
    try:
        import psutil
        return int(psutil.cpu_percent(interval=None))
    except Exception:
        pass
    if os.name == "nt":
        try:
            import ctypes
            i, k, u = (ctypes.c_ulonglong() for _ in range(3))
            ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(i), ctypes.byref(k), ctypes.byref(u))
            cur = (i.value, k.value + u.value)
            if not _CPU_PREC:
                _CPU_PREC.append(cur)
                return None
            di, dt = cur[0] - _CPU_PREC[0][0], cur[1] - _CPU_PREC[0][1]
            _CPU_PREC[0] = cur
            return int(round(100 * (dt - di) / dt)) if dt > 0 else None
        except Exception:
            return None
    try:
        with open("/proc/stat") as f:
            v = [int(x) for x in f.readline().split()[1:]]
        cur = (v[3] + (v[4] if len(v) > 4 else 0), sum(v))
        if not _CPU_PREC:
            _CPU_PREC.append(cur)
            return None
        di, dt = cur[0] - _CPU_PREC[0][0], cur[1] - _CPU_PREC[0][1]
        _CPU_PREC[0] = cur
        return int(round(100 * (dt - di) / dt)) if dt > 0 else None
    except Exception:
        pass
    try:
        return int(min(100, 100 * os.getloadavg()[0] / (os.cpu_count() or 1)))
    except Exception:
        return None


def _mem_pct():
    try:
        import psutil
        return int(psutil.virtual_memory().percent)
    except Exception:
        pass
    if os.name == "nt":
        try:
            import ctypes

            class M(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + [(n, ctypes.c_ulonglong) for n in ("t", "a", "tp", "ap", "tv", "av", "ae")]
            m = M()
            m.dwLength = ctypes.sizeof(M)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return int(m.dwMemoryLoad)
        except Exception:
            return None
    try:
        d = {}
        with open("/proc/meminfo") as f:
            for l in f:
                k, v = l.split(":")
                d[k] = int(v.split()[0])
        return int(round(100 * (1 - d["MemAvailable"] / d["MemTotal"])))
    except Exception:
        return None


def _gpu():
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        v = [x.strip() for x in r.stdout.strip().splitlines()[0].split(",")]
        u, mu, mt = (float(x) for x in v[:3])
        tp = int(float(v[3])) if len(v) > 3 and re.match(r"^\d+(\.\d+)?$", v[3]) else None
        return {"gpu": int(u), "vram_pct": int(round(100 * mu / mt)) if mt else None, "gpu_temp": tp}
    except Exception:
        return {}


_GPU = {"t": 0, "v": {}}


def mesures_pc():
    """Échantillon léger : processeur (historique des 10 dernières minutes), mémoire, carte graphique (toutes les 60 s)."""
    cpu, mem = _cpu_pct(), _mem_pct()
    if cpu is not None and (not _CPU_HIST or _CPU_HIST[-1][0] < time.time() - 50):
        _CPU_HIST.append((time.time(), cpu))
        del _CPU_HIST[:-15]
    if time.time() - _GPU["t"] > 60:
        _GPU["t"], _GPU["v"] = time.time(), _gpu()
    return dict({"cpu": cpu, "memoire_pct": mem, "cpu_sature_min": sum(1 for _, v in _CPU_HIST[-10:] if v >= 92)}, **_GPU["v"])


_SAT_DEPUIS = [0]
SATURATION_TOLEREE_MIN = 15


def sante_pc(sy, en=False):
    alertes = []
    if (sy.get("cpu_sature_min") or 0) >= 8:
        alertes.append(f"CPU saturated ({sy['cpu_sature_min']}/10 min above 92 %)" if en else f"processeur saturé ({sy['cpu_sature_min']}/10 min au-dessus de 92 %)")
    if sy.get("memoire_pct") is not None and sy["memoire_pct"] > 90:
        alertes.append(f"memory used at {sy['memoire_pct']} %" if en else f"mémoire utilisée à {sy['memoire_pct']} %")
    if sy.get("disque_libre_go") is not None and sy["disque_libre_go"] < 30:
        alertes.append(f"disk almost full ({sy['disque_libre_go']} GB free)" if en else f"disque presque plein ({sy['disque_libre_go']} Go libres)")
    charge = max([v for v in (sy.get("cpu"), sy.get("memoire_pct"), sy.get("gpu")) if isinstance(v, (int, float))] or [0])
    pauses = (["space out heavy tasks; automatic assignments wait until the saturation ends", "one heavy tool (engine, 3D render) at a time"] if en else
              ["espacer les tâches lourdes ; les attributions automatiques attendent la fin de la saturation",
               "un seul outil lourd (moteur, rendu 3D) à la fois"]) if alertes else []
    # Saturation passagère (petites tâches, quelques minutes) : on laisse tourner. Les automatismes ne sont freinés
    # (« bloquant ») que si le disque est presque plein ou si la saturation dure plus de SATURATION_TOLEREE_MIN minutes.
    maintenant = time.time()
    _SAT_DEPUIS[0] = (_SAT_DEPUIS[0] or maintenant) if alertes else 0
    duree = int((maintenant - _SAT_DEPUIS[0]) / 60) if _SAT_DEPUIS[0] else 0
    disque = sy.get("disque_libre_go") is not None and sy["disque_libre_go"] < 30
    bloquant = bool(alertes) and (disque or duree >= SATURATION_TOLEREE_MIN)
    if alertes and not bloquant:
        pauses = [f"brief saturation ({duree} min): work goes on; automations slow down only if it lasts over {SATURATION_TOLEREE_MIN} min" if en
                  else f"saturation passagère ({duree} min) : on laisse tourner ; les automatismes ne ralentissent que si ça dure plus de {SATURATION_TOLEREE_MIN} min"]
    return {"sature": bool(alertes), "bloquant": bloquant, "sature_depuis_min": duree, "alertes": alertes, "pauses": pauses, "charge": int(charge)}



def sante_complements(sy, en=False):
    """Tous les disques, températures, avertissements (non bloquants) : autres disques presque pleins, chauffe."""
    temps = sy.get("temperatures") or {}
    av = []
    for d in sy.get("disques") or []:
        if not d.get("projet") and (d.get("libre_pct", 100) < 8 or (d.get("libre_go") or 0) < 10):
            av.append(f"disk {d['lettre']} almost full ({d['libre_go']} GB free)" if en else f"disque {d['lettre']} presque plein ({d['libre_go']} Go libres)")
        if isinstance(d.get("temp_c"), (int, float)) and d["temp_c"] >= 65:
            av.append(f"disk {d['lettre']} hot ({d['temp_c']} °C)" if en else f"disque {d['lettre']} chaud ({d['temp_c']} °C)")
    if isinstance(temps.get("cpu_c"), (int, float)) and temps["cpu_c"] >= 95:
        av.append(f"CPU hot ({temps['cpu_c']} °C)" if en else f"processeur chaud ({temps['cpu_c']} °C)")
    if isinstance(sy.get("gpu_temp"), (int, float)) and sy["gpu_temp"] >= 87:
        av.append(f"GPU hot ({sy['gpu_temp']} °C)" if en else f"carte graphique chaude ({sy['gpu_temp']} °C)")
    try:   # fiche de l'agent : une jauge par disque et par température (sante_machine.jauges, jumeau du studio d'origine)
        jg = sante_machine.jauges(sy.get("cpu"), sy.get("memoire_pct"), sy.get("gpu"), sy.get("vram_pct"), sy.get("gpu_temp"),
                                  sy.get("disques") or [], temps, en)
    except Exception as e:  # noqa: une jauge en panne ne coupe pas le studio
        jg = {"erreur": f"{type(e).__name__} : {e}"[:200]}
    return {"disques": sy.get("disques") or [], "temperatures": temps, "gpu_temp": sy.get("gpu_temp"), "avertissements": av, "jauges": jg}


def dans(p, racine):
    return p == racine or p.startswith(racine.rstrip(os.sep) + os.sep)




def lire_json(chemin, defaut):
    """JSON avec ou sans BOM (certains outils écrivent un BOM UTF-8)."""
    return jsonio.lire(chemin, defaut)


ECRITURE = threading.RLock()   # M8 : le battement et la boucle principale n'écrivent jamais etat.json en même temps


def ecrire_json(chemin, donnees, indent=None):
    """jsonio.ecrire : temporaire unique (M8 : propre à chaque fil), fsync, nouveaux essais si Windows tient le fichier,
    temporaire jamais laissé en cas d'erreur."""
    jsonio.ecrire(chemin, donnees, indent=indent)


def court(texte, n=90):
    texte = re.sub(r"[*`_]+", " ", str(texte or "")).replace("\r", "").strip()
    texte = re.sub(r"\s+", " ", texte.split("\n")[0]).strip()
    return texte if len(texte) <= n else texte[: n - 1].rstrip() + "…"


def hm(t):
    return time.strftime("%H:%M", time.localtime(t)) if t else ""


def age_min(chemin):
    try:
        return (time.time() - os.path.getmtime(chemin)) / 60
    except OSError:
        return None


def iso_vers_t(s):
    s = str(s or "").strip()
    if re.search(r"T?\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})$", s):   # M12 : date avec fuseau (…Z, …+01:00) : heure exacte
        try:
            import datetime
            return datetime.datetime.fromisoformat(re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", re.sub(r"Z$", "+00:00", s)).replace(" ", "T", 1)).timestamp()
        except ValueError:
            pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return time.mktime(time.strptime(s[:19] if "S" in fmt else s[:16], fmt))
        except ValueError:
            pass
    return 0


def restant_de(prog):
    """Minutes restantes : restant_min, sinon fin (HH:MM ou date ISO)."""
    if not isinstance(prog, dict):
        return None
    r = prog.get("restant_min")
    if isinstance(r, (int, float)) and not isinstance(r, bool) and r >= 0:
        return round(float(r), 1)
    fin = str(prog.get("fin", "") or "").strip()
    m_dans = re.match(r"^(?:dans|in)\s+(\d+(?:[.,]\d+)?)\s*(min|h)", fin, re.I)      # « dans 20 min », « in 2 h »
    if m_dans:
        v = float(m_dans.group(1).replace(",", "."))
        return round(v * (60 if m_dans.group(2).lower() == "h" else 1), 1)
    t = iso_vers_t(fin)
    if not t:
        m = re.match(r"^(\d{1,2})\s*[:h]\s*(\d{2})?$", fin, re.I)                   # « 14:30 », « 14h30 », « 14 h »
        if m:
            lt = time.localtime()
            t = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, int(m.group(1)), int(m.group(2) or 0), 0, 0, 0, -1))
            if t < time.time() - 6 * 3600:
                t += 86400
            elif t > time.time() + 18 * 3600:
                t -= 86400                                   # F33 : « 23:50 » lu à 00:10 = hier soir (en retard), pas demain
    return round(max(0.0, (t - time.time()) / 60), 1) if t else None


def pct_de(prog):
    if isinstance(prog, dict) and isinstance(prog.get("pct"), (int, float)) and not isinstance(prog.get("pct"), bool):
        return max(0, min(100, int(round(prog["pct"]))))
    return None


MUR_EXAMENS_MAX, MUR_SECONDES_MAX = 2000, 2.0
MUR_CACHES = re.compile(r"/(\.git|node_modules|Intermediate|DerivedDataCache|ShaderCache|Library|Temp|obj|\.godot/imported|\.import|__pycache__)/", re.I)


# Suggestions : phrases françaises → anglais (motif, remplacement), appliquées dans l'ordre quand le projet n'est pas en français
SUGG_EN = [
    (r"^(.+) est inactif alors qu'une tâche l'attend$", r"\1 is idle while a task is waiting for it"),
    (r"^Aucun (.+) depuis (\d+) min ni chaîne active ; prochaine tâche : (.+)\.$", r"No \1 for \2 min and no active chain; next task: \3."),
    (r"^Relancer la chaîne (.+) sur cette tâche\.$", r"Restart the \1 chain on this task."),
    (r"^(\d+) (.+) ouverts en même temps$", r"\1 \2 open at the same time"),
    (r"^Une seule chaîne moteur à la fois : risque de conflit et de mémoire\.$", "One engine chain at a time: risk of conflicts and memory pressure."),
    (r"^Fermer l'instance de (.+) qui n'appartient pas à la chaîne\.$", r"Close the \1 instance that is not part of the chain."),
    (r"^Disque du projet presque plein$", "Project disk almost full"),
    (r"^([\d.]+) Go libres \(seuil (.+) Go\)\.$", r"\1 GB free (threshold \2 GB)."),
    (r"^Déplacer les données lourdes hors du disque du projet ou supprimer d'anciens worktrees\.$", "Move heavy data off the project disk or remove old worktrees."),
    (r"^Modifications non commitées sur (.+)$", r"Uncommitted changes on \1"),
    (r"^(\d+) fichier\(s\) suivi\(s\), par ex\. (.+)\.$", r"\1 tracked file(s), e.g. \2."),
    (r"^Les committer ou les ranger avant le prochain versement\.$", "Commit or stash them before the next merge."),
    (r"^(.+) est bloqué$", r"\1 is blocked"),
    (r"^Lire sa progression et débloquer, ou poser une décision\.$", "Read its progress and unblock it, or ask a decision."),
    (r"^Progression figée : (.+)$", r"Progress frozen: \1"),
    (r"^(\d+) % depuis (\d+) min : (.*)$", r"\1 % for \2 min: \3"),
    (r"^Vérifier si l'agent tourne encore ; sinon le relancer ou passer la tâche en attente\.$", "Check whether the agent is still running; otherwise restart it or put the task on hold."),
    (r"^Demande en attente : (.+)$", r"Pending request: \1"),
    (r"^Déposée à (.+) : (.*)$", r"Filed at \1: \2"),
    (r"^Lancer l'agent \(voir SKILL\.md, « Demandes »\) ou répondre pourquoi elle attend\.$", "Start the agent (see SKILL.md, “Demandes”) or say why it is waiting."),
    (r"^Fichier illisible ignoré : (.+)$", r"Unreadable file ignored: \1"),
    (r"^Le réécrire au bon format \(JSON objet\) ; le studio continue sans lui\.$", "Rewrite it in the right format (JSON object); the studio carries on without it."),
    (r"^(\d+) demande\(s\) de la page sans réponse$", r"\1 request(s) from the page without an answer"),
    (r"^Les traiter et répondre dans reponses_assistant\.json\.$", "Handle them and answer in reponses_assistant.json."),
    (r"^La roadmap n'a pas suivi : (.+) est encore « (.+) »$", r"The roadmap fell behind: \1 is still “\2”"),
    (r"^Le commit (.+) \((.*)\) la cite : « (.*) »( ; (\d+) autre\(s\) tâche\(s\) dans le même cas)?$", r"Commit \1 (\2) mentions it: “\3”\4"),
    (r" ; (\d+) autre\(s\) tâche\(s\) dans le même cas", r"; \1 other task(s) in the same case"),
    (r"^Si elle est versée : statut, preuve et fait_le dans \.studio/roadmap\.json et docs/ROADMAP\.md\.$", "If it is merged: status, proof and fait_le in .studio/roadmap.json and docs/ROADMAP.md."),
    (r"^docs/ROADMAP\.md a changé, pas roadmap\.json$", "docs/ROADMAP.md changed, not roadmap.json"),
    (r"^(.+) est plus récent de (\d+) min : le studio montre peut-être un avancement en retard\.$", r"\1 is \2 min newer: the studio may show outdated progress."),
    (r"^Reporter les mêmes changements dans \.studio/roadmap\.json\.$", "Copy the same changes into .studio/roadmap.json."),
]


def traduire_sugg(texte):
    texte = str(texte or "")
    for motif, rempl in SUGG_EN:
        texte = re.sub(motif, rempl, texte)
    return texte


# Studios jumeaux (même règle dans les deux) : tant que le % d'un agent monte, sa fin prévue ne recule pas (un agent qui
# réécrit 5 puis 9 min restantes à 98 % ne fait plus remonter le temps affiché). La fin peut reculer si le % baisse
# (nouvelle étape), si l'ancienne fin est déjà passée (la barre était « en retard »), ou après 1 h sans recalage.
_FIN_MEMO = {}


def fin_sans_recul(cle, pct, fin_t, maintenant=None, memo=None):
    memo = _FIN_MEMO if memo is None else memo
    maintenant = time.time() if maintenant is None else maintenant
    pct = float(pct) if isinstance(pct, (int, float)) and not isinstance(pct, bool) else None
    v = memo.get(cle)
    if (v and pct is not None and v[0] is not None and pct >= v[0] and fin_t > v[1] and v[1] > maintenant
            and maintenant - v[2] < 3600):
        memo[cle] = (pct, v[1], v[2])
        return v[1]
    memo[cle] = (pct, fin_t, maintenant)
    return fin_t


class Memo:
    """Garde un résultat coûteux quelques secondes (et l'ancienne valeur en cas d'erreur)."""
    def __init__(self):
        self.c = {}

    def __call__(self, cle, duree, f):
        t, v = self.c.get(cle, (0, None))
        if time.time() - t > duree:
            try:
                v = f()
            except Exception as e:  # noqa: une source en panne ne doit pas arrêter le studio
                print("erreur", cle, repr(e), flush=True)
            self.c[cle] = (time.time(), v)
        return v


# ------------------------------------------------------------------ le studio d'un projet


class Studio:
    def __init__(self, projet, donnees=None):
        self.projet = os.path.abspath(projet)
        self.donnees = os.path.realpath(donnees) if donnees else None
        self.dossier = os.path.join(self.projet, ".studio")
        self.memo = Memo()
        self.debut = time.time()
        self.auto_srv = None        # automatismes côté serveur (automatismes.py), créés au premier passage
        self.outil_vu = {}          # nom d'outil lourd -> dernière fois vu ouvert (départ : lancement du script)
        # mur d'images : parcours repris là où le passage précédent s'est arrêté, images déjà trouvées et dossiers qui en donnent
        self.mur_iter, self.mur_connus, self.mur_dossiers = {}, {}, {}
        self.depuis = {}
        self.anomalies = {}         # fichier d'agent illisible -> {fichier, raison, vu} : ignoré, signalé
        self.menage_srv = None      # ménage proposé de Santé du PC (sante_machine.Menage), créé au premier passage
        self.lus = {}               # O8 : chemin -> ((date, taille), données) : un fichier inchangé n'est pas relu
        self.passage_debut = 0.0    # C3 : début du passage en cours (0 : aucun passage en cours)
        self.passage_fini = 0       # C3 : fin du dernier passage terminé (horodatage)
        self.dernier_etat = None    # dernier etat.json écrit par la boucle principale (republié par le battement)
        self._sugg_ecrite = (0, None)

    def lire_cache(self, chemin):
        """O8 : JSON relu seulement si sa date ou sa taille a changé (copie rendue : l'appelant peut la modifier).
        FileNotFoundError et erreurs de lecture remontent à l'appelant ; seules les lectures réussies sont gardées."""
        st = os.stat(chemin)
        cle = (st.st_mtime_ns, st.st_size)
        c = self.lus.get(chemin)
        if c and c[0] == cle:
            return json.loads(c[1])
        with open(chemin, encoding="utf-8-sig") as f:      # avec ou sans BOM ; les erreurs remontent (voir plus haut)
            brut = f.read()
        d = json.loads(brut)
        if len(self.lus) > 3000:                            # mémoire bornée (fichiers supprimés entre-temps)
            self.lus.clear()
        self.lus[chemin] = (cle, brut)
        return d

    def lire_json_c(self, chemin, defaut):
        """lire_json avec le cache O8 (fichiers nombreux et rarement modifiés : demandes de la page)."""
        try:
            return self.lire_cache(chemin)
        except Exception:
            return defaut

    def anomalie(self, rel, raison):
        """Fichier illisible noté une fois : « vu » garde la date complète de la PREMIÈRE fois (M11), tant que la raison ne change pas."""
        a = self.anomalies.get(rel)
        if a and a.get("raison") == raison:
            return
        self.anomalies[rel] = {"fichier": rel, "raison": raison, "vu": time.strftime("%Y-%m-%dT%H:%M:%S")}

    def lire_agent(self, chemin):
        """JSON écrit par un agent : illisible (ou pas un objet) = ignoré et noté dans les anomalies, jamais bloquant."""
        rel = os.path.relpath(chemin, self.dossier).replace("\\", "/")
        try:
            d = self.lire_cache(chemin)
            if not isinstance(d, dict):
                raise ValueError("objet JSON attendu")
            self.anomalies.pop(rel, None)
            return d
        except FileNotFoundError:
            self.anomalies.pop(rel, None)
            self.lus.pop(chemin, None)
            return None
        except Exception as e:  # noqa: un fichier fautif ne doit pas arrêter le studio
            if age_min(chemin) is not None and age_min(chemin) < 0.05:
                return None   # en cours d'écriture : on attend le passage suivant
            self.anomalie(rel, court(f"{type(e).__name__} : {e}", 140))
            return None

    def f(self, *p):
        return os.path.join(self.dossier, *p)

    def g(self, *p):
        """M9 : glob dans .studio/ ; le chemin du projet est échappé (un dossier « Mon jeu [v2] » n'est pas un motif)."""
        return glob.glob(os.path.join(glob.escape(self.f(*p[:-1])), p[-1]))

    # ---------------- configuration
    def config(self):
        c = lire_json(self.f("studio.config.json"), {})
        return c if isinstance(c, dict) else {}

    def outils_lourds(self, conf):
        """[{nom, processus[], poste}] : outils lourds surveillés. Défaut : le moteur de la config (Unreal, Godot, Unity…)."""
        postes = [p.get("id") for p in conf.get("postes") or [] if isinstance(p, dict)]
        defaut_poste = next((p for p in postes if p and "moteur" in p), postes[0] if postes else "")
        out = []
        liste = conf.get("outils_lourds")
        if not isinstance(liste, list) or not liste:
            m = conf.get("moteur") if isinstance(conf.get("moteur"), dict) else {}
            liste = [{"nom": m.get("nom") or "moteur", "processus": m.get("processus") or [], "poste": m.get("poste") or defaut_poste}] if m else []
        for o in liste:
            if not isinstance(o, dict):
                continue
            procs = [str(x).lower() for x in (o.get("processus") or []) if isinstance(x, str) and x.strip()]
            if procs:
                out.append({"nom": str(o.get("nom") or procs[0]), "processus": procs, "poste": str(o.get("poste") or defaut_poste)})
        return out

    # ---------------- sources
    def processus(self):
        """Noms des processus en cours (minuscules, sans .exe). Commande fixe, lecture seule."""
        try:
            if os.name == "nt":
                try:
                    noms = exe_windows()          # lecture directe : rapide même quand la machine est saturée
                except Exception:
                    r = subprocess.run(["tasklist", "/fo", "csv", "/nh"], **SUBPROC)
                    noms = [l.split('","')[0].strip('"') for l in r.stdout.splitlines() if l.startswith('"')]
            else:
                r = subprocess.run(["ps", "-A", "-o", "args="], **SUBPROC)   # S13 : « comm » coupe les noms à 15 caractères sous Linux
                noms = [os.path.basename(l.strip().split(" ")[0]) for l in r.stdout.splitlines() if l.strip()]
        except Exception:
            return None
        return [re.sub(r"\.exe$", "", n.lower()) for n in noms]

    def git(self):
        """Branche, fichiers suivis modifiés, derniers commits. Lecture seule (aucun verrou d'index pris)."""
        if not os.path.exists(os.path.join(self.projet, ".git")):
            return None
        env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0",   # sans fsmonitor : pas de démon de surveillance lancé
                   GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="core.fsmonitor", GIT_CONFIG_VALUE_0="false")
        def g(*a):
            return subprocess.run(["git", "-C", self.projet, *a], env=env, **SUBPROC)
        try:
            br = g("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
            st = [l[3:] for l in g("status", "--porcelain", "--untracked-files=no").stdout.splitlines() if len(l) > 3]
            lg = g("log", "-8", "--format=%h%x1f%s%x1f%ct").stdout.splitlines()
            minuit = int(time.mktime(time.localtime()[:3] + (0, 0, 0, 0, 0, -1)))
            jour = g("rev-list", "--count", f"--since={minuit}", "HEAD").stdout.strip()   # commits du jour (conversations du studio)
        except Exception:
            return None
        commits = []
        for l in lg:
            p = l.split("\x1f")
            if len(p) == 3:
                commits.append({"hash": p[0], "sujet": court(p[1], 120), "h": hm(int(p[2] or 0)), "t": int(p[2] or 0)})
        return {"branche": br, "sales": len(st), "fichiers_sales": st[:8], "commits": commits,
                "commits_jour": int(jour) if jour.isdigit() else None}

    def systeme(self, conf):
        try:
            u = shutil.disk_usage(self.projet)
            libre = round(u.free / 1e9, 1)
        except OSError:
            libre = None
        # Santé du PC, « vrai agent » (sante_machine.py) : tous les disques fixes et les températures (si activées)
        try:
            temps = sante_machine.temperatures(self.f("sante"), self.en())
        except Exception as e:  # noqa: une source en panne ne coupe pas le reste
            temps = {"etat": "non_disponible", "message": f"{type(e).__name__} : {e}"[:160], "disques": {}}
        try:
            disques = sante_machine.disques(self.projet, temps.get("disques") or {})
        except Exception:
            disques = []
        return dict({"disque_libre_go": libre, "disques": disques, "temperatures": temps}, **mesures_pc())

    # ---------------- ménage proposé (Santé du PC) : analyse, décision sous la cloche, rien sans « Faire ce ménage »
    def cfg_menage(self, conf):
        """Dossiers du projet et de ses caches seulement : caches du moteur dans le projet, builds (studio.config.json
        « dossiers_builds », dans le projet ou --donnees, sinon Builds/Packaged/Saved/StagedBuilds ; jamais Build/, la configuration de plateforme d Unreal), worktrees fusionnés
        du dépôt du projet, fichiers *.tmp de .studio. La corbeille du disque est exclue par défaut : elle n'est proposée
        que si studio.config.json dit « sante »: {"corbeille": "toute"} (toute la corbeille, fichiers jetés hors du projet compris)."""
        sa = conf.get("sante") if isinstance(conf.get("sante"), dict) else {}
        seuils = conf.get("seuils") if isinstance(conf.get("seuils"), dict) else {}
        builds = []
        for b in (conf.get("dossiers_builds") if isinstance(conf.get("dossiers_builds"), list) else None) or ["Builds", "Packaged", "Saved/StagedBuilds"]:
            if not isinstance(b, str) or not b.strip():
                continue
            p = os.path.realpath(b if os.path.isabs(b) else os.path.join(self.projet, *b.split("/")))
            if (dans(p, self.projet) or (self.donnees and dans(p, self.donnees))) and p != self.projet and os.path.isdir(p):
                builds.append(p)
        return {"projets": [self.projet], "depots": [self.projet] if os.path.exists(os.path.join(self.projet, ".git")) else [],
                "builds": builds, "temporaires": [(self.dossier, r"\.tmp$")], "corbeille": "toute" if sa.get("corbeille") == "toute" else False,
                "seuil_go": float(sa.get("menage_seuil_go") or seuils.get("menage_go") or 30), "seuil_pct": float(sa.get("menage_seuil_pct") or 8),
                "min_go": float(sa.get("menage_min_go") or 1), "langue": "en" if self.en() else "fr", "principale": sa.get("branche_principale")}

    def menage(self, conf, sysinfo, ouverts):
        if self.menage_srv is None:
            self.menage_srv = sante_machine.Menage(self.f("sante"), self.cfg_menage(conf))
        else:
            self.menage_srv.cfg = self.cfg_menage(conf)
        reps = lire_json(self.f("reponses.json"), [])
        reps = {x.get("id"): x for x in (reps if isinstance(reps, list) else []) if isinstance(x, dict) and x.get("id")}
        return self.menage_srv.passer(sysinfo.get("disques") or [], bool(ouverts), reps)

    def session_active(self, conf):
        """Âge (min) du journal de session Claude Code le plus récent du projet (lecture de la date seulement)."""
        d = conf.get("dossier_session") or "auto"
        if d == "auto":
            code = re.sub(r"[^A-Za-z0-9]", "-", self.projet)
            d = os.path.join(os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude"), "projects", code)   # S13
        try:
            fichiers = glob.glob(os.path.join(glob.escape(d), "*.jsonl"))
            return min((age_min(f) for f in fichiers if age_min(f) is not None), default=None)
        except Exception:
            return None

    def activite_claude(self, conf):
        """F (assistant actif) : âge (min) de la dernière écriture d'une session Claude du projet, sous-agents compris
        (une session qui attend un workflow reste « ouverte »). Lecture des dates seulement ; None : aucun journal trouvé."""
        d = conf.get("dossier_session") or "auto"
        if d == "auto":
            code = re.sub(r"[^A-Za-z0-9]", "-", self.projet)
            d = os.path.join(os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude"), "projects", code)
        try:
            fichiers = [(os.path.getmtime(f), f) for f in glob.glob(os.path.join(glob.escape(d), "*.jsonl")) if os.path.isfile(f)]
        except OSError:
            return None
        if not fichiers:
            return None
        recent = max(t for t, _ in fichiers)
        for _, f in sorted(fichiers, reverse=True)[:2]:        # les 2 sessions les plus récentes : leurs sous-agents
            for base, _dirs, noms in os.walk(os.path.join(f[:-6], "subagents")):
                for n in noms:
                    if n.endswith(".jsonl"):
                        try:
                            recent = max(recent, os.path.getmtime(os.path.join(base, n)))
                        except OSError:
                            pass
        return max(0.0, (time.time() - recent) / 60)

    @staticmethod
    def demandes_en_attente(demandes, messages):
        """F : ce qui attend une session Claude : demandes de la page ou auto: pas encore prises, messages « nouvelle »."""
        n_dem = sum(1 for d in demandes or [] if d.get("lancer") and not d.get("vu"))
        n_msg = sum(1 for m in messages or [] if isinstance(m, dict) and m.get("statut") == "nouvelle")
        return n_dem, n_msg

    def roadmap(self):
        r = lire_json(self.f("roadmap.json"), None)
        if not isinstance(r, dict) or not isinstance(r.get("jalons"), list):
            return None
        for j in r["jalons"]:
            if not isinstance(j, dict):
                continue
            if not isinstance(j.get("taches"), list):      # F3 : « taches: null » ou un mauvais type ne fige plus l'alimentation
                if j.get("taches") is not None:
                    self.anomalie("roadmap.json", f"jalon {j.get('id')} : « taches » n'est pas une liste")
                j["taches"] = []
            j["taches"] = [t for t in j["taches"] if isinstance(t, dict) and t.get("id")]
        r["jalons"] = [j for j in r["jalons"] if isinstance(j, dict) and j.get("id")]
        return r

    def progressions(self):
        """{nom de fichier: (données, âge en min)}"""
        out = {}
        for f in self.g("progression", "*.json"):
            d = self.lire_agent(f)
            if isinstance(d, dict):
                out[os.path.basename(f)[:-5]] = (d, age_min(f) or 0)
        return out

    def recrues(self):
        out = []
        for f in sorted(self.g("recrues", "*.json"), key=lambda x: os.path.getmtime(x)):
            if os.path.basename(f) == "index.json":
                continue
            r = self.lire_agent(f)
            if isinstance(r, dict) and r.get("nom"):
                out.append(r)
        return out

    def statuts(self):
        s = lire_json(self.f("demandes", "statuts.json"), {})
        return s if isinstance(s, dict) else {}

    def demandes(self, statuts):
        """Demandes confiées à un poste (recrutement, tâche) : [{fichier, poste, titre, lancer, statut, cree_le}]."""
        out = []
        for f in sorted(self.g("demandes", "*.json")):
            b = os.path.basename(f)
            if b == "statuts.json":
                continue
            d = self.lire_agent(f)
            if not isinstance(d, dict):
                continue
            poste = str(d.get("nom") or d.get("cible") or d.get("poste") or "")
            if not poste:
                continue
            st = statuts.get(b) if isinstance(statuts.get(b), dict) else statuts.get(poste) if isinstance(statuts.get(poste), dict) else {}
            statut = str(st.get("statut") or d.get("statut") or ("en attente" if d.get("lancer", True) else "pas lancé")).lower()
            out.append({"fichier": b, "poste": poste, "titre": court(d.get("titre") or d.get("mission") or d.get("role") or d.get("texte") or "", 120),
                        "lancer": d.get("lancer", True) is not False, "statut": statut, "cree_le": str(d.get("cree_le") or ""),
                        "vu": bool(st.get("statut") or d.get("statut")),   # F : un statut écrit = une session Claude l'a prise
                        "maj": str(st.get("maj") or ""), "type": str(d.get("type") or ""), "origine": str(d.get("origine") or ""),
                        "tache_id": str(d.get("tache_id") or "")})
        return out

    def messages(self):
        """Fil de la page : les 40 derniers messages de l'utilisateur (demandes_vocales/), pour la vue Conversation."""
        def ligne(f):
            d = self.lire_json_c(f, None)
            if isinstance(d, dict) and d.get("texte"):
                return {"id": str(d.get("id") or os.path.basename(f)[:-5])[:80], "cible": str(d.get("cible") or "")[:40],
                        "texte": str(d["texte"])[:600], "cree_le": str(d.get("cree_le") or "")[:19],
                        "statut": str(d.get("statut") or "nouvelle")[:20], "via": str(d.get("via") or "")[:10],
                        **({"pieces": [os.path.basename(str(x))[:90] for x in d["pieces"][:10]]} if isinstance(d.get("pieces"), list) and d["pieces"] else {})}
            return None
        tous = sorted(self.g("demandes_vocales", "*.json"))
        fil = tous[-40:]
        # la dernière demande à l'auditeur et au contrôleur des modèles reste connue de la page même hors des 40 derniers
        avant = [f for c in ("auditeur", "controleur-modeles") for f in [next((x for x in reversed(tous) if x.endswith("_" + c + ".json")), None)] if f and f not in fil]
        return [x for x in map(ligne, sorted(avant) + fil) if x]

    def attentes(self):
        a = lire_json(self.f("attentes.json"), {})
        return {k: v for k, v in a.items() if isinstance(v, dict)} if isinstance(a, dict) else {}

    # ---------------- roadmap : avancement pondéré et tâches disponibles
    @staticmethod
    def exclue(t):
        """Tâche sortie, écartée, abandonnée, reportée, remplacée ou retirée : jamais proposée ni comptée devant un poste.
        Signes : drapeau (retiree, hors_v1, abandonnee) ou mot dans `note` / `etat` (état écrit à la main dans la roadmap)."""
        if any(t.get(k) is True for k in ("retiree", "hors_v1", "abandonnee", "reportee", "remplacee")):
            return True
        return bool(EXCLUS.search(" ".join(str(t.get(k) or "") for k in ("note", "etat"))))

    @staticmethod
    def avance(taches):
        tot = av = reste = 0.0
        for t in taches or []:
            st = t.get("statut") if t.get("statut") in POIDS_AV else "a_faire"
            h = t.get("estimation_h") if isinstance(t.get("estimation_h"), (int, float)) else 0
            w = h if h > 0 else 1
            tot += w
            av += w * POIDS_AV[st]
            reste += (h if h > 0 else 8) * RESTE[st]
        return (round(100 * av / tot, 1) if tot else 0.0), round(reste, 1)

    def en(self):
        """Projet non français (studio.config.json → langue) : textes de la page en anglais."""
        return str((self.memo.c.get("_conf_langue") or "fr"))[:2].lower() != "fr"

    def tx(self, fr, en):
        return en if self.en() else fr

    def version1(self, r):
        taches = [t for j in (r or {}).get("jalons", []) for t in j.get("taches", [])]
        if not taches:
            return {"pct": 0, "texte": self.tx("pas encore de roadmap", "no roadmap yet"), "source": "aucune"}
        pc, reste_h = self.avance(taches)
        valides = sum(1 for t in taches if t.get("statut") in FAITS)
        jalon = next((j for j in r["jalons"] if any(t.get("statut") not in FAITS for t in j.get("taches", []))), None)
        return {"pct": round(pc), "pct_exact": pc, "reste_h": reste_h, "source": "roadmap",
                "texte": self.tx(f"{valides}/{len(taches)} tâches de roadmap versées · avancement pondéré {round(pc)} %",
                                 f"{valides}/{len(taches)} roadmap tasks merged · weighted progress {round(pc)} %"),
                "jalon": ({"id": jalon["id"], "titre": jalon.get("titre", ""), "pct": round(self.avance(jalon["taches"])[0])} if jalon else None)}

    def taches_disponibles(self, r):
        """Tâches « a_faire » ou « en_cours » dont toutes les dépendances sont versées ; les entrées écrites à la main sont gardées."""
        if not r:
            return []
        statut = {t["id"]: t.get("statut") for j in r["jalons"] for t in j["taches"]}
        out = []
        for j in r["jalons"]:
            for t in j["taches"]:
                if t.get("statut") not in ("a_faire", "en_cours") or self.exclue(t):
                    continue
                if any(statut.get(d) not in FAITS for d in t.get("depend_de") or [] if d in statut):
                    continue
                moteur = t.get("moteur") is True
                out.append({"id": t["id"], "origine": "roadmap", "jalon": j["id"], "jalon_titre": j.get("titre", ""),
                            "titre": court(t.get("titre"), 120), "critere": court(t.get("critere"), 160), "statut": t.get("statut"),
                            "poste": t.get("poste") or "", "pour": [t["poste"]] if t.get("poste") else [], "moteur": moteur,
                            "sans_moteur": not moteur, "effort_h": t.get("estimation_h"), "depend_de": t.get("depend_de") or []})
        out.sort(key=lambda x: x["statut"] != "en_cours")
        return out

    def backlog(self):
        """Tâches propres au studio et au skill (.studio/backlog_studio.json, statut « a_corriger ») : pour les postes de métier « studio »."""
        b = lire_json(self.f("backlog_studio.json"), {})
        out = []
        for t in ((b.get("taches") if isinstance(b, dict) else None) or [])[:300]:
            if isinstance(t, dict) and t.get("statut") == "a_corriger" and t.get("id"):
                out.append({"id": "studio-" + court(str(t["id"]), 40), "origine": "backlog", "jalon": "studio", "jalon_titre": "backlog du studio",
                            "titre": court(t.get("titre") or str(t["id"]), 120), "critere": court(t.get("version") or t.get("critere") or "", 160),
                            "statut": "a_faire", "poste": "", "pour": [], "metier": "studio", "moteur": False, "sans_moteur": True,
                            "effort_h": None, "depend_de": []})
        return out

    def ecrire_taches(self, liste):
        chemin = self.f("taches_disponibles.json")
        ancien = lire_json(chemin, None) if os.path.exists(chemin) else {}
        if ancien is None:
            return                                          # F15 : illisible (en cours d'écriture ?) : on ne réécrit pas, les tâches à la main restent
        main = [x for x in ((ancien.get("taches") if isinstance(ancien, dict) else None) or []) if isinstance(x, dict) and x.get("origine") not in ("roadmap", "backlog")]
        doc = {"maj": time.strftime("%Y-%m-%dT%H:%M:%S"), "source": "roadmap.json (a_faire / en_cours, dépendances versées) + backlog_studio.json",
               "taches": main + liste + self.backlog()}
        if not isinstance(ancien, dict) or doc["taches"] != ancien.get("taches"):
            ecrire_json(chemin, doc, indent=1)

    # ---------------- chaîne active
    def chaine_active(self, progs, demandes, ouverts):
        """La chaîne la plus récente : progression modifiée depuis 10 min, outil lourd ouvert, ou demande lancée depuis 15 min."""
        cand = []
        for nom, (d, age) in progs.items():
            if age < CHAINE_MIN and (pct_de(d) is None or pct_de(d) < 100):
                cand.append((age, {"source": f"progression/{nom}.json", "poste": d.get("poste") or nom, "texte": court(d.get("etape") or d.get("texte"), 80), "depuis_min": int(age)}))
        for o in ouverts:
            cand.append((0, {"source": "outil lourd : " + o["nom"], "poste": o["poste"], "texte": o["nom"] + " ouvert", "depuis_min": 0}))
        for dm in demandes:
            if dm["statut"].startswith("lanc"):
                t = iso_vers_t(dm["maj"] or dm["cree_le"])
                if t and time.time() - t < 15 * 60:
                    cand.append(((time.time() - t) / 60, {"source": "demande " + dm["fichier"], "poste": dm["poste"], "texte": dm["titre"], "depuis_min": int((time.time() - t) // 60)}))
        cand.sort(key=lambda x: x[0])
        return cand[0][1] if cand else None

    # ---------------- postes
    def postes(self, conf, r, progs, statuts, demandes, att, ouverts, session_age, chaine=None):
        self.memo.c["_conf_langue"] = conf.get("langue") or "fr"
        tx = self.tx
        recr = self.recrues()
        liste = []
        for p in conf.get("postes") or []:
            if isinstance(p, dict) and p.get("id"):
                liste.append(dict(p, genre="fixe"))
        ids = {p["id"] for p in liste}
        for x in recr:
            if x["nom"] in ids:
                continue
            liste.append({"id": x["nom"], "nom": x.get("nom_affiche") or x["nom"], "role": x.get("role", ""), "couleur": x.get("couleur") or "#6b8f71",
                          "apparence": x.get("apparence") or "aucune", "skills": x.get("skills") or [], "genre": "recrue",
                          "mission": court(x.get("mission"), 300), "cree_le": x.get("cree_le", ""), "poste": x.get("poste", "")})
            ids.add(x["nom"])
        taches = [(j, t) for j in (r or {}).get("jalons", []) for t in j.get("taches", [])]
        sess_poste = conf.get("session_poste") or ("direction" if "direction" in ids else "")
        out = []
        for p in liste:
            pid = p["id"]
            # progression : son fichier, ou le plus frais des fichiers qui déclarent "poste": pid
            prog, prog_nom, prog_age = None, "", None
            for nom, (d, age) in progs.items():
                if nom == pid or d.get("poste") == pid:
                    if prog is None or age < prog_age or (nom == pid and prog_nom != pid and age <= FRAIS_MIN and prog_age > FRAIS_MIN):
                        prog, prog_nom, prog_age = d, nom, age
            st = statuts.get(pid) if isinstance(statuts.get(pid), dict) else {}
            statut = str(st.get("statut") or "").lower()
            pc = pct_de(prog)
            frais = prog is not None and prog_age is not None and prog_age <= FRAIS_MIN
            fini_prog = pc is not None and pc >= 100
            # ce qui reste devant lui
            restantes = [court(x, 80) for x in (prog.get("restantes") if isinstance(prog, dict) and isinstance(prog.get("restantes"), list) else [])][:12]
            rm_taches = [t for _, t in taches if t.get("poste") == pid and t.get("statut") not in FAITS and not self.exclue(t)]
            restantes += [f"{t['id']} · {court(t.get('titre'), 70)}" for t in rm_taches][:12]
            dem = [d for d in demandes if d["poste"] == pid and not d["statut"].startswith("fini") and d["statut"] != "pas lancé"]
            if fini_prog and dem:
                t_prog = time.time() - (prog_age or 0) * 60
                dem = [d for d in dem if iso_vers_t(d["cree_le"]) > t_prog]   # une progression à 100 après la demande la solde
            a = att.get(pid) or {}
            ouvert = next((o for o in ouverts if o["poste"] == pid), None)
            lancee = next((d for d in dem if d["statut"].startswith("lanc")), None)
            # état
            if (isinstance(prog, dict) and prog.get("bloque")) or statut.startswith("bloq"):
                etat = "bloque"
            elif (frais and not fini_prog) or (statut.startswith("lanc") and not fini_prog) or lancee or ouvert:
                etat = "travaille"
            elif pid == sess_poste and session_age is not None and session_age < 3:
                etat = "travaille"
            elif restantes or dem or a.get("attente") or a.get("suite") or (prog is not None and not fini_prog):
                etat = "fini" if fini_prog and not dem and not a else "attend"
            else:
                etat = "disponible"
            # progression affichée
            if pc is not None:
                prog_aff, src = pc, f"progression/{prog_nom}.json"
            elif statut.startswith("fini"):
                prog_aff, src = 100, "statut de la demande"
            elif statut.startswith("lanc") or lancee:
                prog_aff, src = 50, "statut de la demande (lancé)"
            elif rm_taches or any(t.get("poste") == pid for _, t in taches):
                prog_aff, src = round(self.avance([t for _, t in taches if t.get("poste") == pid])[0]), "tâches de roadmap du poste (pondéré)"
            else:
                prog_aff, src = None, ""
            # ligne du bandeau : pictogramme + tâche, jamais vide
            texte_prog = ""
            if isinstance(prog, dict):
                vu = [x for x in (prog.get("etape"), prog.get("texte")) if x]
                texte_prog = court(next((x for x in vu if re.search(r"\b[A-Z]\d+-\d+\b", str(x))), vu[0] if vu else ""), 120)
            if etat == "bloque":
                picto, complet = "⛔", tx("bloqué : ", "blocked: ") + (texte_prog or court(st.get("texte"), 100) or tx("raison à voir", "reason to check"))
            elif etat == "travaille":
                picto = "▶"
                if frais and texte_prog and not fini_prog:
                    complet = texte_prog
                elif lancee:
                    complet = lancee["titre"] or tx("demande lancée", "request started")
                elif ouvert:
                    complet = f"{ouvert['nom']} " + tx("ouvert", "open") + (tx(" : ", ": ") + texte_prog if texte_prog and not fini_prog else "")
                elif pid == sess_poste:
                    complet = tx("orchestre la session", "runs the session")
                else:
                    complet = court(st.get("texte"), 100) or texte_prog or tx("au travail", "at work")
            elif etat in ("attend", "fini"):
                if a.get("attente"):
                    picto, complet = "⏸", tx("attend ", "waiting for ") + court(a["attente"], 100)
                elif dem:
                    picto, complet = "⏸", tx("attend le lancement : ", "waiting to start: ") + (dem[0]["titre"] or dem[0]["fichier"])
                elif prog is not None and not fini_prog and texte_prog:
                    picto, complet = "⏸", tx("en pause", "paused") + f" ({int(prog_age or 0)} min)" + tx(" : ", ": ") + texte_prog
                elif a.get("suite"):
                    picto, complet = "↔", tx("suite : ", "next: ") + court(a["suite"], 100)
                elif restantes:
                    picto, complet = "↔", tx("suite : ", "next: ") + restantes[0]
                else:
                    picto, complet = "⏸", tx("en attente", "waiting")
            else:
                picto, complet = "☕", tx("libre", "free")
            if not str(complet).strip():
                picto, complet = "?", tx("état inconnu", "unknown state")
            q = {"id": pid, "nom": p.get("nom") or pid, "role": p.get("role", ""), "couleur": p.get("couleur", ""), "apparence": p.get("apparence", ""),
                 "skills": p.get("skills") or [], "genre": p["genre"], "etat": etat, "occupe": etat == "travaille", "actif": etat == "travaille",
                 "progression": prog_aff, "progression_source": src, "restant_min": restant_de(prog) if etat in ("travaille", "bloque") else None,
                 "texte": texte_prog or court(st.get("texte"), 120), "tache": complet, "restantes": restantes[:12],
                 "demandes": [{"fichier": d["fichier"], "titre": d["titre"], "statut": d["statut"], "tache_id": d["tache_id"],
                               "origine": d["origine"]} for d in dem][:6],
                 "ligne": {"picto": picto, "texte": court(complet, 40), "complet": court(complet, 200)}}
            # fin de tâche : vrai calme (100 % immobile depuis 5 min, rien devant lui, pas de chaîne à son nom, pas de demande lancée)
            q["calme_min"] = int(prog_age) if prog is not None and prog_age is not None else None
            # temps réel : heure de la dernière nouvelle de l'agent et fin prévue, pour une barre qui avance entre deux écritures
            if prog is not None and prog_age is not None and src.startswith("progression/"):
                try:
                    q["progression_t"] = int(os.path.getmtime(self.f("progression", prog_nom + ".json")))
                except OSError:
                    q["progression_t"] = int(time.time() - prog_age * 60)
                r_ = prog.get("restant_min") if isinstance(prog, dict) else None
                if isinstance(r_, (int, float)) and not isinstance(r_, bool) and r_ >= 0:
                    q["fin_t"] = int(q["progression_t"] + r_ * 60)
                elif isinstance(q.get("restant_min"), (int, float)):
                    q["fin_t"] = int(time.time() + q["restant_min"] * 60)
                if q.get("fin_t"):
                    q["fin_t"] = fin_sans_recul(pid, q.get("progression"), q["fin_t"])
                    q["restant_min"] = max(0, int(round((q["fin_t"] - time.time()) / 60)))
            q["fin_de_tache"] = bool(etat == "disponible" and fini_prog and prog_age is not None and prog_age >= CALME_FIN_MIN
                                     and not lancee and not (chaine and chaine.get("poste") == pid))
            if q["fin_de_tache"]:
                q["fini"] = court(texte_prog or st.get("texte") or "", 120)
            if p["genre"] == "recrue":
                q.update(mission=p.get("mission", ""), cree_le=p.get("cree_le", ""), poste=p.get("poste", ""))
            ancien = self.depuis.get(pid)
            if not ancien or ancien[0] != etat:
                self.depuis[pid] = (etat, int(time.time()))
            q["depuis"] = self.depuis[pid][1]
            out.append(q)
        return out

    # ---------------- analyse continue
    def analyser(self, conf, postes, chaine, ouverts, procs, dispo, gitinfo, sysinfo, demandes):
        sug = []
        self.memo.c["_conf_langue"] = conf.get("langue") or self.memo.c.get("_conf_langue") or "fr"

        def ajoute(id_, gravite, titre, explication, action):
            if self.en():                              # projet non français : suggestions en anglais (la page les montre)
                titre, explication, action = (traduire_sugg(x) for x in (titre, explication, action))
            sug.append({"id": id_, "gravite": gravite, "titre": titre, "explication": explication, "action_proposee": action})
        seuils = conf.get("seuils") if isinstance(conf.get("seuils"), dict) else {}
        inactif_min = float(seuils.get("inactivite_min") or 10)
        for o in self.outils_lourds(conf):
            nb = sum(1 for n in (procs or []) if n in o["processus"])
            if nb:
                self.outil_vu[o["nom"]] = time.time()
            absent = (time.time() - self.outil_vu.get(o["nom"], self.debut)) / 60
            attend = [t for t in dispo if t["moteur"] and (not t["poste"] or t["poste"] == o["poste"])]
            # l'alerte suit la chaîne active : rien tant qu'une chaîne tourne
            if procs is not None and attend and not nb and not chaine and absent >= inactif_min:
                ajoute(f"inactif-{o['nom'].lower()}", "conseil", f"{o['nom']} est inactif alors qu'une tâche l'attend",
                       f"Aucun {o['nom']} depuis {int(absent)} min ni chaîne active ; prochaine tâche : {attend[0]['id']} {attend[0]['titre']}.",
                       f"Relancer la chaîne {o['nom']} sur cette tâche.")
            if nb >= 2:
                ajoute(f"deux-{o['nom'].lower()}", "urgent", f"{nb} {o['nom']} ouverts en même temps",
                       "Une seule chaîne moteur à la fois : risque de conflit et de mémoire.", f"Fermer l'instance de {o['nom']} qui n'appartient pas à la chaîne.")
        go = sysinfo.get("disque_libre_go")
        seuil_go = float(seuils.get("disque_go") or 20)
        if go is not None and go < seuil_go:
            ajoute("disque", "urgent", "Disque du projet presque plein", f"{go} Go libres (seuil {seuil_go:g} Go).",
                   "Déplacer les données lourdes hors du disque du projet ou supprimer d'anciens worktrees.")
        if gitinfo and gitinfo["sales"]:
            ajoute("depot-modifie", "conseil", f"Modifications non commitées sur {gitinfo['branche']}",
                   f"{gitinfo['sales']} fichier(s) suivi(s), par ex. {gitinfo['fichiers_sales'][0]}.", "Les committer ou les ranger avant le prochain versement.")
        for q in postes:
            if q["etat"] == "bloque":
                ajoute(f"bloque-{q['id']}", "urgent", f"{q['nom']} est bloqué", q["tache"], "Lire sa progression et débloquer, ou poser une décision.")
        for nom, (d, age) in self.progressions().items():
            pc = pct_de(d)
            if pc is not None and pc < 100 and 60 <= age <= 24 * 60 and not d.get("bloque"):
                ajoute(f"figee-{nom}", "info", f"Progression figée : {nom}", f"{pc} % depuis {int(age)} min : {court(d.get('texte'), 90)}",
                       "Vérifier si l'agent tourne encore ; sinon le relancer ou passer la tâche en attente.")
        for dm in demandes:
            t = iso_vers_t(dm["cree_le"])
            if dm["lancer"] and dm["statut"] in ("nouvelle", "en attente") and t and time.time() - t > 15 * 60:
                ajoute(f"demande-{dm['fichier']}", "conseil", f"Demande en attente : {dm['poste']}", f"Déposée à {hm(t)} : {dm['titre']}",
                       "Lancer l'agent (voir SKILL.md, « Demandes ») ou répondre pourquoi elle attend.")
        for a in list(self.anomalies.values())[:5]:
            ajoute("illisible-" + re.sub(r"[^a-z0-9]+", "-", a["fichier"].lower()), "urgent", f"Fichier illisible ignoré : {a['fichier']}",
                   a["raison"], "Le réécrire au bon format (JSON objet) ; le studio continue sans lui.")
        for s_ in self.roadmap_en_retard(gitinfo):
            ajoute(*s_)
        vocales = [self.lire_json_c(f, {}) for f in sorted(self.g("demandes_vocales", "*.json"))[-200:]]   # F34 : les 200 plus récentes
        vieilles = [v for v in vocales if isinstance(v, dict) and v.get("statut") == "nouvelle" and iso_vers_t(v.get("cree_le")) and time.time() - iso_vers_t(v.get("cree_le")) > 5 * 60]
        if vieilles:
            ajoute("demandes-vocales", "info", f"{len(vieilles)} demande(s) de la page sans réponse", court(vieilles[0].get("texte"), 120),
                   "Les traiter et répondre dans reponses_assistant.json.")
        return sug

    def roadmap_en_retard(self, gitinfo):
        """roadmap.json en retard : un commit récent cite une tâche encore « a_faire » / « en_cours », ou docs/ROADMAP.md
        a été modifié plus de 10 min après roadmap.json. Seulement des suggestions : la roadmap reste écrite par Claude."""
        r, out = self.roadmap(), []
        if not r:
            return out
        ouvertes = {t["id"]: t for j in r["jalons"] for t in j["taches"] if t.get("statut") in ("a_faire", "en_cours")}
        cites = []
        for c in ((gitinfo or {}).get("commits") or []):
            for tid in ouvertes:
                if len(tid) >= 3 and re.search(r"(?<![\w-])" + re.escape(tid) + r"(?![\w-])", c.get("sujet") or ""):
                    cites.append((tid, c))
        if cites:
            tid, c = cites[0]
            out.append(("roadmap-commit-" + re.sub(r"[^a-z0-9]+", "-", tid.lower()), "conseil",
                        f"La roadmap n'a pas suivi : {tid} est encore « {ouvertes[tid].get('statut')} »",
                        f"Le commit {c.get('hash')} ({c.get('h')}) la cite : « {court(c.get('sujet'), 90)} »"
                        + (f" ; {len(cites) - 1} autre(s) tâche(s) dans le même cas" if len(cites) > 1 else ""),
                        "Si elle est versée : statut, preuve et fait_le dans .studio/roadmap.json et docs/ROADMAP.md."))
        doc = (r.get("sources") or {}).get("document") if isinstance(r.get("sources"), dict) else None
        md = os.path.join(self.projet, doc if isinstance(doc, str) and doc and not os.path.isabs(doc) and ".." not in doc else os.path.join("docs", "ROADMAP.md"))
        try:
            if os.path.getmtime(md) - os.path.getmtime(self.f("roadmap.json")) > 600:
                out.append(("roadmap-md-seul", "conseil", "docs/ROADMAP.md a changé, pas roadmap.json",
                            f"{os.path.basename(md)} est plus récent de {int((os.path.getmtime(md) - os.path.getmtime(self.f('roadmap.json'))) // 60)} min : "
                            "le studio montre peut-être un avancement en retard.", "Reporter les mêmes changements dans .studio/roadmap.json."))
        except OSError:
            pass
        return out

    # ---------------- propositions de renvoi (sous la cloche, jamais appliquées seules)
    def decisions_studio(self, postes, dispo):
        """Recrue libre depuis RENVOI_LIBRE_H heures et plus aucune tâche prête pour son poste : proposition « Renvoyer / Garder ».
        L'identifiant porte le début de la période libre : une fois « Garder », rien n'est reproposé avant la prochaine."""
        reponses = lire_json(self.f("reponses.json"), [])
        repondues = {x.get("id") for x in (reponses if isinstance(reponses, list) else []) if isinstance(x, dict)}
        out = []
        for q in postes:
            if q["genre"] != "recrue" or q["etat"] != "disponible" or time.time() - q["depuis"] < RENVOI_LIBRE_H * 3600:
                continue
            if any(q["id"] in (t.get("pour") or []) or t.get("poste") == q["id"] for t in dispo):
                continue
            ident = f"renvoi-{q['id']}-{q['depuis']}"
            if ident in repondues:
                continue
            h = int((time.time() - q["depuis"]) // 3600)
            out.append({"id": ident, "type": "renvoi", "nom": q["id"], "poste": q["id"],      # M7 : textes dans la langue du projet
                        "titre": self.tx(f"Renvoyer {q['nom']} ?", f"Dismiss {q['nom']}?"),
                        "explication": self.tx(f"Libre depuis {h} h et plus aucune tâche prête pour son poste. Le renvoi archive sa fiche "
                                               "(réembauche possible) ; rien n'est fait sans ta réponse.",
                                               f"Free for {h} h and no task ready for this role any more. Dismissing archives the profile "
                                               "(can be rehired); nothing happens without your answer."),
                        "choix": [{"id": "renvoyer", "libelle": self.tx("Renvoyer", "Dismiss")}, {"id": "garder", "libelle": self.tx("Garder", "Keep")}],
                        "recommande": "garder", "cree_le": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(q["depuis"] + RENVOI_LIBRE_H * 3600))})
        try:                                                # Santé du PC : ménage proposé (une décision, sous la cloche)
            dm = self.menage_srv.decision() if self.menage_srv else None
            if dm and dm["id"] not in repondues:
                out.append(dm)
        except Exception as e:
            print("erreur décision ménage", repr(e), flush=True)
        try:                                                # plan de restructuration ouvert (bouton de l'équipe) : une décision
            import restructuration
            pr = restructuration.plan_ouvert(self.dossier)
            if pr and pr["id"] not in repondues:
                out.append(restructuration.decision(pr))
        except Exception as e:
            print("erreur plan de restructuration", repr(e), flush=True)
        chemin = self.f("decisions_studio.json")
        if lire_json(chemin, None) != out:
            ecrire_json(chemin, out, indent=1)
        return out

    # ---------------- mur d'images
    # ---------------- radio : musiques et ambiances du jeu (lecture seule du projet)
    AUDIO_EXT = (".ogg", ".mp3", ".wav", ".flac", ".opus")

    def _decouverte_audio(self):
        """outils/decouverte_audio.py, mis en cache 10 min (parcours borné à 40 000 entrées)."""
        c = getattr(self, "_decouv_cache", None)
        if c and time.time() - c[0] < 600:
            return c[1]
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("decouverte_audio", os.path.join(ICI, "outils", "decouverte_audio.py"))
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            r = mod.decouvrir(self.projet)
        except Exception as e:  # noqa: la radio n'empêche jamais l'état
            print("découverte audio", repr(e), flush=True)
            r = ([], [])
        self._decouv_cache = (time.time(), r)
        return r

    def _sources_audio(self, conf, cle, i_decouv):
        motifs = [s_.get("motif") for s_ in (conf.get(cle) or []) if isinstance(s_, dict) and isinstance(s_.get("motif"), str)]
        if not motifs:
            return self._decouverte_audio()[i_decouv]
        trouves = set()
        for m in motifs:
            if "{{" in m:
                continue
            racine, motif = self.motif_permis(m)
            if not motif:
                continue
            try:
                fichiers = glob.glob(motif, recursive=True)[:400]
            except Exception:
                continue
            for p in fichiers:
                try:
                    if p.lower().endswith(self.AUDIO_EXT) and dans(os.path.realpath(p), racine):
                        trouves.add(p)
                except OSError:
                    continue
        return sorted(trouves)

    def _remplir_audio(self, genre, dossier, sources, encoder, max_copie, max_n):
        """Copie (ou encode avec ffmpeg) les sources dans .studio/<dossier>/, toujours en tâche de fond ; rend la liste prête."""
        dest = self.f(dossier)
        def nom_de(p, ext):
            return re.sub(r"[^A-Za-z0-9_-]+", "_", os.path.splitext(os.path.basename(p))[0])[:60] + ext
        def remplir():
            try:
                os.makedirs(dest, exist_ok=True)
                ff, garder, n = shutil.which("ffmpeg"), set(), 0
                for p in sources[:max_n]:
                    ext = os.path.splitext(p)[1].lower()
                    try:
                        taille = os.path.getsize(p)
                    except OSError:
                        continue
                    direct = ext in (".ogg", ".mp3") and taille <= max_copie and not (encoder and ff)
                    nom = nom_de(p, ext if direct or not ff else ".ogg")
                    if nom in garder:
                        nom = nom_de(p, "")[:52] + f"_{len(garder)}" + os.path.splitext(nom)[1]
                    garder.add(nom); dst = os.path.join(dest, nom)
                    if os.path.exists(dst) and (not direct or os.path.getsize(dst) == taille):
                        continue
                    if ff and not direct:
                        args = [ff, "-v", "error", "-y", "-i", p] + (["-ac", "1", "-ar", "32000", "-q:a", "1"] if encoder else ["-ar", "44100", "-q:a", "4"]) + ["-c:a", "libvorbis", "-f", "ogg", dst + ".part"]
                        try:
                            rc = subprocess.run(args, timeout=240, stdin=subprocess.DEVNULL, capture_output=True,
                                                creationflags=(0x08000000 | 0x00004000) if os.name == "nt" else 0).returncode
                        except Exception:
                            rc = -1
                        if rc != 0:                   # M10 : encodage raté : rien n'est publié, le .part est effacé
                            try:
                                os.remove(dst + ".part")
                            except OSError:
                                pass
                            garder.discard(nom)
                            continue
                    elif taille <= max_copie:
                        shutil.copyfile(p, dst + ".part")
                    if os.path.exists(dst + ".part"):
                        os.replace(dst + ".part", dst); n += 1
                for f in os.listdir(dest):            # seul ce dossier est nettoyé : un morceau retiré du projet disparaît
                    if f not in garder and not f.endswith(".part"):
                        try:
                            os.remove(os.path.join(dest, f))
                        except OSError:
                            pass
            except Exception as e:  # noqa: un fichier illisible ne coupe pas la radio
                print(genre, repr(e), flush=True)
            finally:
                setattr(self, "_en_cours_" + genre, False)
        if sources and not getattr(self, "_en_cours_" + genre, False) and time.time() - getattr(self, "_fait_" + genre, 0) > 60:
            setattr(self, "_en_cours_" + genre, True); setattr(self, "_fait_" + genre, time.time())
            import threading
            threading.Thread(target=remplir, daemon=False).start()   # jamais dans le passage : le premier etat.json n'attend pas ffmpeg ;
            # pas « daemon » : avec --une-fois, le processus finit les copies après avoir écrit etat.json
        if not os.path.isdir(dest):
            return []
        return sorted(dossier + "/" + f for f in os.listdir(dest) if f.lower().endswith(self.AUDIO_EXT))[:max_n]

    def musiques(self, conf):
        """Radio du studio : TOUTES les musiques du jeu (conf["sources_musique"] ; sinon découverte automatique,
        outils/decouverte_audio.py : MUS_/music_/bgm_/ost_… ou dossiers music/musique/bgm/ost/soundtrack, en .ogg .mp3 .wav
        .flac .opus), dans .studio/musique/. OGG et MP3 de 15 Mo au plus copiés tels quels ; le reste encodé en OGG avec
        ffmpeg (sans ffmpeg : copié s'il fait 15 Mo au plus). 200 morceaux au plus, en tâche de fond."""
        return self._remplir_audio("musiques", "musique", self._sources_audio(conf, "sources_musique", 0), False, 15 * 1024 * 1024, 200)

    def ambiances(self, conf):
        """Radio du studio : petits passages des ambiances du jeu (conf["sources_ambiance"] ; sinon découverte automatique),
        dans .studio/ambiance/. Avec ffmpeg : OGG mono 32 kHz léger ; sans ffmpeg : copie des fichiers de 6 Mo au plus.
        120 au plus, en tâche de fond ; rend tout de suite ce qui est déjà prêt."""
        mus = set(self._sources_audio(conf, "sources_musique", 0))
        return self._remplir_audio("ambiances", "ambiance", [p for p in self._sources_audio(conf, "sources_ambiance", 1) if p not in mus], True, 6 * 1024 * 1024, 120)

    def images(self, conf):
        """Copie les images récentes de sources_images dans .studio/mur/ (servies par le serveur) ; renvoie la liste."""
        mur = self.f("mur")
        os.makedirs(mur, exist_ok=True)
        vus = {}
        limite = time.time() - 4   # un fichier encore en cours d'écriture attend le passage suivant
        # borne (gros projet Unreal ou Unity) : 2 000 chemins examinés et 2 s au plus par passage, dossiers de cache ignorés.
        # Pour ne pas manquer les images récentes d'un très gros dossier : le parcours reprend où il s'était arrêté, les images
        # déjà trouvées sont revérifiées, et les dossiers qui ont déjà donné des images sont relus d'abord à chaque passage.
        budget, t0 = [MUR_EXAMENS_MAX], time.time()
        sources = {}
        for s in conf.get("sources_images") or []:
            if not isinstance(s, dict) or not isinstance(s.get("motif"), str) or "{{" in s["motif"]:
                continue
            racine, motif = self.motif_permis(s["motif"])
            if motif:
                sources[s["motif"]] = (racine, s, motif)

        def examiner(p, racine, s):
            if not dans(os.path.realpath(p), racine):
                return
            try:                                   # dossiers de cache cherchés sous la racine seulement (le projet peut vivre sous « Temp »)
                if MUR_CACHES.search("/" + os.path.relpath(p, racine).replace("\\", "/")):
                    return
            except ValueError:
                pass
            ext = os.path.splitext(p)[1].lower()
            if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif") or TECHNIQUE.search(os.path.splitext(os.path.basename(p))[0]):
                return
            try:
                t, n = os.path.getmtime(p), os.path.getsize(p)
            except OSError:
                self.mur_connus.pop(p, None)
                return
            if t < limite and 0 < n <= IMAGE_MAX_OCTETS:
                vus[p] = (t, ext, s)
                self.mur_connus[p] = s["motif"]
                self.mur_dossiers.pop(os.path.dirname(p), None)       # le plus récent en dernier, 200 dossiers au plus
                self.mur_dossiers[os.path.dirname(p)] = s["motif"]
                while len(self.mur_dossiers) > 200:
                    self.mur_dossiers.pop(next(iter(self.mur_dossiers)))

        for p, m in list(self.mur_connus.items()):          # 1. images déjà trouvées (encore là ? modifiées ?)
            if m in sources:
                examiner(p, sources[m][0], sources[m][1])
            else:
                self.mur_connus.pop(p, None)
        for d, m in list(self.mur_dossiers.items())[-40:]:   # 2. dossiers productifs : leurs nouvelles images
            if m not in sources or time.time() - t0 > MUR_SECONDES_MAX:
                continue
            try:
                with os.scandir(d) as it:
                    for k, e in enumerate(it):
                        if k >= 300:
                            break
                        if e.is_file() and e.path not in vus:
                            examiner(e.path, sources[m][0], sources[m][1])
            except OSError:
                self.mur_dossiers.pop(d, None)
        for cle, (racine, s, motif) in sources.items():     # 3. parcours, repris là où il s'était arrêté
            if budget[0] <= 0 or time.time() - t0 > MUR_SECONDES_MAX:
                break
            it = self.mur_iter.get(cle)
            if it is None:
                try:
                    it = self.mur_iter[cle] = glob.iglob(motif, recursive=True)
                except Exception:
                    continue
            while budget[0] > 0 and time.time() - t0 <= MUR_SECONDES_MAX:
                p = next(it, None)
                if p is None:
                    self.mur_iter.pop(cle, None)            # parcours fini : il recommence au passage suivant
                    break
                budget[0] -= 1
                if p not in vus:
                    examiner(p, racine, s)
        if len(self.mur_connus) > 5000:                      # mémoire bornée : on garde les plus récentes
            garder_ = dict(sorted(vus.items(), key=lambda x: -x[1][0])[:2000])
            self.mur_connus = {p: m for p, m in self.mur_connus.items() if p in garder_}
        out, garder = [], set()
        for p, (t, ext, s) in sorted(vus.items(), key=lambda x: -x[1][0])[:IMAGES_MAX]:
            nom = hashlib.sha1((p + str(int(t))).encode("utf-8", "replace")).hexdigest()[:16] + ext
            dst = os.path.join(mur, nom)
            try:
                if not os.path.exists(dst):
                    shutil.copyfile(p, dst + ".tmp")
                    os.replace(dst + ".tmp", dst)
            except OSError:
                continue
            garder.add(nom)
            titre = os.path.splitext(os.path.basename(p))[0]
            if titre.lower() in ("rendu", "capture", "image", "screenshot"):
                titre = os.path.basename(os.path.dirname(p)) + " · " + titre
            out.append({"src": "mur/" + nom, "titre": titre.replace("_", " ")[:80], "libelle": str(s.get("libelle") or "Image")[:40],
                        "poste": str(s.get("poste") or ""), "h": time.strftime("%d/%m %H:%M", time.localtime(t)), "t": int(t)})
        for f in os.listdir(mur):   # seul le dossier mur/ est nettoyé
            if f not in garder:
                try:
                    os.remove(os.path.join(mur, f))
                except OSError:
                    pass
        return out

    def motif_permis(self, m):
        """(racine, motif absolu) si le motif reste dans le projet ou dans --donnees ; sinon (None, None)."""
        m = m.replace("\\", "/")
        if m.startswith("{donnees}/"):
            if not self.donnees:
                return None, None
            racine, rel = self.donnees, m[len("{donnees}/"):]
        elif os.path.isabs(m) or re.match(r"^[A-Za-z]:", m):
            return None, None
        else:
            racine, rel = os.path.realpath(self.projet), m
        parties = rel.split("/")
        if not rel or ".." in parties:
            return None, None
        fixe = []
        for x in parties:   # partie fixe du motif (avant le premier joker) : doit rester dans la racine
            if any(c in x for c in "*?["):
                break
            fixe.append(x)
        if not dans(os.path.realpath(os.path.join(racine, *fixe)), racine):
            return None, None
        return racine, os.path.join(glob.escape(racine), *parties)   # M9 : racine échappée, seul le motif est un motif

    # ---------------- rapport de l'assistant
    def prochain_rapport(self):
        reg = lire_json(self.f("reglages.json"), {})
        prof = lire_json(self.f("profil.json"), {})
        freq = (reg.get("frequence_rapport_min") if isinstance(reg, dict) else None) or ((prof.get("assistant") or {}).get("frequence_rapport_min") if isinstance(prof, dict) else None) or 120
        freq = freq if freq in (15, 30, 60, 120) else 120
        rap = lire_json(self.f("rapport_assistant.json"), {})
        t = iso_vers_t((rap or {}).get("heure")) if isinstance(rap, dict) else 0
        if not t and isinstance(rap, dict) and rap.get("heure"):
            t = os.path.getmtime(self.f("rapport_assistant.json"))
        prochain = (t + freq * 60) if t else time.time()
        return {"frequence_min": freq, "dernier": hm(t) if t else "", "prochain": hm(max(prochain, time.time())),
                "dans_min": max(0, int(round((prochain - time.time()) / 60)))}

    # ---------------- passage complet
    def quetes(self, tout=False):
        """S4 : un passage de quetes.py toutes les 60 s, tout de suite quand la page vient de répondre à une quête ou de changer
        un réglage des quêtes (mode du style, agents de soutien).
        Lecture seule hors de .studio/ ; une erreur ne fige jamais l'alimentation."""
        try:
            if ICI not in sys.path:
                sys.path.insert(0, ICI)
            import quetes
            ch = self.f("quetes_reponses.json")
            mt = os.path.getmtime(ch) if os.path.exists(ch) else 0
            reg = lire_json(self.f("reglages.json"), {})          # mode du style, agents de soutien, quêtes : effet au passage suivant
            reg = reg if isinstance(reg, dict) else {}
            mt = (mt, json.dumps({k: v for k, v in reg.items() if k in ("habillage_mode", "auditeur", "controle_modeles", "quetes_actives",
                                  "quetes_secondaires") or str(k).startswith("soutien.")}, sort_keys=True, default=str))
            t0, res, mt0 = self.memo.c.get("_quetes", (0, None, 0))
            if tout or res is None or mt != mt0 or time.time() - t0 >= 60:
                e = quetes.passe(self.projet)
                res = {"resume": quetes.resume(e), "xp": int(e.get("xp") or 0)}
                self.memo.c["_quetes"] = (time.time(), res, mt)
            return res
        except Exception as e:
            print("erreur quêtes", repr(e), flush=True)
            return (self.memo.c.get("_quetes", (0, None, 0))[1]) or {}

    def passer(self, tout=False):
        """Un passage complet. C3 : son début et sa fin sont notés ; le battement ne republie etat.json que pendant un
        passage jeune (BATTEMENT_MAX_S) : une boucle vraiment figée laisse vieillir etat.json et la veille la relance."""
        self.passage_debut = time.time()
        try:
            return self._passer(tout)
        finally:
            self.passage_debut = 0.0

    def ecrire_suggestions(self, sug):
        """O6 : suggestions.json réécrit seulement si la liste change (ou toutes les 10 min, pour sa date « maj »)."""
        t, ancienne = self._sugg_ecrite
        if ancienne == sug and time.time() - t < 600 and os.path.exists(self.f("suggestions.json")):
            return
        ecrire_json(self.f("suggestions.json"), {"maj": time.strftime("%Y-%m-%dT%H:%M:%S"), "suggestions": sug}, indent=1)
        self._sugg_ecrite = (time.time(), sug)

    def _passer(self, tout=False):
        conf = self.config()
        try:
            r = self.roadmap()
        except Exception as e:                              # une roadmap inattendue ne fige jamais l'alimentation
            self.anomalie("roadmap.json", court(f"{type(e).__name__} : {e}", 140))
            r = None
        for rel in [k for k in self.anomalies if not os.path.exists(self.f(*k.split("/")))]:
            self.anomalies.pop(rel, None)                   # F16 : le fichier fautif a été supprimé : l'alerte part avec lui
        progs = self.progressions()
        statuts = self.statuts()
        demandes = self.demandes(statuts)
        att = self.attentes()
        procs = self.memo("processus", 20, self.processus)
        ouverts = [o for o in self.outils_lourds(conf) if procs and any(n in o["processus"] for n in procs)]
        session_age = self.memo("session", 30, lambda: self.session_active(conf))
        chaine = self.chaine_active(progs, demandes, ouverts)
        postes = self.postes(conf, r, progs, statuts, demandes, att, ouverts, session_age, chaine)
        dispo = self.memo("taches", 0 if tout else 60, lambda: self.taches_disponibles(r)) or []
        gitinfo = self.memo("git", 0 if tout else 60, self.git)
        sysinfo = self.memo("systeme", 0 if tout else 60, lambda: self.systeme(conf)) or {}
        images = self.memo("images", 0 if tout else 90, lambda: self.images(conf)) or []
        if tout or time.time() - self.memo.c.get("_sugg", (0, None))[0] > 60:
            try:
                sug = self.analyser(conf, postes, chaine, ouverts, procs, dispo, gitinfo, sysinfo, demandes)
                self.ecrire_suggestions(sug)
                self.ecrire_taches(dispo)
                self.decisions_studio(postes, dispo)
                self.memo.c["_sugg"] = (time.time(), sug)
            except Exception as e:
                print("erreur analyse", repr(e), flush=True)
        sug = self.memo.c.get("_sugg", (0, []))[1] or []
        sante = sante_pc(sysinfo, self.en())
        try:
            sante["menage"] = self.memo("menage", 0 if tout else 15, lambda: self.menage(conf, sysinfo, ouverts))
        except Exception as e:
            sante["menage"] = {"statut": "erreur", "erreur": f"{type(e).__name__} : {e}"[:200]}
        sante.update(sante_complements(sysinfo, self.en()))
        # S37 : fin de tâche, tyrannie et embauche tournent ici, sans aucun onglet ouvert ; la page ne fait plus qu'afficher
        try:
            if self.auto_srv is None:
                if ICI not in sys.path:
                    sys.path.insert(0, ICI)
                import automatismes
                self.auto_srv = automatismes.Automatismes(self)
            autos = self.auto_srv.passer(conf, postes, r, progs, ouverts, chaine, sante)
        except Exception as e:
            autos = {"serveur": False, "erreur": f"{type(e).__name__} : {e}"[:200]}
        qres = self.quetes(tout) if conf.get("mode") == "travail" else {}
        etat = {
            "version": 1, "projet": conf.get("nom_projet") or os.path.basename(self.projet), "heure": time.strftime("%H:%M:%S"),
            "horodatage": int(time.time()), "version1": self.version1(r), "postes": postes, "chaine_active": chaine,
            "outils_lourds": [{"nom": o["nom"], "poste": o["poste"], "ouvert": o in ouverts} for o in self.outils_lourds(conf)],
            "git": gitinfo, "systeme": {k: v for k, v in sysinfo.items() if k not in ("disques", "temperatures")},   # O6 : déjà dans « sante »
            "sante": sante, "automatismes": autos, "images": images, "musiques": self.memo("musiques", 300, lambda: self.musiques(conf)) or [], "ambiances": self.memo("ambiances", 600, lambda: self.ambiances(conf)) or [], "nb_suggestions": len(sug),
            "alertes": [s for s in sug if s["gravite"] == "urgent"][:5], "taches_dispo": len(dispo), "rapport": self.prochain_rapport(),
            "anomalies": list(self.anomalies.values())[:20], "messages": self.memo("messages", 0 if tout else 5, self.messages) or [],
        }
        try:                                                # F : « aucune session Claude depuis N min : tes demandes attendent »
            n_dem, n_msg = self.demandes_en_attente(demandes, etat["messages"])
            seuils = conf.get("seuils") if isinstance(conf.get("seuils"), dict) else {}
            seuil = float(seuils.get("session_min") or 15)
            age = self.memo("activite_claude", 30, lambda: self.activite_claude(conf))
            etat["session"] = {"age_min": None if age is None else round(age, 1), "seuil_min": seuil, "demandes": n_dem, "messages": n_msg,
                               "absente": (age is None or age >= seuil) and (n_dem + n_msg) > 0}
        except Exception as e:
            etat["session"] = {"erreur": f"{type(e).__name__} : {e}"[:160]}
        if qres:                                            # S4 : quêtes (résumé) ; l'XP des quêtes s'ajoute au niveau (la page l'additionne)
            etat["quetes"], etat["xp"] = qres.get("resume"), qres.get("xp", 0)
        fini = int(time.time())
        etat["passage_fini"] = fini                          # C3 : seule la boucle principale l'écrit ; la veille juge dessus
        with ECRITURE:
            ecrire_json(self.f("etat.json"), etat)
            self.dernier_etat, self.passage_fini = etat, fini
        return etat


def verrou(studio, forcer):
    """Une seule boucle par projet : .studio/studio_etat.verrou (pid et heure de création), rafraîchi à chaque passage,
    écrit d'un coup, effacé à la sortie ; un verrou dont le processus est mort ou n'est plus le nôtre est ignoré."""
    if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from veille_studio import ecrire_verrou, lire_pid, verrou_vivant
    v = studio.f("studio_etat.verrou")
    if not forcer:
        pid = verrou_vivant(v)
        if pid and pid != os.getpid():
            raise SystemExit(f"une alimentation tourne déjà pour ce projet (pid {pid}) ; --forcer pour passer outre")
    if lire_pid(v) != os.getpid() or not getattr(verrou, "pose", False):
        ecrire_verrou(v)
        verrou.pose = True
    else:
        os.utime(v, None)


def exe_windows():
    """Noms des programmes en cours sous Windows, lus directement (Toolhelp32 par ctypes), sans lancer de processus :
    « tasklist » peut mettre des dizaines de secondes quand la machine est saturée (moteur qui compile, agents)."""
    import ctypes

    class PE(ctypes.Structure):
        _fields_ = [("dwSize", ctypes.c_ulong), ("cntUsage", ctypes.c_ulong), ("th32ProcessID", ctypes.c_ulong),
                    ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", ctypes.c_ulong), ("cntThreads", ctypes.c_ulong),
                    ("th32ParentProcessID", ctypes.c_ulong), ("pcPriClassBase", ctypes.c_long), ("dwFlags", ctypes.c_ulong),
                    ("szExeFile", ctypes.c_wchar * 260)]
    k = ctypes.windll.kernel32
    k.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    h = k.CreateToolhelp32Snapshot(2, 0)
    noms = []
    try:
        e = PE()
        e.dwSize = ctypes.sizeof(PE)
        ok = k.Process32FirstW(ctypes.c_void_p(h), ctypes.byref(e))
        while ok:
            noms.append(e.szExeFile)
            ok = k.Process32NextW(ctypes.c_void_p(h), ctypes.byref(e))
    finally:
        k.CloseHandle(ctypes.c_void_p(h))
    return noms


BATTEMENT_MAX_S = 600   # C3 : au-delà, un passage est jugé figé : plus de battement (la veille relance, voir veille_studio.py)


def battement(s, intervalle):
    """Battement de cœur : pendant un passage plus long que prévu (premier passage, machine saturée, git lent),
    etat.json est republié (horodatage à jour, calcul_en_cours) pour que la page n'affiche pas « figée » à tort.
    C3 : seulement pendant les BATTEMENT_MAX_S premières secondes d'un passage. Au-delà, la boucle est figée :
    etat.json vieillit, la page l'affiche et la veille relance l'alimentation. « passage_fini » n'est jamais avancé ici.
    M8 : écriture sous le même verrou que la boucle, date du fichier revérifiée juste avant d'écrire."""

    def boucle():
        while True:
            time.sleep(max(2.0, intervalle / 2))
            try:
                chemin = s.f("etat.json")
                debut = s.passage_debut
                if not debut or time.time() - debut > BATTEMENT_MAX_S or not isinstance(s.dernier_etat, dict):
                    continue
                with ECRITURE:
                    if not os.path.exists(chemin) or time.time() - os.path.getmtime(chemin) < max(10.0, intervalle * 1.5):
                        continue
                    if s.passage_debut != debut:            # le passage vient de finir : etat.json est déjà neuf
                        continue
                    d = dict(s.dernier_etat)
                    d["heure"], d["horodatage"], d["calcul_en_cours"] = time.strftime("%H:%M:%S"), int(time.time()), True
                    ecrire_json(chemin, d)
            except Exception as e:
                print("erreur battement", repr(e), flush=True)
    threading.Thread(target=boucle, daemon=True).start()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Alimentation du studio gamedev : etat.json, suggestions.json, taches_disponibles.json.")
    ap.add_argument("--projet", required=True, help="dossier du projet (lit et écrit dans <projet>/.studio)")
    ap.add_argument("--une-fois", action="store_true", help="un seul passage, puis s'arrête")
    ap.add_argument("--intervalle", type=float, default=10, help="secondes entre deux passages (défaut 10)")
    ap.add_argument("--duree-h", type=float, default=12, help="s'arrête seul après ce nombre d'heures (défaut 12 ; 0 = sans limite)")
    ap.add_argument("--forcer", action="store_true", help="ignorer le verrou d'une autre boucle")
    ap.add_argument("--donnees", default=None, help="dossier de données hors du projet (motifs « {donnees}/… » du mur d'images)")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # console sans UTF-8 : les pictogrammes deviennent « ? »
    except Exception:
        pass
    s = Studio(a.projet, a.donnees)
    if not os.path.isdir(s.dossier):
        raise SystemExit(f"pas de dossier .studio dans {s.projet}")
    # reprend les « depuis » du passage précédent (même état = même départ)
    ancien = lire_json(s.f("etat.json"), {})
    if isinstance(ancien, dict) and ancien:
        # le battement du premier passage republie l'état précédent, SANS son « passage_fini » (vieux, d'un autre
        # processus) : sinon la veille (branche « autre alimentation ») jugerait figé un premier passage normal
        s.dernier_etat = {k: v for k, v in ancien.items() if k != "passage_fini"}
    for q in (ancien.get("postes") if isinstance(ancien, dict) else None) or []:
        if isinstance(q, dict) and q.get("id") and q.get("etat") and isinstance(q.get("depuis"), int):
            s.depuis[q["id"]] = (q["etat"], q["depuis"])
    if a.une_fois:
        e = s.passer(tout=True)
        print(f"etat.json écrit : {len(e['postes'])} postes, V1 {e['version1']['pct']} %, {e['nb_suggestions']} suggestion(s), {len(e['images'])} image(s)")
        for q in e["postes"]:
            print(f"  {q['id']:<22} {q['etat']:<10} {'assis ' if q['occupe'] else 'debout'} {q['ligne']['picto']} {q['ligne']['texte']}")
        return
    print(f"alimentation du studio : {s.dossier} (toutes les {a.intervalle:g} s)", flush=True)
    fin = time.time() + a.duree_h * 3600 if a.duree_h > 0 else float("inf")
    battement(s, a.intervalle)
    while time.time() < fin:
        try:
            verrou(s, a.forcer)
            s.passer()
        except SystemExit:
            raise
        except Exception as e:
            print("erreur", repr(e), flush=True)
        time.sleep(max(1.0, a.intervalle))


if __name__ == "__main__":
    sys.exit(main())
