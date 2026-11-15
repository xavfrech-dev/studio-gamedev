"""Conversation de Claude Code pour le panneau « Conversation » du studio (lecture seule, servie en local seulement).

Lit le transcript JSONL de la session active (le .jsonl le plus récent de ~/.claude/projects/<slug du projet>/, sans les
sous-agents) en flux : on ne relit que la fin (offset). Garde seulement ce que Claude Code affiche : le texte de
l'utilisateur et le texte de l'assistant. Jamais les résultats d'outils, les appels d'outils, les pensées, les rappels
système, les notifications de tâches ni les conversations des sous-agents. Rien n'est copié ailleurs.
Images (15/11) : les images envoyées au chat (SendUserFile) sont jointes au message suivant de l'assistant (champ « images »,
chemins locaux ; la page les montre par GET /api/image), ou forment un message à elles si aucun texte ne suit.
"""
import glob
import json
import os
import re

DEBUT_MAX = 2_000_000          # premier appel : au plus les 2 derniers Mo du fichier
LOT_MAX = 4_000_000            # appels suivants : au plus 4 Mo d'un coup
CACHE = re.compile(r"^\s*<(system-reminder|task-notification|command-|local-command|bash-|user-prompt-submit-hook|tool_use_error)", re.I)


def slug(projet):
    return re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(projet))


def session_active(dossier):
    """Le transcript le plus récent du dossier de projets de Claude Code (fichiers du niveau 1 seulement)."""
    try:
        fichiers = [f for f in glob.glob(os.path.join(glob.escape(dossier), "*.jsonl")) if os.path.isfile(f)]   # M9 : crochets
        return max(fichiers, key=os.path.getmtime) if fichiers else None
    except OSError:
        return None


def _message_images(d, images):
    """Message de l'assistant fait seulement d'images envoyées au chat (pas de texte après elles dans ce lot)."""
    return {"id": str(d.get("uuid") or d.get("id") or "envoi") + "-images", "role": "assistant", "texte": "", "images": images[:24],
            "t": str(d.get("timestamp") or "")[:40]}


def _texte_visible(d):
    """(role, texte) si la ligne est un message que Claude Code affiche, sinon None."""
    t = d.get("type")
    if t not in ("user", "assistant") or d.get("isSidechain") or d.get("isMeta") or d.get("isCompactSummary"):
        return None
    m = d.get("message") or {}
    c = m.get("content")
    morceaux = []
    if isinstance(c, str):
        morceaux = [c]
    elif isinstance(c, list):
        for x in c:
            if isinstance(x, dict) and x.get("type") == "text" and isinstance(x.get("text"), str):
                morceaux.append(x["text"])
    texte = "\n\n".join(s for s in morceaux if s and s.strip() and not CACHE.match(s)).strip()
    if not texte:
        return None
    return ("utilisateur" if t == "user" else "assistant"), texte


IMAGES_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif")


def _images_envoyees(d):
    """Images montrées à l'utilisateur dans le chat par cette ligne (appel SendUserFile de l'assistant), chemins absolus."""
    if d.get("type") != "assistant" or d.get("isSidechain"):
        return []
    c = (d.get("message") or {}).get("content")
    out = []
    for b in c if isinstance(c, list) else []:
        if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "SendUserFile" and isinstance(b.get("input"), dict):
            for f in b["input"].get("files") or []:
                if isinstance(f, str) and f.strip().lower().endswith(IMAGES_EXT):
                    f = f.strip()
                    if not os.path.isabs(f) and d.get("cwd"):
                        f = os.path.join(str(d["cwd"]), f)
                    out.append(os.path.normpath(f))
    return out


def lire(chemin, depuis=None):
    """{"fichier", "offset", "messages": [{id, role, texte, t}], "debut": bool}. depuis=None : la fin du fichier."""
    if not chemin or not os.path.isfile(chemin):
        return {"fichier": None, "offset": 0, "messages": []}
    taille = os.path.getsize(chemin)
    reprise = depuis is None or depuis > taille or depuis < 0
    debut = max(0, taille - DEBUT_MAX) if reprise else depuis
    fin = min(taille, debut + (DEBUT_MAX if reprise else LOT_MAX))
    with open(chemin, "rb") as f:
        f.seek(debut)
        bloc = f.read(fin - debut)
    if reprise and debut > 0:                       # on commence à la première ligne entière
        i = bloc.find(b"\n")
        bloc, debut = (bloc[i + 1:], debut + i + 1) if i >= 0 else (b"", fin)
    dernier = bloc.rfind(b"\n")                     # on s'arrête à la dernière ligne entière (la suivante est peut-être en cours)
    if dernier < 0:
        if fin - debut >= (DEBUT_MAX if reprise else LOT_MAX):   # une seule ligne plus grande que le lot : on la saute
            return {"fichier": os.path.basename(chemin), "offset": fin, "messages": [], "debut": reprise}
        return {"fichier": os.path.basename(chemin), "offset": debut, "messages": [], "debut": reprise}
    lignes, offset = bloc[:dernier].split(b"\n"), debut + dernier + 1
    out, images, dernier_envoi = [], [], {}
    for l in lignes:
        if b'"type":"user"' not in l and b'"type":"assistant"' not in l and b'"type": "user"' not in l and b'"type": "assistant"' not in l:
            continue
        if b'"type":"tool_result"' in l and b'"type":"text"' not in l:   # O14 : résultat d'outil seul, jamais affiché
            continue
        try:
            d = json.loads(l.decode("utf-8", "replace"))
        except ValueError:
            continue
        envoyees = _images_envoyees(d)            # images envoyées au chat : jointes au texte de l'assistant qui suit
        if envoyees:
            images += [x for x in envoyees if x not in images]
            dernier_envoi = d
        v = _texte_visible(d)
        if v and v[0] == "utilisateur" and images:  # personne n'a commenté les images : elles restent un message à elles
            out.append(_message_images(dernier_envoi, images))
            images = []
        if v:
            m = {"id": str(d.get("uuid") or d.get("id") or len(out)), "role": v[0], "texte": v[1][:20000], "t": str(d.get("timestamp") or "")[:40]}
            if v[0] == "assistant" and images:
                m["images"], images = images[:24], []
            out.append(m)
    if images:
        out.append(_message_images(dernier_envoi, images))
    return {"fichier": os.path.basename(chemin), "offset": offset, "messages": out[-200:], "debut": reprise}
