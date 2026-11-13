# Routage vers les skills spécialisés

Ce skill **n'embarque aucun skill tiers** : il les appelle s'ils sont installés (outil Skill, nom complet `plugin:skill`). S'il en manque un, dis-le, donne la commande d'installation, et continue avec ta propre connaissance.

## Skills requis et optionnels

| Paquet | Statut | Installation | Licence |
|---|---|---|---|
| **gamedev** (awesome-gamedev-agent-skills : router + 77 skills, 12 moteurs) | Fortement recommandé | `claude plugin marketplace add gamedev-skills/awesome-gamedev-agent-skills` puis `claude plugin install gamedev@awesome-gamedev-agent-skills` | Apache-2.0 |
| **ecc** (Everything Claude Code) | Optionnel | voir son dépôt (`affaan-m/ECC`) | MIT |
| Commandes intégrées de Claude Code (`/code-review`, `/simplify`, `/security-review`, `/loop`, `/schedule`, `/run`) | Inclus | — | — |

Vérifie la présence dans la liste des skills de la session (`gamedev:router`, `ecc:…`). Ne lance aucune installation sans accord.

## Règle générale

1. Au début de chaque tâche : **`gamedev:router`**. Il détecte le moteur dans le dépôt, classe la tâche et lit le minimum de skills (moteur → discipline → genre → workflow).
2. Sans le router : utilise les tables ci-dessous, dans le même ordre.
3. Lis le corps d'un skill seulement quand la tâche le demande ; ne charge pas une catégorie entière.
4. Le skill moteur décide de l'API ; le skill de discipline décide du concept ; le skill de genre décide de l'assemblage.

## Moteur → skills (plugin gamedev)

| Moteur | Base | Selon la tâche | Tests | Sortie |
|---|---|---|---|---|
| Godot 4 | `gamedev:godot-gdscript` ou `gamedev:godot-csharp`, `gamedev:godot-nodes-scenes`, `gamedev:godot-signals-groups` | `godot-2d-movement`, `godot-tilemap`, `godot-physics`, `godot-3d-essentials`, `godot-ui-control`, `godot-animation`, `godot-shaders`, `godot-resources`, `godot-audio`, `godot-multiplayer` | `godot-gdscript-headless-testing` | `godot-export` |
| Unity 6 | `gamedev:unity-csharp-scripting` | `unity-input-system`, `unity-physics`, `unity-animation`, `unity-scriptableobjects`, `unity-tilemap-2d`, `unity-navmesh` | (`ecc:csharp-testing`) | `unity-build-pipeline` |
| Unreal 5 | `gamedev:unreal-blueprints` et/ou `gamedev:unreal-cpp-gameplay` | `unreal-enhanced-input`, `unreal-behavior-trees`, `unreal-niagara` | (`ecc:cpp-testing`, tests d'automatisation du moteur) | `unreal-packaging` |
| Phaser 4 | `gamedev:phaser-core` | `phaser-arcade-physics` | (`ecc:e2e-testing`) | `itch-publish` |
| three.js | `gamedev:threejs-scene-setup` | `threejs-gltf-loading`, `threejs-materials-lighting` | (`ecc:e2e-testing`) | `itch-publish` |
| PixiJS 8 | `gamedev:pixijs-rendering` | — | — | `itch-publish` |
| Bevy | `gamedev:bevy-ecs` | — | (`ecc:rust-testing`) | — |
| Ebitengine | `gamedev:ebitengine-game` | ses références | inclus | inclus |
| pygame | `gamedev:pygame-core` | — | (`ecc:python-testing`) | — |
| LÖVE | `gamedev:love2d-core` | — | — | — |
| Defold | `gamedev:defold-core` | — | — | inclus |
| Roblox | `gamedev:roblox-luau`, `gamedev:roblox-studio-workflow` | `roblox-characters`, `roblox-ui`, `roblox-physics`, `roblox-networking`, `roblox-datastores`, `roblox-simulator-economy` | — | — |

## Tâche → skill de discipline (sans moteur)

| La tâche parle de… | Skill |
|---|---|
| DA, bible de style, sprites, textures, icônes, briefs 3D | `gamedev:create-game-assets` |
| IA ennemie, états, poursuite, chemin | `gamedev:game-ai` |
| Arbres de comportement, IA utilitaire | `gamedev:ai-behavior-trees-utility-ai` |
| Procédural, bruit, donjons, butin | `gamedev:procedural-gen` |
| Dialogues, Ink, Yarn | `gamedev:dialogue-systems` |
| Sauvegarde, emplacements, migration | `gamedev:save-systems` |
| Musique adaptative, mixage, SFX | `gamedev:audio-design` |
| Shaders | `gamedev:shader-programming` |
| Physique qui tremble, traverse, pas de temps | `gamedev:physics-tuning` |
| Niveaux, blockout, rythme | `gamedev:level-design` |
| Touches, manette, remappage | `gamedev:input-systems` |
| « Juice », secousses, hit-stop | `gamedev:game-feel` |
| Caméra | `gamedev:camera-systems` |
| HUD, menus, mise à l'échelle | `gamedev:game-ui-ux` |
| FPS bas, optimisation | `gamedev:performance-optimization` |

## Genre → skill de genre

`platformer`, `roguelike`, `rpg`, `fps-shooter`, `tower-defense`, `card-game`, `visual-novel`, `survival-crafting`, `puzzle` (préfixe `gamedev:`). Un seul genre à la fois ; le secondaire seulement si la tâche le demande.

Réponse du questionnaire (`genre.principal`) → skill de genre ; sans skill de genre, les disciplines à appeler à la place :

| Réponse | Skill de genre | Sinon (ou en plus) |
|---|---|---|
| `action_aventure` | — | `game-feel`, `camera-systems`, `level-design`, `game-ai` |
| `survie` | `survival-crafting` | `save-systems`, `procedural-gen` |
| `rpg` | `rpg` | `dialogue-systems`, `save-systems` |
| `plateforme` | `platformer` | `game-feel`, `level-design` |
| `roguelike` | `roguelike` | `procedural-gen` |
| `fps` | `fps-shooter` | `camera-systems`, `game-ai` |
| `strategie` | — | `game-ai`, `ai-behavior-trees-utility-ai`, `game-ui-ux` |
| `tower_defense` | `tower-defense` | `game-ai` |
| `gestion` | — | `game-ui-ux`, `save-systems` ; Roblox : `roblox-simulator-economy` |
| `simulation` | — | `physics-tuning`, `game-ui-ux`, `save-systems` |
| `course` | — | `physics-tuning`, `camera-systems`, `input-systems` |
| `sport` | — | `physics-tuning`, `game-ai`, `input-systems` |
| `cartes` | `card-game` | `game-ui-ux` |
| `puzzle` | `puzzle` | `level-design` |
| `visual_novel` | `visual-novel` | `dialogue-systems` |
| `horreur` | — | `audio-design`, `game-ai`, `level-design`, `shader-programming` |
| `rythme` | — | `audio-design`, `input-systems`, `game-feel` |
| `bac_a_sable` | — | `procedural-gen`, `save-systems`, `physics-tuning` |

Moteur « maison » ou sans skill moteur : pas de skill moteur ; les disciplines ci-dessus, `gamedev:prototype-fast`, et les skills de test du langage (`ecc:python-testing`, `ecc:cpp-testing`, `ecc:rust-testing`…).

## Jalon → skills attendus

| Jalon | Skills |
|---|---|
| J0 Cadrage | ce skill (questionnaire, documents) ; optionnel `ecc:blueprint` (découper), `ecc:product-lens` (valider le pourquoi), `ecc:architecture-decision-records` (format des décisions) |
| J1 Prototype jouable | `gamedev:prototype-fast` + skill moteur de base + `input-systems` + `camera-systems` (+ skill de genre pour le contrôleur) |
| J2 Boucle centrale | skill de genre + ses disciplines (ex. survie : `save-systems`, `procedural-gen`, `game-ui-ux`) |
| J3 Contenu | `level-design`, `create-game-assets`, `procedural-gen`, `dialogue-systems`, `game-ai` |
| J4 Finition | `game-feel`, `game-ui-ux`, `audio-design`, `performance-optimization`, `shader-programming` |
| J5 Sortie | skill d'export du moteur, `steam-publish` ou `itch-publish` ; `/security-review` si en ligne |
| Mode jam | `gamedev:game-jam` remplace le découpage |

## Qualité (à chaque versement)

| Besoin | Appel |
|---|---|
| Tests ciblés | skill de test du moteur ou du langage (tableau moteur), sinon `ecc:tdd-workflow` en version légère |
| Relecture | `/code-review` (intégré) ou `ecc:code-review` ; agents `ecc:cpp-reviewer`, `ecc:csharp-reviewer`, `ecc:python-reviewer` selon le langage |
| Vérification avant versement | `ecc:verification-loop` (sinon : build + tests + relecture du diff à la main) |
| Simplifier | `/simplify` |
| Travail parallèle | `ecc:parallel-execution-optimizer`, `ecc:git-workflow` (worktrees) |
| Coûts | `ecc:cost-tracking` |
| Chercher avant d'écrire un système générique | `ecc:search-first` |

## Poste du studio → skills

| Poste | Skills principaux |
|---|---|
| Direction | `gamedev:router`, `ecc:blueprint` |
| Intégration moteur | skills moteur (base, tests, sortie) |
| Code gameplay | skill de genre, disciplines de systèmes, skills de test |
| Art et DA | `gamedev:create-game-assets`, `gamedev:shader-programming` |
| Son | `gamedev:audio-design` + audio du moteur |
| Level design | `gamedev:level-design`, `gamedev:procedural-gen` |
| Narration | `gamedev:dialogue-systems` |
| Réseau | multijoueur du moteur, `roblox-networking`, `/security-review` |
| QA et tests | skills de test, `ecc:verification-loop` |
| Sortie | export du moteur, `steam-publish`, `itch-publish` |
