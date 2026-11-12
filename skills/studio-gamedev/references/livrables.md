# Livrables de la phase 2

Remplis les gabarits de `modeles/` avec `.studio/reponses_questionnaire.json` (réponses écrites par la page) et `.studio/profil.json`. Écris dans la langue du projet. Les réponses `à confirmer` restent visibles (marque « ? ») au lieu d'être présentées comme sûres.

| Fichier du projet | Gabarit | Contenu |
|---|---|---|
| `docs/GDD.md` | `modeles/GDD.md` | Conception du jeu |
| `docs/ROADMAP.md` | `modeles/ROADMAP.md` | Jalons, tâches, estimations, dépendances, critères, statuts, succès (écrit en phase 1 bis, avant le reste) |
| `.studio/roadmap.json` (+ copie studio) | `modeles/roadmap.json` | La même roadmap pour la page du studio (schéma : `studio.md`) |
| `docs/DECISIONS.md` | `modeles/DECISIONS.md` | Décisions D001…, décisions en attente, à confirmer |
| `docs/CHANGELOG.md` | — | Titre seul au départ |
| `docs/ASSETS.md` | — | Tableau : asset, origine, licence, outil, crédits dépensés |
| `CLAUDE.md` | `modeles/CLAUDE.md` | Règles de travail du projet |
| `.studio/reponses_questionnaire.json` | — | Réponses (écrites par la page en phase 1) |
| `.studio/profil.json` | `modeles/profil.json` | Personnages (déjà écrit en phase 1) |
| `.studio/studio.config.json` | `modeles/studio.config.json` | Paramètres du studio (phase 4) |

## Adoption : ne jamais écraser

Projet déjà commencé (`SKILL.md`, « Adoption d'un projet existant ») : chaque livrable regarde d'abord `analyse_projet.json.fichiers_proteges`.

| Fichier du projet | S'il n'existe pas | S'il existe déjà |
|---|---|---|
| `docs/ROADMAP.md`, `docs/GDD.md`, `docs/DECISIONS.md`, `docs/CHANGELOG.md`, `docs/ASSETS.md` | écrit normalement | **écrit à côté** : `docs/ROADMAP.studio.md`… ; ou, **après accord**, section délimitée `<!-- studio-gamedev -->` … `<!-- /studio-gamedev -->` ajoutée à la fin |
| `README.md` | un README court | jamais touché ; ce que le studio veut y dire va dans `README.studio.md` (ou un bloc délimité après accord) |
| `CLAUDE.md` | gabarit `modeles/CLAUDE.md` | **seulement un bloc délimité**, après accord, par `adoption.py bloc --fichier CLAUDE.md --contenu <fichier>` (ajouté à la fin, ou remplacé s'il y est déjà ; le reste n'est jamais réécrit) ; sans accord : `.studio/propositions/CLAUDE.bloc.md` |
| `.gitignore` | créé avec le bloc `.studio/` | `adoption.py gitignore` : bloc ajouté à la fin **seulement s'il manque** |
| `.claude/agents/<poste>.md` | écrit depuis `modeles/agent.md` | gardé ; le poste prend un autre nom ou réutilise l'agent |
| code, scènes, assets, réglages du moteur | — | **jamais touchés pendant l'adoption** ; ils changent ensuite tâche par tâche, comme dans tout projet |

Pas de nouvelle arborescence imposée (« Structure de dépôt par moteur » ne s'applique qu'à un nouveau projet) : le studio suit la structure et les conventions trouvées (`analyse_projet.json.conventions`). Contrôle final : `adoption.py verifier` compare chaque fichier existant à sa photo prise à l'analyse (empreinte complète, ou début identique + seul bloc délimité ajouté) ; code 1 = un fichier existant a été modifié ou supprimé.

## Roadmap : comment découper

- J0 Cadrage (en adoption : **J0 « Ce qui existe déjà »**, tâches versées avec preuve, voir `questionnaire.md`, « Mode adoption ») : questionnaire, documents, dépôt, studio (souvent fini à la fin de ce skill).
- J1 Prototype jouable : le verbe principal jouable dans une scène grise, contrôles et caméra ; critère : « on peut <verbe> pendant 1 minute sans bug bloquant ».
- J2 Boucle centrale : la boucle de 30 s et la boucle de session complètes, une sauvegarde si besoin.
- J3 Contenu : monde / niveaux, assets selon la DA (image validée d'abord), IA, histoire.
- J4 Finition : game feel, UI, son, performances sur la machine cible.
- J5 Sortie : build, page de magasin, publication (avec accord).

5 à 12 tâches par jalon. Chaque tâche : identifiant, titre, critère de « fait » vérifiable par un test ou un lancement court, poste responsable, besoin du moteur (oui / non), estimation en heures, dépendances, statut (`à faire`, `en cours`, `prêt` = préparé sans moteur, `versé`, `écart noté` ; dans `roadmap.json` : `a_faire`, `en_cours`, `pret`, `verse`, `ecart`). Chaque jalon : but, critère de fin, dépendances, fin visée, succès. Règles de génération depuis les réponses : `questionnaire.md`, « Roadmap générée ».

Adapte à l'ambition : prototype → J0 à J2 seulement ; jam → jalons en heures (`game-jam`).

## Structure de dépôt par moteur

| Moteur | Arborescence proposée | `.gitignore` |
|---|---|---|
| Godot | `game/` (projet Godot), `docs/`, `tools/`, `tests/` | `.godot/`, `*.import` générés, `export/` |
| Unity | racine = projet Unity (`Assets/`, `Packages/`, `ProjectSettings/`), `docs/`, `Tools/` | `Library/`, `Temp/`, `Obj/`, `Build*/`, `Logs/`, `UserSettings/` |
| Unreal | `Game/` (projet .uproject), `docs/`, `Tools/` | `Binaries/`, `Intermediate/`, `Saved/`, `DerivedDataCache/`, `*.sln` |
| Web (Phaser, three.js, PixiJS) | `src/`, `public/assets/`, `tests/`, `docs/` | `node_modules/`, `dist/` |
| Bevy | `src/`, `assets/`, `tests/`, `docs/` | `target/` |
| pygame / LÖVE / Defold / Ebitengine | selon le skill du moteur | selon le moteur |

Toujours : `docs/` et un `README.md` court versionnés. **`.studio/` n'est pas versionné** (profil, dictées jusqu'à 4 000 caractères, mur d'images, état de la machine : rien de cela ne doit partir sur GitHub), sauf `roadmap.json` et `studio.config.json` (chemins relatifs seulement, aucun chemin local). Bloc à mettre dans le `.gitignore` du projet dès la phase 1 (voir `studio.md`, « Installation ») :

```gitignore
# Studio gamedev : données locales (profil, dictées, images, état de la machine)
.studio/*
!.studio/roadmap.json
!.studio/studio.config.json
```

Le reste de `.studio/` n'est versionné que si l'utilisateur le demande. Git LFS pour les binaires lourds si l'utilisateur l'a choisi (`*.png`, `*.fbx`, `*.glb`, `*.wav`, `*.uasset`, `*.umap`).
