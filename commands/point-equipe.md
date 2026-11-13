---
description: Point d'équipe régulier du studio (avancement, fin prévue, décisions) / Regular team report of the studio
argument-hint: "[stop | 15 | 30 | 60 | 120]"
---

Utilise le skill `studio-gamedev`, fichier `references/point_equipe.md`.

Argument : $ARGUMENTS

- vide : lance le point d'équipe (ou fais un point tout de suite s'il tourne déjà) ;
- `stop` : arrête le point d'équipe ;
- un nombre (15, 30, 60, 120) : change la fréquence (minutes), puis relance.

Le point est coupé par défaut : le lancer revient à passer `point_auto` à `true` dans `.studio/reglages.json`. « Tout couper » dans le studio l'arrête ; le mode nuit l'empile. Réponds dans la langue de l'utilisateur.
