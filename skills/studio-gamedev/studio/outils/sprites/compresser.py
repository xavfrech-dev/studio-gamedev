# -*- coding: utf-8 -*-
"""
Compresse les planches de personnages (assembler.py) pour un dépôt public : WebP sans perte, masques réduits à
leur alpha, accessoires choisis, tailles choisies. Réécrit atlas.json et atlas.js (même contrat, chemins en .webp).

  python compresser.py --planches <dossier sprites assemblé> --sortie <skill>/studio/sprites
                       [--tailles 128,256] [--anims-256 tape,marche,repos] [--sans-acc chapeau_conique] [--sans-anims sautille]

Rien d'autre n'est copié : pas de planche de contrôle, pas de démo.
"""
import io, json, os, sys
from PIL import Image
for _flux in (sys.stdout, sys.stderr):                 # S6 : sortie en UTF-8, même redirigée (Windows)
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def arg(nom, d=None):
    a = sys.argv
    return a[a.index(nom) + 1] if nom in a and a.index(nom) + 1 < len(a) else d


ZONES = ('peau', 'cheveux', 'haut', 'bas', 'chaussures')


def ecrire_webp(src, dst, masque):
    im = Image.open(src)
    im.load()
    im = im.convert('RGBA')
    if masque:   # seul l'alpha sert à la recoloration : RVB blanc partout (compresse bien mieux)
        a = im.getchannel('A')
        im = Image.new('RGBA', im.size, (255, 255, 255, 0))
        im.putalpha(a)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    b = io.BytesIO()
    im.save(b, 'WEBP', lossless=True, quality=100, method=4, exact=False)
    with open(dst, 'wb') as f:
        f.write(b.getvalue())
    return len(b.getvalue())


def main():
    src = arg('--planches')
    sortie = arg('--sortie')
    if not src or not sortie:
        print(__doc__)
        return 2
    tailles = [t for t in (arg('--tailles', '128') or '128').split(',') if t]
    anims256 = set((arg('--anims-256', '') or '').split(',')) - {''}
    sans_acc = set((arg('--sans-acc', '') or '').split(',')) - {''}
    sans_anims = set((arg('--sans-anims', '') or '').split(',')) - {''}
    with open(os.path.join(src, 'atlas.json'), encoding='utf-8') as f:
        atlas = json.load(f)
    atlas['anims'] = {k: v for k, v in atlas['anims'].items() if k not in sans_anims}
    atlas['accessoires'] = [a for a in atlas['accessoires'] if a not in sans_acc]
    for a in sans_acc:
        atlas.get('hauteur_accessoire', {}).pop(a, None)
    total = 0
    for nom, an in atlas['anims'].items():
        fichiers = {}
        for cle, chemin in an['fichiers'].items():
            if cle.startswith('acc_') and cle.replace('acc_', '').replace('_masque', '') in sans_acc:
                continue
            fichiers[cle] = chemin.replace('.png', '.webp')
            masque = cle in ZONES or cle.endswith('_masque')
            for t in tailles:
                if t == '256' and anims256 and nom not in anims256:
                    continue
                s = os.path.join(src, chemin.replace('{taille}', t))
                d = os.path.join(sortie, chemin.replace('{taille}', t).replace('.png', '.webp'))
                total += ecrire_webp(s, d, masque)
        an['fichiers'] = fichiers
        # tailles réellement livrées pour cette animation (le studio prend la plus grande disponible)
        an['tailles'] = [int(t) for t in tailles if not (t == '256' and anims256 and nom not in anims256)]
    atlas['tailles'] = {t: v for t, v in atlas['tailles'].items() if t in tailles}
    atlas['format'] = 'webp'
    atlas['description'] = ("Personnage chibi du studio (rendu Blender, licence MIT du skill) : planches par animation "
                            "(lignes = 8 directions, colonnes = images), recoloration par masques. Voir LISEZMOI.md.")
    os.makedirs(sortie, exist_ok=True)
    brut = json.dumps(atlas, ensure_ascii=False, separators=(',', ':'))
    with open(os.path.join(sortie, 'atlas.json'), 'w', encoding='utf-8') as f:
        f.write(brut)
    with open(os.path.join(sortie, 'atlas.js'), 'w', encoding='utf-8') as f:
        f.write('window.ATLAS_PERSO = ' + brut + ';\n')
    total += len(brut.encode('utf-8')) * 2
    print(f'{total / 1e6:.2f} Mo écrits dans {sortie}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
