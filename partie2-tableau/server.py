"""Serveur du tableau interactif (FastAPI) : API HTTP POST /draw + WebSocket /ws.

Lancement : python server.py   puis ouvrir http://localhost:8000 (un onglet = un tableau)
"""

import json
import os

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

PORT: int = int(os.environ.get("TABLEAU_PORT", "8000"))
DOSSIER: str = os.path.dirname(os.path.abspath(__file__))
FICHIER_DESSIN: str = os.path.join(DOSSIER, "donnees", "dessin.json")

Forme = dict[str, int | str | list[int]]

# Champs obligatoires de chaque forme (documentation du sujet)
CHAMPS: dict[str, list[str]] = {
    "point": ["x", "y", "color"],
    "line": ["x1", "y1", "x2", "y2", "color"],
    "circle": ["x", "y", "radius", "color"],
    "rectangle": ["x", "y", "width", "height", "color"],
    "square": ["x", "y", "cote", "color"],
}

os.makedirs(os.path.join(DOSSIER, "donnees"), exist_ok=True)
app = FastAPI()
tableaux: list[WebSocket] = []          # pages web connectées
formes: list[Forme] = []                # formes déjà dessinées
if os.path.exists(FICHIER_DESSIN):
    with open(FICHIER_DESSIN, encoding="utf-8") as f:
        formes = json.load(f)


def sauver_dessin() -> None:
    with open(FICHIER_DESSIN, "w", encoding="utf-8") as f:
        json.dump(formes, f, indent=2)


async def envoyer_a_tous(message: dict) -> None:
    for ws in tableaux:
        await ws.send_json(message)


@app.get("/")
def page_tableau() -> HTMLResponse:
    with open(os.path.join(DOSSIER, "tableau.html"), encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.post("/draw", status_code=201)     # 201 Created
async def dessiner(forme: dict) -> dict:
    if forme.get("shape") not in CHAMPS:
        raise HTTPException(400, f"Forme inconnue, formes possibles : {list(CHAMPS)}")
    manquants = [champ for champ in CHAMPS[forme["shape"]] if champ not in forme]
    if manquants:
        raise HTTPException(400, f"Champs manquants : {manquants}")
    formes.append(forme)
    sauver_dessin()
    await envoyer_a_tous(forme)
    return {"tableaux": len(tableaux)}


@app.get("/draw")
def lister_formes() -> list[Forme]:
    return formes


@app.delete("/draw")
async def effacer() -> dict:
    formes.clear()
    sauver_dessin()
    await envoyer_a_tous({"shape": "clear"})
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_tableau(ws: WebSocket) -> None:
    await ws.accept()
    tableaux.append(ws)
    for forme in formes:                # un nouveau tableau reçoit tout le dessin
        await ws.send_json(forme)
    try:
        while True:
            await ws.receive_text()     # on attend juste la déconnexion
    except WebSocketDisconnect:
        tableaux.remove(ws)


uvicorn.run(app, host="0.0.0.0", port=PORT)
