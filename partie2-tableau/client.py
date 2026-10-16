"""Client du tableau interactif : demande une forme et l'envoie au serveur. Lancement : python client.py"""

import json
import os
import random
import re

import requests

URL: str = os.environ.get("TABLEAU_URL", "http://localhost:8000")
DOSSIER_DESSINS: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dessins")

Forme = dict[str, int | str | list[int]]

# Pour chaque forme : (clé dans l'API, question posée)
QUESTIONS: dict[str, list[tuple[str, str]]] = {
    "point": [("x", "x"), ("y", "y")],
    "line": [("x1", "x de départ"), ("y1", "y de départ"), ("x2", "x d'arrivée"), ("y2", "y d'arrivée")],
    "circle": [("x", "x du centre"), ("y", "y du centre"), ("radius", "rayon")],
    "rectangle": [("x", "x du coin haut gauche"), ("y", "y du coin haut gauche"),
                  ("width", "largeur"), ("height", "hauteur")],
    "square": [("x", "x du coin haut gauche"), ("y", "y du coin haut gauche"), ("cote", "côté")],
}
MENU: dict[str, str] = {"1": "point", "2": "line", "3": "circle", "4": "rectangle", "5": "square"}


def demander_nombre(question: str, minimum: int = 0) -> int:
    while True:
        texte = input(f"  {question} : ")
        if texte.isdigit() and int(texte) >= minimum:
            return int(texte)
        print(f"    Entrez un nombre entier supérieur ou égal à {minimum}.")


def demander_couleur() -> list[int]:
    while True:
        texte = input("  couleur r,g,b (Entrée = aléatoire) : ")
        if texte == "":
            return [random.randint(0, 255) for _ in range(3)]
        m = re.search(r"^(\d{1,3}),(\d{1,3}),(\d{1,3})$", texte.replace(" ", ""))
        if m and max(int(v) for v in m.groups()) <= 255:
            return [int(v) for v in m.groups()]
        print("    Exemple : 120,200,102")


def demander_forme(shape: str) -> Forme:
    forme: Forme = {"shape": shape}
    for cle, question in QUESTIONS[shape]:
        forme[cle] = demander_nombre(question)
    forme["color"] = demander_couleur()
    return forme


def placer(forme: Forme, x: int, y: int, taille: int) -> Forme:
    """Les dessins sont décrits dans un carré de 100 x 100 : on les agrandit puis on les déplace."""
    nouvelle = dict(forme)
    for cle, valeur in forme.items():
        if cle in ["x", "x1", "x2"]:
            nouvelle[cle] = x + valeur * taille // 100
        elif cle in ["y", "y1", "y2"]:
            nouvelle[cle] = y + valeur * taille // 100
        elif cle in ["radius", "width", "height", "cote"]:
            nouvelle[cle] = max(1, valeur * taille // 100)
    return nouvelle


def dessin_compose() -> None:
    noms = [os.path.splitext(f)[0] for f in sorted(os.listdir(DOSSIER_DESSINS)) if f.endswith(".json")]
    for i, nom in enumerate(noms, start=1):
        print(f"  {i}. {nom}")
    choix = demander_nombre("numéro du dessin", minimum=1)
    if choix > len(noms):
        print("  Dessin inconnu")
        return
    x, y = demander_nombre("x"), demander_nombre("y")
    taille = demander_nombre("taille", minimum=10)
    with open(os.path.join(DOSSIER_DESSINS, noms[choix - 1] + ".json"), encoding="utf-8") as f:
        for forme in json.load(f):
            envoyer(placer(forme, x, y, taille))


def envoyer(forme: Forme) -> None:
    try:
        r = requests.post(URL + "/draw", json=forme, timeout=5)
    except requests.ConnectionError:
        print("  Serveur injoignable : lancez server.py")
        return
    if r.status_code == 201:
        print(f"  OK : {forme['shape']} envoyé à {r.json()['tableaux']} tableau(x)")
    else:
        print(f"  Erreur {r.status_code} : {r.json()['detail']}")


while True:
    print("\n1. Point  2. Ligne  3. Cercle  4. Rectangle  5. Carré  6. Dessin composé  7. Effacer  0. Quitter")
    choix = input("> ")
    if choix == "0":
        break
    elif choix in MENU:
        envoyer(demander_forme(MENU[choix]))
    elif choix == "6":
        dessin_compose()
    elif choix == "7":
        requests.delete(URL + "/draw", timeout=5)
        print("  Tableau effacé")
    else:
        print("  Choix inconnu")
