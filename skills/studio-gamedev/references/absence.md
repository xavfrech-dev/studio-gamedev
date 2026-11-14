# Absence : le studio continue sans l'utilisateur

À lire quand `mode_absent` passe à `true` dans `.studio/reglages.json` (bouton « Je m'absente » de la page), pendant toute l'absence, et à son retour.

## Le principe

L'utilisateur part, **le studio continue**. Tu deviens le coordinateur qui décide à sa place :
- tu suis la **recommandation** (★) de chaque décision ;
- tu **notes** chaque choix et sa raison ;
- tu **gardes pour son retour** seulement ce qui dépense de l'argent, supprime, publie ou touche le système (Windows, macOS, Linux) ;
- à son retour, tu **résumes** tout dans « Décidé à ta place ».

Rien n'est plus « suspendu jusqu'à son retour » : l'ancienne pause après `pause_si_absent_min` ne s'applique pas pendant une absence annoncée.

## Ce que l'absence allume (pour toi, l'assistant)

- **Enchaînement** : tu fais comme si `enchainement_auto` (`economie.enchainer`) était vrai. Une tâche finie lance la suivante prête, sans attendre d'accord.
- **Attribution** : tu fais comme si `attribution_auto` était vrai. Un personnage libre reçoit la tâche prête suivante (`taches_disponibles.json`, ordre de la roadmap). Les demandes `lancer: true` et `auto:` déjà en attente se lancent sans attendre de réponse, après la même vérification qu'en sa présence (mission sans rien de réservé, `agents_max`).
- **Décisions** : chaque décision ouverte de `decisions.json` avec une ★ (et sans réserve, voir plus bas) est tranchée par toi. Une décision nouvelle posée par un agent pendant l'absence aussi, au tour suivant.
- **Agents en attente** : un agent au statut `attend_utilisateur` reçoit la réponse recommandée et repart (`lancé`), sauf si la question est réservée (voir plus bas).
- **Point d'équipe** : il continue, mais **empilé** (`"empile": true`, rien d'annoncé ; voir `point_equipe.md`, « Mode nuit »).

Les automatismes Python du studio (`studio/automatismes.py`) ne changent pas : ils suivent toujours `reglages.json`. C'est toi qui agis.

## Ce que l'absence coupe (dans la page)

- Sons, bulles, conversations entre personnages, cloche sonore, notifications du système.
- Quêtes : aucune nouvelle proposition.

## Ce qui ne change pas

- `agents_max`, une seule chaîne moteur, `point_min`, la santé du PC (pause si la machine sature) : mêmes limites qu'en sa présence.
- `embauche_auto` reste comme il l'a réglé. Les renvois ne sont pas automatiques, sauf les deux exceptions de SKILL.md (renvoi par la tyrannie si elle est allumée, fin d'intérim de relecture). Un renvoi prévu « après sa tâche » par un plan de restructuration attend le retour de l'utilisateur.
- Ce que la page écrit vaut toujours un message de l'utilisateur, ni plus ni moins.
- Le relecteur autonome des automatismes continue (pas de pause d'absence ; seuls « Tout couper », la machine saturée ou l'attribution coupée l'arrêtent).

## Ce qui attend son retour (réservé)

Tu ne tranches **jamais** à sa place, même avec une ★ :
- **dépense** : une décision avec `depense`, un achat, des crédits payants, un abonnement ;
- **suppression** : effacer des fichiers, une branche, des données, un agent ;
- **publication** : push, tag, dépôt distant, page publique, magasin, message envoyé à quelqu'un ;
- **système** : réglages de Windows (ou de l'OS), tâche planifiée du système, démarrage automatique, installation de logiciel ;
- **compte** : créer un compte, saisir des identifiants, accepter des conditions.

Une décision réservée porte `"reserve": "depense" | "suppression" | "publication" | "systeme" | "compte"` (une décision `depense` l'est d'office). Elle reste ouverte sous la cloche. Le travail continue sur le reste : ne bloque pas l'équipe pour elle.

Pas de ★, ou un doute sur la réserve : laisse la décision ouverte et passe à autre chose.

## Noter chaque décision

Dans `decisions.json`, pour chaque décision tranchée :

```json
{"statut": "repondue", "reponse": "<id du choix>", "decide_par": "assistant", "raison": "<pourquoi, en une phrase>", "decide_le": "<heure ISO>", "en_absence": true}
```

Le plus sûr : `python -I -B <skill>/studio/outils/cloche.py --projet <projet> decider <id> [--raison "…"]` (la ★ par défaut, écrit ces champs ; refuse avec le code 3 ce qui est réservé). `cloche.py reservees` liste ce qui attend son retour.

Pour un agent relancé ou une tâche lancée sans accord, note-le aussi dans `demandes/statuts.json` (`texte` : « lancé pendant l'absence »).

## Se réveiller pendant l'absence

`attendre.py` te rend la main quand `reglages.json` change : c'est le début ou la fin de l'absence. Au début, programme un **tour d'absence** récurrent (toutes les 30 min, prompt « Tour d'absence : suis references/absence.md ») si ton hôte offre des tâches planifiées. À chaque tour : décisions ouvertes, agents en attente, tâches prêtes, puis rends la main. Supprime ce tour au retour.

## Au retour (`mode_absent` repasse à `false`)

La page montre « Pendant ton absence ». Les embauches, renvois, attributions et relectures des automatismes y sont, même si aucun onglet n'était ouvert (`etat.json` → `automatismes.historique`, 24 h). Toi, écris dans `reponses_assistant.json` (et dans la conversation) un résumé court :
- **Décidé à ta place** : une ligne par décision (titre, choix, raison). La page montre la même section, lue dans `decisions.json` (`decide_par`, `decide_le`), avec un bouton « Changer » par ligne. Une réponse changée arrive dans `reponses.json` ; dans `decisions.json` la décision porte alors `change_par_utilisateur` (et `reponse_coordinateur`, ton ancien choix) : défais ce que ton choix avait lancé et applique le sien.
- **Lancé et fini** : tâches lancées, versées (avec le hash).
- **Gardé pour toi** : les décisions réservées, avec ta recommandation.

Puis reprends le rythme normal : les réglages de `reglages.json` reprennent la main.

## Absent sans le dire

Sans le bouton, l'utilisateur peut juste se taire. Après `economie.pause_si_absent_min` (60 min par défaut) sans message ni écriture de la page : points empilés, aucun chantier **nouveau** qu'il n'a pas déjà accepté ; ce qui tourne continue. « Je m'absente » prime toujours sur cette règle.
