# database.py

from pymongo import MongoClient
import config

class Database:
    def __init__(self):
        self.client = MongoClient(config.MONGODB_URI)
        
        # Connessione al database 'telegram-app'
        self.db_telegram_app = self.client['telegram-app']
        self.collection_canali = self.db_telegram_app['canali']  # Assicurati che il nome della collezione sia corretto
    
        # Connessione al database 'telegram-eco'
        self.db_telegram_eco = self.client['telegram-eco']
        self.collection_entries = self.db_telegram_eco['entries']

    def get_db(self):
        """Restituisce il database 'telegram-app' per mantenere la compatibilità."""
        return self.db_telegram_app

    def get_collection_canali(self):
        """Restituisce la collezione 'canali' dal database 'telegram-app'."""
        return self.collection_canali

    def get_collection_entries(self):
        """Restituisce la collezione 'entries' dal database 'telegram-eco'."""
        return self.collection_entries

    def get_db_telegram_app(self):
        """Restituisce l'istanza del database 'telegram-app'."""
        return self.db_telegram_app

    def get_db_telegram_eco(self):
        """Restituisce l'istanza del database 'telegram-eco'."""
        return self.db_telegram_eco
