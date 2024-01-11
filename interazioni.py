from database import Database
import datetime

# Crea un'istanza della classe Database
database_instance = Database()

# Funzione per salvare un messaggio nel database
def save_message(chat_id, message_text, is_user=True, forwarded_from=None, bot_chat_id=None, user_id=None, message_id=None, user_name=None):
    try:
        # Ottieni un riferimento al database
        db = database_instance.get_db()

        # Ottieni la data e l'ora correnti
        timestamp = datetime.datetime.now()

        # Trova il documento dell'utente nel database o crea uno nuovo se non esiste
        user_doc = db.Users.find_one({"user_id": user_id})
        if user_doc is None:
            user_doc = {
                "user_id": user_id,
                "user_name": user_name,  # Sostituisci con il nome dell'utente se disponibile
                "bot_chat_id": bot_chat_id,
                "chat_id": chat_id,
                "permessi": 0, # 0 visitatore 1 fruitore 2 gestore 3 full admin
                "interactions": []  # Inizializza l'elenco delle interazioni
                
        }

        # Creare un documento per l'interazione
        interaction_doc = {
            "chat_id": chat_id,
            "message_text": message_text,
            "is_user": is_user,
            "forwarded_from": forwarded_from,
            "bot_chat_id": bot_chat_id,
            "user_id": user_id,
            "user_name": user_name,
            "message_id": message_id,
            "timestamp": timestamp,
        }

        # Aggiungi l'interazione al documento dell'utente
        user_doc["interactions"].append(interaction_doc)

        # Aggiorna il documento dell'utente nel database
        db.Users.update_one({"user_id": user_id}, {"$set": user_doc}, upsert=True)

        # Interazione salvata con successo
        #return True

        # Inserimento Log

        # Trova il documento dell'utente nel database o crea uno nuovo se non esiste
        log_user_doc = db["Log Users"].find_one({"user_id": user_id})
        if log_user_doc is None:
            log_user_doc = {
                "user_id": user_id,
                "user_name": user_name,
                "bot_chat_id": bot_chat_id,
                "chat_id": chat_id,
                "log": []  # Inizializza l'elenco dei log
                
        }

        # Creare un documento per l'interazione
        log_doc = {
            "chat_id": chat_id,
            "message_text": message_text,
            "is_user": is_user,
            "forwarded_from": forwarded_from,
            "bot_chat_id": bot_chat_id,
            "user_id": user_id,
            "user_name": user_name,  # Aggiungi il nome dell'utente subito dopo user_id
            "message_id": message_id,
            "timestamp": timestamp,
        }

        # Aggiungi il log al documento dell'utente
        log_user_doc["log"].append(log_doc)


        # Aggiorna il documento dell'utente nel database
        #db.Log Users.update_one({"user_id": user_id}, {"$set": user_doc}, upsert=True)
        db["Log Users"].update_one({"user_id": user_id}, {"$set": log_user_doc}, upsert=True)


        # Log salvato con successo
        return True

    except Exception as e:
        print(f"Errore durante il salvataggio dell'interazione nel database: {str(e)}")
        return False

def select_cronologia_messaggi(user_id, user_name):
    try:
        # Ottieni un riferimento al database
        db = database_instance.get_db()

        # Trova il documento dell'utente nel database in base all'ID utente e al nome utente
        user_doc = db.Users.find_one({"user_id": user_id, "user_name": user_name})

        # Se il documento dell'utente esiste
        if user_doc:
            # Estrai la cronologia delle interazioni dal documento dell'utente
            interazioni = user_doc.get("interactions", [])

            # Estrai tutti i message_id dalle interazioni
            message_ids = [interazione.get("message_id") for interazione in interazioni]

            # Restituisci la lista di tutti i message_id
            return message_ids
        else:
            return []
    except Exception as e:
        print(f"Errore durante la selezione dei message_id nel database: {str(e)}")
        return []

# Funzione per aggiornare il db quando si attiva il pulsante torna indietro
def attivazione_pulsante_back(user_id, user_name):
    try:
        # Ottieni un riferimento al database
        db = database_instance.get_db()
        # Ottieni la connessione al database

        # Cerca il documento che corrisponde al user_id
        user_document = db['Users'].find_one({"user_id": user_id})

        if user_document:
            # Rimuovi tutti i contenuti annidati dentro interactions
            user_document['interactions'] = []
            db['Users'].update_one({"user_id": user_id}, {"$set": {"interactions": []}})
            return True
        else:
            return False

    except Exception as e:
        print(f"Errore durante l'eliminazione dei messaggi: {str(e)}")
        return False

# 

def chiudi_messaggio(user_id, user_name, message_id):
    try:
        # Ottieni un riferimento al database
        db = database_instance.get_db()
        
        # Cerca il documento Users corrispondente all'utente
        user_document = db['Users'].find_one({"user_id": user_id})
        
        if user_document:
            # Estrai la lista delle interazioni
            interactions = user_document.get('interactions', [])
            
            # Itera sulle interazioni e rimuovi quella con message_id specifico
            for interaction in interactions:
                if interaction.get('message_id') == message_id:
                    interactions.remove(interaction)
            
            # Aggiorna il documento Users con la lista di interazioni modificata
            db['Users'].update_one({"user_id": user_id}, {"$set": {"interactions": interactions}})
            
            return True
        else:
            return False
    except Exception as e:
        print(f"Errore durante l'eliminazione del messaggio: {str(e)}")
        return False

