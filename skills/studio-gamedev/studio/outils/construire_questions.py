# -*- coding: utf-8 -*-
"""Construit studio/questions.fr.json et studio/questions.en.json.

Source unique des questions de la page (les deux langues côte à côte, pour
qu'elles restent alignées). references/questionnaire.md en est la version
lisible : si tu changes une question, change-la ici et relance :

    python -I -B studio/outils/construire_questions.py

Builds both question files from one bilingual source. Standard library only.
"""
import json
import os
import sys
for _flux in (sys.stdout, sys.stderr):                 # S6 : sortie en UTF-8, même redirigée (Windows)
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
sys.dont_write_bytecode = True   # jamais de __pycache__ dans le dossier du skill

ICI = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(ICI)
if STUDIO not in sys.path:
    sys.path.insert(0, STUDIO)
import jsonio  # noqa: E402  (C4 : studio/jsonio.py)


def O(id, illus, fr, en, dfr="", den="", vfr=(), ven=(), si=None):
    """Une option (carte). illus = nom du dessin dans studio/cartes/."""
    return dict(id=id, illus=illus, fr=fr, en=en, dfr=dfr, den=den,
                vfr=list(vfr), ven=list(ven), si=si)


def Q(id, chap, type, fr, en, afr, aen, options=(), rec=None, rapide=False,
      si=None, depuis=None, max=None, libre=True, passer=True, extra=None):
    return dict(id=id, chap=chap, type=type, fr=fr, en=en, afr=afr, aen=aen,
                options=list(options), rec=rec, rapide=rapide, si=si,
                depuis=depuis, max=max, libre=libre, passer=passer,
                extra=extra or {})


CHAPITRES = [
    ("accueil", "Accueil", "Welcome", []),
    ("vision", "Vision", "Vision", ["bureau_direction", "tableau_piliers", "enseigne"]),
    ("gameplay", "Gameplay", "Gameplay", ["bureau_code", "tableau_boucle"]),
    ("monde", "Monde", "World", ["table_level_design", "etagere_livres"]),
    ("da", "Direction artistique", "Art direction", ["atelier_art"]),
    ("son", "Son", "Sound", ["cabine_son"]),
    ("technique", "Technique", "Tech", ["salle_moteur", "baie_reseau"]),
    ("ambition", "Ambition", "Scope", ["mur_roadmap", "cloche_decisions"]),
    ("personnages", "Personnages", "Characters", ["personnages", "porte_equipe"]),
    ("fin", "Récapitulatif", "Summary", []),
]

# ---------------------------------------------------------------- genres
GENRES = [
    O("action_aventure", "epee", "Action / aventure", "Action / adventure",
      "Explorer, se battre, avancer dans une aventure.", "Explore, fight, push through an adventure.",
      ["action", "aventure"], ["action", "adventure"]),
    O("survie", "feu_camp", "Survie / crafting", "Survival / crafting",
      "Récolter, fabriquer, tenir face au monde.", "Gather, craft, hold out against the world.",
      ["survie", "crafting", "fabrication"], ["survival", "crafting"]),
    O("rpg", "bouclier", "RPG", "RPG",
      "Un héros qui grandit : stats, quêtes, choix.", "A hero who grows: stats, quests, choices.",
      ["rpg", "jeu de rôle", "role"], ["rpg", "role playing"]),
    O("plateforme", "plateforme", "Plateforme", "Platformer",
      "Courir, sauter, la précision avant tout.", "Run, jump, precision first.",
      ["plateforme", "plateformer", "saut"], ["platformer", "platform", "jump"]),
    O("roguelike", "donjon", "Roguelike / roguelite", "Roguelike / roguelite",
      "Des parties courtes, générées, on recommence plus fort.", "Short generated runs, start over stronger.",
      ["roguelike", "roguelite", "rogue"], ["roguelike", "roguelite", "rogue"]),
    O("fps", "viseur", "Tir (FPS / TPS)", "Shooter (FPS / TPS)",
      "Viser, tirer, se déplacer vite.", "Aim, shoot, move fast.",
      ["tir", "fps", "shooter", "tps"], ["shooter", "fps", "tps", "shooting"]),
    O("strategie", "echecs", "Stratégie", "Strategy",
      "Réfléchir avant d'agir : tour par tour ou temps réel.", "Think before acting: turn-based or real time.",
      ["stratégie", "tactique", "tour par tour"], ["strategy", "tactics", "turn based"]),
    O("tower_defense", "tour", "Tower defense", "Tower defense",
      "Placer des défenses, tenir les vagues.", "Place defenses, survive the waves.",
      ["tower defense", "défense", "tours"], ["tower defense", "defense", "towers"]),
    O("gestion", "ville", "Gestion / construction", "Management / city building",
      "Bâtir, organiser, faire tourner un système.", "Build, organise, keep a system running.",
      ["gestion", "construction", "ville", "tycoon"], ["management", "city builder", "tycoon"]),
    O("simulation", "avion", "Simulation", "Simulation",
      "Reproduire une activité : conduite, ferme, vol…", "Recreate an activity: driving, farming, flying…",
      ["simulation", "simu"], ["simulation", "sim", "simulator"]),
    O("course", "course", "Course", "Racing",
      "Vitesse, trajectoires, chronomètre.", "Speed, racing lines, the clock.",
      ["course", "voiture", "racing"], ["racing", "race", "cars"]),
    O("sport", "ballon", "Sport", "Sports",
      "Un sport réel ou inventé.", "A real or invented sport.",
      ["sport", "foot", "ballon"], ["sports", "football", "ball"]),
    O("cartes", "cartes", "Jeu de cartes / deckbuilder", "Card game / deckbuilder",
      "Construire un paquet, jouer ses cartes.", "Build a deck, play your cards.",
      ["cartes", "deck", "deckbuilder"], ["cards", "deck", "deckbuilder"]),
    O("puzzle", "puzzle", "Puzzle / réflexion", "Puzzle",
      "Des énigmes, le déclic qui fait plaisir.", "Puzzles and that satisfying click.",
      ["puzzle", "réflexion", "énigme"], ["puzzle", "logic", "brain"]),
    O("visual_novel", "bulle", "Visual novel / narratif", "Visual novel / narrative",
      "Lire, choisir, vivre une histoire.", "Read, choose, live a story.",
      ["visual novel", "narratif", "histoire"], ["visual novel", "narrative", "story"]),
    O("horreur", "horreur", "Horreur", "Horror",
      "Peur, ombre, ressources rares.", "Fear, darkness, scarce resources.",
      ["horreur", "peur", "épouvante"], ["horror", "scary", "fear"]),
    O("rythme", "note", "Rythme / musique", "Rhythm / music",
      "Jouer en mesure, la musique mène.", "Play on the beat, the music leads.",
      ["rythme", "musique"], ["rhythm", "music"]),
    O("bac_a_sable", "cubes", "Bac à sable", "Sandbox",
      "Un monde de jouets, le joueur se fixe ses buts.", "A toy world, players set their own goals.",
      ["bac à sable", "sandbox", "créatif"], ["sandbox", "creative"]),
]

ANGLE_3D = ["3d", "2_5d"]

Q_ = []
add = Q_.append

# ================================================================ accueil
add(Q("accueil.nom", "accueil", "nom",
      "Salut ! Je suis ton assistant. Comment je t'appelle ?",
      "Hi! I'm your assistant. What should I call you?",
      "Un prénom ou un pseudo : c'est comme ça que je te parlerai.",
      "A first name or a nickname: that's how I'll talk to you.",
      rapide=True, passer=False))
add(Q("accueil.mode", "accueil", "choix",
      "Comment on cadre ce jeu ?", "How do we set up this game?",
      "Le mode rapide déduit le reste et le marque « à confirmer » ; on pourra y revenir.",
      "Quick mode infers the rest and marks it \"to confirm\"; we can come back to it.",
      [O("rapide", "eclair", "Rapide", "Quick", "Une vingtaine de questions, 5 à 8 min.", "About twenty questions, 5 to 8 min.",
         ["rapide", "vite"], ["quick", "fast"]),
       O("complet", "carnet", "Complet", "Full", "Toutes les étapes, environ 25 min.", "Every step, about 25 min.",
         ["complet", "tout"], ["full", "complete", "everything"]),
       O("reprise", "marque_page", "Reprise", "Resume", "Je reprends un questionnaire commencé.", "Pick up where I left off.",
         ["reprise", "reprendre", "continuer"], ["resume", "continue"])],
      rec="rapide", rapide=True, libre=False, passer=False))
add(Q("accueil.experience", "accueil", "choix",
      "Tu as déjà fait des jeux ?", "Have you made games before?",
      "Je règle mes explications et mes conseils sur ton expérience.",
      "I'll pitch my explanations and advice to your experience.",
      [O("quelques", "pousse", "Quelques petits projets", "A few small projects", "Des essais, des tutos, une jam.", "Tests, tutorials, a jam.",
         ["quelques", "un peu", "petits projets"], ["a few", "some", "small projects"]),
       O("jamais", "graine", "Jamais", "Never", "Je découvre : explique-moi tout.", "I'm new: explain everything.",
         ["jamais", "débutant", "non"], ["never", "beginner", "no"]),
       O("plusieurs", "boites", "Oui, plusieurs sortis", "Yes, I've shipped several", "J'ai déjà publié des jeux.", "I've released games before.",
         ["plusieurs", "sortis", "publiés"], ["several", "shipped", "released"]),
       O("pro", "medaille", "Je suis pro", "I'm a professional", "C'est mon métier : va à l'essentiel.", "It's my job: keep it short.",
         ["pro", "professionnel", "métier"], ["pro", "professional"])],
      rec="quelques", rapide=True))
add(Q("accueil.personnages_quand", "accueil", "choix",
      "On crée nos têtes maintenant ou à la fin ?", "Do we design our looks now or at the end?",
      "Ton avatar et le mien. Par défaut on le fait à la fin, en récompense.",
      "Your avatar and mine. By default we do it at the end, as a treat.",
      [O("fin", "drapeau", "À la fin", "At the end", "On commence par le jeu.", "Game first.", ["fin", "après"], ["end", "later"]),
       O("maintenant", "miroir", "Maintenant", "Now", "On fait les personnages d'abord.", "Characters first.", ["maintenant", "tout de suite"], ["now", "first"])],
      rec="fin", libre=False))

# ================================================================ vision
add(Q("vision.pitch", "vision", "texte",
      "Raconte-moi ton jeu en 2 ou 3 phrases.",
      "Tell me about your game in 2 or 3 sentences.",
      "Ce qu'on fait, où, et ce qui le rend différent. Pas d'idée ? Dis-le, je t'en propose.",
      "What you do, where, and what makes it different. No idea yet? Say so and I'll suggest some.",
      rapide=True, passer=False, extra={"attend_deductions": True}))
add(Q("vision.emotion", "vision", "multi",
      "Qu'est-ce que le joueur doit ressentir ?", "What should the player feel?",
      "L'émotion principale guide la DA, le son et le rythme.", "The core emotion drives art, sound and pacing.",
      [O("tension", "bougie", "Tension / peur", "Tension / fear", "Le cœur qui bat.", "Heart pounding.", ["tension", "peur", "stress"], ["tension", "fear", "dread"]),
       O("maitrise", "cible", "Maîtrise / défi", "Mastery / challenge", "Progresser à force d'essais.", "Get better through practice.", ["maîtrise", "défi", "challenge"], ["mastery", "challenge", "skill"]),
       O("detente", "tasse", "Détente / contemplation", "Calm / contemplation", "Souffler, regarder.", "Breathe, take it in.", ["détente", "calme", "contemplation", "cosy"], ["calm", "relax", "cozy", "chill"]),
       O("decouverte", "boussole", "Découverte", "Discovery", "Voir ce qu'il y a derrière la colline.", "See what's over the hill.", ["découverte", "exploration", "curiosité"], ["discovery", "exploration", "wonder"]),
       O("puissance", "foudre", "Puissance", "Power", "Se sentir fort, tout balayer.", "Feel strong, sweep everything.", ["puissance", "fort"], ["power", "strong", "mighty"]),
       O("rire", "rire", "Rire", "Laughter", "Des situations drôles, du chaos.", "Funny situations, chaos.", ["rire", "humour", "drôle"], ["laughter", "fun", "funny"]),
       O("emotion_histoire", "coeur", "Émotion / attachement", "Emotion / attachment", "S'attacher, être touché.", "Care, be moved.", ["émotion", "attachement", "touchant"], ["emotion", "attachment", "moving"])],
      depuis="deductions", max=3))
add(Q("vision.piliers", "vision", "texte",
      "Les 3 piliers du jeu ?", "The game's 3 pillars?",
      "Trois idées que chaque fonction doit servir. Je t'en propose trois tirées de ton pitch.",
      "Three ideas every feature must serve. I'll suggest three from your pitch.",
      depuis="deductions", extra={"propositions_depuis": "deductions.propositions"}))
add(Q("vision.references", "vision", "texte",
      "Des jeux de référence ?", "Any reference games?",
      "« Comme X mais Y » : ça m'aide à viser juste.", "\"Like X but Y\": it helps me aim right.",
      depuis="deductions", extra={"propositions_depuis": "deductions.propositions"}))
add(Q("vision.motivation", "vision", "choix",
      "Pourquoi ce jeu ?", "Why this game?",
      "Ça change la façon dont on mesure la réussite.", "It changes how we measure success.",
      [O("plaisir", "coeur", "Pour le plaisir / apprendre", "For fun / to learn", "Le chemin compte autant que le jeu.", "The journey matters as much as the game.", ["plaisir", "apprendre", "fun"], ["fun", "learn", "hobby"]),
       O("vendre", "pieces", "Pour le vendre", "To sell it", "On pensera public et marché.", "We'll think audience and market.", ["vendre", "argent", "commercial"], ["sell", "money", "commercial"]),
       O("jam", "chrono", "Pour une jam / un concours", "For a jam / contest", "Délai court, thème imposé.", "Short deadline, set theme.", ["jam", "concours"], ["jam", "contest", "competition"]),
       O("public_precis", "public", "Pour un public précis", "For a specific audience", "Une classe, une asso, des proches…", "A class, a club, loved ones…", ["public", "association", "école"], ["audience", "school", "club"])],
      rec="plaisir"))
add(Q("genre.principal", "vision", "choix",
      "Quel est le genre principal de ton jeu ?", "What is your game's main genre?",
      "Le genre décide des systèmes qu'on construit en premier.", "Genre decides which systems we build first.",
      GENRES, rec="action_aventure", rapide=True, depuis="deductions"))
add(Q("genre.secondaire", "vision", "choix",
      "Un genre secondaire ?", "A secondary genre?",
      "Un mélange peut donner du caractère ; aucun, c'est très bien aussi.", "A blend can add character; none is fine too.",
      [O("aucun", "vide", "Aucun", "None", "On reste centré.", "Stay focused.", ["aucun", "non", "rien"], ["none", "no"])] + GENRES,
      rec="aucun", depuis="deductions"))
add(Q("genre.session", "vision", "choix",
      "Combien de temps dure une session de jeu ?", "How long is a typical play session?",
      "La durée d'une session règle le rythme et les sauvegardes.", "Session length sets pacing and saving.",
      [O("moyenne", "horloge", "20 à 60 min", "20 to 60 min", "Une soirée tranquille.", "A relaxed evening.", ["moyenne", "une heure"], ["medium", "an hour"]),
       O("courte", "sablier", "Courte (< 10 min)", "Short (< 10 min)", "Une pause, un trajet.", "A break, a commute.", ["courte", "rapide"], ["short", "quick"]),
       O("longue", "nuit", "Longue (> 1 h)", "Long (> 1 h)", "On s'y plonge.", "Deep dives.", ["longue", "des heures"], ["long", "hours"])],
      rec="moyenne"))
add(Q("public.cible", "vision", "choix",
      "Pour qui ?", "Who is it for?",
      "Le public décide de la difficulté et du ton.", "The audience shapes difficulty and tone.",
      [O("reguliers", "manette", "Joueurs réguliers", "Regular players", "Ils connaissent les codes.", "They know the conventions.", ["réguliers", "joueurs"], ["regular", "gamers"]),
       O("famille", "famille", "Grand public / familles", "Everyone / families", "Simple à prendre en main.", "Easy to pick up.", ["famille", "grand public", "enfants"], ["family", "casual", "kids"]),
       O("hardcore", "flamme", "Joueurs hardcore", "Hardcore players", "Ils veulent du défi.", "They want a challenge.", ["hardcore", "exigeant"], ["hardcore", "core"]),
       O("potes", "potes", "Mes potes et moi", "My friends and me", "Un jeu pour la bande.", "A game for the crew.", ["potes", "amis", "copains"], ["friends", "mates", "crew"])],
      rec="reguliers"))
add(Q("public.age", "vision", "choix",
      "Âge visé ?", "Target age rating?",
      "Une classification indicative : elle cadre la violence et le langage.", "An indicative rating: it frames violence and language.",
      [O("12", "age_12", "12 +", "12 +", "", "", ["douze"], ["twelve"]),
       O("tous", "age_tous", "Tout public", "Everyone", "", "", ["tout public", "tous"], ["everyone", "all ages"]),
       O("16", "age_16", "16 +", "16 +", "", "", ["seize"], ["sixteen"]),
       O("18", "age_18", "18 +", "18 +", "", "", ["dix-huit", "adulte"], ["eighteen", "adult", "mature"])],
      rec="12"))
add(Q("public.accessibilite", "vision", "multi",
      "Quelle accessibilité en priorité ?", "Which accessibility features first?",
      "Plus c'est prévu tôt, moins ça coûte.", "The earlier it's planned, the cheaper it is.",
      [O("sous_titres", "sous_titres", "Sous-titres et taille du texte", "Subtitles and text size", "", "", ["sous-titres", "texte"], ["subtitles", "text size"]),
       O("touches", "touches", "Touches remappables", "Remappable controls", "", "", ["touches", "remap"], ["remap", "controls", "keys"]),
       O("daltonisme", "daltonisme", "Daltonisme", "Colour blindness", "", "", ["daltonisme", "couleurs"], ["colour blind", "color blind"]),
       O("difficulte", "curseurs", "Difficulté réglable", "Adjustable difficulty", "", "", ["difficulté", "réglable"], ["difficulty", "assist"])],
      rec=["sous_titres", "touches"]))
add(Q("public.langues", "vision", "choix",
      "Le jeu sera dans quelles langues ?", "Which languages will the game ship in?",
      "On prépare la traduction dès le départ, même pour une seule langue.", "We set up translation from day one, even for one language.",
      [O("deux", "langues", "Ma langue et l'anglais", "My language and English", "", "", ["deux", "français et anglais", "bilingue"], ["two", "bilingual"]),
       O("anglais", "langue_une", "Anglais seul", "English only", "", "", ["anglais"], ["english"]),
       O("une", "langue_une", "Ma langue seule", "My language only", "", "", ["une seule", "français"], ["one", "my language"]),
       O("plus", "globe", "Plusieurs langues", "Several languages", "", "", ["plusieurs", "plus"], ["several", "many"])],
      rec="deux"))

# ================================================================ gameplay
add(Q("camera.dimension", "gameplay", "choix",
      "2D ou 3D ?", "2D or 3D?",
      "C'est le choix qui pèse le plus sur le temps de production.", "This choice weighs most on production time.",
      [O("2d", "plan_2d", "2D", "2D", "Sprites, tuiles, lisible et rapide.", "Sprites, tiles, readable and fast.", ["deux d", "2d"], ["two d", "2d"]),
       O("3d", "cube_3d", "3D", "3D", "Modèles, lumière, caméra libre.", "Models, lighting, free camera.", ["trois d", "3d"], ["three d", "3d"]),
       O("2_5d", "iso_25d", "2,5D", "2.5D", "Décor 3D, jeu sur un plan.", "3D scenery, played on a plane.", ["deux et demi", "2.5"], ["two and a half", "2.5"])],
      rec="3d", rapide=True, depuis="deductions"))
add(Q("camera.vue", "gameplay", "choix",
      "Où est la caméra ?", "Where is the camera?",
      "La caméra décide de ce que le joueur voit et de comment il vise.", "The camera decides what players see and how they aim.",
      [O("premiere_personne", "cam_fps", "1re personne", "First person", "À travers ses yeux.", "Through their eyes.", ["première personne", "fps", "yeux"], ["first person", "fps"], si={"camera.dimension": {"dans": ANGLE_3D}}),
       O("troisieme_personne", "cam_tps", "3e personne", "Third person", "Derrière l'épaule.", "Over the shoulder.", ["troisième personne", "épaule"], ["third person", "shoulder"], si={"camera.dimension": {"dans": ANGLE_3D}}),
       O("cote", "cam_cote", "De côté", "Side view", "Comme un plateformer.", "Like a platformer.", ["côté", "profil", "scrolling"], ["side", "side scroller"]),
       O("dessus", "cam_dessus", "Vue de dessus", "Top-down", "Le monde vu d'en haut.", "The world from above.", ["dessus", "top down"], ["top down", "overhead"]),
       O("isometrique", "cam_iso", "Isométrique", "Isometric", "En biais, comme une maquette.", "Angled, like a diorama.", ["isométrique", "iso"], ["isometric", "iso"]),
       O("ecran_fixe", "cam_fixe", "Écran fixe", "Fixed screen", "Une scène à la fois.", "One screen at a time.", ["fixe", "écran"], ["fixed", "single screen"], si={"camera.dimension": {"egal": "2d"}})],
      rec="troisieme_personne", rapide=True, depuis="deductions"))
add(Q("camera.controle", "gameplay", "choix",
      "Caméra libre ou guidée ?", "Free or guided camera?",
      "Une caméra guidée raconte mieux, une libre laisse explorer.", "A guided camera tells stories better; a free one lets you explore.",
      [O("libre", "cam_libre", "Libre", "Free", "Souris ou stick.", "Mouse or stick.", ["libre"], ["free"]),
       O("guidee", "rail", "Guidée / scriptée", "Guided / scripted", "Elle suit des rails.", "It follows rails.", ["guidée", "scriptée", "rail"], ["guided", "scripted", "rails"]),
       O("mixte", "cam_mixte", "Mixte", "Mixed", "Libre, avec des moments cadrés.", "Free, with framed moments.", ["mixte"], ["mixed", "both"])],
      rec="libre"))
add(Q("gameplay.verbe", "gameplay", "choix",
      "Que fait le joueur 80 % du temps ?", "What does the player do 80% of the time?",
      "Le verbe principal : tout le reste se construit autour.", "The core verb: everything else is built around it.",
      [O("explorer", "boussole", "Explorer", "Explore", "", "", ["explorer", "exploration"], ["explore", "exploration"]),
       O("combattre", "epee", "Combattre", "Fight", "", "", ["combattre", "combat", "se battre"], ["fight", "combat"]),
       O("construire", "marteau", "Construire", "Build", "", "", ["construire", "bâtir"], ["build", "construct"]),
       O("survivre", "feu_camp", "Survivre", "Survive", "", "", ["survivre", "survie"], ["survive", "survival"]),
       O("resoudre", "puzzle", "Résoudre", "Solve", "", "", ["résoudre", "énigmes"], ["solve", "puzzles"]),
       O("conduire", "volant", "Conduire / piloter", "Drive / pilot", "", "", ["conduire", "piloter"], ["drive", "pilot"]),
       O("gerer", "ville", "Gérer", "Manage", "", "", ["gérer", "organiser"], ["manage", "organise"]),
       O("discuter", "bulle", "Discuter / choisir", "Talk / choose", "", "", ["discuter", "parler", "dialoguer"], ["talk", "choose", "dialogue"]),
       O("collectionner", "coffre", "Collectionner", "Collect", "", "", ["collectionner", "ramasser"], ["collect", "gather"]),
       O("infiltrer", "ombre", "S'infiltrer", "Sneak", "", "", ["infiltrer", "discrétion"], ["sneak", "stealth"])],
      rec="explorer", rapide=True, depuis="deductions"))
add(Q("gameplay.systemes", "gameplay", "multi",
      "Quels systèmes dans le jeu ?", "Which systems does the game need?",
      "Je pré-coche ceux qu'on attend dans ton genre.", "I pre-select what your genre usually needs.",
      [O("combat", "epee", "Combat", "Combat", "", "", ["combat"], ["combat"]),
       O("inventaire", "sac", "Inventaire", "Inventory", "", "", ["inventaire", "sac"], ["inventory", "bag"]),
       O("fabrication", "enclume", "Fabrication", "Crafting", "", "", ["fabrication", "craft"], ["crafting", "craft"]),
       O("dialogues", "bulle", "Dialogues", "Dialogue", "", "", ["dialogues"], ["dialogue"]),
       O("sauvegarde", "disquette", "Sauvegarde", "Save system", "", "", ["sauvegarde"], ["save", "saving"]),
       O("ia_ennemie", "ia", "IA des ennemis", "Enemy AI", "", "", ["ia", "ennemis"], ["ai", "enemies"]),
       O("procedural", "de", "Génération procédurale", "Procedural generation", "", "", ["procédural", "génération"], ["procedural", "generation"]),
       O("physique", "physique", "Physique", "Physics", "", "", ["physique"], ["physics"]),
       O("meteo", "meteo", "Météo / jour et nuit", "Weather / day-night", "", "", ["météo", "jour nuit"], ["weather", "day night"]),
       O("economie", "pieces", "Économie / commerce", "Economy / trading", "", "", ["économie", "commerce"], ["economy", "trading"])],
      rec=["sauvegarde"], depuis="deductions"))
add(Q("gameplay.difficulte", "gameplay", "choix",
      "Quelle difficulté ?", "How hard?",
      "", "",
      [O("reglable", "curseurs", "Réglable", "Adjustable", "Chacun choisit.", "Everyone picks.", ["réglable"], ["adjustable", "settings"]),
       O("dure", "crane", "Dure et juste", "Hard but fair", "On apprend en mourant.", "Learn by dying.", ["dure", "difficile"], ["hard", "tough"]),
       O("facile", "plume", "Facile / détente", "Easy / relaxed", "On profite.", "Just enjoy.", ["facile", "détente"], ["easy", "relaxed"]),
       O("adaptative", "balance", "Adaptative", "Adaptive", "Le jeu s'ajuste au joueur.", "The game adapts to the player.", ["adaptative", "dynamique"], ["adaptive", "dynamic"])],
      rec="reglable"))
add(Q("gameplay.echec", "gameplay", "choix",
      "Que se passe-t-il quand on échoue ?", "What happens when you fail?",
      "", "",
      [O("checkpoint", "drapeau", "Retour au dernier point de sauvegarde", "Back to the last checkpoint", "", "", ["checkpoint", "sauvegarde"], ["checkpoint", "save point"]),
       O("permadeath", "tombe", "Mort définitive", "Permadeath", "On recommence tout.", "Start over.", ["mort définitive", "permadeath"], ["permadeath", "permanent"]),
       O("aucun", "infini", "Pas d'échec", "No failure", "On ne peut pas perdre.", "You can't lose.", ["pas d'échec", "aucun"], ["no failure", "none"]),
       O("partielle", "sac_perce", "Perte partielle", "Partial loss", "On perd une partie de ce qu'on porte.", "Lose part of what you carry.", ["perte", "partielle"], ["partial", "drop"])],
      rec="checkpoint"))
add(Q("boucle.courte", "gameplay", "texte",
      "La boucle de 30 secondes ?", "The 30-second loop?",
      "Ce que le joueur répète sans cesse. Je t'en propose une depuis ton verbe.", "What the player repeats again and again. I'll suggest one from your verb.",
      depuis="deductions", extra={"propositions_depuis": "deductions.propositions"}))
add(Q("boucle.session", "gameplay", "texte",
      "La boucle d'une session ?", "The session loop?",
      "Par exemple : sortir, récolter, rentrer, améliorer.", "For example: head out, gather, return, upgrade.",
      depuis="deductions", extra={"propositions_depuis": "deductions.propositions"}))
add(Q("boucle.retour", "gameplay", "multi",
      "Qu'est-ce qui fait revenir le joueur ?", "What brings players back?",
      "", "",
      [O("progression", "niveau", "Progression du personnage", "Character progression", "", "", ["progression", "niveau"], ["progression", "level"]),
       O("histoire", "livre", "L'histoire", "The story", "", "", ["histoire", "suite"], ["story", "what's next"]),
       O("contenus", "de", "Nouveaux contenus / procédural", "New content / procedural", "", "", ["contenus", "procédural"], ["content", "procedural"]),
       O("score", "trophee", "Défi / score", "Challenge / score", "", "", ["score", "défi", "classement"], ["score", "challenge", "leaderboard"]),
       O("base", "maison", "Construction de base", "Base building", "", "", ["base", "construction"], ["base", "building"])],
      rec=["progression"], depuis="deductions", max=3))
add(Q("progression.type", "gameplay", "multi",
      "Comment le joueur progresse ?", "How does the player progress?",
      "", "",
      [O("competences", "arbre", "Compétences / niveaux", "Skills / levels", "", "", ["compétences", "niveaux", "xp"], ["skills", "levels", "xp"]),
       O("equipement", "bouclier", "Équipement", "Gear", "", "", ["équipement", "objets"], ["gear", "equipment", "items"]),
       O("zones", "cle", "Débloquage de zones", "Unlocking areas", "", "", ["zones", "débloquer"], ["areas", "unlock"]),
       O("connaissance", "ampoule", "Seulement ce que le joueur apprend", "Only player knowledge", "", "", ["connaissance", "savoir"], ["knowledge", "player skill"])],
      rec=["competences"], depuis="deductions"))
add(Q("progression.meta", "gameplay", "choix",
      "Une progression entre les parties ?", "Progression between runs?",
      "", "",
      [O("aucune", "vide", "Aucune", "None", "", "", ["aucune", "non"], ["none", "no"]),
       O("legere", "cle", "Légère (débloquages)", "Light (unlocks)", "", "", ["légère", "débloquages"], ["light", "unlocks"]),
       O("forte", "boucle", "Forte (roguelite)", "Strong (roguelite)", "", "", ["forte", "roguelite"], ["strong", "roguelite"])],
      rec="aucune", depuis="deductions"))
add(Q("progression.duree", "gameplay", "choix",
      "Durée de vie visée ?", "Target playtime?",
      "", "",
      [O("5_10h", "horloge", "5 à 10 h", "5 to 10 h", "", "", ["cinq à dix"], ["five to ten"]),
       O("moins_2h", "sablier", "Moins de 2 h", "Under 2 h", "", "", ["moins de deux", "court"], ["under two", "short"]),
       O("20h", "calendrier", "20 h et plus", "20 h or more", "", "", ["vingt", "long"], ["twenty", "long"]),
       O("infinie", "infini", "Infinie / rejouable", "Endless / replayable", "", "", ["infinie", "rejouable"], ["endless", "replayable"])],
      rec="5_10h"))

# ================================================================ monde
add(Q("monde.structure", "monde", "choix",
      "Comment le monde est-il organisé ?", "How is the world structured?",
      "La structure décide du travail de level design.", "Structure decides the level-design workload.",
      [O("niveaux", "niveaux", "Niveaux successifs", "Level by level", "Un niveau après l'autre.", "One level after another.", ["niveaux"], ["levels"]),
       O("ouvert", "monde_ouvert", "Monde ouvert", "Open world", "Tout est relié, on va où on veut.", "All connected, go anywhere.", ["monde ouvert", "open world"], ["open world"]),
       O("hub", "hub", "Hub et zones", "Hub and zones", "Un camp de base et des sorties.", "A home base and outings.", ["hub", "zones"], ["hub", "zones"]),
       O("arene", "arene", "Une seule carte / arène", "A single map / arena", "Tout se joue au même endroit.", "Everything in one place.", ["arène", "une carte"], ["arena", "one map"])],
      rec="niveaux", rapide=True, depuis="deductions"))
add(Q("monde.taille", "monde", "choix",
      "Quelle taille ?", "How big?",
      "Plus grand = beaucoup plus de travail. Petit et dense, c'est souvent mieux.", "Bigger = much more work. Small and dense is often better.",
      [O("petite", "taille_petite", "Petite et dense", "Small and dense", "", "", ["petite", "dense"], ["small", "dense"]),
       O("moyenne", "taille_moyenne", "Moyenne", "Medium", "", "", ["moyenne"], ["medium"]),
       O("grande", "taille_grande", "Grande", "Large", "Attention au coût.", "Mind the cost.", ["grande", "immense"], ["large", "huge"]),
       O("procedurale", "de", "Procédurale", "Procedural", "Générée, sans limite fixe.", "Generated, no fixed limit.", ["procédurale"], ["procedural"])],
      rec="petite"))
add(Q("monde.lieu", "monde", "texte",
      "Où et quand se passe le jeu ?", "Where and when is the game set?",
      "Un lieu, une époque, une ambiance.", "A place, an era, a mood.",
      depuis="deductions", extra={"propositions_depuis": "deductions.propositions"}))
add(Q("monde.climat", "monde", "choix",
      "Quel paysage domine ?", "Which landscape dominates?",
      "Le décor principal : il oriente les assets et la lumière.", "The main setting: it steers assets and lighting.",
      [O("foret", "foret", "Forêts et campagne", "Forests and countryside", "", "", ["forêt", "campagne"], ["forest", "countryside"]),
       O("montagne", "montagne", "Montagne / neige", "Mountains / snow", "", "", ["montagne", "neige"], ["mountain", "snow"]),
       O("desert", "desert", "Désert", "Desert", "", "", ["désert", "sable"], ["desert", "sand"]),
       O("tropical", "palmier", "Île / tropiques", "Island / tropics", "", "", ["île", "tropical", "plage"], ["island", "tropical", "beach"]),
       O("ville", "immeubles", "Ville", "City", "", "", ["ville", "urbain"], ["city", "urban"]),
       O("mer", "vagues", "Mer / océan", "Sea / ocean", "", "", ["mer", "océan"], ["sea", "ocean"]),
       O("souterrain", "grotte", "Souterrain / donjon", "Underground / dungeon", "", "", ["souterrain", "grotte", "donjon"], ["underground", "cave", "dungeon"]),
       O("espace", "planete", "Espace / autre planète", "Space / alien world", "", "", ["espace", "planète"], ["space", "planet"]),
       O("imaginaire", "chateau", "Monde imaginaire", "Fantasy realm", "", "", ["imaginaire", "fantasy"], ["fantasy", "imaginary"])],
      rec="foret", depuis="deductions"))
add(Q("monde.saisons", "monde", "choix",
      "Des saisons ?", "Seasons?",
      "Le temps qui passe change le décor, et parfois le gameplay.", "Passing time changes the scenery, sometimes the gameplay.",
      [O("aucune", "vide", "Pas de saisons", "No seasons", "", "", ["aucune", "pas de saisons"], ["none", "no seasons"]),
       O("cycle", "saisons", "Le cycle des 4 saisons", "All 4 seasons", "", "", ["cycle", "quatre saisons"], ["cycle", "four seasons"]),
       O("printemps", "printemps", "Printemps", "Spring", "", "", ["printemps"], ["spring"]),
       O("ete", "ete", "Été", "Summer", "", "", ["été"], ["summer"]),
       O("automne", "automne", "Automne", "Autumn", "", "", ["automne"], ["autumn", "fall"]),
       O("hiver", "hiver", "Hiver", "Winter", "", "", ["hiver"], ["winter"])],
      rec="aucune", depuis="deductions"))
add(Q("monde.generation", "monde", "choix",
      "Monde fait main ou généré ?", "Handmade or generated world?",
      "", "",
      [O("main", "main", "Fait main", "Handmade", "Chaque lieu pensé.", "Every place designed.", ["main", "fait main"], ["handmade", "hand crafted"]),
       O("procedural", "de", "Procédural", "Procedural", "Généré par des règles.", "Generated from rules.", ["procédural", "généré"], ["procedural", "generated"]),
       O("mixte", "mixte", "Mixte", "Mixed", "Base générée, lieux clés à la main.", "Generated base, key places by hand.", ["mixte"], ["mixed", "hybrid"])],
      rec="main", depuis="deductions"))
add(Q("histoire.place", "monde", "choix",
      "Quelle place pour l'histoire ?", "How much story?",
      "", "",
      [O("legere", "parchemin", "Légère", "Light", "Un contexte, quelques moments.", "Some context, a few moments.", ["légère", "un peu"], ["light", "a little"]),
       O("aucune", "vide", "Aucune", "None", "", "", ["aucune", "pas d'histoire"], ["none", "no story"]),
       O("importante", "livre", "Importante", "Important", "", "", ["importante"], ["important", "big"]),
       O("centre", "plume_encre", "Au centre (narratif)", "Central (narrative)", "", "", ["centre", "narratif"], ["central", "narrative"])],
      rec="legere", depuis="deductions"))
add(Q("histoire.narration", "monde", "multi",
      "Comment on la raconte ?", "How is it told?",
      "", "",
      [O("environnement", "ruines", "Le décor et les objets", "Environment and objects", "", "", ["décor", "environnement", "objets"], ["environment", "objects"]),
       O("dialogues", "bulle", "Dialogues", "Dialogue", "", "", ["dialogues"], ["dialogue"]),
       O("cinematiques", "clap", "Cinématiques", "Cutscenes", "", "", ["cinématiques"], ["cutscenes", "cinematics"]),
       O("journal", "journal", "Journal / textes", "Journal / notes", "", "", ["journal", "textes", "notes"], ["journal", "notes", "texts"])],
      rec=["environnement"], si={"histoire.place": {"different_de": "aucune"}}))
add(Q("histoire.choix", "monde", "choix",
      "Les choix du joueur changent l'histoire ?", "Do player choices change the story?",
      "", "",
      [O("aucun", "ligne", "Non, ou pour le détail", "No, or only cosmetic", "", "", ["non", "aucun"], ["no", "none", "cosmetic"]),
       O("embranchements", "fourche", "Quelques embranchements", "Some branches", "", "", ["embranchements", "quelques"], ["branches", "some"]),
       O("ramifiee", "arbre_branches", "Fortement ramifiée", "Heavily branching", "", "", ["ramifiée", "beaucoup"], ["branching", "a lot"])],
      rec="aucun", si={"histoire.place": {"different_de": "aucune"}}))
add(Q("histoire.fin", "monde", "choix",
      "Une fin ?", "An ending?",
      "", "",
      [O("une", "fin_une", "Une fin", "One ending", "", "", ["une fin"], ["one ending"]),
       O("plusieurs", "fins", "Plusieurs fins", "Several endings", "", "", ["plusieurs"], ["several", "multiple"]),
       O("aucune", "infini", "Pas de fin (bac à sable)", "No ending (sandbox)", "", "", ["pas de fin"], ["no ending"])],
      rec="une", si={"histoire.place": {"different_de": "aucune"}}))

# ================================================================ DA
add(Q("da.style", "da", "choix",
      "Quel style visuel ?", "Which visual style?",
      "Le style décide du coût de chaque asset : choisis ce que tu sais produire.", "Style sets the cost of every asset: pick what you can produce.",
      [O("stylise", "stylise", "Stylisé / peint", "Stylised / painterly", "Formes lisibles, couleurs choisies.", "Readable shapes, chosen colours.", ["stylisé", "peint", "cartoon"], ["stylised", "stylized", "painterly", "cartoon"]),
       O("realiste", "realiste", "Réaliste", "Realistic", "Le plus coûteux à produire.", "The costliest to produce.", ["réaliste", "photo"], ["realistic", "photoreal"]),
       O("pixel", "pixel", "Pixel art", "Pixel art", "", "", ["pixel", "rétro"], ["pixel", "retro"]),
       O("low_poly", "low_poly", "Low poly", "Low poly", "Peu de polygones, aplats.", "Few polygons, flat colours.", ["low poly", "polygones"], ["low poly"]),
       O("cel", "cel", "Cel shading / BD", "Cel shading / comic", "", "", ["cel", "bd", "manga"], ["cel", "comic", "toon"]),
       O("voxel", "voxel", "Voxel", "Voxel", "", "", ["voxel", "cubes"], ["voxel", "blocks"]),
       O("dessin_main", "dessin_main", "Dessiné à la main", "Hand-drawn", "", "", ["dessiné", "crayon", "aquarelle"], ["hand drawn", "sketch", "watercolour"])],
      rec="stylise", rapide=True, depuis="deductions"))
add(Q("da.palette", "da", "choix",
      "Quelle palette, quelle ambiance ?", "Which palette, which mood?",
      "Je la propose depuis l'émotion que tu as choisie.", "I suggest one from the emotion you picked.",
      [O("chaude", "soleil", "Chaude", "Warm", "Ocres, orangés, lumière dorée.", "Ochres, oranges, golden light.", ["chaude", "dorée"], ["warm", "golden"]),
       O("froide", "lune", "Froide", "Cool", "Bleus, gris, nuit.", "Blues, greys, night.", ["froide", "bleue"], ["cool", "cold", "blue"]),
       O("contrastee", "contraste", "Contrastée", "High contrast", "Ombres franches, accents vifs.", "Hard shadows, vivid accents.", ["contrastée", "contraste"], ["contrast", "high contrast"]),
       O("sourde", "brume", "Sourde / brumeuse", "Muted / misty", "Désaturée, mélancolique.", "Desaturated, wistful.", ["sourde", "brume", "désaturée"], ["muted", "misty", "desaturated"]),
       O("vive", "arc_en_ciel", "Vive et colorée", "Bright and colourful", "Joyeuse, saturée.", "Cheerful, saturated.", ["vive", "colorée"], ["bright", "colourful", "colorful"])],
      rec="chaude", depuis="deductions"))
add(Q("da.sources", "da", "multi",
      "D'où viendront les assets ?", "Where will assets come from?",
      "Règle d'or : on valide une image cible avant de produire une série.", "Golden rule: approve one target image before making a series.",
      [O("melange", "melange", "Un mélange", "A mix", "Packs gratuits, génération, retouche.", "Free packs, generation, touch-ups.", ["mélange"], ["mix", "mixed"]),
       O("main", "pinceau", "Faits main", "Made by hand", "", "", ["main", "moi-même"], ["by hand", "myself"]),
       O("achetes", "panier", "Achetés", "Bought", "Packs du commerce.", "Store packs.", ["achetés", "packs"], ["bought", "store", "packs"]),
       O("ia", "etincelles", "Générés par IA", "AI-generated", "Toujours avec image validée d'abord.", "Always with an approved image first.", ["ia", "génération"], ["ai", "generated"])],
      rec=["melange"]))
add(Q("da.references", "da", "choix",
      "Tu as des images de référence ?", "Do you have reference images?",
      "", "",
      [O("oui", "dossier", "J'en ai", "I have some", "Un dossier ou des liens.", "A folder or links.", ["oui", "j'en ai"], ["yes", "i have"]),
       O("planches", "planches", "Propose-moi des planches", "Suggest mood boards", "", "", ["planches", "propose"], ["mood board", "suggest"]),
       O("pas_encore", "vide", "Pas encore", "Not yet", "", "", ["pas encore", "non"], ["not yet", "no"])],
      rec="oui"))
add(Q("interface.hud", "da", "choix",
      "Quel affichage pendant le jeu (HUD) ?", "What on-screen display (HUD)?",
      "", "",
      [O("minimal", "hud_minimal", "Minimal / dans le monde", "Minimal / diegetic", "Presque rien à l'écran.", "Almost nothing on screen.", ["minimal", "diégétique"], ["minimal", "diegetic"]),
       O("classique", "hud_classique", "Classique", "Classic", "Vie, carte, objets.", "Health, map, items.", ["classique"], ["classic"]),
       O("riche", "hud_riche", "Riche", "Rich", "Des panneaux partout (gestion).", "Panels everywhere (management).", ["riche", "complet"], ["rich", "detailed"])],
      rec="minimal", depuis="deductions"))
add(Q("interface.menus", "da", "choix",
      "Quel style de menus ?", "Which menu style?",
      "", "",
      [O("univers", "carnet", "Dans l'univers du jeu", "In the game's world", "Un carnet, un terminal…", "A notebook, a terminal…", ["univers", "carnet", "terminal"], ["in world", "notebook", "terminal"]),
       O("moderne", "menu_moderne", "Sobre et moderne", "Clean and modern", "", "", ["sobre", "moderne"], ["clean", "modern"]),
       O("retro", "menu_retro", "Rétro", "Retro", "", "", ["rétro", "arcade"], ["retro", "arcade"])],
      rec="univers"))
add(Q("interface.ecrans", "da", "multi",
      "Quels écrans sont indispensables ?", "Which screens are must-haves?",
      "", "",
      [O("menu", "menu_moderne", "Menu, options, pause", "Menu, options, pause", "", "", ["menu", "options", "pause"], ["menu", "options", "pause"]),
       O("inventaire", "sac", "Inventaire", "Inventory", "", "", ["inventaire"], ["inventory"]),
       O("carte", "carte", "Carte", "Map", "", "", ["carte"], ["map"]),
       O("journal", "journal", "Journal / quêtes", "Journal / quests", "", "", ["journal", "quêtes"], ["journal", "quests"])],
      rec=["menu"]))

# ================================================================ son
add(Q("son.musique", "son", "choix",
      "Quelle place pour la musique ?", "How much music?",
      "", "",
      [O("adaptative", "musique_adaptative", "Adaptative", "Adaptive", "Elle suit la situation.", "It follows the action.", ["adaptative", "dynamique"], ["adaptive", "dynamic"]),
       O("ambiante", "musique_douce", "Ambiante et discrète", "Ambient and subtle", "", "", ["ambiante", "discrète"], ["ambient", "subtle"]),
       O("forte", "orchestre", "Très présente", "Front and centre", "", "", ["forte", "présente"], ["strong", "front"]),
       O("aucune", "silence", "Aucune", "None", "", "", ["aucune", "pas de musique"], ["none", "no music"])],
      rec="adaptative", rapide=True, depuis="deductions"))
add(Q("son.sources", "son", "multi",
      "D'où viendront les sons ?", "Where will sounds come from?",
      "", "",
      [O("libres", "bibliotheque", "Bibliothèques libres de droits", "Royalty-free libraries", "", "", ["libres", "bibliothèques"], ["free", "libraries"]),
       O("composee", "partition", "Composée", "Composed", "Par moi ou un musicien.", "By me or a musician.", ["composée", "musicien"], ["composed", "musician"]),
       O("ia", "etincelles", "Générée par IA", "AI-generated", "", "", ["ia", "génération"], ["ai", "generated"]),
       O("achetes", "panier", "Packs achetés", "Bought packs", "", "", ["achetés", "packs"], ["bought", "packs"])],
      rec=["libres"]))
add(Q("son.voix", "son", "choix",
      "Des voix ?", "Voices?",
      "", "",
      [O("aucune", "silence", "Aucune", "None", "", "", ["aucune", "pas de voix"], ["none", "no voice"]),
       O("onomatopees", "onomatopee", "Quelques sons / onomatopées", "Grunts and barks", "", "", ["onomatopées", "sons"], ["grunts", "barks"]),
       O("partiel", "micro", "Doublage partiel", "Partial voice-over", "", "", ["partiel"], ["partial"]),
       O("complet", "micros", "Doublage complet", "Full voice-over", "", "", ["complet"], ["full"])],
      rec="aucune"))
add(Q("son.ambiance", "son", "choix",
      "Et l'ambiance sonore ?", "And the soundscape?",
      "", "",
      [O("importante", "ambiance_3d", "Importante", "Rich", "Son 3D, météo, faune.", "3D sound, weather, wildlife.", ["importante", "riche"], ["rich", "important"]),
       O("sobre", "haut_parleur", "Sobre", "Simple", "", "", ["sobre", "simple"], ["simple", "sober"]),
       O("minimale", "silence", "Minimale", "Minimal", "", "", ["minimale"], ["minimal"])],
      rec="importante", depuis="deductions"))

# ================================================================ technique
add(Q("plateforme.cibles", "technique", "multi",
      "On joue sur quoi ?", "What will people play on?",
      "Chaque plateforme en plus = des tests en plus.", "Each extra platform = extra testing.",
      [O("pc", "pc", "PC (Windows)", "PC (Windows)", "", "", ["pc", "windows", "ordinateur"], ["pc", "windows", "computer"]),
       O("web", "navigateur", "Navigateur web", "Web browser", "", "", ["navigateur", "web", "internet"], ["browser", "web"]),
       O("mobile", "mobile", "Mobile", "Mobile", "", "", ["mobile", "téléphone", "tablette"], ["mobile", "phone", "tablet"]),
       O("consoles", "console", "Consoles de salon", "Home consoles", "", "", ["console", "consoles"], ["console", "consoles"]),
       O("portable", "console_portable", "Console / PC portable", "Handheld", "", "", ["portable", "console portable"], ["handheld"]),
       O("mac_linux", "portable", "Mac / Linux", "Mac / Linux", "", "", ["mac", "linux"], ["mac", "linux"]),
       O("vr", "vr", "Réalité virtuelle", "Virtual reality", "", "", ["vr", "réalité virtuelle", "casque"], ["vr", "virtual reality", "headset"]),
       O("roblox", "briques", "Roblox", "Roblox", "Plateforme et moteur à la fois.", "Platform and engine in one.", ["roblox"], ["roblox"])],
      rec=["pc"], rapide=True, depuis="deductions"))
add(Q("plateforme.controles", "technique", "multi",
      "Avec quelles commandes ?", "Which controls?",
      "", "",
      [O("clavier_souris", "clavier", "Clavier-souris", "Keyboard and mouse", "", "", ["clavier", "souris"], ["keyboard", "mouse"]),
       O("manette", "manette", "Manette", "Gamepad", "", "", ["manette"], ["gamepad", "controller"]),
       O("tactile", "tactile", "Tactile", "Touch", "", "", ["tactile", "doigt"], ["touch", "finger"]),
       O("les_deux", "clavier_manette", "Clavier-souris et manette", "Keyboard, mouse and gamepad", "", "", ["les deux"], ["both"])],
      rec=["les_deux"], depuis="deductions"))
add(Q("plateforme.machine", "technique", "choix",
      "Quelle machine doit le faire tourner ?", "Which machine should run it?",
      "", "",
      [O("milieu", "pc", "PC milieu de gamme", "Mid-range PC", "", "", ["milieu de gamme", "moyen"], ["mid range", "average"]),
       O("haut", "pc_puissant", "PC haut de gamme", "High-end PC", "", "", ["haut de gamme", "puissant"], ["high end", "powerful"]),
       O("petite", "portable", "Petite config / portable", "Low-end / laptop", "", "", ["petite", "portable"], ["low end", "laptop"]),
       O("mobile", "mobile", "Téléphone", "Phone", "", "", ["mobile", "téléphone"], ["phone", "mobile"])],
      rec="milieu", depuis="deductions"))
add(Q("moteur.nom", "technique", "choix",
      "Quel moteur ?", "Which engine?",
      "Je te recommande celui qui colle le mieux à tes réponses ; tu peux en choisir un autre.", "I recommend the best fit for your answers; you can pick another.",
      [O("godot", "moteur_libre", "Godot", "Godot", "Libre, léger, très bien pour 2D et 3D légère.", "Open source, light, great for 2D and light 3D.", ["godot"], ["godot"]),
       O("unity", "moteur_polyvalent", "Unity", "Unity", "Polyvalent, C#, mobile et consoles.", "Versatile, C#, mobile and consoles.", ["unity"], ["unity"]),
       O("unreal", "moteur_lourd", "Unreal Engine", "Unreal Engine", "3D haut de gamme ; lourd, compilations longues.", "High-end 3D; heavy, long builds.", ["unreal"], ["unreal"]),
       O("phaser", "moteur_web", "Phaser", "Phaser", "2D dans le navigateur.", "2D in the browser.", ["phaser"], ["phaser"]),
       O("threejs", "moteur_web3d", "three.js", "three.js", "3D dans le navigateur.", "3D in the browser.", ["three", "threejs"], ["three", "threejs"]),
       O("pixijs", "moteur_web", "PixiJS", "PixiJS", "Rendu 2D web rapide.", "Fast 2D web rendering.", ["pixi"], ["pixi"]),
       O("bevy", "moteur_code", "Bevy", "Bevy", "Rust, tout en code.", "Rust, code-first.", ["bevy"], ["bevy"]),
       O("ebitengine", "moteur_code", "Ebitengine", "Ebitengine", "Go, 2D simple.", "Go, simple 2D.", ["ebiten", "ebitengine"], ["ebiten", "ebitengine"]),
       O("love", "moteur_code", "LÖVE", "LÖVE", "Lua, petits jeux 2D.", "Lua, small 2D games.", ["love", "löve"], ["love"]),
       O("pygame", "moteur_code", "pygame", "pygame", "Python, pour apprendre.", "Python, great to learn.", ["pygame", "python"], ["pygame", "python"]),
       O("defold", "moteur_code", "Defold", "Defold", "Lua, léger, mobile et web.", "Lua, light, mobile and web.", ["defold"], ["defold"]),
       O("roblox", "briques", "Roblox Studio", "Roblox Studio", "Luau, publié sur Roblox.", "Luau, published on Roblox.", ["roblox"], ["roblox"]),
       O("maison", "moteur_maison", "Moteur maison", "Custom engine", "Tout construire soi-même.", "Build it all yourself.", ["maison", "custom"], ["custom", "homemade", "own engine"])],
      rec="godot", rapide=True, depuis="deductions"))
add(Q("moteur.langage", "technique", "choix",
      "Quel langage ?", "Which language?",
      "", "",
      [O("gdscript", "script", "GDScript", "GDScript", "Simple, fait pour Godot.", "Simple, made for Godot.", ["gdscript"], ["gdscript"], si={"moteur.nom": {"egal": "godot"}}),
       O("csharp", "code", "C#", "C#", "", "", ["c sharp", "c#"], ["c sharp", "c#"], si={"moteur.nom": {"dans": ["godot", "unity"]}}),
       O("blueprints_cpp", "noeuds_code", "Blueprints + C++", "Blueprints + C++", "", "", ["blueprints et c++"], ["blueprints and c++"], si={"moteur.nom": {"egal": "unreal"}}),
       O("blueprints", "noeuds", "Blueprints seuls", "Blueprints only", "Visuel, sans code texte.", "Visual, no text code.", ["blueprints"], ["blueprints"], si={"moteur.nom": {"egal": "unreal"}}),
       O("cpp", "code", "C++", "C++", "", "", ["c plus plus", "c++"], ["c plus plus", "c++"], si={"moteur.nom": {"dans": ["unreal", "maison"]}}),
       O("typescript", "code", "TypeScript", "TypeScript", "", "", ["typescript"], ["typescript"], si={"moteur.nom": {"dans": ["phaser", "threejs", "pixijs"]}}),
       O("javascript", "script", "JavaScript", "JavaScript", "", "", ["javascript"], ["javascript"], si={"moteur.nom": {"dans": ["phaser", "threejs", "pixijs"]}}),
       O("luau", "script", "Luau", "Luau", "", "", ["luau"], ["luau"], si={"moteur.nom": {"egal": "roblox"}}),
       O("impose", "code", "Celui du moteur", "The engine's own", "Rust, Go, Lua ou Python selon le moteur.", "Rust, Go, Lua or Python, per engine.", ["celui du moteur"], ["engine default"], si={"moteur.nom": {"dans": ["bevy", "ebitengine", "love", "pygame", "defold"]}})],
      rec=None, depuis="deductions"))
add(Q("moteur.version", "technique", "choix",
      "Quelle version du moteur ?", "Which engine version?",
      "", "",
      [O("derniere", "etiquette_neuve", "La dernière stable", "Latest stable", "", "", ["dernière", "stable"], ["latest", "stable"]),
       O("precise", "etiquette", "Une version précise", "A specific version", "Dis-la dans le champ libre.", "Type it in the free field.", ["précise"], ["specific"])],
      rec="derniere"))
add(Q("moteur.versionnage", "technique", "choix",
      "Contrôle de version ?", "Version control?",
      "Indispensable pour revenir en arrière quand ça casse.", "Essential to roll back when things break.",
      [O("git_lfs", "branches_lfs", "Git + LFS", "Git + LFS", "Avec gestion des gros fichiers.", "With large-file support.", ["git lfs", "lfs"], ["git lfs", "lfs"]),
       O("git", "branches", "Git", "Git", "", "", ["git"], ["git"]),
       O("pas_encore", "vide", "Pas encore", "Not yet", "Je m'en occupe avec toi.", "I'll set it up with you.", ["pas encore", "non"], ["not yet", "no"])],
      rec="git_lfs"))
add(Q("multijoueur.mode", "technique", "choix",
      "Multijoueur ?", "Multiplayer?",
      "Le réseau se prévoit dès l'architecture, même s'il arrive plus tard.", "Networking must be planned in the architecture, even if it ships later.",
      [O("solo", "solo", "Non, solo", "No, single-player", "", "", ["solo", "non"], ["single player", "solo", "no"]),
       O("coop_ligne", "coop_ligne", "Coop en ligne", "Online co-op", "", "", ["coop en ligne", "coopération"], ["online co-op", "coop"]),
       O("coop_locale", "ecran_partage", "Coop locale / écran partagé", "Local co-op / split screen", "", "", ["locale", "écran partagé"], ["local", "split screen", "couch"]),
       O("competitif", "versus", "Compétitif en ligne", "Online competitive", "", "", ["compétitif", "pvp", "versus"], ["competitive", "pvp", "versus"])],
      rec="solo", rapide=True, depuis="deductions"))
add(Q("multijoueur.joueurs", "technique", "choix",
      "Combien de joueurs ensemble ?", "How many players together?",
      "", "",
      [O("2_4", "joueurs_4", "2 à 4", "2 to 4", "", "", ["deux à quatre"], ["two to four"]),
       O("2", "joueurs_2", "2", "2", "", "", ["deux", "duo"], ["two", "duo"]),
       O("5_16", "joueurs_16", "5 à 16", "5 to 16", "", "", ["cinq à seize"], ["five to sixteen"]),
       O("massif", "foule", "Massif", "Massive", "Avertissement : très gros chantier.", "Warning: a huge undertaking.", ["massif", "mmo"], ["massive", "mmo"])],
      rec="2_4", si={"multijoueur.mode": {"different_de": "solo"}}))
add(Q("multijoueur.architecture", "technique", "choix",
      "Qui fait tourner la partie ?", "Who hosts the game?",
      "", "",
      [O("hote", "hote", "Un joueur héberge", "A player hosts", "", "", ["héberge", "hôte"], ["host", "player hosts"]),
       O("dedie", "serveur", "Serveur dédié", "Dedicated server", "", "", ["serveur", "dédié"], ["server", "dedicated"]),
       O("services", "nuage", "Services du moteur / plateforme", "Engine / platform services", "", "", ["services", "nuage"], ["services", "cloud"])],
      rec="hote", si={"multijoueur.mode": {"dans": ["coop_ligne", "competitif"]}}))
add(Q("multijoueur.quand", "technique", "choix",
      "Quand arrive le multijoueur ?", "When does multiplayer arrive?",
      "", "",
      [O("apres_solo", "plan", "Prévu dès le début, livré après le solo", "Planned now, shipped after solo", "", "", ["après", "plus tard"], ["after", "later"]),
       O("prototype", "eclair", "Dès le prototype", "From the prototype", "", "", ["prototype", "tout de suite"], ["prototype", "right away"])],
      rec="apres_solo", si={"multijoueur.mode": {"dans": ["coop_ligne", "competitif"]}}))

# ================================================================ ambition
add(Q("monetisation.modele", "ambition", "choix",
      "Quel modèle économique ?", "Which business model?",
      "", "",
      [O("gratuit", "cadeau", "Gratuit / projet perso", "Free / personal project", "", "", ["gratuit", "perso"], ["free", "personal"]),
       O("achat", "etiquette_prix", "Achat unique", "One-time purchase", "", "", ["achat", "payant"], ["purchase", "paid", "premium"]),
       O("f2p", "gemme", "Free-to-play", "Free-to-play", "Pas de « payer pour gagner » par défaut.", "No pay-to-win by default.", ["free to play", "f2p"], ["free to play", "f2p"]),
       O("dons", "chapeau_dons", "Dons / prix libre", "Donations / pay what you want", "", "", ["dons", "prix libre"], ["donations", "pay what you want"])],
      rec="gratuit", rapide=True))
add(Q("monetisation.publication", "ambition", "multi",
      "Où le publier ?", "Where to release it?",
      "", "",
      [O("itch", "stand", "itch.io", "itch.io", "Simple, idéal pour commencer.", "Easy, great to start.", ["itch"], ["itch"]),
       O("steam", "vitrine", "Steam", "Steam", "", "", ["steam"], ["steam"]),
       O("stores_mobiles", "mobile", "Stores mobiles", "Mobile stores", "", "", ["store", "mobile"], ["app store", "mobile store"]),
       O("consoles", "console", "Stores consoles", "Console stores", "", "", ["consoles"], ["consoles"]),
       O("nulle_part", "vide", "Nulle part pour l'instant", "Nowhere for now", "", "", ["nulle part", "pas encore"], ["nowhere", "not yet"])],
      rec=["itch"]))
add(Q("monetisation.prix", "ambition", "choix",
      "Prix visé ?", "Target price?",
      "", "",
      [O("5_15", "prix_2", "5 à 15", "5 to 15", "Dans ta monnaie.", "In your currency.", ["cinq à quinze"], ["five to fifteen"]),
       O("moins_5", "prix_1", "Moins de 5", "Under 5", "", "", ["moins de cinq"], ["under five"]),
       O("15_30", "prix_3", "15 à 30", "15 to 30", "", "", ["quinze à trente"], ["fifteen to thirty"]),
       O("plus_30", "prix_4", "Plus de 30", "Over 30", "", "", ["plus de trente"], ["over thirty"])],
      rec="5_15", si={"monetisation.modele": {"egal": "achat"}}))
add(Q("monetisation.f2p", "ambition", "choix",
      "Qu'est-ce qu'on vend ?", "What do you sell?",
      "", "",
      [O("cosmetiques", "chapeau", "Cosmétiques seulement", "Cosmetics only", "", "", ["cosmétiques", "skins"], ["cosmetics", "skins"]),
       O("contenus", "coffre", "Contenus", "Content", "", "", ["contenus", "extensions"], ["content", "expansions"]),
       O("confort", "fauteuil", "Confort", "Convenience", "Gain de temps, sans avantage décisif.", "Time savers, no decisive edge.", ["confort"], ["convenience"])],
      rec="cosmetiques", si={"monetisation.modele": {"egal": "f2p"}}))
add(Q("ambition.taille", "ambition", "choix",
      "Quelle taille de projet ?", "How big is the project?",
      "Je te la recommande selon ton temps et ton expérience : mieux vaut finir petit qu'abandonner grand.", "I recommend it from your time and experience: better to finish small than drop something big.",
      [O("prototype", "prototype", "Prototype", "Prototype", "1 à 2 semaines.", "1 to 2 weeks.", ["prototype"], ["prototype"]),
       O("petit", "boite_petite", "Petit jeu complet", "Small complete game", "1 à 3 mois.", "1 to 3 months.", ["petit"], ["small"]),
       O("moyen", "boite_moyenne", "Jeu moyen", "Medium game", "6 à 12 mois.", "6 to 12 months.", ["moyen"], ["medium"]),
       O("grand", "boite_grande", "Grand jeu", "Large game", "Plus d'un an ; à découper en jalons.", "Over a year; split into milestones.", ["grand", "gros"], ["large", "big"])],
      rec="petit", rapide=True, depuis="deductions"))
add(Q("ambition.temps", "ambition", "choix",
      "Combien de temps peux-tu y consacrer ?", "How much time can you give it?",
      "", "",
      [O("quelques_heures", "horloge", "Quelques heures par semaine", "A few hours a week", "", "", ["quelques heures"], ["a few hours"]),
       O("soirs", "lune_soir", "Soirs et week-ends", "Evenings and weekends", "", "", ["soirs", "week-ends"], ["evenings", "weekends"]),
       O("plein", "calendrier", "Temps plein", "Full time", "", "", ["temps plein"], ["full time"]),
       O("jam", "chrono", "Une jam (48 à 72 h)", "A jam (48 to 72 h)", "", "", ["jam"], ["jam"])],
      rec="quelques_heures", rapide=True))
add(Q("ambition.equipe", "ambition", "choix",
      "Qui d'autre dans l'équipe ?", "Who else is on the team?",
      "", "",
      [O("seul", "solo", "Moi seul (+ les agents)", "Just me (+ the agents)", "", "", ["seul", "moi"], ["just me", "solo"]),
       O("2_3", "potes", "2 à 3 personnes", "2 to 3 people", "", "", ["deux trois"], ["two three"]),
       O("plus", "equipe", "Plus", "More", "", "", ["plus", "équipe"], ["more", "team"])],
      rec="seul"))
add(Q("ambition.cible", "ambition", "texte",
      "Une date ou une étape à viser ?", "A date or milestone to aim for?",
      "Par défaut : une version jouable dans 2 semaines.", "By default: a playable build in 2 weeks.",
      extra={"defaut": {"fr": "Une version jouable dans 2 semaines", "en": "A playable build in 2 weeks"}}))
add(Q("ia.autorises", "ambition", "multi",
      "Qu'est-ce que l'IA a le droit de produire ?", "What may AI produce?",
      "Tu gardes la main : rien n'est généré sans ton feu vert sur une image cible.", "You stay in control: nothing is generated without your go-ahead on a target image.",
      [O("code", "code", "Le code", "Code", "Écrit par les agents, relu.", "Written by agents, reviewed.", ["code"], ["code"]),
       O("images", "image", "Images / textures", "Images / textures", "", "", ["images", "textures"], ["images", "textures"]),
       O("modeles_3d", "modele_3d", "Modèles 3D", "3D models", "", "", ["3d", "modèles"], ["3d", "models"]),
       O("son", "onde", "Son / musique", "Sound / music", "", "", ["son", "musique"], ["sound", "music"]),
       O("rien", "interdit", "Rien", "Nothing", "", "", ["rien", "aucun"], ["nothing", "none"])],
      rec=["code", "images"], rapide=True, extra={"seulement_rapide": True}))
add(Q("ia.code", "ambition", "choix",
      "L'IA écrit le code ?", "Does AI write the code?",
      "", "",
      [O("relecture", "loupe", "Oui, avec relecture", "Yes, with review", "", "", ["relecture", "oui"], ["review", "yes"]),
       O("libre", "code", "Oui, sans relecture", "Yes, no review", "", "", ["sans relecture"], ["no review"]),
       O("suggestions", "ampoule", "Seulement des suggestions", "Suggestions only", "", "", ["suggestions"], ["suggestions"])],
      rec="relecture"))
add(Q("ia.images", "ambition", "choix",
      "Images, textures, concept art par IA ?", "AI images, textures, concept art?",
      "", "",
      [O("valide", "valide", "Oui, image validée d'abord", "Yes, approved image first", "", "", ["oui", "validée"], ["yes", "approved"]),
       O("non", "interdit", "Non", "No", "", "", ["non"], ["no"]),
       O("maquettes", "croquis", "Seulement pour des maquettes", "Mock-ups only", "", "", ["maquettes"], ["mock ups", "mockups"])],
      rec="valide"))
add(Q("ia.modeles_3d", "ambition", "choix",
      "Modèles 3D par IA (image vers 3D) ?", "AI 3D models (image to 3D)?",
      "", "",
      [O("oui", "modele_3d", "Oui, un modèle par objet validé", "Yes, one model per approved object", "", "", ["oui"], ["yes"]),
       O("non", "interdit", "Non", "No", "", "", ["non"], ["no"]),
       O("maquettes", "croquis", "Maquettes seulement", "Mock-ups only", "", "", ["maquettes"], ["mock ups", "mockups"])],
      rec="oui", si={"camera.dimension": {"dans": ANGLE_3D}}))
add(Q("ia.son", "ambition", "choix",
      "Son, musique, voix par IA ?", "AI sound, music, voices?",
      "", "",
      [O("maquettes", "croquis", "Seulement des maquettes", "Mock-ups only", "", "", ["maquettes"], ["mock ups", "mockups"]),
       O("oui", "onde", "Oui", "Yes", "", "", ["oui"], ["yes"]),
       O("non", "interdit", "Non", "No", "", "", ["non"], ["no"])],
      rec="maquettes"))
add(Q("ia.outils", "ambition", "multi",
      "Quels outils as-tu déjà ?", "Which tools do you already have?",
      "Donne leurs noms dans le champ libre si tu veux.", "Name them in the free field if you like.",
      [O("images", "image", "Génération d'images", "Image generation", "", "", ["images"], ["images"]),
       O("3d", "modele_3d", "Génération 3D", "3D generation", "", "", ["3d"], ["3d"]),
       O("modelage", "modelage", "Logiciel 3D", "3D software", "", "", ["logiciel 3d", "modélisation"], ["3d software", "modelling"]),
       O("musique", "partition", "Musique", "Music", "", "", ["musique"], ["music"]),
       O("aucun", "vide", "Aucun", "None", "", "", ["aucun"], ["none"])],
      rec=["aucun"]))
add(Q("budget.claude", "ambition", "choix",
      "Quel budget d'usage de Claude ?", "How much Claude usage?",
      "", "",
      [O("normal", "jauge_moyenne", "Normal", "Normal", "Quelques agents en parallèle.", "A few agents in parallel.", ["normal"], ["normal"]),
       O("econome", "jauge_basse", "Économe", "Thrifty", "1 à 2 agents.", "1 to 2 agents.", ["économe"], ["thrifty", "low"]),
       O("large", "jauge_haute", "Large", "Generous", "Plusieurs agents en continu.", "Several agents non-stop.", ["large"], ["generous", "high"])],
      rec="normal"))
add(Q("budget.generation_par_jalon", "ambition", "choix",
      "Budget de génération payante par jalon ?", "Paid generation budget per milestone?",
      "Images, 3D, son : les crédits se vérifient avec toi avant une grosse série.", "Images, 3D, sound: credits are checked with you before a big batch.",
      [O("plafond", "plafond", "Je fixe un plafond", "I set a cap", "", "", ["plafond"], ["cap", "limit"]),
       O("aucun", "interdit", "Aucun (rien de payant)", "None (nothing paid)", "", "", ["aucun", "rien"], ["none", "nothing"]),
       O("sans_plafond", "demander", "Sans plafond, demander avant", "No cap, ask first", "", "", ["sans plafond"], ["no cap"])],
      rec="plafond", rapide=True))
add(Q("budget.plafond", "ambition", "curseur",
      "Combien de crédits au plus par jalon ?", "How many credits at most per milestone?",
      "Un nombre dans l'unité de ton outil.", "A number in your tool's unit.",
      si={"budget.generation_par_jalon": {"egal": "plafond"}},
      extra={"min": 0, "max": 5000, "pas": 50, "defaut": 500}))
add(Q("budget.regle", "ambition", "choix",
      "Combien d'essais par objet ?", "How many attempts per object?",
      "", "",
      [O("un", "essai_un", "Un seul, demander avant de refaire", "One, ask before redoing", "", "", ["un", "un seul"], ["one", "single"]),
       O("deux", "essai_deux", "Jusqu'à 2", "Up to 2", "", "", ["deux"], ["two"]),
       O("libre", "jauge_haute", "Libre dans le plafond", "Free within the cap", "", "", ["libre"], ["free"])],
      rec="un", si={"budget.generation_par_jalon": {"different_de": "aucun"}}))
add(Q("jalons.decoupage", "ambition", "choix",
      "Comment découper le projet ?", "How do we split the project?",
      "", "",
      [O("propose", "jalons", "Le découpage proposé", "The suggested plan", "Cadrage, prototype, boucle, contenu, finition, sortie.", "Setup, prototype, core loop, content, polish, release.", ["proposé", "standard"], ["suggested", "standard"]),
       O("court", "jalons_courts", "Plus court", "Shorter", "Prototype puis jeu.", "Prototype, then game.", ["court"], ["shorter", "short"]),
       O("je_decris", "plume_encre", "Je le décris", "I'll describe it", "", "", ["je décris", "moi"], ["describe", "my own"])],
      rec="propose"))
add(Q("jalons.rythme", "ambition", "choix",
      "Tous les combien une version à essayer ?", "How often a build to try?",
      "", "",
      [O("heures", "sablier", "Toutes les quelques heures de travail", "Every few hours of work", "", "", ["heures"], ["hours"]),
       O("jour", "soleil", "Une par jour", "Once a day", "", "", ["jour"], ["day", "daily"]),
       O("jalon", "drapeau", "Une par jalon", "Once per milestone", "", "", ["jalon"], ["milestone"])],
      rec="heures"))
add(Q("jalons.autonomie", "ambition", "choix",
      "Les agents continuent sans toi ?", "Do agents keep going without you?",
      "", "",
      [O("oui", "engrenages", "Oui, ils enchaînent", "Yes, they keep going", "Ils s'arrêtent pour ce que tu dois voir.", "They stop for what you must see.", ["oui", "enchaînent"], ["yes", "keep going"]),
       O("non", "feu_vert", "Non, feu vert à chaque tâche", "No, green light each task", "", "", ["non", "feu vert"], ["no", "green light"])],
      rec="oui"))
add(Q("jalons.verifications", "ambition", "choix",
      "Quelles vérifications ?", "How much checking?",
      "", "",
      [O("minimum", "coche", "Le minimum", "The minimum", "Ça compile, quelques tests, un lancement court ; je regarde en jeu.", "It builds, a few tests, a short run; I look in game.", ["minimum"], ["minimum"]),
       O("poussees", "loupe", "Poussées", "Thorough", "Séries de tests, captures.", "Test suites, screenshots.", ["poussées"], ["thorough"])],
      rec="minimum"))
add(Q("jalons.donnees_lourdes", "ambition", "choix",
      "Où ranger les données lourdes ?", "Where do heavy files live?",
      "Sources d'assets, rendus, exports : hors du dépôt.", "Asset sources, renders, exports: outside the repo.",
      [O("a_cote", "dossier", "Un dossier à côté du projet", "A folder next to the project", "", "", ["à côté"], ["next to"]),
       O("dans_projet", "dossier_ignore", "Dans le projet (ignoré par git)", "In the project (git-ignored)", "", "", ["dans le projet"], ["in the project"]),
       O("autre_disque", "disque", "Un autre disque", "Another drive", "Donne le chemin.", "Give the path.", ["autre disque"], ["another drive"])],
      rec="a_cote"))

# ================================================================ personnages
add(Q("personnages.maitre", "personnages", "personnage",
      "Et maintenant, à toi : à quoi tu ressembles ?", "Now you: what do you look like?",
      "Ton avatar dans le studio. « Au hasard » ou « Par défaut » pour aller vite.", "Your avatar in the studio. \"Random\" or \"Default\" to go fast.",
      rapide=True, extra={"cible": "maitre", "boutons": ["hasard", "defaut"]}))
add(Q("assistant.nom", "personnages", "nom",
      "Et moi, comment tu m'appelles ?", "And what do you call me?",
      "Je te propose trois noms selon ma personnalité.", "I'll suggest three names to match my personality.",
      rapide=True, depuis="deductions", extra={"propositions_depuis": "deductions.propositions"}))
add(Q("assistant.titre", "personnages", "choix",
      "Mon titre ?", "My title?",
      "", "",
      [O("assistant", "badge", "Assistant", "Assistant", "", "", ["assistant"], ["assistant"]),
       O("intendant", "trousseau", "Intendant", "Steward", "", "", ["intendant"], ["steward"]),
       O("sidekick", "acolyte", "Acolyte", "Sidekick", "", "", ["acolyte", "sidekick"], ["sidekick"]),
       O("majordome", "noeud_papillon", "Majordome", "Butler", "", "", ["majordome"], ["butler"])],
      rec="assistant"))
add(Q("assistant.espece", "personnages", "choix",
      "Qu'est-ce que je suis ?", "What am I?",
      "Précise dans le champ libre : chat, corbeau, fantôme…", "Be specific in the free field: cat, raven, ghost…",
      [O("humain", "humain", "Un humain", "A human", "", "", ["humain"], ["human"]),
       O("robot", "robot", "Un robot", "A robot", "", "", ["robot"], ["robot"]),
       O("animal", "animal", "Un animal", "An animal", "", "", ["animal", "chat", "renard", "corbeau"], ["animal", "cat", "fox", "raven"]),
       O("creature", "fantome", "Une créature", "A creature", "", "", ["créature", "fantôme", "slime"], ["creature", "ghost", "slime"])],
      rec="humain"))
add(Q("assistant.personnalite", "personnages", "choix",
      "Ma personnalité ?", "My personality?",
      "", "",
      [O("espiegle", "espiegle", "Espiègle", "Playful", "", "", ["espiègle", "joueur"], ["playful", "cheeky"]),
       O("serieux", "serieux", "Sérieux et carré", "Serious and tidy", "", "", ["sérieux", "carré"], ["serious", "tidy"]),
       O("sarcastique", "sarcastique", "Sarcastique", "Sarcastic", "", "", ["sarcastique"], ["sarcastic"]),
       O("zen", "zen", "Zen", "Zen", "", "", ["zen", "calme"], ["zen", "calm"])],
      rec="espiegle", rapide=True))
add(Q("assistant.humour", "personnages", "choix",
      "Mon humour ?", "My sense of humour?",
      "Toujours sur la situation, le code, la malchance ; jamais sur un groupe de personnes.", "Always about the situation, the code, bad luck; never about a group of people.",
      [O("leger", "sourire", "Léger", "Light", "", "", ["léger"], ["light"]),
       O("absurde", "absurde", "Absurde", "Absurd", "", "", ["absurde"], ["absurd", "silly"]),
       O("geek", "geek", "Geek", "Geeky", "", "", ["geek"], ["geek", "geeky"]),
       O("noir", "crane", "Noir", "Dark", "", "", ["noir"], ["dark", "gallows"]),
       O("aucun", "vide", "Aucun", "None", "", "", ["aucun", "pas d'humour"], ["none", "no humour"])],
      rec="leger"))
add(Q("assistant.frequence", "personnages", "choix",
      "Je te fais un rapport tous les… ?", "I report to you every…?",
      "Seulement si quelque chose a bougé, et toujours en fin de jalon. Plus souvent = plus de jetons.", "Only if something changed, and always at the end of a milestone. More often = more tokens.",
      [O("120", "freq_120", "2 h", "2 h", "", "", ["deux heures"], ["two hours"]),
       O("60", "freq_60", "1 h", "1 h", "", "", ["une heure", "soixante"], ["one hour", "sixty"]),
       O("30", "freq_30", "30 min", "30 min", "", "", ["trente"], ["thirty"]),
       O("15", "freq_15", "15 min", "15 min", "", "", ["quinze"], ["fifteen"])],
      rec="120", rapide=True))
add(Q("assistant.langue", "personnages", "choix",
      "Dans quelle langue je te parle ?", "Which language do I speak?",
      "", "",
      [O("projet", "langues", "Celle du projet", "The project's", "", "", ["projet"], ["project"]),
       O("fr", "langue_une", "Français", "French", "", "", ["français"], ["french"]),
       O("en", "langue_une", "Anglais", "English", "", "", ["anglais"], ["english"])],
      rec="projet"))
add(Q("assistant.voix", "personnages", "choix",
      "Je te parle à voix haute ?", "Do I speak out loud?",
      "", "",
      [O("non", "bulle", "Non, des bulles seulement", "No, speech bubbles only", "", "", ["non", "bulles"], ["no", "bubbles"]),
       O("oui", "haut_parleur", "Oui", "Yes", "Voix du navigateur.", "Browser voice.", ["oui"], ["yes"]),
       O("cloche", "cloche", "Seulement pour la cloche", "Only for the bell", "", "", ["cloche"], ["bell"])],
      rec="non"))
add(Q("assistant.apparence", "personnages", "choix",
      "Et mon apparence ?", "And my look?",
      "", "",
      [O("choisir", "miroir", "Je la choisis", "I'll design it", "Même éditeur que pour toi.", "Same editor as yours.", ["choisir", "je choisis"], ["design", "choose"]),
       O("hasard", "de", "Au hasard", "Random", "", "", ["hasard"], ["random"]),
       O("assortie", "jumeaux", "Assortie à la mienne", "Matching mine", "", "", ["assortie", "comme moi"], ["matching", "like mine"]),
       O("da", "palette", "Assortie à la DA du jeu", "Matching the game's art", "", "", ["da", "jeu"], ["art", "game"])],
      rec="choisir"))
add(Q("personnages.assistant", "personnages", "personnage",
      "Dessine-moi !", "Draw me!",
      "", "",
      si={"assistant.apparence": {"egal": "choisir"}},
      extra={"cible": "assistant", "boutons": ["hasard", "defaut"]}))

# ================================================================ fin
add(Q("fin.valider", "fin", "choix",
      "On écrit le projet ?", "Shall I write the project?",
      "Chaque ligne du récapitulatif se corrige d'un clic. Ensuite, j'écris ta roadmap.", "Every summary line can be fixed with one click. Then I write your roadmap.",
      [O("oui", "valide", "Oui, on lance le studio !", "Yes, open the studio!", "J'écris le projet et ta roadmap.", "I write the project and your roadmap.", ["oui", "go", "on lance"], ["yes", "go", "start"]),
       O("corriger", "gomme", "Je corrige une réponse", "I'll fix an answer", "", "", ["corriger"], ["fix", "change"]),
       O("complet", "carnet", "Je passe en mode complet", "Switch to full mode", "Pour les réponses « à confirmer ».", "For the \"to confirm\" answers.", ["complet"], ["full"])],
      rec="oui", libre=False, passer=False))


# ---------------------------------------------------------------- roadmap
# Textes de l'écran « Voici ta roadmap » (fin du questionnaire, non sautable)
# et du panneau Roadmap (studio/roadmap.js). Format : references/studio.md.
ROADMAP_UI = {
    "bouton": ("Roadmap", "Roadmap"),
    "surtitre": ("Studio", "Studio"),
    "titre": ("Roadmap", "Roadmap"),
    "voici": ("Voici ta roadmap !", "Here is your roadmap!"),
    "voici_aide": ("Je l'ai tirée de tes réponses : jalons, tâches, estimations. Chaque jalon terminé débloque un succès et fait monter le studio de niveau.",
                   "I built it from your answers: milestones, tasks, estimates. Each finished milestone unlocks an achievement and levels up the studio."),
    "attente": ("J'écris ta roadmap à partir de tes réponses…", "I'm writing your roadmap from your answers…"),
    "de_la_v1": ("de la version 1", "of version 1"),
    "restants": ("restants", "left"),
    "details": ("Détails (tâches, jalons, niveau)", "Details (tasks, milestones, level)"),
    "heros_aide": ("Avancement pondéré par la durée des tâches, le même chiffre que « Version 1 ». Le compte brut des tâches est dans les détails.",
                   "Progress weighted by task duration, the same figure as “Version 1”. The raw task count is in the details."),
    "attente_longue": ("Toujours en train d'écrire : une roadmap complète, ça se soigne.", "Still writing: a full roadmap deserves some care."),
    "attente_bloquee": ("Rien n'arrive depuis 5 minutes. Si la session de Claude s'est fermée, rouvre-la et dis « reprends mon studio » : il écrira la roadmap à partir de tes réponses, qui sont gardées.",
                        "Nothing for 5 minutes. If the Claude session closed, reopen it and say \"resume my studio\": it will write the roadmap from your answers, which are saved."),
    "relancer": ("Lui rappeler d'écrire la roadmap", "Remind it to write the roadmap"),
    "relance_texte": ("Le questionnaire est validé : écris la roadmap (docs/ROADMAP.md et .studio/roadmap.json) à partir de .studio/reponses_questionnaire.json.",
                      "The questionnaire is approved: write the roadmap (docs/ROADMAP.md and .studio/roadmap.json) from .studio/reponses_questionnaire.json."),
    "relance_ok": ("Rappel déposé pour l'assistant.", "Reminder left for the assistant."),
    "continuer": ("C'est parti !", "Let's go!"),
    "jalon": ("Jalon", "Milestone"),
    "taches": ("tâches", "tasks"),
    "fin_visee": ("fin visée", "target"),
    "estimation": ("estimation", "estimate"),
    "heures": ("h", "h"),
    "depend_de": ("après", "after"),
    "critere_fin": ("Fini quand", "Done when"),
    "succes": ("Succès", "Achievement"),
    "grand_succes": ("Grand succès", "Major achievement"),
    "succes_verrouille": ("Verrouillé", "Locked"),
    "succes_gagne": ("Gagné le", "Earned on"),
    "succes_titre": ("Succès de la roadmap", "Roadmap achievements"),
    "niveau": ("Niveau du studio", "Studio level"),
    "xp_vers": ("XP vers le niveau", "XP to level"),
    "avancement": ("Avancement", "Progress"),
    "en_cours": ("Jalon en cours", "Current milestone"),
    "aucune": ("Pas encore de roadmap.", "No roadmap yet."),
    "statut_a_faire": ("à faire", "to do"),
    "statut_en_cours": ("en cours", "in progress"),
    "statut_pret": ("prêt", "ready"),
    "statut_verse": ("versé", "merged"),
    "statut_ecart": ("écart noté", "deviation noted"),
    "jalon_termine": ("Jalon terminé", "Milestone complete"),
}


# ---------------------------------------------------------------- sortie
def construire(langue):
    fr = langue == "fr"
    chap = [{"id": c, "titre": tf if fr else te, "construit": b} for c, tf, te, b in CHAPITRES]
    out = []
    for q in Q_:
        d = {"id": q["id"], "chapitre": q["chap"], "type": q["type"]}
        if q["rapide"]:
            d["rapide"] = True
        if q["extra"].get("seulement_rapide"):
            d["seulement_rapide"] = True
        d["titre"] = q["fr"] if fr else q["en"]
        aide = q["afr"] if fr else q["aen"]
        if aide:
            d["aide"] = aide
        if q["options"]:
            ch = []
            for o in q["options"]:
                c = {"id": o["id"], "libelle": o["fr"] if fr else o["en"]}
                det = o["dfr"] if fr else o["den"]
                if det:
                    c["detail"] = det
                c["illustration"] = "cartes/%s.svg" % o["illus"]
                c["mots_voix"] = o["vfr"] if fr else o["ven"]
                if o["si"]:
                    c["si"] = o["si"]
                ch.append(c)
            d["choix"] = ch
            d["recommande"] = q["rec"]
            if q["type"] == "multi" and q["max"]:
                d["max"] = q["max"]
        if q["depuis"]:
            d["recommande_depuis"] = q["depuis"]
        for k in ("propositions_depuis", "cible", "boutons", "min", "max", "pas", "attend_deductions"):
            if k in q["extra"]:
                d[k] = q["extra"][k]
        if "defaut" in q["extra"]:
            v = q["extra"]["defaut"]
            d["defaut"] = v[langue] if isinstance(v, dict) else v
        d["libre"] = q["libre"] if q["type"] in ("choix", "multi") else q["type"] in ("texte", "nom")
        d["micro"] = q["type"] in ("choix", "multi", "texte", "nom")
        d["passer"] = q["passer"]
        d["si"] = q["si"]
        out.append(d)
    i = 0 if langue == "fr" else 1
    roadmap = {k: v[i] for k, v in ROADMAP_UI.items()}
    roadmap["attend"] = "roadmap.json"
    roadmap["sautable"] = False
    return {"version": 1, "langue": langue, "chapitres": chap, "questions": out, "roadmap": roadmap}


def verifier():
    ids = set()
    erreurs = []
    for q in Q_:
        if q["id"] in ids:
            erreurs.append("doublon " + q["id"])
        ids.add(q["id"])
        oids = [o["id"] for o in q["options"]]
        if len(oids) != len(set(oids)):
            erreurs.append("option en double dans " + q["id"])
        r = q["rec"]
        for v in (r if isinstance(r, list) else [r] if r else []):
            if v not in oids:
                erreurs.append("recommande inconnu %s dans %s" % (v, q["id"]))
        for cond in [q["si"]] + [o["si"] for o in q["options"]]:
            for k in (cond or {}):
                if k not in ids and k != q["id"]:
                    erreurs.append("condition sur une question pas encore posée : %s (%s)" % (k, q["id"]))
        if q["chap"] not in [c[0] for c in CHAPITRES]:
            erreurs.append("chapitre inconnu " + q["id"])
    return erreurs


def illustrations():
    return sorted({o["illus"] for q in Q_ for o in q["options"]})


if __name__ == "__main__":
    err = verifier()
    if err:
        print("\n".join(err))
        sys.exit(1)
    for lg in ("fr", "en"):
        p = os.path.join(STUDIO, "questions.%s.json" % lg)
        jsonio.ecrire_texte(p, json.dumps(construire(lg), ensure_ascii=False, indent=1) + "\n", newline="\n")
    n_r = sum(1 for q in Q_ if q["rapide"])
    print("%d questions (%d en mode rapide), %d options, %d illustrations"
          % (len(Q_), n_r, sum(len(q["options"]) for q in Q_), len(illustrations())))
    if "--illustrations" in sys.argv:
        print(" ".join(illustrations()))
