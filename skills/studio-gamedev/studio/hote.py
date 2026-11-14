"""L'hôte du studio : un personnage d'ambiance que l'utilisateur crée lui-même (quête « Un hôte pour le studio »).

Bibliothèque standard seulement. Le serveur (serveur_studio.py, route /api/hote) et la page (hote.js) s'en servent ;
l'assistant aussi, en ligne de commande, quand l'utilisateur décrit son hôte par un prompt.

Fichiers (dans <projet>/.studio/) :
  hote.json              la fiche de l'hôte installé (absent = pas d'hôte)
  hote_proposition.json  la fiche proposée par l'assistant après un prompt (statut en_attente | prete | refusee)
  anciens/hote_<date>.json  un hôte supprimé ou remplacé (rien n'est effacé pour de bon)

Fiche : {"version": 1, "nom", "source": "choix" | "prompt", "prompt"?, "allure"?, "couleurs"?, "look": {morphologie, peau,
cheveux: {coupe, couleur}, tenue: {style, couleur1, couleur2}, accessoire}, "coin", "activites": [3 ou 4], "objets": [≤ 3,
plus ceux qu'une activité exige], "ton", "repliques"?: {coin, spontanees, fini, commit, decision, bloque, matin, soir,
activites: {<id>: [...]}} (langue du projet), "reglages": {"sons": true, "parole": "souvent|normal|rarement|jamais"}}.
Tout vient des pièces de hote_catalogue.json ; seuls le nom et les répliques sont libres, et ils passent par le filtre :
rien de vulgaire, de drogue ni de dénigrant. Aucune image n'est générée (sprites du skill, recolorés).

Ligne de commande :
  python -I -B hote.py --projet <projet> proposer <fiche.json> [--demande <id>]   fiche de l'assistant -> hote_proposition.json
  python -I -B hote.py --projet <projet> montrer                                   l'hôte installé (ou rien)
  python -I -B hote.py filtre "<texte>"                                             code 1 si un mot est refusé
  python -I -B hote.py verifier                                                     contrôle du catalogue (code 1 si erreur)
"""
import json
import os
import re
import shutil
import sys
import time
import unicodedata

sys.dont_write_bytecode = True
ICI = os.path.dirname(os.path.abspath(__file__))
if ICI not in sys.path:
    sys.path.insert(0, ICI)
import jsonio                                        # C4 : lecture (BOM) et écriture atomique communes
CATALOGUE = os.path.join(ICI, "hote_catalogue.json")
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

PERMIS = {
    "morphologie": {"mince", "moyenne", "costaude", "petite", "grande"},
    "coupe": {"courts", "longs", "boucles", "en_bataille", "queue", "rase", "aucune"},
    "style": {"sweat", "chemise", "bleu_de_travail", "heros", "tablier", "costume", "armure", "robe"},
}
CLES_REPLIQUES = ("coin", "spontanees", "fini", "commit", "decision", "bloque", "matin", "soir")
JETONS_PERMIS = {"nom", "tache", "titre"}
COULEUR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
ACTIVITES_DEFAUT = ("lit", "tournee", "fenetre", "carnet")
PAROLES = ("souvent", "normal", "rarement", "jamais")


class Refus(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


def lire_json(chemin, defaut=None):
    return jsonio.lire(chemin, defaut)


def ecrire_json(chemin, donnees):
    jsonio.ecrire(chemin, donnees, newline="\n")


def maintenant():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


_CAT = {"t": 0, "d": None}


def catalogue_valide(c):
    """Un catalogue sans filtre laisserait tout passer : il faut au moins un mot refusé dans chaque catégorie et des coins."""
    f = c.get("filtre") if isinstance(c, dict) else None
    return (isinstance(f, dict) and all(isinstance(f.get(k), list) and f.get(k) for k in ("vulgaire", "drogue", "denigrant"))
            and bool(ids(c, "coins")))


def catalogue():
    """Catalogue de l'hôte, gardé en mémoire tant que le fichier ne change pas. Absent, illisible ou sans filtre : Refus(503),
    jamais mis en mémoire (le filtre ne s'ouvre jamais faute de catalogue ; un fichier réparé est relu au prochain appel)."""
    try:
        mt = os.path.getmtime(CATALOGUE)
    except OSError:
        mt = 0
    if _CAT["d"] is None or mt != _CAT["t"]:
        d = lire_json(CATALOGUE, None) if mt else None
        if not catalogue_valide(d):
            _CAT["d"], _CAT["t"] = None, 0
            raise Refus(503, "catalogue de l'hôte absent ou illisible (hote_catalogue.json) : rien n'est accepté")
        _CAT["d"], _CAT["t"] = d, mt
    return _CAT["d"]


def nom_archive(dossier, prefixe):
    """Nom libre dans anciens/ : <prefixe>_<date>.json, puis _2, _3… (deux rangements dans la même seconde ne s'écrasent pas)."""
    os.makedirs(dossier, exist_ok=True)
    pile = time.strftime("%Y%m%d-%H%M%S")
    dest, n = os.path.join(dossier, f"{prefixe}_{pile}.json"), 1
    while os.path.exists(dest):
        n += 1
        dest = os.path.join(dossier, f"{prefixe}_{pile}_{n}.json")
    return dest


def ids(cat, cle):
    return [x["id"] for x in cat.get(cle, []) if isinstance(x, dict) and x.get("id")]


# ------------------------------------------------------------------ filtre de contenu
# Même algorithme dans hote.js (filtrer) : toute modification se fait des deux côtés (essai_hote.py compare les deux).
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "€": "e", "!": "i"})
# lettres grecques et cyrilliques qui ressemblent à des lettres latines (« fυck », « сon ») ; ß, œ, æ en deux lettres
_SOSIES = str.maketrans({"α": "a", "β": "b", "ε": "e", "η": "n", "ι": "i", "κ": "k", "ν": "v", "ο": "o", "ρ": "p", "τ": "t", "υ": "u",
                         "χ": "x", "ς": "c", "σ": "o", "μ": "u", "γ": "y", "ω": "w", "а": "a", "в": "b", "е": "e", "ё": "e", "к": "k",
                         "м": "m", "н": "h", "о": "o", "р": "p", "с": "c", "т": "t", "у": "y", "х": "x", "і": "i", "ї": "i", "ј": "j",
                         "ѕ": "s", "ԁ": "d", "ɡ": "g", "ı": "i", "ł": "l", "ø": "o", "đ": "d", "ß": "ss", "œ": "oe", "æ": "ae"})


def sans_accents(s):
    """Texte ramené à des lettres simples : NFKD (lettres larges, mathématiques…), sans accents ni caractères invisibles."""
    return "".join(c for c in unicodedata.normalize("NFKD", str(s)) if unicodedata.category(c) not in ("Mn", "Me", "Cf"))


def simplifier(texte):
    s = sans_accents(texte).lower().translate(_SOSIES)
    s = sans_accents(s).translate(_LEET)
    return re.sub(r"([a-z])[*#._-]+(?=[a-z])", r"\1", s)    # lettres masquées ou séparées : « f*ck », « m.e.r.d.e », « tue-les »


def jetons(texte):
    """Mots du texte, sans accents ni majuscules, chiffres lus comme des lettres (m3rde -> merde)."""
    return re.findall(r"[a-z]+", simplifier(texte))


def recolles(brut):
    """Lettres isolées à la suite recollées : « p u t a i n » -> putain."""
    out, i = [], 0
    while i < len(brut):
        j = i
        while j < len(brut) and len(brut[j]) == 1:
            j += 1
        if j - i >= 3:
            out.append("".join(brut[i:j]))
        i = max(j, i + 1)
    return out


def variantes(m):
    return {m, re.sub(r"(.)\1{2,}", r"\1", m), re.sub(r"(.)\1+", r"\1", m)}   # « merdeee », « connnard »


def _motif(mot):
    return " ".join(jetons(mot.rstrip("*"))) + ("*" if mot.strip().endswith("*") else "")


def _exempte(m, exceptions):
    return any((m.startswith(e[:-1]) if e.endswith("*") else m == e) for e in exceptions)


def filtrer(texte, cat=None):
    """Liste des (catégorie, mot) refusés trouvés dans le texte ; vide si le texte est propre.
    « mot » : mot entier ; « mot* » : début de mot ; « ~mot » : n'importe où dans le mot ; « deux mots » : expression.
    Les exceptions (mots) et les expressions permises passent toujours (« salopette », « nulle part », « en retard »)."""
    cat = cat or catalogue()
    if not catalogue_valide(cat):
        raise Refus(503, "catalogue de l'hôte sans filtre : rien n'est accepté")
    f = cat.get("filtre") or {}
    brut = jetons(texte)
    neutre = [False] * len(brut)
    for e in f.get("expressions_permises") or []:
        ej = jetons(e)
        n = len(ej)
        for i in range(len(brut) - n + 1):
            if n and brut[i:i + n] == ej:
                for k in range(i, i + n):
                    neutre[k] = True
    exceptions = [_motif(e) for e in f.get("exceptions") or []]
    seq = ["_" if neutre[i] or _exempte(m, exceptions) else m for i, m in enumerate(brut)]
    mots = [m for m in seq if m != "_"] + [m for m in recolles(brut) if not _exempte(m, exceptions)]
    tous = set()
    for m in mots:
        tous |= variantes(m)
    phrase = " " + " ".join(seq) + " "
    trouves = []
    for categorie in ("vulgaire", "drogue", "denigrant"):
        for mot in f.get(categorie) or []:
            dedans = mot.strip().startswith("~")
            m = _motif(mot.strip().lstrip("~"))
            if not m or m == "*":
                continue
            if dedans:
                ok = any(m.rstrip("*") in x for x in tous)
            elif " " in m:
                ok = (" " + m.rstrip("*") + " ") in phrase or (m.endswith("*") and (" " + m[:-1]) in phrase)
            elif m.endswith("*"):
                ok = any(x.startswith(m[:-1]) for x in tous)
            else:
                ok = m in tous
            if ok and (categorie, mot) not in trouves:
                trouves.append((categorie, mot))
    return trouves


def message_filtre(trouves, en=False):
    cats = sorted({c for c, _ in trouves})
    noms = {"vulgaire": ("vulgarité", "vulgarity"), "drogue": ("drogue ou alcool", "drugs or alcohol"), "denigrant": ("propos dénigrants", "demeaning words")}
    lib = ", ".join(noms[c][1 if en else 0] for c in cats)
    return (f"Not allowed for the studio host ({lib}). Keep it kind and family-friendly." if en
            else f"Refusé pour l'hôte du studio ({lib}). Garde-le gentil et tout public.")


# ------------------------------------------------------------------ fiche
def texte_propre(v, maxi):
    s = " ".join(str(v or "").split())
    s = "".join(c for c in s if unicodedata.category(c)[0] != "C")
    return s[:maxi].strip()


def couleur(v, defaut):
    return v if isinstance(v, str) and COULEUR_RE.match(v) else defaut


def look_propre(l, cat):
    l = l if isinstance(l, dict) else {}
    ch = l.get("cheveux") if isinstance(l.get("cheveux"), dict) else {}
    te = l.get("tenue") if isinstance(l.get("tenue"), dict) else {}
    acc = l.get("accessoire") if l.get("accessoire") in (cat.get("accessoires") or []) else "aucun"
    return {
        "morphologie": l.get("morphologie") if l.get("morphologie") in PERMIS["morphologie"] else "moyenne",
        "peau": couleur(l.get("peau"), "#e0ac69"),
        "cheveux": {"coupe": ch.get("coupe") if ch.get("coupe") in PERMIS["coupe"] else "courts", "couleur": couleur(ch.get("couleur"), "#2b1d14")},
        "tenue": {"style": te.get("style") if te.get("style") in PERMIS["style"] else "sweat",
                  "couleur1": couleur(te.get("couleur1"), "#3f7a52"), "couleur2": couleur(te.get("couleur2"), "#e9c47f")},
        "accessoire": acc,
    }


def repliques_propres(r, cat, avert):
    lim = cat.get("limites") or {}
    maxi, n_max = int(lim.get("replique_max", 140)), int(lim.get("repliques_max_par_cle", 8))
    out = {}

    def liste(v, ou):
        res = []
        for x in (v if isinstance(v, list) else [])[:n_max * 2]:
            s = texte_propre(x, maxi)
            if not s:
                continue
            if set(re.findall(r"\{(\w+)\}", s)) - JETONS_PERMIS:
                avert.append(f"réplique écartée ({ou}) : jeton inconnu")
                continue
            if filtrer(s, cat):
                avert.append(f"réplique écartée ({ou}) : refusée par le filtre")
                continue
            if s not in res:
                res.append(s)
            if len(res) >= n_max:
                break
        return res
    if not isinstance(r, dict):
        return out
    for k in CLES_REPLIQUES:
        l = liste(r.get(k), k)
        if l:
            out[k] = l
    acts = r.get("activites")
    if isinstance(acts, dict):
        a = {}
        for k in ids(cat, "activites"):
            l = liste(acts.get(k), "activites." + k)
            if l:
                a[k] = l
        if a:
            out["activites"] = a
    return out


def normaliser(fiche, cat=None, completer=False):
    """Fiche propre (identifiants connus, couleurs valides, répliques filtrées) et avertissements. Refus(400|422).
    completer : fiche venue d'un prompt (assistant) : ce qui manque est complété au lieu d'être refusé."""
    cat = cat or catalogue()
    if not isinstance(fiche, dict):
        raise Refus(400, "fiche : un objet JSON")
    lim = cat.get("limites") or {}
    avert = []
    nom = texte_propre(fiche.get("nom"), int(lim.get("nom_max", 30)))
    if not nom:
        raise Refus(400, "nom de l'hôte manquant")
    if filtrer(nom, cat):
        raise Refus(422, message_filtre(filtrer(nom, cat)))
    coins, acts_ok, objs_ok, tons = ids(cat, "coins"), ids(cat, "activites"), ids(cat, "objets"), ids(cat, "tons")
    coin = fiche.get("coin")
    if coin not in coins:
        if not completer:
            raise Refus(400, "coin inconnu")
        coin = coins[0]
        avert.append("coin complété")
    acts = []
    for a in fiche.get("activites") if isinstance(fiche.get("activites"), list) else []:
        if a in acts_ok and a not in acts:
            acts.append(a)
    amin, amax = int(lim.get("activites_min", 3)), int(lim.get("activites_max", 4))
    if len(acts) < amin:
        if not completer:
            raise Refus(400, f"choisis de {amin} à {amax} activités")
        for a in ACTIVITES_DEFAUT:
            if len(acts) >= amin:
                break
            if a not in acts:
                acts.append(a)
        avert.append("activités complétées")
    acts = acts[:amax]
    objs = []
    for o in fiche.get("objets") if isinstance(fiche.get("objets"), list) else []:
        if o in objs_ok and o not in objs:
            objs.append(o)
    objs = objs[:int(lim.get("objets_max", 3))]
    for a in acts:                                   # une activité qui a besoin d'un objet l'apporte (arroser : une plante)
        req = next((x.get("objet_requis") for x in cat.get("activites", []) if x.get("id") == a), None)
        if req and req not in objs:
            objs.append(req)
    ton = fiche.get("ton")
    if ton not in tons:
        if not completer:
            raise Refus(400, "ton inconnu")
        ton = tons[0]
        avert.append("ton complété")
    allure = fiche.get("allure") if fiche.get("allure") in ids(cat, "allures") else None
    coul = fiche.get("couleurs") if fiche.get("couleurs") in ids(cat, "couleurs") else None
    look = fiche.get("look")
    if not isinstance(look, dict):                   # composé depuis l'allure et les couleurs choisies
        base = next((x["look"] for x in cat.get("allures", []) if x["id"] == allure), {}) if allure else {}
        look = json.loads(json.dumps(base))
        c = next((x for x in cat.get("couleurs", []) if x["id"] == coul), None)
        if c:
            look.setdefault("tenue", {}).update(couleur1=c["couleur1"], couleur2=c["couleur2"])
        if fiche.get("accessoire"):
            look["accessoire"] = fiche.get("accessoire")
    look = look_propre(look, cat)
    reg = fiche.get("reglages") if isinstance(fiche.get("reglages"), dict) else {}
    propre = {"version": 1, "nom": nom, "source": "prompt" if fiche.get("source") == "prompt" else "choix",
              "look": look, "coin": coin, "activites": acts, "objets": objs, "ton": ton,
              "reglages": {"sons": reg.get("sons") is not False, "parole": reg.get("parole") if reg.get("parole") in PAROLES else "normal"}}
    if allure:
        propre["allure"] = allure
    if coul:
        propre["couleurs"] = coul
    if propre["source"] == "prompt":
        p = texte_propre(fiche.get("prompt"), int(lim.get("prompt_max", 600)))
        if p and not filtrer(p, cat):
            propre["prompt"] = p
    rep = repliques_propres(fiche.get("repliques"), cat, avert)
    if rep:
        propre["repliques"] = rep
    for k in ("cree_le", "maj"):
        if isinstance(fiche.get(k), str) and re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d$", fiche[k]):
            propre[k] = fiche[k]
    return propre, avert


# ------------------------------------------------------------------ fichiers du projet
def chemins(projet):
    st = os.path.join(projet, ".studio")
    return {"hote": os.path.join(st, "hote.json"), "prop": os.path.join(st, "hote_proposition.json"), "anciens": os.path.join(st, "anciens")}


def ranger_ancien(projet, quoi="hote"):
    """Met l'hôte actuel de côté (anciens/hote_<date>.json) : rien n'est effacé pour de bon."""
    c = chemins(projet)
    if not os.path.isfile(c["hote"]):
        return None
    dest = nom_archive(c["anciens"], quoi)
    os.replace(c["hote"], dest)
    return dest


def enregistrer(projet, fiche, cat=None):
    propre, avert = normaliser(fiche, cat)
    c = chemins(projet)
    ancien = lire_json(c["hote"], None)
    if isinstance(ancien, dict) and ancien.get("cree_le"):
        propre["cree_le"] = ancien["cree_le"]
    propre.setdefault("cree_le", maintenant())
    propre["maj"] = maintenant()
    # L'ancien hôte (même illisible) est COPIÉ dans anciens/ avant d'écrire le nouveau ; hote.json n'est remplacé qu'une fois
    # le nouveau écrit en entier (ecrire_json : temporaire puis os.replace). Si l'écriture échoue, l'ancien reste en place
    # et la copie en trop est retirée : jamais de studio sans hôte, jamais d'hôte perdu.
    copie = None
    if os.path.isfile(c["hote"]):
        copie = nom_archive(c["anciens"], "hote_remplace")
        shutil.copyfile(c["hote"], copie)
    try:
        ecrire_json(c["hote"], propre)
    except BaseException:
        if copie:
            try:
                os.remove(copie)
            except OSError:
                pass
        try:
            os.remove(c["hote"] + ".tmp")
        except OSError:
            pass
        raise
    p = lire_json(c["prop"], None)
    if isinstance(p, dict) and p.get("statut") == "prete":
        p["statut"] = "installee"
        ecrire_json(c["prop"], p)
    return propre, avert


def regler(projet, sons=None, parole=None):
    c = chemins(projet)
    h = lire_json(c["hote"], None)
    if not isinstance(h, dict):
        raise Refus(404, "pas d'hôte dans ce studio")
    r = h.get("reglages") if isinstance(h.get("reglages"), dict) else {}
    if sons is not None:
        if not isinstance(sons, bool):
            raise Refus(400, "sons : true ou false")
        r["sons"] = sons
    if parole is not None:
        if parole not in PAROLES:
            raise Refus(400, "parole : " + ", ".join(PAROLES))
        r["parole"] = parole
    h["reglages"] = r
    h["maj"] = maintenant()
    ecrire_json(c["hote"], h)
    return h


def supprimer(projet):
    c = chemins(projet)
    dest = ranger_ancien(projet, "hote_supprime")
    if not dest:
        raise Refus(404, "pas d'hôte dans ce studio")
    if os.path.isfile(c["prop"]):
        os.replace(c["prop"], nom_archive(c["anciens"], "hote_proposition"))
    return dest


def consigne(projet, skill_studio, ident, en):
    """Consigne de l'assistant pour une demande « hote » (prompt de l'utilisateur)."""
    cmd = f'python -I -B "{os.path.join(skill_studio, "hote.py")}" --projet "{projet}" proposer "{os.path.join(projet, ".studio", "hote_brouillon.json")}" --demande {ident}'
    if en:
        return ("The user describes the studio host they want (text above). Build ONE host sheet (JSON) from that description, "
                f"using only the pieces of {os.path.join(skill_studio, 'hote_catalogue.json')}: look (morphologie, peau, cheveux.coupe/couleur, "
                "tenue.style/couleur1/couleur2, accessoire from the allowed lists, colours as #rrggbb), coin, 3 or 4 activites, up to 3 objets, ton, "
                "a short kind name, and repliques in the project language (3 per key: coin, spontanees, fini, commit, decision, bloque, matin, soir, "
                "and activites.<id> for each chosen activity; tokens allowed: {nom}, {tache}, {titre}). Nothing vulgar, no drugs or alcohol, "
                "nothing demeaning. No image generation, no paid service. Write it to .studio/hote_brouillon.json, then run: " + cmd +
                " (it filters and writes .studio/hote_proposition.json; the page shows the preview; if it answers that the request was cancelled, stop there). Then mark this request done.")
    return ("L'utilisateur décrit l'hôte du studio qu'il veut (texte ci-dessus). Compose UNE fiche d'hôte (JSON) à partir de cette description, "
            f"uniquement avec les pièces de {os.path.join(skill_studio, 'hote_catalogue.json')} : look (morphologie, peau, cheveux.coupe/couleur, "
            "tenue.style/couleur1/couleur2, accessoire pris dans les listes permises, couleurs en #rrggbb), coin, 3 ou 4 activites, 3 objets au plus, ton, "
            "un nom court et gentil, et des repliques dans la langue du projet (3 par clé : coin, spontanees, fini, commit, decision, bloque, matin, soir, "
            "et activites.<id> pour chaque activité choisie ; jetons permis : {nom}, {tache}, {titre}). Rien de vulgaire, ni drogue ni alcool, "
            "rien de dénigrant. Aucune génération d'image, aucun service payant. Écris-la dans .studio/hote_brouillon.json, puis lance : " + cmd +
            " (il filtre et écrit .studio/hote_proposition.json ; la page montre l'aperçu ; s'il répond que la demande est annulée, arrête-toi là). Puis marque cette demande comme traitée.")


def proposer(projet, chemin_fiche, demande=None, cat=None):
    """Fiche écrite par l'assistant après un prompt -> hote_proposition.json (statut prete, ou refusee avec la raison)."""
    cat = cat or catalogue()
    c = chemins(projet)
    fiche = lire_json(chemin_fiche, None)
    ancien = lire_json(c["prop"], {}) if os.path.isfile(c["prop"]) else {}
    if demande:
        # l'utilisateur a annulé (Annuler, Recommencer) ou envoyé une autre description depuis : pas d'aperçu pour cette demande
        d = lire_json(os.path.join(projet, ".studio", "demandes_vocales", str(demande) + ".json"), {}) if re.match(r"^[A-Za-z0-9_.:+-]{1,120}$", str(demande)) else {}
        if isinstance(d, dict) and d.get("statut") == "annulee":
            return {"ok": False, "code": 409, "erreur": "demande annulée par l'utilisateur : rien à proposer", "annulee": True}
        if not isinstance(ancien, dict) or ancien.get("demande") != demande or ancien.get("statut") != "en_attente":
            return {"ok": False, "code": 409, "erreur": "plus d'attente pour cette demande (annulée ou remplacée) : rien à proposer", "annulee": True}
    base = {"demande": demande or (ancien or {}).get("demande"), "prompt": (ancien or {}).get("prompt"), "le": maintenant()}
    try:
        if isinstance(fiche, dict):
            fiche = dict(fiche, source="prompt")
            if base["prompt"] and not fiche.get("prompt"):
                fiche["prompt"] = base["prompt"]
        propre, avert = normaliser(fiche, cat, completer=True)
    except Refus as e:
        ecrire_json(c["prop"], dict(base, statut="refusee", raison=e.message))
        return {"ok": False, "code": e.code, "erreur": e.message}
    ecrire_json(c["prop"], dict(base, statut="prete", fiche=propre, avertissements=avert))
    return {"ok": True, "fiche": propre, "avertissements": avert}


# ------------------------------------------------------------------ contrôle du catalogue
def verifier(cat=None):
    cat = cat or catalogue()
    err = []

    def bilingue(o, ou):
        if isinstance(o, dict):
            if set(o) >= {"fr", "en"} and len(o) == 2:
                if not (o["fr"] and o["en"]):
                    err.append("texte vide " + ou)
                if isinstance(o["fr"], (list, dict)) and type(o["fr"]) is not type(o["en"]):
                    err.append("fr/en de formes différentes " + ou)
                if isinstance(o["fr"], dict) and set(o["fr"]) != set(o["en"]):
                    err.append("fr/en clés différentes " + ou)
                return
            for k, v in o.items():
                bilingue(v, ou + "." + k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                bilingue(v, f"{ou}[{i}]")
    for cle in ("allures", "couleurs", "coins", "objets", "activites", "tons"):
        l = ids(cat, cle)
        if len(l) != len(set(l)) or not l:
            err.append(cle + " : identifiants en double ou vides")
        if any(not re.match(r"^[a-z][a-z0-9_]{1,30}$", x) for x in l):
            err.append(cle + " : identifiant non ASCII")
        bilingue(cat.get(cle), cle)
    for a in cat.get("allures", []):
        if look_propre(a.get("look"), cat)["morphologie"] != a["look"].get("morphologie"):
            err.append("allure " + a["id"] + " : morphologie")
    for c in cat.get("couleurs", []):
        if not (COULEUR_RE.match(c.get("couleur1", "")) and COULEUR_RE.match(c.get("couleur2", ""))):
            err.append("couleurs " + c["id"])
    for c in cat.get("coins", []):
        x0, y0, x1, y1 = c["r"]
        pts = [c["siege"], c["table"]] + c["places"]
        if not (isinstance(c.get("debout"), list) and 0 < c["debout"][0] < 16 and 0 < c["debout"][1] < 12):
            err.append("coin " + c["id"] + " : point « debout » (près du guéridon) manquant")
        if not (0 < x0 < x1 < 16 and 0 < y0 < y1 < 12) or any(not (x0 <= p[0] <= x1 and y0 <= p[1] <= y1) for p in pts):
            err.append("coin " + c["id"] + " : points hors du coin")
        if len(c["places"]) < 3:
            err.append("coin " + c["id"] + " : 3 places d'objets")
    for a in cat.get("activites", []):
        if a.get("objet_requis") and a["objet_requis"] not in ids(cat, "objets"):
            err.append("activité " + a["id"] + " : objet requis inconnu")
        for lang in ("fr", "en"):
            for s in a["repliques"][lang]:
                if filtrer(s, cat):
                    err.append(f"activité {a['id']} : réplique refusée par le filtre ({s})")
    for t in cat.get("tons", []):
        for lang in ("fr", "en"):
            r = t["repliques"][lang]
            if set(r) != set(CLES_REPLIQUES):
                err.append(f"ton {t['id']} ({lang}) : clés {sorted(set(CLES_REPLIQUES) ^ set(r))}")
            for k, l in r.items():
                for s in l:
                    if filtrer(s, cat):
                        err.append(f"ton {t['id']} : réplique refusée par le filtre ({s})")
                    if set(re.findall(r"\{(\w+)\}", s)) - JETONS_PERMIS:
                        err.append(f"ton {t['id']} : jeton inconnu ({s})")
    for lang in ("fr", "en"):
        for s in (cat.get("reponses_collegues") or {}).get(lang, []):
            if filtrer(s, cat):
                err.append("réponse refusée par le filtre : " + s)
    for a in cat.get("accessoires", []):
        if a not in {"aucun", "casque", "casque_audio", "casquette", "beret", "chapeau", "lunettes", "barbe", "couronne", "bandeau", "capuche", "cornes"}:
            err.append("accessoire inconnu " + a)
    return err


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    projet = None
    if "--projet" in a:
        i = a.index("--projet")
        projet = os.path.abspath(a[i + 1])
        del a[i:i + 2]
    demande = None
    if "--demande" in a:
        i = a.index("--demande")
        demande = a[i + 1]
        del a[i:i + 2]
    if not a:
        print(__doc__)
        return 2
    cmd = a[0]
    try:
        return _commande(cmd, a, projet, demande)
    except Refus as e:
        print(json.dumps({"ok": False, "code": e.code, "erreur": e.message}, ensure_ascii=False))
        return 1


def _commande(cmd, a, projet, demande):
    if cmd == "filtre":
        t = " ".join(a[1:])
        tr = filtrer(t)
        print(json.dumps({"ok": not tr, "refuses": [{"categorie": c, "mot": m} for c, m in tr]}, ensure_ascii=False))
        return 1 if tr else 0
    if cmd == "verifier":
        err = verifier()
        print(json.dumps({"erreurs": err}, ensure_ascii=False, indent=1))
        return 1 if err else 0
    if not projet:
        print("--projet requis")
        return 2
    if cmd == "proposer" and len(a) > 1:
        r = proposer(projet, os.path.abspath(a[1]), demande)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0 if r["ok"] else 3
    if cmd == "montrer":
        print(json.dumps(lire_json(chemins(projet)["hote"], None), ensure_ascii=False, indent=1))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
