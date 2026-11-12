# Règles de travail du studio

Ces règles sont recopiées (adaptées au moteur et aux réponses) dans le `CLAUDE.md` du projet, et dans chaque définition d'agent créée pour un poste. Elles viennent d'un vrai projet mené avec des agents ; elles évitent les deux pièges classiques : le moteur saturé par plusieurs agents, et une roadmap qui ne dit plus la vérité.

## 1. Un jalon à la fois

- Le jalon en cours est écrit en tête de `docs/ROADMAP.md`. On ne commence pas le suivant tant que ses critères ne sont pas remplis.
- Un écart à un critère se **note** (avec ce qu'il faut regarder en jeu) ; il ne bloque pas forcément : le maître tranche à l'essai.
- Une tâche = un identifiant (`J1-03`), un critère de « fait » vérifiable, une branche.

## 2. Une seule chaîne moteur

- **Un seul agent à la fois** utilise le moteur (éditeur, compilation, cuisson, build, tests dans le moteur). C'est la chaîne moteur ; elle intègre, dans l'ordre, ce qui a été préparé.
- Tous les autres préparent **sans moteur**, en parallèle, chacun dans son worktree : logique pure et ses tests, données (tables, dialogues, niveaux en texte), documents, assets (image validée, puis 3D, puis nettoyage), outils.
- Avant de lancer le moteur, vérifie qu'aucun processus du moteur ne tourne déjà (liste `moteur.processus` de `studio.config.json`). En cas de doute, demande à la Direction.
- **Enchaînement** (réglage `economie.enchainer` de `studio.config.json`, `false` par défaut) : sans accord, une tâche finie **n'en lance pas une autre** ; tu la proposes dans le point ou par une décision. Si le maître a mis `enchainer: true` (ou le demande : « enchaîne », « travaille cette nuit »), le moteur ne reste pas inactif tant qu'il reste du préparé, sauf quand il joue (il le dit), et toujours dans la limite de `economie.agents_max` agents à la fois.

## 3. Tests au minimum

- Par tâche : ça compile, les tests automatiques ciblés passent, un **lancement court** prouve que la fonction s'active (une ligne de journal, un état lu).
- Pas de séries de mesures ni de dizaines de répétitions : 3 essais suffisent pour dire que ça marche.
- Ce qui se voit à l'écran (rendu, réglages graphiques, sensations), **le maître le juge lui-même** : dis-lui précisément quoi regarder et où.

## 4. Roadmap vraie en temps réel

- Une tâche n'est « faite » que lorsqu'elle est **versée dans la branche principale** avec son critère rempli ; la preuve est le hash du commit.
- À chaque versement : statut dans `docs/ROADMAP.md`, une entrée dans `docs/CHANGELOG.md`, progression écrite pour le studio.
- Ne jamais prétendre qu'une chose est finie sans l'avoir vue (commit, journal, rapport d'agent).

## 5. Le point de suivi

- L'assistant de suivi (nom, personnalité, humour, langue et fréquence dans `profil.json`) fait un point à la fréquence choisie et en fin de jalon :
  - une blague courte dans son ton (sur la situation, le code, la malchance ; jamais sur un groupe de personnes) ;
  - un tableau : chantier | étape | % | temps restant (fourchette honnête ; les estimations moteur doublent souvent) ;
  - ce qui a fini depuis le dernier point (avec le hash) ;
  - l'heure de fin prévue ;
  - ce qui attend le maître (décision, essai en jeu) : ça fait sonner la cloche du studio.
- **Si rien n'a bougé : pas de point du tout** (ni fichier, ni message). Avant chaque point programmé, lance `python -I -B <skill>/studio/outils/attendre.py --projet <projet> --point` : code 3 = rien de neuf, le tour s'arrête là.
- Le point ne lance aucun chantier et ne touche à aucune branche.
- Mise en place : tâche planifiée récurrente à la fréquence choisie (`profil.json`, **2 h par défaut** ; jamais moins que `economie.point_min` sauf demande du maître), à une minute fixe ; vérifier qu'elle n'existe pas déjà ; « stop suivi » la supprime. Pas de tâche planifiée pendant le questionnaire. Si le maître est absent depuis `economie.pause_si_absent_min` (aucun message, aucune écriture de la page), suspends les points et les lancements jusqu'à son retour ; seul le point de fin de jalon reste.

## 6. Le cycle : intégrer → version → essai → décisions

1. La Direction répartit : chaîne moteur (une) + préparations sans moteur (plusieurs).
2. La chaîne moteur intègre le préparé, tâche par tâche : tests au minimum, relecture, versement, roadmap.
3. Après quelques heures (rythme choisi à l'étape 20) : **une version à essayer** (build) et un guide court « nouveautés, quoi regarder, ce qui est connu comme cassé ».
4. Le maître essaie ; ses retours deviennent des tâches ou des décisions (`docs/DECISIONS.md`, cloche du studio).
5. On reprend : avec l'accord du maître, ou tout seul si `economie.enchainer` est vrai (alors les agents ne s'arrêtent que pour ce qui demande vraiment le maître).

## 7. Assets et crédits

- Pour chaque objet ou famille : **image cible validée d'abord** (référence, photo, génération), puis seulement la génération 3D ou la série.
- **Un seul modèle par objet** ; ne jamais doubler une dépense de crédits sans accord.
- Respecter le plafond de l'étape Budget ; vérifier le solde avec le maître avant une grosse série.
- Origine et licence de chaque asset notées (`docs/ASSETS.md`).

## 8. Dépôt et fichiers

- Une branche par tâche, worktree par agent ; commits petits, messages dans la langue du projet, ligne d'attribution de Claude.
- Pas de push ni de publication sans accord explicite.
- Données lourdes (sources d'assets, builds, captures) **hors dépôt**, dans le dossier de données choisi.
- Jamais de clé d'API dans un fichier, un commit ou à l'écran.

## 9. Progression pour le studio

Chaque agent écrit `<projet>/.studio/progression/<poste>.json` :

```json
{"pct": 42, "texte": "ce que je fais, en une ligne (120 caractères au plus)"}
```

Mis à jour à chaque étape importante ; `pct: 100` à la fin. Le studio relit ces fichiers toutes les 10 s (c'est le script d'alimentation qui les lit, pas Claude : aucun jeton).

## Gabarit pour le `CLAUDE.md` du projet

Voir `modeles/CLAUDE.md` : il reprend les sections 1 à 9 en version courte, plus le moteur, les commandes de build et de test, le dossier de données et la liste des skills à appeler (tirée de `routage_skills.md`).
