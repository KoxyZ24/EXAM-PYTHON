"""Serveur des records du Dog Guesser (WebSocket). Lancement : python server.py"""

import asyncio
import json
import os
from datetime import datetime

from websockets.asyncio.server import broadcast, serve
from websockets.exceptions import ConnectionClosed

HOTE: str = os.environ.get("DOG_HOTE", "0.0.0.0")      # 0.0.0.0 : accessible depuis les autres machines
PORT: int = int(os.environ.get("DOG_PORT", "8765"))
FICHIER_RECORDS: str = os.path.join("donnees", "records.json")
FICHIER_LOG: str = os.path.join("donnees", "serveur.log")

Records = dict[str, int]              # {"alice": 1450, "bob": 980}
Classement = list[tuple[str, int]]    # [("alice", 1450), ("bob", 980)]

os.makedirs("donnees", exist_ok=True)
joueurs = set()


def log(message: str) -> None:
    ligne = f"{datetime.now():%Y-%m-%d %H:%M:%S} [INFO] {message}"
    print(ligne)
    with open(FICHIER_LOG, "a", encoding="utf-8") as f:
        f.write(ligne + "\n")


def charger_records() -> Records:
    if not os.path.exists(FICHIER_RECORDS):
        return {}
    with open(FICHIER_RECORDS, encoding="utf-8") as f:
        return json.load(f)


records: Records = charger_records()


def classement() -> Classement:
    return sorted(records.items(), key=lambda r: r[1], reverse=True)[:5]


async def handler(ws) -> None:
    joueurs.add(ws)
    await ws.send(json.dumps(classement()))        # classement actuel dès la connexion
    try:
        async for message in ws:
            data = json.loads(message)
            joueur, score = data["joueur"], data["score"]
            log(f"{joueur} : {score} pts")
            if score > records.get(joueur, 0):
                records[joueur] = score
                with open(FICHIER_RECORDS, "w", encoding="utf-8") as f:
                    json.dump(records, f, indent=2)
                broadcast(joueurs, json.dumps(classement()))   # envoyé à tous les joueurs connectés
    except ConnectionClosed:
        pass
    finally:
        joueurs.remove(ws)


async def main() -> None:
    async with serve(handler, HOTE, PORT):
        log(f"Serveur des records lancé sur le port {PORT}")
        await asyncio.Future()                     # tourne indéfiniment


asyncio.run(main())
