"""Nettoyage d'une dictée : segments qui se recouvrent et débuts de phrase répétés.

Cas réel (13/11) : « faut faut que faut que tu de de faire de faire une de faire une version… » : chaque morceau reprend le
précédent (résultats partiels empilés, ou segments de Whisper qui se chevauchent). On garde le texte final une seule fois.
"""
import re

DOUBLES_PERMIS = {"très", "si", "oui", "non", "bien", "plus", "encore", "vite", "tout", "beaucoup", "trop", "jamais",
                  "very", "so", "yes", "no", "really", "much", "too", "more", "bye", "ha", "ah", "oh"}


def _n(mot):
    return re.sub(r"[^\w']", "", mot.lower())


def fusion_segments(segments):
    """Segments successifs : un segment qui reprend le précédent le remplace ; un segment déjà contenu au début du
    précédent est ignoré ; un recouvrement fin / début n'est gardé qu'une fois."""
    out = []
    for s in segments:
        s = " ".join(str(s or "").split())
        if not s:
            continue
        if out:
            a, b = [_n(x) for x in out[-1].split()], [_n(x) for x in s.split()]
            if b[:len(a)] == a:
                out[-1] = s
                continue
            if a[:len(b)] == b:
                continue
            k = next((k for k in range(min(len(a), len(b)), 1, -1) if a[-k:] == b[:k]), 0)   # recouvrement d'au moins 2 mots
            if k:
                out[-1] = out[-1] + " " + " ".join(s.split()[k:])
                continue
        out.append(s)
    return " ".join(out).strip()


def dedoublonner(texte):
    """Mots qui reprennent ce qui vient d'être dit (« faut faut que faut que tu ») : supprimés. Les doublons voulus
    (« très très », « non non ») sont gardés."""
    mots = str(texte or "").split()
    out = []
    i = 0
    while i < len(mots):
        saut = 0
        for k in range(min(8, len(out), len(mots) - i), 0, -1):
            if [_n(x) for x in out[-k:]] == [_n(x) for x in mots[i:i + k]] and not (k == 1 and _n(mots[i]) in DOUBLES_PERMIS):
                saut = k
                break
        if saut:
            i += saut
            continue
        out.append(mots[i])
        i += 1
    return " ".join(out)


def propre(segments_ou_texte):
    if isinstance(segments_ou_texte, (list, tuple)):
        return dedoublonner(fusion_segments(segments_ou_texte))
    return dedoublonner(segments_ou_texte)


if __name__ == "__main__":          # essai : le cas réel du 13/11
    cas = "faut faut que faut que tu de de faire de faire une de faire une version portable"
    attendu = "faut que tu de faire une version portable"
    assert propre(cas) == attendu, propre(cas)
    assert propre(["faut", "faut que", "faut que tu", "de", "de faire", "de faire une", "de faire une version portable"]) == attendu
    assert propre(["il faut que tu fasses", "que tu fasses une version", "une version portable"]) == "il faut que tu fasses une version portable"
    assert propre("c'est très très bien, non non") == "c'est très très bien, non non"
    assert propre("une phrase normale sans répétition") == "une phrase normale sans répétition"
    print("dictée propre : 5/5")
