"""studio/jsonio.py : lecture et écriture des fichiers JSON du studio, en un seul endroit.

- lire() : tolère le BOM (utf-8-sig) ; fichier absent ou illisible → la valeur par défaut.
- lire_strict() : même lecture, mais l'erreur remonte (pour qui doit distinguer « absent » et « illisible »).
- ecrire() / ecrire_texte() : écriture atomique. Un temporaire au nom unique dans le même dossier, vidé sur le disque
  (fsync), puis os.replace. Sous Windows, la page ou un agent peut tenir le fichier un court instant : nouvel essai
  (jusqu'à ~2 s). En cas d'échec, le temporaire est effacé et l'erreur remonte (FichierOccupe si le fichier reste tenu).
- verrou(chemin) : un verrou par fichier dans un même processus (RLock, donc réentrant). ecrire() le prend toujours ;
  une lecture-modification-écriture l'entoure : « with jsonio.verrou(ch): d = lire(ch, {}); ...; ecrire(ch, d) ».

Python 3.8 et plus, bibliothèque standard seulement.
"""
import contextlib
import json
import os
import tempfile
import threading
import time

ESSAIS = 6                     # nouveaux essais de os.replace quand Windows refuse (fichier tenu)
_VERROUS = {}
_VERROU_TABLE = threading.Lock()


class FichierOccupe(PermissionError):
    """Le fichier est resté tenu par un autre programme pendant tous les essais (reste une PermissionError)."""


def _cle(chemin):
    return os.path.normcase(os.path.abspath(chemin))


def verrou_de(chemin):
    """Le verrou (RLock) propre à ce fichier dans ce processus."""
    cle = _cle(chemin)
    with _VERROU_TABLE:
        v = _VERROUS.get(cle)
        if v is None:
            v = _VERROUS[cle] = threading.RLock()
        return v


@contextlib.contextmanager
def verrou(chemin):
    v = verrou_de(chemin)
    with v:
        yield


def lire_strict(chemin, encoding="utf-8-sig"):
    """Lit un JSON (avec ou sans BOM). FileNotFoundError, ValueError (JSON invalide) ou OSError remontent."""
    with open(chemin, encoding=encoding) as f:
        return json.load(f)


def lire(chemin, defaut=None):
    """Lit un JSON (avec ou sans BOM) ; absent, illisible ou invalide → defaut."""
    try:
        return lire_strict(chemin)
    except Exception:
        return defaut


def lire_texte(chemin, defaut=None, encoding="utf-8-sig"):
    try:
        with open(chemin, encoding=encoding) as f:
            return f.read()
    except Exception:
        return defaut


def _remplacer(tmp, chemin, essais):
    for essai in range(essais):
        try:
            os.replace(tmp, chemin)
            return
        except PermissionError:
            if essai == essais - 1:
                raise
            time.sleep(0.1 * (essai + 1))


def ecrire_texte(chemin, texte, encoding="utf-8", essais=ESSAIS, fsync=True, newline=None):
    """Écrit un texte de façon atomique (temporaire unique, fsync, os.replace avec nouveaux essais)."""
    dossier = os.path.dirname(os.path.abspath(chemin))
    os.makedirs(dossier, exist_ok=True)
    with verrou(chemin):
        fd, tmp = tempfile.mkstemp(dir=dossier, prefix="." + os.path.basename(chemin) + ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding=encoding, newline=newline) as f:
                f.write(texte)
                if fsync:
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except OSError:
                        pass
            try:
                _remplacer(tmp, chemin, max(1, int(essais)))
            except PermissionError as e:
                raise FichierOccupe(e.errno, f"fichier occupé ({os.path.basename(chemin)})", chemin) from e
        except BaseException:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise


def ecrire(chemin, donnees, indent=1, ensure_ascii=False, sort_keys=False, default=None, essais=ESSAIS, fsync=True, newline=None):
    """Écrit un JSON de façon atomique. La sérialisation se fait avant d'ouvrir quoi que ce soit : une donnée
    impossible à écrire (TypeError) ne laisse ni temporaire ni fichier à moitié écrit."""
    texte = json.dumps(donnees, ensure_ascii=ensure_ascii, indent=indent, sort_keys=sort_keys, default=default)
    ecrire_texte(chemin, texte, essais=essais, fsync=fsync, newline=newline)
