import asyncio
import argparse
from datetime import datetime
from pymongo import MongoClient
from telethon.sync import TelegramClient
from telethon.tl import types
from telethon.tl.types import DocumentAttributeFilename
from telethon.tl.functions.channels import GetFullChannelRequest
import urllib.parse
import re
from tqdm import tqdm  # Importa il modulo tqdm

# Credenziali MongoDB
MONGODB_HOST = "plex-aik.ddns.net"
MONGODB_PORT = 27017
MONGODB_USERNAME = "Aik"
MONGODB_PASSWORD = "16889@Al@mon"
MONGODB_DATABASE = "telegram-drive"

# Codifica pass utente
MONGODB_USERNAME_ENCODED = urllib.parse.quote_plus(MONGODB_USERNAME)
MONGODB_PASSWORD_ENCODED = urllib.parse.quote_plus(MONGODB_PASSWORD)

# Crea la variabile MONGODB_URI utilizzando le variabili di connessione
MONGODB_URI = f"mongodb://{MONGODB_USERNAME_ENCODED}:{MONGODB_PASSWORD_ENCODED}@{MONGODB_HOST}:{MONGODB_PORT}/?authMechanism=DEFAULT"

# Crea una connessione al server MongoDB utilizzando l'URL di connessione
client_mongodb = MongoClient(MONGODB_URI)

# Accedi al database MongoDB
db = client_mongodb[MONGODB_DATABASE]

# Credenziali dell'API Telegram
API_ID = "1797369"
API_HASH = "ea3204de669492fd7732df8440079e1f"
BOT_TOKEN = "6401590878:AAE_6f-pOH4QqnPNlBSAYeALCX1EPEni6dg"

# Numero di telefono del tuo account Telegram
phone_number = '+393667749398'

async def get_max_message_id(client, channel):
    full_channel = await client(GetFullChannelRequest(channel))
    return full_channel.full_chat.id

async def save_media_to_mongodb(channel_id):
    season_number = None  # Inizializzo season_number all'inizio della funzione
    episode_number = None  # Inizializzo episode_number all'inizio della funzione
    async with TelegramClient('extract_media', API_ID, API_HASH) as client:
        # Accedi con il numero di telefono
        await client.start(phone=phone_number)

        # Ottieni le informazioni sul canale utilizzando l'ID del canale
        try:
            channel = await client.get_entity(int(channel_id))
        except ValueError:
            print(f"Il canale con l'ID {channel_id} non è stato trovato. Verifica l'ID del canale.")
            return

        # Nome del canale estratto dall'ID del canale
        channel_name = channel.title

        # Crea una connessione al server MongoDB
        client_mongodb = MongoClient(MONGODB_URI)

        # Accedi al database MongoDB
        db = client_mongodb[MONGODB_DATABASE]

        # Crea una collezione (collection) nel database per i file del canale
        library_collection_name = f"Libreria: {channel_name}"
        library_collection = db[library_collection_name]

        # Verifica se ci sono documenti nel database "Libreria: nome canale"
        if library_collection.count_documents({}) > 0:
            # Trova il valore più alto di "Message ID" tra i documenti esistenti
            max_message_document = library_collection.find_one(sort=[('Message ID', -1)])
            if max_message_document:
                max_message_id = max_message_document['Message ID']
            else:
                max_message_id = 0
        else:
            # Se non ci sono documenti, imposta max_message_id a 0
            max_message_id = 0

        # Contatore per i media importati
        media_imported = 0

        # Data e ora dell'importazione da Telegram
        import_datetime = datetime.now()

        # Conta il numero totale di messaggi per il progresso
        total_messages = (await client.get_messages(channel, limit=0)).total

        # Crea la barra di progresso
        pbar = tqdm(total=total_messages, desc="Processing messages")

        # Estrai i media dal canale a partire dal Message ID successivo
        async for message in client.iter_messages(channel, min_id=max_message_id, limit=None, reverse=True):
            pbar.update(1)  # Aggiorna la barra di progresso

            if message.media:
                media_info = {
                    'Data': message.date,
                    'Tipo Media': message.media.__class__.__name__,
                    'Testo': message.text,
                    'Nome Canale': channel_name,
                    'Chat ID': int(channel_id),
                    'From Chat ID': int(message.from_id.channel_id) if isinstance(message.from_id, types.PeerChannel) else None,
                    'Message ID': int(message.id),
                    'Data Import': import_datetime  # Aggiunto il campo Data Import
                }
                if hasattr(message.media, 'photo'):
                    media_info['Dimensioni Foto'] = message.media.photo.sizes[-1].w, message.media.photo.sizes[-1].h
                elif hasattr(message.media, 'video') and hasattr(message.media.video, 'duration'):
                    media_info['Durata Video (secondi)'] = message.media.video.duration
                elif hasattr(message.media, 'document'):
                    for attr in message.media.document.attributes:
                        if isinstance(attr, DocumentAttributeFilename):
                            media_info['Name'] = attr.file_name
                            media_info['Dimensioni Documento (bytes)'] = message.media.document.size
                            media_info['File ID'] = message.media.document.id

                            # Estrai il valore di Name dal testo del messaggio, se presente
                            text = message.text
                            if text:
                                match = re.search(r'(?i)FileName: (.+)', text)
                                if match:
                                    name_from_text = match.group(1).strip()
                                    # Qui imposti il valore di Name nel dizionario media_info
                                    media_info['Name'] = name_from_text

                # Aggiungi il controllo per 'Year', 'Title', 'Type', 'Season', 'Episode' qui
                media_data = {}

                # Inizializza la variabile part a None
                part = 0

                # Controllo se il messaggio.text contiene la chiave "Part"
                if message.text:
                    text_lines = message.text.strip().split('\n')
                    for line in text_lines:
                        parts = line.split(':')
                        if len(parts) == 2:
                            key, value = parts[0].strip(), parts[1].strip()
                            media_data[key] = value

                            if key == 'Season':
                                season_number = value
                            elif key == 'Episode':
                                episode_number = value
                            elif key == 'Part':
                                # Controllo se il valore contiene "/" e se sì, estraggo la parte prima
                                part = value.split('/')[0].strip()
                                # Verifica se part è un numero valido prima di assegnarlo
                                if part.isdigit():
                                    part = int(part)
                                else:
                                    part = 0

                year_str = media_data.get('Year', '0')
                if year_str.isdigit():
                    year = int(year_str)
                else:
                    year = 0

                # Imposta il flag su True se sono stati importati nuovi media
                media_imported += 1

                # Verifica il campo Testo per categorizzare il media
                if message.text:
                    text_lines = message.text.strip().split('\n')
                    media_data = {}
                    for line in text_lines:
                        parts = line.split(':')
                        if len(parts) == 2:
                            key, value = parts[0].strip(), parts[1].strip()
                            media_data[key] = value

                    # Se il campo "Title" è presente, crea il documento "Libreria: nome Canale"
                    if 'Title' in media_data:
                        title = media_data['Title']

                        # Cerca un documento esistente che corrisponda a "Title" ed "Year"
                        existing_document = library_collection.find_one({'Title': title, 'Year': year})

                        if existing_document:
                            # Se esiste già un documento con lo stesso "Title" ed "Year", aggiungi le informazioni alla struttura esistente
                            season_exists = False
                            for season in existing_document.get('Seasons', []):
                                if season['SeasonNumber'] == (int(season_number) if season_number else ""):
                                    # Cerca l'episodio esistente con lo stesso numero di episodio
                                    episode_exists = False
                                    for episode in season['Episodes']:
                                        if episode['EpisodeNumber'] == (int(episode_number) if episode_number else ""):
                                            episode['Contents'].append({
                                                'Size': media_info['Dimensioni Documento (bytes)'],
                                                'Name': media_info['Name'],  # Utilizza il valore estratto
                                                'Part': int(part),
                                                'Message ID': int(message.id),
                                                'File ID': media_info['File ID'],
                                                'Tipo Media': media_info['Tipo Media']
                                            })
                                            episode_exists = True
                                            break

                                    # Se non esiste un episodio con lo stesso numero di episodio, crea un nuovo episodio
                                    if not episode_exists:
                                        season['Episodes'].append({
                                            'EpisodeNumber': (int(episode_number) if episode_number else ""),
                                            'Contents': [{
                                                'Size': media_info['Dimensioni Documento (bytes)'],
                                                'Name': media_info['Name'],  # Utilizza il valore estratto
                                                'Part': int(part),
                                                'Message ID': int(message.id),
                                                'File ID': media_info['File ID'],
                                                'Tipo Media': media_info['Tipo Media']
                                            }]
                                        })
                                    season_exists = True
                                    break

                            # Se la stagione non esiste, crea una nuova stagione
                            if not season_exists:
                                existing_document['Seasons'].append({
                                    'SeasonNumber': (int(season_number) if season_number else ""),
                                    'Episodes': [{
                                        'EpisodeNumber': (int(episode_number) if episode_number else ""),
                                        'Contents': [{
                                            'Size': media_info['Dimensioni Documento (bytes)'],
                                            'Name': media_info['Name'],  # Utilizza il valore estratto
                                            'Part': int(part),
                                            'Message ID': int(message.id),
                                            'File ID': media_info['File ID'],
                                            'Tipo Media': media_info['Tipo Media']
                                        }]
                                    }]
                                })

                            # Aggiorna il documento esistente nel database
                            library_collection.update_one({'_id': existing_document['_id']}, {'$set': existing_document})
                        else:
                            # Se non esiste un documento con lo stesso "Title" ed "Year", crea un nuovo documento
                            library_document = {
                                'Nome Canale': channel_name,
                                'Canale ID': int(channel_id),
                                'Title': title,
                                'Year': int(year),
                                'Type': media_data.get('Type', ''),
                                'Seasons': []
                            }

                            season_doc = {
                                'SeasonNumber': (int(season_number) if season_number else ""),
                                'Episodes': []
                            }

                            episode_doc = {
                                'EpisodeNumber': (int(episode_number) if episode_number else ""),
                                'Contents': [{
                                    'Size': media_info['Dimensioni Documento (bytes)'],
                                    'Name': media_info['Name'],  # Utilizza il valore estratto
                                    'Part': int(part),
                                    'Message ID': int(message.id),
                                    'File ID': media_info['File ID'],
                                    'Tipo Media': media_info['Tipo Media']
                                }]
                            }

                            season_doc['Episodes'].append(episode_doc)
                            library_document['Seasons'].append(season_doc)

                            # Inserisci il nuovo documento nella collezione "Libreria: nome Canale"
                            library_collection.insert_one(library_document)

        # Chiudi la barra di progresso
        pbar.close()

        # Stampa il numero di media importati o il messaggio se è 0
        if media_imported > 0:
            print(f"Numero di media importati: {media_imported}")
        else:
            print(f"Nessun media importato per il canale {channel_name}. Attualmente hai catalogato tutti i file di questo canale, ovvero: {library_collection.count_documents({})} contenuti.")

        # Aggiorna o inserisce il documento nel database "Canali"
        channels_collection = db["Canali"]
        channel_doc = {
            'Canale': channel_name,
            'ID Canale': channel_id,
            'Data Ultimo Import': import_datetime
        }
        channels_collection.update_one({'ID Canale': channel_id}, {'$set': channel_doc}, upsert=True)

        insert_into_telegram_upload_db(channel_name)

# Funzione per inserire dati nel DB 'telegram-upload'
def insert_into_telegram_upload_db(channel_name):
    # Accedi al database 'telegram-upload'
    upload_db = client_mongodb["telegram-upload-drive"]

    # Accedi alle collezioni 'show' e 'movie'
    show_collection = upload_db["show"]
    movie_collection = upload_db["movie"]

    # Accedi alla tua collezione 'Libreria: nome Canale'
    library_collection = db[f"Libreria: {channel_name}"]

    # Itera attraverso ogni documento nella tua collezione 'Libreria'
    for document in library_collection.find({}):
        if 'Type' in document:
            if document['Type'] == "show":
                for season in document['Seasons']:
                    season_number = int(season['SeasonNumber']) if season['SeasonNumber'] else 0
                    for episode in season['Episodes']:
                        episode_number = int(episode['EpisodeNumber']) if episode['EpisodeNumber'] else 0
                        for content in episode['Contents']:
                            # estraggo il nome del file dal documento
                            file_name1 = content['Name']
                            # Verifica se 'file_name' non contiene '(4 cifre)' seguite da '- SxxExx -'
                            if not re.search(r'\(\d{4}\) - S\d{2}E\d{2} -', file_name1):
                                # Estrai la parte del nome del file che segue "- SxxExx -"
                                remaining_text = re.split(r'- S\d{2}E\d{2} -', file_name1)[-1]

                                # Costruisci il nuovo nome del file
                                file_name = f"{document['Title']} ({document['Year']}) - S{season_number:02}E{episode_number:02} -{remaining_text}"

                                print(file_name)
                                show_data = {
                                    "Canale": int(document['Canale ID']),
                                    "Nome File": file_name,
                                    "Part": int(content['Part']),
                                    "Percorso": document['Nome Canale'],
                                    "Type": document['Type'],
                                    "Title": document['Title'],
                                    "Year": int(document['Year']),
                                    "Season": season_number,
                                    "Episode": episode_number,
                                    "File ID": content['File ID'],
                                    "Message ID": int(content['Message ID'])
                                }
                                show_collection.insert_one(show_data)
                            else:
                                show_data = {
                                    "Canale": int(document['Canale ID']),
                                    "Nome File": content['Name'],
                                    "Part": int(content['Part']),
                                    "Percorso": document['Nome Canale'],
                                    "Type": document['Type'],
                                    "Title": document['Title'],
                                    "Year": int(document['Year']),
                                    "Season": season_number,
                                    "Episode": episode_number,
                                    "File ID": content['File ID'],
                                    "Message ID": int(content['Message ID'])
                                }
                                show_collection.insert_one(show_data)

            elif document['Type'] == "movie":
                for season in document['Seasons']:
                    for episode in season['Episodes']:
                        for content in episode['Contents']:
                            movie_data = {
                                "Canale": int(document['Canale ID']),
                                "Nome File": content['Name'],
                                "Part": int(content['Part']),
                                "Percorso": document['Nome Canale'],
                                "Title": document['Title'],
                                "Year": int(document['Year']),
                                "Type": document['Type'],
                                "Season": None,
                                "Episode": None,
                                "File ID": content['File ID'],
                                "Message ID": int(content['Message ID'])
                            }
                            movie_collection.insert_one(movie_data)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Estrai la lista dei media da un canale Telegram e salvali su MongoDB.')
    parser.add_argument('channel_id', help="L'ID del canale")

    args = parser.parse_args()

    print("Estrazione e salvataggio in corso...")
    asyncio.run(save_media_to_mongodb(args.channel_id))
