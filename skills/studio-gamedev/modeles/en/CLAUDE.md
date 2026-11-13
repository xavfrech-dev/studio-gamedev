# {{nom_projet}}

{{pitch_court}}

- Engine: {{moteur}} {{version}} ({{langage}})
- Build: `{{commande_build}}`
- Tests: `{{commande_tests}}`
- Short run: `{{commande_lancement}}`
- Heavy data outside the repository: `{{dossier_donnees}}`
- Documents: `docs/GDD.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md`, `docs/CHANGELOG.md`
- Studio: `{{dossier_studio}}` (port {{port}})

## Working rules
1. **One milestone at a time**; deviations are noted, the boss decides by playing.
2. **A single engine chain** ({{processus_moteur}}). Other agents prepare without the engine, each in its own worktree. Unattended chaining: {{enchainer}} (setting `economie.enchainer`; "no" by default: a finished task waits for the boss's go-ahead before the next one).
3. **Minimal tests**: build, targeted tests, one short run. What shows on screen, the boss judges: tell them what to look at.
4. **Honest roadmap**: "merged" = in the main branch with its criterion met, proof = hash; CHANGELOG at each merge.
5. **Status report** by {{nom_assistant}} every {{frequence}} min, only if something moved (`attendre.py --point`), and at the end of a milestone. At most {{agents_max}} agents at once.
6. **Builds to try** every {{rythme_versions}}, with a "what's new, what to look at" guide.
7. **Assets**: image approved first; one model per object; credit cap {{plafond}} per milestone.
8. No push or release without approval; never an API key in a file.
9. Each agent writes its progress to `{{dossier_studio}}/progression/<agent>.json`.

## Skills to call
- At the start of each task: `gamedev:router` (if installed).
- Engine: {{skills_moteur}}
- Genre: {{skill_genre}}
- Disciplines: {{skills_disciplines}}
- Quality: {{skills_qualite}}
