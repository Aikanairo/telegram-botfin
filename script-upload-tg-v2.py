import os
import sys
import subprocess
import hashlib
import re
import urllib.parse
import math
from pymongo import MongoClient

# Ottieni il percorso assoluto dello script
script_directory = os.path.dirname(os.path.abspath(__file__))

# Credenziali MongoDB
MONGODB_HOST = ""
MONGODB_PORT = 
MONGODB_USERNAME = ""
MONGODB_PASSWORD = ""
MONGODB_DATABASE = "telegram-upload"
MONGODB_DATAAPP = "telegram-app"

# Codifica pass utente
MONGODB_USERNAME_ENCODED = urllib.parse.quote_plus(MONGODB_USERNAME)
MONGODB_PASSWORD_ENCODED = urllib.parse.quote_plus(MONGODB_PASSWORD)

# Crea la variabile MONGODB_URI utilizzando le variabili di connessione
MONGODB_URI = f"mongodb://{MONGODB_USERNAME_ENCODED}:{MONGODB_PASSWORD_ENCODED}@{MONGODB_HOST}:{MONGODB_PORT}/?authMechanism=DEFAULT"

# Crea una connessione al server MongoDB utilizzando l'URL di connessione
client_mongodb = MongoClient(MONGODB_URI)

# Accedi al database MongoDB telegram-upload
db = client_mongodb[MONGODB_DATABASE]

# Accedi al database MongoDB telegram-app
db_app = client_mongodb[MONGODB_DATAAPP]

# funziona split by aik
def split_file(file_path, max_part_size):
    part_num = 0
    # script_directory = os.path.dirname(os.path.abspath(file_path))

    with open(file_path, 'rb') as f:
        while True:
            part_num += 1
            part_file_name = "{}.{}".format(os.path.basename(file_path), str(part_num).zfill(3))
            part_file_path = os.path.join(script_directory, part_file_name)

            with open(part_file_path, 'wb') as part_file:
                remaining_size = max_part_size
                while remaining_size > 0:
                    chunk_size = min(remaining_size, 1024 * 1024 * 100)  # Massimo 100 megabyte per parte
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    part_file.write(chunk)
                    remaining_size -= len(chunk)

                print(f"Suddivido il file {part_file_name} in parte {part_num}")

                if remaining_size <= 0:
                    continue
                else:
                    break

    return part_num  # Restituisci il numero di parti create
# Funzione per creare il comando telegram-upload per un singolo file
def create_telegram_upload_command(file_path, linkcanale, file_type, caption):
    print("\033[95mstop caricando:", file_path, "\033[0m")
    command = f'/home/aik/Scrivania/python/packages/telegram-upload/venv/bin/telegram-upload --to {linkcanale} "{file_path}" --caption "{caption}" --print-file-id'
    #print(command)  # Aggiungi questa linea per stampare il comando
    return command
# Funzione per calcolare l'hash SHA-256 di un testo
def calculate_sha256(text):
    sha256 = hashlib.sha256()
    sha256.update(text.encode('utf-8'))
    return sha256.hexdigest()
# Funzione per estrarre le informazioni dal nome del file o dal percorso
def extract_file_info(file_name, file_path, file_type):
    # Se il file_name ha un suffisso come .001, rimuovilo
    file_name = re.sub(r'\.\d{3}$', '', file_name)

    title = ""
    year = ""
    season = ""
    episode = ""
    description = ""
    file_info = ""

    if file_type == "show":
        # Estrai il titolo, l'anno, la stagione, l'episodio e altre informazioni dal nome del file
        file_info_match = re.search(r'^(.*?)\s*(?:\((\d{4})\))?(?:\s*-\s*S(\d+)E(\d+))?\s*-\s*(.*?)\s*-\s*(.*)', file_name)
        if file_info_match:
            title = file_info_match.group(1).strip()
            year = file_info_match.group(2)
            season_match = file_info_match.group(3)
            episode_match = file_info_match.group(4)
            description = file_info_match.group(5).strip()
            file_info = file_info_match.group(6).strip()

            # Se sono presenti valori di stagione ed episodio, assegna loro i valori
            if season_match and episode_match:
                season = season_match
                episode = episode_match

        # Se l'anno non è stato trovato, cerca tra parentesi nel percorso
        if not year:
            path_year_match = re.search(r'\((\d{4})\)', os.path.abspath(file_path))
            if path_year_match:
                year = path_year_match.group(1)

        # Controllo se nel titolo è presente - quindi estrae fino a "- S01E01 -"
        title_match = re.search(r'^(.*?)\s*-\s*S\d+E\d+\s*-', file_name)
        if title_match:
            extracted_title = title_match.group(1).strip()
            
            # Rimuovi l'anno dal titolo se è contenuto anche in extracted_title
            if year and year in extracted_title:
                title = extracted_title.replace(year, "").strip()
            else:
                title = extracted_title

            # Se il title finisce con spazio e parentesi tonde, rimuovi lo spazio e le parentesi
            if title.endswith(' ()'):
                title = title[:-2].strip()
        
        # Se non sono stati trovati episodi, effettua una nuova ricerca nel nome del file
        if not season or not episode or not year:
            season_episode_match = re.search(r'-\s*S(\d+)E(\d+)', file_name)
            if season_episode_match:
                if not season:
                    season = season_episode_match.group(1)
                if not episode:
                    episode = season_episode_match.group(2)

    elif file_type == "movie":
        # Estrai il titolo fino al primo match di 4 cifre (anno)
        title_match = re.search(r'^(.*?)\s*(\d{4})', file_name)
        if title_match:
            title = title_match.group(1).strip()

            # Se il title finisce con spazio e parentesi tonde, rimuovi lo spazio e le parentesi
            if title.endswith(' ('):
                title = title[:-2].strip()
        

        # Estrai l'anno (4 cifre)
        year_match = re.search(r'\d{4}', file_name)
        if year_match:
            year = year_match.group(0)

    # Estrai la descrizione dal nome del file
    description_match = re.search(r'-(.*?)\s*-', file_name)
    if description_match:
        description = description_match.group(1).strip()

    # Estrai le informazioni aggiuntive dal nome del file
    file_info_match = re.search(r'-\s*(.*?)\s*$', file_name)
    if file_info_match:
        file_info = file_info_match.group(1).strip()

    return title, year, season, episode, description, file_info
# Funzione per creare la caption per il file
def create_caption(file_path, file_type, title, year, season, episode):
    # Estrai solo il nome del file dal percorso completo
    file_name = os.path.basename(file_path)
    # Crea la caption con le informazioni del file
    caption = f"fileName: {file_name}\nTitle: {title}\nYear: {year}\nType: {file_type}"
    # Aggiungi informazioni di stagione ed episodio se disponibili
    if season and episode:
        caption += f"\nSeason: {season}\nEpisode: {episode}"
    return caption
# Funzione per estrarre il nome del canale dall'id dal db
def get_channel_name_by_id(linkcanale):
    #print(linkcanale)

    channel_document = db_app['Canali'].find_one({'ID Canale': linkcanale})
    if channel_document:
        return channel_document['Canale']
    return None
# Funzione per inserire i contenuti nel database telegram-app per gli spettacoli televisivi
def insert_show_content_to_db(linkcanale, file_path, file_name, title, year, file_type,season, episode, file_id, message_id, part):
    # Rimuovi l'estensione numerica dal nome del file
    file_name = re.sub(r'\.\d{3}$', '', file_name)
    # Aggiornamento del database telegram-upload
    if file_type == "show":
        show_document = {
            'Canale': int(linkcanale),
            'Nome File': file_name,
            'Percorso': file_path,
            'Type': file_type,
            'Title': title,
            'Year': int(year),
            'Season': int(season),
            'Episode': int(episode),
            'File ID': file_id,
            'Message ID': int(message_id),
            
        }
        db['show'].insert_one(show_document)
    elif file_type == "movie":
        movie_document = {
            'Canale': int(linkcanale),
            'Nome File': file_name,
            'Percorso': file_path,
            'Type': file_type,
            'Title': title,
            'Year': int(year),
            'File ID': file_id,
            'Message ID': int(message_id),
        }
        db['movie'].insert_one(movie_document)

    #aggiornamato db telegram-app
    nomelink = get_channel_name_by_id(linkcanale)
    if not nomelink:
        print("Non è stato possibile trovare il nome del canale nel database telegram-app.")
        return

    library_collection_name = f"Libreria: {nomelink}"
    library_collection = db_app[library_collection_name]

    existing_document = library_collection.find_one({'Title': title, 'Year': year})

    if existing_document:
        season_exists = False
        for season_data in existing_document['Seasons']:
            if season_data['SeasonNumber'] == int(season):
                episode_exists = False
                for episode_data in season_data['Episodes']:
                    if episode_data['EpisodeNumber'] == int(episode):
                        episode_data['Contents'].append({
                            'Size': os.path.getsize(file_path),
                            'Name': file_name,
                            'Message ID': int(message_id),
                            'File ID': file_id,
                            'Part': int(part)
                            # 'Tipo Media': file_type
                        })
                        episode_exists = True
                        break

                if not episode_exists:
                    season_data['Episodes'].append({
                        'EpisodeNumber': int(episode),
                        'Contents': [{
                            'Size': os.path.getsize(file_path),
                            'Name': file_name,
                            'Message ID': int(message_id),
                            'File ID': file_id,
                            'Part': int(part)
                            # 'Tipo Media': file_type
                        }]
                    })
                season_exists = True
                break

        if not season_exists:
            existing_document['Seasons'].append({
                'SeasonNumber': int(season),
                'Episodes': [{
                    'EpisodeNumber': int(episode),
                    'Contents': [{
                        'Size': os.path.getsize(file_path),
                        'Name': file_name,
                        'Message ID': int(message_id),
                        'File ID': file_id,
                        'Part': int(part)
                        # 'Tipo Media': file_type
                    }]
                }]
            })

        library_collection.update_one({'_id': existing_document['_id']}, {'$set': existing_document})
    else:
        library_document = {
            'Nome Canale': nomelink,
            'Canale ID': int(linkcanale),
            'Title': title,
            'Year': int(year),
            'Type': file_type,
            'Seasons': [{
                'SeasonNumber': int(season),
                'Episodes': [{
                    'EpisodeNumber': int(episode),
                    'Contents': [{
                        'Size': os.path.getsize(file_path),
                        'Name': file_name,
                        'Message ID': int(message_id),
                        'File ID': file_id,
                        'Part': int(part)
                        # 'Tipo Media': file_type
                    }]
                }]
            }]
        }
        library_collection.insert_one(library_document)      
# Funzione di controllo se il file è gia presente nel db, questo viene skippato
def file_exists_in_db(file_name, file_type):
    # Accedi alla collezione corretta in base al tipo di file (show o movie)
    collection = db["show"] if file_type == "show" else db["movie"]

    # Cerca il documento con il nome del file
    existing_document = collection.find_one({'Nome File': file_name})
    #print(existing_document)
    return existing_document is not None
#Conta quante parti del file esistono già nel database.
def count_existing_parts(file_name, file_type):
    """
    Conta quante parti del file esistono già nel database.
    
    Args:
    - file_name (str): Il nome del file.
    - file_type (str): Il tipo di file ("show" o "movie").
    
    Returns:
    - int: Il numero di parti esistenti nel database con quel nome del file.
    """
    
    # Accedi alla collezione corretta in base al tipo di file (show o movie)
    collection = db["show"] if file_type == "show" else db["movie"]
    
    # Conta quanti documenti esistono con quel nome del file
    count = collection.count_documents({'Nome File': file_name})
    
    return count

# Funzione principale
def main():
    if len(sys.argv) < 4:
        print("Usage: python script.py <linkcanale> <percorso> <file_type (show/movie)> --from <from_letter> --to <to_letter>")
        sys.exit(1)

    linkcanale = sys.argv[1]
    root_folder = sys.argv[2]
    file_type = sys.argv[3]

    if file_type not in ["show", "movie"]:
        print("Il tipo di file deve essere 'show' o 'movie'.")
        sys.exit(1)

    if not os.path.isdir(root_folder):
        print("Il percorso specificato non è una cartella valida.")
        sys.exit(1)

    from_letter = None
    to_letter = None
    from_special = False

    if "--from" in sys.argv:
        from_index = sys.argv.index("--from")
        if from_index + 1 < len(sys.argv):
            from_value = sys.argv[from_index + 1]
            if from_value == "special":
                from_special = True
            else:
                from_letter = from_value
        else:
            print("Parametro mancante per --from.")
            sys.exit(1)

    if "--to" in sys.argv:
        to_index = sys.argv.index("--to")
        if to_index + 1 < len(sys.argv):
            to_letter = sys.argv[to_index + 1]
        else:
            print("Parametro mancante per --to.")
            sys.exit(1)

    # Loop attraverso i file nella cartella radice
    for root, dirs, files in os.walk(root_folder):
        for file_name in files:
            if file_name.startswith('.') or file_name.endswith(('.txt', '.nfo')):
                continue  # Salta i file nascosti, i file .txt e i file .nfo

            file_path = os.path.join(root, file_name)

            if from_letter and file_name < from_letter:
                continue

            if to_letter and file_name > to_letter:
                continue

            # Estrai informazioni dal nome del file o dal percorso
            title, year, season, episode, description, file_info = extract_file_info(file_name, file_path, file_type)

            # Verifica se il file esiste nel database
            expected_parts_count = math.ceil(os.path.getsize(file_path) / (3.8 * 1024 * 1024 * 1024))
            # Conta quante parti del file esistono già nel database
            existing_parts_count = count_existing_parts(file_name, file_type)

            # Altrimenti, crea la caption per il file
            caption = create_caption(file_path, file_type, title, year, season, episode)

            # Verifica se 'file_name' non contiene '(4 cifre)' seguite da '- SxxExx -'
            if not re.search(r'\(\d{4}\) - S\d{2}E\d{2} -', file_name):
                # Estrai la parte del nome del file che segue "- SxxExx -"
                remaining_text = re.split(r'- S\d{2}E\d{2} -', file_name)[-1]

                # Costruisci il nuovo nome del file
                file_name = f"{title} ({year}) - S{season}E{episode} -{remaining_text}"
                #print(file_name )

            # Verifica se il file è più grande di 4 GB e deve essere suddiviso
            max_size_bytes = int(3.8 * 1024 * 1024 * 1024)
            file_size = os.path.getsize(file_path)

            if file_size > max_size_bytes:

                # Verifica se il file e tutte le sue parti esistono nel database
                if existing_parts_count < expected_parts_count:
                    # Se non tutte le parti esistono, esegui la suddivisione
                    num_parts = split_file(file_path, max_size_bytes)
                    print("\033[94m" + f"Il file {file_name} verrà suddiviso in {num_parts} parti" + "\033[0m")
                else:
                    print(f"\033[93mIl file {file_name} e tutte le sue {expected_parts_count} parti sono già presenti nel database telegram-upload. Verrà saltato.\033[0m")
                    continue  # Salta il file e passa al successivo

                # Se il file è più grande di max_part_size, esegui la suddivisione
                existing_parts_count = count_existing_parts(file_name, file_type)
                num_parts = math.ceil(file_size / max_size_bytes)  # Questo calcola il numero totale di parti previste
                missing_parts_count = num_parts - existing_parts_count

                #num_parts = split_file(file_path, max_size_bytes)
                print("\033[94m" + f"Il file {file_name} è troppo grande verrà suddiviso in {num_parts} parti" + "\033[0m")

                file_id = ""
                file_ids = []  # Lista per memorizzare i file_id delle parti
                message_ids = []  # Lista per memorizzare i message_id delle parti
                part_file_paths = []  # Lista per memorizzare i percorsi dei file suddivisi

                #for part_num in range(1, num_parts + 1):
                for part_num in range(existing_parts_count + 1, num_parts + 1):
                    part_file_name = f"{file_name}.{str(part_num).zfill(3)}"
                    part_file_path = os.path.join(script_directory, part_file_name)
                    part_caption = f"{caption}\nPart: {part_num}/{num_parts}"
                    part = part_num

                    # Crea il comando per l'upload della parte
                    upload_command = create_telegram_upload_command(part_file_path, linkcanale, file_type, part_caption)
                    print(part_caption)
                    
                    try:
                        # Esegui il comando di upload e acquisisci l'output
                        upload_result = subprocess.check_output(upload_command, shell=True, text=True)
                        #print(upload_result)
                        print("\033[96m" + upload_result + "\033[0m")
                        # Estrai l'ID del file dall'output
                        file_id_match = re.search(r'\(file_id (\S+)\)', upload_result)
                        if file_id_match:
                            file_id = file_id_match.group(1)
                            file_ids.append(file_id)
                            #print(f"File ID: {file_id}")  # Stampa il file_id estratto

                        # Estrai l'ID del messaggio dall'output
                        message_id_match = re.search(r'message_id (\d+)', upload_result)
                        if message_id_match:
                            message_id = message_id_match.group(1)
                            message_ids.append(message_id)
                            
                            # Inserisci i dettagli del file nel database telegram-app
                            insert_show_content_to_db(linkcanale, part_file_path, os.path.basename(part_file_path), title, year, file_type, season, episode, file_id, message_id, part)
                            #print(f"Inserito nel database: {file_id}, {message_id}")
                        else:
                            print(f"Errore durante l'upload di {os.path.basename(part_file_path)}. Impossibile ottenere file_id e message_id.")
                    except subprocess.CalledProcessError as e:
                        print(f"Errore durante l'upload della parte {os.path.basename(part_file_path)}: {e}")

                    # Aggiungi il percorso del file suddiviso alla lista
                    part_file_paths.append(part_file_path)

                # Elimina i file suddivisi dopo l'upload
                for part_file_path in part_file_paths:
                    try:
                        os.remove(part_file_path)
                        print("\033[91m" + f"File suddiviso {part_file_path} eliminato con successo." + "\033[0m")
                    except OSError as e:
                        print(f"Errore durante l'eliminazione di {part_file_path}: {e}")

            else:
        
                # controllo per verificare se il file esiste già nel database
                if file_exists_in_db(file_name, file_type):
                    print(f"\033[93mIl file {file_name} è già presenti nel database telegram-upload. Verrà saltato.\033[0m")
                    continue  # Salta il file e passa al successivo
                #print(file_size)
                print(file_name)
                print(caption)
                # Il file non deve essere suddiviso, quindi caricalo come un unico file
                upload_command = create_telegram_upload_command(file_path, linkcanale, file_type, caption)
                
                try:
                    file_id = ""
                    part = 0
                    file_ids = []  # Lista per memorizzare i file_id delle parti
                    message_ids = []  # Lista per memorizzare i message_id delle parti

                    upload_result = subprocess.check_output(upload_command, shell=True, text=True)
                    #print(upload_result)
                    print("\033[96m" + upload_result + "\033[0m")
                    # Estrai l'ID del file dall'output
                    file_id_match = re.search(r'\(file_id (\S+)\)', upload_result)
                    if file_id_match:
                        file_id = file_id_match.group(1)
                        file_ids.append(file_id)
                        #print(f"File ID: {file_id}")  # Stampa il file_id estratto

                    # Estrai l'ID del messaggio dall'output
                    message_id_match = re.search(r'message_id (\d+)', upload_result)
                    if message_id_match:
                        message_id = message_id_match.group(1)
                        message_ids.append(message_id)
                            
                    # Inserisci i dettagli del file nel database telegram-app
                    insert_show_content_to_db(linkcanale, file_path, file_name, title, year, file_type,season, episode, file_id, message_id, part)
                except subprocess.CalledProcessError as e:
                    print(f"Errore durante l'upload di {file_name}: {e}")

if __name__ == "__main__":
    main()
