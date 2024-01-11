import telebot
import config
import os
import pandas as pd
from datetime import datetime
from database import Database
import interazioni # gestisce il salvatagio nel db delle interazioni tra utente e bot
from io import BytesIO


def setup_check_module(bot):
    # Ottieni l'istanza del database
    database = Database()
    db = database.get_db()
    
    if db is None:
        print("Errore: Impossibile ottenere l'istanza del database.")
        return
    # Ottenere la data e l'orario corrente come un oggetto datetime
    now = datetime.now()

    # Formattare la data e l'orario nel formato desiderato (giorno/mese/anno ora:minuto:secondo)
    formatted_datetime = now.strftime("%d-%m-%Y %H:%M:%S")

    def create_csv_and_send(chat_id):
        try:
            # Stampa un messaggio di stato
            print("Creazione del file CSV in corso...")

            data = []

            # Ottieni tutti i documenti che iniziano con "Libreria:"
            libreria_documents = db.list_collection_names(filter={"name": {"$regex": "^Libreria:"}})

            for collection_name in libreria_documents:
                # Estrai il nome della libreria dalla collezione
                libreria_name = collection_name.replace("Libreria: ", "")

                # Trova tutti i documenti nella collezione
                documents = db[collection_name].find()

                for doc in documents:
                    # Controllo se il campo "Type" ha un valore di "show"
                    if doc.get('Type') == 'show':
                        # Estrai le informazioni rilevanti
                        title = doc.get('Title', '')
                        year = doc.get('Year', '')
                        seasons_info = doc.get('Seasons', [])

                        missing_episodes = []

                        for season_info in seasons_info:
                            season = str(season_info.get('SeasonNumber', ''))
                            episode_numbers = season_info.get('Episodes', [])

                            # Calcola il valore massimo degli episodi per questa stagione
                            max_episode = max(int(episode.get('EpisodeNumber', '0')) for episode in episode_numbers if episode.get('EpisodeNumber', ''))

                            # Trova gli episodi mancanti
                            missing = [str(i).zfill(2) for i in range(1, max_episode + 1) if str(i).zfill(2) not in [episode.get('EpisodeNumber', '') for episode in episode_numbers if episode.get('EpisodeNumber', '')]]

                            if missing:
                                missing_episodes.append(f'Stagione {season}: {", ".join(missing)}')

                        if missing_episodes:
                            # Creare una riga di dati per il CSV
                            data_row = {
                                'Nome Libreria': f'{libreria_name}',
                                'Nome Serie': f'{title} ({str(year)})',
                                'Episodi Mancanti': ', '.join(missing_episodes)
                            }

                            data.append(data_row)

            # Creare un DataFrame da questi dati
            df = pd.DataFrame(data)

            # Ottenere il percorso dello script attuale
            script_dir = os.path.dirname(os.path.abspath(__file__))

            # Creare il percorso completo della cartella "csv" all'interno della cartella dello script
            csv_dir = os.path.join(script_dir, 'csv')

            # Verifica se la cartella "csv" esiste, altrimenti creala
            if not os.path.exists(csv_dir):
                os.makedirs(csv_dir)

            # Creare il percorso completo del file CSV all'interno della cartella "csv"
            csv_filename = os.path.join(csv_dir, f'lista-episodi-mancanti-{formatted_datetime}.csv')

            # Salvare il DataFrame in un file CSV
            df.to_csv(csv_filename, index=False)

            # Ora invia il file CSV nella chat del bot
            with open(csv_filename, 'rb') as file:
                message = bot.send_document(chat_id, document=file, caption="La tua caption qui.")
                # Ora puoi accedere all'ID del messaggio
                invia_documento = message.message_id

                # E puoi anche accedere all'ID della chat se necessario
                chat_id = message.chat.id

                #interazioni.save_message(chat_id, "Invio Lista CSV", is_user=False, forwarded_from=None, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=message.message_id)
                print(invia_documento)

            # Stampa un messaggio di completamento
            print("File CSV creato e inviato con successo!")

            # Stampa un messaggio se il campo "Type" non è "show" in un documento
            print("Alcuni documenti non hanno il campo 'Type' uguale a 'show' e sono stati ignorati.")

        except Exception as e:
            # Stampa un messaggio di errore se si verifica un'eccezione
            print(f"Errore: {str(e)}")

    # Gestisci il comando /check
    @bot.message_handler(commands=['check'])
    def handle_check(message):
        chat_id = message.chat.id

        # Esegui la funzione per creare il CSV e inviarlo
        create_csv_and_send(chat_id)
