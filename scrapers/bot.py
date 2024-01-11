import pymongo
import argparse
import config
import database
import requests

def get_tmdb_details(title, year, media_type):
    tmdb_api_key = config.TMDB_API_KEY

    # Imposta l'URL in base al tipo di media (serie TV o film)
    if media_type == "show":
        tmdb_url = 'https://api.themoviedb.org/3/search/tv'
    else:
        tmdb_url = 'https://api.themoviedb.org/3/search/movie'

    params = {
        'api_key': tmdb_api_key,
        'query': title,
        'year': year
    }

    try:
        response = requests.get(tmdb_url, params=params)
        #print(response)
        
        response.raise_for_status()

        data = response.json()
        #print(data)
        if data.get('results'):
            media_details = data['results'][0]
            media_id = media_details.get('id')
            
            # Ottenere la descrizione in italiano se disponibile
            tmdb_language_params = {
                'api_key': tmdb_api_key,
                'language': 'it'  # Imposta la lingua a italiano
            }

            if media_type == 'show':
                media_info_url = f'https://api.themoviedb.org/3/tv/{media_id}'
            elif media_type == 'movie':
                media_info_url = f'https://api.themoviedb.org/3/movie/{media_id}'
            
            # Effettua una seconda richiesta per ottenere i dettagli completi in italiano
            # Effettua una seconda richiesta per ottenere i dettagli completi in italiano
            media_info_response = requests.get(media_info_url, params=tmdb_language_params)

            if media_info_response.status_code == 200:
                media_info = media_info_response.json()
                
                # Ora accedi direttamente al campo 'seasons'
                if media_type == 'show':  # Assicurati di fare questo solo per le serie TV
                    tmdb_seasons = media_info.get("seasons", [])
                    #print(tmdb_seasons)
                    # Aggiungi le stagioni ai dettagli del media
                    media_details["seasons"] = tmdb_seasons
            
            cast = []
            if media_info.get("credits") and media_info["credits"].get("cast"):
                cast_data = media_info["credits"]["cast"]
                for actor_data in cast_data:
                    actor = {
                        "nome": actor_data.get("name"),
                        "immagine": f"https://image.tmdb.org/t/p/w185/{actor_data.get('profile_path')}",
                        "personaggio": actor_data.get("character")
                    }
                    cast.append(actor)
            
            # Aggiungi i dettagli estratti senza alterare la struttura esistente
            media_details["genere"] = media_info.get("genres")
            media_details["descrizione"] = media_info.get("overview")
            media_details["valutazione"] = media_info.get("vote_average")
            media_details["attori"] = cast
            media_details["copertina"] = media_details.get("poster_path")
            media_details["banner"] = media_details.get("backdrop_path")

            return media_details
        else:
            print("Nessun risultato trovato su TMDB.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Errore nella richiesta a TMDB: {e}")
        return None
    except requests.exceptions.JSONDecodeError as e:
        print(f"Errore nel parsing della risposta JSON da TMDB: {e}")
        return None

# Funzione principale per aggiornare i documenti nel database
def update_database_with_media_details(collection_name, media_type):
    db = database.Database().get_db()
    collection = db[collection_name]  # Utilizza il nome della collezione specificato

    media_list = collection.find({})

    for media in media_list:
        title = media["Title"]
        year = media.get("Year")

        media_details = get_tmdb_details(title, year, media_type)

        if media_details:
            update_media_document(media, media_details)
            #print(f"Aggiornamento completato per il documento {media['_id']}")

def update_media_document(media_doc, media_details):
    db = database.Database().get_db()
    collection = db[args.collection]  # Utilizza il nome della collezione specificato

    update_data = {
        "$set": {
            "genere": media_details.get("genere"),
            "descrizione": media_details.get("descrizione"),
            "valutazione": media_details.get("valutazione"),
            "attori": media_details.get("attori"),
            "copertina": media_details.get("copertina"),
            "banner": media_details.get("banner")
        }
    }

    # Verifica se la chiave "Seasons" è presente nel documento media
    seasons = media_doc.setdefault("Seasons", [])

    # Estrai l'elenco delle stagioni dalla risposta JSON di TMDB
    tmdb_seasons = media_details.get("seasons", [])
    #print(tmdb_seasons)

    # Creare un dizionario stagione per facilitare l'accesso ai dati della stagione
    tmdb_season_dict = {season["season_number"]: season for season in tmdb_seasons}
    #print(tmdb_season_dict)

    # Cicla attraverso gli oggetti Season da media_doc
    # Stampare l'array "seasons" dal JSON di TMDB per debugging
    #print("Stagioni in TMDB JSON:")
    #print(media_details.get("seasons"))

    # Cicla attraverso gli oggetti Season da media_doc
    for index, season in enumerate(seasons):
        season_number = season.get("SeasonNumber")
        tmdb_season_data = next((season_info for season_info in media_details.get("seasons", []) if season_info.get("season_number") == season_number), None)
        
        if tmdb_season_data:
            season_updates = {
                f"Seasons.{index}.air_date": tmdb_season_data.get("air_date"),
                f"Seasons.{index}.episode_count": tmdb_season_data.get("episode_count"),
                f"Seasons.{index}.id": tmdb_season_data.get("id"),
                f"Seasons.{index}.overview": tmdb_season_data.get("overview"),
                f"Seasons.{index}.poster_path": tmdb_season_data.get("poster_path"),
                f"Seasons.{index}.vote_average": tmdb_season_data.get("vote_average"),
            }
            collection.update_one({"_id": media_doc["_id"]}, {"$set": season_updates})


    # Stampa la query di aggiornamento
    query_result = collection.find_one_and_update({"_id": media_doc["_id"]}, update_data, return_document=pymongo.ReturnDocument.AFTER)
    #print(f"Query di aggiornamento: {query_result}")
   # print(f"Documento {media_doc['_id']} aggiornato con successo nel database.")

if __name__ == "__main__":
    # Creazione di un parser per gli argomenti da linea di comando
    parser = argparse.ArgumentParser(description="Aggiorna i documenti nel database con dettagli di film o serie TV")
    parser.add_argument("collection", help="Nome della collezione nel database MongoDB")
    parser.add_argument("media_type", choices=["show", "movie"], help="Tipo di media da cercare: 'show' per serie TV, 'movie' per film")

    args = parser.parse_args()

    update_database_with_media_details(args.collection, args.media_type)
