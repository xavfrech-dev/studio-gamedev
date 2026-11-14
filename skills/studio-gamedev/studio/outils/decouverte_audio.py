# -*- coding: utf-8 -*-
"""Découverte des musiques et des ambiances d'un projet de jeu (lecture seule du projet).

Règles (communes aux deux studios jumeaux) :
  - parcours du projet sur 6 niveaux au plus, sans les dossiers lourds ou générés (.git, Intermediate, Saved,
    DerivedDataCache, Binaries, Library, Temp, node_modules, .godot, .import, Build(s), .studio, .venv…), 40 000 entrées au plus ;
  - extensions audio : .ogg .mp3 .wav .flac .opus ;
  - MUSIQUE : nom qui commence par MUS_ / music_ / musique_ / bgm_ / ost_, ou fichier rangé dans un dossier
    « music », « musique », « musics », « bgm », « ost », « soundtrack » ;
  - AMBIANCE : nom qui contient amb / ambiance / ambience / atmo / atmos / roomtone / bed (mot entier entre _ - espace ou
    chiffres), ou dossier « ambiance(s) », « ambience(s) », « amb », « atmos » ; plus les nappes naturelles évidentes
    (riviere, ruisseau, river, stream, wind, vent, rain, pluie, fire, feu, crepitement, ocean, waves, foret, forest)
    quand le fichier dure assez (≥ 1,5 Mo en wav/flac, ≥ 150 ko compressé) et n'est pas un bruitage d'action
    (ponct, allumer, boire, éteindre, bûche, briquet, ouvre, ferme, clic, impact, pas…) ;
  - jamais un fichier déjà classé musique dans les ambiances.
Sortie : {"musiques": [chemins absolus], "ambiances": [chemins absolus]} triés.
"""
import os, re, sys, json
EXT = ('.ogg', '.mp3', '.wav', '.flac', '.opus')
SAUTER = {'.git', '.svn', '.hg', 'intermediate', 'saved', 'deriveddatacache', 'binaries', 'library', 'temp', 'tmp', 'node_modules',
          '.godot', '.import', 'build', 'builds', '.studio', '.venv', 'venv', '__pycache__', 'obj', 'logs', '.vs', '.idea', 'packaged', 'dist'}
DOS_MUS = {'music', 'musique', 'musics', 'musiques', 'bgm', 'ost', 'soundtrack'}
DOS_AMB = {'ambiance', 'ambiances', 'ambience', 'ambiences', 'amb', 'atmos', 'atmo', 'ambient'}
RE_MUS = re.compile(r'^(mus|music|musique|bgm|ost)[_\- ]', re.I)
RE_AMB = re.compile(r'(^|[_\- \d])(amb|ambiance|ambience|ambient|atmo|atmos|roomtone|bed)([_\- \d.]|$)', re.I)
RE_ACTION = re.compile(r'(ponct|allum|boire|eteindre|buche|briquet|ajout|effondr|ouvre|ferme|clic|impact|hit|step|pas_|jump|saut|orage|thunder|explos)', re.I)
RE_NAPPE = re.compile(r'(^|[_\- ])(riviere|ruisseau|river|stream|wind|vent|rain|pluie|fire|feu|crepitement|ocean|waves|vagues|foret|forest)([_\- \d.]|$)', re.I)

def decouvrir(racine, niveaux=6, max_entrees=40000):
    musiques, ambiances, vus = [], [], 0
    racine = os.path.realpath(racine)
    for dossier, sous, fichiers in os.walk(racine):
        prof = os.path.relpath(dossier, racine).count(os.sep) + (0 if dossier == racine else 1)
        sous[:] = [d for d in sous if d.lower() not in SAUTER and not d.startswith('.') and prof < niveaux]
        noms_dos = {p.lower() for p in os.path.relpath(dossier, racine).replace(os.sep, '/').split('/')}
        for f in fichiers:
            vus += 1
            if vus > max_entrees:
                return sorted(set(musiques)), sorted(set(ambiances))
            if not f.lower().endswith(EXT):
                continue
            p = os.path.join(dossier, f)
            try:
                if not os.path.isfile(p) or os.path.islink(p) or not os.path.realpath(p).startswith(racine):
                    continue
                taille = os.path.getsize(p)
            except OSError:
                continue
            base = os.path.splitext(f)[0]
            if RE_MUS.match(base) or noms_dos & DOS_MUS:
                musiques.append(p)
            elif RE_AMB.search(base) or noms_dos & DOS_AMB or (RE_NAPPE.search(base) and not RE_ACTION.search(base) and taille >= (1_500_000 if f.lower().endswith(('.wav', '.flac')) else 150_000)):
                ambiances.append(p)
    return sorted(set(musiques)), sorted(set(ambiances))

if __name__ == '__main__':
    m, a = decouvrir(sys.argv[1] if len(sys.argv) > 1 else '.')
    print(json.dumps({'musiques': m, 'ambiances': a}, ensure_ascii=False, indent=1))
