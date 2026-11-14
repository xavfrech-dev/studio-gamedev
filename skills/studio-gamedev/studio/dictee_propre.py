"""Nettoyage d'une dictée : segments qui se recouvrent et débuts de phrase répétés.

Cas réel (13/11) : « faut faut que faut que tu de de faire de faire une de faire une version… » : chaque morceau reprend le
précédent (résultats partiels empilés, ou segments de Whisper qui se chevauchent). On garde le texte final une seule fois.
"""
import re

DOUBLES_PERMIS = {"très", "si", "oui", "non", "bien", "plus", "encore", "vite", "tout", "beaucoup", "trop", "jamais",
                  "nous", "vous", "se", "s'", "en", "y", "l'", "la", "le",
                  "very", "so", "yes", "no", "really", "much", "too", "more", "bye", "ha", "ah", "oh", "that", "had", "is"}
FIN_PHRASE = re.compile(r"[.!?…:;]$")


def _permis(mot):
    """Doublon d'un seul mot qu'on garde : mots qui se répètent dans la langue (« nous nous », « très très »), nombres (« 11 11 »)."""
    m = _n(mot)
    return m in DOUBLES_PERMIS or m.isdigit()


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
            # un segment plus court qui reprend le début du précédent est gardé : il a peut-être vraiment été redit
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
            avant = out[-k:]
            if any(FIN_PHRASE.search(x) for x in avant):
                continue                                         # jamais par-dessus une fin de phrase (« Il est parti. Parti où ? »)
            if [_n(x) for x in avant] == [_n(x) for x in mots[i:i + k]] and not (k == 1 and _permis(mots[i])):
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


# Phrases que Whisper invente sur du silence ou du bruit (génériques de sous-titres de vidéos). Le segment n'est jeté que
# s'il EST une de ces phrases : « Corrige le sous-titrage du jeu » est une vraie demande (avant : jetée en entier, B1 du 13/11).
HALLUCINATIONS = [re.compile(x, re.I) for x in (
    r"^sous[- ]titr(?:age|es?)(?: (?:réalisés?|faits?|fr|st|par|société|de|pour)\b.*)?$",
    r"^(?:merci d'avoir regardé|merci de votre attention|abonnez[- ]vous|n'oubliez pas de vous abonner)\b.{0,40}$",
    r"amara\.org", r"radio[- ]canada\W*$", r"^(?:thanks for watching|please subscribe|subtitles by)\b.{0,40}$")]


def est_hallucination(segment):
    t = " ".join(str(segment or "").replace("’", "'").split()).strip(" .!?…")
    return bool(t) and any(h.search(t) for h in HALLUCINATIONS)


def _distance(a, b):
    d = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        p, d[0] = d[0], i
        for j, y in enumerate(b, 1):
            p, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, p + (x != y))
    return d[-1]


def _cle(x):
    import unicodedata
    x = unicodedata.normalize("NFD", x.lower())
    return "".join(c for c in x if c.isalnum())


def corriger_vocabulaire(texte, vocabulaire):
    """Mots du projet écrits au son par Whisper, remis à l'orthographe du vocabulaire : « Deepwood » → « DEEPWOODS »,
    « Elevants Labs » → « ElevenLabs », « grimbour » → « Grimbourg ». Seulement les noms propres (au moins une
    majuscule) ; à l'identique (casse près) sous 7 lettres, à 75 % près au-delà, même première lettre : « clause » ne
    devient jamais « Claude »."""
    termes = [t.strip() for t in (vocabulaire if isinstance(vocabulaire, (list, tuple)) else str(vocabulaire or "").split(","))]
    termes = [t.strip(" .") for t in termes if t and any(c.isupper() for c in t)]
    mots = str(texte or "").split(" ")
    if not mots or not termes:
        return texte
    cibles = [(t, _cle(t)) for t in termes if _cle(t)]
    out, i = [], 0
    while i < len(mots):
        fait = False
        for n in (3, 2, 1):                       # « Elevants Labs », « tour de garde » : plusieurs mots du texte pour un terme
            if i + n > len(mots):
                continue
            bloc = mots[i:i + n]
            m = re.match(r"^(\W*)(.*?)(\W*)$", " ".join(bloc))
            avant, coeur, apres = m.group(1), m.group(2), m.group(3)
            k = _cle(coeur)
            if not k or (n > 1 and any(len(_cle(x)) < 3 for x in bloc)):
                continue                          # « Megascans en » ne devient jamais « Megascans » : pas de petit mot avalé
            if n > 1 and any(_cle(x) == ct or _cle(x) + "s" == ct for x in bloc for _, ct in cibles):
                continue                          # un des mots est déjà un terme du projet : on le corrige seul
            for terme, ct in cibles:
                if n > 1 and len(terme.split()) == 1 and len(ct) < 7:
                    continue
                if k == ct:
                    bon = True
                elif len(ct) >= 7 and k[0] == ct[0] and abs(len(k) - len(ct)) <= 2:
                    bon = _distance(k, ct) <= max(1, int(len(ct) * 0.25 + 0.5))
                elif len(ct) >= 6 and k == ct[:-1] and ct.endswith("s"):    # pluriel perdu : « Deepwood »
                    bon = True
                else:
                    bon = False
                if bon:
                    out.append(avant + terme + apres)
                    i += n
                    fait = True
                    break
            if fait:
                break
        if not fait:
            out.append(mots[i])
            i += 1
    return " ".join(out)



if __name__ == "__main__":          # essai : le cas réel du 13/11
    cas = "faut faut que faut que tu de de faire de faire une de faire une version portable"
    attendu = "faut que tu de faire une version portable"
    assert propre(cas) == attendu, propre(cas)
    assert propre(["faut", "faut que", "faut que tu", "de", "de faire", "de faire une", "de faire une version portable"]) == attendu
    assert propre(["il faut que tu fasses", "que tu fasses une version", "une version portable"]) == "il faut que tu fasses une version portable"
    assert propre("c'est très très bien, non non") == "c'est très très bien, non non"
    assert propre("une phrase normale sans répétition") == "une phrase normale sans répétition"
    # F17 / F38 : répétitions voulues, fins de phrase et segment redit plus court
    assert propre("nous nous sommes vus") == "nous nous sommes vus"
    assert propre("vous vous trompez") == "vous vous trompez"
    assert propre("Il est parti. Parti où ?") == "Il est parti. Parti où ?"
    assert propre("rendez-vous le 11 11 à midi") == "rendez-vous le 11 11 à midi"
    assert propre(["je pense que c'est bien", "je pense"]) == "je pense que c'est bien je pense"
    # B1 du 13/11 : le mot « sous-titrage » dans une vraie phrase ne la fait plus disparaître
    assert not est_hallucination("Corrige le sous-titrage du jeu, les sous-titres coupent la fin des phrases.")
    assert not est_hallucination("Sous-titrage du tutoriel à revoir, la fin est coupée.")
    assert est_hallucination("Sous-titrage ST' 501") and est_hallucination("Sous-titres réalisés par la communauté d'Amara.org")
    assert est_hallucination("Merci d'avoir regardé !") and est_hallucination("Sous-titrage Société Radio-Canada")
    v = "DEEPWOODS, Godot, Unreal, Tripo, Nanite, ElevenLabs, Grimbourg, Claude, tour de garde, studio."
    assert corriger_vocabulaire("la faune de Deepwood.", v) == "la faune de DEEPWOODS."
    assert corriger_vocabulaire("avec Elevants Labs pour", v) == "avec ElevenLabs pour"
    assert corriger_vocabulaire("près du grimbour.", v) == "près du Grimbourg."
    assert corriger_vocabulaire("une clause du contrat, tripot et nanny", v) == "une clause du contrat, tripot et nanny"
    assert corriger_vocabulaire("les rochers Megascans en Nanite", "Megascans, Nanite") == "les rochers Megascans en Nanite"
    print("dictée propre : 19/19")
