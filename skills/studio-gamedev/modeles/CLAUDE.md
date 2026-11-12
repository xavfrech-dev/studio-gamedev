# {{nom_projet}}

{{pitch_court}}

- Moteur : {{moteur}} {{version}} ({{langage}})
- Build : `{{commande_build}}`
- Tests : `{{commande_tests}}`
- Lancement court : `{{commande_lancement}}`
- Données lourdes hors dépôt : `{{dossier_donnees}}`
- Documents : `docs/GDD.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md`, `docs/CHANGELOG.md`
- Studio : `{{dossier_studio}}` (port {{port}})

## Règles de travail
1. **Un jalon à la fois** ; les écarts se notent, le maître tranche à l'essai.
2. **Une seule chaîne moteur** ({{processus_moteur}}). Les autres agents préparent sans moteur, chacun dans son worktree. Enchaînement sans surveillance : {{enchainer}} (réglage `economie.enchainer` ; « non » par défaut : une tâche finie attend l'accord du maître pour la suivante).
3. **Tests au minimum** : compile, tests ciblés, un lancement court. Ce qui se voit à l'écran, le maître le juge : dis-lui quoi regarder.
4. **Roadmap vraie** : « versé » = dans la branche principale avec son critère, preuve = hash ; CHANGELOG à chaque versement.
5. **Point de suivi** par {{nom_assistant}} toutes les {{frequence}} min, seulement si quelque chose a bougé (`attendre.py --point`), et en fin de jalon. Au plus {{agents_max}} agents en même temps.
6. **Versions à essayer** toutes les {{rythme_versions}}, avec un guide « nouveautés, quoi regarder ».
7. **Assets** : image validée d'abord ; un modèle par objet ; plafond de crédits {{plafond}} par jalon.
8. Pas de push ni de publication sans accord ; jamais de clé d'API dans un fichier.
9. Chaque agent écrit sa progression dans `{{dossier_studio}}/progression/<agent>.json`.

## Skills à appeler
- Au début de chaque tâche : `gamedev:router` (s'il est installé).
- Moteur : {{skills_moteur}}
- Genre : {{skill_genre}}
- Disciplines : {{skills_disciplines}}
- Qualité : {{skills_qualite}}
