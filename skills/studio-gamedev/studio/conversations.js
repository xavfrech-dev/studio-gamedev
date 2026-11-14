/* studio/conversations.js : les petites conversations du bureau, fabriquées à partir de l'état réel du studio.
   Sources : ce que la page a déjà chargé (postes et leur progression, roadmap, décisions, git, santé du PC, mur
   d'images, recrues) ; aucun appel réseau. Ce qui vient de etat.json (git, santé, version 1, images) n'est cité que si
   l'alimentation est à jour (moins d'une minute). Entre deux rafraîchissements, observer() compare l'état et range les
   changements (tâche finie, prête, versée, commencée, pourcentage qui saute, étape, blocage, commit, décision, jalon,
   embauche, départ, compile, santé, nouvelle image) dans une file prioritaire ; tic() joue tout de suite un événement
   important, alterne les événements ordinaires avec un bavardage d'ambiance tiré de ce qui est vrai à cet instant, et
   espace les échanges d'un même type (pas plus d'un « % » toutes les 3 min). Aucune phrase identique avant 30 min, aucun
   gabarit rejoué avant 20 min tant qu'il en reste d'autres, sujets et personnages en rotation. Chaque gabarit existe en
   français et en anglais ; un titre dont la langue (la sienne, sinon celle de l'ensemble du projet) est l'autre langue
   n'est pas cité, un titre sans langue décidable (nom propre) l'est. Un gabarit n'est choisi que si toutes ses données
   existent : jamais de fait inventé (« versée » seulement quand la roadmap le dit, « fini » seulement à 100 % ou à l'état
   fini, compile cassée seulement si le texte de l'agent le dit avec un mot d'état précis, temps restant seulement s'il va
   avec le %). Essai sans navigateur : node studio/outils/essai_conversations.js. */
(function () {
  'use strict';
  const MIN = 60000, MEMOIRE = 30 * MIN;
  const REELS = new Set(['tache', 'pct', 'pct0', 'reste', 'suite', 'etape', 'etape0', 'raison', 'attente', 'outil', 'role', 'mission',
    'tache2', 'pct2', 'v1', 'jalon', 'jpct', 'jalon2', 'jreste', 'faites', 'total', 'commit', 'heure_c', 'nbc', 'ncj', 'dec', 'nbd_d',
    'nbp', 'nbt_t', 'tdispo', 'cpu', 'mem', 'alerte', 'image', 'parti', 'id', 'saut', 'tacheB', 'pctB']);
  // données « nommées » (un titre, un commit, une décision…), plus strictes qu'un simple chiffre
  const NOMMEES = new Set(['tache', 'tache2', 'suite', 'etape', 'etape0', 'raison', 'attente', 'commit', 'dec', 'jalon', 'jalon2', 'image', 'id', 'parti', 'role', 'mission', 'outil', 'tacheB']);
  const OUTILS = ['Unreal', 'Unity', 'Godot', 'Blender', 'Tripo', 'Nanite', 'Niagara', 'Substance', 'Houdini', 'Krita', 'Aseprite', 'Audacity',
    'ElevenLabs', 'FMOD', 'Wwise', 'Photoshop', 'GIMP', 'Bevy', 'Phaser', 'Roblox Studio', 'Defold', 'Pygame', 'LÖVE'];
  const METIERS = [['direction', /direction|\bchef|\blead\b|coordin|product/], ['relecture', /relect|review|\bqa\b|qualit|testeur|tester\b/],
    ['faune', /faune|wildlife|cr[eé]ature|animal|comportement|behavio/], ['son', /\bsons?\b|audio|sound|musi|bruitage|eleven|fmod|wwise/],
    ['modele3d', /blender|\b3d\b|mod[eé]l|nanite|mesh|maillage|tripo|houdini/], ['level', /level|niveau|monde|world|carte|terrain|v[eé]g[eé]t|environ|d[eé]cor/],
    ['narration', /narr|dialog|qu[eê]te|quest|[eé]criture|writ|histoire|story/], ['art', /\bart\b|\bda\b|concept|illustr|texture|interface|\bui\b|style|krita|aseprite/],
    ['moteur', /moteur|engine|unreal|unity|godot|int[eé]gration|integration|bevy|phaser|roblox|defold|pygame/],
    ['code', /gameplay|\bcode\b|program|d[eé]velop|script|logique|logic/],
    ['studio', /studio|outil|tool|pipeline|skill/]];
  const OBJETS = {
    fr: { direction: 'la roadmap', relecture: 'tes relectures', son: 'tes sons', modele3d: 'tes modèles', faune: 'tes créatures', level: 'ta carte',
      narration: 'tes dialogues', art: 'tes images', moteur: 'ton intégration', code: 'ton code', studio: 'les outils du studio', autre: 'ta tâche' },
    en: { direction: 'the roadmap', relecture: 'your reviews', son: 'your sounds', modele3d: 'your models', faune: 'your creatures', level: 'your map',
      narration: 'your dialogue', art: 'your images', moteur: 'your integration', code: 'your code', studio: 'the studio tools', autre: 'your task' }
  };
  const MOMENTS = { fr: { matin: 'ce matin', midi: 'ce midi', aprem: 'cet après-midi', soir: 'ce soir', nuit: 'cette nuit' },
    en: { matin: 'this morning', midi: 'at lunchtime', aprem: 'this afternoon', soir: 'tonight', nuit: 'at this hour' } };
  const VIDES = { fr: /\s+(de|du|des|la|le|les|l'|d'|à|au|aux|et|ou|en|un|une|pour|par|sur|avec|dans|sans)$/i, en: /\s+(of|the|a|an|and|or|to|for|in|on|with|by|at|from|into)$/i };

  // ---------------------------------------------------------------- gabarits : « a: » le poste concerné, « b: » son interlocuteur, « c: » le chef
  // {x} = donnée (le gabarit est écarté si elle manque) ; {?x} = condition invisible.
  const G = {
    fr: {
      fini: [
        ["a:Et voilà, « {tache} » : terminé !", "b:Bien joué. Tu enchaînes sur quoi ?", "a:Sur « {suite} »."],
        ["a:« {tache} » : 100 %.", "b:Propre ! Je jette un œil quand tu veux.", "c:Beau travail, on note ça."],
        ["b:Tu as le sourire, non ?", "a:« {tache} » vient de passer à 100 %.", "b:Ça mérite un café."],
        ["c:Bravo pour « {tache} » !", "a:Merci ! La version 1 en est à {v1} %."],
        ["a:Fini ! « {tache} » ne bougera plus.", "b:Une ligne de moins sur le tableau."],
        ["b:Alors, « {tache} » ?", "a:Terminé. Prochaine étape : « {suite} ».", "b:Ça s'enchaîne bien."],
        ["a:« {tache} », c'est bouclé.", "b:Pense à demander une relecture avant le versement.", "a:Bien sûr."],
        ["b:Dis donc, « {tache} » à 100 % ? Respect.", "a:Merci ! Je souffle deux minutes."],
        ["a:Je pose les outils : « {tache} », c'est fait.", "c:Bien ! Souffle un peu avant « {suite} »."],
        ["{?relect}b:Je relis « {tache} » ?", "a:Volontiers, c'est fini de mon côté."],
        ["a:Tu peux cocher « {tache} » : 100 %.", "c:C'est noté, merci."],
        ["a:« {tache} » : terminé.", "b:Bravo ! Moi, « {tacheB} » est à {pctB} %."],
      ],
      verse: [
        ["c:La tâche « {tache} » est versée !", "a:Enfin dans le jeu.", "b:Le jalon « {jalon} » passe à {jpct} %."],
        ["a:{id} versée : « {tache} ».", "b:Bravo ! Ça fait {faites} sur {total}."],
        ["b:Tu as vu ? « {tache} » est dans le jeu.", "a:Oui, la tâche vient d'être versée.", "b:On sent le jalon « {jalon} » avancer."],
        ["{?proprio}c:Versement fait : « {tache} ».", "a:Je peux passer à la suite, alors."],
        ["a:« {tache} » : versée, c'est officiel.", "b:« {jalon} » en est à {jpct} %.", "a:On tient le rythme."],
        ["b:Une de plus : « {tache} ».", "c:{faites} sur {total}, on avance bien."],
        ["{?proprio}a:Ma tâche « {tache} » est versée.", "b:Ça se fête ? Café ?", "a:Café."],
        ["c:Je coche {id} sur la roadmap.", "b:« {tache} », c'est ça ?", "c:Oui, versée."],
        ["a:{id} vient d'entrer dans le jeu.", "b:« {tache} » ? Enfin !"],
        ["b:La roadmap bouge : {id} est versée.", "a:Le jalon « {jalon} » est maintenant à {jpct} %."],
        ["b:« {tache} » est versée ?", "a:Oui, {id} est dans le jeu.", "b:Ça me motive pour « {tacheB} »."],
      ],
      pret: [
        ["a:La tâche « {tache} » est prête à verser.", "b:Je regarde ça dès que je peux."],
        ["b:La tâche « {tache} » est prête ?", "a:Oui, il ne manque que le versement."],
        ["a:« {tache} » attend son versement.", "c:Parfait. Tu peux souffler un peu."],
        ["b:Statut « prête » pour « {tache} », je vois ça.", "a:Je croise les doigts pour le versement."],
        ["{?proprio}a:« {tache} » : prête !", "b:Tu as pensé aux cas limites ?", "a:Je repasse dessus si on me le demande."],
        ["c:La tâche {id} est prête.", "a:Oui, « {tache} », il reste juste à la verser."],
        ["b:Ça sent le versement, « {tache} ».", "a:La tâche est prête, oui.", "b:Tant mieux, « {jalon} » en a besoin."],
        ["{?proprio}a:Je passe « {tache} » en prête.", "b:Une de moins sur ta liste."],
        ["{?relect}b:Je prends « {tache} » en relecture ?", "a:Oui, la tâche est prête."],
        ["a:{id} passe en « prête ».", "b:Le jalon « {jalon} » est à {jpct} % en attendant."],
        ["b:Qu'est-ce qui attend un versement ?", "a:{id} : « {tache} »."],
        ["a:{id} est prête : « {tache} ».", "b:Je la regarde après « {tacheB} »."],
      ],
      commence: [
        ["{?proprio}a:Je commence « {tache} ».", "b:Bon courage ! C'est pour « {jalon} » ?", "a:Exactement."],
        ["{?proprio}b:Nouvelle tâche ?", "a:Oui, « {tache} » démarre."],
        ["{?proprio}a:On attaque « {tache} ».", "c:Parfait, dis-moi si ça coince."],
        ["{?proprio}b:C'est toi qui prends « {tache} » ?", "a:Oui, c'est parti."],
        ["a:{id} en cours : « {tache} ».", "b:Le jalon « {jalon} » se remplit."],
        ["{?proprio}c:« {tache} » démarre.", "a:J'ouvre mes notes et j'y vais."],
        ["{?proprio}a:Hop, « {tache} » passe en cours.", "b:Tu veux un coup de main pour démarrer ?", "a:Ça ira, merci !"],
        ["{?proprio}b:Tiens, « {tache} » a commencé.", "a:Oui, je m'y mets maintenant."],
        ["b:{id} vient de passer en cours.", "a:« {tache} », pour le jalon « {jalon} »."],
        ["c:Qui s'occupe de {id} ?", "a:C'est lancé : « {tache} »."],
        ["{?proprio}a:Premier pas sur « {tache} ».", "b:Le plus dur, c'est de commencer."],
        ["a:{id} démarre : « {tache} ».", "b:Et moi je continue « {tacheB} »."],
      ],
      pct: [
        ["b:Ça avance, « {tache} » ?", "a:De {pct0} à {pct} % depuis tout à l'heure."],
        ["b:Tu en es où ?", "a:{pct} % sur « {tache} ».", "b:Belle progression."],
        ["a:{pct} % ! « {tache} » prend forme.", "b:Il reste combien ?", "a:À peu près {reste}."],
        ["b:Je vois ta barre à {pct} %.", "a:Oui, « {tache} » avance bien."],
        ["a:Encore un palier : {pct} % sur « {tache} ».", "c:Continue comme ça."],
        ["b:Tu étais à {pct0} % tout à l'heure, non ?", "a:Oui, maintenant {pct} %.", "b:Joli bond."],
        ["a:« {tache} » : {pct} %, il me reste environ {reste}.", "b:Ça se tient."],
        ["b:{pct} %, tu accélères ?", "a:Un peu : {saut} points de plus sur « {tache} »."],
        ["c:Belle remontée, {pct0} → {pct} %.", "a:Merci, je continue sur « {tache} »."],
        ["a:Plus que {reste} sur « {tache} », d'après ma barre.", "b:Tu tiens le bon bout."],
        ["b:{saut} points d'un coup ?", "a:Oui, « {tache} » est à {pct} %."],
        ["{?moitie}a:Passé la moitié : {pct} % sur « {tache} ».", "b:Le reste va filer."],
        ["c:Où en est « {tache} » ?", "a:{pct} %, il reste environ {reste}."],
        ["a:{pct} % sur « {tache} ».", "b:Pas mal ! Moi, « {tacheB} » est à {pctB} %."],
        ["b:{saut} points de plus sur « {tache} » ?", "a:Oui, {pct} % maintenant."],
      ],
      etape: [
        ["b:Nouvelle étape ?", "a:Oui : « {etape} »."],
        ["a:Je passe de « {etape0} » à « {etape} ».", "b:Bien, tu avances."],
        ["a:Je passe à « {etape} ».", "b:Ça te prendra longtemps ?", "a:On verra, mais ça part bien."],
        ["b:Tu changes de cap ?", "a:Juste l'étape suivante : « {etape} »."],
        ["a:Étape suivante : « {etape} ».", "c:Parfait, garde ce rythme."],
        ["b:C'est quoi, maintenant ?", "a:« {etape} ».", "b:Ah, la partie amusante."],
        ["a:« {etape0} », c'est derrière moi.", "b:Et devant ?", "a:« {etape} »."],
        ["a:Je m'attaque à « {etape} ».", "b:Dis-moi si tu veux un regard extérieur."],
        ["c:Tu changes d'étape ?", "a:Oui, maintenant « {etape} »."],
        ["a:Étape « {etape} ».", "b:Moi, toujours « {tacheB} »."],
      ],
      bloque: [
        ["b:Ça coince ?", "a:Oui, sur « {raison} ».", "b:Je regarde avec toi si tu veux."],
        ["a:Je suis à l'arrêt : « {raison} ».", "c:Je vois ça, je cherche ce qui manque."],
        ["b:Ta barre est rouge…", "a:« {raison} ». J'attends que ça se débloque."],
        ["a:Ma tâche est bloquée : « {raison} ».", "b:Courage, ça arrive à tout le monde."],
        ["c:Qu'est-ce qui bloque ?", "a:« {raison} ».", "c:Je le note."],
        ["b:Besoin d'aide ?", "a:Peut-être : « {raison} »."],
        ["a:Pause forcée : « {raison} ».", "b:Profites-en pour un café."],
        ["b:Toujours à l'arrêt ?", "a:Oui, « {raison} ».", "b:On trouvera."],
        ["b:Ça coince ?", "a:Oui : « {raison} ».", "b:Je finis « {tacheB} » et je viens voir."],
        ["a:Bloqué : « {raison} ».", "b:Je suis sur « {tacheB} », mais appelle-moi si besoin."],
      ],
      debloque: [
        ["a:Ça repart !", "b:Super, « {tache} » reprend ?", "a:Oui, enfin."],
        ["a:Débloqué ! Je reprends « {tache} ».", "b:Bonne nouvelle."],
        ["c:Plus de blocage ?", "a:Non, « {tache} » avance de nouveau."],
        ["a:La voie est libre pour « {tache} ».", "b:Fonce !"],
        ["b:Ta barre est repassée au vert.", "a:Oui, je reprends « {tache} »."],
        ["a:Enfin ! Je peux continuer « {tache} ».", "c:Parfait, on rattrape le temps perdu."],
        ["b:Tu as trouvé la solution ?", "a:Ça s'est débloqué, je reprends « {tache} »."],
        ["a:Reprise de « {tache} ».", "b:Ça fait plaisir à voir."],
        ["a:Je reprends « {tache} » : {pct} %.", "b:Bien. Moi, je continue « {tacheB} »."],
      ],
      commit: [
        ["a:Nouveau commit : « {commit} ».", "b:Je l'ai vu passer."],
        ["b:Tu as vu le dernier commit ?", "a:« {commit} », à {heure_c}."],
        ["a:{nbc} nouveaux commits, dont « {commit} ».", "b:Ça bouge, aujourd'hui."],
        ["a:« {commit} » vient d'arriver dans le dépôt.", "b:Je mets mon côté à jour.", "a:Bonne idée."],
        ["b:Commit de {heure_c} : « {commit} ».", "c:Le dépôt avance."],
        ["a:Le dépôt bouge : « {commit} ».", "b:Pourvu que la compile suive !"],
        ["c:Un commit de plus : « {commit} ».", "a:Petit à petit…", "b:… le jeu fait son nid."],
        ["b:« {commit} », c'est passé à quelle heure ?", "a:{heure_c}."],
        ["a:À {heure_c}, « {commit} ».", "b:Je le récupère tout de suite."],
        ["a:« {commit} » est dans le dépôt.", "b:Je l'intègre à « {tacheB} »."],
      ],
      decision: [
        ["a:Une décision attend {maitre} : « {dec} ».", "b:On avance sur le reste en attendant."],
        ["b:Tu as vu la cloche ?", "a:Oui : « {dec} ».", "b:J'ai hâte de voir la réponse."],
        ["a:« {dec} » : à {maitre} de trancher.", "b:Je parie sur la recommandation."],
        ["c:Nouvelle question pour {maitre} : « {dec} ».", "a:On verra à la réponse."],
        ["b:La cloche sonne : « {dec} ».", "a:Bonne question, celle-là."],
        ["a:{nbd_d} en attente maintenant.", "b:Dont « {dec} »."],
        ["b:Il faudra l'avis de {maitre} sur « {dec} ».", "a:Oui, la cloche est là pour ça."],
        ["a:« {dec} »… Moi j'ai mon idée.", "b:Garde-la pour {maitre} !"],
      ],
      jalon: [
        ["c:Le jalon « {jalon} » est bouclé !", "a:Plus rien en suspens ?", "c:Plus rien."],
        ["a:« {jalon} » : terminé !", "b:On passe au suivant : « {jalon2} »."],
        ["b:Champagne ? « {jalon} » est fini.", "a:Un café suffira."],
        ["c:Jalon « {jalon} » fermé.", "b:{v1} % de la version 1, on y croit."],
        ["a:On vient de fermer « {jalon} ».", "b:Il en reste combien ?", "a:{jreste}."],
        ["b:« {jalon} » derrière nous.", "c:Prochain cap : « {jalon2} »."],
        ["a:Le mur de la roadmap passe au vert pour « {jalon} ».", "b:Ça fait du bien de le voir."],
        ["c:Bravo à toute l'équipe pour « {jalon} ».", "a:Merci ! On attaque « {jalon2} » ?"],
      ],
      embauche: [
        ["b:Bienvenue ! Tu arrives pour quoi ?", "a:{role}.", "b:Parfait, on en avait besoin."],
        ["a:Bonjour ! Je viens pour : {role}.", "b:Salut ! Ton bureau est prêt."],
        ["c:Je vous présente {A} : {role}.", "b:Bienvenue dans l'équipe !"],
        ["b:Un nouveau bureau est occupé.", "a:C'est moi ! {role}."],
        ["b:Bienvenue {A}. Tu commences par quoi ?", "a:{mission}."],
        ["a:Premier jour au studio !", "b:Tu verras, on est bien ici. Tu fais quoi ?", "a:{role}."],
        ["b:On s'agrandit : {nbp} postes maintenant.", "a:Et c'est moi, la nouvelle recrue."],
        ["c:Nouvelle recrue : {A}.", "a:Bonjour ! Je m'occupe de : {role}.", "b:Bienvenue !"],
        ["a:Bonjour ! {role}.", "b:Bienvenue ! Moi, je suis sur « {tacheB} »."],
      ],
      renvoi: [
        ["a:{parti} a rangé son bureau.", "b:Ça fait un vide."],
        ["b:Tu as vu ? {parti} a quitté le studio.", "a:On reprendra le relais si besoin."],
        ["a:Le bureau de {parti} est libre maintenant.", "b:On sera {nbp} pour la suite."],
        ["c:{parti} nous quitte.", "a:Merci pour le travail fait."],
        ["b:Plus que {nbp} postes.", "a:Depuis le départ de {parti}, oui."],
        ["a:Au revoir {parti} !", "b:Bonne route."],
        ["b:Qui reprend ce que faisait {parti} ?", "c:On verra à la prochaine attribution."],
        ["a:Le carton de {parti} vient de passer la porte.", "b:Pas la plante, j'espère."],
      ],
      sante: [
        ["a:Le PC souffle fort.", "b:Oui : {alerte}."],
        ["b:Ça rame un peu, non ?", "a:{alerte}. On espace les tâches lourdes."],
        ["c:Attention, {alerte}.", "a:Je ferme ce qui ne sert pas."],
        ["a:{alerte}…", "b:On attend que ça redescende avant de relancer quoi que ce soit."],
        ["b:Le ventilateur chante.", "a:Normal : {alerte}."],
        ["a:La machine sature : {alerte}.", "b:Pause café forcée, alors."],
        ["c:Santé du PC à l'orange : {alerte}.", "b:On lève le pied."],
        ["a:Tu sens la chaleur du PC ?", "b:Oui, {alerte}.", "a:Un outil lourd à la fois."],
      ],
      sante_ok: [
        ["a:Le PC respire de nouveau.", "b:Processeur à {cpu} %, ça va mieux."],
        ["b:Plus d'alerte machine.", "a:Mémoire à {mem} %, on peut relancer."],
        ["c:La santé du PC est revenue au vert.", "a:Processeur à {cpu} %, parfait."],
        ["a:Fini la surchauffe : {cpu} % de processeur.", "b:On reprend le rythme normal."],
        ["b:Le ventilateur s'est calmé.", "a:Oui, {mem} % de mémoire seulement."],
        ["a:La machine a retrouvé son souffle.", "c:{cpu} % de processeur, on peut relancer les tâches lourdes."],
        ["b:Tu sens ? Le PC ne chauffe plus.", "a:{cpu} % de processeur, ça change tout."],
        ["c:Alerte machine levée.", "b:Mémoire à {mem} %, ça respire."],
      ],
      compile_ok: [
        ["a:Compile verte !", "b:Ça passe ?", "a:Oui : « {tache} »."],
        ["b:Tu souris ?", "a:« {tache} ». Tout est vert."],
        ["a:« {tache} » : la compile passe.", "c:Excellent."],
        ["c:La compile est verte ?", "a:Oui, « {tache} »."],
        ["a:Pas une erreur : « {tache} ».", "b:Note la date, c'est historique."],
        ["b:J'ai vu passer « {tache} ».", "a:Oui, ça compile."],
        ["a:Vert de chez vert : « {tache} ».", "b:On peut tester, alors ?", "a:On peut tester."],
        ["a:« {tache} », tout passe !", "b:Bravo, on peut avancer."],
      ],
      compile_ko: [
        ["a:Aïe, la compile casse.", "b:Sur quoi ?", "a:« {tache} »."],
        ["b:Ça a l'air rouge chez toi.", "a:« {tache} ». Je cherche."],
        ["a:« {tache} »… raté pour cette fois.", "c:Prends le temps de lire l'erreur."],
        ["c:La compile échoue ?", "a:Oui : « {tache} »."],
        ["a:Rouge : « {tache} ».", "b:Courage, on a tous vécu ça."],
        ["b:Besoin d'un deuxième regard ?", "a:Volontiers : « {tache} »."],
        ["a:La compile ne passe pas : « {tache} ».", "b:Café, puis on relit ensemble ?"],
        ["a:« {tache} », ça casse.", "c:Pas de panique, on corrige avant de verser."],
      ],
      image: [
        ["a:Nouvelle image au mur : « {image} ».", "b:Elle rend bien !"],
        ["{?auteur}b:Tu as accroché « {image} » ?", "a:Oui, toute fraîche."],
        ["a:Regardez le mur : « {image} ».", "c:Ça donne envie de jouer."],
        ["b:« {image} », c'est nouveau ?", "a:Tout juste sorti."],
        ["{?auteur}a:J'ai ajouté « {image} » au mur.", "b:Le jeu prend des couleurs."],
        ["{?auteur}c:Belle image, « {image} ».", "a:Merci ! Il y en aura d'autres."],
        ["b:Le mur s'enrichit : « {image} ».", "a:On voit enfin à quoi ça ressemble."],
        ["a:« {image} » est au mur.", "b:Je la mets en fond d'écran.", "a:Flatteur !"],
        ["a:« {image} » est au mur.", "b:Ça va m'aider pour « {tacheB} »."],
      ],
      travail: [
        ["b:Tu en es où ?", "a:« {tache} », {pct} %."],
        ["b:Ça avance, « {tache} » ?", "a:{pct} %, il me reste environ {reste}."],
        ["b:Besoin d'un coup de main ?", "a:Ça va, « {tache} » avance : {pct} %."],
        ["a:La tête dans « {tache} ».", "b:On ne te dérange pas, alors."],
        ["b:Toujours sur « {tache} » ?", "a:Toujours. {pct} % pour l'instant."],
        ["a:Encore {reste} sur « {tache} », à peu près.", "b:Courage !"],
        ["b:Tu travailles dans {outil} ?", "a:Oui, pour « {tache} »."],
        ["b:Ça donne quoi, {objet} ?", "a:« {tache} » est à {pct} %."],
        ["a:« {tache} » : {pct} %, ça tient.", "b:Je te laisse, alors."],
        ["c:Tout va bien sur « {tache} » ?", "a:Oui, {pct} % pour l'instant."],
        ["b:Je peux te prendre deux minutes ?", "a:Après « {tache} », il me reste environ {reste}."],
        ["a:Je suis à {pct} %.", "b:Sur « {tache} » ? Pas mal."],
        ["b:Tu es sur quoi, là ?", "a:« {tache} »."],
        ["b:Ça avance de ton côté ?", "a:« {tache} », {pct} %. Et toi ?", "b:« {tacheB} », {pctB} %."],
        ["a:« {tache} » : {pct} %.", "b:Moi, « {tacheB} »."],
      ],
      duo: [
        ["a:J'en suis à {pct} % sur « {tache} ». Et toi ?", "b:{pct2} % sur « {tache2} »."],
        ["a:Chacun son front : « {tache} » pour moi.", "b:Et « {tache2} » pour moi."],
        ["b:Tu es à combien ?", "a:{pct} %. Et toi, « {tache2} » ?"],
        ["a:Je finis « {tache} » et je viens t'aider.", "b:Avec plaisir, « {tache2} » me donne du fil à retordre."],
        ["b:Pause ?", "a:Pas tout de suite, « {tache} » est à {pct} %."],
        ["a:Concentration maximale sur « {tache} ».", "b:Pareil pour « {tache2} »."],
        ["{?devant}a:Ta barre avance plus vite que la mienne.", "b:{pct2} % contre {pct} % ? Ça va s'équilibrer."],
        ["b:On fait la course ?", "a:« {tache} » contre « {tache2} », d'accord !"],
        ["a:{pct} % ici, sur « {tache} ».", "b:{pct2} % de mon côté."],
        ["b:Tu me prêtes ton écran deux secondes ?", "a:Après « {tache} », promis."],
      ],
      attente: [
        ["b:Tu attends quoi ?", "a:J'attends {attente}."],
        ["a:Je patiente : j'attends {attente}.", "b:Courage."],
        ["b:Ta tâche est en pause ?", "a:Oui, j'attends {attente}.", "b:Je te préviens si je vois quelque chose."],
        ["a:Rien à faire tant que je n'ai pas {attente}.", "b:Café en attendant ?"],
        ["c:Tout va bien ?", "a:J'attends {attente}, c'est tout."],
        ["b:Encore en attente ?", "a:Oui, toujours {attente}."],
        ["a:Si quelqu'un voit passer {attente}, je prends.", "b:Je garde l'œil ouvert."],
        ["b:Tu n'as pas l'air de bouger.", "a:J'attends {attente}."],
      ],
      suite: [
        ["b:Et après, tu fais quoi ?", "a:« {suite} »."],
        ["a:Prochaine tâche : « {suite} ».", "b:Ça a l'air sympa."],
        ["b:Ta liste, ça donne quoi ?", "a:Ensuite, « {suite} »."],
        ["a:J'ai déjà « {suite} » sur ma liste.", "b:Tu ne chômes pas."],
        ["c:Tu sais ce qui t'attend ?", "a:Oui : « {suite} »."],
        ["b:Il te reste quoi ?", "a:« {suite} », pour commencer."],
        ["a:« {suite} » arrive bientôt.", "b:Dis-moi si tu veux en parler."],
        ["b:Prochaine étape ?", "a:« {suite} ».", "b:Bon programme."],
      ],
      libre: [
        ["a:Pause café ?", "b:Oui. La version 1 est à {v1} %, on l'a méritée."],
        ["a:Tu as vu le dernier commit ?", "b:« {commit} », oui."],
        ["a:{nbt_t} au travail, et nous au café.", "b:Notre tour viendra."],
        ["a:Il reste {tdispo}.", "b:On va bien en trouver une pour nous."],
        ["b:On attend la suite du jalon « {jalon} ».", "a:En attendant, café."],
        ["a:Rien sur mon bureau pour l'instant.", "b:Pareil. Le jalon « {jalon} » est à {jpct} %."],
        ["b:On n'a rien devant nous.", "a:La roadmap dit {v1} %, ça va venir."],
        ["a:Un café ?", "b:Avec plaisir. Tu as vu « {commit} » ?"],
      ],
      roadmap: [
        ["a:La version 1 est à {v1} %.", "b:Et le jalon « {jalon} » à {jpct} %."],
        ["b:On en est où, globalement ?", "a:{v1} % de la version 1."],
        ["a:« {jalon} » : {jpct} %.", "b:On tient le bon bout."],
        ["c:{faites} sur {total}.", "a:On avance, pas à pas."],
        ["b:Tu as regardé la roadmap ?", "a:Oui, {v1} %. Le jalon en cours : « {jalon} »."],
        ["a:Encore un effort sur « {jalon} ».", "b:Il est à {jpct} %, ça vient."],
        ["b:{faites} sur {total}, pas mal.", "a:Et chaque versement compte."],
        ["c:Point roadmap : {v1} %.", "b:Le prochain jalon se rapproche."],
      ],
      attente_decisions: [
        ["a:{nbd_d} en attente pour {maitre}.", "b:Dont « {dec} »."],
        ["b:La cloche attend toujours.", "a:Oui : « {dec} »."],
        ["a:« {dec} », toujours pas tranché.", "b:{maitre} a sûrement d'autres chats à fouetter."],
        ["c:Petit rappel : « {dec} ».", "a:La cloche clignote encore."],
        ["b:On aurait besoin d'une réponse sur « {dec} ».", "a:Ça viendra."],
        ["a:{nbd_d} sous la cloche.", "b:On continue sans, en attendant."],
        ["b:Pour « {dec} », tu crois que {maitre} va choisir quoi ?", "a:Aucune idée, surprise."],
        ["a:Toujours « {dec} » en suspens.", "c:Je le remonterai au prochain point."],
        ["a:« {dec} » attend toujours.", "b:Pas grave, je continue « {tacheB} »."],
      ],
      commits_jour: [
        ["a:{ncj} aujourd'hui.", "b:Le dernier : « {commit} »."],
        ["{?ncj_plus}b:Ça commite beaucoup, aujourd'hui.", "a:{ncj} depuis minuit."],
        ["a:Le dépôt est vivant : {ncj} aujourd'hui.", "b:Et la compile tient ?"],
        ["{?ncj_plus}c:Belle journée : {ncj}.", "a:Dont « {commit} »."],
        ["b:Dernier commit à {heure_c}.", "a:« {commit} », je l'ai vu."],
        ["{?ncj_plus}a:{ncj}, c'est un record ?", "b:Peut-être bien."],
        ["b:Tu as vu « {commit} » ?", "a:Oui, à {heure_c}."],
        ["a:Encore un commit : « {commit} ».", "b:Le dépôt ne dort jamais."],
      ],
      heure: [
        ["a:{moment}, je suis sur « {tache} ».", "b:{remarque}"],
        ["b:{remarque}", "a:Et « {tache} » avance : {pct} %."],
        ["a:{moment}, {nbt_t} au travail.", "b:{remarque}"],
        ["b:{moment}, la version 1 est à {v1} %.", "a:{remarque}"],
        ["a:{remarque}", "b:{moment}, je suis sur « {tache2} »."],
        ["b:Programme de {moment_court} ?", "a:« {tache} »."],
        ["a:{moment}, objectif : « {tache} ».", "b:{remarque}"],
        ["b:{moment}, on vise le jalon « {jalon} ».", "a:{remarque}"],
      ],
      metier: [
        ["b:C'est comment, {objet} ?", "a:Ça avance : « {tache} »."],
        ["a:{outil} et moi, on se comprend aujourd'hui.", "b:Tant mieux pour « {tache} »."],
        ["b:Tu me montres {objet} ?", "a:Bientôt. « {tache} » d'abord."],
        ["a:Mon métier : {role}.", "b:Et en ce moment ?", "a:« {tache} »."],
        ["b:Ça te plaît, {objet} ?", "a:Beaucoup. Surtout « {tache} »."],
        ["a:Aujourd'hui, {outil} pour « {tache} ».", "b:Bon courage avec ça."],
        ["b:Tu as besoin de quoi pour « {tache} » ?", "a:De calme et de café."],
        ["a:{role} : c'est moi.", "b:Et « {tache} », c'est toi aussi ?", "a:Oui."],
        ["{?cat_son}b:Tu as le casque sur les oreilles ?", "a:Oui, « {tache} » s'écoute au calme."],
        ["{?cat_relecture}b:Tu relis quoi, en ce moment ?", "a:« {tache} »."],
        ["{?cat_modele3d}b:Combien de polygones pour « {tache} » ?", "a:Assez pour être joli, pas trop pour le jeu."],
        ["{?cat_faune}b:Tes bêtes se tiennent bien ?", "a:On verra : « {tache} » est à {pct} %."],
        ["{?cat_moteur}b:Le moteur te laisse tranquille ?", "a:Pour l'instant. « {tache} » : {pct} %."],
        ["{?cat_code}b:Ta logique tient debout ?", "a:Les cas simples, oui. « {tache} » : {pct} %."],
        ["{?cat_level}b:Ta carte s'agrandit ?", "a:« {tache} », {pct} %."],
        ["{?cat_art}b:Tu me montres tes croquis ?", "a:Quand « {tache} » aura avancé."],
        ["{?cat_direction}b:La roadmap te donne des cheveux blancs ?", "a:Non : {v1} % de la version 1, ça va."],
        ["{?cat_narration}b:Tu écris quoi, en ce moment ?", "a:« {tache} »."],
        ["{?cat_studio}b:Tu bricoles encore le studio ?", "a:Oui : « {tache} »."],
      ],
      pc: [
        ["a:Le PC tient le coup ?", "b:Processeur à {cpu} %, mémoire à {mem} %."],
        ["b:{cpu} % de processeur, tranquille.", "a:Tant mieux."],
        ["a:Mémoire à {mem} %.", "b:On a de la marge."],
        ["c:Santé du PC : {cpu} % de processeur.", "a:Rien d'inquiétant."],
        ["b:Tu entends le ventilateur ?", "a:À {cpu} %, il est encore sage."],
        ["a:{mem} % de mémoire, ça va.", "b:On peut ouvrir un outil lourd."],
        ["b:La machine va bien ?", "a:{cpu} % de processeur, elle se repose presque."],
        ["a:Processeur à {cpu} %.", "b:Il en a vu d'autres."],
      ],
      nouveau: [
        ["a:Tu as vu « {image} » au mur ?", "b:Oui, ça donne envie de jouer."],
        ["b:« {image} », c'est récent ?", "a:Oui, ça vient d'arriver."],
        ["a:Le mur change : « {image} ».", "b:J'adore."],
        ["c:Jetez un œil à « {image} ».", "b:Superbe."],
        ["b:Le jeu ressemble de plus en plus à quelque chose.", "a:« {image} » en est la preuve."],
        ["a:« {image} » : on voit le progrès.", "b:Carrément."],
        ["b:Qui a fait « {image} » ?", "a:L'équipe, comme toujours."],
        ["a:Petite fierté du jour : « {image} ».", "b:Il y a de quoi."],
      ],
    },
    en: {
      fini: [
        ["a:There we go, “{tache}”: done!", "b:Nice one. What's next for you?", "a:“{suite}”."],
        ["a:“{tache}”: 100 %.", "b:Clean! I'll take a look whenever you want.", "c:Great work, noted."],
        ["b:You look pleased.", "a:“{tache}” just hit 100 %.", "b:That deserves a coffee."],
        ["c:Well done on “{tache}”!", "a:Thanks! Version 1 is at {v1} %."],
        ["a:Done! “{tache}” won't move anymore.", "b:One line less on the board."],
        ["b:So, “{tache}”?", "a:Finished. Next up: “{suite}”.", "b:Smooth."],
        ["a:“{tache}” is wrapped up.", "b:Ask for a review before the merge.", "a:Of course."],
        ["b:Wait, “{tache}” at 100 %? Respect.", "a:Thanks! Taking a two-minute breather."],
        ["a:Tools down: “{tache}” is done.", "c:Good! Breathe a bit before “{suite}”."],
        ["{?relect}b:Shall I review “{tache}”?", "a:Please do, it's finished on my side."],
        ["a:You can tick “{tache}”: 100 %.", "c:Noted, thanks."],
        ["a:“{tache}”: done.", "b:Bravo! “{tacheB}” is at {pctB} % on my side."],
      ],
      verse: [
        ["c:The task “{tache}” is merged!", "a:Finally in the game.", "b:“{jalon}” moves to {jpct} %."],
        ["a:{id} merged: “{tache}”.", "b:Bravo! That's {faites} out of {total}."],
        ["b:Did you see? “{tache}” is in the game.", "a:Yes, the task was just merged.", "b:You can feel “{jalon}” moving."],
        ["{?proprio}c:Merge done: “{tache}”.", "a:Then I can move on."],
        ["a:“{tache}”: merged, it's official.", "b:“{jalon}” is at {jpct} %.", "a:We're keeping pace."],
        ["b:One more: “{tache}”.", "c:{faites} out of {total}, good progress."],
        ["{?proprio}a:My task “{tache}” is merged.", "b:Celebrate? Coffee?", "a:Coffee."],
        ["c:Ticking {id} on the roadmap.", "b:“{tache}”, right?", "c:Yes, merged."],
        ["a:{id} just made it into the game.", "b:“{tache}”? At last!"],
        ["b:The roadmap moves: {id} is merged.", "a:“{jalon}” is now at {jpct} %."],
        ["b:Is “{tache}” merged?", "a:Yes, {id} is in the game.", "b:That motivates me for “{tacheB}”."],
      ],
      pret: [
        ["a:The task “{tache}” is ready to merge.", "b:I'll look at it as soon as I can."],
        ["b:Is the task “{tache}” ready?", "a:Yes, it only needs merging."],
        ["a:“{tache}” is waiting for its merge.", "c:Perfect. Take a breather."],
        ["b:“Ready” status on “{tache}”, I see.", "a:Fingers crossed for the merge."],
        ["{?proprio}a:“{tache}”: ready!", "b:Did you think about edge cases?", "a:I'll go over it again if asked."],
        ["c:Task {id} is ready.", "a:Yes, “{tache}”, it just needs merging."],
        ["b:Smells like a merge, “{tache}”.", "a:The task is ready, yes.", "b:Good, “{jalon}” needs it."],
        ["{?proprio}a:Marking “{tache}” as ready.", "b:One less on your list."],
        ["{?relect}b:Shall I review “{tache}”?", "a:Yes, the task is ready."],
        ["a:{id} moves to “ready”.", "b:“{jalon}” is at {jpct} % meanwhile."],
        ["b:What's waiting for a merge?", "a:{id}: “{tache}”."],
        ["a:{id} is ready: “{tache}”.", "b:I'll look at it after “{tacheB}”."],
      ],
      commence: [
        ["{?proprio}a:Starting “{tache}”.", "b:Good luck! Is it for “{jalon}”?", "a:Exactly."],
        ["{?proprio}b:New task?", "a:Yes, “{tache}” is starting."],
        ["{?proprio}a:Let's tackle “{tache}”.", "c:Great, tell me if it gets stuck."],
        ["{?proprio}b:You're taking “{tache}”?", "a:Yes, here we go."],
        ["a:{id} in progress: “{tache}”.", "b:“{jalon}” is filling up."],
        ["{?proprio}c:“{tache}” is starting.", "a:Opening my notes and off I go."],
        ["{?proprio}a:Right, “{tache}” is in progress.", "b:Want a hand getting started?", "a:I'm fine, thanks!"],
        ["{?proprio}b:Oh, “{tache}” has started.", "a:Yes, getting into it now."],
        ["b:{id} just moved to in progress.", "a:“{tache}”, for “{jalon}”."],
        ["c:Who's on {id}?", "a:It's under way: “{tache}”."],
        ["{?proprio}a:First step on “{tache}”.", "b:Starting is the hardest part."],
        ["a:{id} starts: “{tache}”.", "b:And I'm carrying on with “{tacheB}”."],
      ],
      pct: [
        ["b:How's “{tache}” going?", "a:From {pct0} to {pct} % since earlier."],
        ["b:Where are you at?", "a:{pct} % on “{tache}”.", "b:Nice progress."],
        ["a:{pct} %! “{tache}” is taking shape.", "b:How long left?", "a:About {reste}."],
        ["b:I see your bar at {pct} %.", "a:Yes, “{tache}” is going well."],
        ["a:Another step: {pct} % on “{tache}”.", "c:Keep it up."],
        ["b:Weren't you at {pct0} % earlier?", "a:Yes, now {pct} %.", "b:Nice jump."],
        ["a:“{tache}”: {pct} %, about {reste} left.", "b:Sounds right."],
        ["b:{pct} %, speeding up?", "a:A bit: {saut} more points on “{tache}”."],
        ["c:Nice climb, {pct0} → {pct} %.", "a:Thanks, carrying on with “{tache}”."],
        ["a:Only {reste} left on “{tache}”, says my bar.", "b:You're nearly there."],
        ["b:{saut} points in one go?", "a:Yes, “{tache}” is at {pct} %."],
        ["{?moitie}a:Past halfway: {pct} % on “{tache}”.", "b:The rest will fly by."],
        ["c:Where's “{tache}” at?", "a:{pct} %, about {reste} left."],
        ["a:{pct} % on “{tache}”.", "b:Not bad! “{tacheB}” is at {pctB} % on my side."],
        ["b:{saut} more points on “{tache}”?", "a:Yes, {pct} % now."],
      ],
      etape: [
        ["b:New step?", "a:Yes: “{etape}”."],
        ["a:Moving from “{etape0}” to “{etape}”.", "b:Good, you're moving."],
        ["a:On to “{etape}”.", "b:Will it take long?", "a:We'll see, but it's off to a good start."],
        ["b:Changing course?", "a:Just the next step: “{etape}”."],
        ["a:Next step: “{etape}”.", "c:Great, keep that pace."],
        ["b:What is it now?", "a:“{etape}”.", "b:Ah, the fun part."],
        ["a:“{etape0}” is behind me.", "b:And ahead?", "a:“{etape}”."],
        ["a:Tackling “{etape}”.", "b:Tell me if you want a fresh pair of eyes."],
        ["c:New step for you?", "a:Yes, now “{etape}”."],
        ["a:Step “{etape}”.", "b:Still “{tacheB}” for me."],
      ],
      bloque: [
        ["b:Stuck?", "a:Yes, on “{raison}”.", "b:I can look at it with you."],
        ["a:I'm at a standstill: “{raison}”.", "c:On it, I'll find what's missing."],
        ["b:Your bar is red…", "a:“{raison}”. Waiting for it to clear."],
        ["a:My task is blocked: “{raison}”.", "b:Hang in there, it happens to everyone."],
        ["c:What's blocking?", "a:“{raison}”.", "c:Noted."],
        ["b:Need help?", "a:Maybe: “{raison}”."],
        ["a:Forced break: “{raison}”.", "b:Grab a coffee meanwhile."],
        ["b:Still stuck?", "a:Yes, “{raison}”.", "b:We'll figure it out."],
        ["b:Stuck?", "a:Yes: “{raison}”.", "b:I'll finish “{tacheB}” and come and look."],
        ["a:Blocked: “{raison}”.", "b:I'm on “{tacheB}”, but call me if needed."],
      ],
      debloque: [
        ["a:Back on track!", "b:Great, “{tache}” again?", "a:Yes, finally."],
        ["a:Unblocked! Resuming “{tache}”.", "b:Good news."],
        ["c:No more blocker?", "a:No, “{tache}” is moving again."],
        ["a:The way is clear for “{tache}”.", "b:Go for it!"],
        ["b:Your bar is green again.", "a:Yes, resuming “{tache}”."],
        ["a:Finally! I can carry on with “{tache}”.", "c:Great, let's catch up."],
        ["b:Found the fix?", "a:It cleared up, back to “{tache}”."],
        ["a:Resuming “{tache}”.", "b:Good to see."],
        ["a:Back on “{tache}”: {pct} %.", "b:Good. I'm carrying on with “{tacheB}”."],
      ],
      commit: [
        ["a:New commit: “{commit}”.", "b:Saw it go by."],
        ["b:Seen the latest commit?", "a:“{commit}”, at {heure_c}."],
        ["a:{nbc} new commits, including “{commit}”.", "b:Busy day."],
        ["a:“{commit}” just landed in the repo.", "b:I'll update my side.", "a:Good idea."],
        ["b:Commit at {heure_c}: “{commit}”.", "c:The repo is moving."],
        ["a:The repo moves: “{commit}”.", "b:Let's hope the build keeps up!"],
        ["c:One more commit: “{commit}”.", "a:Bit by bit…", "b:… the game takes shape."],
        ["b:“{commit}”, what time was that?", "a:{heure_c}."],
        ["a:At {heure_c}, “{commit}”.", "b:Pulling it right now."],
        ["a:“{commit}” is in the repo.", "b:I'll bring it into “{tacheB}”."],
      ],
      decision: [
        ["a:A decision is waiting for {maitre}: “{dec}”.", "b:We'll push on with the rest meanwhile."],
        ["b:Seen the bell?", "a:Yes: “{dec}”.", "b:Can't wait to see the answer."],
        ["a:“{dec}”: up to {maitre}.", "b:My bet is on the recommendation."],
        ["c:New question for {maitre}: “{dec}”.", "a:We'll see what comes back."],
        ["b:The bell rings: “{dec}”.", "a:Good question, that one."],
        ["a:{nbd_d} waiting now.", "b:Including “{dec}”."],
        ["b:We'll need {maitre} on “{dec}”.", "a:Yes, that's what the bell is for."],
        ["a:“{dec}”… I have my own idea.", "b:Save it for {maitre}!"],
      ],
      jalon: [
        ["c:Milestone “{jalon}” is wrapped up!", "a:Nothing pending?", "c:Nothing."],
        ["a:“{jalon}”: done!", "b:On to the next: “{jalon2}”."],
        ["b:Champagne? “{jalon}” is finished.", "a:Coffee will do."],
        ["c:Milestone “{jalon}” closed.", "b:{v1} % of version 1, we believe."],
        ["a:We just closed “{jalon}”.", "b:How many left?", "a:{jreste}."],
        ["b:“{jalon}” is behind us.", "c:Next stop: “{jalon2}”."],
        ["a:The roadmap wall turns green for “{jalon}”.", "b:Feels good to see."],
        ["c:Well done everyone on “{jalon}”.", "a:Thanks! On to “{jalon2}”?"],
      ],
      embauche: [
        ["b:Welcome! What are you here for?", "a:{role}.", "b:Perfect, we needed that."],
        ["a:Hello! I'm here for: {role}.", "b:Hi! Your desk is ready."],
        ["c:Meet {A}: {role}.", "b:Welcome to the team!"],
        ["b:A new desk is taken.", "a:That's me! {role}."],
        ["b:Welcome {A}. What do you start with?", "a:{mission}."],
        ["a:First day at the studio!", "b:You'll like it here. What do you do?", "a:{role}."],
        ["b:We're growing: {nbp} desks now.", "a:And I'm the new hire."],
        ["c:New hire: {A}.", "a:Hello! I handle: {role}.", "b:Welcome!"],
        ["a:Hello! {role}.", "b:Welcome! I'm on “{tacheB}”."],
      ],
      renvoi: [
        ["a:{parti} packed up their desk.", "b:Feels empty."],
        ["b:Did you see? {parti} left the studio.", "a:We'll pick things up if needed."],
        ["a:{parti}'s desk is free now.", "b:We'll be {nbp} from now on."],
        ["c:{parti} is leaving us.", "a:Thanks for the work."],
        ["b:Only {nbp} desks left.", "a:Since {parti} left, yes."],
        ["a:Goodbye {parti}!", "b:Safe travels."],
        ["b:Who takes over what {parti} was doing?", "c:We'll see at the next assignment."],
        ["a:{parti}'s box just went out the door.", "b:Not the plant, I hope."],
      ],
      sante: [
        ["a:The PC is breathing hard.", "b:Yes: {alerte}."],
        ["b:Bit sluggish, isn't it?", "a:{alerte}. Let's space out heavy tasks."],
        ["c:Careful, {alerte}.", "a:Closing what I don't need."],
        ["a:{alerte}…", "b:Let's wait for it to settle before launching anything."],
        ["b:The fan is singing.", "a:No wonder: {alerte}."],
        ["a:The machine is saturated: {alerte}.", "b:Forced coffee break, then."],
        ["c:PC health turns orange: {alerte}.", "b:Easing off."],
        ["a:Feel the PC heat?", "b:Yes, {alerte}.", "a:One heavy tool at a time."],
      ],
      sante_ok: [
        ["a:The PC is breathing again.", "b:CPU at {cpu} %, much better."],
        ["b:No more machine alert.", "a:Memory at {mem} %, we can restart."],
        ["c:PC health is back to green.", "a:CPU at {cpu} %, perfect."],
        ["a:No more overheating: {cpu} % CPU.", "b:Back to normal pace."],
        ["b:The fan calmed down.", "a:Yes, only {mem} % memory."],
        ["a:The machine got its breath back.", "c:{cpu} % CPU, heavy tasks can resume."],
        ["b:Feel that? The PC isn't hot anymore.", "a:{cpu} % CPU, what a difference."],
        ["c:Machine alert cleared.", "b:Memory at {mem} %, breathing room."],
      ],
      compile_ok: [
        ["a:Green build!", "b:It passes?", "a:Yes: “{tache}”."],
        ["b:Are you smiling?", "a:“{tache}”. All green."],
        ["a:“{tache}”: the build passes.", "c:Excellent."],
        ["c:Is the build green?", "a:Yes, “{tache}”."],
        ["a:Not a single error: “{tache}”.", "b:Mark the date, it's historic."],
        ["b:I saw “{tache}” go by.", "a:Yes, it builds."],
        ["a:Green as green gets: “{tache}”.", "b:Can we test, then?", "a:We can test."],
        ["a:“{tache}”, everything passes!", "b:Bravo, we can move on."],
      ],
      compile_ko: [
        ["a:Ouch, the build breaks.", "b:On what?", "a:“{tache}”."],
        ["b:Looks red on your side.", "a:“{tache}”. Looking into it."],
        ["a:“{tache}”… not this time.", "c:Take the time to read the error."],
        ["c:Build failing?", "a:Yes: “{tache}”."],
        ["a:Red: “{tache}”.", "b:Hang in there, we've all been there."],
        ["b:Need a second pair of eyes?", "a:Gladly: “{tache}”."],
        ["a:The build won't pass: “{tache}”.", "b:Coffee, then we read it together?"],
        ["a:“{tache}”, it breaks.", "c:No panic, we fix it before merging."],
      ],
      image: [
        ["a:New image on the wall: “{image}”.", "b:Looks great!"],
        ["{?auteur}b:Did you hang “{image}”?", "a:Yes, fresh out."],
        ["a:Look at the wall: “{image}”.", "c:Makes me want to play."],
        ["b:“{image}”, is that new?", "a:Just out."],
        ["{?auteur}a:I added “{image}” to the wall.", "b:The game is getting colourful."],
        ["{?auteur}c:Nice image, “{image}”.", "a:Thanks! More to come."],
        ["b:The wall grows: “{image}”.", "a:We finally see what it looks like."],
        ["a:“{image}” is on the wall.", "b:Making it my wallpaper.", "a:Flattering!"],
        ["a:“{image}” is on the wall.", "b:That'll help with “{tacheB}”."],
      ],
      travail: [
        ["b:Where are you at?", "a:“{tache}”, {pct} %."],
        ["b:How's “{tache}” going?", "a:{pct} %, about {reste} left."],
        ["b:Need a hand?", "a:I'm fine, “{tache}” is moving: {pct} %."],
        ["a:Head down in “{tache}”.", "b:We won't disturb you then."],
        ["b:Still on “{tache}”?", "a:Still. {pct} % for now."],
        ["a:About {reste} more on “{tache}”.", "b:Hang in there!"],
        ["b:Working in {outil}?", "a:Yes, for “{tache}”."],
        ["b:How's it going with {objet}?", "a:“{tache}” is at {pct} %."],
        ["a:“{tache}”: {pct} %, holding up.", "b:I'll leave you to it."],
        ["c:All good on “{tache}”?", "a:Yes, {pct} % for now."],
        ["b:Got two minutes?", "a:After “{tache}”: about {reste} left."],
        ["a:I'm at {pct} %.", "b:On “{tache}”? Not bad."],
        ["b:What are you on right now?", "a:“{tache}”."],
        ["b:Moving on your side?", "a:“{tache}”, {pct} %. You?", "b:“{tacheB}”, {pctB} %."],
        ["a:“{tache}”: {pct} %.", "b:Me, “{tacheB}”."],
      ],
      duo: [
        ["a:I'm at {pct} % on “{tache}”. You?", "b:{pct2} % on “{tache2}”."],
        ["a:Each to our own: “{tache}” for me.", "b:And “{tache2}” for me."],
        ["b:Where are you at?", "a:{pct} %. And you, “{tache2}”?"],
        ["a:I'll finish “{tache}” and come help.", "b:Gladly, “{tache2}” is giving me a hard time."],
        ["b:Break?", "a:Not yet, “{tache}” is at {pct} %."],
        ["a:Full focus on “{tache}”.", "b:Same for “{tache2}”."],
        ["{?devant}a:Your bar moves faster than mine.", "b:{pct2} % against {pct} %? It'll even out."],
        ["b:Race you?", "a:“{tache}” against “{tache2}”, deal!"],
        ["a:{pct} % here, on “{tache}”.", "b:{pct2} % on my side."],
        ["b:Can I borrow your screen for a sec?", "a:After “{tache}”, promise."],
      ],
      attente: [
        ["b:What are you waiting for?", "a:I'm waiting for {attente}."],
        ["a:Being patient: waiting for {attente}.", "b:Hang in there."],
        ["b:Your task is paused?", "a:Yes, waiting for {attente}.", "b:I'll tell you if I see anything."],
        ["a:Nothing to do until I get {attente}.", "b:Coffee meanwhile?"],
        ["c:All good?", "a:Waiting for {attente}, that's all."],
        ["b:Still waiting?", "a:Yes, still {attente}."],
        ["a:If anyone sees {attente}, I'll take it.", "b:I'll keep an eye out."],
        ["b:You don't seem to move.", "a:Waiting for {attente}."],
      ],
      suite: [
        ["b:And after that?", "a:“{suite}”."],
        ["a:Next task: “{suite}”.", "b:Sounds fun."],
        ["b:What's on your list?", "a:Next, “{suite}”."],
        ["a:“{suite}” is already on my list.", "b:No rest for you."],
        ["c:Know what's coming?", "a:Yes: “{suite}”."],
        ["b:What's left for you?", "a:“{suite}”, to start with."],
        ["a:“{suite}” is coming up.", "b:Tell me if you want to talk it through."],
        ["b:Next step?", "a:“{suite}”.", "b:Good plan."],
      ],
      libre: [
        ["a:Coffee break?", "b:Yes. Version 1 is at {v1} %, we earned it."],
        ["a:Seen the latest commit?", "b:“{commit}”, yes."],
        ["a:{nbt_t} at work, and us at the coffee machine.", "b:Our turn will come."],
        ["a:Still {tdispo}.", "b:We'll find one for us."],
        ["b:Waiting for the rest of “{jalon}”.", "a:Coffee meanwhile."],
        ["a:Nothing on my desk for now.", "b:Same. “{jalon}” is at {jpct} %."],
        ["b:Nothing in front of us.", "a:The roadmap says {v1} %, it'll come."],
        ["a:Coffee?", "b:Sure. Seen “{commit}”?"],
      ],
      roadmap: [
        ["a:Version 1 is at {v1} %.", "b:And “{jalon}” at {jpct} %."],
        ["b:Where are we overall?", "a:{v1} % of version 1."],
        ["a:“{jalon}”: {jpct} %.", "b:We're getting there."],
        ["c:{faites} out of {total}.", "a:Step by step."],
        ["b:Looked at the roadmap?", "a:Yes, {v1} %. Current milestone: “{jalon}”."],
        ["a:One more push on “{jalon}”.", "b:It's at {jpct} %, coming along."],
        ["b:{faites} out of {total}, not bad.", "a:And every merge counts."],
        ["c:Roadmap check: {v1} %.", "b:The next milestone is getting closer."],
      ],
      attente_decisions: [
        ["a:{nbd_d} waiting for {maitre}.", "b:Including “{dec}”."],
        ["b:The bell is still waiting.", "a:Yes: “{dec}”."],
        ["a:“{dec}”, still undecided.", "b:{maitre} surely has other things to do."],
        ["c:Quick reminder: “{dec}”.", "a:The bell is still blinking."],
        ["b:We'd need an answer on “{dec}”.", "a:It'll come."],
        ["a:{nbd_d} under the bell.", "b:We carry on without it meanwhile."],
        ["b:For “{dec}”, what do you think {maitre} will pick?", "a:No idea, surprise."],
        ["a:“{dec}” still pending.", "c:I'll bring it up at the next update."],
        ["a:“{dec}” is still waiting.", "b:No matter, I'm carrying on with “{tacheB}”."],
      ],
      commits_jour: [
        ["a:{ncj} today.", "b:The latest: “{commit}”."],
        ["{?ncj_plus}b:Lots of commits today.", "a:{ncj} since midnight."],
        ["a:The repo is alive: {ncj} today.", "b:And the build holds?"],
        ["{?ncj_plus}c:Good day: {ncj}.", "a:Including “{commit}”."],
        ["b:Latest commit at {heure_c}.", "a:“{commit}”, I saw it."],
        ["{?ncj_plus}a:{ncj}, a record?", "b:Could be."],
        ["b:Seen “{commit}”?", "a:Yes, at {heure_c}."],
        ["a:Another commit: “{commit}”.", "b:The repo never sleeps."],
      ],
      heure: [
        ["a:{moment}, I'm on “{tache}”.", "b:{remarque}"],
        ["b:{remarque}", "a:And “{tache}” is moving: {pct} %."],
        ["a:{moment}, {nbt_t} at work.", "b:{remarque}"],
        ["b:{moment}, version 1 is at {v1} %.", "a:{remarque}"],
        ["a:{remarque}", "b:{moment}, I'm on “{tache2}”."],
        ["b:Plans for {moment_court}?", "a:“{tache}”."],
        ["a:{moment}, the goal: “{tache}”.", "b:{remarque}"],
        ["b:{moment}, we aim at “{jalon}”.", "a:{remarque}"],
      ],
      metier: [
        ["b:How's it going with {objet}?", "a:Moving along: “{tache}”."],
        ["a:{outil} and I get along today.", "b:Good for “{tache}”."],
        ["b:Will you show me {objet}?", "a:Soon. “{tache}” first."],
        ["a:My job: {role}.", "b:And right now?", "a:“{tache}”."],
        ["b:Enjoying {objet}?", "a:A lot. Especially “{tache}”."],
        ["a:Today, {outil} for “{tache}”.", "b:Good luck with that."],
        ["b:What do you need for “{tache}”?", "a:Quiet and coffee."],
        ["a:{role}: that's me.", "b:And “{tache}”, that's you too?", "a:Yes."],
        ["{?cat_son}b:Headphones on?", "a:Yes, “{tache}” needs quiet."],
        ["{?cat_relecture}b:What are you reviewing right now?", "a:“{tache}”."],
        ["{?cat_modele3d}b:How many polygons for “{tache}”?", "a:Enough to look nice, not too many for the game."],
        ["{?cat_faune}b:Are your creatures behaving?", "a:We'll see: “{tache}” is at {pct} %."],
        ["{?cat_moteur}b:Is the engine leaving you alone?", "a:So far. “{tache}”: {pct} %."],
        ["{?cat_code}b:Does your logic hold up?", "a:The simple cases do. “{tache}”: {pct} %."],
        ["{?cat_level}b:Is your map growing?", "a:“{tache}”, {pct} %."],
        ["{?cat_art}b:Will you show me your sketches?", "a:Once “{tache}” has moved on."],
        ["{?cat_direction}b:Is the roadmap giving you grey hair?", "a:No: version 1 is at {v1} %, it's fine."],
        ["{?cat_narration}b:What are you writing right now?", "a:“{tache}”."],
        ["{?cat_studio}b:Tinkering with the studio again?", "a:Yes: “{tache}”."],
      ],
      pc: [
        ["a:Is the PC holding up?", "b:CPU at {cpu} %, memory at {mem} %."],
        ["b:{cpu} % CPU, easy.", "a:Good."],
        ["a:Memory at {mem} %.", "b:Plenty of room."],
        ["c:PC health: {cpu} % CPU.", "a:Nothing worrying."],
        ["b:Hear the fan?", "a:At {cpu} %, it's still quiet."],
        ["a:{mem} % memory, fine.", "b:We can open a heavy tool."],
        ["b:Machine all right?", "a:{cpu} % CPU, it's almost resting."],
        ["a:CPU at {cpu} %.", "b:It's seen worse."],
      ],
      nouveau: [
        ["a:Seen “{image}” on the wall?", "b:Yes, makes me want to play."],
        ["b:“{image}”, is it recent?", "a:Yes, just arrived."],
        ["a:The wall changes: “{image}”.", "b:Love it."],
        ["c:Have a look at “{image}”.", "b:Gorgeous."],
        ["b:The game looks more and more like something.", "a:“{image}” proves it."],
        ["a:“{image}”: you can see the progress.", "b:Totally."],
        ["b:Who made “{image}”?", "a:The team, as always."],
        ["a:Small pride of the day: “{image}”.", "b:Rightly so."],
      ],
    },
  };
  const REMARQUES = {
    fr: { matin: ["Le café du matin fait effet.", "Bonne journée qui commence.", "Rien de tel qu'un bureau rangé le matin.", "On démarre en douceur.", "Les idées sont fraîches à cette heure."],
      midi: ["Ça sent la pause déjeuner.", "Une bouchée et on reprend.", "Le soleil est au plus haut.", "On mange sur le pouce ?", "Pause bien méritée bientôt."],
      aprem: ["Le creux de l'après-midi, courage.", "Un thé pour tenir ?", "L'après-midi file vite.", "On garde le rythme.", "C'est le moment de s'y remettre."],
      soir: ["La lumière baisse dehors.", "Encore un peu et on souffle.", "Belle journée, quand même.", "Le studio se calme doucement.", "Dernier café de la journée ?"],
      nuit: ["Le studio tourne même la nuit.", "Les étoiles sont sorties.", "Calme plat dehors.", "La nuit porte conseil.", "On avance pendant que tout dort."] },
    en: { matin: ["The morning coffee kicks in.", "A good day is starting.", "Nothing beats a tidy desk in the morning.", "Easing into it.", "Ideas are fresh at this hour."],
      midi: ["Smells like lunch break.", "A quick bite and back to it.", "The sun is high.", "Lunch at the desk?", "A well-earned break soon."],
      aprem: ["The afternoon slump, hang in there.", "Tea to keep going?", "The afternoon flies by.", "Keeping the pace.", "Time to get back into it."],
      soir: ["The light is fading outside.", "A bit more and we rest.", "Good day, all in all.", "The studio quiets down.", "Last coffee of the day?"],
      nuit: ["The studio runs even at night.", "The stars are out.", "Dead calm outside.", "Night brings counsel.", "We move while everything sleeps."] }
  };
  const MOMENTS_COURTS = { fr: { matin: 'la matinée', midi: 'la mi-journée', aprem: "l'après-midi", soir: 'la soirée', nuit: 'la nuit' },
    en: { matin: 'the morning', midi: 'midday', aprem: 'the afternoon', soir: 'the evening', nuit: 'the night' } };
  // Priorités : un événement important (>= HAUTE) passe tout de suite ; les ordinaires alternent avec l'ambiance.
  const PRIO = { decision: 9, bloque: 8, verse: 8, fini: 7, jalon: 7, embauche: 7, renvoi: 6, compile_ko: 6, compile_ok: 5, pret: 5, commit: 5,
    debloque: 5, commence: 4, pct: 4, sante: 6, sante_ok: 3, etape: 3, image: 3 }, HAUTE = 6;
  // pause minimale entre deux échanges du même type d'événement ordinaire (le studio qui bouge ne parle pas que de %)
  const PAUSE_TYPE = { pct: 3 * MIN, etape: 3 * MIN, commence: 2 * MIN, commit: 2 * MIN, pret: 90000, image: 3 * MIN, compile_ok: 2 * MIN, sante_ok: 5 * MIN, debloque: MIN };
  const PAUSE_PCT_POSTE = 6 * MIN, FILE_MAX = 10, GABARIT_MIN = 20 * MIN;
  const AMBIANCE = { travail: 3, duo: 2, attente: 1.5, suite: 1.5, libre: 2, roadmap: 1.2, attente_decisions: 1.2, commits_jour: 1, heure: .8, metier: 2, pc: .5, nouveau: .8 };
  // Compile : « 0 erreur », « sans erreur », « no errors » valent un succès ; un texte qui dit à la fois oui et non ne fait rien dire.
  // Seuls des mots d'état précis comptent (liste fermée, pas de racine ouverte) : « plantes », « vertex », « je passe au
  // build » ne disent rien de la compile. Les négations (« ne passe pas / plus / jamais », « doesn't build anymore ») sont
  // lues d'abord comme un échec, « 0 erreur », « sans erreur », « no errors » comme un succès.
  // \b et \w de JavaScript ignorent les lettres accentuées (« échoue », « planté ») : U() les remplace par leurs équivalents
  // Unicode avant de compiler l'expression.
  const MOT = '[\\p{L}\\p{N}_]', BORD = '(?:(?<!' + MOT + ')(?=' + MOT + ')|(?<=' + MOT + ')(?!' + MOT + '))';
  const U = (re, f) => new RegExp(String(re.source || re).replace(/\\b/g, BORD).replace(/\\w/g, MOT), (f || '') + 'u');
  const COMPILE = U(/(?:\b|re-?)(?:compil\w*|build\w*|cook\w*|packag\w*|empaquet\w*)/, 'i');
  const VERBE_C = '(?:re)?(?:passe\\w*|compile\\w*|build\\w*|cook\\w*|marche\\w*|fonctionne\\w*)';
  const SANS_ERREUR = U(/\b(?:0|z[ée]ro|aucune?|sans|no|zero|without)\s+(?:erreurs?|errors?|[ée]checs?|failures?|fails?)\b|\b(?:erreurs?|errors?)\s+(?:corrig[ée]e?s?|r[ée]gl[ée]e?s?|fixed|resolved)\b/, 'gi');
  const NEGATION_KO = U("\\bn(?:e\\s+|['’]\\s*)" + VERBE_C + "\\s+(?:pas|plus|jamais)\\b|\\b(?:does|did|do|is|was)\\s*n(?:o|['’])t\\s+(?:re)?(?:pass|build|compile|cook|work)\\w*"
    + "|\\b(?:won['’]?t|can['’]?t|cannot|no\\s+longer)\\s+(?:re)?(?:pass|build|compile|cook|work)\\w*|\\bn['’]est\\s+plus\\s+vert", 'gi');
  const CIBLE_C = '(?:compil\\w*|(?:re)?build\\w*|cook\\w*|packag\\w*|empaquet\\w*|tests?|ci)';
  const OK_RE = U("\\bok\\b|\\b(?:au|en|est|reste|repasse|passe|is|stays|turned|went)\\s+(?:au\\s+)?(?:vert|green)\\b|\\b" + CIBLE_C + "\\s+(?:est\\s+|sont\\s+|is\\s+|are\\s+)?(?:vert|verte|verts|vertes|green|propre|clean)\\b"
    + "|\\br[ée]ussi(?:e|es|s|t)?\\b|\\bsucc[eè]s\\b|\\bsucce(?:ss|ssful|ssfully|eded|eds)\\b|\\b(?:passes|passed|passing)\\b"
    + "|\\b(?:" + CIBLE_C + "|[çc]a|il|elle|tout)\\s+(?:re)?passe(?:nt)?\\b(?!\\s+(?:au|à|aux|en|sur|par|sous|à\\s+la)\\b)", 'i');
  const KO_RE = U("\\b\\d+\\s+(?:erreurs?|errors?)\\b|\\b(?:erreurs?|errors?)\\s+(?:de|d['’]|du)\\s*(?:compil|build|link|cook|packag)\\w*|\\b(?:compil\\w*|build|link\\w*|cook)\\s+errors?\\b|\\ben\\s+erreur\\b|\\bwith\\s+errors?\\b"
    + "|\\b[ée]chou(?:e|ent|é|ée|és|ées)\\b|\\b[ée]chec\\b|\\bfail(?:s|ed|ing|ure|ures)?\\b|\\bbroken\\b|\\bcass(?:é|ée|és|ées)\\b|\\bplant(?:é|ée|és|ées)\\b|\\b(?:[çc]a|il|elle|qui|" + CIBLE_C + ")\\s+plante(?:nt)?\\b"
    + "|\\bcrash(?:es|ed|e|é|ée)?\\b|\\b(?:au|en|est|reste|passe)\\s+(?:au\\s+)?(?:rouge|red)\\b|\\b" + CIBLE_C + "\\s+(?:est\\s+|sont\\s+|is\\s+)?(?:rouges?|red)\\b", 'i');
  function etatCompile(txt) {
    if (!COMPILE.test(txt)) return null;
    let s = String(txt), ko = false, ok = false;
    s = s.replace(NEGATION_KO, () => { ko = true; return ' '; });
    s = s.replace(SANS_ERREUR, () => { ok = true; return ' '; });
    if (KO_RE.test(s)) ko = true;
    if (OK_RE.test(s)) ok = true;
    return ko && ok ? null : ko ? 'ko' : ok ? 'ok' : null;
  }
  // Langue d'un texte (repère grossier : mots outils, accents, terminaisons) ; à défaut, la langue de l'ensemble des données
  // du projet (voir langueProjet). Un texte dont la langue est connue et n'est pas celle de la page n'est pas cité.
  const MOTS_FR = U(/\b(le|la|les|des|du|de|une|un|et|pour|avec|sur|dans|sans|quand|qui|est|au|aux|en|ou|par|puis|plus|pas)\b/, 'gi'),
    MOTS_EN = U(/\b(the|and|with|for|of|to|is|without|from|when|on|into|at|a|an|by|then|more|not|this|that)\b/, 'gi'),
    FIN_FR = U(/\b\w+(?:eaux?|eux|euse|oire|ière|ier|ages?|ée|ées|ette|elle|ment|rices?)\b/, 'gi'), FIN_EN = U(/\b\w+(?:ing|ness|ship|ful|less|ed|ly|ity|ies)\b/, 'gi');
  function langueDe(s) {
    s = String(s || ''); const f = 1.5 * (s.match(MOTS_FR) || []).length + 2 * (s.match(/[éèêàùçœâîôûë]/gi) || []).length + .6 * (s.match(FIN_FR) || []).length,
      e = 1.5 * (s.match(MOTS_EN) || []).length + .6 * (s.match(FIN_EN) || []).length;
    return f >= e + 1 ? 'fr' : e >= f + 1 ? 'en' : null;
  }
  const TEXTES_LIBRES = ['tache', 'tache2', 'tacheB', 'suite', 'etape', 'etape0', 'raison', 'attente', 'commit', 'dec', 'jalon', 'jalon2', 'image', 'role', 'mission'];

  function creer(S) {
    const lg = () => (S.langue() === 'fr' ? 'fr' : 'en');
    const frais = () => (S.frais ? !!S.frais() : true);
    const JOURNAL = [], ECH = [], FILE = [], PARLE = {}, RECENTS_S = [], DERNIER_TYPE = {}, PCT_POSTE = {}, ECARTES = {}, ARRIVES = {};
    let NUM = 0, SUITE_EV = 0;
    let PREC = null, ANNONCE = {}, occupeJusqua = 0, prochaineAmbiance = Date.now() + 20000, rapide = /[?&]babil=rapide\b/.test(location.search);
    const now = () => Date.now();
    let MEMO = (() => {
      const m = S.ls.get('babil_memo', null); if (!m || !Array.isArray(m.p)) return { p: [], g: [] };
      m.g = (Array.isArray(m.g) ? m.g : []).map(x => Array.isArray(x) ? x : [String(x), 0]); return m;
    })();
    const memoPurger = () => { const n = now(); MEMO.p = MEMO.p.filter(x => Array.isArray(x) && n - x[1] < MEMOIRE).slice(-400); MEMO.g = MEMO.g.filter(x => n - x[1] < MEMOIRE).slice(-60); };
    const dejaDit = txt => MEMO.p.some(x => x[0] === txt && now() - x[1] < MEMOIRE);
    const sauver = () => { memoPurger(); S.ls.set('babil_memo', MEMO); };
    const ecarter = (type, pourquoi) => { const k = type + ':' + pourquoi; ECARTES[k] = (ECARTES[k] || 0) + 1; };

    // ---------------- mise en forme des données (aucun chemin, aucun hash, pas de coupure au milieu d'un mot)
    function propre(s, n, garderQ) {
      n = n || 46; s = String(s == null ? '' : s);
      s = s.replace(/https?:\/\/\S+/g, ' ')
        .replace(/(?:[A-Za-z]:)?(?:[\\/][^\s\\/«»"“”()[\]]+){2,}[\\/]?/g, ' ')
        .replace(/\b[\w.-]+[\\/][\w.\\/-]+/g, ' ')
        .replace(/\b[\w-]+\.(?:json|py|js|ts|html|css|md|txt|csv|ini|uasset|umap|uproject|blend|fbx|glb|gltf|obj|png|jpe?g|webp|wav|ogg|mp3|tscn|gd|cs|cpp|h|unity|prefab|log)\b/gi, ' ')
        .replace(/\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b/gi, ' ')
        .replace(/\s*\([^()]*\)/g, '').replace(/\s*\[[^\]]*\]/g, '')
        .replace(/[`*_]{1,}/g, ' ').replace(/[«»"“”]/g, '')
        .replace(/^\s*(?:[A-Z]{1,4}\d*-\d+[a-z]?|[A-Z]\d+)\s*[·:–—-]\s*/, '')
        .replace(/\s+/g, ' ').trim();
      const question = garderQ && /\?\s*$/.test(s);
      s = s.replace(/^[\s,;:·–—.-]+|[\s,;:·–—?!.-]+$/g, '');
      if (s.length > n) {
        const c = s.slice(0, n + 1), i = c.lastIndexOf(' ');
        if (i < 8) return null;
        s = c.slice(0, i); for (let k = 0; k < 3; k++) s = s.replace(VIDES[lg()], '').replace(/[\s,;:·–—-]+$/, '');
        s += '…';
      } else if (question) s += lg() === 'fr' ? ' ?' : '?';
      return s.length >= 3 && /[A-Za-zÀ-ÿ]/.test(s) ? s : null;
    }
    // la fiche du poste, sans ce qu'elle nie (« sans moteur », « hors moteur », « without engine », « pas de Blender »…)
    const NIE = /\b(?:sans|hors|pas\s+de|pas\s+d['’]|without|no|not\s+in|outside(?:\s+of)?)\s+(?:(?:le|la|les|l['’]|un|une|du|the|an?|any)\s+)?[\wÀ-ÿ'’-]+/gi;
    const fiche = p => [p.id, p.role, (p.metiers || []).join(' '), (p.skills || []).join(' '), p.mission].join(' ').toLowerCase().replace(NIE, ' ').replace(/engine-free/g, ' ');
    function categorie(p) {
      const txt = fiche(p);
      for (const [c, re] of METIERS) if (re.test(txt)) return c;
      return 'autre';
    }
    // outil cité seulement s'il est nommé dans la fiche du poste (et pas nié) ; le moteur du projet seulement pour un poste
    // dont le métier est le moteur (catégorie « moteur » : un poste son qui « intègre ses sons » ne travaille pas dans le moteur)
    function outilDe(p) {
      const txt = fiche(p);
      const o = OUTILS.find(x => new RegExp('(^|[^a-z0-9])' + x.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '($|[^a-z0-9])').test(txt)
        || (x === 'LÖVE' && /(^|[^a-z])love2d([^a-z]|$)/.test(txt)));
      if (o) return o;
      const m = S.moteur && S.moteur(); if (!m || categorie(p) !== 'moteur') return null;
      return /\bmoteur\b|\bengine\b|int[eé]gration|integration/.test(txt) || txt.includes(String(m).toLowerCase()) ? String(m).slice(0, 20) : null;
    }
    const sansPrefixe = s => String(s || '').replace(/^(attend(?: le lancement)?|waiting(?: to start| for)?|en pause \(\d+ min\)|paused \(\d+ min\)|suite|next|bloqu[ée]|blocked)\s*:?\s*/i, '');
    function moment() { const h = new Date().getHours(); return h >= 5 && h < 11 ? 'matin' : h < 14 && h >= 11 ? 'midi' : h >= 14 && h < 18 ? 'aprem' : h >= 18 && h < 22 ? 'soir' : 'nuit'; }
    const pluriel = (n, un, plus) => n === 1 ? un : n + ' ' + plus;

    // ---------------- instantané de l'état (les données de etat.json ne sont lues que si l'alimentation est à jour)
    function photo() {
      const ps = S.postes(), F = frais(), E = F ? (S.global() || {}) : {}, rm = S.roadmap(), out = { postes: {}, ordre: [], t: now(), frais: F };
      ps.forEach((p, i) => {
        let e; try { e = S.etat(p); } catch (err) { return; }
        const ep = S.brut(p);
        const pctB = S.pctBrut(p);
        const complet = (ep && ep.ligne && ep.ligne.complet) || (ep && ep.tache) || (e.ligne && e.ligne.texte) || '';
        const texteBrut = ep ? String(ep.texte || '') : String(e.texte || '');   // le texte de l'agent, jamais la ligne affichée (« libre »…)
        const tache = propre(texteBrut) || (e.etat === 'travaille' ? propre(sansPrefixe(complet)) : null);
        const lance = complet.match(/^(?:attend le lancement|waiting to start)\s*:\s*(.+)$/i), tl = lance && propre(lance[1], 36);
        const attente = lance ? (tl ? (lg() === 'fr' ? 'le lancement de « ' + tl + ' »' : 'the start of “' + tl + '”') : null)
          : /^(attend|waiting for)\b/i.test(complet) ? propre(complet.replace(/^(attend|waiting for)\s*/i, ''), 44) : null;
        const suite = (e.restantes || []).map(r => propre(r)).find(r => r && r !== tache && !(tache && tache.startsWith(r.replace(/…$/, '')))) || null;
        out.postes[p.id] = { id: p.id, i, p, nom: S.nom(p), etat: e.etat, pct: pctB, tache, etape: propre(texteBrut), suite, attente, reste: e.reste,
          comp: etatCompile(texteBrut), raison: e.etat === 'bloque' ? (propre(texteBrut) || propre(sansPrefixe(complet))) : null, cat: categorie(p), outil: outilDe(p),
          role: propre(p.role, 60), mission: propre(p.mission, 60), recrue: p.genre === 'recrue' };
        out.ordre.push(p.id);
      });
      const git = E.git || {}, commits = Array.isArray(git.commits) ? git.commits.filter(c => c && c.hash) : [];
      out.commits = commits.map(c => c.hash); out.commit = commits[0] || null; out.ncj = Number.isFinite(+git.commits_jour) && git.commits_jour !== null ? +git.commits_jour : null;
      out.decisions = (S.decisions() || []).map(d => ({ id: d.id, titre: d.titre }));
      out.taches = {}; out.jalons = [];
      if (rm && Array.isArray(rm.jalons)) {
        for (const j of rm.jalons) { out.jalons.push({ id: j.id, titre: j.titre, ferme: !!j.ferme, pct: j.pct, faites: j.faites, total: j.total });
          for (const tc of j.taches || []) if (tc && tc.id) out.taches[tc.id] = { id: tc.id, titre: tc.titre, statut: tc.statut, poste: tc.poste, jalon: j.id }; }
        out.faites = rm.faites; out.total = rm.total;
      }
      const v = E.version1 || {}; out.v1 = Number.isFinite(+v.pct) && v.pct !== null && v.source !== 'aucune' ? Math.round(+v.pct) : null;
      out.jalonEnCours = v.jalon ? { id: v.jalon.id, titre: v.jalon.titre, pct: v.jalon.pct } : null;
      const sa = E.sante || {}, sy = E.systeme || {};
      out.sature = F ? !!sa.sature : null; out.alerte = Array.isArray(sa.alertes) && sa.alertes[0] ? propre(sa.alertes[0], 60) : null;
      out.cpu = Number.isFinite(+sy.cpu) && sy.cpu !== null ? Math.round(+sy.cpu) : null; out.mem = Number.isFinite(+sy.memoire_pct) && sy.memoire_pct !== null ? Math.round(+sy.memoire_pct) : null;
      const imgs = Array.isArray(E.images) ? E.images.filter(x => x && x.t).sort((a, b) => b.t - a.t) : [];
      out.image = imgs[0] ? { t: imgs[0].t, titre: propre(imgs[0].titre, 40), poste: imgs[0].poste } : null;
      out.tdispo = Number.isFinite(+E.taches_dispo) && E.taches_dispo !== null ? +E.taches_dispo : null;
      out.langue = langueProjet(out);
      return out;
    }

    // Langue de l'ensemble des données (tâches des postes, roadmap, décisions, commits) : un titre court sans indice (« Rocher
    // moussu », « Cadrage ») prend la langue du projet. Il faut une nette majorité, sinon on ne tranche pas.
    function langueProjet(o) {
      const l = [];
      for (const id of o.ordre) { const x = o.postes[id]; l.push(x.tache, x.etape, x.suite, x.p && x.p.mission); }
      for (const id in o.taches) l.push(o.taches[id].titre);
      o.jalons.forEach(j => l.push(j.titre)); o.decisions.forEach(d => l.push(d.titre)); if (o.commit) l.push(o.commit.sujet);
      let fr = 0, en = 0; for (const t of l) { const g = t && langueDe(t); if (g === 'fr') fr++; else if (g === 'en') en++; }
      return fr >= 3 && fr >= 3 * en ? 'fr' : en >= 3 && en >= 3 * fr ? 'en' : null;
    }
    // ---------------- événements : ce qui a changé depuis le dernier rafraîchissement
    function pousser(ev) {
      ev.t = now(); ev.pas_avant = ev.t + (ev.delai || 0); ev.prio = PRIO[ev.type] || 1;
      const cle = ev.type + ':' + (ev.poste || '') + ':' + (ev.cle || '');
      for (let i = FILE.length - 1; i >= 0; i--) {
        const f = FILE[i];
        if (f.k === cle && f.type === 'pct' && ev.type === 'pct') { FILE.splice(i, 1); ev.t = f.t; continue; }   // même % mis à jour : pas un écart
        if (f.k === cle || (ev.poste && f.poste === ev.poste && ['pct', 'etape'].includes(f.type) && ['fini', 'bloque', 'pct', 'etape', 'compile_ok', 'compile_ko'].includes(ev.type))) { FILE.splice(i, 1); ecarter(f.type, 'remplace'); }
      }
      ev.k = cle; FILE.push(ev); FILE.sort((a, b) => b.prio - a.prio || b.t - a.t);
      while (FILE.length > FILE_MAX) ecarter(FILE.pop().type, 'file_pleine');
    }
    function observer() {
      const P = photo();
      if (!PREC) { PREC = P; for (const id in P.postes) ANNONCE[id] = P.postes[id].pct; return []; }
      const A = PREC, avant = FILE.length, n = now();
      for (const id of P.ordre) {
        const x = P.postes[id], y = A.postes[id];
        if (!y) { pousser({ type: 'embauche', poste: id, delai: 9000 }); ANNONCE[id] = x.pct; ARRIVES[id] = n; continue; }
        const fini = (x.etat === 'fini' && y.etat !== 'fini') || (x.pct === 100 && y.pct !== null && y.pct < 100);
        if (fini && (x.tache || y.tache)) pousser({ type: 'fini', poste: id, d: { tache: x.tache || y.tache } });
        else if (x.etat === 'bloque' && y.etat !== 'bloque') pousser({ type: 'bloque', poste: id });
        else if (y.etat === 'bloque' && x.etat === 'travaille') pousser({ type: 'debloque', poste: id });
        else if (x.etat === 'travaille' && x.pct !== null && x.pct < 100) {
          const a0 = ANNONCE[id] == null ? y.pct : ANNONCE[id];
          // un bond d'au moins 10 points depuis le dernier % DIT, et au plus un échange « % » joué par poste toutes les 6 min.
          // ANNONCE et PCT_POSTE ne bougent qu'au moment où l'échange est joué (voir jouer) : un % remplacé ou périmé ne
          // bloque rien et le bond suivant part toujours de la dernière valeur réellement annoncée.
          if (a0 !== null && a0 !== undefined && x.pct - a0 >= 10 && !(PCT_POSTE[id] && n - PCT_POSTE[id] < PAUSE_PCT_POSTE)) {
            pousser({ type: 'pct', poste: id, d: { pct0: a0, saut: x.pct - a0, moitie: a0 < 50 && x.pct >= 50 ? 1 : 0 } });
          } else if (x.etape && y.etape && x.etape !== y.etape) pousser({ type: 'etape', poste: id, d: { etape0: y.etape } });
        }
        if (x.pct !== null && (ANNONCE[id] == null || x.pct < ANNONCE[id])) ANNONCE[id] = x.pct;
        if (x.comp && x.comp !== y.comp && x.tache) pousser({ type: x.comp === 'ok' ? 'compile_ok' : 'compile_ko', poste: id });
      }
      for (const id of A.ordre) if (!P.postes[id]) pousser({ type: 'renvoi', cle: id, d: { parti: A.postes[id].nom } });
      if (P.frais && A.frais) {   // git, santé et mur d'images : seulement entre deux états à jour (sinon : faux départs)
        const nouveaux = P.commits.filter(h => !A.commits.includes(h));
        if (nouveaux.length && P.commit && A.commits.length) pousser({ type: 'commit', cle: P.commit.hash, d: { nbc: nouveaux.length } });
        if (P.sature !== A.sature) pousser({ type: P.sature ? 'sante' : 'sante_ok' });
        if (P.image && (!A.image || P.image.t > A.image.t) && P.image.titre) pousser({ type: 'image', poste: P.postes[P.image.poste] ? P.image.poste : '', cle: String(P.image.t) });
      }
      const decA = new Set(A.decisions.map(d => d.id)), neuve = P.decisions.find(d => !decA.has(d.id));
      if (neuve) pousser({ type: 'decision', cle: neuve.id, delai: 10000, d: { dec: propre(neuve.titre, 60, true) } });
      for (const id in P.taches) {
        const x = P.taches[id], y = A.taches[id]; if (!y || x.statut === y.statut) continue;
        const type = x.statut === 'verse' ? 'verse' : x.statut === 'pret' ? 'pret' : x.statut === 'en_cours' && y.statut === 'a_faire' ? 'commence' : null;
        if (type) pousser({ type, poste: P.postes[x.poste] ? x.poste : '', cle: id, d: { tache: propre(x.titre), id, jalonId: x.jalon } });
      }
      for (const j of P.jalons) { const k = A.jalons.find(z => z.id === j.id); if (k && j.ferme && !k.ferme) pousser({ type: 'jalon', cle: j.id, d: { jalon: propre(j.titre, 40) } }); }
      PREC = P;
      for (let i = FILE.length - 1; i >= 0; i--) if (n - FILE[i].t > 15 * MIN) { ecarter(FILE[i].type, 'perime'); FILE.splice(i, 1); }
      return FILE.slice(avant);
    }

    // téléphone : 2 répliques au plus ; perso au travail : 2 répliques pour l'ambiance, 3 pour un événement (lisibilité)
    const court = (l, evenement) => S.app() ? 2 : (!evenement && l.some(y => y && y.etat === 'travaille')) ? 2 : 3;
    // ---------------- choix des personnages
    const visibles = () => (PREC ? PREC.ordre.map(id => PREC.postes[id]) : []);
    const ancien = l => l.slice().sort((u, v) => (PARLE[u.id] || 0) - (PARLE[v.id] || 0) + (Math.random() - .5) * 20000);
    function chef(exclus) {
      const l = visibles().filter(x => x.cat === 'direction' && !exclus.includes(x.id));
      return l.length ? l[0].id : 'assistant';
    }
    function interlocuteur(x, prefer) {
      const l0 = visibles().filter(y => y.id !== x.id), anciens = l0.filter(y => !(ARRIVES[y.id] && now() - ARRIVES[y.id] < 5 * MIN)), l = anciens.length ? anciens : l0;
      if (!l.length) return null;
      if (prefer === 'relecture') { const r = l.filter(y => y.cat === 'relecture'); if (r.length) return ancien(r)[0]; }
      // voisins : bureaux côte à côte dans la même rangée du plan (positions réelles, pas l'ordre des postes)
      const px = S.place && S.place(x.i), voisins = px ? l.filter(y => { const q = S.place(y.i); return q && Math.abs(q[1] - px[1]) < .3 && Math.abs(q[0] - px[0]) < 4.5; }) : [];
      const libres = l.filter(y => y.etat !== 'travaille');
      const pool = Math.random() < .5 && voisins.length ? voisins : libres.length ? libres : l;
      return ancien(pool)[0];
    }

    // ---------------- données d'un échange
    // l'interlocuteur parle de SA propre tâche (seulement s'il y travaille vraiment)
    function tacheDe(b, x, d) {
      if (b && x && b.id !== x.id && b.etat === 'travaille' && b.tache && b.tache !== d.tache) { d.tacheB = b.tache; if (b.pct !== null && b.pct < 100) d.pctB = b.pct; }
      return d;
    }
    function donneesGlobales(P) {
      const L = lg(), d = {};
      if (P.v1 !== null) d.v1 = P.v1;
      const jc = P.jalonEnCours || P.jalons.find(j => !j.ferme);
      if (jc) { d.jalon = propre(jc.titre, 40); if (Number.isFinite(+jc.pct) && jc.pct !== null) d.jpct = Math.round(+jc.pct); }
      if (Number.isFinite(+P.faites) && +P.faites > 0 && +P.total > 0) { const f = +P.faites; d.faites = L === 'fr' ? (f === 1 ? 'une tâche versée' : f + ' tâches versées') : (f === 1 ? 'one task merged' : f + ' tasks merged'); d.total = P.total; }
      if (P.commit) { d.commit = propre(P.commit.sujet, 50); d.heure_c = P.commit.h || null; }
      if (P.ncj !== null && P.ncj > 0) { d.ncj = L === 'fr' ? (P.ncj === 1 ? 'un commit' : P.ncj + ' commits') : (P.ncj === 1 ? 'one commit' : P.ncj + ' commits'); d.ncj_plus = P.ncj >= 3 ? 1 : 0; }
      const decs = P.decisions; if (decs.length) { d.dec = propre(decs[0].titre, 60, true); d.nbd_d = L === 'fr' ? pluriel(decs.length, 'Une décision', 'décisions') : pluriel(decs.length, 'One decision', 'decisions'); }
      d.maitre = S.maitre() || (L === 'fr' ? 'la personne aux commandes' : 'the boss');
      const nt = P.ordre.filter(id => P.postes[id].etat === 'travaille').length;
      if (nt) d.nbt_t = L === 'fr' ? pluriel(nt, 'Une personne', 'personnes') : pluriel(nt, 'One person', 'people');
      d.nbp = P.ordre.length;
      if (P.tdispo) d.tdispo = L === 'fr' ? (P.tdispo === 1 ? 'une seule tâche disponible' : P.tdispo + ' tâches disponibles') : (P.tdispo === 1 ? 'just one task available' : P.tdispo + ' tasks available');
      if (P.cpu !== null) d.cpu = P.cpu; if (P.mem !== null) d.mem = P.mem;
      if (P.alerte) d.alerte = P.alerte;
      if (P.image && P.image.titre && now() / 1000 - P.image.t < 6 * 3600) d.image = P.image.titre;
      const m = moment(); d.moment = MOMENTS[L][m].replace(/^./, c => c.toUpperCase()); d.moment_court = MOMENTS_COURTS[L][m];
      d.remarque = REMARQUES[L][m][(Math.random() * REMARQUES[L][m].length) | 0];
      return d;
    }
    // Le % et le temps restant viennent de sources différentes (progression d'un côté ; fin prévue, restant_min ou rythme
    // observé de l'autre) : le temps n'est cité qu'avec un % connu et s'il va avec lui (au plus 8 min par point restant,
    // 15 min de marge), sinon « 99 %, il me reste 50 min » se dirait.
    function resteCoherent(x) {
      if (x.reste === null || x.reste === undefined || !(x.reste > 0.5) || x.pct === null || x.pct === undefined || x.pct >= 100) return false;
      return x.reste <= Math.max(15, (100 - x.pct) * 8);
    }
    function donneesPoste(x, d) {
      if (!x) return d;
      d.A = x.nom; if (x.tache && x.etat === 'travaille') d.tache = x.tache;   // une tâche finie n'est jamais dite « en cours »
      if (x.pct !== null && x.pct !== undefined && x.pct < 100 && x.etat === 'travaille') d.pct = x.pct;
      if (resteCoherent(x) && x.etat === 'travaille') d.reste = S.duree(x.reste);
      if (x.suite) d.suite = x.suite; if (x.etape) d.etape = x.etape; if (x.attente) d.attente = x.attente;
      if (x.raison) d.raison = x.raison; if (x.outil) d.outil = x.outil; if (x.role) d.role = x.role; if (x.mission) d.mission = x.mission;
      d.objet = OBJETS[lg()][x.cat] || OBJETS[lg()].autre; d['cat_' + x.cat] = 1;
      return d;
    }
    // Une donnée dont la langue est l'autre langue n'est pas citée (la tâche de la roadmap garde alors son identifiant).
    // Langue du texte s'il en donne une, sinon celle du projet ; si ni l'un ni l'autre ne tranche, le titre est cité tel quel
    // (un nom propre comme « Nanite » ou « Boss 2 » n'a pas de langue).
    function accorder(d) {
      const L = lg(), LP = PREC ? PREC.langue : null;
      for (const k of TEXTES_LIBRES) {
        if (d[k] === undefined || d[k] === null) continue;
        const l = langueDe(d[k]) || LP; if (!l || l === L) continue;
        if (k === 'tache' && d.id) d.tache = d.id; else delete d[k];
      }
      return d;
    }

    // ---------------- rendu d'un gabarit
    const elider = s => lg() !== 'fr' ? s : s.replace(/\b([qQ])ue ([AEIOUYÀÂÉÈÊÎÔÛ])/g, "$1u'$2").replace(/(^|[\s(])([dD])e ([AEIOUYÀÂÉÈÊÎÔÛ][a-zà-ÿ])/g, "$1$2'$3")
      .replace(/(^|[\s(])([dD]|[qQ]u)e « (?=[AEIOUYÀÂÉÈÊÎÔÛaeiouyàâéèêîôûHh])/g, "$1$2'« ");
    function rendre(lignes, d) {
      const out = [];
      for (let l of lignes) {
        const conds = []; l = l.replace(/\{\?(\w+)\}/g, (_, k) => { conds.push(k); return ''; });
        if (conds.some(k => !d[k])) return null;
        const qui = l[0], corps = l.slice(2); let manque = false, aDonnee = false, nommee = false;
        let txt = corps.replace(/\{(\w+)\}/g, (_, k) => { const v = d[k]; if (v === null || v === undefined || v === '') { manque = true; return ''; } if (REELS.has(k)) aDonnee = true; if (NOMMEES.has(k)) nommee = true; return String(v); });
        if (manque) return null;
        if (lg() === 'en') txt = txt.replace(/(\d) %/g, '$1%');
        out.push({ qui, texte: elider(txt).replace(/^./, c => c.toUpperCase()), reel: aDonnee, nommee });
      }
      return out;
    }
    // un gabarit déjà joué ne revient pas avant 20 min (ni parmi les 12 derniers) ; à défaut, le plus ancien hors des 4 derniers
    function choisir(sujet, d, roles, max) {
      const L = lg(), liste = (G[L] && G[L][sujet]) || [], n = now();
      const vu = id => { for (let k = MEMO.g.length - 1; k >= 0; k--) if (MEMO.g[k][0] === id) return MEMO.g[k][1]; return 0; };
      const derniers = MEMO.g.slice(-12).map(x => x[0]), tout_derniers = MEMO.g.slice(-4).map(x => x[0]);
      const cand = [];
      liste.forEach((g, i) => {
        const id = sujet + '#' + i; if (tout_derniers.includes(id) || g.length > (max || 3)) return;   // jamais une question coupée de sa réponse
        if (g.some(l => l.replace(/\{\?\w+\}/g, '')[0] === 'c') && !roles.c) return;
        const r = rendre(g, d); if (!r) return;
        if (r.some(x => dejaDit(x.texte))) return;
        const t = vu(id);
        cand.push({ id, lignes: r, frais: !derniers.includes(id) && (!t || n - t > GABARIT_MIN), t });
      });
      if (!cand.length) return null;
      let pool = cand.filter(c => c.frais);
      if (!pool.length) { pool = cand.slice().sort((a, b) => a.t - b.t).slice(0, 2); ecarter(sujet, 'gabarits_epuises'); }
      // tirage pondéré : une réplique qui nomme une donnée (tâche, commit, décision…) compte un peu plus
      const poids = pool.map(c => .25 + 1.6 * Math.pow(c.lignes.filter(x => x.reel).length / c.lignes.length, 1.5) + (c.lignes.some(x => x.nommee) ? .3 : 0));
      let r = Math.random() * poids.reduce((a, b) => a + b, 0);
      for (let i = 0; i < pool.length; i++) { r -= poids[i]; if (r <= 0) return pool[i]; }
      return pool[pool.length - 1];
    }

    // ---------------- préparer un échange (événement ou ambiance)
    function depuisEvenement(ev) {
      const P = PREC; if (!P) return null;
      const d = donneesGlobales(P), roles = {};
      let x = ev.poste ? P.postes[ev.poste] : null;
      if (ev.type === 'renvoi' || ev.type === 'commit' || ev.type === 'decision' || ev.type === 'jalon' || ev.type === 'sante' || ev.type === 'sante_ok' || ((ev.type === 'image' || ev.type === 'verse' || ev.type === 'pret' || ev.type === 'commence') && !x)) {
        const l = ancien(visibles()); x = l[0] || null;
      }
      if (!x) return null;
      donneesPoste(x, d); Object.assign(d, ev.d || {});
      if (ev.type === 'fini') { d.pct = null; d.reste = null; }
      if (ev.type === 'pct') { d.pct = x.pct; d.saut = x.pct - ev.d.pct0; if (d.saut < 1) return null; }
      if (ev.type === 'commit' && P.commit) { d.commit = propre(P.commit.sujet, 50); d.nbc = ev.d.nbc >= 2 ? ev.d.nbc : null; }
      if (['verse', 'pret', 'commence'].includes(ev.type)) {
        d.id = ev.d.id; d.tache = ev.d.tache; const j = P.jalons.find(z => z.id === ev.d.jalonId);
        if (j) { d.jalon = propre(j.titre, 40); d.jpct = Number.isFinite(+j.pct) && j.pct !== null ? Math.round(+j.pct) : null; } else { d.jalon = null; d.jpct = null; }
        if (ev.type !== 'verse') d.faites = null;
      }
      if (ev.type === 'jalon') {
        const i = P.jalons.findIndex(z => z.id === ev.cle), suiv = P.jalons.slice(i + 1).find(z => !z.ferme);
        d.jalon2 = suiv ? propre(suiv.titre, 40) : null; const reste = P.jalons.filter(z => !z.ferme).length;
        d.jreste = lg() === 'fr' ? (reste ? pluriel(reste, 'Un seul', 'jalons') : 'Aucun') : (reste ? pluriel(reste, 'Just one', 'milestones') : 'None');
      }
      if (ev.type === 'image' && P.image) d.image = P.image.titre;
      d.auteur = ev.type === 'image' && !!ev.poste ? 1 : 0; d.proprio = ['verse', 'pret', 'commence'].includes(ev.type) && !!ev.poste ? 1 : 0;   // « j'ai… » seulement pour le vrai poste
      if (ev.type === 'compile_ok' || ev.type === 'compile_ko') { d.tache = x.tache; }
      roles.a = x.id; const b = interlocuteur(x, ['fini', 'pret', 'compile_ko'].includes(ev.type) ? 'relecture' : null);
      roles.b = b ? b.id : (x.id !== 'assistant' ? 'assistant' : null); if (!roles.b) return null;
      const c = chef([roles.a, roles.b]); roles.c = c !== roles.a && c !== roles.b ? c : null;
      if (b) d.B = b.nom; d.relect = b && b.cat === 'relecture' ? 1 : 0; tacheDe(b, x, d);
      accorder(d);
      const g = choisir(ev.type, d, roles, court([x, b], true)); if (!g) return null;
      return { sujet: ev.type, evenement: true, gabarit: g.id, lignes: g.lignes, roles, travaille: [x, b].some(y => y && y.etat === 'travaille'), pctDit: ev.type === 'pct' ? x.pct : null };
    }
    function ambiance() {
      const P = PREC; if (!P) return null;
      const tous = visibles(); if (!tous.length) return null;
      const dG = donneesGlobales(P), cands = [];
      const trav = tous.filter(x => x.etat === 'travaille' && x.tache), att = tous.filter(x => x.etat === 'attend' && x.attente),
        sui = tous.filter(x => x.suite && x.etat !== 'travaille'), lib = tous.filter(x => x.etat === 'disponible'), tch = tous.filter(x => x.tache && x.etat === 'travaille');
      const ajoute = (sujet, x, poids) => { if (x) cands.push({ sujet, x, poids: poids * (RECENTS_S.slice(-4).includes(sujet) ? .15 : 1) }); };
      ajoute('travail', ancien(trav)[0], AMBIANCE.travail);
      if (trav.length >= 2) ajoute('duo', ancien(trav)[0], AMBIANCE.duo);
      ajoute('attente', ancien(att)[0], AMBIANCE.attente);
      ajoute('suite', ancien(sui)[0], AMBIANCE.suite);
      if (lib.length >= 2) ajoute('libre', ancien(lib)[0], AMBIANCE.libre);
      if (dG.v1 !== undefined || dG.jalon) ajoute('roadmap', ancien(tous)[0], AMBIANCE.roadmap);
      if (dG.dec) ajoute('attente_decisions', ancien(tous)[0], AMBIANCE.attente_decisions);
      if (dG.ncj || dG.commit) ajoute('commits_jour', ancien(tous)[0], AMBIANCE.commits_jour);
      ajoute('heure', ancien(tch.length ? tch : tous)[0], AMBIANCE.heure);
      ajoute('metier', ancien(tch)[0], AMBIANCE.metier);
      if (dG.cpu !== undefined && P.sature === false) ajoute('pc', ancien(tous)[0], AMBIANCE.pc);
      if (dG.image) ajoute('nouveau', ancien(tous)[0], AMBIANCE.nouveau);
      const essais = cands.slice();
      while (essais.length) {
        const tot = essais.reduce((s, c) => s + c.poids, 0); let r = Math.random() * tot, k = 0;
        for (; k < essais.length - 1; k++) { r -= essais[k].poids; if (r <= 0) break; }
        const c = essais.splice(k, 1)[0], x = c.x, d = Object.assign({}, dG), roles = { a: x.id };
        donneesPoste(x, d);
        let b;
        if (c.sujet === 'duo') b = ancien(trav.filter(y => y.id !== x.id))[0];
        else if (c.sujet === 'libre') b = ancien(lib.filter(y => y.id !== x.id))[0];   // deux persos vraiment libres
        else b = interlocuteur(x);
        if (c.sujet === 'duo' && b) { d.tache2 = b.tache; if (b.pct !== null && b.pct < 100) d.pct2 = b.pct; d.devant = b.pct !== null && x.pct !== null && b.pct > x.pct ? 1 : 0; }
        if (c.sujet === 'heure' && b && b.tache && b.etat === 'travaille') d.tache2 = b.tache;
        roles.b = b ? b.id : 'assistant'; if (b) d.B = b.nom;
        if (roles.b === roles.a) continue;
        if (c.sujet !== 'duo') tacheDe(b, x, d);
        const ch = chef([roles.a, roles.b]); roles.c = ch !== roles.a && ch !== roles.b ? ch : null;
        accorder(d);
        const g = choisir(c.sujet, d, roles, court([x, b], false)); if (!g) continue;
        return { sujet: c.sujet, evenement: false, gabarit: g.id, lignes: g.lignes, roles, travaille: [x, b].some(y => y && y.etat === 'travaille') };
      }
      return null;
    }
    function repli() {
      const tous = visibles(), l = S.repli()[lg()] || S.repli().en; if (tous.length < 2) return null;
      const a = ancien(tous)[0], b = ancien(tous.filter(y => y.id !== a.id))[0];
      const derniers = MEMO.g.slice(-2).map(x => x[0]);
      const choix = l.map((x, i) => ({ x, i })).filter(o => !derniers.includes('repli#' + o.i) && !dejaDit(o.x[0]));
      if (!choix.length) return null;
      const o = choix[(Math.random() * choix.length) | 0];
      return { sujet: 'repli', evenement: false, gabarit: 'repli#' + o.i, lignes: [{ qui: 'a', texte: o.x[0], reel: false }, { qui: 'b', texte: o.x[1], reel: false }], roles: { a: a.id, b: b.id }, travaille: false };
    }

    // ---------------- jouer un échange
    // Téléphone : un échange ne démarre que si aucune autre bulle n'est ouverte, et chaque réplique remplace la précédente
    // de l'échange : il n'occupe jamais qu'une bulle, donc la réponse a toujours sa place (jamais une question seule).
    function jouer(ech) {
      let lignes = ech.lignes.slice();
      const tel = S.app(); if (tel) lignes = lignes.slice(0, 2);   // filet : le choix du gabarit respecte déjà la limite
      let t = 0; const n0 = ++NUM, montrees = [];
      ECH.push({ n: n0, t: now(), sujet: ech.sujet, gabarit: ech.gabarit, evenement: ech.evenement, lignes: lignes.length }); if (ECH.length > 300) ECH.shift();
      const reserve = lignes.map(l => { const r = [l.texte, now()]; MEMO.p.push(r); return r; });   // un autre échange ne la reprend pas
      const liberer = i => { for (let k = i; k < reserve.length; k++) { const j = MEMO.p.indexOf(reserve[k]); if (j >= 0) MEMO.p.splice(j, 1); } };
      let coupe = false;
      lignes.forEach((l, i) => {
        const qui = ech.roles[l.qui]; if (!qui) return;
        const sec = Math.min(8, 4 + l.texte.length / 22);
        setTimeout(() => {
          if (coupe) return;
          if (!S.permis()) {   // onglet caché, mode absent… : l'échange s'arrête et la question déjà posée disparaît avec lui
            coupe = true; liberer(i); montrees.forEach(q => { if (S.taire) S.taire(q); }); const e = ECH.find(z => z.n === n0); if (e) e.coupe = true; return;
          }
          if (tel && i > 0) { const prec = montrees[montrees.length - 1]; if (prec && prec !== qui && S.taire) S.taire(prec); }
          S.dire(qui, l.texte, sec); montrees.push(qui);
          const nom = qui === 'assistant' ? 'assistant' : (PREC && PREC.postes[qui] ? PREC.postes[qui].nom : qui);
          JOURNAL.push({ n: n0, t: now(), h: new Date().toTimeString().slice(0, 8), sujet: ech.sujet, gabarit: ech.gabarit, evenement: ech.evenement, qui, nom, texte: l.texte, reel: l.reel, nommee: !!l.nommee, langue: lg(), rang: i, sur: lignes.length, tel: !!tel, bulles: S.bulles() });
          if (JOURNAL.length > 600) JOURNAL.splice(0, JOURNAL.length - 600);
          if (i === 0 && !ech.travaille && Math.random() < .25) setTimeout(() => S.gobelet(), 900);
        }, t);
        t += Math.min(5600, 2300 + l.texte.length * 45);
      });
      MEMO.g.push([ech.gabarit, now()]); RECENTS_S.push(ech.sujet); RECENTS_S.splice(0, Math.max(0, RECENTS_S.length - 8));
      for (const k of Object.values(ech.roles)) if (k) PARLE[k] = now();
      if (ech.evenement) { DERNIER_TYPE[ech.sujet] = now(); SUITE_EV++; } else SUITE_EV = 0;
      occupeJusqua = now() + t + (rapide ? 1500 : 4000);
      sauver();
    }
    // Ordre de passage : un événement important tout de suite ; un événement ordinaire seulement si son type n'a pas parlé
    // récemment, et jamais deux d'affilée quand l'ambiance attend son tour.
    function prochainEvenement(n) {
      for (const e of FILE) {
        if (e.pas_avant > n) continue;
        if (e.prio >= HAUTE) return e;
        const p = PAUSE_TYPE[e.type] || 0; if (p && DERNIER_TYPE[e.type] && n - DERNIER_TYPE[e.type] < (rapide ? p / 4 : p)) continue;
        if (SUITE_EV >= 1 && n >= prochaineAmbiance) continue;
        return e;
      }
      return null;
    }
    function tic(forcer) {
      if (!S.permis() && !forcer) return false;
      if (!PREC) observer();
      const n = now(); if (!forcer && n < occupeJusqua) return false;
      if (S.app() && S.bulles() >= 1) return false;
      const ev = prochainEvenement(n);
      if (ev) {
        FILE.splice(FILE.indexOf(ev), 1); const e = depuisEvenement(ev);
        if (e) { jouer(e); if (ev.type === 'pct' && e.pctDit != null) { ANNONCE[ev.poste] = e.pctDit; PCT_POSTE[ev.poste] = n; } return true; }
        ecarter(ev.type, 'sans_gabarit');
      }
      if (!forcer && n < prochaineAmbiance) return false;
      const amb = S.rythme() === 'vivante' ? [25, 40] : [35, 55], [lo, hi] = rapide ? [5, 8] : amb;
      prochaineAmbiance = n + (lo + Math.random() * (hi - lo)) * 1000;
      const e = ambiance() || repli(); if (e) { jouer(e); return true; }
      return false;
    }
    function stats() {
      const l = JOURNAL, n = l.length, dist = new Set(l.map(x => x.texte)).size, reel = l.filter(x => x.reel).length, nom = l.filter(x => x.nommee).length;
      const parSujet = {}; l.forEach(x => { parSujet[x.sujet] = (parSujet[x.sujet] || 0) + 1; });
      let repetes30 = 0; l.forEach((x, i) => { if (l.slice(0, i).some(y => y.texte === x.texte && x.t - y.t < MEMOIRE)) repetes30++; });
      let gabaritsSuite = 0, sujetsSuite = 0, gab20 = 0;
      ECH.forEach((e, i) => { if (i && ECH[i - 1].gabarit === e.gabarit) gabaritsSuite++; if (i && ECH[i - 1].sujet === e.sujet) sujetsSuite++;
        if (ECH.slice(0, i).some(y => y.gabarit === e.gabarit && e.t - y.t < GABARIT_MIN)) gab20++; });
      const parGab = {}; ECH.forEach(e => { parGab[e.gabarit] = (parGab[e.gabarit] || 0) + 1; });
      const qui = {}; l.forEach(x => { qui[x.nom] = (qui[x.nom] || 0) + 1; });
      // téléphone : un échange dont une réplique a été montrée mais pas la suivante
      const orphelins = ECH.filter(e => { const r = l.filter(x => x.n === e.n); return !e.coupe && r.length && r.length < e.lignes && now() - e.t > 30000; }).length;
      return { repliques: n, distinctes: dist, part_distinctes: n ? Math.round(1000 * dist / n) / 10 : 0, avec_donnee: reel, part_donnee: n ? Math.round(1000 * reel / n) / 10 : 0,
        avec_donnee_nommee: nom, part_donnee_nommee: n ? Math.round(1000 * nom / n) / 10 : 0,
        repetees_moins_30min: repetes30, echanges: ECH.length, gabarits_distincts: Object.keys(parGab).length, gabarit_max: Math.max(0, ...Object.values(parGab)),
        meme_gabarit_moins_20min: gab20, meme_gabarit_daffilee: gabaritsSuite, meme_sujet_daffilee: sujetsSuite,
        echanges_evenements: ECH.filter(e => e.evenement).length, echanges_ambiance: ECH.filter(e => !e.evenement).length, echanges_incomplets: orphelins, echanges_coupes_onglet_cache: ECH.filter(e => e.coupe).length,
        par_sujet: parSujet, par_personnage: qui, file: FILE.map(e => e.type), ecartes: Object.assign({}, ECARTES) };
    }
    return { observer, tic, stats, journal: () => JOURNAL.slice(), echanges: () => ECH.slice(), file: () => FILE.slice(), rapide(v) { rapide = !!v; prochaineAmbiance = 0; },
      propre, etatCompile, outilDe, categorie, oublier() { MEMO = { p: [], g: [] }; sauver(); } };
  }
  window.ConversationsStudio = { creer, GABARITS: G, etatCompile, langueDe };
})();
