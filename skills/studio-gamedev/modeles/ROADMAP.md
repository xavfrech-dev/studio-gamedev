# {{nom_projet}} : roadmap

<!-- Générée à la fin du questionnaire (étape obligatoire) à partir de .studio/reponses_questionnaire.json.
     Jumelle de .studio/roadmap.json (lue par le studio) : mêmes jalons, mêmes tâches, mis à jour ensemble.
     Generated at the end of the questionnaire; twin of .studio/roadmap.json. -->

## 1.1 État réel

Jalon en cours : **{{jalon_en_cours}}** — {{fait}} / {{total}} tâches versées · niveau du studio {{niveau}} ({{xp}} XP) · succès {{succes_gagnes}} / {{succes_total}}.

| Tâche | Titre | Critère de « fait » | Poste | Moteur ? | Estim. (h) | Dépend de | Statut | Preuve |
|---|---|---|---|---|---|---|---|---|
| J0-01 | Questionnaire et documents | GDD, roadmap et décisions écrits | Direction | non | 1 | — | versé | {{hash}} |
| J0-02 | Studio en mode travail | page du studio ouverte, postes visibles | Direction | non | 0,5 | J0-01 | à faire | |
| J1-01 | {{titre}} | {{critere}} | {{poste}} | oui | {{h}} | J0-01 | à faire | |

Statuts : `à faire`, `en cours`, `prêt` (préparé sans moteur), `versé` (dans la branche principale, critère rempli), `écart noté` (dans `roadmap.json` : `a_faire`, `en_cours`, `pret`, `verse`, `ecart`).

## 1.2 Programme

Rythme : {{heures_par_semaine}} h par semaine à partir du {{debut}} (réponse « temps disponible »).

| Jalon | But | Tâches | Estimation (h) | Dépend de | Fin visée | Succès débloqué |
|---|---|---|---|---|---|---|
| J0 | Cadrage | 2 | 1,5 | — | {{date}} | {{succes_j0}} |
| J1 | Prototype jouable | {{n}} | {{h}} | J0 | {{date}} | {{succes_j1}} |
| J2 | Boucle centrale | {{n}} | {{h}} | J1 | {{date}} | {{succes_j2}} |
| J3 | Contenu | {{n}} | {{h}} | J2 | {{date}} | {{succes_j3}} |
| J4 | Finition | {{n}} | {{h}} | J3 | {{date}} | {{succes_j4}} |
| J5 | Sortie | {{n}} | {{h}} | J4 | {{date}} | {{succes_j5}} |
| | **Total** | {{n}} | {{h}} | | {{date}} | {{succes_final}} |

## 2. Détail des jalons

### J1 : Prototype jouable

- **But** : {{but}}
- **Fini quand** : on peut {{verbe}} pendant 1 minute sans bug bloquant.
- **Dépend de** : J0.
- **Succès** : « {{titre_succes}} » — {{description_succes}}.
- **Tirée des réponses** : {{cles_du_questionnaire}} (les réponses « ? à confirmer » donnent une tâche « Confirmer : … »).

| Tâche | Titre | Critère de « fait » | Poste | Moteur ? | Estim. (h) | Dépend de |
|---|---|---|---|---|---|---|
| J1-01 | {{titre}} | {{critere}} | {{poste}} | oui | {{h}} | J0-01 |

Écarts notés : aucun.

<!-- Une section par jalon, même forme. -->
