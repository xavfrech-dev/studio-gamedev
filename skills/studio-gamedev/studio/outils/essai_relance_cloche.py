"""Essai (16/11) : une relance depuis la cloche n'est pas un nouveau message de l'utilisateur.
Elle reprend son message d'origine et ne doit pas allumer seule le bandeau « en attente » (champ « auto »).

python -I -B essai_relance_cloche.py
"""
import os
import sys
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from studio_etat import message_auto  # noqa: E402

CAS = [
    ("Relancer l’assistant : « ajoute un bouton » (12 min)", True),     # texte exact de la cloche (fr)
    ("Relancer l'assistant : « ajoute un bouton » (12 min)", True),     # apostrophe droite
    ("Remind the assistant : « add a button » (12 min)", True),         # texte exact de la cloche (en : gabarit « ${T.relancer} : »)
    ("Remind the assistant: « add a button »", True),
    ("Contremaître : agent bloqué", True),
    ("ajoute un bouton optimiser", False),                              # vrai message : compte toujours
    ("Peux-tu relancer l’assistant demain ?", False),                   # le mot seul ne suffit pas
]
echecs = 0
for texte, attendu in CAS:
    obtenu = message_auto({"texte": texte})
    ok = obtenu == attendu
    echecs += not ok
    print(("OK   " if ok else "ECHEC"), texte, "->", obtenu)
# le texte réel produit par la page : ${T.relancer} : « … »
html = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "studio.html"), encoding="utf-8").read()
for cle in ("cl_relancer: 'Relancer l’assistant'", "cl_relancer: 'Remind the assistant'"):
    ok = cle in html
    echecs += not ok
    print(("OK   " if ok else "ECHEC"), "libellé de la cloche présent :", cle)
print("RESULTAT", "OK" if not echecs else f"{echecs} échec(s)")
sys.exit(1 if echecs else 0)
