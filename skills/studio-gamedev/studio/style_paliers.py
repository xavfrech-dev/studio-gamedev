"""studio/style_paliers.py : l'habillage du studio par la DA du jeu (paquet S4).

Deux axes séparés : le bâtiment (paliers.js, suit le niveau) et l'HABILLAGE (ce fichier, suit la DA réelle du jeu).
Cinq paliers d'habillage :
  1 Maquette grise  (départ : gris neutres, police système, coins à 4 px, pas d'ombres douces)
  2 Palette         (les jetons de l'UI prennent la palette du jeu, contraste AA garanti)
  3 Polices         (« Jeu Texte » et « Jeu Interface » chargées depuis .studio/da/)
  4 Logo            (logo dans l'en-tête, icône d'onglet, enseigne au mur)
  5 Décor           (motif de fond léger, cadre des panneaux, affiches, sons d'UI si permis)

Source unique : <projet>/.studio/da.json, écrit par Claude APRÈS validation de l'utilisateur. Sans
`valide_par_utilisateur`, da.json est un brouillon : rien n'est appliqué. Chemins relatifs au projet seulement,
sans `..` ni lien ; les fichiers utiles sont COPIÉS (bornés) dans .studio/da/ : le serveur ne sert que ce dossier.
Un SVG n'est jamais inséré dans la page : il est marqué `insertion: "img"`.

Modes (reglages.json → habillage_mode) : `progressif` (défaut), `atelier` (style de référence, toujours), `jeu`
(la DA dès que da.json est validé, sans attendre les quêtes).

Python standard, aucune dépendance. Lecture seule hors de <projet>/.studio/.
Ligne de commande : python style_paliers.py <projet> [--mode progressif|atelier|jeu] [--ecrire]
"""
import hashlib
import json
import os
import re
import shutil
import sys
import time

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

# Style de référence « Atelier » (jumeau du studio de référence : mêmes valeurs que :root de studio.html)
ATELIER = {
    "--nuit": "#1a1713", "--nuit2": "#241f19", "--bord": "rgba(233,210,160,.16)", "--texte": "#efe6d2",
    "--papier": "#f4ecd9", "--encre": "#2b241c", "--encre2": "#5c4f3f", "--encre3": "#8a7b66",
    "--ocre": "#b98532", "--ocre2": "#e2b866", "--sapin": "#3f7a52", "--rouge": "#a8432e", "--bleu": "#4d6f9c",
    "--alerte": "#c9953e", "--rayon": "10px", "--ombre": "0 10px 30px rgba(0,0,0,.35)", "--degrade": "1",
    "--motif": "none", "--motif-opacite": "0",
    "--sans": '"Jeu Interface","Segoe UI",system-ui,-apple-system,Arial,sans-serif',
    "--serif": '"Jeu Texte",Georgia,"Times New Roman",serif',
}
ETATS_REFERENCE = {"succes": "#3f7a52", "alerte": "#c9953e", "danger": "#a8432e"}

# Palier 1 : maquette grise (conception § 8.2)
GRIS = {
    "--nuit": "#1b1c1e", "--nuit2": "#232528", "--bord": "rgba(214,216,219,.14)", "--texte": "#d6d8db",
    "--papier": "#2a2c2f", "--encre": "#d6d8db", "--encre2": "#aeb2b7", "--encre3": "#8a8f96",
    "--ocre": "#8a8f96", "--ocre2": "#a9aeb4", "--sapin": "#6f8f78", "--rouge": "#a0675c", "--bleu": "#7d8896",
    "--alerte": "#a8956a", "--rayon": "4px", "--ombre": "none", "--degrade": "0",
    "--motif": "none", "--motif-opacite": "0",
    "--sans": 'system-ui,-apple-system,"Segoe UI",Arial,sans-serif',
    "--serif": 'system-ui,-apple-system,"Segoe UI",Arial,sans-serif',
}
NOMS = {1: ("Maquette grise", "Grey mock-up"), 2: ("Palette", "Palette"), 3: ("Polices", "Fonts"),
        4: ("Logo", "Logo"), 5: ("Décor", "Decor")}
CHAMPS_PALIER = {1: [], 2: ["palette"], 3: ["palette", "polices.titre", "polices.interface"],
                 4: ["palette", "polices.titre", "polices.interface", "logo"],
                 5: ["palette", "polices.titre", "polices.interface", "logo", "decor"]}
# quête qui donne chaque palier (catalogue : recompense.habillage) ; relu dans le catalogue quand il est fourni
QUETE_PALIER = {2: "Q-ID-02", 3: "Q-ID-03", 4: "Q-ID-04", 5: "Q-ID-06"}

LIMITES = {"police": (2 * 1024 * 1024, {".ttf", ".otf", ".woff", ".woff2"}),
           "image": (2 * 1024 * 1024, {".png", ".webp", ".jpg", ".jpeg", ".svg"}),
           "son": (1 * 1024 * 1024, {".ogg", ".wav", ".mp3"})}
COPIES_MAX = 16
ROLES = ("fond", "surface", "texte", "accent", "accent2", "succes", "alerte", "danger")
FAITES = ("remplie", "deja_faite")


# ------------------------------------------------------------------ couleurs
def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def hexa(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in c)


def mix(a, b, t):
    ra, rb = rgb(a), rgb(b)
    return hexa(tuple(ra[i] + (rb[i] - ra[i]) * t for i in range(3)))


def luminance(h):
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb(h)
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contraste(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def lab(h):
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in rgb(h))
    x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
    y = (r * 0.2126 + g * 0.7152 + b * 0.0722)
    z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(a, b):
    la, lb = lab(a), lab(b)
    return sum((la[i] - lb[i]) ** 2 for i in range(3)) ** 0.5


def rgba(h, a):
    r, g, b = rgb(h)
    return f"rgba({r},{g},{b},{a})"


def lisible(texte, fonds, cible=4.5):
    """Éclaircit ou fonce `texte` jusqu'à un contraste ≥ cible sur chacun des `fonds`. (couleur, ajusté ?)"""
    if all(contraste(texte, f) >= cible for f in fonds):
        return texte, False
    sombre = sum(luminance(f) for f in fonds) / len(fonds) < 0.4
    but = "#ffffff" if sombre else "#000000"
    for i in range(1, 21):
        c = mix(texte, but, i / 20)
        if all(contraste(c, f) >= cible for f in fonds):
            return c, True
    return but, True


# ------------------------------------------------------------------ chemins et da.json
def chemin_sur(projet, rel):
    """Chemin relatif au projet, sans `..`, sans lien, fichier ordinaire existant. Sinon None."""
    if not isinstance(rel, str) or not rel.strip() or len(rel) > 400:
        return None
    r = rel.replace("\\", "/").strip()
    if r.startswith("/") or re.match(r"^[A-Za-z]:", r) or any(p in ("..", "") for p in r.split("/")) or "\x00" in r:
        return None
    base = os.path.realpath(projet)
    abs_ = os.path.join(base, *r.split("/"))
    try:
        if os.path.islink(abs_) or not os.path.isfile(abs_):
            return None
        reel = os.path.realpath(abs_)
    except OSError:
        return None
    if os.path.commonpath([reel, base]) != base:
        return None
    return reel


def lire_da(projet):
    """(da nettoyé ou None, problèmes). Le nettoyage ne garde que des valeurs sûres."""
    ch = os.path.join(projet, ".studio", "da.json")
    try:
        with open(ch, encoding="utf-8-sig") as f:
            brut = json.load(f)
    except FileNotFoundError:
        return None, []
    except Exception as e:  # noqa: un da.json fautif ne bloque jamais le studio
        return None, [f"da.json illisible : {type(e).__name__}"]
    if not isinstance(brut, dict):
        return None, ["da.json : objet attendu"]
    pb, da = [], {}
    for k in ("version", "maj", "source", "valide_par_utilisateur"):
        if isinstance(brut.get(k), (str, int)) and not isinstance(brut.get(k), bool):
            da[k] = brut[k]
    pal = brut.get("palette")
    if isinstance(pal, dict):
        p = {k: v for k, v in pal.items() if k in ROLES and isinstance(v, str) and HEX.match(v)}
        ignores = [k for k, v in pal.items() if k != "bureau" and k not in p]
        if ignores:
            pb.append("palette : valeurs ignorées (" + ", ".join(sorted(ignores)) + ")")
        if isinstance(pal.get("bureau"), dict):
            p["bureau"] = {k: v for k, v in pal["bureau"].items() if k in ("mur", "sol", "bois", "lumiere") and isinstance(v, str) and HEX.match(v)}
        if all(k in p for k in ("fond", "texte", "accent")):
            da["palette"] = p
        else:
            pb.append("palette : fond, texte et accent sont obligatoires")
    pol = brut.get("polices")
    if isinstance(pol, dict):
        for role in ("titre", "interface"):
            x = pol.get(role)
            if isinstance(x, dict) and chemin_sur(projet, x.get("fichier")):
                da.setdefault("polices", {})[role] = {"fichier": x["fichier"].replace("\\", "/"),
                                                      "nom": str(x.get("nom") or role)[:60], "licence": str(x.get("licence") or "")[:40]}
            elif x is not None:
                pb.append(f"polices.{role} : fichier absent ou chemin refusé")
    logo = brut.get("logo")
    if isinstance(logo, dict) and chemin_sur(projet, logo.get("fichier")):
        da["logo"] = {k: logo[k].replace("\\", "/") for k in ("fichier", "fond_clair", "icone") if chemin_sur(projet, logo.get(k))}
    elif logo is not None:
        pb.append("logo : fichier absent ou chemin refusé")
    dec = brut.get("decor")
    if isinstance(dec, dict):
        d = {}
        if chemin_sur(projet, dec.get("motif")):
            d["motif"] = dec["motif"]
        c = dec.get("cadre")
        if isinstance(c, dict) and chemin_sur(projet, c.get("fichier")):
            tr = c.get("tranches") if isinstance(c.get("tranches"), list) and len(c.get("tranches")) == 4 else [16, 16, 16, 16]
            d["cadre"] = {"fichier": c["fichier"], "tranches": [max(0, min(128, int(v))) if isinstance(v, (int, float)) else 16 for v in tr]}
        aff = [a for a in (dec.get("affiches") or []) if chemin_sur(projet, a)][:3] if isinstance(dec.get("affiches"), list) else []
        if aff:
            d["affiches"] = aff
        if chemin_sur(projet, dec.get("curseur")):
            d["curseur"] = dec["curseur"]
        if d:
            da["decor"] = d
        else:
            pb.append("decor : aucun fichier utilisable")
    sons = brut.get("sons_ui")
    if isinstance(sons, dict):
        s = {k: v for k, v in sons.items() if k in ("clic", "succes", "survol", "erreur") and chemin_sur(projet, v)}
        if s:
            da["sons_ui"] = s
    return da, pb


def champ(da, nom):
    """Valeur d'un champ pointé (« polices.titre ») de da.json nettoyé, ou None."""
    v = da
    for p in nom.split("."):
        if not isinstance(v, dict) or p not in v:
            return None
        v = v[p]
    return v


def da_valide(da):
    return bool(da and isinstance(da.get("valide_par_utilisateur"), str) and da["valide_par_utilisateur"].strip())


# ------------------------------------------------------------------ copies bornées dans .studio/da/
def copier(projet, rel, genre, copies, refus):
    src = chemin_sur(projet, rel)
    if not src:
        refus.append({"chemin": str(rel), "raison": "chemin refusé"})
        return None
    taille_max, exts = LIMITES[genre]
    ext = os.path.splitext(src)[1].lower()
    if ext not in exts:
        refus.append({"chemin": rel, "raison": f"type {ext or '?'} refusé pour {genre}"})
        return None
    taille = os.path.getsize(src)
    if taille > taille_max:
        refus.append({"chemin": rel, "raison": f"{taille // 1024} Ko > {taille_max // 1024} Ko"})
        return None
    if rel in copies:
        return copies[rel]
    if len(copies) >= COPIES_MAX:
        refus.append({"chemin": rel, "raison": f"plus de {COPIES_MAX} fichiers"})
        return None
    with open(src, "rb") as f:
        donnees = f.read()
    emp = hashlib.sha256(donnees).hexdigest()[:10]
    nom = emp + "_" + re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(src))[-60:]
    dossier = os.path.join(projet, ".studio", "da")
    os.makedirs(dossier, exist_ok=True)
    dst = os.path.join(dossier, nom)
    if not os.path.exists(dst):
        with open(dst + ".tmp", "wb") as f:
            f.write(donnees)
        os.replace(dst + ".tmp", dst)
    info = {"url": "da/" + nom, "empreinte": emp, "octets": taille}
    if ext == ".svg":
        info["insertion"] = "img"          # jamais inséré dans la page : <img> seulement, donc sans script
        if re.search(rb"<script|\son[a-z]+\s*=|javascript:", donnees, re.I):
            info["contenu_actif"] = True    # noté : il reste inoffensif en <img>
    copies[rel] = info
    return info


# ------------------------------------------------------------------ jetons
def jetons_palette(pal, ajust):
    fond, surface = pal["fond"], pal.get("surface") or mix(pal["fond"], pal["texte"], 0.1)
    clair = luminance(fond) > 0.5
    texte, a = lisible(pal["texte"], [fond, surface])
    if a:
        ajust.append({"fr": "texte éclairci pour la lisibilité" if not clair else "texte foncé pour la lisibilité",
                      "en": "text lightened for readability" if not clair else "text darkened for readability",
                      "avant": pal["texte"], "apres": texte})
    accent = pal["accent"]
    accent2 = pal.get("accent2") or mix(accent, texte, 0.35)
    etats = {k: pal.get(k) for k in ("succes", "alerte", "danger")}
    ok = all(etats.values())
    if ok:
        vals = list(etats.values())
        paires = [(vals[i], vals[j]) for i in range(3) for j in range(i + 1, 3)] + [(v, x) for v in vals for x in (accent, accent2)]
        ok = all(delta_e(x, y) >= 20 for x, y in paires)
    if not ok:
        etats = dict(ETATS_REFERENCE)
        ajust.append({"fr": "couleurs d'état du studio de référence gardées (trop proches entre elles ou des accents)",
                      "en": "reference state colours kept (too close to each other or to the accents)"})
    j = {
        "--nuit": fond, "--nuit2": surface, "--texte": texte, "--bord": rgba(texte, ".16"),
        "--papier": surface, "--encre": texte, "--encre2": mix(texte, surface, 0.25), "--encre3": mix(texte, surface, 0.45),
        "--ocre": accent, "--ocre2": mix(accent, "#ffffff" if not clair else "#000000", 0.3), "--bleu": accent2,
        "--sapin": etats["succes"], "--alerte": etats["alerte"], "--rouge": etats["danger"],
        "--rayon": "10px", "--ombre": "0 10px 30px rgba(0,0,0,.35)" if not clair else "0 8px 24px rgba(0,0,0,.15)", "--degrade": "1",
        "--motif": "none", "--motif-opacite": "0", "--sans": ATELIER["--sans"], "--serif": ATELIER["--serif"],
    }
    return j, ("clair" if clair else "sombre")


def palier_atteint(da, statuts, mode, catalogue=None):
    """Palier 1 à 5. progressif : quêtes d'Identité remplies ET champs valides ; jeu : champs valides seulement."""
    qp = dict(QUETE_PALIER)
    if catalogue:
        for x in catalogue.get("quetes", []):
            h = x.get("recompense", {}).get("habillage")
            if isinstance(h, int):
                qp[h] = x["id"]
    if not da_valide(da):
        return 1
    p = 1
    for n in range(2, 6):
        if not all(champ(da, c) for c in CHAMPS_PALIER[n]):
            break
        if mode == "progressif" and not all((statuts or {}).get(qp[k]) in FAITES for k in range(2, n + 1)):
            break
        p = n
    return p


def calculer(projet, statuts=None, mode="progressif", reglages=None, catalogue=None, copier_fichiers=True):
    """Habillage complet du studio : palier, jetons CSS, polices, logo, décor, thème du bureau, ajustements."""
    reglages = reglages or {}
    mode = mode if mode in ("progressif", "atelier", "jeu") else "progressif"
    da, problemes = lire_da(projet)
    reel = palier_atteint(da, statuts, "jeu" if mode == "jeu" else "progressif", catalogue)
    ajust, copies, refus = [], {}, []
    res = {"version": 1, "mode": mode, "palier": reel, "nom": {"fr": NOMS[reel][0], "en": NOMS[reel][1]},
           "brouillon": bool(da) and not da_valide(da), "problemes_da": problemes, "theme": "sombre",
           "polices": [], "logo": None, "decor": None, "sons_ui": None, "ajustements": ajust, "refus": refus,
           "bureau": {"desaturation": 0.85} if reel == 1 else {}}
    if mode == "atelier":
        res.update(jetons=dict(ATELIER), rendu="atelier", bureau={})
        res["css"] = css(res)
        return res
    if reel == 1:
        res.update(jetons=dict(GRIS), rendu="maquette_grise")
        res["css"] = css(res)
        return res
    j, theme = jetons_palette(da["palette"], ajust)
    res["theme"], res["rendu"] = theme, "jeu"
    pb = da["palette"].get("bureau") or {}
    res["bureau"] = dict({k: v for k, v in pb.items()}, accent=j["--ocre"], accent2=j["--bleu"])
    if reel >= 3:
        for role, famille in (("titre", "Jeu Texte"), ("interface", "Jeu Interface")):
            info = copier(projet, da["polices"][role]["fichier"], "police", copies, refus) if copier_fichiers else None
            if info:
                res["polices"].append(dict(info, famille=famille, role=role, nom=da["polices"][role]["nom"],
                                           licence=da["polices"][role]["licence"] or None))
                if not da["polices"][role]["licence"]:
                    ajust.append({"fr": f"police « {da['polices'][role]['nom']} » sans licence notée : à vérifier avant la sortie",
                                  "en": f"font \"{da['polices'][role]['nom']}\" has no licence noted: check before release"})
        if len(res["polices"]) < 2 and copier_fichiers:
            reel = 2       # une police refusée (taille, type) : on reste au palier Palette, repli système
            ajust.append({"fr": "police refusée : le studio reste au palier Palette", "en": "font refused: studio stays at the Palette tier"})
    if reel >= 4:
        lg = {}
        for k in ("fichier", "fond_clair", "icone"):
            if da["logo"].get(k):
                info = copier(projet, da["logo"][k], "image", copies, refus) if copier_fichiers else None
                if info:
                    lg[k] = info
        if lg.get("fichier"):
            res["logo"] = lg
        elif copier_fichiers:
            reel = 3
    if reel >= 5:
        d = {}
        if da["decor"].get("motif"):
            m = copier(projet, da["decor"]["motif"], "image", copies, refus)
            if m:
                d["motif"] = m
                j["--motif"] = f'url("{m["url"]}")'
                j["--motif-opacite"] = "0.06"     # ≤ 6 % : lisibilité d'abord
        if da["decor"].get("cadre"):
            m = copier(projet, da["decor"]["cadre"]["fichier"], "image", copies, refus)
            if m:
                d["cadre"] = dict(m, tranches=da["decor"]["cadre"]["tranches"])
        aff = [copier(projet, a, "image", copies, refus) for a in da["decor"].get("affiches", [])]
        if [a for a in aff if a]:
            d["affiches"] = [a for a in aff if a]
        if da["decor"].get("curseur"):
            m = copier(projet, da["decor"]["curseur"], "image", copies, refus)
            if m:
                d["curseur"] = m
        res["decor"] = d or None
        if reglages.get("habillage_sons_ui") is True and da.get("sons_ui"):
            s = {k: copier(projet, v, "son", copies, refus) for k, v in da["sons_ui"].items()}
            res["sons_ui"] = {k: v for k, v in s.items() if v} or None
    if reel < res["palier"]:
        res["palier"], res["nom"] = reel, {"fr": NOMS[reel][0], "en": NOMS[reel][1]}
    res["jetons"] = j
    res["copies"] = copies
    res["css"] = css(res)
    return res


def css(res):
    """Feuille à charger après studio.html : uniquement des jetons (la mise en page ne change jamais)."""
    l = [f"/* habillage du studio : palier {res['palier']} ({res['nom']['fr']}), mode {res['mode']} */", ":root{"]
    l += [f"  {k}:{v};" for k, v in res["jetons"].items()]
    l.append("}")
    for p in res.get("polices") or []:
        fmt = {"ttf": "truetype", "otf": "opentype", "woff": "woff", "woff2": "woff2"}[p["url"].rsplit(".", 1)[-1].lower()]
        l.append(f'@font-face{{font-family:"{p["famille"]}";src:url("{p["url"]}") format("{fmt}");font-display:swap}}')
    if res.get("palier") == 1 and res.get("mode") != "atelier":
        l.append("/* maquette grise : pas de dégradés ni d'ombres douces */")
        l.append("body.habillage-1 .bt,body.habillage-1 .feuille{background-image:none!important;box-shadow:none!important}")
    return "\n".join(l) + "\n"


def ecrire(projet, res):
    """Écrit .studio/da/habillage.css et .studio/habillage.json (rien d'autre)."""
    d = os.path.join(projet, ".studio", "da")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "habillage.css.tmp"), "w", encoding="utf-8", newline="\n") as f:
        f.write(res["css"])
    os.replace(os.path.join(d, "habillage.css.tmp"), os.path.join(d, "habillage.css"))
    sortie = {k: v for k, v in res.items() if k != "css"}
    sortie["maj"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    ch = os.path.join(projet, ".studio", "habillage.json")
    with open(ch + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        json.dump(sortie, f, ensure_ascii=False, indent=1)
    os.replace(ch + ".tmp", ch)


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if not a or a[0].startswith("-"):
        print(__doc__)
        return 2
    projet = os.path.abspath(a[0])
    mode = a[a.index("--mode") + 1] if "--mode" in a else "progressif"
    etat = {}
    try:
        with open(os.path.join(projet, ".studio", "quetes_etat.json"), encoding="utf-8") as f:
            etat = {k: v.get("statut") for k, v in json.load(f).get("quetes", {}).items()}
    except Exception:  # noqa
        pass
    res = calculer(projet, etat, mode, copier_fichiers="--ecrire" in a)
    if "--ecrire" in a:
        ecrire(projet, res)
    print(json.dumps({k: v for k, v in res.items() if k != "css"}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
