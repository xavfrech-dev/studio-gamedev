---
description: Ouvre le studio de jeu vidéo (nouveau projet ou reprise) / Open the game studio (new project or resume)
argument-hint: "[dossier du jeu / game folder]"
---

Utilise le skill `studio-gamedev` pour ouvrir le studio de jeu vidéo.

Dossier du jeu : $ARGUMENTS

S'il est vide, prends le dossier courant si c'est bien le dossier du jeu, sinon demande-le en une question. Si `<dossier>/.studio/reponses_questionnaire.json` existe, reprends le projet ; sinon commence un nouveau projet (phase 0 du skill). Réponds dans la langue de l'utilisateur.
