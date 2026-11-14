"""Essai de compatibilité Python 3.10 (B1 de l'audit du 14/11), bibliothèque standard seulement.

Les README promettent « Python 3.10+ ». Une f-string écrite à la mode 3.12 (antislash ou mêmes guillemets dans une
expression, commentaire, saut de ligne dans une f-string simple) est une erreur de syntaxe sous 3.10 et 3.11 : le module
ne se charge plus, souvent sans alerte. Cet essai relit chaque .py du studio (dossier du skill, sous-dossiers compris) :
- avec la grammaire 3.10 (ast.parse, feature_version=(3, 10)) ;
- jeton par jeton, l'intérieur de chaque f-string (sous Python 3.12 ou plus, qui découpe les f-strings) ;
- et cherche les noms de la bibliothèque standard apparus après 3.10 (tomllib, datetime.UTC, typing.Self, except*…).
Limite : rien ne tourne sous un vrai 3.10 ; c'est une lecture du code.

Usage : python -I -B essai_compat310.py [--studio <dossier du studio>]      code 0 = tout vert
"""
import argparse
import ast
import io
import os
import re
import sys
import tokenize

for _flux in (sys.stdout, sys.stderr):                 # sortie en UTF-8, même redirigée (Windows, cp1252)
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
sys.dont_write_bytecode = True
ICI = os.path.dirname(os.path.abspath(__file__))
SAUTER = {"__pycache__", ".git", "node_modules"}
RECENTS = re.compile(r"\b(import tomllib|from tomllib|datetime\.UTC\b|from datetime import [^\n]*\bUTC\b|typing\.Self\b|from typing import [^\n]*\bSelf\b|"
                     r"ExceptionGroup|except\s*\*|asyncio\.TaskGroup|itertools\.batched|from itertools import [^\n]*\bbatched\b|"
                     r"enum\.StrEnum|from enum import [^\n]*\bStrEnum\b|\.add_note\()")


def fichiers(racine):
    for d, sous, noms in os.walk(racine):
        sous[:] = sorted(s for s in sous if s not in SAUTER)
        for n in sorted(noms):
            if n.endswith(".py"):
                yield os.path.join(d, n)


def fstrings_312(src):
    """Constructions de f-string refusées avant 3.12 : [(ligne, motif)]. Vide si Python < 3.12 (pas de jetons FSTRING_*)."""
    if not hasattr(tokenize, "FSTRING_START"):
        return []
    out, pile = [], []                                  # pile : [guillemets, profondeur d'accolades]
    for t in tokenize.generate_tokens(io.StringIO(src).readline):
        if t.type == tokenize.FSTRING_START:
            q = t.string.lstrip("rRbBfFuU")
            if pile and pile[-1][1] > 0 and any(q[0] == s[0][0] for s in pile):
                out.append((t.start[0], "f-string imbriquée avec les mêmes guillemets"))
            pile.append([q, 0])
        elif t.type == tokenize.FSTRING_END:
            pile.pop()
        elif pile:
            h = pile[-1]
            if t.type == tokenize.OP and t.string == "{":
                h[1] += 1
            elif t.type == tokenize.OP and t.string == "}":
                h[1] = max(0, h[1] - 1)
            elif h[1] > 0:
                if t.type == tokenize.STRING:
                    if "\\" in t.string:
                        out.append((t.start[0], "antislash dans une expression de f-string"))
                    if any(t.string.lstrip("rRbBfFuU")[0] == s[0][0] for s in pile):
                        out.append((t.start[0], "mêmes guillemets dans une expression de f-string"))
                elif t.type == tokenize.COMMENT:
                    out.append((t.start[0], "commentaire dans une f-string"))
                elif t.type in (tokenize.NL, tokenize.NEWLINE) and len(h[0]) == 1:
                    out.append((t.start[0], "saut de ligne dans une f-string simple"))
    return out


def verifier(racine):
    problemes, n = [], 0
    for p in fichiers(racine):
        n += 1
        rel = os.path.relpath(p, racine)
        try:
            with open(p, encoding="utf-8-sig") as f:
                src = f.read()
        except (OSError, UnicodeDecodeError) as e:
            problemes.append(f"{rel} : illisible ({e})")
            continue
        try:
            ast.parse(src, p, feature_version=(3, 10))
        except SyntaxError as e:
            problemes.append(f"{rel}:{e.lineno} : grammaire 3.10 refusée ({e.msg})")
        try:
            problemes += [f"{rel}:{l} : {m}" for l, m in fstrings_312(src)]
        except (tokenize.TokenError, SyntaxError) as e:
            problemes.append(f"{rel} : découpage impossible ({e})")
        if os.path.abspath(p) == os.path.abspath(__file__):     # ce fichier cite ces noms pour les chercher
            continue
        for i, ligne in enumerate(src.splitlines(), 1):
            if ligne.lstrip().startswith("#"):
                continue
            m = RECENTS.search(ligne)
            if m:
                problemes.append(f"{rel}:{i} : « {m.group(0)} » n'existe pas en 3.10")
    return n, problemes


def essai_detecteur():
    """Le détecteur voit bien le défaut B1 (antislash dans une expression de f-string)."""
    if not hasattr(tokenize, "FSTRING_START"):
        return True
    mauvais = 'import re\nx = f"a {re.sub(r\'^b\\s*\', \'\', \'c\')} d"\n'
    bon = 'import re\nm = re.sub(r"^b\\s*", "", "c")\nx = f"a {m} d"\n'
    return bool(fstrings_312(mauvais)) and not fstrings_312(bon)


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--studio", default=os.path.dirname(ICI), help="dossier du studio à relire (par défaut : celui de ce script)")
    a = a.parse_args(argv)
    if not essai_detecteur():
        print("ÉCHEC : le détecteur ne voit pas un antislash dans une f-string")
        return 1
    if not hasattr(tokenize, "FSTRING_START"):
        print("  (Python < 3.12 : seule la grammaire 3.10 est relue, pas l'intérieur des f-strings)")
    n, problemes = verifier(os.path.abspath(a.studio))
    for p in problemes:
        print("  ÉCHEC " + p)
    if problemes:
        print(f"COMPATIBILITÉ 3.10 : {len(problemes)} problème(s) sur {n} fichiers .py")
        return 1
    print(f"COMPATIBILITÉ 3.10 RÉUSSIE ({n} fichiers .py relus)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
