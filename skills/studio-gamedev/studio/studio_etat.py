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
import time

sys.dont_write_bytecode = True   # jamais de __pycache__ dans le dossier du skill
FAITS = ("verse", "ecart")
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
        r = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        u, mu, mt = [float(x) for x in r.stdout.strip().splitlines()[0].split(",")]
        return {"gpu": int(u), "vram_pct": int(round(100 * mu / mt)) if mt else None}
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


def sante_pc(sy):
    alertes = []
    if (sy.get("cpu_sature_min") or 0) >= 8:
        alertes.append(f"processeur saturé ({sy['cpu_sature_min']}/10 min au-dessus de 92 %)")
    if sy.get("memoire_pct") is not None and sy["memoire_pct"] > 90:
        alertes.append(f"mémoire utilisée à {sy['memoire_pct']} %")
    if sy.get("disque_libre_go") is not None and sy["disque_libre_go"] < 30:
        alertes.append(f"disque presque plein ({sy['disque_libre_go']} Go libres)")
    charge = max([v for v in (sy.get("cpu"), sy.get("memoire_pct"), sy.get("gpu")) if isinstance(v, (int, float))] or [0])
    pauses = ["espacer les tâches lourdes ; les attributions automatiques attendent la fin de la saturation",
              "un seul outil lourd (moteur, rendu 3D) à la fois"] if alertes else []
    return {"sature": bool(alertes), "alertes": alertes, "pauses": pauses, "charge": int(charge)}



def dans(p, racine):
    return p == racine or p.startswith(racine.rstrip(os.sep) + os.sep)




def lire_json(chemin, defaut):
    """JSON avec ou sans BOM (certains outils écrivent un BOM UTF-8)."""
    try:
        with open(chemin, encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return defaut


def ecrire_json(chemin, donnees, indent=None):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=indent)
    os.replace(tmp, chemin)


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
    s = str(s or "")
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
    fin = str(prog.get("fin", "") or "")
    t = iso_vers_t(fin)
    if not t:
        m = re.match(r"^(\d{1,2})[:h](\d{2})$", fin)
        if m:
            lt = time.localtime()
            t = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, int(m.group(1)), int(m.group(2)), 0, 0, 0, -1))
            if t < time.time() - 6 * 3600:
                t += 86400
    return round(max(0.0, (t - time.time()) / 60), 1) if t else None


def pct_de(prog):
    if isinstance(prog, dict) and isinstance(prog.get("pct"), (int, float)) and not isinstance(prog.get("pct"), bool):
        return max(0, min(100, int(round(prog["pct"]))))
    return None


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
        self.outil_vu = {}          # nom d'outil lourd -> dernière fois vu ouvert (départ : lancement du script)
        self.depuis = {}
        self.anomalies = {}         # fichier d'agent illisible -> {fichier, raison, vu} : ignoré, signalé

    def lire_agent(self, chemin):
        """JSON écrit par un agent : illisible (ou pas un objet) = ignoré et noté dans les anomalies, jamais bloquant."""
        rel = os.path.relpath(chemin, self.dossier).replace("\\", "/")
        try:
            with open(chemin, encoding="utf-8-sig") as f:
                d = json.load(f)
            if not isinstance(d, dict):
                raise ValueError("objet JSON attendu")
            self.anomalies.pop(rel, None)
            return d
        except FileNotFoundError:
            self.anomalies.pop(rel, None)
            return None
        except Exception as e:  # noqa: un fichier fautif ne doit pas arrêter le studio
            if age_min(chemin) is not None and age_min(chemin) < 0.05:
                return None   # en cours d'écriture : on attend le passage suivant
            self.anomalies[rel] = {"fichier": rel, "raison": court(f"{type(e).__name__} : {e}", 140), "vu": time.strftime("%H:%M")}
            return None

    def f(self, *p):
        return os.path.join(self.dossier, *p)

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
                r = subprocess.run(["tasklist", "/fo", "csv", "/nh"], **SUBPROC)
                noms = [l.split('","')[0].strip('"') for l in r.stdout.splitlines() if l.startswith('"')]
            else:
                r = subprocess.run(["ps", "-A", "-o", "comm="], **SUBPROC)
                noms = [os.path.basename(l.strip()) for l in r.stdout.splitlines() if l.strip()]
        except Exception:
            return None
        return [re.sub(r"\.exe$", "", n.lower()) for n in noms]

    def git(self):
        """Branche, fichiers suivis modifiés, derniers commits. Lecture seule (aucun verrou d'index pris)."""
        if not os.path.exists(os.path.join(self.projet, ".git")):
            return None
        env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
        def g(*a):
            return subprocess.run(["git", "-C", self.projet, *a], env=env, **SUBPROC)
        try:
            br = g("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
            st = [l[3:] for l in g("status", "--porcelain", "--untracked-files=no").stdout.splitlines() if len(l) > 3]
            lg = g("log", "-8", "--format=%h%x1f%s%x1f%ct").stdout.splitlines()
        except Exception:
            return None
        commits = []
        for l in lg:
            p = l.split("\x1f")
            if len(p) == 3:
                commits.append({"hash": p[0], "sujet": court(p[1], 120), "h": hm(int(p[2] or 0)), "t": int(p[2] or 0)})
        return {"branche": br, "sales": len(st), "fichiers_sales": st[:8], "commits": commits}

    def systeme(self, conf):
        try:
            u = shutil.disk_usage(self.projet)
            libre = round(u.free / 1e9, 1)
        except OSError:
            libre = None
        return dict({"disque_libre_go": libre}, **mesures_pc())

    def session_active(self, conf):
        """Âge (min) du journal de session Claude Code le plus récent du projet (lecture de la date seulement)."""
        d = conf.get("dossier_session") or "auto"
        if d == "auto":
            code = re.sub(r"[^A-Za-z0-9]", "-", self.projet)
            d = os.path.join(os.path.expanduser("~"), ".claude", "projects", code)
        try:
            fichiers = glob.glob(os.path.join(d, "*.jsonl"))
            return min((age_min(f) for f in fichiers if age_min(f) is not None), default=None)
        except Exception:
            return None

    def roadmap(self):
        r = lire_json(self.f("roadmap.json"), None)
        if not isinstance(r, dict) or not isinstance(r.get("jalons"), list):
            return None
        for j in r["jalons"]:
            if not isinstance(j, dict):
                continue
            j.setdefault("taches", [])
            j["taches"] = [t for t in j["taches"] if isinstance(t, dict) and t.get("id")]
        r["jalons"] = [j for j in r["jalons"] if isinstance(j, dict) and j.get("id")]
        return r

    def progressions(self):
        """{nom de fichier: (données, âge en min)}"""
        out = {}
        for f in glob.glob(self.f("progression", "*.json")):
            d = self.lire_agent(f)
            if isinstance(d, dict):
                out[os.path.basename(f)[:-5]] = (d, age_min(f) or 0)
        return out

    def recrues(self):
        out = []
        for f in sorted(glob.glob(self.f("recrues", "*.json")), key=lambda x: os.path.getmtime(x)):
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
        for f in sorted(glob.glob(self.f("demandes", "*.json"))):
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
                        "maj": str(st.get("maj") or ""), "type": str(d.get("type") or ""), "origine": str(d.get("origine") or ""),
                        "tache_id": str(d.get("tache_id") or "")})
        return out

    def messages(self):
        """Fil de la page : les 40 derniers messages de l'utilisateur (demandes_vocales/), pour la vue Conversation."""
        out = []
        for f in sorted(glob.glob(self.f("demandes_vocales", "*.json")))[-40:]:
            d = lire_json(f, None)
            if isinstance(d, dict) and d.get("texte"):
                out.append({"id": str(d.get("id") or os.path.basename(f)[:-5])[:80], "cible": str(d.get("cible") or "")[:40],
                            "texte": str(d["texte"])[:600], "cree_le": str(d.get("cree_le") or "")[:19],
                            "statut": str(d.get("statut") or "nouvelle")[:20], "via": str(d.get("via") or "")[:10]})
        return out

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

    def version1(self, r):
        taches = [t for j in (r or {}).get("jalons", []) for t in j.get("taches", [])]
        if not taches:
            return {"pct": 0, "texte": "pas encore de roadmap", "source": "aucune"}
        pc, reste_h = self.avance(taches)
        valides = sum(1 for t in taches if t.get("statut") in FAITS)
        jalon = next((j for j in r["jalons"] if any(t.get("statut") not in FAITS for t in j.get("taches", []))), None)
        return {"pct": round(pc), "pct_exact": pc, "reste_h": reste_h, "source": "roadmap",
                "texte": f"{valides}/{len(taches)} tâches de roadmap versées · avancement pondéré {round(pc)} %",
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

    def ecrire_taches(self, liste):
        chemin = self.f("taches_disponibles.json")
        ancien = lire_json(chemin, {})
        main = [x for x in ((ancien.get("taches") if isinstance(ancien, dict) else None) or []) if isinstance(x, dict) and x.get("origine") != "roadmap"]
        doc = {"maj": time.strftime("%Y-%m-%dT%H:%M:%S"), "source": "roadmap.json (a_faire / en_cours, dépendances versées)", "taches": main + liste}
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
                picto, complet = "⛔", "bloqué : " + (texte_prog or court(st.get("texte"), 100) or "raison à voir")
            elif etat == "travaille":
                picto = "▶"
                if frais and texte_prog and not fini_prog:
                    complet = texte_prog
                elif lancee:
                    complet = lancee["titre"] or "demande lancée"
                elif ouvert:
                    complet = f"{ouvert['nom']} ouvert" + (f" : {texte_prog}" if texte_prog and not fini_prog else "")
                elif pid == sess_poste:
                    complet = "orchestre la session"
                else:
                    complet = court(st.get("texte"), 100) or texte_prog or "au travail"
            elif etat in ("attend", "fini"):
                if a.get("attente"):
                    picto, complet = "⏸", "attend " + court(a["attente"], 100)
                elif dem:
                    picto, complet = "⏸", "attend le lancement : " + (dem[0]["titre"] or dem[0]["fichier"])
                elif prog is not None and not fini_prog and texte_prog:
                    picto, complet = "⏸", f"en pause ({int(prog_age or 0)} min) : {texte_prog}"
                elif a.get("suite"):
                    picto, complet = "↔", "suite : " + court(a["suite"], 100)
                elif restantes:
                    picto, complet = "↔", "suite : " + restantes[0]
                else:
                    picto, complet = "⏸", "en attente"
            else:
                picto, complet = "☕", "libre"
            if not str(complet).strip():
                picto, complet = "?", "état inconnu"
            q = {"id": pid, "nom": p.get("nom") or pid, "role": p.get("role", ""), "couleur": p.get("couleur", ""), "apparence": p.get("apparence", ""),
                 "skills": p.get("skills") or [], "genre": p["genre"], "etat": etat, "occupe": etat == "travaille", "actif": etat == "travaille",
                 "progression": prog_aff, "progression_source": src, "restant_min": restant_de(prog) if etat in ("travaille", "bloque") else None,
                 "texte": texte_prog or court(st.get("texte"), 120), "tache": complet, "restantes": restantes[:12],
                 "demandes": [{"fichier": d["fichier"], "titre": d["titre"], "statut": d["statut"], "tache_id": d["tache_id"],
                               "origine": d["origine"]} for d in dem][:6],
                 "ligne": {"picto": picto, "texte": court(complet, 40), "complet": court(complet, 200)}}
            # fin de tâche : vrai calme (100 % immobile depuis 5 min, rien devant lui, pas de chaîne à son nom, pas de demande lancée)
            q["calme_min"] = int(prog_age) if prog is not None and prog_age is not None else None
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
        def ajoute(id_, gravite, titre, explication, action):
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
        vocales = [lire_json(f, {}) for f in glob.glob(self.f("demandes_vocales", "*.json"))]
        vieilles = [v for v in vocales if isinstance(v, dict) and v.get("statut") == "nouvelle" and iso_vers_t(v.get("cree_le")) and time.time() - iso_vers_t(v.get("cree_le")) > 5 * 60]
        if vieilles:
            ajoute("demandes-vocales", "info", f"{len(vieilles)} demande(s) de la page sans réponse", court(vieilles[0].get("texte"), 120),
                   "Les traiter et répondre dans reponses_assistant.json.")
        return sug

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
            out.append({"id": ident, "type": "renvoi", "nom": q["id"], "poste": q["id"], "titre": f"Renvoyer {q['nom']} ?",
                        "explication": f"Libre depuis {h} h et plus aucune tâche prête pour son poste. Le renvoi archive sa fiche "
                                       "(réembauche possible) ; rien n'est fait sans ta réponse.",
                        "choix": [{"id": "renvoyer", "libelle": "Renvoyer"}, {"id": "garder", "libelle": "Garder"}],
                        "recommande": "garder", "cree_le": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(q["depuis"] + RENVOI_LIBRE_H * 3600))})
        chemin = self.f("decisions_studio.json")
        if lire_json(chemin, None) != out:
            ecrire_json(chemin, out, indent=1)
        return out

    # ---------------- mur d'images
    def musiques(self, conf):
        """Radio du studio : les musiques du jeu de l'utilisateur, copiées dans .studio/musique/ (servies par le serveur).
        Sources : conf["sources_musique"] (motifs dans le projet, comme sources_images) ; sinon les dossiers « music » ou
        « musique » des trois premiers niveaux du projet. Rien s'il n'y en a pas. 20 morceaux, 15 Mo chacun au plus."""
        motifs = [s_.get("motif") for s_ in (conf.get("sources_musique") or []) if isinstance(s_, dict) and isinstance(s_.get("motif"), str)]
        if not motifs:
            motifs = [f"{p}[Mm]usi[cq]*/{e}" for p in ("", "*/", "*/*/") for e in ("*.ogg", "*.mp3")]
        dossier = self.f("musique")
        trouves = {}
        for m in motifs:
            if "{{" in m:
                continue
            racine, motif = self.motif_permis(m)
            if not motif:
                continue
            try:
                fichiers = glob.glob(motif, recursive=True)[:200]
            except Exception:
                continue
            for p in fichiers:
                ext = os.path.splitext(p)[1].lower()
                if ext in (".ogg", ".mp3", ".wav") and dans(os.path.realpath(p), racine) and 0 < os.path.getsize(p) <= 15 * 1024 * 1024:
                    trouves[p] = ext
        if not trouves:
            return []
        os.makedirs(dossier, exist_ok=True)
        out, garder = [], set()
        for p, ext in sorted(trouves.items())[:20]:
            nom = re.sub(r"[^A-Za-z0-9_-]+", "_", os.path.splitext(os.path.basename(p))[0])[:60] + ext
            dst = os.path.join(dossier, nom)
            try:
                if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(p):
                    shutil.copyfile(p, dst + ".tmp")
                    os.replace(dst + ".tmp", dst)
            except OSError:
                continue
            garder.add(nom)
            out.append("musique/" + nom)
        for f in os.listdir(dossier):          # seul le dossier musique/ est nettoyé
            if f not in garder:
                try:
                    os.remove(os.path.join(dossier, f))
                except OSError:
                    pass
        return out

    def images(self, conf):
        """Copie les images récentes de sources_images dans .studio/mur/ (servies par le serveur) ; renvoie la liste."""
        mur = self.f("mur")
        os.makedirs(mur, exist_ok=True)
        vus = {}
        limite = time.time() - 4   # un fichier encore en cours d'écriture attend le passage suivant
        for s in conf.get("sources_images") or []:
            if not isinstance(s, dict) or not isinstance(s.get("motif"), str) or "{{" in s["motif"]:
                continue
            racine, motif = self.motif_permis(s["motif"])
            if not motif:
                continue
            try:
                fichiers = glob.glob(motif, recursive=True)
            except Exception:
                continue
            for p in fichiers[:4000]:
                if not dans(os.path.realpath(p), racine):
                    continue
                ext = os.path.splitext(p)[1].lower()
                if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif") or TECHNIQUE.search(os.path.splitext(os.path.basename(p))[0]):
                    continue
                try:
                    t, n = os.path.getmtime(p), os.path.getsize(p)
                except OSError:
                    continue
                if t < limite and 0 < n <= IMAGE_MAX_OCTETS:
                    vus[p] = (t, ext, s)
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
        return racine, os.path.join(racine, *parties)

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
    def passer(self, tout=False):
        conf = self.config()
        r = self.roadmap()
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
                ecrire_json(self.f("suggestions.json"), {"maj": time.strftime("%Y-%m-%dT%H:%M:%S"), "suggestions": sug}, indent=1)
                self.ecrire_taches(dispo)
                self.decisions_studio(postes, dispo)
                self.memo.c["_sugg"] = (time.time(), sug)
            except Exception as e:
                print("erreur analyse", repr(e), flush=True)
        sug = self.memo.c.get("_sugg", (0, []))[1] or []
        etat = {
            "version": 1, "projet": conf.get("nom_projet") or os.path.basename(self.projet), "heure": time.strftime("%H:%M:%S"),
            "horodatage": int(time.time()), "version1": self.version1(r), "postes": postes, "chaine_active": chaine,
            "outils_lourds": [{"nom": o["nom"], "poste": o["poste"], "ouvert": o in ouverts} for o in self.outils_lourds(conf)],
            "git": gitinfo, "systeme": sysinfo, "sante": sante_pc(sysinfo), "images": images, "musiques": self.memo("musiques", 300, lambda: self.musiques(conf)) or [], "nb_suggestions": len(sug),
            "alertes": [s for s in sug if s["gravite"] == "urgent"][:5], "taches_dispo": len(dispo), "rapport": self.prochain_rapport(),
            "anomalies": list(self.anomalies.values())[:20], "messages": self.memo("messages", 0 if tout else 5, self.messages) or [],
        }
        ecrire_json(self.f("etat.json"), etat)
        return etat


def verrou(studio, forcer):
    """Une seule boucle par projet : .studio/studio_etat.verrou (pid), rafraîchi à chaque passage."""
    v = studio.f("studio_etat.verrou")
    a = age_min(v)
    if a is not None and a < 1 and not forcer:
        try:
            pid = int(open(v, encoding="utf-8").read().strip() or 0)
        except (OSError, ValueError):
            pid = 0
        if pid and pid != os.getpid():
            raise SystemExit(f"une alimentation tourne déjà pour ce projet (pid {pid}) ; --forcer pour passer outre")
    with open(v, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))


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
        sys.stdout.reconfigure(errors="replace")   # console sans UTF-8 : les pictogrammes deviennent « ? »
    except Exception:
        pass
    s = Studio(a.projet, a.donnees)
    if not os.path.isdir(s.dossier):
        raise SystemExit(f"pas de dossier .studio dans {s.projet}")
    # reprend les « depuis » du passage précédent (même état = même départ)
    ancien = lire_json(s.f("etat.json"), {})
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
