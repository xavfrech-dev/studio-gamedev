# studio/ : le studio virtuel animé

Version **générique et paramétrable** du studio : tout vient de `<projet>/.studio/` (config, profil, roadmap, progression). Lancer : `python -I -B serveur_studio.py --projet <dossier du jeu>`, puis ouvrir `http://127.0.0.1:<port>/studio.html`.

| Fichier | Rôle |
|---|---|
| `studio.html` | La page isométrique (**prête**). Mode **accueil** : l'assistant fait créer le jeu question par question (cartes illustrées, ★ mise en avant, champ libre, micro, récapitulatif corrigeable), le studio se construit à chaque chapitre, puis « Voici ta roadmap ». Mode **travail** : postes et personnages, barres de progression avec temps restant, cloche des décisions, notifications, bandeau des succès en file, niveau, demandes à l'assistant ou à un poste (écrit ou voix) |
| `questions.fr.json`, `questions.en.json` | Le questionnaire en données (**prêt** : 96 questions, 23 en mode rapide, 377 cartes) |
| `cartes/` | Illustrations des cartes (**prêtes** : 264 SVG style carnet, tracés par code) |
| `outils/construire_questions.py` | Source unique des questions (FR et EN côte à côte) ; écrit les deux JSON |
| `outils/dessiner_cartes.py` | Trace toutes les illustrations des cartes (aucune image générée, aucune police, aucun logo) |
| `outils/planche_cartes.py` | Planche de contrôle (HTML + PNG via Edge ou Chrome sans tête) |
| `roadmap.js`, `roadmap.css` | Bouton et panneau **Roadmap** (**prêts**) : jalons, barres d'avancement, tâches cochées, succès gagnés ou verrouillés avec son, niveau du studio ; écran « Voici ta roadmap » à la fin du questionnaire |
| `roadmap.html` | Le panneau Roadmap seul (`?voici`, `?lang=en`), pour un aperçu |
| `paliers.js` | Le studio grandit avec le jeu : 5 paliers (garage → studio AAA) liés au niveau et à la roadmap, chantier animé, palette déduite des réponses |
| `conversations.js` | Les petites conversations du bureau, **fabriquées à partir de l'état réel** (tâches et %, étapes, versements, commits, décisions, jalons, embauches, compile, santé du PC, mur d'images, heure) : événements d'abord, bavardage ensuite, gabarits FR et EN, aucune phrase identique avant 30 min, aucun gabarit rejoué avant 20 min ; événements importants tout de suite, les autres en alternance avec l'ambiance ; données de `etat.json` citées seulement si elles ont moins d'une minute ; repli sur quelques phrases fixes sans aucune donnée. Compile lue sur une liste fermée de mots d'état (négations comprises) ; temps restant cité seulement s'il va avec le % ; un titre dont la langue (la sienne, sinon celle de l'ensemble du projet) n'est pas celle de la page n'est pas cité, un titre sans langue décidable (nom propre) l'est. Essais : `node studio/outils/essai_conversations.js` (compile, métier et outil, langue, gabarits FR = EN) ; dans la page, `window.__conversationsEssai()` (journal), `.stats()`, `.oublier()` (vide la mémoire « déjà dit », gardée dans le navigateur, avant une mesure répétée), `?babil=rapide` |
| `sprites.js`, `sprites/` | Personnages rendus dans Blender (WebP, 8 directions, recoloration par masques) ; `outils/sprites/` pour les régénérer |
| `serveur_studio.py` | Serveur local (**prêt**, 127.0.0.1, Host et Origin vérifiés) : sert `.studio/` puis ce dossier ; API : réponses au questionnaire, profil, demandes, décisions, réglages, **recrutement**, transcription locale facultative (501 sans faster-whisper) |
| `outils/essai_complet.py` | Essai de bout en bout (projet jetable, réponses fictives, roadmap conforme, versement d'un jalon, serveur sur le premier port libre, jamais 8790) |
| `outils/adoption.py` | Adoption d'un projet déjà commencé : analyse en lecture seule (`.studio/analyse_projet.json`), réponses déduites (`"mode": "adoption"`), ajout du bloc `.studio/` au `.gitignore` s'il manque, bloc délimité dans `CLAUDE.md` après accord, contrôle par empreintes qu'aucun fichier existant n'a changé |
| `outils/attendre.py` | Attente économe : rend la main à Claude seulement quand la page a écrit quelque chose ; `--point` dit si un point de suivi est utile |
| `studio_etat.py` | Alimentation (**prête**) : `etat.json` (10 s), `suggestions.json` et `taches_disponibles.json` (60 s), mur d'images `mur/` ; outil lourd configurable (Unreal, Godot, Unity…) ; git en lecture seule |
| `modeles/agent.md` | Gabarit de définition d'agent pour les postes recrutés |
| `sante_machine.py` | **Santé du PC**, vrai agent : tous les disques fixes (Windows, Linux, macOS), températures processeur et disques (Windows : activation en un clic, `outils/temperatures_windows.ps1` lancé avec élévation, Windows demande « Oui » une fois ; Linux : lecture directe ; sinon « non disponible »), **ménage proposé** quand un disque du projet passe sous 30 Go : caches du moteur, vieilles builds (2 gardées), worktrees fusionnés, temporaires, corbeille ; décision sous la cloche, rien n'est effacé sans « Faire ce ménage », journal `.studio/sante/menage_journal.json`. Essai : `outils/essai_sante.py` |

## Ce qui change par rapport à la première version

- Tous les chemins, le nom du projet, le moteur, les postes et les étapes viennent de `studio.config.json` (aucune valeur en dur).
- Le questionnaire se joue dans la page et ses réponses vont dans `.studio/reponses_questionnaire.json`.
- Repris du premier studio, en générique : alimentation automatique (`studio_etat.py`), recrutement (bouton, fiche rôle et mission avec dictée, définition d'agent dans le projet, demande, arrivée du personnage par la porte), mur d'images, rapport plein cadre de l'assistant (`rapport_assistant.json`, par la file unique), personnage assis quand il travaille et debout quand il est libre.
- Les deux personnages (le maître et l'assistant) viennent de `profil.json` : nom, morphologie, peau, cheveux, tenue, accessoire, personnalité, humour, langue, fréquence des rapports, voix.
- Micro partout (Web Speech API, repli sur l'écrit).
- Les définitions d'agents sont écrites dans le projet (`.claude/agents/`), pas dans le dossier global de l'utilisateur.

Contrat de fichiers, API et lancement : `../references/studio.md`.

---

# studio/: the animated virtual studio

The **generic, configurable** animated studio. Start it with `python -I -B serveur_studio.py --projet <game folder>` and open `http://127.0.0.1:<port>/studio.html`. It is an in-browser "game to create your game" (your assistant asks questions one by one, answer by clicking, typing or speaking, and the studio builds itself chapter by chapter), then the working studio where you watch your agents. See `../references/studio.md`.

Existing projects: `outils/adoption.py` analyses a game already in progress without changing it (`.studio/analyse_projet.json`), pre-fills what it can deduce (`"mode": "adoption"`), appends the `.studio/` block to `.gitignore` only when missing, adds a delimited block to `CLAUDE.md` only with consent, and checks by fingerprints that no existing file changed (`essai_complet.py adoption`).

Ready: the studio page and its local server (`studio.html`, `serveur_studio.py`, end-to-end test `outils/essai_complet.py`), the feeder `studio_etat.py` (desk states, alerts, ready tasks, image wall), hiring, the image wall and the assistant's full-screen report, the Roadmap panel (`roadmap.js`, `roadmap.css`, `roadmap.html`: milestones, progress bars, ticked tasks, locked or earned achievements with sound, studio level; reads `roadmap.json`, written by the skill at the end of the questionnaire), `questions.fr.json` / `questions.en.json` (96 questions, 377 cards) and `cartes/` (264 hand-coded SVG card illustrations, regenerated by `outils/dessiner_cartes.py`; contact sheet with `outils/planche_cartes.py`).
