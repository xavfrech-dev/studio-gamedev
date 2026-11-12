# sprites/ : les personnages du studio

Personnage « chibi » modélisé, animé et rendu dans Blender pour ce skill (`../outils/sprites/perso_sprites.py`), puis assemblé (`assembler.py`) et compressé pour le dépôt (`compresser.py`). **Licence : MIT du skill** (rendus faits pour le skill, aucun asset tiers, aucun élément d'un jeu).

- `atlas.json` (et `atlas.js` : la même chose en `window.ATLAS_PERSO`) : tailles, directions, animations, ancres (pieds, tête, mains), clavier, marche.
- `planches/<taille>/<animation>/*.webp` : une ligne par direction (8 : SE, S, SO, O, NO, N, NE, E ; angle = d × 45°, 0 = +x de la grille), une colonne par image.
  - `base` : rendu ombré avec contour ; zones recolorables en blanc ombré.
  - `peau`, `cheveux`, `haut`, `bas`, `chaussures` : masques (seul l'alpha compte).
  - `acc_<nom>` / `acc_<nom>_masque` : accessoire à poser par-dessus (`casquette`, `bonnet`, `casque_audio`, `lunettes`, `beret`, `barbe`).
- Tailles : 128 px pour toutes les animations ; 256 px (écrans HiDPI) pour `tape`, `marche`, `repos`, `cafe_debout`.
- Animations : `repos`, `marche`, `tape` (assis), `assis_boit`, `cafe_debout`, `parle`, `joie`, `gratte`, `cloche`, `manette` (assis au canapé).

`../sprites.js` teint une planche par (look, animation, direction, taille) avec trois opérations canvas (pas de `getImageData`), la garde en cache et renvoie `null` tant que rien n'est chargé : la page garde alors son dessin vectoriel.

Régénérer (Blender 4.5) :

```
blender --background --factory-startup --python ../outils/sprites/perso_sprites.py -- --sortie sprites_brut/complet
python ../outils/sprites/assembler.py --brut sprites_brut/complet --sortie sprites_planches
python ../outils/sprites/compresser.py --planches sprites_planches --sortie . --tailles 128,256 --anims-256 tape,marche,repos,cafe_debout --sans-acc chapeau_conique --sans-anims sautille
```
