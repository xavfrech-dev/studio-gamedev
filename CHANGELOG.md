# Changelog

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ; versions : [SemVer](https://semver.org/lang/fr/).

## [0.4.16] - 2026-11-13

### Corrigé
- Projet en anglais (F24) : changer le rôle d'une recrue réécrit aussi la section « Your role » / « Ton rôle » de sa définition d'agent ; le titre des métiers suit la langue du projet (« Trades » / « Métiers »).
- Projet en anglais (F25) : les refus du serveur (tâche en cours, réglage coupé, poste de base, nom, plafonds…) et les alertes de santé du PC sont en anglais.
- Projet en anglais (F26) : l'éditeur de personnage traduit ses libellés et ses options (« Build », « headphones »…) ; les valeurs enregistrées ne changent pas.

## [0.4.15] - 2026-11-13

### Modifié
- Roadmap (P11) : un seul chiffre en tête, « X % de la version 1 · ≈ N j restants » (le même que « Version 1 », pondéré par les durées, expliqué au survol) ; tâches, jalons, niveau et XP repliés sous « Détails » ; durées avec la virgule en français (« 5,5 j »).
- Décisions (P13) : fenêtre étroite ; on voit qui demande et ce qui l'attend ; choix en cartes numérotées, touches 1 à 9 au clavier ; la ★ dit « la réponse recommandée par l'assistant ».
- Accessibilité (P18) : la scène est dans un `<main>`, le groupe est une liste ; chaque membre est lu en mots (« au travail », « en attente »…), les pictogrammes sont cachés aux lecteurs d'écran.
- Couleurs d'état (P19) : un jeton par état (`--etat-travaille`, `--etat-attend`…) partagé par le groupe et la scène.

## [0.4.14] - 2026-11-13

### Modifié
- Grand écran (P9) : à partir de 1800 × 950, puis 2200 × 1200 (1440p) et 3000 × 1600, l'interface grandit avec l'écran (en-tête, groupe, panneaux, questionnaire, notifications, micro, zoom : × 1,15, × 1,32, × 1,6) ; la scène reste nette (elle se redessine à la taille de la fenêtre). Le questionnaire s'élargit jusqu'à 1 200 px.

## [0.4.13] - 2026-11-13

### Ajouté
- Thème clair et sombre (P4) : l'interface suit le thème du système, ou le réglage « Thème : comme le système / clair / sombre » (Réglages, Affichage). En clair : fond papier, en-tête, groupe, notifications, onglets du téléphone et boutons de zoom clairs ; la scène garde son décor. La couleur de la barre du navigateur (`theme-color`) suit.

### Modifié
- « Mode nuit » s'appelle « Je m'absente » : ce n'est pas un thème sombre mais le mode absent (plus de notifications, résumé au retour).

## [0.4.12] - 2026-11-13

### Ajouté
- « Aujourd'hui » : l'état du studio en une carte (ce qui a avancé aujourd'hui, ce qui attend avec « Décider » et les agents bloqués, la prochaine étape, le % de la version 1). Premier onglet au téléphone, bouton au PC ; la carte se met à jour seule.
- Décisions d'un balayage au téléphone : pour une question à deux réponses, balayer à droite choisit la réponse recommandée (★), à gauche l'autre ; la réponse part au bout de 5 s, « Annuler » la rouvre.
- « Résumé du matin » : à la première ouverture après plus de 4 h sans studio ouvert, une feuille dit ce qui a été versé, les réponses de l'assistant, les décisions qui attendent et les problèmes, avec « Tout est vu ».

## [0.4.11] - 2026-11-13

### Modifié
- Questionnaire au téléphone (T11) : la scène des questions prend l'écran (la pièce reste en bandeau au-dessus), une barre « Vision · 1/9 » remplace les pastilles des chapitres, seuls les Réglages restent dans les onglets ; le bandeau des succès passe sous la zone sûre du haut.
- Questionnaire au PC (P16) : pendant le premier questionnaire, la barre d'outils se réduit à Son, Plein écran et Réglages ; la fenêtre des questions monte à 70 % de la hauteur ; « Direction artistique » devient « Style » dans les chapitres.
- Bouton Dicter (T15) : même icône que le gros micro (20 px), icône seule dans un rond de 44 px au téléphone, anneau qui pulse pendant l'écoute (sauf mouvement réduit).

## [0.4.10] - 2026-11-13

### Corrigé
- Radio : un lien cassé dans le dossier de musiques ne coupe plus toute la radio ; deux fichiers de même nom ne s'écrasent plus.
- Les demandes vocales ne sont plus relues en entier toutes les minutes (les 200 plus récentes).
- Tutoriel : l'équipe est bien entourée à la première étape ; le tutoriel automatique attend qu'aucun panneau ne soit ouvert.

## [0.4.9] - 2026-11-13

### Ajouté
- Les suggestions de l'alimentation (disque plein, moteur ouvert deux fois, progression figée, roadmap en retard…) sont enfin montrées : notification pour les urgentes, liste dans la Vue d'ensemble avec « Confier à l'assistant ».
- Icône du plugin.

### Modifié
- Avec plusieurs onglets ouverts (PC et téléphone), un seul fait tourner les automatismes (le plus ancien encore ouvert, désigné par le serveur) ; les autres affichent seulement.
- Sortie des scripts en UTF-8 même redirigée (plus de « pr�t » sous Windows).
- macOS et Linux : noms de processus complets, dossier de configuration de Claude Code (`CLAUDE_CONFIG_DIR`) respecté, historique git lu seulement si le projet a son propre dépôt.
- README : vérifier Python, voix locale installée avec le bon Python, section « Sur ton téléphone », confidentialité précisée, historique renvoyé au CHANGELOG, français et anglais en miroir ; description du skill sous 1 024 caractères ; exemples sans noms internes.

## [0.4.8] - 2026-11-13

### Modifié
- Cloche au téléphone : toucher un choix suffit (petite vibration de confirmation) ; la réponse libre est repliée sous « Autre réponse… » ; sans décision, un écran « Rien à décider. L’équipe avance. ».
- Barre d'onglets : onglet actif annoncé (aria-current) et plus marqué, retour visuel au toucher, pastille plus lisible, nom de barre correct.
- Fermetures (×) de 44 px ; hauteur du fil calculée sur la hauteur visible réelle (dvh).
- Tutoriel au téléphone : « En bas, ton équipe… Touche un perso » ; la bulle du tutoriel disparaît quand on le ferme.

## [0.4.7] - 2026-11-13

### Modifié
- Barre d'outils du PC sur une ligne : actions et vues d'abord, icônes seules pour Notifications, Mode nuit et Son, puis un menu « ⋯ » (Vue d'ensemble, Journal de l'assistant, Optimiser, Personnaliser, Recruter, Réglages, Plein écran) ; Tout couper à part.
- Équipe sur une seule colonne qui défile (plus de deuxième colonne sur la scène en 720p), version compacte sous 800 px de haut ; notifications à gauche des boutons de zoom.
- Téléphone : texte à 16 px et texte secondaire à 14 px ; réglages en lignes tactiles avec interrupteurs et intertitres (Automatismes, Son et notifications, Affichage) ; roadmap en vrai plein écran, jalons collants.
- Le bouton Retour du téléphone ferme le panneau ouvert au lieu de quitter le studio ; tirer vers le bas ne recharge plus la page.

### Accessibilité
- Panneaux nommés par leur titre, focus placé à l'ouverture puis rendu à la fermeture, tabulation gardée dans le panneau ; roadmap en fenêtre nommée ; Son, Mode nuit et Tout couper annoncent leur état (aria-pressed).
- Raccourcis à une lettre (A, V, Espace) désactivables dans les réglages, ignorés quand le focus est sur un bouton ; « ? » ouvre la fiche des raccourcis.
- Textes atténués plus contrastés.

## [0.4.6] - 2026-11-13

### Modifié
- Sobriété au repos : une seule requête par cycle (`/api/instantane`, un ETag commun, réponse 304 si rien n'a changé) au lieu d'une par fichier, soit environ 12 requêtes par minute au lieu de 160.
- Rendu du bureau limité à 30 images/s, puis 10 quand personne n'a touché la page depuis 2 minutes, et 1 sans animations.
- « Réduire les animations » du système respecté pour toutes les animations ; la cloche et « Tout couper » ne clignotent plus sans fin.
- L'en-tête n'écrit dans la page que ce qui a changé (horloge, version, fraîcheur, mode nuit, bandeau).

## [0.4.5] - 2026-11-13

### Modifié
- Notifications : au-delà de deux à l'écran, une seule carte « N nouvelles notifications » qui ouvre la liste ; au téléphone, en haut de l'écran, une à la fois, masquées pendant la saisie.
- Téléphone : en-tête compact (nom du jeu, pourcentage, point d'état, bouton « ⋯ ») ; les outils du bureau passent dans une feuille d'actions ; plus de bouton de chat flottant (l'onglet Conversation suffit) ; boutons de zoom au-dessus de l'équipe ; équipe en défilement aimanté avec un dégradé.
- Conversation au téléphone : titre compact, aide clavier masquée, état vide avec trois suggestions.

## [0.4.4] - 2026-11-13

### Corrigé
- Fichier JSON illisible (questionnaire, personnages, réglages) : 3 nouvelles lectures, puis une copie `<nom>.corrompu-<date>.json`, rien n'est écrit (503) et la page affiche pourquoi ; l'index des recrues illisible est reconstruit depuis les fiches (aucune recrue perdue).
- Verrous : PID et heure de création du processus, écrits d'un coup et effacés à la sortie ; un PID repris par un autre programme après un redémarrage n'est plus jamais arrêté ni pris pour une veille en cours ; une alimentation figée est arrêtée avant d'en lancer une autre.
- Roadmap avec `"taches": null` : l'alimentation ne se fige plus ; les tâches écrites à la main ne sont plus effacées ; une alerte « fichier illisible » disparaît avec le fichier ; « 23:50 » lu après minuit = en retard.
- Tyrannie : une tâche refusée par le serveur reste proposable.
- Rallumer un automatisme dans les Réglages pendant « Tout couper » rend aussi les autres comme avant.
- Relance après un arrêt brutal : même port qu'avant s'il est libre ; embauche à la main au-delà de 12 bureaux refusée ; `Content-Length` ou valeur du mauvais type : refus 400 (plus d'erreur interne).
- Page : serveur injoignable signalé (bandeau rouge, effacé au retour) ; double clic dans le questionnaire ; gros micro qui restait sur « J'écoute… » ; « Nom et rôles » garde le vrai modèle ; fiche de recrue relue tout de suite ; nom du jeu dans les panneaux.
- Conversation : une ligne géante du transcript ne bloque plus le fil ; pas de relecture depuis le début sans fichier connu.
- Dictée : seules les reprises de début de segment sont retirées ; « nous nous », « vous vous », les nombres, les fins de phrase et un segment vraiment redit sont gardés.

## [0.4.3] - 2026-11-13

### Corrigé
- Un fichier JSON illisible (réponses du questionnaire, personnages, réglages) n'est plus jamais écrasé : il est mis de côté (`<nom>.illisible-<date>.json`) avant d'en repartir, et signalé par `/api/qui`.
- Deux serveurs ne peuvent plus écouter le même port sous Windows : un `--port` déjà pris est refusé avec un message clair.
- Le rôle d'un agent qui contient « : » ne casse plus l'en-tête de sa définition.
- « Tout rallumer » rend la main à la config pour les automatismes qu'elle allume (au lieu de les laisser coupés) ; le bouton les compte aussi.
- Le crochet de journal est copié dans le projet (`.studio/outils/`) : une mise à jour du plugin ne le casse plus ; une réinstallation remplace une entrée périmée.
- Les copies mises de côté, sauvegardes, temporaires et le crochet copié ne sont jamais servis.

### Modifié
- Téléphone : bords sûrs (encoche, indicateur d'accueil) ; clavier ouvert, la barre d'onglets s'efface et la saisie reste visible ; conversation en colonne avec la saisie collée en bas et la touche « envoyer » ; téléphone couché : icônes sur une rangée et onglets en rail vertical.
- Bandeau « infos qui datent » : sous les boutons (il ne les cache plus), en ambre, sans jargon, avec « Relancer » (redémarre l'alimentation, `/api/relancer`) et une croix qui le masque 30 min.

## [0.4.2] - 2026-11-13

### Ajouté
- Application sur le téléphone : studio installable (manifeste au nom du projet, icônes, balises iOS, service worker qui ne met en cache que la coquille, en « réseau d'abord » : jamais les données ni l'API) ; sur téléphone ou depuis l'écran d'accueil, barre d'onglets en bas (Équipe, Conversation, Cloche, Roadmap, Réglages), panneaux plein écran, gros boutons. L'aide (Réglages) explique l'ajout à l'écran d'accueil en http sur le Wi-Fi (sans mode hors ligne).

### Corrigé
- Dictée qui répétait les débuts de phrase (« faut faut que faut que tu… ») : texte reconstruit à chaque événement, segments fusionnés, débuts répétés retirés, mode phrase sur téléphone, texte rendu une seule fois ; même nettoyage pour la transcription locale. Essais : `studio/outils/test_dictee.js`, `studio/dictee_propre.py`.

## [0.4.1] - 2026-11-13

### Ajouté
- Option `--reseau` du serveur (coupée par défaut) : le studio aussi sur l'IP locale, pour l'ouvrir depuis un téléphone sur le Wi-Fi de la maison. Toute requête qui ne vient pas de la machine elle-même doit porter une clé secrète (32 caractères, `.studio/cle_reseau.txt`, jamais servie), en `?cle=` puis en cookie ; Host et Origin vérifiés ; l'adresse à ouvrir est écrite dans `.studio/adresse_telephone.txt`. Aucun réglage du système n'est modifié.

## [0.4.0] - 2026-11-13

### Ajouté
- Vitrine : README français et anglais avec un GIF du studio animé et des captures (jour, nuit, questionnaire, tutoriel, téléphone) prises sur des projets d'essai, dans `docs/images/`.
- Suggestions de l'alimentation (alertes de la page) dans la langue du projet.

### Modifié
- Téléphone : la barre « Version 1 » tient dans l'écran ; `?apercu` coupe aussi les notifications (captures propres).

## [0.3.12] - 2026-11-13

### Ajouté
- Conversation à droite : la même conversation que dans Claude Code, lue en local et en lecture seule dans le transcript de la session (`GET /api/conversation`, seulement la fin du fichier) ; texte de l'utilisateur et de l'assistant seulement, en markdown, relu toutes les 2,5 s, défilement en bas sauf si on remonte ; les questions avec leurs boutons puis « réglé : … » ; saisie en bas (Entrée envoie, Maj+Entrée retour à la ligne) avec le micro.
- Tyrannie : diagnostic de chaque agent bloqué (ta décision, moteur et place dans la file, outil lourd, autre agent, fichier, machine saturée, erreur du journal, silence), bulle « X est bloqué : raison → action », demande à l'assistant avec le diagnostic (seulement si la liste change, au plus toutes les 15 min), question bloquante remontée en tête de la cloche et du fil.
- Rôle temporaire : un agent qui attend (moteur, décision, autre agent, fichier, outil) reçoit une autre tâche sans moteur (`origine: auto:temporaire`, mêmes plafonds) ; sa tâche d'origine reste réservée ; affiché dans sa fiche.
- Aperçus : `?heure=14` (jour, nuit…) et `?apercu` (sans tutoriel) pour les captures.

### Corrigé
- Un agent à 100 % ou avec des nouvelles depuis moins de 20 min n'est jamais « bloqué ».
- Points : un seul rapport en plein cadre à la fois ; un nouveau point à moins de 15 min du précédent va au journal, sans cloche.

## [0.3.11] - 2026-11-13

### Ajouté
- Temps réel : entre deux écritures de l'agent, la barre avance d'elle-même (du % écrit vers 100 à la fin prévue, jamais au-delà de 99 % avant que l'agent écrive 100 ; un nouveau % plus bas la fait redescendre doucement). `etat.json` donne `progression_t` (dernière nouvelle de l'agent, affichée) et `fin_t`. La fiche ouverte, le groupe et la vue d'ensemble se mettent à jour toutes les 5 s, dans chaque onglet.
- « À décider » des rapports calculé en direct depuis les décisions : les ouvertes avec « Décider », celles réglées entretemps barrées « réglé » (vieux rapports compris). Une décision que l'assistant ferme (`statut: repondue`, réponse donnée dans le chat) quitte aussi la cloche.
- « Tout rallumer » : après « Tout couper », le même bouton remet les automatismes comme avant (`/api/couper`).
- Persos libres qui s'amusent : café, fenêtre, chat du garage, machine à café, îlot, télé, borne d'arcade selon le palier (un coin toutes les 90 s, ils y marchent).
- Projet en anglais : `modeles/en/profil.json` et `studio.config.json` (règles des agents, titre, reconnaissance vocale en anglais) ; lignes des postes, « Version 1 », infobulles et accessoires du recrutement en anglais.

### Corrigé
- L'en-tête de `SKILL.md` n'était pas du YAML valide : le skill se chargeait sans sa description (trouvé par un essai d'installation propre). Le contrôle avant publication le vérifie désormais.
- Tyrannie : un perso qui attend seulement la suite de la roadmap, sans demande ni progression depuis 10 min, compte comme inactif ; la tyrannie et l'embauche tournent aussi quand l'onglet est caché.
- La définition d'agent n'écrit plus de chemin de la machine (`.studio/progression/…` relatif).
- Pastille du bouton Roadmap = même chiffre pondéré que « Version 1 ».
- Résumé d'adoption : pluriels (« 1 scène », « 1 commit »).

## [0.3.10] - 2026-11-13

### Modifié
- Téléphone (≤ 640 px) : barre d'outils sur une ligne qui défile, icônes seules (le nom de chaque bouton reste lu par les lecteurs d'écran) ; la pièce se centre dans la hauteur laissée par l'équipe.
- Mur d'images : le parcours borné reprend au passage suivant là où il s'est arrêté ; les images déjà trouvées et les dossiers qui en donnent sont relus d'abord (les images récentes d'un très gros dossier ne manquent plus).

## [0.3.9] - 2026-11-13

### Ajouté
- Anglais complet : gabarits `modeles/en/` (GDD, ROADMAP, DECISIONS, CLAUDE, agent) ; un projet non français reçoit des agents en anglais ; langue du projet = celle du premier message ; la page prend la langue du navigateur par défaut ; résumé anglais en tête de SKILL.md et des références.
- « Arrête le studio » : `studio/outils/arreter.py` arrête la veille, l'alimentation et le serveur du projet (seulement eux). Le serveur note son port dans `.studio/serveur.json` et répond sur `GET /api/qui` ; relancé, il réutilise celui qui tourne déjà pour ce projet.
- Questionnaire posé dans le chat : la page ouverte relit les réponses toutes les 5 s et avance seule.
- « J'écris ta roadmap… » bloqué plus de 5 min : explication (rouvrir la session et dire « reprends mon studio ») et bouton de rappel pour l'assistant.
- Micro refusé : bouton « Ouvrir dans mon navigateur » (adresse copiée en secours).

### Modifié
- Notifications plus grandes (560 px, texte 18 px, pictogramme).
- Moins de téléchargements : ETag et réponses 304, une seule vague de lectures à la fois (8 s au plus), onglet caché lu une fois par minute.
- Mur d'images borné : 2 000 chemins et 2 s au plus par passage, dossiers de cache (Intermediate, DerivedDataCache, Library, .godot/imported…) ignorés.
- Heure de fin acceptée sous plus de formes (« dans 20 min », « 14h30 », « 14 h ») ; git lancé sans fsmonitor ; écritures réessayées sous Windows (sinon « fichier occupé »).

### Corrigé
- Transcription locale : elle suit la langue du projet ; une seule à la fois ; ffmpeg limité au flux reçu.

## [0.3.8] - 2026-11-13

### Ajouté
- Backlog du studio : `.studio/backlog_studio.json` liste les tâches propres au studio lui-même (pas au jeu). Les entrées « a_corriger » rejoignent `taches_disponibles.json` (`origine: "backlog"`, métier « studio ») ; la fin de tâche et la tyrannie les proposent seulement aux personnages qui ont le métier « Studio » (fiche « Nom et rôles »), jamais hors métier.
- Roadmap en retard : une suggestion quand un commit récent cite une tâche encore « à faire » ou « en cours », ou quand `docs/ROADMAP.md` a changé sans `roadmap.json`.
- Routage : table des 18 genres du questionnaire vers le skill de genre ou, sans skill de genre, les disciplines à appeler ; ligne pour un moteur « maison ».

### Modifié
- Gabarit d'agent : règle « Roadmap » (mettre à jour `docs/ROADMAP.md` et `.studio/roadmap.json` à chaque versement, citer l'id dans le commit) ; progression avec `tache`, `restant_min` et `fin`.
- Documentation : mur d'images, bandeau d'événements, ligne de tâche et personnages libres décrits dans `references/studio.md`.

## [0.3.7] - 2026-11-13

### Ajouté
- Fiche « Nom et rôles » : choix du modèle d'IA de l'agent (Rapide = Haiku, Équilibré = Sonnet, Le plus fort = Opus, Comme la session). Recrue : champ `modele` de sa fiche et ligne `model:` de sa définition d'agent (ajoutée si elle manque) ; poste de la config : `modeles_postes` dans `reglages.json`, relu quand l'assistant lance l'agent. Le modèle s'affiche dans la bulle d'infos ; il vaut pour le prochain lancement, pas pour une tâche en cours.

## [0.3.6] - 2026-11-13

### Corrigé
- Tyrannie : elle ne relance plus un personnage pour qui il ne reste aucune tâche faisable (métier, préparation sans moteur, hors métier sans moteur, déjà confiées exclues). Quand tout le travail restant attend le moteur, elle affiche « file moteur » et laisse les personnages souffler, sans déposer de demande.

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
