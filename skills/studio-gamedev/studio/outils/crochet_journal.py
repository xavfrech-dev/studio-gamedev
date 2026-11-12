"""Crochet « Stop » de Claude Code pour le studio : recopie chaque réponse de l'assistant dans
<projet>/.studio/journal_assistant.json ; le studio l'affiche en rapport et dans la conversation.

Installé seulement avec l'accord de l'utilisateur (installer_crochet.py), dans <projet>/.claude/settings.local.json.
Lit sur l'entrée standard le JSON du crochet (transcript_path, session_id, cwd). Ne bloque jamais Claude : sort toujours 0.
- lit seulement la fin de la transcription (4 Mo) ;
- reprend tous les blocs de texte du tour (depuis le dernier message de l'utilisateur), sans les sous-agents ;
- masque clés, jetons et adresses électroniques ;
- verrou + fichier temporaire unique + 5 essais d'écriture ; un fichier illisible n'est jamais écrasé ;
- n'écrit rien si le projet n'a pas de dossier .studio/.
Bibliothèque standard seulement."""
import json
import os
import re
import sys
import time

MAX = 60
FIN = 4 * 1024 * 1024
SECRETS = [
    (re.compile(r"\b(sk|tsk|pk|rk)[-_][A-Za-z0-9_\-]{16,}"), "[clé masquée]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), "[jeton masqué]"),
    (re.compile(r"\bgithub" + r"_pat_[A-Za-z0-9_]{20,}"), "[jeton masqué]"),   # motif coupé en deux : ce n'est pas un jeton
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[clé masquée]"),
    (re.compile(r"(?i)\b(api[_-]?key|token|secret|password|mot de passe)\s*[:=]\s*\S{8,}"), r"\1 : [masqué]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[adresse masquée]"),
]


def masquer(t):
    for motif, rempl in SECRETS:
        t = motif.sub(rempl, t)
    return t


def fin_du_fichier(chemin):
    with open(chemin, "rb") as f:
        f.seek(0, 2)
        taille = f.tell()
        f.seek(max(0, taille - FIN))
        brut = f.read()
    if taille > FIN:
        brut = brut[brut.find(b"\n") + 1:]
    return brut.decode("utf-8", "replace").splitlines()


def reponse_du_tour(chemin):
    try:
        lignes = fin_du_fichier(chemin)
    except OSError:
        return ""
    blocs = []
    for ligne in reversed(lignes):
        try:
            o = json.loads(ligne)
        except Exception:
            continue
        if o.get("isSidechain"):
            continue
        m = o.get("message") or {}
        c = m.get("content")
        if o.get("type") == "user" and (isinstance(c, str) or (isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "text" for b in c))):
            break
        if m.get("role") == "assistant" and isinstance(c, list):
            t = "\n".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text").strip()
            if t:
                blocs.append(t)
    return "\n\n".join(reversed(blocs)).strip()


class Verrou:
    def __init__(self, chemin):
        self.chemin, self.fd = chemin, None

    def __enter__(self):
        for _ in range(50):
            try:
                self.fd = os.open(self.chemin, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return self
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(self.chemin) > 30:
                        os.remove(self.chemin)
                except OSError:
                    pass
                time.sleep(0.1)
        return self

    def __exit__(self, *a):
        if self.fd is not None:
            os.close(self.fd)
            try:
                os.remove(self.chemin)
            except OSError:
                pass


def main():
    try:
        d = json.loads(sys.stdin.read() or "{}")
    except Exception:
        d = {}
    chemin = d.get("transcript_path") or ""
    if not chemin or os.sep + "subagents" + os.sep in os.path.normpath(chemin) or os.path.basename(chemin).startswith("agent-"):
        return
    projet = os.environ.get("CLAUDE_PROJECT_DIR") or d.get("cwd") or os.getcwd()
    studio = os.path.join(projet, ".studio")
    if not os.path.isdir(studio):
        return
    texte = masquer(reponse_du_tour(chemin))
    if not texte:
        return
    sortie = os.path.join(studio, "journal_assistant.json")
    session = str(d.get("session_id") or "")[:8]
    with Verrou(sortie + ".lock"):
        try:
            with open(sortie, encoding="utf-8-sig") as f:
                liste = json.load(f)
            if not isinstance(liste, list):
                return
        except FileNotFoundError:
            liste = []
        except Exception:
            return
        if liste and isinstance(liste[-1], dict) and liste[-1].get("texte") == texte[:12000]:
            return
        premiere = next((l for l in texte.splitlines() if l.strip()), "")[:120]
        liste.append({"id": time.strftime("%Y%m%d-%H%M%S") + (f"-{session}" if session else ""), "cree_le": time.strftime("%Y-%m-%dT%H:%M:%S"),
                      "titre": premiere.strip("*# _"), "texte": texte[:12000], "source": "crochet"})
        tmp = f"{sortie}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(liste[-MAX:], f, ensure_ascii=False, indent=1)
        for essai in range(5):
            try:
                os.replace(tmp, sortie)
                return
            except PermissionError:
                time.sleep(0.2 * (essai + 1))
        try:
            os.remove(tmp)
        except OSError:
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
