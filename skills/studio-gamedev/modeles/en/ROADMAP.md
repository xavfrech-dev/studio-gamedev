# {{nom_projet}}: roadmap

<!-- Generated at the end of the questionnaire (mandatory step) from .studio/reponses_questionnaire.json.
     Twin of .studio/roadmap.json (read by the studio): same milestones, same tasks, updated together. -->

## 1.1 Current state

Current milestone: **{{jalon_en_cours}}** — {{fait}} / {{total}} tasks merged · studio level {{niveau}} ({{xp}} XP) · achievements {{succes_gagnes}} / {{succes_total}}.

| Task | Title | "Done" criterion | Desk | Engine? | Est. (h) | Depends on | Status | Proof |
|---|---|---|---|---|---|---|---|---|
| J0-01 | Questionnaire and documents | GDD, roadmap and decisions written | Direction | no | 1 | — | merged | {{hash}} |
| J0-02 | Studio in work mode | studio page open, desks visible | Direction | no | 0.5 | J0-01 | to do | |
| J1-01 | {{titre}} | {{critere}} | {{poste}} | yes | {{h}} | J0-01 | to do | |

Statuses: `to do`, `in progress`, `ready` (prepared without the engine), `merged` (in the main branch, criterion met), `deviation noted` (in `roadmap.json`: `a_faire`, `en_cours`, `pret`, `verse`, `ecart`).

## 1.2 Schedule

Pace: {{heures_par_semaine}} h per week starting {{debut}} ("available time" answer).

| Milestone | Goal | Tasks | Estimate (h) | Depends on | Target end | Achievement unlocked |
|---|---|---|---|---|---|---|
| J0 | Framing | 2 | 1.5 | — | {{date}} | {{succes_j0}} |
| J1 | Playable prototype | {{n}} | {{h}} | J0 | {{date}} | {{succes_j1}} |
| J2 | Core loop | {{n}} | {{h}} | J1 | {{date}} | {{succes_j2}} |
| J3 | Content | {{n}} | {{h}} | J2 | {{date}} | {{succes_j3}} |
| J4 | Polish | {{n}} | {{h}} | J3 | {{date}} | {{succes_j4}} |
| J5 | Release | {{n}} | {{h}} | J4 | {{date}} | {{succes_j5}} |
| | **Total** | {{n}} | {{h}} | | {{date}} | {{succes_final}} |

## 2. Milestone details

### J1: Playable prototype

- **Goal**: {{but}}
- **Done when**: you can {{verbe}} for 1 minute without a blocking bug.
- **Depends on**: J0.
- **Achievement**: "{{titre_succes}}" — {{description_succes}}.
- **Taken from the answers**: {{cles_du_questionnaire}} ("? to confirm" answers give a "Confirm: …" task).

| Task | Title | "Done" criterion | Desk | Engine? | Est. (h) | Depends on |
|---|---|---|---|---|---|---|
| J1-01 | {{titre}} | {{critere}} | {{poste}} | yes | {{h}} | J0-01 |

Deviations noted: none.

<!-- One section per milestone, same shape. -->

Ranks (`roadmap.json` → `niveau.rangs`, in the project language): 1 Garage, 5 Neighborhood workshop, 10 Indie studio, 16 AA studio, 24 AAA studio.
