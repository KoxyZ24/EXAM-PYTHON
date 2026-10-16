# TP3 · Communiquer à travers le réseau

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/Mac : source .venv/bin/activate
pip install -r requirements.txt
```

## Partie I · Dog Guesser

```bash
cd partie1-dog-guesser
python server.py    # serveur des records (WebSocket, port 8765)
python jeu.py       # le jeu, dans un autre terminal (on peut en lancer plusieurs)
```

- Une photo de dog.ceo, 4 races proposées, 10 photos par partie, réponse au clic ou avec les touches 1 à 4.
- Score : 100 pts par bonne réponse + bonus de rapidité (100 pts, moins 10 par seconde).
- `jeu.py` sauvegarde les parties dans `mes_scores.json` et envoie le score au serveur.
- `server.py` garde le meilleur score de chaque joueur dans `records.json` et renvoie le classement
  à tous les joueurs connectés dès qu'un record tombe.

## Partie II · Tableau interactif

```bash
cd partie2-tableau
python server.py    # puis ouvrir http://localhost:8000 (un onglet = un tableau)
python client.py    # dans un autre terminal
```

- `client.py` demande la forme en ligne de commande et l'envoie avec `POST /draw`.
- `server.py` (FastAPI) vérifie la forme (erreur 400 si elle est invalide) et la retransmet par WebSocket à tous les tableaux.
- `tableau.html` dessine les formes dans un `<canvas>`. Un tableau ouvert plus tard reçoit les formes déjà dessinées.
- En plus de l'API demandée : une maison composée de plusieurs formes, l'effacement (`DELETE /draw`)
  et l'affichage de la position de la souris pour choisir les coordonnées.

## Utilisation de l'IA

 **Tests et corrections** : cas où le serveur ou l'API dog.ceo ne répondent pas, saisies invalides dans le client.
 **Aide à la conception** : Aide à la conception graphique et serveur.
