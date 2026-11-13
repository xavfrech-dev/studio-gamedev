# Le studio virtuel animé

> **English summary.** The animated studio: files, `studio.config.json` settings, install, local API, file contract (`etat.json`, `roadmap.json`, studio backlog…), studio tiers, voice and stopping.

Une page web locale, en vue isométrique. Elle a deux modes :
- **accueil** : dès le lancement du skill, « le jeu commence ». L'assistant accueille le maître et lui fait créer son jeu question par question (cartes illustrées, ★ mise en avant, champ libre, micro). Le studio se construit à chaque chapitre terminé (voir `questionnaire.md`, « Chapitres »).
- **travail** : chaque poste est un personnage à son bureau, avec une barre de progression façon barre de vie. Le maître est à son bureau de direction ; l'assistant circule, fait ses rapports et sonne la cloche quand une décision attend. On y trouve aussi le mur des dernières images et le bouton de recrutement.

**Partout, on peut parler ou écrire** : bouton micro sur chaque question, bouton « Appeler l'assistant » (demande vocale ou écrite), et sur la fiche de chaque agent « Lui demander… ».

Fonctionne avec **Python 3.10+ (bibliothèque standard seulement)** et un navigateur récent. Aucun service en ligne à part, si le maître l'active, la reconnaissance vocale du navigateur (voir « Voix »).

## Fichiers (dans `studio/` du skill)

| Fichier | Rôle |
|---|---|
| `studio.html` | La page (aucune dépendance externe) : bureau isométrique (12 bureaux, barres de progression avec temps restant, ligne « pictogramme + tâche » sous chaque barre, personnage **assis** quand il travaille et **debout, tasse à la main** quand il est libre, décor construit chapitre par chapitre, l'assistant qui circule), notifications, bandeau des succès en file, niveau, scène du questionnaire (cartes, champ libre, micro, récapitulatif), éditeur de personnage, décisions, « Appeler l'assistant », fiche de poste avec « Lui demander… », bouton **Recruter**, **mur d'images** (3 cadres au mur + bouton « Images »), **rapport plein cadre** de l'assistant |
| `questions.fr.json`, `questions.en.json` | Le questionnaire en données (format dans `questionnaire.md`) ; leur bloc `roadmap` donne les textes du panneau Roadmap |
| `roadmap.js`, `roadmap.css` | Bouton et panneau **Roadmap** (jalons, barres d'avancement, tâches cochées, succès gagnés ou verrouillés, niveau) ; écran « Voici ta roadmap » en fin de questionnaire |
| `roadmap.html` | Le panneau Roadmap seul (aperçu) ; `?voici` = écran de fin du questionnaire, `?lang=en` |
| `paliers.js` | **Le studio grandit** : 5 paliers (sol, murs, fenêtre et vue, mobilier, éclairage, effets), chantier animé au passage d'un palier, palette déduite des réponses ; tout tracé par code (voir « Paliers du studio ») |
| `sprites.js`, `sprites/` | **Personnages** rendus dans Blender : `atlas.json` + planches WebP (8 directions ; 128 px, et 256 px pour `tape`, `marche`, `repos`, `cafe_debout`), recoloration par masques (peau, cheveux, haut, bas, chaussures), couvre-chefs ; repli vectoriel tant qu'ils chargent. Contrat : `sprites/LISEZMOI.md`. Licence MIT du skill |
| `outils/sprites/` | `perso_sprites.py` (Blender 4.5 : modèle, armature, animations, rendu), `assembler.py` (planches, atlas), `compresser.py` (WebP pour le dépôt) |
| `cartes/` | Illustrations des cartes (SVG, sans logos de marques) |
| `serveur_studio.py` | Sert la page et l'API JSON ci-dessous ; écoute **127.0.0.1 seulement** ; vérifie les en-têtes Host et Origin ; corps ≤ 64 Ko, champs bornés ; écrit seulement dans les fichiers listés ; **n'exécute aucune commande** ; JSON lus avec ou sans BOM ; transcription locale facultative |
| `studio_etat.py` | **Alimentation** : toutes les 10 s, lit `.studio/` (progression, recrues, demandes, statuts, attentes, roadmap), l'état git du projet (lecture seule), les processus (outil lourd ouvert ?), le disque ; écrit `etat.json`, `suggestions.json`, `taches_disponibles.json`, `decisions_studio.json` et copie les dernières images dans `mur/` ; aucune dépendance au moteur : tout vient de la config ; un fichier d'agent illisible est ignoré et signalé, le reste continue |
| `veille_studio.py` | **Veille** : lance `studio_etat.py` sans limite de durée et le relance s'il s'arrête (5 s, 30 s après 3 arrêts rapides) ou se fige (`etat.json` plus vieux que 3 min) ; une seule par projet (`veille_studio.verrou`), journal `veille_studio.log` ; ne double jamais une alimentation vivante |
| `outils/essai_complet.py` | Essai de bout en bout : projet jetable, `deductions.json`, réponses fictives, `roadmap.json` conforme et vérifié, versement d'un jalon, mode travail avec images d'essai, progression simulée, rapport, vérification d'une recrue ; `fonctions` (aussi lancé par `tout`) : serveur réel sur un port libre, bulles de décision, fil, fin de tâche, attribution et embauche automatiques et leurs garde-fous, renvoi / réembauche, renvoi proposé, fichier fautif, tâche sortie ; serveur (avec l'alimentation) sur le premier port libre (jamais 8790, le port du vrai studio) |
| `outils/attendre.py` | **Attente économe** : attend sans jetons qu'un fichier écrit par la page change (questionnaire, demandes, décisions), puis rend la main avec la liste des changements ; `--point` dit si un point de suivi est utile (code 3 : rien de neuf) |
| `modeles/agent.md` | Gabarit de définition d'agent pour un poste recruté (`tools:` limités, `model:` tiré de `economie.modele_agents`, marque « recrue du studio ») |

**Dossier du studio** : `<projet>/.studio/`. Le serveur sert d'abord ce dossier (config, profil, `roadmap.json`, progression, `mur/`…), puis les fichiers du skill posés à côté de lui : rien à copier. La page marche sans l'alimentation (elle calcule alors l'état des postes elle-même, mêmes règles) ; avec elle, `etat.json` fait foi tant qu'il a moins d'une minute.

## Paramètres : `studio.config.json`

Gabarit : `modeles/studio.config.json`.

| Champ | Sens | Défaut |
|---|---|---|
| `mode` | `accueil` (questionnaire) ou `travail` | `accueil` au premier lancement |
| `nom_projet` | Titre affiché | nom du dossier (remplacé par le nom du jeu dès qu'il est donné) |
| `langue` | Langue de la page et du fichier de questions | langue de l'utilisateur |
| `dossier_projet` | Racine du dépôt | — |
| `dossier_studio` | Où tournent la page et ses fichiers | `<projet>/.studio` (le serveur sert ce dossier, puis les fichiers du skill) |
| `theme` | Remplace, couleur par couleur, la palette déduite des réponses : `accent`, `accent2`, `sol`, `sol2`, `mur`, `bois`, `lumiere` (`#rrggbb`) | déduite du questionnaire (sinon tons bois et papier) |
| `palier` | Fixe le palier du décor (1 à 5) ; aussi `studio.html?palier=N`, ou `essaiPalier(N)` dans la console (rejoue le chantier) | automatique |
| `dossier_donnees` | Données lourdes hors dépôt (relatif au projet, sinon vide : un dossier hors du projet se passe à l'alimentation par `--donnees` et se note dans `CLAUDE.md`, jamais dans cette config versionnée) | réponse de l'étape 20 |
| `dossier_agents` | Définitions d'agents des postes | `<projet>/.claude/agents` |
| `dossier_session` | Journal de la session Claude Code à suivre | `auto` : `.jsonl` le plus récent sous `~/.claude/projects/<chemin du projet encodé>/` |
| `port` | Port local | 8790 ; s'il est pris, le premier libre après |
| `economie` | Réglages de dépense de jetons (voir SKILL.md, « Économie ») : `agents_max`, `modele_agents` (`haiku`, `sonnet`, `opus`, `inherit`), `point_min`, `point_si_changement`, `enchainer`, `pause_si_absent_min`, `optimisation_auto`, `attribution_auto`, `embauche_auto`, `attente_max_s` ; `reglages.json` (écrit par la page, « Réglages ») passe avant pour `attribution_auto` et `embauche_auto` | `{2, "sonnet", 120, true, false, 60, false, false, false, 1800}` : le plus sobre |
| `moteur.nom`, `moteur.processus[]`, `moteur.poste` | Le moteur et le poste qui tient la chaîne moteur | selon le moteur ; poste : le premier dont l'id contient « moteur » |
| `outils_lourds[]` | `{nom, processus[], poste}` : outils lourds surveillés (Unreal, Godot, Unity, Blender…) ; ouvert = le poste est **occupé** (assis) ; l'alerte d'inactivité porte sur eux | `[moteur]` |
| `seuils` | `{inactivite_min, disque_go}` pour les alertes | `{10, 20}` |
| `session_poste` | Poste « occupé » tant que la session Claude Code bouge (journal de moins de 3 min) | `direction` s'il existe |
| `profil` | Fichier des personnages | `profil.json` |
| `postes[]` | `id`, `nom`, `role`, `couleur`, `apparence`, `skills[]` | vide en accueil ; déduits des réponses en phase 4 |
| `sources_images[]` | `libelle`, `poste`, `motif` (glob **relatif au projet**, ou `{donnees}/…` pour le dossier de données passé à l'alimentation par `--donnees` ; `**` permis ; un motif absolu, avec `..` ou qui sort du projet est ignoré) pour le mur d'images ; les textures techniques (`_N`, `_ORM`, `_mask`…) sont écartées ; 36 images au plus, 12 Mo chacune | captures du moteur, images cibles |
| `libelles_etapes` | Noms lisibles des étapes de la chaîne moteur | vide |
| `regles_agent[]` | Règles courtes injectées dans chaque agent recruté (20 au plus, une ligne de 200 caractères chacune) | tirées de `regles_de_travail.md` |

## Installation

**Phase 1 (mode accueil)** :
1. Crée `<projet>/.studio/` et ses sous-dossiers `progression/`, `demandes/`, `demandes_vocales/`, `recrues/`.
2. Écris `<projet>/.studio/studio.config.json` (`mode: accueil`, `nom_projet`, `langue`, `postes` vides, `theme` facultatif : `accent`, `sol`, `sol2`, `mur`, `bois` en `#rrggbb`) et `profil.json` par défaut (gabarits `modeles/studio.config.json` et `modeles/profil.json` ; projet en anglais : `modeles/en/`, règles des agents, titre et reconnaissance vocale en anglais ; noms vides : `{{nom_maitre}}` et `{{nom_assistant}}` remplacés par `""`, la page les demande).
3. **Toujours** (dépôt git ou pas encore) : ajoute au `.gitignore` du projet, en le créant s'il manque et sans rien retirer de l'existant, le bloc ci-dessous. Tout `.studio/` reste sur la machine (profil, dictées, mur d'images, état de la machine) ; seuls `roadmap.json` et `studio.config.json` (chemins relatifs, aucun chemin local) peuvent être versionnés. Le reste seulement si l'utilisateur le demande.
   ```gitignore
   # Studio gamedev : données locales (profil, dictées, images, état de la machine)
   .studio/*
   !.studio/roadmap.json
   !.studio/studio.config.json
   ```
   Si des fichiers de `.studio/` sont déjà suivis par git, dis-le et propose `git rm --cached` (sans commit sans accord). En adoption, passe par `python -I -B <skill>/studio/outils/adoption.py gitignore --projet <projet>` : le bloc n'est ajouté que s'il manque, à la fin, sans toucher au reste.
4. Lance en arrière-plan : `python -I -B <skill>/studio/serveur_studio.py --projet <projet>` (port : `--port`, sinon `studio.config.json`, sinon 8790 ; s'il est pris, le premier libre après). La première ligne affichée donne l'adresse.
5. Ouvre `http://127.0.0.1:<port>/studio.html` (navigateur intégré s'il existe, sinon donne le lien).

**Phase 4 (mode travail)** : passe `mode` à `travail`, remplis `postes` (9 au plus ; 12 bureaux avec les recrues), `moteur`, `outils_lourds` si besoin, `sources_images`, `regles_agent` ; écris `<dossier_agents>/<id>.md` pour chaque poste depuis `modeles/agent.md` (`{{outils}}` = `Read, Grep, Glob, Edit, Write, Bash, Skill`, `{{modele}}` = `economie.modele_agents` ; ne remplace jamais une définition existante sans accord). Lance l'alimentation en arrière-plan par sa veille : `python -I -B <skill>/studio/veille_studio.py --projet <projet>` (ajoute `--donnees <dossier>` seulement pour le dossier de données hors du projet que l'utilisateur a choisi). Seule, `studio_etat.py --projet <projet>` passe toutes les 10 s et s'arrête après 12 h (`--duree-h 0` : sans limite ; `--une-fois` pour un passage ; une seule boucle par projet grâce à `studio_etat.verrou`). La page relit la config toutes les 10 s ; si `etat.json` a plus d'une minute, un bandeau rouge le dit et la page calcule l'état elle-même.

**Essai** : `python -I -B studio/outils/essai_complet.py preparer --dossier <…>/essai_skill`, puis `… serveur --dossier <…>/essai_skill` (premier port libre à partir de 8810) ; pendant le questionnaire, `… deduire` joue le rôle de Claude après le pitch ; à « J'écris ta roadmap… », `… roadmap` ; puis `… verser J0` fait gagner le premier succès (`… tout` fait preparer, deduire, remplir et roadmap sans navigateur). Mode travail : `… travail` (images d'essai), `… serveur` (lance aussi l'alimentation), « Recruter » dans la page, puis `… recrue <nom>` vérifie demande, fiche et agent ; `… progresser <nom> 40` (assis, « travaille »), `… progresser <nom> 100` (debout, « libre ») ; `… rapport` ouvre le rapport plein cadre ; `… etat` fait un passage d'alimentation sans serveur.

**Adoption (projet déjà commencé)** : avant l'installation, `adoption.py analyser` (lecture seule ; écrit seulement `.studio/analyse_projet.json`, `analyse_projet.md`, `empreintes_adoption.json`), confirmation de l'utilisateur, puis `adoption.py preremplir` (réponses déduites, `"mode": "adoption"`, message « Je reprends ton projet »). Phase 4 : `postes` = `analyse_projet.json.postes_proposes` (les besoins réels du projet), `moteur` = le moteur trouvé ; une définition d'agent qui existe déjà dans `.claude/agents/` n'est jamais remplacée (le poste la réutilise ou prend un autre nom). Fin de l'adoption : `adoption.py verifier` (code 0 = aucun fichier existant modifié). Essai : `… essai_complet.py adoption --dossier <…>/essai_adoption`.

**Config qu'on n'a pas écrite** (dépôt cloné, projet d'un autre, `studio.config.json` modifié hors de toi) : avant de lancer le serveur ou l'alimentation, montre à l'utilisateur ce qu'elle demande (`postes`, `sources_images`, `outils_lourds`, `dossier_agents`, `regles_agent`, `economie`) et fais-la valider. Même validée, le code n'accepte que des chemins dans le projet (ou `--donnees`), borne les règles injectées et n'écrit les agents que dans le projet.

## API locale (écrite par la page, via le serveur)

| Route | Corps | Écrit |
|---|---|---|
| `POST /api/questionnaire` | `{cle?, valeur?, source?, via?, texte_brut?, raison?, chapitre_courant?, chapitres_finis?, etat?, mode?, langue?}` | fusion dans `.studio/reponses_questionnaire.json` (écriture atomique) |
| `POST /api/profil` | `{maitre?, assistant?, voix?}` (valeurs bornées : listes de `questionnaire.md`) | `.studio/profil.json` (fusion) |
| `POST /api/demande` | `{cible: "assistant" \| "<id de poste ou de recrue>", texte, via: "voix" \| "ecrit", sujet?: "optimisation"}` (texte ≤ 2 000 caractères) | `.studio/demandes_vocales/<horodatage>-<ms><code>_<cible>.json` (nom unique, créé en mode exclusif) ; même texte à la même cible en moins de 60 s : rien de plus (`doublon: true`) ; `sujet: "optimisation"` : une seule en attente, 30 min entre deux (429) |
| `POST /api/repondre` | `{id, choix, texte_libre}` | `.studio/reponses.json` (réponse à une décision de la cloche) ; **503 sans rien écrire** si le fichier existe mais est illisible |
| `POST /api/reglages` | `{frequence_rapport_min?, attribution_auto?: bool, embauche_auto?: bool}` (un au moins) | `.studio/reglages.json` (fusion) |
| `POST /api/confier` | `{agent, mission (≤ 4 000), titre?, tache_id?, origine?: "page" \| "tache:<id>" \| "auto:fin-de-tache"}` | `.studio/demandes/<…>_<agent>.json` (`type: "tache"`, `lancer: true`, `statut: "nouvelle"`) ; rien n'est lancé. `auto:` : 403 si `attribution_auto` est coupé, 429 si une attribution automatique du poste attend encore ou s'il y en a déjà eu 4 dans l'heure ; doublon 60 s |
| `POST /api/renvoyer` | `{nom, motif?}` | recrue seulement (403 pour un poste de la config ; 409 si une demande n'est pas finie ou si la progression bouge encore) : `recrues/<nom>.json` → `recrues/_anciens/<nom>.json` (+ `renvoye_le`), définition d'agent marquée → `.studio/anciens/agents/<nom>.md` (hors du dossier des agents : plus chargée), index à jour (`recrues/_anciens/index.json`) ; rien n'est effacé |
| `POST /api/reembaucher` | `{nom}` | l'inverse (fiche avec `reembauche_le`, `lancer: false`) ; 409 si le nom existe déjà ou si les 12 bureaux sont pris |
| `POST /api/recruter` | `{nom (a-z, 0-9, -, 3 à 40), nom_affiche?, role (≤ 200), mission (≤ 4 000), poste?, couleur?, apparence?, skills? (12 au plus), lancer?, remplacer?, via?, auto?}` (`auto: true` = embauche décidée par le studio : 403 si `embauche_auto` est coupé, 429 si une autre a eu lieu dans l'heure, 409 à 12 bureaux ou pour un ancien renvoyé ; `lancer` forcé à `false` ; fiche `origine: "auto:embauche"`) | `<dossier_agents>/<nom>.md` (dans le projet seulement ; 409 s'il existe sans `remplacer`, si le nom est un poste de la config, si le fichier est un lien, ou si `remplacer` vise un agent qui n'est pas une recrue du studio : fiche `recrues/<nom>.json` + marque `<!-- studio-gamedev : recrue -->`), `recrues/<nom>.json`, `recrues/index.json`, `demandes/<horodatage>_<nom>.json` (`type: "recrutement"`) ; rien n'est lancé |
| `POST /api/transcrire` | audio brut (webm/ogg/wav, 8 Mo au plus) | rien : renvoie `{ok, texte}` ; **501** avec un message clair si `faster-whisper` n'est pas installé |

## Contrat de fichiers

Tous dans `<projet>/.studio/` (le « dossier du studio »).

| Fichier | Écrit par | Lu par | Format |
|---|---|---|---|
| `studio.config.json` | Claude | page, serveur | « Paramètres » ci-dessus |
| `reponses_questionnaire.json` | page (API) ; Claude en repli | Claude, page (reprise) | `questionnaire.md`, « Format des réponses » |
| `profil.json` | page (API) ; Claude | page, point de suivi | `questionnaire.md`, « Format de profil.json » |
| `deductions.json` | Claude | page | ★ recalculés, valeurs fixées, propositions, message de l'assistant ; après le pitch, la page attend un fichier **nouveau** (contenu changé) 60 s au plus, avec « Continuer sans attendre » au bout de 8 s |
| `questions_suivi.json` | Claude | page | questions de suivi posées par l'assistant juste après la question en cours |
| `demandes_vocales/<horodatage>_<cible>.json` | page (API) | Claude | `{"id", "cible", "texte", "via", "cree_le", "statut": "nouvelle"}` |
| `reponses_assistant.json` | Claude | page | `[{"id", "a_propos", "texte", "cree_le"}]` → bulle de l'assistant, notification (et voix haute si activée) |
| `progression/<poste>.json` | chaque agent | page, alimentation | `{"pct": 0-100, "texte", "etape"?, "restant_min"?, "fin"?: "HH:MM" ou ISO, "restantes"?: [étapes], "bloque"?: true, "poste"?: "<id>" (rattache un chantier à un poste), "jalon"?}` |
| `recrues/<nom>.json`, `recrues/index.json` | serveur (recrutement) | page, alimentation | `{"nom", "nom_affiche", "role", "mission", "poste", "skills", "couleur", "apparence", "lancer", "via", "cree_le", "agent"}` ; l'index liste les noms dans l'ordre d'arrivée |
| `demandes/<horodatage>_<nom>.json` | serveur (recrutement, tâche confiée) ; Claude | Claude, alimentation | fiche de la recrue + `{"id", "type": "recrutement", "statut": "nouvelle"}` ; une tâche confiée : `{"id", "nom", "type": "tache", "titre", "mission", "tache_id"?, "origine": "page" \| "tache:<id>" \| "auto:fin-de-tache", "lancer", "statut", "cree_le"}` |
| `recrues/_anciens/<nom>.json`, `recrues/_anciens/index.json`, `anciens/agents/<nom>.md` | serveur (renvoi) | page (« Anciens » du recrutement) | fiche + `renvoye_le`, `motif` ; définition d'agent archivée hors du dossier des agents |
| `reglages.json` | page (API) | page, serveur, alimentation | `{"frequence_rapport_min"?, "attribution_auto"?, "embauche_auto"?, "maj"}` : absent = valeur de `economie` (coupé par défaut) |
| `decisions_studio.json` | `studio_etat.py` (60 s) | page | propositions du studio, même forme que `decisions.json` + `{"type": "renvoi", "nom"}` : recrue libre depuis 24 h sans tâche prête pour son poste → « Renvoyer / Garder » (★ Garder) ; l'id porte le début de la période libre (une réponse « Garder » n'est pas reproposée avant la suivante) ; jamais appliquée sans réponse |
| `demandes/statuts.json` | Claude (Direction) | page, alimentation | `{"<poste>" ou "<fichier de demande>": {"statut": "nouvelle" \| "en attente" \| "lancé" \| "fini" \| "bloqué", "maj", "texte"}}` |
| `attentes.json` | Claude (Direction) | alimentation | `{"<poste>": {"attente": "…", "suite": "…"}}` : un poste listé ici n'est jamais « disponible » |
| `rapport_assistant.json` | Claude (point de suivi) | page, alimentation | `{"heure": ISO, "blague", "tableau": [{"chantier", "etape", "pct", "reste"}], "fini": [texte], "a_decider": [texte \| {"id" de décision, "titre"}]}` → s'ouvre **plein cadre au centre** par la file unique (une fois par rapport ; bouton « Rapport » pour le rouvrir) |
| `decisions.json` | Claude / assistant | page | `[{"id", "titre", "explication", "choix": [{"id", "libelle"}], "recommande", "cree_le", "poste"?}]` → la cloche sonne, une bulle « ? » apparaît au-dessus du personnage `poste` (sinon de l'assistant) et la décision entre dans le fil de conversation |
| `reponses.json` | page (API) | Claude | `[{"id", "choix", "texte_libre", "repondu_le"}]` → reportées dans `DECISIONS.md` |
| `roadmap.json` | Claude (fin du questionnaire, puis à chaque versement) | page | « roadmap.json » ci-dessous |
| `analyse_projet.json`, `analyse_projet.md` | `adoption.py analyser` (adoption) | Claude | inventaire du projet existant : `moteur` {nom, version, langage, preuve, details}, `scenes`, `code`, `systemes[]` {id, titre, preuve, carte, poste, estimation_standard_h}, `assets`, `docs`, `pitch_readme`, `conventions`, `tests`, `todo`, `git`, `calibrage` {heures_deja_estimees, methode, heures_standard_de_l_existant, facteur, heures_par_semaine_observees}, `deductions` {sures, probables}, `existant[]` (→ J0), `manques`, `postes_proposes`, `fichiers_proteges[]` {chemin, action : `a_cote`, `bloc` ou `bloc_gitignore`, cible}, `agents_existants`, `resume` (5 lignes) |
| `empreintes_adoption.json` | `adoption.py analyser` (première analyse ; `--nouvelle-photo` pour la refaire) | `adoption.py verifier` | `{"cree_le", "fichiers": {"<chemin>": {"sha256", "taille"}}}` |
| `propositions/<fichier>.bloc.md` | Claude (adoption) | Claude, utilisateur | bloc proposé pour un fichier existant (`CLAUDE.md`…), en attente d'accord |
| `etat.json` | `studio_etat.py` (10 s) | page (fait foi s'il a moins de 60 s) | `{"version": 1, "projet", "heure", "horodatage", "version1": {"pct", "texte", "source": "roadmap", "jalon"}, "postes": [{"id", "nom", "genre": "fixe" \| "recrue", "etat", "occupe", "progression", "restant_min", "texte", "tache", "restantes", "demandes", "ligne": {"picto", "texte" (≤ 40), "complet"}, "depuis"}], "chaine_active", "outils_lourds", "git": {"branche", "sales", "commits"}, "systeme", "images": [{"src": "mur/…", "titre", "libelle", "poste", "h"}], "alertes", "rapport": {"prochain", "dans_min"}, "anomalies": [{"fichier", "raison", "vu"}], "messages": [{"id", "cible", "texte", "cree_le", "statut", "via"}]}` ; chaque poste a aussi `progression_t` (heure du fichier de progression : « dernière nouvelle de l'agent ») et `fin_t` (fin prévue : heure du fichier + `restant_min` écrit par l'agent), d'où la page tire une barre qui avance entre deux écritures (jamais au-delà de 99 % avant que l'agent écrive 100, redescente douce si le nouveau % est plus bas ; fiche, groupe et vue d'ensemble rafraîchis toutes les 5 s), `calme_min`, `fin_de_tache` (et `fini`, ce qu'il vient de finir), `demandes[].tache_id` et `.origine` ; `xp`, s'il y est, s'ajoute au niveau |
| `suggestions.json` | `studio_etat.py` (60 s) | Claude, assistant | `{"maj", "suggestions": [{"id", "gravite": "urgent" \| "conseil" \| "info", "titre", "explication", "action_proposee"}]}` : outil lourd inactif alors qu'une tâche l'attend (seulement sans chaîne active), deux instances de l'outil lourd, disque presque plein, dépôt modifié non commité, poste bloqué, progression figée depuis 1 h, demande en attente depuis 15 min, demandes de la page sans réponse |
| `taches_disponibles.json` | `studio_etat.py` (60 s) | Claude, page (fin de tâche, embauche) | `{"maj", "taches": [{"id", "jalon", "titre", "critere", "statut", "poste", "moteur", "sans_moteur", "effort_h", "depend_de", "origine", "metier"}]}` (plus les entrées `a_corriger` de `backlog_studio.json`) : tâches `a_faire` ou `en_cours` dont toutes les dépendances sont versées, **sauf** les tâches sorties, écartées, abandonnées, reportées, remplacées ou retirées (drapeau `retiree` / `hors_v1` / `abandonnee` / `reportee` / `remplacee`, ou ce mot dans `note` ou `etat`) ; les entrées sans `"origine": "roadmap"` (écrites à la main) sont gardées |
| `mur/` | `studio_etat.py` | page | copies des dernières images de `sources_images` (le dossier est nettoyé : n'y mets rien d'autre) ; parcours borné à 2 000 chemins et 2 s par passage, repris au passage suivant là où il s'est arrêté ; les images déjà trouvées et les dossiers qui en donnent sont relus d'abord ; dossiers de cache ignorés |

**État d'un poste** (mêmes règles dans `studio_etat.py` et, à défaut, dans la page) :
- *bloqué* si `bloque` ou statut « bloqué » ;
- *travaille* (**occupé = assis à son poste**) si sa progression a bougé depuis 30 min et est sous 100 %, si sa demande est « lancé », si son outil lourd est ouvert, ou (poste `session_poste`) si la session Claude Code bouge ;
- *disponible* (**debout, « ☕ libre »**) **seulement s'il ne reste rien** : ni `restantes`, ni tâche de roadmap à son poste qui ne soit `verse` ou `ecart`, ni demande non finie (une progression à 100 % écrite après la demande la solde), ni attente dans `attentes.json` ;
- *fini* s'il a fini mais a encore des étapes ; *en attente* sinon (« ⏸ attend le lancement : … », « ⏸ en pause (N min) : … », « ↔ suite : … »).
La **ligne du bandeau** (pictogramme ▶ ⏸ ↔ ☕ ⛔ + tâche, 40 caractères) n'est jamais vide (« ? état inconnu » en dernier recours). **Version 1** : avancement de la roadmap pondéré par l'effort (`verse`/`ecart` 1, `pret` 0,7, `en_cours` 0,35, `a_faire` 0 ; tâche sans estimation = poids 1). **Chaîne active** : progression modifiée depuis 10 min, outil lourd ouvert ou demande lancée depuis 15 min ; tant qu'il y en a une, l'alerte d'inactivité se tait. Temps restant : `restant_min`, sinon `fin`, sinon estimé sur la vitesse observée (« ? » tant qu'il n'y a pas assez de mesures). Tous les JSON sont lus avec ou sans BOM.

**Une seule file pour le panneau central** : fiche de poste, décision, « Appeler l'assistant » s'ouvrent l'un après l'autre (« N à suivre ») ; le bandeau des succès a sa propre file, ne montre chaque succès qu'une fois et reprend au retour sur l'onglet. Un rapport n'est marqué « vu » que quand l'onglet est visible.

**Décisions, conversation, fin de tâche, renvoi (mode travail)** :
- **Bulles de décision** : chaque décision ouverte (`decisions.json` et `decisions_studio.json`) a une bulle « ? » dorée au coin de l'étiquette du personnage nommé par `poste` (ou `qui`, `nom`), sinon au-dessus de l'assistant (plusieurs : un compteur). Clic : la décision en grand (choix, champ libre, micro). Répondue, la bulle s'envole (✓) et disparaît.
- **Conversation avec l'assistant** (bouton « Conversation ») : fil dans l'ordre des heures : messages de l'utilisateur (`etat.json` → `messages`, plus ceux envoyés depuis ce navigateur ; statut « déposé », « lu » = `prise`, « traité » = `faite`), réponses de `reponses_assistant.json`, décisions (boutons tant qu'elles sont ouvertes, réponse donnée sinon) ; champ et micro en bas pour écrire à l'assistant. Le fil n'est redessiné que s'il change, le brouillon en cours reste. **Filet** : une réponse qui finit par « ? » sans décision créée dans la minute (et sans message de l'utilisateur depuis) → bulle bleue « L'assistant te pose une question » au-dessus de lui et notification ; clic = le fil.
- **Fin de tâche** : quand `etat.json` dit `fin_de_tache` (progression à 100 % immobile depuis 5 min, plus rien devant lui, pas de chaîne active à son nom, pas de demande lancée), le personnage quitte son bureau et va attendre près de l'assistant (« J'ai fini … Quelque chose pour moi ? », pictogramme ⚑). Sa fiche propose **Lui confier une tâche** (liste), **Trouve-toi une tâche** (première de la règle), **Laisser en pause**. Règle : tâche prête de son poste, puis préparation sans moteur d'une tâche de son poste dont les dépendances ne sont pas faites, seulement ensuite une tâche sans moteur hors de son métier ; jamais une tâche déjà confiée ou en cours. Avec `attribution_auto` (coupé par défaut), sans réponse en 2 min, l'assistant confie la première (`origine: "auto:fin-de-tache"`). Un personnage simplement libre a le même encadré, sans compte à rebours.
- **Renvoi** : « Renvoyer… » sur la fiche d'une recrue (jamais un poste de la config), avec confirmation ; il part par la porte avec son carton. Le formulaire Recruter liste les **Anciens** avec « Réembaucher ». Une ligne « Renvoyer / Garder » de `decisions_studio.json` répondue « Renvoyer » appelle le renvoi (refusé si une tâche est en cours : la décision reste ouverte).
- **Embauche automatique** (`embauche_auto`, coupé par défaut) : une tâche prête dont le `poste` n'a personne → recrue de ce métier (`lancer: false`), une par heure, 12 bureaux, jamais un ancien renvoyé.
- **Rapport** : chaque ligne « À décider » a un bouton **Décider** (décision retrouvée par `id`, sinon par son texte) ou **Ouvrir la cloche** ; jamais un recrutement ni une tâche confiée depuis ces lignes.
- **Réglages** (bouton engrenage) : fréquence du rapport, attribution automatique, embauches automatiques, avec la raison de leur défaut coupé (chaque automatisme fait travailler un agent, donc dépense des jetons).
- **Alimentation** : bandeau rouge si `etat.json` a plus d'une minute ; un fichier illisible de `etat.json` → `anomalies` donne une alerte (une fois). Avancements par lot : compte des objets distincts (pas des fichiers ; dossiers de travail `_…` et scripts ignorés) dans `pct`, `texte` ou `restantes`.

Traitement d'une demande vocale par Claude : lire le fichier, passer `statut` à `prise`, agir (ou transmettre à l'agent), répondre dans `reponses_assistant.json`, passer `statut` à `faite`. Une question à l'utilisateur : de préférence une décision (`decisions.json`, avec `poste` si elle concerne un personnage) plutôt qu'une réponse qui finit par « ? ». Une demande sensible (publier, supprimer, dépenser des crédits, pousser du code) devient une **décision** dans `decisions.json` ou une question dans la conversation : jamais exécutée sur la seule foi d'une dictée.

**Ce que montre aussi la page** : le **mur d'images** (3 cadres au mur, bouton « Images » : les dernières images de `sources_images`, copiées dans `mur/`) ; le **bandeau d'événements** (succès, fins de tâche, embauches, en file, une fois chacun) ; la **ligne de tâche** sous chaque barre (toujours remplie, voir plus haut) ; les **persos libres** : seul un personnage sans tâche se lève et reste debout à côté de son bureau, une tasse à la main (petites conversations en bulles si le réglage est ouvert) ; un personnage au travail reste assis au clavier.

**Téléphone** (largeur ≤ 640 px) : barre d'outils sur une ligne qui défile, icônes seules (le nom de chaque bouton reste lu par les lecteurs d'écran) ; l'équipe en bande horizontale en bas.

**Conversation (à droite)** : le bouton « Conversation » ouvre à droite la même conversation que Claude Code. Le serveur lit en lecture seule le transcript de la session (`~/.claude/projects/<slug du projet>/` : le `.jsonl` le plus récent, ou `dossier_session` de la config), en flux (seulement la fin, `GET /api/conversation?depuis=<offset>`), et ne garde que le texte de l'utilisateur et de l'assistant (ni outils, ni pensées, ni rappels système, ni sous-agents) ; la page le relit toutes les 2,5 s, en markdown, et reste en bas sauf si on remonte. Les questions de `decisions.json` y sont aussi, avec leurs boutons, puis « réglé : … ». En bas : saisie multiligne (Entrée envoie, Maj+Entrée retour à la ligne) et micro ; l'envoi passe par `demandes_vocales/`. Le transcript ne quitte jamais la machine.

**Tyrannie : diagnostic et rôle temporaire** : un agent bloqué (marqué bloqué, ou sans nouvelles depuis 20 min sans être à 100 %) reçoit un diagnostic : attend ta décision (la question remonte en tête de la cloche et du fil), attend le moteur (sa place dans la file), un outil lourd déjà ouvert, un autre agent (seulement « attend X », « en attente de X », « bloqué par X »), un fichier, machine saturée (Santé du PC), erreur dans son journal (extrait), ou silence (relance proposée). Bulle : « X est bloqué : raison → action » ; la demande à l'assistant contient le diagnostic (seulement si la liste change, au plus toutes les 15 min). S'il attend le moteur, une décision, un agent, un fichier ou un outil, il reçoit une autre tâche sans moteur (`origine: "auto:temporaire"`, permise par la tyrannie, mêmes plafonds) en **rôle temporaire** affiché dans sa fiche ; sa tâche d'origine reste réservée.

**Points regroupés** : un seul rapport de point en plein cadre à la fois ; un nouveau point à moins de 15 min du précédent (ou pendant qu'un point est ouvert) va au journal, sans cloche (« N points plus anciens dans le journal »).

**Application sur le téléphone** : le studio est installable (`manifest.webmanifest` servi par le serveur avec le nom du projet, icônes `icone-180/192/512.png`, balises iOS, `sw.js`). Le service worker ne met en cache que la coquille (HTML, scripts, styles, icônes) en « réseau d'abord » : jamais les données (`*.json`) ni `/api/`, et le PC voit toujours la dernière version ; il ne s'enregistre qu'en contexte sûr (https ou l'ordinateur lui-même). En http sur le Wi-Fi, « Ajouter à l'écran d'accueil » marche quand même, sans mode hors ligne (l'aide le dit dans Réglages). Sur téléphone (≤ 640 px) ou lancé depuis l'écran d'accueil (`?app=1`) : barre d'onglets en bas (Équipe, Conversation, Cloche, Roadmap, Réglages), panneaux plein écran, gros boutons.

**Dictée propre** : la reconnaissance du navigateur reconstruit tout le texte à chaque événement depuis `e.results` (jamais d'accumulation), fusionne les segments (une version plus longue remplace la précédente, une plus courte ou identique est ignorée, un recouvrement n'est gardé qu'une fois) et retire les débuts de phrase répétés (« faut faut que faut que tu » → « faut que tu » ; « très très » gardé) ; sur téléphone, mode phrase (`continuous = false`) ; le texte n'est rendu qu'une fois. Même nettoyage côté transcription locale (`dictee_propre.py`). Essais : `node studio/outils/test_dictee.js`, `python -I studio/dictee_propre.py`.

**Backlog du studio** (`backlog_studio.json`, facultatif) : tâches propres au studio lui-même (pas au jeu), écrites par l'assistant : `{"taches": [{"id", "titre", "statut": "a_corriger" | "corrige" | "ecarte", "version", "note"}]}`. L'alimentation ajoute chaque entrée `a_corriger` à `taches_disponibles.json` (`origine: "backlog"`, id `studio-<id>`, `metier: "studio"`) ; la fin de tâche et la tyrannie la proposent **seulement** aux postes qui ont le métier « Studio » (fiche « Nom et rôles »), jamais hors métier.

### Ajouts 0.3.1

| Fichier | Écrit par | Contenu |
|---|---|---|
| `journal_assistant.json` | crochet Stop (`outils/crochet_journal.py`, installé avec accord par `outils/installer_crochet.py`) | `[{id, cree_le, titre, texte, source:"crochet"}]`, 60 dernières réponses de l'assistant (clés et adresses masquées) ; la page les fusionne avec `reponses_assistant.json` |
| `demandes_vocales/*.json` | page | champ facultatif `en_reponse_a` : id de la réponse ou du rapport sous lequel l'utilisateur a répondu |
| `reglages.json` | page | `attribution_auto`, `embauche_auto`, `enchainement_auto`, `point_auto`, `optimisation_auto`, `tyrannie_auto` (tous `false` par défaut, « Tout couper » les remet à `false`), `frequence_rapport_min`, `mode_absent` (+ `mode_absent_depuis`, `absence_derniere`), `ordre_equipe` (ordre du groupe à gauche), `sante_auto`, `blague`, `noms_postes`, `roles_postes`, `metiers_postes`, `modeles_postes` (fiche « Nom et rôles » des postes de la config ; à relire quand l'assistant lance un agent) |
| `optimisation.json` | assistant | `{heure, resume, actions_faites:[{titre, detail}], propositions:[{id, titre, detail, gain_estime}]}` : rapport « Optimiser » ; les propositions cochées reviennent en une seule demande |
| `musique/` | alimentation | copie des musiques du jeu (`sources_musique` de la config, sinon dossiers `music`/`musique` des 3 premiers niveaux du projet ; 20 morceaux, 15 Mo chacun au plus) pour la radio du studio (coupée par défaut) |

## roadmap.json : la roadmap dans le studio

Écrit par Claude **à la fin du questionnaire** (étape non sautable, `questionnaire.md`, « Roadmap générée ») dans `<projet>/.studio/roadmap.json` (versionné, lu par la page toutes les 10 s). Même contenu que `docs/ROADMAP.md`, mis à jour en même temps à chaque versement. Exemple court : `modeles/roadmap.json`. Textes dans la langue du projet.

| Champ | Sens |
|---|---|
| `version`, `langue`, `projet`, `cree_le`, `maj` | `1` ; `fr` / `en` ; nom du jeu ; horodatages ISO |
| `sources` | `{"questionnaire": ".studio/reponses_questionnaire.json", "document": "docs/ROADMAP.md"}` |
| `rythme` | `{"heures_par_semaine", "debut"}` : base des dates visées |
| `niveau` | `{"xp_par_tache": 100, "xp_par_jalon": 500, "rangs": [{"niveau", "nom"}]}` |
| `jalons[]` | `id` (`J0`…), `titre`, `but`, `critere_fin`, `depend_de[]` (jalons), `fin_visee` (date), `succes`, `taches[]` |
| `jalons[].taches[]` | `id` (`J1-03`), `titre`, `critere`, `poste`, `moteur` (bool), `estimation_h`, `depend_de[]` (tâches), `statut`, `preuve?` (commit, ou fichier pour le J0 d'une adoption), `fait_le?` |
| `mode?`, `sources.analyse?`, `rythme.facteur_calibrage?` | adoption : `"adoption"`, `.studio/analyse_projet.json`, facteur appliqué aux estimations ; `sources.document` = `docs/ROADMAP.studio.md` si `docs/ROADMAP.md` existait |
| `statut` | `a_faire`, `en_cours`, `pret` (préparé sans moteur), `verse` (critère rempli, dans la branche principale), `ecart` (écart noté, accepté) |
| `jalons[].succes` | `{"id", "titre", "description", "icone", "son", "obtenu_le?"}` ; `icone` = `cartes/<nom>.svg` ou un caractère ; `son` = `petit`, `moyen`, `grand` (fanfare synthétisée) ou un fichier `.ogg` / `.mp3` / `.wav` relatif au studio |
| `succes_final` | même forme : débloqué quand tous les jalons sont terminés |

Règles lues par la page (`roadmap.js`, fonction `calculer`) :
- Un jalon est **terminé** quand toutes ses tâches sont `verse` ou `ecart` ; son succès est alors **gagné** (ou dès que Claude écrit `succes.obtenu_le`). Sinon il s'affiche verrouillé (🔒).
- Nouveau succès gagné : bannière en haut de la page + son, une seule fois par navigateur (mémoire locale) ; en fin de questionnaire, les succès déjà gagnés sont fêtés.
- **Niveau du studio** : XP = `xp_par_tache` × tâches versées + `xp_par_jalon` × jalons terminés ; niveau = ⌊(XP / 100)^0,55⌋ + 1 ; rang = dernier `rangs[]` atteint. Une montée de niveau donne un grand succès. La page envoie l'événement `studio:roadmap` (détail : avancement, XP, niveau) : `studio.html` l'ajoute à l'XP de `etat.json` s'il en a une, sinon l'affiche tel quel.
- Ce qui vient du fichier est affiché comme du texte (jamais comme du HTML) ; icônes et sons seulement en chemins relatifs du studio.

**Dans la page** : `<link rel="stylesheet" href="roadmap.css"><script src="roadmap.js"></script>`, puis `Roadmap.installer({langue, barre: <barre des boutons>, succes: <fonction de succès du studio, facultative>})` ajoute le bouton **Roadmap** (avec le % d'avancement) ; quand le maître valide le récapitulatif (`fin.valider = oui`), la page appelle `Roadmap.voici()` : écran « J'écris ta roadmap… » sans bouton fermer, puis « Voici ta roadmap » avec fanfare dès que `roadmap.json` arrive, et bouton « C'est parti ! ».

## Paliers du studio

`paliers.js`, appelé par `studio.html`. Palier = le plus haut de :
- **niveau du studio** (`roadmap.json` + XP de `etat.json`) : 1 → garage, 5 → petit bureau, 10 → studio, 16 → studio pro, 24 → studio AAA (les rangs du gabarit) ;
- **avancement de la roadmap** (tâches versées) : 15 %, 35 %, 60 %, 90 % (ou roadmap finie).

Mode accueil (questionnaire) : garage. Le palier vu est mémorisé dans le navigateur (`studio.palier.<nom du projet>`) : une montée depuis la dernière visite se joue une fois en **chantier** (7,5 s : échafaudage, plots, poussière, étincelles, perceuse et marteau synthétisés, bandeau « Travaux en cours », puis apparition pièce par pièce) et un succès « Ton studio s'agrandit ». Sans animation si `prefers-reduced-motion`.

| Palier | Sol | Murs | Lumière et effets | Mobilier |
|---|---|---|---|---|
| 1 Garage | béton (dalles, joints, taches) | parpaings, gaine | ampoule qui se balance, guirlande qui scintille, poussière dans le faisceau de la fenêtre | tréteaux, vieil écran, étagère métal, cartons, ventilateur, chat endormi, cactus ou plante sur l'appui |
| 2 Petit bureau | stratifié clair | peints, plinthe | deux suspensions, lumière du jour | plantes, tableau blanc, horloge à l'heure, tapis |
| 3 Studio | dalles de moquette | mur d'accent à la couleur du jeu | suspensions industrielles, écrans | îlot, machine à café (vapeur), canapé, télé et console (l'assistant s'y assoit et joue), affiches |
| 4 Studio pro | parquet chaud | lambris bas | éclairage chaud, appliques, écrans muraux animés | salle de réunion vitrée, panneaux acoustiques, grande plante |
| 5 Studio AAA | bois sombre ciré | tasseaux, poutre | verrière et rais de lumière, rails lumineux mobiles, particules, néon | mezzanine, borne d'arcade, trophées |

**DA déduite** (jamais d'asset du jeu) : `da.palette` (chaude, froide, contrastée, sourde, vive) donne accent, accent 2, mur, sol, bois, lumière ; `genre.principal` = horreur assombrit et refroidit ; `vision.emotion` (détente, tension) règle le voile ; `monde.climat` choisit la vue (forêt, montagne, désert, tropical, ville, mer, souterrain, espace, imaginaire) et les plantes (cactus, palmier, cristaux, champignons). Nuit (après 21 h) : ciel étoilé, voile plus dense.

Personnages (`sprites.js`) : assis à leur poste, dos à nous, face à l'écran (qui affiche du code quand ils travaillent) ; debout « gratte la tête » s'ils sont bloqués, « joie » s'ils ont fini, tasse à la main s'ils sont libres ; l'assistant marche (8 directions, pieds sans glisse), boit un café ou joue sur le canapé à partir du palier 3.

## Voix

- **Reconnaissance** : Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`), langue = `profil.voix.langue_reconnaissance` (déduite de la langue du maître), résultats intermédiaires affichés en direct dans le champ, puis le texte final est modifiable avant validation (sauf correspondance sûre à une carte : sélection avec 3 s pour annuler ; sinon `voix_a_interpreter` + `texte_brut`).
- **Bascule sur une transcription locale** : si l'API manque, si le navigateur est Brave, ou si la reconnaissance échoue (`network`, `not-allowed`, `service-not-allowed`, `audio-capture`, `language-not-supported`), la page enregistre le micro (MediaRecorder) et l'envoie à `POST /api/transcrire` ; la bascule est retenue pour les fois suivantes. Le serveur transcrit avec `faster-whisper` s'il est installé (`pip install faster-whisper` ; modèle `STUDIO_WHISPER`, `small` par défaut ; dossier des modèles `STUDIO_WHISPER_DIR` ; GPU si possible, sinon processeur), sinon il répond 501 et la page invite à écrire la réponse. Décodage de l'audio, dans l'ordre : `ffmpeg` en ligne de commande s'il est dans le PATH (commande fixe, l'audio passe par l'entrée standard), sinon PyAV, sinon le décodeur de faster-whisper ; 422 seulement si les trois échouent.
- **Vie privée** : dans plusieurs navigateurs, la reconnaissance est faite par un service en ligne du fournisseur du navigateur. La page le dit au premier clic sur le micro, et `voix.micro_actif: false` le coupe partout. La transcription locale ne garde aucun son (fichier temporaire effacé aussitôt).
- **Voix de l'assistant** (option `assistant.voix_haute: "oui"`) : `speechSynthesis` du navigateur, pour les réponses de `reponses_assistant.json` ; coupée par défaut.
- Raccourcis : **A** = appeler l'assistant ; **Échap** ferme le panneau.

## Arrêt

« Arrête le studio » : `python -I -B <skill>/studio/outils/arreter.py --projet <projet>` arrête la veille, l'alimentation puis le serveur, et seulement eux (pids notés dans `.studio/veille_studio.verrou`, `.studio/studio_etat.verrou` et `.studio/serveur.json` ; le serveur doit d'abord confirmer sur `GET /api/qui` qu'il sert ce projet avec ce pid). Les fichiers restent ; relancer reprend où on en était (questionnaire compris : la page repart à la première question sans réponse).

**Téléphone sur le Wi-Fi de la maison** (coupé par défaut, seulement si l'utilisateur le demande) : `serveur_studio.py --projet <projet> --reseau` écoute aussi sur l'IP locale (privée, détectée, ou `--ip=192.168.x.y`). Toute requête qui ne vient pas de 127.0.0.1 doit porter la clé secrète (32 caractères, `.studio/cle_reseau.txt`, jamais servie) en `?cle=` ou en cookie ; sinon refus. L'adresse à ouvrir sur le téléphone est écrite dans `.studio/adresse_telephone.txt`. Aucun réglage du système n'est touché : Windows peut demander d'autoriser Python, c'est l'utilisateur qui accepte.

**Reprise** : le serveur note son port et son pid dans `.studio/serveur.json` (effacé à l'arrêt). Relancé alors que le serveur de ce projet répond encore, `serveur_studio.py` ne double pas : il affiche la même adresse (« déjà lancé, réutilisé ») et rend la main. La veille refuse aussi de tourner deux fois (`veille_studio.verrou`).

