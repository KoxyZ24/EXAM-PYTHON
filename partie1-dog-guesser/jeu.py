"""Dog Guesser : retrouve la race du chien sur la photo. Lancement : python jeu.py"""

import csv
import json
import os
import random
import re
import time
import tkinter as tk
from datetime import datetime
from io import BytesIO
from tkinter import messagebox, simpledialog

import requests
from PIL import Image, ImageTk
from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect

API: str = os.environ.get("DOG_API", "https://dog.ceo/api")
SERVEUR: str = os.environ.get("DOG_SERVEUR", "ws://localhost:8765")
HISTORIQUE: str = "historique.csv"
NB_PHOTOS: int = 10

Classement = list[list]               # [["alice", 1450], ["bob", 980]]


# ---------- API dog.ceo ----------

def appel_api(chemin: str) -> dict:
    return requests.get(API + chemin, timeout=5).json()


def liste_races() -> list[str]:
    races = []
    for race, sous_races in appel_api("/breeds/list/all")["message"].items():
        if sous_races:
            races += [f"{race}-{s}" for s in sous_races]    # "hound-afghan", "hound-basset"...
        else:
            races.append(race)
    return races


def chien_aleatoire() -> tuple[str, str]:
    url = appel_api("/breeds/image/random")["message"]
    # https://images.dog.ceo/breeds/hound-afghan/n02088094_1003.jpg  ->  "hound-afghan"
    race = re.search(r"/breeds/(?P<race>[\w-]+)/", url).group("race")
    return url, race


def nom_lisible(race: str) -> str:
    mots = race.split("-")
    if mots[0] != "australian":
        mots.reverse()                                     # "hound-afghan" -> "Afghan Hound"
    return " ".join(mots).title()


# ---------- Historique local (CSV) ----------

def sauver_partie(joueur: str, score: int) -> None:
    nouveau_fichier = not os.path.exists(HISTORIQUE)
    with open(HISTORIQUE, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "joueur", "score"])
        if nouveau_fichier:
            writer.writeheader()
        writer.writerow({"date": f"{datetime.now():%Y-%m-%d %H:%M}", "joueur": joueur, "score": score})


def record_perso(joueur: str) -> int:
    if not os.path.exists(HISTORIQUE):
        return 0
    with open(HISTORIQUE, encoding="utf-8") as f:
        scores = [int(ligne["score"]) for ligne in csv.DictReader(f) if ligne["joueur"] == joueur]
    return max(scores, default=0)


def calcul_points(temps: float) -> int:
    return 100 + max(0, 100 - int(temps * 10))    # 100 pts + bonus de rapidité (-10 par seconde)


# ---------- Interface ----------

class DogGuesser:
    def __init__(self, fenetre: tk.Tk) -> None:
        self.fenetre = fenetre
        fenetre.title("Dog Guesser")
        fenetre.protocol("WM_DELETE_WINDOW", self.quitter)
        self.joueur = simpledialog.askstring("Dog Guesser", "Ton pseudo :") or "anonyme"
        self.races = liste_races()
        try:
            self.ws = connect(SERVEUR, open_timeout=2)
        except OSError:
            self.ws = None

        self.label_classement = tk.Label(fenetre, font=("Arial", 12), fg="#8A5A00")
        self.label_classement.pack(pady=5)
        self.label_info = tk.Label(fenetre, font=("Arial", 14, "bold"))
        self.label_info.pack()
        self.label_image = tk.Label(fenetre)
        self.label_image.pack(padx=20, pady=10)
        cadre = tk.Frame(fenetre)
        cadre.pack()
        self.boutons = []
        for i in range(4):
            bouton = tk.Button(cadre, width=28, height=2, font=("Arial", 12, "bold"),
                               command=lambda i=i: self.repondre(i))
            bouton.grid(row=i // 2, column=i % 2, padx=5, pady=5)
            self.boutons.append(bouton)
            fenetre.bind(str(i + 1), lambda e, i=i: self.repondre(i))   # touches 1 à 4
        self.label_resultat = tk.Label(fenetre, font=("Arial", 13, "bold"))
        self.label_resultat.pack(pady=10)

        self.verifier_serveur()
        self.nouvelle_partie()

    def verifier_serveur(self) -> None:
        """Toutes les 300 ms : lit le classement envoyé par le serveur, s'il y en a un."""
        if self.ws is None:
            self.label_classement.config(text="🏆 Classement : serveur hors ligne")
            return
        try:
            top: Classement = json.loads(self.ws.recv(timeout=0))
            texte = "   ".join(f"{i}. {joueur} ({score} pts)" for i, (joueur, score) in enumerate(top, 1))
            self.label_classement.config(text="🏆 " + (texte or "Aucun record"))
        except TimeoutError:
            pass                                     # pas de nouveau message
        except ConnectionClosed:
            self.ws = None
        self.fenetre.after(300, self.verifier_serveur)

    def nouvelle_partie(self) -> None:
        self.score = 0
        self.numero = 0
        self.photo_suivante()

    def photo_suivante(self) -> None:
        try:
            url, self.bonne_race = chien_aleatoire()
            image = Image.open(BytesIO(requests.get(url, timeout=5).content))
        except requests.RequestException:
            self.label_resultat.config(text="dog.ceo ne répond pas, nouvel essai...", fg="red")
            self.fenetre.after(2000, self.photo_suivante)
            return
        image.thumbnail((500, 380))
        self.photo = ImageTk.PhotoImage(image)        # garder une référence, sinon l'image disparaît
        self.label_image.config(image=self.photo)

        self.numero += 1
        self.choix = random.sample([r for r in self.races if r != self.bonne_race], 3) + [self.bonne_race]
        random.shuffle(self.choix)
        for i, race in enumerate(self.choix):
            self.boutons[i].config(text=f"{i + 1}. {nom_lisible(race)}", bg="white")
        self.label_info.config(text=f"{self.joueur} · Photo {self.numero}/{NB_PHOTOS} · "
                                    f"Score : {self.score} · Ton record : {record_perso(self.joueur)}")
        self.label_resultat.config(text="")
        self.en_attente = True
        self.debut = time.time()

    def repondre(self, i: int) -> None:
        if not self.en_attente:                       # évite les doubles clics
            return
        self.en_attente = False
        bonne = self.choix.index(self.bonne_race)
        self.boutons[bonne].config(bg="lightgreen")
        if i == bonne:
            points = calcul_points(time.time() - self.debut)
            self.score += points
            self.label_resultat.config(text=f"Bravo ! +{points} pts", fg="green")
        else:
            self.boutons[i].config(bg="salmon")
            self.label_resultat.config(text=f"Raté, c'était : {nom_lisible(self.bonne_race)}", fg="red")
        suite = self.photo_suivante if self.numero < NB_PHOTOS else self.fin_partie
        self.fenetre.after(1500, suite)

    def fin_partie(self) -> None:
        ancien_record = record_perso(self.joueur)
        sauver_partie(self.joueur, self.score)
        if self.ws is not None:
            self.ws.send(json.dumps({"joueur": self.joueur, "score": self.score}))
        bilan = "Nouveau record perso !" if self.score > ancien_record else f"Ton record : {ancien_record} pts"
        if messagebox.askyesno("Partie terminée", f"Score : {self.score} pts\n{bilan}\n\nRejouer ?"):
            self.nouvelle_partie()
        else:
            self.quitter()

    def quitter(self) -> None:
        if self.ws is not None:
            self.ws.close()
        self.fenetre.destroy()


if __name__ == "__main__":
    fenetre = tk.Tk()
    try:
        DogGuesser(fenetre)
        fenetre.mainloop()
    except requests.RequestException:
        print("Impossible de joindre l'API dog.ceo")
