# Questionnaire

## Mode d'emploi

Le questionnaire **se joue dans la page du studio**, comme un jeu pour créer son jeu :
- l'assistant (personnage) accueille le maître, puis pose les questions **une par une** dans une scène ;
- chaque question = des **cartes de choix illustrées**, la ★ mise en avant (plus grande, lumineuse, badge « recommandé »), un **champ libre** et un **bouton micro** ;
- une barre de progression par **chapitres** ; chaque chapitre terminé **construit une partie du studio** (bureau, décor) ;
- on peut **toujours** répondre à la voix ou par écrit, revenir en arrière, passer (« je ne sais pas » = la ★, marquée `à confirmer`).

Les questions sont des **données** (`studio/questions.fr.json`, `studio/questions.en.json`, format plus bas) que la page affiche ; ce fichier-ci en est la version lisible. Les deux fichiers sont produits par `studio/outils/construire_questions.py` (source unique, les deux langues côte à côte) : pour changer une question, modifie ce script puis relance-le (`python -I -B studio/outils/construire_questions.py`), et reporte le changement ici.

Toi (Claude), pendant que la page tourne : tu écris `deductions.json` après le pitch, `questions_suivi.json` si une réponse doit être précisée, et tu lis `.studio/reponses_questionnaire.json` (réponses).

**Repli conversation** (pas de studio) : mêmes questions avec `AskUserQuestion` (1 à 4 questions par appel, 2 à 4 choix, « Autre » d'office), une étape par appel, ★ en premier suffixé « (recommandé) ». Même fichier de réponses.

Règles communes :
- Le ★ indiqué ici est le défaut ; il est recalculé avec le pitch et les réponses précédentes (règles R, via `deductions.json`).
- Une ligne de contexte courte par question (pourquoi elle compte), dite par l'assistant dans son ton.
- Réponse libre gardée telle quelle et résumée au récapitulatif.

## Chapitres de la page et studio qui se construit

| Chapitre | Étapes ci-dessous | Ce qui apparaît dans le studio à la fin du chapitre |
|---|---|---|
| 1. Vision | 0 Pitch, 1 Vision, 2 Genre, 3 Public | Le bureau de direction et le tableau des 3 piliers ; l'enseigne du studio au nom du jeu |
| 2. Gameplay | 6 Caméra, 7 Gameplay central, 8 Boucle, 9 Progression | Le bureau Code gameplay, un tableau blanc avec la boucle dessinée |
| 3. Monde | 10 Monde (dont paysage et saisons), 11 Histoire | La table de level design avec une maquette ; une étagère de livres si l'histoire compte |
| 4. DA | 12 Direction artistique, 14 Interface | L'atelier d'art (chevalet, planches au mur aux couleurs de la palette) |
| 5. Son | 13 Son et musique | La cabine son (micro, enceintes) ; une musique d'ambiance douce si le maître l'active |
| 6. Technique | 4 Plateforme, 5 Moteur, 15 Multijoueur | La salle moteur (machine au logo neutre du moteur choisi) ; une baie réseau si multijoueur |
| 7. Ambition | 16 Monétisation, 17 Ambition, 18 Outils IA, 19 Budget, 20 Jalons | Le mur de la roadmap (jalons en post-it, remplis par la roadmap générée à la fin) et la cloche des décisions |
| 8. Personnages | P Personnages | Le maître et l'assistant prennent leur apparence ; la porte du studio s'ouvre, l'équipe arrive |

Ordre : l'accueil demande seulement le **nom du maître** (l'assistant doit savoir comment l'appeler) et le **mode** ; le chapitre Personnages est ★ à la fin (« et maintenant, donne-moi une tête ! ») mais la page propose « le faire maintenant ». Au départ, l'assistant a une apparence neutre par défaut.

Mode **rapide** : les mêmes chapitres, avec seulement les questions marquées `rapide` dans `questions.json` ; chaque chapitre construit quand même son décor.

## Accueil et choix du mode

L'assistant se présente (« Salut ! Je suis ton assistant. On va créer ton jeu ensemble. ») et demande d'abord : « Comment je t'appelle ? » (texte ou voix). Puis :

| Question | Choix |
|---|---|
| Comment on cadre ce jeu ? | ★ **Rapide** : ~20 questions, 5 à 8 min, le reste est déduit et marqué à confirmer · **Complet** : 20 étapes, ~25 min · **Reprise** : je reprends un questionnaire commencé |
| Tu as déjà fait des jeux ? | ★ Quelques petits projets · Jamais · Oui, plusieurs sortis · Je suis pro |

La 2e question règle le niveau de détail des explications et pèse sur le ★ du moteur et de l'ambition.

## Étape 0 : pitch (texte libre, pas d'outil à choix)

Demande en une phrase : « Raconte ton jeu en 2 ou 3 phrases : ce qu'on fait, où, et ce qui le rend différent. » Si l'utilisateur n'a pas d'idée : propose 3 pitchs courts tirés de son expérience et de ses goûts (une question), ou le mode « jam » (R12).

Déduis du pitch : genre probable, caméra, 2D/3D, ton, références. Ces déductions deviennent les ★ des étapes suivantes.

## Étape P : personnages du studio (comme dans un vrai jeu)

Chapitre 8 de la page (★ à la fin, ou « maintenant » si le maître le choisit à l'accueil). Dans la page, c'est un **éditeur de personnage** avec aperçu animé (type `personnage`) ; en mode rapide, boutons « Au hasard » et « Par défaut » pour aller vite. Résultat : `.studio/profil.json` (format plus bas). Les tableaux ci-dessous servent au repli conversation et à définir les options de l'éditeur.

**P1. Le maître (ton avatar)**

| Question | Choix |
|---|---|
| Ton nom dans le studio ? | texte libre (prénom ou pseudo) ; ★ le prénom connu de l'utilisateur s'il l'a donné |
| Ta morphologie ? | ★ Moyenne · Mince · Costaud · Petite |
| Couleur de peau ? | 4 choix parmi une palette de 8 teintes (claire, claire dorée, mate, olive, brune, foncée, très foncée) + Autre (couleur libre) ; ne mets pas de ★ ici, demande simplement |
| Cheveux ? | Courts · Longs · Bouclés · Rasé / chauve (puis couleur en Autre ou question suivante) |

| Question | Choix |
|---|---|
| Couleur des cheveux ? | Brun · Noir · Blond · Roux (Autre : gris, bleu…) |
| Ta tenue ? | ★ Sweat à capuche · Chemise · Bleu de travail · Tenue de héros (puis 2 couleurs) |
| Tes couleurs ? | ★ Celles de la DA du jeu · Vert et ocre · Bleu et blanc · Noir et rouge |
| Un accessoire ? | ★ Casque audio · Casquette · Lunettes · Chapeau (Autre : béret, couronne, barbe, bandeau, capuche, cornes…) |

**P2. L'assistant de suivi** (celui qui fait les rapports, sonne la cloche des décisions, analyse le projet en continu, vit sa vie dans le studio et raconte des blagues)

| Question | Choix |
|---|---|
| Comment s'appelle-t-il ? | texte libre ; propose 3 noms selon la personnalité choisie (« Bidule », « Jeeves », « Capitaine »…) |
| Son titre ? | ★ Assistant · Intendant · Sidekick · Majordome |
| Qu'est-ce que c'est ? | ★ Un humain · Un robot · Un animal (chat, corbeau, renard…) · Une créature (fantôme, gobelin, slime…) |
| Sa personnalité ? | ★ Espiègle · Sérieux et carré · Sarcastique · Zen (Autre : pirate, majordome anglais, sergent instructeur…) |

| Question | Choix |
|---|---|
| Son humour ? | ★ Léger · Absurde · Geek · Noir (Autre : aucun) — l'humour porte toujours sur la situation, le code, la malchance ; jamais sur un groupe de personnes |
| Il te fait un rapport tous les… | ★ 2 h · 1 h · 30 min · 15 min (seulement si quelque chose a bougé ; + toujours un point en fin de jalon ; plus souvent = plus de jetons) |
| Dans quelle langue ? | ★ Celle du projet · Français · Anglais (Autre) |
| Il te parle à voix haute ? | ★ Non, des bulles seulement · Oui (voix du navigateur) · Seulement pour la cloche |
| Son apparence ? | ★ Je la choisis comme pour moi (repose P1 morphologie / peau / cheveux / tenue / accessoire) · Au hasard · Assortie à la mienne · Assortie à la DA du jeu |

Récapitule les deux personnages en deux lignes avant de passer à la suite (« Alex, directeur, casque audio, sweat vert ; Bidule, assistant espiègle, robot, humour léger, rapport toutes les 2 h »).

## Étapes du mode complet

### 1. Vision

| Question | Choix |
|---|---|
| L'émotion principale du joueur ? (multi) | ★ déduite du pitch · Tension / peur · Maîtrise / défi · Détente / contemplation · Découverte · Puissance · Rire |
| Trois piliers (ce que chaque fonction doit servir) ? | ★ 3 piliers proposés depuis le pitch · Je les écris (Autre) |
| Jeux de référence ? | texte libre (« comme X mais Y ») ; ★ 2 références déduites du pitch |
| Pourquoi ce jeu, pourquoi toi ? | ★ Pour le plaisir / apprendre · Pour le vendre · Pour un concours / une jam · Pour un public précis — si « vendre » et le pitch est flou : propose `ecc:product-lens` (optionnel) |

### 2. Genre

| Question | Choix |
|---|---|
| Genre principal ? | ★ déduit · Action / aventure · Survie / crafting · RPG · (Autre : plateforme, roguelike, FPS, tower defense, cartes, visual novel, puzzle, gestion, course, sport, horreur, simulation…) |
| Genre secondaire ? | ★ Aucun · 2 proposés compatibles |
| Solo ou durée de session ? | ★ Sessions de 20 à 60 min · Courtes (< 10 min) · Longues (> 1 h) |

Si le genre correspond à un skill de genre installé (`platformer`, `roguelike`, `rpg`, `fps-shooter`, `tower-defense`, `card-game`, `visual-novel`, `survival-crafting`, `puzzle`), lis sa description pour proposer ensuite les systèmes typiques (étape 7).

### 3. Public

| Question | Choix |
|---|---|
| Pour qui ? | ★ Joueurs réguliers · Grand public / familles · Joueurs hardcore · Mes potes et moi |
| Âge visé (classification) ? | ★ 12+ · Tout public · 16+ · 18+ |
| Accessibilité prioritaire ? (multi) | ★ Sous-titres et taille du texte · Touches remappables · Daltonisme · Difficulté réglable |
| Langues du jeu ? | ★ Français et anglais · Anglais seul · Français seul · Plus (Autre) |

### 4. Plateforme

| Question | Choix |
|---|---|
| Sur quoi on joue ? (multi) | ★ PC Windows · Navigateur web · Mobile · Consoles (Autre : Mac, Linux, Steam Deck, VR) |
| Contrôles ? (multi) | ★ Clavier-souris · Manette · Tactile · Les deux premiers |
| Machine cible ? | ★ PC milieu de gamme · PC haut de gamme · Petite config / portable · Mobile |

### 5. Moteur

Calcule le ★ (R5). Présente au plus 4 choix pertinents, avec une demi-ligne de raison.

| Question | Choix typiques |
|---|---|
| Quel moteur ? | ★ calculé · Godot 4 · Unity 6 · Unreal 5 (Autre : Phaser, three.js, PixiJS, Bevy, Ebitengine, LÖVE, pygame, Defold, Roblox, moteur maison) |
| Quel langage ? | selon le moteur : Godot ★ GDScript / C# ; Unity C# ; Unreal ★ Blueprints + C++ / Blueprints seuls / C++ ; web ★ TypeScript / JavaScript |
| Version du moteur ? | ★ La dernière stable (version de référence des skills) · Une version précise (Autre) |
| Contrôle de version ? | ★ Git + LFS pour les gros fichiers · Git sans LFS · Pas encore |

### 6. Caméra et perspective

| Question | Choix |
|---|---|
| 2D ou 3D ? | ★ déduit · 2D · 3D · 2,5D |
| Caméra ? | 3D : ★ déduit · 1re personne · 3e personne · Isométrique / vue de dessus — 2D : ★ Côté (plateforme) · Vue de dessus · Isométrique · Écran fixe |
| Caméra libre ou guidée ? | ★ Libre (souris / stick) · Guidée / scriptée · Mixte |

### 7. Gameplay central

| Question | Choix |
|---|---|
| Le verbe principal (ce que le joueur fait 80 % du temps) ? | ★ déduit · 3 verbes proposés (explorer, combattre, construire, survivre, résoudre…) |
| Systèmes du jeu ? (multi ; en repli conversation, deux appels de 4 choix) | ★ ceux du skill de genre · Combat · Inventaire · Fabrication · Dialogues · Sauvegarde · IA ennemie · Génération procédurale · Physique · Météo / cycle jour-nuit · Économie |
| Difficulté ? | ★ Réglable · Dure et juste · Facile / détente · Adaptative |
| Mort / échec ? | ★ Retour au dernier point de sauvegarde · Mort définitive (roguelike) · Pas d'échec · Perte partielle |

### 8. Boucle

| Question | Choix |
|---|---|
| La boucle de 30 s ? | ★ proposée depuis le verbe (« repérer → s'approcher → agir → récompense ») · Je l'écris |
| La boucle de session ? | ★ proposée (« sortir → récolter → rentrer → améliorer ») · Je l'écris |
| Qu'est-ce qui fait revenir ? (multi) | ★ Progression du personnage · Histoire · Nouveaux contenus / procédural · Défi / score · Construction de base |

### 9. Progression

| Question | Choix |
|---|---|
| Type de progression ? (multi) | ★ déduit · Compétences / niveaux · Équipement · Débloquage de zones · Connaissance du joueur seulement |
| Progression méta (entre parties) ? | ★ Aucune · Légère (débloquages) · Forte (roguelite) |
| Durée de vie visée ? | ★ 5 à 10 h · < 2 h · 20 h + · Infinie / rejouable |

### 10. Monde

| Question | Choix |
|---|---|
| Structure ? | ★ déduit · Niveaux successifs · Monde ouvert · Hub et zones · Une seule arène / carte |
| Taille ? | ★ Petite et dense · Moyenne · Grande (avertir sur le coût) · Procédurale |
| Lieu et époque ? | texte libre ; ★ déduit du pitch |
| Paysage dominant ? | ★ déduit · Forêts et campagne · Montagne / neige · Désert · Île / tropiques · Ville · Mer · Souterrain · Espace · Monde imaginaire |
| Des saisons ? | ★ Pas de saisons · Le cycle des 4 saisons · Printemps · Été · Automne · Hiver |
| Monde fait main ou procédural ? | ★ Fait main · Procédural · Mixte (base procédurale, lieux clés à la main) |

### 11. Histoire

| Question | Choix |
|---|---|
| Place de l'histoire ? | ★ Légère (contexte, quelques moments) · Aucune · Importante · Au centre (narratif) |
| Comment on la raconte ? (multi) | ★ Environnement et objets · Dialogues · Cinématiques · Journal / textes |
| Choix du joueur ? | ★ Aucun ou cosmétiques · Quelques embranchements · Fortement ramifiée |
| Fin ? | ★ Une fin · Plusieurs fins · Pas de fin (bac à sable) |

### 12. Direction artistique

| Question | Choix |
|---|---|
| Style visuel ? | ★ déduit · Réaliste · Stylisé / peint · Pixel art (Autre : low poly, cel shading, voxel, dessin à la main) |
| Palette et ambiance ? | ★ proposée depuis l'émotion · Chaude · Froide · Contrastée |
| D'où viennent les assets ? (multi) | ★ Mélange : packs gratuits + génération + retouche · Faits main · Achetés · Générés par IA |
| Images de référence ? | ★ J'en ai (dossier ou liens) · Propose-moi des planches · Pas encore |

Règle à noter dans le GDD : pour chaque famille d'assets, **valider une image cible avant de produire la série** (skill `create-game-assets`).

### 13. Son et musique

| Question | Choix |
|---|---|
| Musique ? | ★ Adaptative selon la situation · Ambiante discrète · Aucune · Forte présence |
| Sources ? (multi) | ★ Bibliothèques libres de droits · Composée · Générée par IA · Jeux de sons achetés |
| Voix ? | ★ Aucune · Quelques sons / onomatopées · Doublage partiel · Complet |
| Ambiance sonore ? | ★ Importante (3D, météo, faune) · Sobre · Minimale |

### 14. Interface

| Question | Choix |
|---|---|
| HUD ? | ★ Minimal / diégétique · Classique · Riche (jeu de gestion) |
| Style des menus ? | ★ Dans l'univers du jeu (carnet, terminal…) · Sobre et moderne · Rétro |
| Écrans indispensables ? (multi) | ★ Menu, options, pause · Inventaire · Carte · Journal / quêtes |

### 15. Multijoueur

| Question | Choix |
|---|---|
| Multijoueur ? | ★ Non (solo) · Coop en ligne · Coop locale / écran partagé · Compétitif en ligne |
| (si oui) Combien de joueurs ? | ★ 2 à 4 · 2 · 5 à 16 · Massif |
| (si en ligne) Architecture ? | ★ Un joueur héberge · Serveur dédié · Services du moteur / plateforme |
| (si en ligne) Quand ? | ★ Prévu dès l'architecture, livré après le solo · Dès le prototype |

### 16. Monétisation

| Question | Choix |
|---|---|
| Modèle ? | ★ Gratuit / projet perso · Achat unique · Free-to-play · Dons / pay-what-you-want |
| Où le publier ? (multi) | ★ itch.io · Steam · Stores mobiles · Nulle part pour l'instant |
| (si achat) Prix visé ? | ★ 5 à 15 € · < 5 € · 15 à 30 € · > 30 € |
| (si F2P) Ce qu'on vend ? | ★ Cosmétiques seulement · Contenus · Confort (avertir : pas de pay-to-win par défaut) |

### 17. Ambition et durée

| Question | Choix |
|---|---|
| Taille du projet ? | ★ calculée (R8) · Prototype (1 à 2 semaines) · Petit jeu complet (1 à 3 mois) · Jeu moyen (6 à 12 mois) |
| Temps disponible ? | ★ Quelques heures par semaine · Soirs et week-ends · Temps plein · Une jam (48 à 72 h) |
| Équipe humaine ? | ★ Moi seul (+ les agents) · 2 à 3 personnes · Plus |
| Date ou étape cible ? | texte libre ; ★ « une version jouable dans 2 semaines » |

### 18. Outils IA autorisés

| Question | Choix |
|---|---|
| Code ? | ★ Oui, par les agents, avec relecture · Oui sans relecture · Seulement des suggestions |
| Images / textures / concept art ? | ★ Oui, image validée d'abord · Non · Seulement pour des maquettes |
| Modèles 3D (image vers 3D) ? | ★ Oui, après image validée, un modèle par objet · Non · Maquettes seulement |
| Son / musique / voix ? | ★ Seulement des maquettes · Oui · Non |

Ajoute une question si besoin : « Quels outils as-tu déjà ? » (multi : génération d'images, génération 3D, Blender, musique) ; les noms d'outils sont ceux que l'utilisateur donne.

### 19. Budget de crédits

| Question | Choix |
|---|---|
| Budget d'usage de Claude ? | ★ Normal (agents en parallèle raisonnables) · Économe (1 à 2 agents) · Large (plusieurs agents en continu) |
| Budget de génération (images, 3D, son) par jalon ? | ★ Je fixe un plafond (Autre : nombre de crédits) · Aucun (pas de génération payante) · Pas de plafond (demander avant chaque grosse série) |
| Règle de dépense ? | ★ Un seul essai par objet, demander avant de refaire · Jusqu'à 2 essais · Libre dans le plafond |

Rappel : aucune clé d'API n'est écrite dans les fichiers ; les soldes de crédits se vérifient avec l'utilisateur avant une grosse série.

### 20. Jalons et rythme de travail

| Question | Choix |
|---|---|
| Découpage ? | ★ Proposé : J0 cadrage · J1 prototype jouable · J2 boucle centrale · J3 contenu · J4 finition · J5 sortie · Plus court (prototype puis jeu) · Je le décris |
| Rythme des versions à essayer ? | ★ Toutes les quelques heures de travail · Une par jour · Une par jalon |
| Les agents continuent sans toi ? | ★ Oui, ils enchaînent tant qu'il y a du préparé, et s'arrêtent pour ce que tu dois voir · Non, ils attendent mon feu vert à chaque tâche |
| Vérifications ? | ★ Au minimum : compiler, quelques tests, un lancement court ; je regarde moi-même en jeu · Poussées (séries de tests, captures) |
| Dossier pour les données lourdes (hors dépôt) ? | ★ Un dossier à côté du projet · Dans le projet (ignoré par git) · Un autre disque (Autre : chemin) |

Ces réponses, avec celles des étapes 6 à 19, donnent la roadmap générée à la fin (voir « Roadmap générée »).

## Version rapide (questions `rapide: true`, 23 questions)

1. Accueil : nom du maître, mode, expérience.
2. Vision : pitch (texte ou voix), genre.
3. Gameplay : 2D / 3D et caméra, verbe principal.
4. Monde : structure (niveaux, monde ouvert…).
5. DA : style visuel.
6. Son : musique (une question).
7. Technique : plateforme, moteur (★ calculé), multijoueur.
8. Ambition : monétisation, taille, temps disponible, outils IA autorisés (`ia.autorises`, multi, posée seulement en mode rapide : en mode complet elle est remplacée par les 4 questions détaillées), budget de génération.
9. Personnages : nom et personnalité de l'assistant, fréquence des rapports ; apparences « au hasard » ou « par défaut », sauf si le maître veut les choisir (alors le chapitre complet).

Tout le reste prend son ★ et est marqué `à confirmer` dans `reponses_questionnaire.json` et dans `DECISIONS.md` (section « À confirmer »). La reprise les reposera plus tard.

## Règles d'adaptation

- **R1 Roblox** : plateforme = Roblox (PC, mobile, consoles), moteur = Roblox Studio (Luau), monétisation = Robux (passes, objets) ; saute 4, 5 et la question « où publier ».
- **R2 Navigateur** : ★ moteur = Phaser (2D) ou three.js (3D) ; machine cible = « petite config » ; publication ★ itch.io.
- **R3 Mobile** : contrôles tactiles ; ★ Godot ou Unity ; avertir si 3D réaliste.
- **R4 Projet existant** (moteur détecté en phase 0) : moteur et langage fixés ; saute 5.
- **R5 Calcul du ★ moteur** : 
  - 2D, débutant ou petit projet → Godot.
  - 3D réaliste, monde ouvert, PC haut de gamme → Unreal (avertir : lourd, compilations longues, une seule chaîne moteur indispensable).
  - 3D stylisé, mobile ou console, équipe connaissant C# → Unity.
  - 3D petite à moyenne, open source voulu → Godot.
  - Navigateur → R2. Roblox → R1.
  - Langage déjà connu : Rust → Bevy, Go → Ebitengine, Python → pygame (petits jeux), Lua → LÖVE ou Defold.
  - Sans préférence → Godot (le moteur le mieux couvert par les skills gamedev).
- **R6 Solo** (15 = Non) : saute les questions 15 suivantes ; pas de poste Réseau.
- **R7 2D** : caméras proposées 2D seulement ; pas de question « 1re personne ».
- **R8 Calcul du ★ ambition** : temps disponible × expérience × taille du monde. Débutant + monde ouvert 3D → ★ « Prototype » puis « Petit jeu », et un avertissement clair sur le périmètre.
- **R9 Histoire = aucune** : saute la suite de 11 ; pas de poste Narration.
- **R10 Pas de génération IA** (18) : saute 19 (budget de génération) ; poste Art = intégration d'assets existants.
- **R11 Gratuit / perso** : saute prix et F2P.
- **R12 Jam** (temps = jam) : version rapide forcée, jalons = heures (J0 1 h, J1 prototype 6 h…), monétisation et budget sautés, skill `game-jam`.
- **R13 Pro** (expérience = pro) : explications réduites au minimum, mode complet proposé ★.
- **R14 Genre avec skill** : les systèmes ★ de l'étape 7 viennent du skill de genre.
- **R15 Âge 18+ ou horreur** : l'humour noir de l'assistant reste possible ; pour « tout public », ★ humour = léger.

## Format des questions pour la page : `studio/questions.json`

Livré avec le studio (une version par langue : `questions.fr.json`, `questions.en.json`, mêmes `id` partout ; seuls les textes changent). La page les affiche une par une, dans l'ordre, en sautant celles dont la condition `si` est fausse ou dont la valeur est déjà fixée par `deductions.json`. Contenu actuel : 96 questions (23 en mode rapide), 377 cartes, 264 illustrations ; chapitres `accueil`, les 8 chapitres de la page, puis `fin` (récapitulatif). Le bloc `roadmap` du fichier donne les textes de l'écran « Voici ta roadmap » et du panneau Roadmap (`attend: "roadmap.json"`, `sautable: false`).

```json
{
  "version": 1,
  "langue": "fr",
  "chapitres": [
    {"id": "vision", "titre": "Vision", "construit": ["bureau_direction", "tableau_piliers", "enseigne"]},
    {"id": "gameplay", "titre": "Gameplay", "construit": ["bureau_code", "tableau_boucle"]}
  ],
  "questions": [
    {
      "id": "genre.principal",
      "chapitre": "vision",
      "type": "choix",
      "rapide": true,
      "titre": "Quel est le genre principal de ton jeu ?",
      "aide": "Le genre décide des systèmes qu'on va construire en premier.",
      "choix": [
        {"id": "action_aventure", "libelle": "Action / aventure", "detail": "Explorer, se battre, avancer dans une aventure.", "illustration": "cartes/epee.svg", "mots_voix": ["action", "aventure"]},
        {"id": "survie", "libelle": "Survie / crafting", "detail": "Récolter, fabriquer, tenir face au monde.", "illustration": "cartes/feu_camp.svg", "mots_voix": ["survie", "crafting", "fabrication"]},
        {"id": "rpg", "libelle": "RPG", "detail": "Un héros qui grandit : stats, quêtes, choix.", "illustration": "cartes/bouclier.svg", "mots_voix": ["rpg", "jeu de rôle"]}
      ],
      "recommande": "action_aventure",
      "recommande_depuis": "deductions",
      "libre": true,
      "micro": true,
      "passer": true,
      "si": null
    },
    {
      "id": "multijoueur.joueurs",
      "chapitre": "technique",
      "type": "choix",
      "titre": "Combien de joueurs ensemble ?",
      "choix": [{"id": "2-4", "libelle": "2 à 4"}, {"id": "2", "libelle": "2"}, {"id": "5-16", "libelle": "5 à 16"}],
      "recommande": "2-4",
      "si": {"multijoueur.mode": {"different_de": "solo"}}
    }
  ]
}
```

Types : `choix` (une carte), `multi` (plusieurs cartes, `max` facultatif), `texte` (champ libre long, ex. pitch), `nom` (champ court), `couleur` (nuancier + libre), `personnage` (éditeur visuel : morphologie, peau, cheveux, tenue, couleurs, accessoire, avec aperçu animé), `curseur` (valeur numérique, ex. plafond de crédits).

Conditions `si` : `{"<clé>": {"egal": v}}`, `{"different_de": v}`, `{"dans": [..]}`, `{"existe": true}` ; plusieurs clés = toutes vraies ; une clé sans réponse rend `egal` et `dans` faux, `different_de` vrai. Les règles R qui demandent un vrai raisonnement (R5 moteur, R8 ambition, R14 systèmes du genre) ne sont **pas** codées dans la page : c'est toi qui les appliques dans `deductions.json`.

Champs d'une question : `id`, `chapitre`, `type`, `rapide` (facultatif), `seulement_rapide` (posée seulement en mode rapide), `titre`, `aide` (la ligne de contexte que dit l'assistant), `choix`, `recommande` (la ★ : un `id`, une liste d'`id` pour `multi`, ou `null` quand seule `deductions.json` peut la donner), `recommande_depuis: "deductions"` (la ★ est recalculée par toi), `max` (multi), `propositions_depuis` (texte : la page affiche en suggestions `deductions.propositions[<id>]`), `defaut` (valeur par défaut d'un texte ou d'un curseur), `min` / `max` / `pas` (curseur), `cible` et `boutons` (personnage), `libre`, `micro`, `passer`, `si`.

Champs d'une carte : `id`, `libelle`, `detail` (une demi-ligne sous le libellé, facultatif), `illustration`, `mots_voix` (synonymes pour la dictée, en plus du libellé), `si` (facultatif : la carte n'est montrée que si la condition est vraie, ex. les langages selon le moteur).

Illustrations : `studio/cartes/<nom>.svg`, 160 × 120, style carnet (papier crème, trait d'encre, lavis, hachures, une seule couleur d'accent rouille), toutes tracées par `studio/outils/dessiner_cartes.py` (aucune image générée, aucune police : les chiffres sont des tracés) ; une même illustration peut servir à plusieurs cartes. Jamais de logo de marque (moteurs, plateformes : pictogramme neutre + nom en texte). Pour ajouter une carte : donne-lui un nom d'illustration dans `construire_questions.py`, ajoute le dessin dans `dessiner_cartes.py` (le script refuse d'écrire s'il en manque un), relance les deux scripts, puis contrôle avec `python -I -B studio/outils/planche_cartes.py <dossier>` (page HTML et PNG de toutes les cartes).

## Format des réponses : `<projet>/.studio/reponses_questionnaire.json`

Écrit par l'API locale à chaque réponse (fusion, écriture atomique). Toi, tu le lis ; en mode repli, tu l'écris au même format.

```json
{
  "version": 1,
  "etat": "en_cours",
  "mode": "rapide",
  "langue": "fr",
  "cree_le": "2026-11-12T16:30:00",
  "maj": "2026-11-12T16:42:00",
  "chapitre_courant": "monde",
  "chapitres_finis": ["vision", "gameplay"],
  "reponses": {
    "vision.pitch": {"valeur": "Survie en forêt après l'effondrement…", "source": "utilisateur", "via": "voix", "t": "2026-11-12T16:31:10"},
    "genre.principal": {"valeur": "survie", "source": "utilisateur", "via": "clic", "t": "…"},
    "moteur.nom": {"valeur": "godot", "source": "déduit", "raison": "R5 : 3D stylisée, petit projet", "t": "…"},
    "monde.taille": {"valeur": "petite_dense", "source": "a_confirmer", "via": "passer", "t": "…"},
    "monde.lieu": {"valeur": null, "texte_brut": "euh plutôt dans les Pyrénées je crois", "source": "voix_a_interpreter", "via": "voix", "t": "…"}
  }
}
```

- `source` : `utilisateur`, `deduit`, `a_confirmer`, `voix_a_interpreter`.
- `via` : `clic`, `ecrit`, `voix`, `passer`.
- Une dictée est d'abord comparée aux `libelle` et `mots_voix` des cartes ; si une seule carte correspond, elle est choisie (`via: voix`, la page la montre sélectionnée et laisse 3 s pour corriger) ; sinon `voix_a_interpreter` + `texte_brut`, et tu poses une question de suivi.
- `etat` passe à `termine` quand le maître valide le récapitulatif.
- Le chapitre Personnages écrit `profil.json` (pas ce fichier), via la même API.

## Tes fichiers vers la page

**`<projet>/.studio/deductions.json`** (après le pitch, puis à chaque fois que c'est utile) :

```json
{
  "maj": "2026-11-12T16:31:40",
  "recommandes": {"genre.principal": "survie", "camera.vue": "premiere_personne", "moteur.nom": "godot"},
  "fixes": {"moteur.nom": {"valeur": "godot", "raison": "projet Godot déjà présent"}},
  "propositions": {"vision.piliers": ["Tension de la survie", "Forêt vivante", "Débrouille"]},
  "message_assistant": "Survie en forêt, j'adore. J'ai préparé quelques idées, dis-moi si je me trompe."
}
```

**`<projet>/.studio/questions_suivi.json`** (questions de suivi que l'assistant pose dans la scène) :

```json
{
  "questions": [
    {"id": "suivi-001", "a_propos": "monde.lieu", "type": "choix", "titre": "Tu parlais des Pyrénées : on part sur une forêt de montagne inspirée des Pyrénées ?",
     "choix": [{"id": "oui", "libelle": "Oui, forêt de montagne"}, {"id": "fictif", "libelle": "Un lieu inventé du même style"}],
     "recommande": "oui", "libre": true, "micro": true, "cree_le": "…", "repondue": false}
  ]
}
```

La page insère la question de suivi juste après la question en cours ; la réponse est écrite dans `reponses_questionnaire.json` sous la clé `suivi-001` et la clé `a_propos` est mise à jour.

## Questions sur les clés

Clés : `<chapitre ou étape>.<question>` en minuscules sans accent (ex. `vision.pitch`, `vision.piliers`, `plateforme.cibles`, `ia.images`, `budget.generation_par_jalon`, `jalons.decoupage`).

## Format de `.studio/profil.json`

Copié tel quel dans le dossier du studio ; le studio le relit à chaque rafraîchissement.

```json
{
  "version": 1,
  "maitre": {
    "nom": "Alex",
    "titre": "Directeur du studio",
    "apparence": {
      "morphologie": "moyenne",
      "peau": "#c68642",
      "cheveux": {"coupe": "courts", "couleur": "#2b1d14"},
      "tenue": {"style": "sweat", "couleur1": "#3f7a52", "couleur2": "#e9c47f"},
      "accessoire": "casque_audio"
    },
    "langue": "fr"
  },
  "assistant": {
    "nom": "Bidule",
    "appellation": "assistant",
    "espece": "robot",
    "apparence": {
      "morphologie": "petite",
      "peau": "#9aa7b0",
      "cheveux": {"coupe": "aucune", "couleur": "#000000"},
      "tenue": {"style": "tablier", "couleur1": "#4d6f9c", "couleur2": "#f4ecd9"},
      "accessoire": "chapeau"
    },
    "personnalite": "espiegle",
    "humour": "leger",
    "tics": [],
    "langue": "fr",
    "frequence_rapport_min": 120,
    "rapport_fin_de_jalon": true,
    "analyse_continue": true,
    "vie_dans_le_studio": true,
    "voix_haute": "non"
  },
  "voix": {"micro_actif": true, "langue_reconnaissance": "fr-FR"}
}
```

Valeurs permises :
- `voix_haute` : `non`, `oui`, `cloche`.
- `voix.langue_reconnaissance` : code BCP 47 (`fr-FR`, `en-US`…), déduit de la langue du maître.
- `morphologie` : `mince`, `moyenne`, `costaude`, `petite`, `grande`.
- `peau`, `couleur`, `couleur1`, `couleur2` : `#rrggbb`.
- `cheveux.coupe` : `courts`, `longs`, `boucles`, `en_bataille`, `queue`, `rase`, `aucune`.
- `tenue.style` : `sweat`, `chemise`, `bleu_de_travail`, `heros`, `tablier`, `costume`, `armure`, `robe`.
- `accessoire` : `aucun`, `casque`, `casque_audio`, `casquette`, `beret`, `chapeau`, `lunettes`, `barbe`, `couronne`, `bandeau`, `capuche`, `cornes`.
- `espece` : `humain`, `robot`, `animal`, `creature` (+ précision libre dans `espece_detail`).
- `personnalite` : `espiegle`, `serieux`, `sarcastique`, `zen`, ou texte libre court.
- `humour` : `aucun`, `leger`, `absurde`, `geek`, `noir`.
- `frequence_rapport_min` : 15, 30, 60, 120.

## Récapitulatif (fin du questionnaire)

Dans la page : l'assistant présente le studio construit, puis un **parchemin** (ou tableau) par chapitre : réponse | source (✔ toi, ~ déduit, ? à confirmer) ; chaque ligne est cliquable pour corriger. Les deux personnages posent côte à côte. Puis la question finale ; « Oui » passe `etat` à `termine`. (En repli conversation : même tableau, puis :)

| Question | Choix |
|---|---|
| On écrit le projet ? | ★ Oui, écris tout · Je corrige une réponse · Je passe en mode complet pour les « à confirmer » |

« Oui » (ou la validation en repli conversation) déclenche **toujours** l'étape suivante : la roadmap générée. Dans la page, l'écran « J'écris ta roadmap… » s'affiche aussitôt (sans bouton fermer), puis « Voici ta roadmap » dès que `roadmap.json` arrive.

## Roadmap générée (fin du questionnaire, étape non sautable)

Après la dernière réponse, tu écris **toujours**, avant tout autre livrable, `docs/ROADMAP.md` et `<projet>/.studio/roadmap.json`. Aucune réponse, aucun mode (rapide, jam, repli conversation) ne permet de sauter cette étape. Schéma de `roadmap.json` : `references/studio.md` ; exemple : `modeles/roadmap.json`.

**Jalons** (`jalons.decoupage`, `ambition.taille`) :
- `propose` : J0 Cadrage · J1 Prototype jouable · J2 Boucle centrale · J3 Contenu · J4 Finition · J5 Sortie (découpage détaillé : `livrables.md`).
- `court` ou `ambition.taille = prototype` : J0 · J1 Prototype · J2 Jeu jouable de bout en bout.
- `ambition.temps = jam` : jalons en heures (`game-jam`) : J0 cadrage (1 h) · J1 prototype · J2 contenu · J3 finition et envoi.
- `je_decris` : les jalons décrits par l'utilisateur, dans son ordre, complétés si besoin par J0.

**Tâches** (5 à 12 par jalon, ID `J<n>-<nn>`), tirées des réponses :

| Réponses | Tâches |
|---|---|
| `moteur.nom`, `moteur.versionnage`, `jalons.donnees_lourdes` | J1 : projet moteur et dépôt (LFS si choisi), dossier de données hors dépôt |
| `camera.*`, `plateforme.controles`, `gameplay.verbe` | J1 : contrôles, caméra, verbe principal jouable dans une scène grise |
| `gameplay.systemes`, `boucle.*`, `gameplay.echec` | J2 : un système par tâche (inventaire, combat, fabrication…), boucle de 30 s, boucle de session, sauvegarde si besoin |
| `genre.*` + skill de genre (R14) | J2 : systèmes typiques du genre |
| `monde.*`, `histoire.*`, `progression.*` | J3 : zones ou niveaux, contenus, histoire, progression |
| `da.*`, `ia.images`, `ia.modeles_3d`, `budget.*` | J3 : bible de style, images cibles validées, assets (dans le plafond de crédits) |
| `son.*`, `ia.son` | J3 ou J4 : ambiance, musique, bruitages |
| `interface.*`, `public.accessibilite`, `public.langues` | J4 : UI, options d'accessibilité, traductions |
| `plateforme.machine` | J4 : performances sur la machine cible |
| `multijoueur.*` | `multijoueur.quand = prototype` : J1 ; sinon J3 (réseau, synchronisation, tests à 2) |
| `plateforme.cibles`, `monetisation.*` | J5 : builds par plateforme, page de magasin, publication (avec accord) |

Toute réponse `a_confirmer` qui pèse sur une tâche donne une tâche « Confirmer : … » au début du jalon concerné.

**Estimations** : en heures de travail par tâche (`estimation_h`, de 0,5 à 16 ; au-delà, découpe la tâche). Dates de fin visées : heures cumulées ÷ heures par semaine (`ambition.temps` : `quelques_heures` = 5 h, `soirs` = 12 h, `plein` = 35 h, `jam` = durée de la jam), à partir d'aujourd'hui, jalon après jalon ; les agents en parallèle (`budget.claude`) peuvent réduire la durée, jamais l'estimation.

**Dépendances** : chaque tâche liste les tâches qu'elle attend (`depend_de`), chaque jalon le jalon précédent ; pas de boucle ; une tâche moteur dépend du projet moteur (J1-01).

**Critères de fin** : chaque tâche a un critère vérifiable par un test ou un lancement court ; chaque jalon a un critère de fin global (J1 : « on peut <verbe> pendant 1 minute sans bug bloquant »).

**Succès** : un par jalon (`succes` : titre court et joyeux dans le ton de l'assistant, description d'une ligne, icône = une carte `cartes/<nom>.svg` ou un caractère, son `petit` / `moyen` / `grand` : `grand` pour le prototype jouable et la sortie), plus un `succes_final` pour la roadmap entière. Écrits dans la langue du projet.

**État de départ** : J0-01 (questionnaire et documents) `verse` ; le reste `a_faire`. Le studio gagne `xp_par_tache` par tâche versée et `xp_par_jalon` par jalon terminé.

