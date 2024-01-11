import pymongo
import argparse
import urllib.parse
from pymongo import MongoClient

# Credenziali MongoDB
MONGODB_HOST = "plex-aik.ddns.net"
MONGODB_PORT = 27017
MONGODB_USERNAME = "Aik"
MONGODB_PASSWORD = "16889@Al@mon"

# Codifica pass utente
MONGODB_USERNAME_ENCODED = urllib.parse.quote_plus(MONGODB_USERNAME)
MONGODB_PASSWORD_ENCODED = urllib.parse.quote_plus(MONGODB_PASSWORD)

# Definizione delle sequenze di escape ANSI per il colore del testo
BLUE = '\033[94m'
YELLOW = '\033[93m'
END = '\033[0m'  # Termina il colore

# Funzione per aggiornare il campo "Name" nei documenti
def update_documents(db):
    documents_to_update = db[args.documento].find()

    for document in documents_to_update:
        for season in document["Seasons"]:
            for episode in season["Episodes"]:
                for content in episode["Contents"]:
                    name = content["Name"]
                    if " - S" in name and "E" in name:
                        parts = name.split(" - S")
                        if len(parts) == 2:
                            name_parts = parts[0].strip().split("(")
                            if len(name_parts) == 1:
                                year = document.get("Year", 0)  # Ottieni l'anno dal campo "Year", default a 0 se non presente
                                episode_parts = parts[1].split("E")
                                if len(episode_parts) == 2:
                                    episode_number = episode_parts[0].strip()
                                    remainder = episode_parts[1].strip()
                                    updated_name = f"{name_parts[0].strip()} ({year}) - S{episode_number}E{remainder}"

                                    # Stampa il "prima" in azzurro e il "dopo" in giallo
                                    print(f"{BLUE}Prima:{name} {END} ")
                                    print(f"{YELLOW}Dopo:{updated_name} {END}")

                                    content["Name"] = updated_name
                                    print(f"Modellando: il nome dal campo Name in '{updated_name}'")

        # Aggiorna il documento nel database
        db[args.documento].update_one(
            {"_id": document["_id"]},
            {"$set": {"Seasons": document["Seasons"]}}
        )

# Parser degli argomenti da linea di comando
parser = argparse.ArgumentParser(description="Modifica il campo 'Name' nei documenti.")
parser.add_argument("--documento", type=str, required=True, help="Nome del documento")

args = parser.parse_args()

# Crea la variabile MONGODB_URI utilizzando le variabili di connessione
MONGODB_URI = f"mongodb://{MONGODB_USERNAME_ENCODED}:{MONGODB_PASSWORD_ENCODED}@{MONGODB_HOST}:{MONGODB_PORT}/?authMechanism=DEFAULT"

# Crea una connessione al server MongoDB utilizzando l'URL di connessione
client = MongoClient(MONGODB_URI)

# Seleziona il database
db = client["telegram-app"]

# Esegui la funzione di aggiornamento dei documenti
update_documents(db)

print(f"Aggiornamento completato per tutti i documenti nel database.")
