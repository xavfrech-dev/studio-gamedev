# Point d'équipe : le point régulier de l'assistant

> **English summary.** Team report: the assistant's regular status report (off by default), only when something changed, with a table of work items, %, time left and decisions.

Le studio a un point régulier, fait par l'assistant (son nom est celui que l'utilisateur a choisi ; sans nom, « le Chef d'équipe »).
Il est **coupé par défaut** (`point_auto: false` dans `.studio/reglages.json`). L'utilisateur l'active dans le tutoriel de départ,
dans « Réglages », ou en disant « point d'équipe » / `/point-equipe`. « Tout couper » l'arrête ; le mode nuit l'empile.

## Lancer (« point d'équipe », `/point-equipe`, ou `point_auto` passé à `true`)

1. Vérifie qu'aucun suivi n'existe déjà (outil de tâches planifiées : liste). S'il y en a un dont le prompt commence par
   « Point d'équipe : », ne le double pas.
2. Fréquence : `frequence_rapport_min` de `reglages.json` (15, 30, 60 ou 120 ; 120 par défaut, jamais plus souvent que
   `economie.point_min` de la config sans demande explicite). Crée la tâche récurrente (par exemple `7 * * * *` pour 60 min)
   avec le prompt « Point d'équipe : suis references/point_equipe.md, section « À chaque point ». ».
3. Fais tout de suite un premier point, puis dis en une ligne que le suivi tourne et comment l'arrêter.

## À chaque point

1. **Relis `reglages.json`** : `point_auto: false` ou `pause: true` (« Tout couper ») : supprime la tâche planifiée et arrête-toi.
   `mode_absent: true` (mode nuit) : fais le point mais **sans le mettre en avant** (voir « Mode nuit »).
2. **État réel, jamais supposé** : `etat.json` (postes, progression, temps restant), `roadmap.json` (avancement pondéré, jalons),
   `git log --oneline -15` et `git worktree list` du projet, processus du moteur (occupé ou libre), l'heure.
   `etat.json` et `roadmap.json` suffisent le plus souvent : ne relis pas tout le projet.
3. **Rien de neuf depuis le dernier point** (`economie.point_si_changement`) : une ligne, pas de rapport.
4. **Écris le rapport dans le studio** : `.studio/rapport_assistant.json` :
   `{"heure", "blague"?, "tableau": [{"chantier", "etape", "pct", "reste"}], "fini": [...], "fin_prevue", "a_decider": [{"id", "titre"}], "suggestions": [...]}`.
   Le studio l'ouvre en grand (sauf en mode nuit) et le garde dans le journal.
5. **Dans la conversation**, court et lisible au téléphone : un tableau chantier | étape | % | reste, ce qui a fini depuis
   le dernier point (avec le hash du commit), l'heure de fin prévue (fourchette honnête : les estimations du moteur doublent souvent),
   ce qui attend l'utilisateur. Chaque question va aussi dans `decisions.json` (miroir des questions).
6. **Lis les réponses** : `reponses.json`, `demandes_vocales/`, `demandes/` ; traite-les comme des messages de l'utilisateur.
7. **Lance les demandes en attente** déjà acceptées (statut `en attente` avec accord), dans les limites de `agents_max`, sans lancer
   le moteur en double ; montre chaque lancement dans la conversation.

## La petite blague

Le point peut s'ouvrir sur une petite blague **bon enfant** (jeu vidéo, bureau, café ; jamais d'humour noir, jamais de cliché
sur un pays, une langue ou un accent). Elle se coupe avec `"blague": false` dans `reglages.json` ou l'humour « aucun » du profil.

## Mode nuit (`mode_absent: true`)

Le point est écrit dans `rapport_assistant.json` avec `"empile": true` et n'est pas annoncé dans la conversation.
Au retour de l'utilisateur, le studio montre « Pendant ton absence » ; reprends alors les points empilés en un seul résumé.

## Arrêt (« stop point d'équipe »)

Liste des tâches planifiées, suppression de celle dont le prompt commence par « Point d'équipe : », `point_auto: false`
dans `reglages.json`. Confirme en une ligne.

## Règles

- Le point ne lance aucun chantier nouveau, ne lance pas le moteur et ne touche pas aux branches en cours.
- Ne jamais dire qu'une chose est finie sans l'avoir vue (commit, journal, rapport d'agent).
- Ne jamais afficher ni écrire de clé d'API.
