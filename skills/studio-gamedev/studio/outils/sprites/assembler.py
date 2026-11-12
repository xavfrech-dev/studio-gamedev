# -*- coding: utf-8 -*-
"""
Assemble les rendus bruts (perso_sprites.py) en planches PNG + atlas JSON, et fabrique la planche de contrôle.

  python assembler.py --brut ./sprites_brut/complet --sortie ./sprites_planches
  python assembler.py --brut ./sprites_brut/test --controle-test fichier.png

Planches (par animation et par taille 128 / 256) : lignes = 8 directions, colonnes = images.
  base.png                     rendu ombré ; zones recolorables en blanc ombré
  peau|cheveux|haut|bas|chaussures.png   masques : RVB blanc, alpha = couverture de la zone
  acc_<nom>.png / acc_<nom>_masque.png   accessoire (à dessiner après le corps), même principe
"""
import os, sys, json, glob, math
import numpy as np
from PIL import Image, ImageDraw

ZONES_CORPS = [('peau', 'mA', 0), ('cheveux', 'mA', 1), ('haut', 'mA', 2), ('bas', 'mB', 0), ('chaussures', 'mB', 1)]
ACCS = ['casquette', 'bonnet', 'chapeau_conique', 'casque_audio', 'lunettes', 'beret', 'barbe']
ANIMS = {   # nom : (images, fps, assis, siège z, objet tenu)
    'marche': (8, 12, False, None, None), 'repos': (4, 3, False, None, None), 'tape': (4, 8, True, 0.36, None),
    'assis_boit': (6, 5, True, 0.36, 'tasse'), 'cafe_debout': (6, 5, False, None, 'tasse'), 'parle': (6, 6, False, None, None),
    'joie': (4, 6, False, None, None), 'gratte': (4, 8, False, None, None), 'sautille': (6, 10, False, None, None),
    'cloche': (6, 10, False, None, 'cloche'), 'manette': (4, 4, True, 0.42, 'manette'),
}
DIRS = [('SE', 'fd'), ('S', None), ('SO', 'fg'), ('O', None), ('NO', 'dg'), ('N', None), ('NE', 'dd'), ('E', None)]
PAS = 0.09

def arg(nom, d=None):
    a = sys.argv
    return a[a.index(nom) + 1] if nom in a and a.index(nom) + 1 < len(a) else d

def srgb_dec(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)

def charger(brut, anim, couche, f, d):
    """→ base RGBA prémultiplié (float 0..1, 256²), dict masques (float 0..1)."""
    pre = os.path.join(brut, anim, couche, 'f%02dd%d_' % (f, d))
    b = np.asarray(Image.open(pre + 'base_0001.png').convert('RGBA'), dtype=np.float32) / 255
    b[..., :3] *= b[..., 3:4]
    mB = np.asarray(Image.open(pre + 'mB_0001.png').convert('RGBA'), dtype=np.float32) / 255
    mB = srgb_dec(mB[..., :3]) * mB[..., 3:4]
    if couche == 'corps':
        mA = np.asarray(Image.open(pre + 'mA_0001.png').convert('RGBA'), dtype=np.float32) / 255
        mA = srgb_dec(mA[..., :3]) * mA[..., 3:4]
        src = {'mA': mA, 'mB': mB}
        masques = {z: np.clip(src[p][..., c], 0, 1) for z, p, c in ZONES_CORPS}
    else:
        masques = {'acc': np.clip(mB[..., 2], 0, 1)}
    # un masque ne dépasse jamais la couverture du pixel
    for k in masques: masques[k] = np.minimum(masques[k], b[..., 3])
    return b, masques

def reduire(x):
    """réduction 2×2 (moyenne exacte) d'une image prémultipliée ou d'un masque."""
    h, w = x.shape[:2]
    return x.reshape(h // 2, 2, w // 2, 2, *x.shape[2:]).mean(axis=(1, 3))

def vers_png_base(bp):
    a = bp[..., 3:4]
    c = np.where(a > 1e-4, bp[..., :3] / np.maximum(a, 1e-4), 0)
    return Image.fromarray(np.clip(np.concatenate([c, a], -1) * 255 + 0.5, 0, 255).astype(np.uint8), 'RGBA')

def vers_png_masque(m):
    h, w = m.shape
    out = np.empty((h, w, 4), np.uint8); out[..., :3] = 255
    out[..., 3] = np.clip(m * 255 + 0.5, 0, 255).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')

# ------------------------------------------------------------------------------------------
# Recoloration : reproduit exactement les opérations canvas décrites dans BRANCHEMENT.md
#   calque couleur = Σ masque_i × couleur_i  ('lighter')
#   résultat = base ; 'multiply' calque couleur ; 'destination-in' base
# ------------------------------------------------------------------------------------------
def hexf(h):
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)

def recolorer(bp, masques, couleurs):
    """bp prémultiplié, masques float, couleurs {zone: '#rrggbb'} → RGBA prémultiplié."""
    cl = np.zeros(bp.shape, np.float32)
    for z, m in masques.items():
        if z in couleurs:
            c = hexf(couleurs[z]); cl[..., :3] += m[..., None] * c; cl[..., 3] += m
    cl = np.clip(cl, 0, 1)
    ab, as_ = bp[..., 3:4], cl[..., 3:4]
    Cb = np.where(ab > 1e-5, bp[..., :3] / np.maximum(ab, 1e-5), 0)
    Cs = np.where(as_ > 1e-5, cl[..., :3] / np.maximum(as_, 1e-5), 0)
    Cs2 = (1 - ab) * Cs + ab * (Cs * Cb)                     # mélange 'multiply' (W3C)
    co = as_ * Cs2 + (1 - as_) * ab * Cb                      # source-over (prémultiplié)
    ao = as_ + ab * (1 - as_)
    # destination-in base : alpha × ab
    k = np.where(ao > 1e-5, ab / np.maximum(ao, 1e-5), 0)
    return np.concatenate([co * k, ao * k], -1)

def poser(fond, rgba_pre, x, y):
    """compose une image prémultipliée float sur une image PIL RGBA."""
    im = vers_png_base(rgba_pre)
    fond.alpha_composite(im, (int(x), int(y)))

# ------------------------------------------------------------------------------------------
# Planches
# ------------------------------------------------------------------------------------------
def planches(brut, sortie):
    ancres = json.load(open(os.path.join(brut, 'ancres.json'), encoding='utf-8'))
    commun = ancres['_commun']
    atlas = {
        'version': 1,
        'description': "Personnage chibi du studio : planches par animation (lignes = 8 directions, colonnes = images). Voir BRANCHEMENT.md.",
        'tailles': {}, 'directions': [], 'zones_corps': [z for z, _, _ in ZONES_CORPS], 'accessoires': ACCS,
        'anims': {},
    }
    for k, (nom, regard) in enumerate(DIRS):
        atlas['directions'].append({'index': k, 'nom': nom, 'angle_studio_deg': 45 * k, 'regard_studio': regard,
                                    'vecteur_studio': [round(math.cos(math.radians(45 * k)), 4), round(math.sin(math.radians(45 * k)), 4)]})
    for T, fac in ((256, 1), (128, 2)):
        atlas['tailles'][str(T)] = {
            'cellule': T, 'ancre_pieds': [commun['pieds'][0] / fac, commun['pieds'][1] / fac],
            'px_sprite_par_px_studio': commun['facteur_px_studio'] / fac,
            'px_par_unite_sol_axe': round(45.2548 * commun['facteur_px_studio'] / fac, 3),
            'px_par_unite_z': round(45.2548 * math.cos(math.radians(30)) * commun['facteur_px_studio'] / fac, 3),
        }
    atlas['projection'] = {'type': 'orthographique', 'elevation_deg': 30, 'azimut': "vue depuis +x+y du studio (losange 2:1, TW=32, TH=16)",
                           'repere': "1 unité = 1 case du studio ; z en cases (ZU=40 px studio ≈ 39,2 px réels, écart 2 %)"}
    atlas['clavier'] = {'local': commun['clavier_local'], 'note': "centre du clavier dans le repère du perso assis : 'avant' cases devant le point de siège, à la hauteur z (dessus du bureau 0,68)",
                        'px_256_par_direction': commun['clavier_par_direction']}
    atlas['marche'] = {'distance_par_cycle': round(4 * PAS, 3), 'note': "un cycle de 8 images couvre cette distance (cases) : image = floor(distance parcourue / distance_par_cycle × 8) mod 8"}
    for anim, (n, fps, assis, sz, objet) in ANIMS.items():
        if not os.path.isdir(os.path.join(brut, anim)): continue
        print('planche', anim, flush=True)
        couches_presentes = [c for c in ['corps'] + ACCS if os.path.isdir(os.path.join(brut, anim, c))]
        feuilles = {}
        for T in (256, 128):
            feuilles[T] = {}
            feuilles[T]['base'] = Image.new('RGBA', (T * n, T * 8))
            for z, _, _ in ZONES_CORPS: feuilles[T][z] = Image.new('RGBA', (T * n, T * 8))
            for a in couches_presentes[1:]:
                feuilles[T]['acc_' + a] = Image.new('RGBA', (T * n, T * 8))
                feuilles[T]['acc_' + a + '_masque'] = Image.new('RGBA', (T * n, T * 8))
        for d in range(8):
            for f in range(n):
                for couche in couches_presentes:
                    bp, ms = charger(brut, anim, couche, f, d)
                    for T in (256, 128):
                        b2 = bp if T == 256 else reduire(bp)
                        pos = (f * T, d * T)
                        if couche == 'corps':
                            feuilles[T]['base'].paste(vers_png_base(b2), pos)
                            for z in ms:
                                feuilles[T][z].paste(vers_png_masque(ms[z] if T == 256 else reduire(ms[z])), pos)
                        else:
                            feuilles[T]['acc_' + couche].paste(vers_png_base(b2), pos)
                            feuilles[T]['acc_' + couche + '_masque'].paste(vers_png_masque(ms['acc'] if T == 256 else reduire(ms['acc'])), pos)
        fichiers = {}
        for T in (256, 128):
            dossier = os.path.join(sortie, 'planches', str(T), anim); os.makedirs(dossier, exist_ok=True)
            for nom, im in feuilles[T].items():
                im.save(os.path.join(dossier, nom + '.png'), optimize=True)
            fichiers = {nom: 'planches/{taille}/%s/%s.png' % (anim, nom) for nom in feuilles[T]}
        anc = ancres.get(anim, {})
        atlas['anims'][anim] = {
            'images': n, 'fps': fps, 'boucle': True, 'assis': assis, 'siege_z': sz, 'objet_tenu': objet,
            'grille': {'colonnes': n, 'lignes': 8, 'colonne': 'image', 'ligne': 'direction'},
            'fichiers': fichiers,
            'ancres_256': {   # par direction puis par image : point haut de la tête (cheveux), mains
                'tete': [[anc.get(str(f), {}).get(str(d), {}).get('tete') for f in range(n)] for d in range(8)],
                'mainD': [[anc.get(str(f), {}).get(str(d), {}).get('mainD') for f in range(n)] for d in range(8)],
                'mainG': [[anc.get(str(f), {}).get(str(d), {}).get('mainG') for f in range(n)] for d in range(8)],
            },
        }
    atlas['hauteur_accessoire'] = {'casquette': 0.03, 'bonnet': 0.07, 'chapeau_conique': 0.13, 'casque_audio': 0.02, 'lunettes': 0, 'beret': 0.03, 'barbe': 0}
    json.dump(atlas, open(os.path.join(sortie, 'atlas.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(os.path.join(sortie, 'atlas.js'), 'w', encoding='utf-8') as fjs:
        fjs.write('// Copie de atlas.json pour les pages ouvertes en file:// (fetch interdit)\nwindow.ATLAS_PERSO = ')
        json.dump(atlas, fjs, ensure_ascii=False)
        fjs.write(';\n')
    print('atlas écrit')

# ------------------------------------------------------------------------------------------
# Planche de contrôle (depuis les rendus bruts) : tenues recolorées, décor studio simplifié
# ------------------------------------------------------------------------------------------
TENUES = [
    {'nom': 'Unreal (casque audio)', 'peau': '#f0c9a4', 'cheveux': '#5a3a26', 'haut': '#4b6f99', 'bas': '#373c47', 'chaussures': '#2a211b', 'acc': 'casque_audio', 'acc_couleur': '#3a3a42'},
    {'nom': 'Blender (béret)', 'peau': '#d9a77f', 'cheveux': '#3b2a20', 'haut': '#d8782f', 'bas': '#3b3838', 'chaussures': '#5a3a26', 'acc': 'beret', 'acc_couleur': '#8e2f21'},
    {'nom': 'Petit chinois (chapeau)', 'peau': '#efcfa6', 'cheveux': '#1d1a1a', 'haut': '#3d6d9e', 'bas': '#2b3340', 'chaussures': '#2a211b', 'acc': 'chapeau_conique', 'acc_couleur': '#d9b56a'},
    {'nom': 'Relecture (lunettes)', 'peau': '#eec4a0', 'cheveux': '#b9b1a6', 'haut': '#7a5c93', 'bas': '#463c4f', 'chaussures': '#2a211b', 'acc': 'lunettes', 'acc_couleur': '#3a2c22'},
    {'nom': 'Tripo (casquette)', 'peau': '#f2cfae', 'cheveux': '#a5652e', 'haut': '#5f8794', 'bas': '#403a3a', 'chaussures': '#e9e1cf', 'acc': 'casquette', 'acc_couleur': '#2f4a3a'},
    {'nom': 'Nanite (bonnet)', 'peau': '#c98f68', 'cheveux': '#1f1a18', 'haut': '#4f8a65', 'bas': '#31373a', 'chaussures': '#3a2a20', 'acc': 'bonnet', 'acc_couleur': '#b8895a'},
    {'nom': 'Joueur (barbe)', 'peau': '#efc39c', 'cheveux': '#3a2a20', 'haut': '#b2463a', 'bas': '#2f3542', 'chaussures': '#2a211b', 'acc': 'barbe', 'acc_couleur': '#3a2a20'},
]

def perso(brut, anim, f, d, tenue, T=256):
    bp, ms = charger(brut, anim, 'corps', f, d)
    img = recolorer(bp, ms, tenue)
    a = tenue.get('acc')
    if a and os.path.isdir(os.path.join(brut, anim, a)):
        ba, ma = charger(brut, anim, a, f, d)
        acc = recolorer(ba, ma, {'acc': tenue['acc_couleur']})
        img = acc + img * (1 - acc[..., 3:4])
    if T == 128: img = reduire(img)
    return img

def P(x, y, z, k, ax, ay):
    return (ax + (x - y) * 32 * k, ay + ((x + y) * 16 - z * 40) * k)

def decor_assis(dr, d, ax, ay, k, siege_z, canape=False):
    """dessine un siège (et un bureau pour les directions de bureau) en iso studio, autour du point (ax, ay)."""
    a = math.radians(45 * d); fx, fy = math.cos(a), math.sin(a)
    def boite(x, y, z, w, dd, h, col):
        pts = lambda L: [P(*p, k, ax, ay) for p in L]
        t = z + h
        dr.polygon(pts([(x, y + dd, z), (x + w, y + dd, z), (x + w, y + dd, t), (x, y + dd, t)]), fill=col[1])
        dr.polygon(pts([(x + w, y, z), (x + w, y + dd, z), (x + w, y + dd, t), (x + w, y, t)]), fill=col[2])
        dr.polygon(pts([(x, y, t), (x + w, y, t), (x + w, y + dd, t), (x, y + dd, t)]), fill=col[0])
    gris = ((70, 72, 78), (52, 54, 60), (40, 41, 46)); bois = ((170, 122, 82), (138, 98, 66), (112, 78, 52))
    if canape:
        boite(-0.35, -0.35, 0, 0.7, 0.7, siege_z, ((150, 82, 62), (120, 64, 48), (100, 52, 40)))
    else:
        boite(-0.2, -0.2, siege_z - 0.07, 0.4, 0.4, 0.07, gris)

def decor_bureau(dr, d, ax, ay, k):
    a = math.radians(45 * d); fx, fy = math.cos(a), math.sin(a)
    cx, cy = fx * 0.30, fy * 0.30
    # dessus de bureau (losange orienté) : bord avant à 0,2 devant le siège
    pts = []
    for u, v in ((-0.6, 0.2), (0.6, 0.2), (0.6, 0.9), (-0.6, 0.9)):
        x = -fy * u + fx * v; y = fx * u + fy * v
        pts.append(P(x, y, 0.68, k, ax, ay))
    dr.polygon(pts, fill=(160, 112, 72, 255), outline=(90, 60, 40, 255))
    kp = []
    for u, v in ((-0.2, -0.065), (0.2, -0.065), (0.2, 0.065), (-0.2, 0.065)):
        x = -fy * u + fx * (0.30 + v); y = fx * u + fy * (0.30 + v)
        kp.append(P(x, y, 0.69, k, ax, ay))
    dr.polygon(kp, fill=(42, 42, 46, 255))

def controle(brut, fichier, demo=True):
    from PIL import ImageFont
    try:
        police = ImageFont.truetype(arg('--police', 'DejaVuSans.ttf'), 18)
        titre = ImageFont.truetype(arg('--police', 'DejaVuSans.ttf'), 26)
    except Exception:
        police = titre = ImageFont.load_default()
    T = 256
    lignes = []
    # ligne 1 : 8 directions au repos (tenue 1)
    lignes.append(('Repos — 8 directions (SE, S, SO, O, NO, N, NE, E)', [('repos', 0, d, 0) for d in range(8)]))
    lignes.append(('Marche — images 0 à 7, direction S', [('marche', f, 1, 1) for f in range(8)]))
    lignes.append(('Assis : tape (SE, NE, NO), boit (SO), manette au canapé (S)', [('tape', 1, 0, 0), ('tape', 1, 6, 0), ('tape', 2, 4, 3), ('assis_boit', 2, 2, 1), ('assis_boit', 0, 6, 1), ('manette', 1, 1, 6), ('manette', 0, 5, 6), ('tape', 0, 1, 4)]))
    lignes.append(('Gestes : café, parle, joie, gratte, sautille, cloche', [('cafe_debout', 2, 1, 4), ('parle', 1, 0, 5), ('joie', 2, 1, 6), ('gratte', 1, 2, 3), ('sautille', 2, 1, 2), ('sautille', 0, 0, 2), ('cloche', 1, 1, 2), ('cloche', 4, 7, 2)]))
    lignes.append(('Accessoires (vue S puis NE)', [('repos', 0, 1, i) for i in range(4)] + [('repos', 0, 6, i) for i in range(4)]))
    cw = 200; marge = 40
    H = marge + sum(40 + 230 for _ in lignes) + 20
    W = marge * 2 + 8 * cw
    fond = Image.new('RGBA', (W, H), (236, 228, 207, 255))
    dr = ImageDraw.Draw(fond)
    y = marge
    for nom, cases in lignes:
        dr.text((marge, y), nom, font=titre, fill=(43, 38, 32, 255)); y += 40
        for i, (anim, f, d, t) in enumerate(cases):
            if not os.path.exists(os.path.join(brut, anim, 'corps', 'f%02dd%d_base_0001.png' % (f, d))):
                continue
            x0 = marge + i * cw
            dr.rounded_rectangle((x0 + 4, y, x0 + cw - 4, y + 222), 12, fill=(244, 237, 220, 255), outline=(216, 201, 166, 255))
            ax, ay = x0 + cw / 2, y + 190
            # sol : losange d'une case
            dr.polygon([P(-.5, -.5, 0, 1.75 * 1, ax, ay), P(.5, -.5, 0, 1.75, ax, ay), P(.5, .5, 0, 1.75, ax, ay), P(-.5, .5, 0, 1.75, ax, ay)], fill=(214, 196, 160, 255))
            assis = ANIMS[anim][2]
            if assis:
                decor_assis(dr, d, ax, ay, 1.75, ANIMS[anim][3], canape=(anim == 'manette'))
            tenue = TENUES[t]
            img = perso(brut, anim, f, d, tenue, T=128)
            im = vers_png_base(img)
            avant_bureau = assis and anim != 'manette' and d in (0, 1, 2)
            if assis and anim != 'manette' and not avant_bureau:
                decor_bureau(dr, d, ax, ay, 1.75)
            fond.alpha_composite(im, (int(ax - 64), int(ay - 112)))
            if avant_bureau:
                # bureau devant le perso (directions face caméra) : dessiné après lui
                lay = Image.new('RGBA', fond.size); d2 = ImageDraw.Draw(lay); decor_bureau(d2, d, ax, ay, 1.75)
                fond.alpha_composite(lay)
            dr.text((x0 + 12, y + 4), '%s f%d %s' % (anim, f, DIRS[d][0]), font=police, fill=(87, 82, 74, 255))
        y += 230
    fond.convert('RGB').save(fichier)
    print('contrôle :', fichier)

if __name__ == '__main__':
    brut = arg('--brut', 'sprites_brut/complet')
    if arg('--controle'):
        controle(brut, arg('--controle'))
    else:
        planches(brut, arg('--sortie', 'sprites_planches'))
