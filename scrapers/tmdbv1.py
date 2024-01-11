from datetime import datetime
import os
import urllib.parse
import requests
import config
import pymongo
import argparse
import database

# funzione per pulire il titolo da spazi bianchi
def clean_title(title):
    return title.strip().lower()
# funzione per creare le cartelle
def create_directories(destination_folder):
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)
# funzione per creare una cartella specifica per il media

# gestisci il titolo per l'argomento --singolo
def get_specific_media_details(collection, title, year):
    # Converte l'anno in un intero
    year_int = int(year)
    # Usa una regex per confrontare il titolo ignorando le differenze di maiuscole/minuscole
    query = {"Title": {"$regex": f"^{title}$", "$options": "i"}, "Year": year_int}
    #print("Query completa:", query)  # Stampa la query completa
    return collection.find_one(query)
# funzione per il download dell'immagine
def download_image(image_url, destination_folder, file_name):
    create_directories(destination_folder)

    response = requests.get(image_url)
    if response.status_code == 200:
        image_path = os.path.join(destination_folder, file_name)

        with open(image_path, "wb") as f:
            f.write(response.content)

        return image_path
    else:
        print(f"Errore nel salvataggio dell'immagine da {image_url}")
        return None
# funzione per il doveload elle imagini degli attori
def save_cast_images(cast, destination_folder):
    for member in cast:
        image_url = member.get("Immagine")
        if image_url:
            file_name = f"{member.get('Nome')}.jpg"
            download_image(image_url, destination_folder, file_name)
# funzione per salvare le immagini
def save_image_and_update_path(image_url, destination_folder, file_name):
    if image_url:
        #print(f"Scaricamento di {image_url}...")
        saved_path = download_image(image_url, destination_folder, file_name)
        if saved_path:
            # Estrai l'estensione del file dall'URL
            file_extension = os.path.splitext(urllib.parse.urlparse(image_url).path)[-1]
            # Aggiungi l'estensione del file al nome del file
            file_name_with_extension = f"{file_name}{file_extension}"
            # Rinomina il file scaricato con il nuovo nome
            new_saved_path = os.path.join(destination_folder, file_name_with_extension)
            os.rename(saved_path, new_saved_path)
            #print(f"Immagine scaricata con successo e rinominata in: {new_saved_path}")
            return new_saved_path
        else:
            print(f"Errore durante il download dell'immagine da: {image_url}")
    else:
        print("URL dell'immagine non fornito.")
    return None

def get_tmdb_cast_details(media_id, media_type, tmdb_api_key):
    credits_url = f"https://api.themoviedb.org/3/{'tv' if media_type == 'show' else 'movie'}/{media_id}/credits"
    params = {'api_key': tmdb_api_key, 'language': 'it'}
    response = requests.get(credits_url, params=params)
    response.raise_for_status()
    return response.json()

def get_tmdb_episode_details(show_id, season_number, tmdb_api_key):
    episode_url = f"https://api.themoviedb.org/3/tv/{show_id}/season/{season_number}"
    params = {'api_key': tmdb_api_key, 'language': 'it'}
    response = requests.get(episode_url, params=params)
    response.raise_for_status()
    data = response.json()
    return data.get("episodes", [])

def get_tmdb_details(title, year, media_type, error_log_collection, skip_multiple_results=False):
    tmdb_api_key = config.TMDB_API_KEY
    tmdb_url = f"https://api.themoviedb.org/3/search/{'tv' if media_type == 'show' else 'movie'}"
    params = {'api_key': tmdb_api_key, 'query': title, 'year': year, 'language': 'it'}
    response = requests.get(tmdb_url, params=params)
    response.raise_for_status()
    data = response.json()

    if data.get('results'):
        media_details = None
        if len(data['results']) > 1:
            if skip_multiple_results:
                print(f"Saltato: {title} ({year}) a causa di risultati multipli.")
                # log_error(title, year, error_log_collection)  # Assicurati che questa funzione sia definita correttamente.
                return None
            else:
                print(f"\033[94mTrovati {len(data['results'])} risultati per '{title}' dell'anno '{year}'.\033[0m")
                for i, result in enumerate(data['results']):
                    print(f"{i+1}: {result['title'] if media_type == 'movie' else result['name']} "
                          f"({result['release_date'] if media_type == 'movie' else result['first_air_date']}) - "
                          f"https://www.themoviedb.org/{'tv' if media_type == 'show' else 'movie'}/{result['id']}")
                print("Premi 'x' per saltare questo titolo.")
                user_input = input("\033[95mSeleziona il numero del risultato corretto o premi 'x' per saltare: \033[0m").strip().lower()
                if user_input == 'x':
                    log_error(title, year, error_log_collection)
                    return None
                else:
                    try:
                        selection = int(user_input) - 1
                        media_details = data['results'][selection]
                    except ValueError:
                        print("\033[91mSelezione non valida. Si prega di inserire un numero.\033[0m")
                        log_error(title, year, error_log_collection)
                        return None
        else:
            media_details = data['results'][0]

        media_id = media_details.get('id')
        tmdb_language_params = {'api_key': tmdb_api_key, 'language': 'it'}
        media_info_url = f"https://api.themoviedb.org/3/{'tv' if media_type == 'show' else 'movie'}/{media_id}"
        media_info_response = requests.get(media_info_url, params=tmdb_language_params)
        media_info_response.raise_for_status()
        media_info = media_info_response.json()

        if media_type == 'show':
            tmdb_seasons = media_info.get("seasons", [])
            media_details["seasons"] = tmdb_seasons

            # Aggiungi dettagli episodi se il media_type è 'show'
            for season in tmdb_seasons:
                season_number = season.get("season_number")
                episodes = get_tmdb_episode_details(media_id, season_number, tmdb_api_key)
                season["episodes"] = episodes

        cast_details = get_tmdb_cast_details(media_id, media_type, tmdb_api_key)
        formatted_cast = []
        if cast_details.get('cast'):
            for member in cast_details['cast']:
                formatted_cast.append({
                    #"ID": member.get("id"),
                    "Personaggio": member.get("character"),
                    "Alias": member.get("name"),
                    "Nome": member.get("original_name"),
                    "Sesso": "donna" if member.get("gender") == 1 else "uomo" if member.get("gender") == 2 else "non specificato",
                    "Genere": member.get("known_for_department"),
                    "Popolarità": member.get("popularity"),
                    "Immagine": f"https://image.tmdb.org/t/p/w500{member.get('profile_path')}" if member.get('profile_path') else None
                })
        media_details["attori"] = formatted_cast
        media_details["genere"] = media_info.get("genres")
        media_details["descrizione"] = media_info.get("overview")
        media_details["valutazione"] = media_info.get("vote_average")
        media_details["copertina"] = media_details.get("poster_path")
        media_details["banner"] = media_details.get("backdrop_path")

        return media_details
    else:
        # print("\033[91mNessun risultato trovato su TMDB, ho inserito .\033[0m")
        print(f"\033[91mNessun risultato trovato, ho inserito: {title}({year}) in Log Scraper Errors\033[0m")
        log_error(title, year, error_log_collection)
        return None

def log_error(title, year, error_log_collection):
    error_log = {
        'Titolo': title,
        'Anno': year,
        'Scraper': 'TMDB',
        'Data': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    error_log_collection.update_one(
        {'Titolo': title, 'Anno': year},
        {'$set': error_log},
        upsert=True
    )

def update_database_with_media_details(collection_name, media_type, fast_mode=False, skip_multiple_results=False, specific_media=None):
    db = database.Database().get_db()
    collection = db[collection_name]
    error_log_collection = db['Log Scraper Errors']

    # Aggiunto il controllo per l'opzione --singolo
    if specific_media:
        title, year = specific_media.split(" | ")
        specific_result = get_specific_media_details(collection, title, year)

        if specific_result:
            print(f"\033[93mRisultato specifico trovato: {title} ({year})\033[0m")
            # Crea cartella se l'argomanto --grafica è impostato
            #if args.grafica:
                #media_folder = create_media_folder(collection_name, title, year)

            media_details = get_tmdb_details(title, year, media_type, error_log_collection, skip_multiple_results)

            if media_details:
                print(f"\033[92mAggiornando il database per: {title}\033[0m")
                update_media_document(specific_result, media_details, collection, title, year)
                
                # Salva le immagini degli attori
                # Salva immagine attori se l'argomanto --grafica è impostato
                if args.grafica:
                    cast = media_details.get("attori", [])
                    save_cast_images(cast, os.path.join("grafica", "attori"))

            else:
                print(f"\033[91mNessun dettaglio trovato per: {title}\033[0m")
                # Log error if no details are found
                log_error(title, year, error_log_collection)
        else:
            print(f"\033[91mNessun risultato trovato con titolo: {title} e anno: {year}\033[0m")
    else:
        # Se --singolo non è fornito, esegui la ricerca e l'aggiornamento normale
        media_list = list(collection.find({}))
        total_media = len(media_list)
        for index, media in enumerate(media_list):
            title = media["Title"]
            year = media.get("Year")
            print(f"\033[93mConteggio: {index + 1} di {total_media} - \033[92mElaborazione di: {title}, Anno: {year}\033[0m\033[93m\033[0m")
            # crea cartell  se l'argomanto --grafica è impostato
            #if args.grafica:
                #media_folder = create_media_folder(collection_name, title, year)
            if fast_mode and media.get("IDTmdb"):
                print(f"\033[94mGià Scrapato: {title} (modalità veloce attiva) verra skippato: \033[0m")
                continue
            media_details = get_tmdb_details(title, year, media_type, error_log_collection, skip_multiple_results)
            if media_details:
                print(f"\033[92mAggiornando il database per: {title}\033[0m")
                update_media_document(media, media_details, collection, title, year)
                
                # Salva immagine attori se l'argomanto --grafica è impostato
                if args.grafica:
                    cast = media_details.get("attori", [])
                    save_cast_images(cast, os.path.join("grafica", "attori"))

            else:
                print(f"\033[91mNessun dettaglio trovato per: {title}\033[0m")
                # Log error if no details are found
                log_error(title, year, error_log_collection)

def update_media_document(media_doc, media_details, collection, title, year):
    #print(collection)
    image_base_url = "https://image.tmdb.org/t/p/"
    desired_size = "w780"

    poster_path = media_details.get("copertina")
    full_poster_path = f"{image_base_url}{desired_size}{poster_path}" if poster_path else None
    backdrop_path = media_details.get("banner")
    full_backdrop_path = f"{image_base_url}original{backdrop_path}" if backdrop_path else None

    update_data = {
        "$set": {
            "Genere": [genre.get("name") for genre in media_details.get("genere", [])],
            "Descrizione": media_details.get("descrizione"),
            "Valutazione": media_details.get("valutazione"),
            "Voto": media_details.get("vote_average"),
            "VotiTotali": media_details.get("vote_count"),
            "Popolarità": media_details.get("popularity"),
            "IDTmdb": media_details.get("id"),
            "Cast": media_details.get("attori"),
            "Copertina": full_poster_path,
            "Sfondo": full_backdrop_path,
        }
    }
    # scarica l'immagine se l'argomanto --grafica è impostato
    if args.grafica:
        save_image_and_update_path(full_poster_path, os.path.join("grafica", f"{collection.name}", f"{title} ({year})"), f"copertina")
        save_image_and_update_path(full_backdrop_path, os.path.join("grafica", f"{collection.name}", f"{title} ({year})"), f"sfondo")

    for index, season in enumerate(media_doc.get("Seasons", [])):
        season_number = season.get("SeasonNumber")
        tmdb_season_data = next((s for s in media_details.get("seasons", []) if s.get("season_number") == season_number), None)
        if tmdb_season_data:
            season_update = {
                f"Seasons.{index}.Data": tmdb_season_data.get("air_date"),
                f"Seasons.{index}.Episodi": tmdb_season_data.get("episode_count"),
                f"Seasons.{index}.Overview": tmdb_season_data.get("overview"),
                f"Seasons.{index}.SeasonPoster": f"{image_base_url}{desired_size}{tmdb_season_data.get('poster_path')}" if tmdb_season_data.get('poster_path') else None,
                f"Seasons.{index}.Voto": tmdb_season_data.get("vote_average"),
            }

            # scarica l'immagine se l'argomanto --grafica è impostato
            if args.grafica:
                immaginestagione = f"{image_base_url}{desired_size}{tmdb_season_data.get('poster_path')}" if tmdb_season_data.get('poster_path') else None
                save_image_and_update_path(immaginestagione, os.path.join("grafica", f"{collection.name}", f"{title} ({year})"), f"statione || {season_number} ")

            updated_episodes = []  # Inizializza la lista degli episodi aggiornati

            # Itera attraverso gli episodi esistenti nella stagione
            for episode_index, episode in enumerate(season.get("Episodes", [])):
                episode_number = episode.get("EpisodeNumber")
                #print(episode_number)

                # Trova i dati dell'episodio corrispondente nelle informazioni ottenute da TMDB 
                tmdb_episode_data = next((e for e in tmdb_season_data.get("episodes", []) if e.get("episode_number") == episode_number), None)
                #print(tmdb_episode_data)

                # Se l'episodio esiste in TMDB, aggiorna le informazioni
                if tmdb_episode_data:
                    # Crea un dizionario con le informazioni aggiornate dell'episodio
                    episode_update = {
                        f"TitoloEpisodio": tmdb_episode_data.get("name"),
                        f"Descrizione": tmdb_episode_data.get("overview"),
                        f"Thumb": f"https://image.tmdb.org/t/p/w780{tmdb_episode_data.get('still_path')}" if tmdb_episode_data.get('still_path') else None,
                        f"VoteAverage": tmdb_episode_data.get("vote_average"),
                        f"VoteCount": tmdb_episode_data.get("vote_count"),
                        f"Data": tmdb_episode_data.get("air_date"),
                    }
                    # scarica l'immagine se l'argomanto --grafica è impostato
                    if args.grafica:
                        immagine_thumb = f"https://image.tmdb.org/t/p/w780{tmdb_episode_data.get('still_path')}" if tmdb_episode_data.get('still_path') else None
                        save_image_and_update_path(immagine_thumb, os.path.join("grafica", f"{collection.name}", f"{title} ({year})", "thumb"), f"S{season_number}E{episode_number}")

                    # Aggiungi il dizionario degli episodi aggiornati alla lista
                    updated_episodes.append({**episode, **episode_update})

            # Aggiorna la lista degli episodi nella stagione con quelli aggiornati
            season_update[f"Seasons.{index}.Episodes"] = updated_episodes
            # Aggiorna solo la parte specifica della stagione nel documento
            update_data["$set"].update(season_update)

    # Aggiorna l'intero documento nel database
    collection.update_one({"_id": media_doc["_id"]}, update_data)


    # Aggiorna l'intero documento nel database
    collection.update_one({"_id": media_doc["_id"]}, update_data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aggiorna i documenti nel database MongoDB con dettagli di film o serie TV")
    parser.add_argument("collection", help="Nome della collezione nel database MongoDB")
    parser.add_argument("media_type", choices=["show", "movie"], help="Tipo di media da cercare: 'show' per serie TV, 'movie' per film")
    parser.add_argument("--fast", action="store_true", help="Salta i record con IDTmdb già presente")
    parser.add_argument("--skip", action="store_true", help="Salta i risultati con più corrispondenze")
    parser.add_argument("--singolo", help="Ricerca un risultato specifico con il formato Titolo | Anno")
    parser.add_argument("--grafica", action="store_true", help="Esegui funzioni relative alla grafica")


    args = parser.parse_args()
    update_database_with_media_details(args.collection, args.media_type, args.fast, args.skip, args.singolo)