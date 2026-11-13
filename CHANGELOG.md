# Changelog

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ; versions : [SemVer](https://semver.org/lang/fr/).

## [0.3.5] - 2026-11-13

### Ajouté
- Santé du PC (réglage `sante_auto`, coupé par défaut) : processeur, mémoire, disque et carte graphique (psutil s'il est installé, sinon un repli léger sous Windows, Linux et macOS), jauge dans le groupe ; quand la machine sature (processeur > 92 % au moins 8 des 10 dernières minutes, mémoire > 90 %, disque < 30 Go), il le signale, propose des pauses et retarde les attributions automatiques, la tyrannie et les embauches. Il ne tue aucun processus et ne touche ni au système, ni au moteur, ni au jeu.
- Fiche d'un personnage : « Nom et rôles » (nom affiché, métiers à cocher, rôle libre), route `POST /api/agent` (fiche de recrue et définition d'agent mises à jour proprement ; postes de la config : `reglages.json`). La tyrannie compte ces métiers pour le travail disponible.
- Point d'équipe : le point régulier de l'assistant (tableau chantier / étape / % / reste, heure de fin, ce qui a fini, rapport dans le studio, lecture des réponses, lancement des demandes en attente, fréquence réglable), décrit dans `references/point_equipe.md`, commande `/point-equipe`. Coupé par défaut ; « Tout couper » l'arrête, le mode nuit l'empile ; petite blague bon enfant désactivable (`blague`).

## [0.3.4] - 2026-11-13

### Ajouté
- Tyrannie (réglage `tyrannie_auto`, coupé par défaut) : l'assistant devient contremaître. Il va voir les personnages inactifs avec une remontrance courte et drôle, l'attribution de fin de tâche passe à 30 s (6 par heure au plus, revérifié par le serveur), il dépose une demande listant les inactifs, embauche quand un métier manque et renvoie lui-même une recrue à 100 % sans travail de son métier depuis 30 min (le serveur refuse si une tâche est en cours), avec « Réintégrer » pendant 10 min. Sa barre dans le groupe = taux d'occupation de l'équipe. « Tout couper » la met en pause.
- Bouton « chat » à côté du gros micro : petite fenêtre de saisie (Entrée = envoyer, Maj+Entrée = retour à la ligne, Échap = fermer), destinataire au choix, « envoyé » et message dans la conversation.
- Ordre du groupe à gauche : glisser-déposer à la souris et au doigt, flèches haut et bas, enregistré dans `reglages.json` (`ordre_equipe`, d'un appareil à l'autre), nouveaux à la fin, bouton « ordre par défaut ».
- Mode nuit / absent : plus aucune notification (sons d'événements, toasts, rapport plein écran, notifications du système), le studio continue de vivre et note tout ; `mode_absent` dans `reglages.json` ; lune discrète ; au retour, rapport « Pendant ton absence » (durée, ce qui a fini, équipe, décisions qui attendent, problèmes), une fois, et gardé au journal.

## [0.3.3] - 2026-11-13

### Ajouté
- Gros micro en bas de l'écran, comme le studio d'origine : clic (ou barre d'espace maintenue) pour parler, carte « J'écoute… » puis texte modifiable, destinataire (l'assistant ou un poste) et « Envoyer » ; mode « appui » ou « maintien » dans Réglages.
- Bulle d'infos au survol d'un personnage : rôle, état, tâche en cours, pourcentage, temps restant, « clic : sa fiche ».
- Fraîcheur des données dans la barre du haut (« à jour · HH:MM » ou « figé depuis … »).
- Réglages : ambiance du bureau (coupée, douce, vivante), babillage des bulles (petits sons), étiquettes des personnages (toujours, au survol, jamais), taille du texte, animations, notifications du système quand l'onglet est caché.

### Corrigé
- Dictée : message clair quand le navigateur bloque le micro (cadenas, adresse du studio) ; si la transcription locale (Whisper) est absente, la dictée repasse par la reconnaissance vocale du navigateur, avec un message clair si aucune des deux n'est disponible.

## [0.3.2] - 2026-11-13

### Ajouté
- Zoom et déplacement de la caméra, avec les réglages du studio d'origine : molette (zoom de 0,9 à 4 autour du curseur), pincement à deux doigts, cliquer-glisser pour se déplacer, bornes (la pièce reste visible), double-clic pour zoomer, boutons +, − et « recentrer », recentrage sur un personnage quand on le clique. Une seule transformation de vue pour le décor, les personnages, les bulles et les étiquettes ; planches de personnages en 256 px dès qu'on zoome (pas de flou) ; canevas vidé en entier avant la transformation (pas de bords au dézoom).

### Corrigé
- Une règle CSS mal fermée (0.3.1) cachait les styles qui la suivaient : le bandeau du groupe, les boutons de zoom et plusieurs blocs s'affichaient sans leur mise en forme.

## [0.3.1] - 2026-11-13

### Ajouté
- Même studio que l'original, adapté à chaque projet : barre du haut complète (Conversation, Vue d'ensemble, Images, Journal, Roadmap, Décisions, Appeler l'assistant, Optimiser, Journal de l'assistant, Personnaliser, Recruter, Notifications, Réglages, Plein écran, Tout couper), boutons « papier » aux couleurs du jeu, date et heure, barre « Version 1 » (avancement pondéré de la roadmap).
- Bandeau du groupe à gauche : portrait, état (▶ ⏸ ↔ ☕ « ? ») et tâche sur deux lignes, barre de progression, temps restant, clic = fiche ; l'assistant y figure aussi pendant le questionnaire.
- « Optimiser » : demande d'optimisation (une seule en attente) et rapport avec cases à cocher, envoyées en un seul lot.
- Radio du studio : les musiques du jeu de l'utilisateur (`sources_musique`, sinon dossiers `music`/`musique` du projet), lecture continue mélangée, fondu enchaîné à puissance égale, sourdine pendant la cloche ; coupée par défaut, rien s'il n'y a pas de musique.
- Sons de vie (ambiance de clavier, porte, gobelet), petites conversations entre personnages libres, touche V (dicter dans le dernier champ), message sans réponse depuis 10 min mis en évidence.
- Réglages : volume, durée des notifications, ambiance, conversations, radio et volume, légende des états, plein écran, revoir le tutoriel ; nouveaux automatismes `enchainement_auto`, `point_auto`, `optimisation_auto`.
- Tutoriel de départ : 6 bulles de l'assistant, puis choix des automatismes avec une estimation des jetons par heure (« Tout activer », « Activer ceux que je choisis », « Plus tard ») ; rien ne s'active sans choix. Bouton « Tout couper », rouge quand un automatisme tourne.
- Tout arrive dans le studio : crochet Stop facultatif (`studio/outils/crochet_journal.py`, installé seulement avec accord par `installer_crochet.py`, fusion dans `.claude/settings.local.json`, `--retirer`) qui recopie chaque réponse dans `.studio/journal_assistant.json` ; champ « Répondre » (micro, touche V) sous chaque réponse, sous le rapport et sous l'optimisation (`en_reponse_a`) ; règles permanentes « miroir des questions » dans SKILL.md ; autorisations d'actions sensibles expliquées dans le README.

## [0.3.0] - 2026-11-12

### Ajouté
- Le studio embellit avec le jeu : cinq paliers (garage, petit bureau, studio, studio pro, studio AAA) liés au niveau du studio et à l'avancement de la roadmap (`studio/paliers.js`) ; chaque palier change sol, murs, éclairage, mobilier et effets ; montée de palier jouée en chantier animé ; `?palier=N` ou `palier` dans `studio.config.json` pour le fixer.
- Palette et ambiance du bureau déduites des réponses (palette, genre, émotion, cadre du monde) ; jamais d'asset du jeu.
- Personnages rendus en 3D (`studio/sprites/` : 8 directions, 10 animations, recoloration par masques, couvre-chefs ; `studio/sprites.js`), avec repli vectoriel tant qu'ils chargent ; outils de rendu et d'assemblage dans `studio/outils/sprites/`.
- README : section « Ton studio grandit avec ton jeu » avec captures (palier 1 et palier 5).

## [0.2.0] - 2026-11-12

### Ajouté
- Bulles de décision dans la scène (champ `poste` d'une décision, sinon au-dessus de l'assistant avec compteur) ; décision ouverte en grand (choix, champ libre, micro).
- Vue « Conversation avec l'assistant » : messages avec statut (déposé, lu, traité), réponses, décisions avec boutons ; bulle « L'assistant te pose une question » si une réponse finit par une question sans décision. `studio_etat.py` met les messages dans `etat.json`.
- Fin de tâche : le personnage attend près de l'assistant ; « Lui confier une tâche », « Trouve-toi une tâche », « Laisser en pause » ; route `POST /api/confier`. Réglage `attribution_auto` (coupé par défaut ; 1 en attente par personnage, 4 par heure, vérifié par le serveur).
- Renvoi et réembauche des recrues (`POST /api/renvoyer`, confirmation, rien n'est effacé : `recrues/_anciens/`, `.studio/anciens/agents/`) ; renvois proposés sous la cloche (`decisions_studio.json`), jamais appliqués seuls.
- Embauche automatique quand un métier manque (`embauche_auto`, coupé par défaut ; 1 par heure, 12 bureaux, jamais un ancien renvoyé, recrue jamais lancée d'office).
- `studio/veille_studio.py` : relance l'alimentation si elle s'arrête ou se fige (`studio_etat.py --duree-h 0` = sans limite).

### Corrigé
- Demandes au nom unique, jamais écrasées ; anti-doublon 60 s.
- Bandeau rouge si `etat.json` a plus de 60 s ; fichier illisible ignoré et signalé ; `reponses.json` illisible jamais réécrit.
- Une seule optimisation en attente, 30 min entre deux (serveur).
- Rapport marqué « vu » seulement quand l'onglet est visible ; redessin seulement si l'état change ; tâches sorties, écartées ou retirées filtrées.

## [0.1.1] - 2026-11-12

- Mode « projet déjà commencé » : analyse en lecture seule, questionnaire raccourci, roadmap à partir de l'existant, aucun fichier écrasé.

## [0.1.0] - 2026-11-12

Première version publique.

### Ajouté
- Skill `studio-gamedev` : lancement d'un projet de jeu en 6 phases (accueil, questionnaire, documents, routage des tâches, studio de travail, suivi).
- Studio local (`studio.html`, `serveur_studio.py`, 127.0.0.1 seulement) : questionnaire joué dans la page (96 questions, mode rapide de 23, FR et EN, 264 illustrations SVG tracées par code), bureau isométrique, cloche des décisions, roadmap avec succès et niveau, rapport plein cadre de l'assistant.
- Alimentation du bureau (`studio_etat.py`) : état des postes, alertes, tâches prêtes, mur d'images limité au projet.
- Recrutement d'agents depuis la page (définitions écrites dans `<projet>/.claude/agents/`, outils limités, modèle réglable).
- Économie de jetons : `attendre.py` (attente sans jetons), bloc `economie` de la config (2 agents au plus, modèle `sonnet`, point toutes les 2 h au plus, pas d'enchaînement sans accord).
- Adoption d'un projet déjà commencé (« adopte mon projet ») : analyse en lecture seule (`adoption.py`), résumé en 5 lignes à confirmer, questionnaire raccourci aux réponses non déduites, roadmap à partir de l'existant (J0 « Ce qui existe déjà » avec preuves, estimations calées sur le rythme observé), postes tirés des besoins réels.
- Commande `/studio-gamedev:studio`.
- Voix : reconnaissance du navigateur, repli local facultatif avec `faster-whisper` et `ffmpeg`.

### Sécurité et confidentialité
- Adoption : aucun fichier existant n'est écrasé (documents écrits à côté en `*.studio.md` ou bloc délimité après accord, `CLAUDE.md` et `.gitignore` seulement complétés, code, scènes, assets et agents existants intacts), contrôle final par empreintes (`adoption.py verifier`).
- `.studio/` ajouté au `.gitignore` du projet dès la phase 1 (seuls `roadmap.json` et `studio.config.json` peuvent être versionnés).
- Le serveur vérifie Host et Origin, n'exécute aucune commande reçue de la page et n'écrase jamais un agent qu'il n'a pas créé.
