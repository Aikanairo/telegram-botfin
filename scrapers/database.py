from pymongo import MongoClient
import config
import threading

# Utilizzare threading.local per mantenere le connessioni separate per ogni thread
local = threading.local()

class Database:
    def __init__(self):
        self.client = None
        self.db = None

    def connect(self):
        try:
            self.client = MongoClient(config.MONGODB_URI)
            self.db = self.client[config.DB_NAME]
            print("Connessione al database stabilita.")
        except Exception as e:
            print(f"Errore durante la connessione al database: {str(e)}")

    def close(self):
        if self.client:
            self.client.close()
            print("Connessione al database chiusa.")

    def get_db(self):
        if not hasattr(local, "db") or local.db is None:
            # Se la connessione locale non esiste o è stata chiusa, creane una nuova
            self.connect()
            local.db = self.db
        return local.db
