# Definisci la funzione per ottenere informazioni sulla serie TV (puoi sostituire con una fonte esterna o un database)
def get_series_info(title, year, tipo):
    print(tipo)
    try:
        # Utilizza la chiave API da config.py per TVDB
        tvdb_api_token = config.TVDB_API_KEY

        # Effettua una richiesta a TVDB API per ottenere informazioni sulla serie TV
        tvdb_headers = {
            'Authorization': f'Bearer {tvdb_api_token}'
        }
        tvdb_params = {
            'q': title,
            'year': year
        }
        tvdb_response = requests.get('https://api.thetvdb.com/search/series', headers=tvdb_headers, params=tvdb_params)

        if tvdb_response.status_code == 200:
            series_data = tvdb_response.json()
            if series_data and series_data['data']:
                # Prendi la prima serie TV dalla risposta (puoi elaborare le corrispondenze multiple)
                serie_info = series_data['data'][0]
                descrizione = serie_info['overview']
                url_immagine = serie_info['banner']
                return descrizione, url_immagine
            else:
                # Se la serie TV non viene trovata su TVDB, prova con TMDb
                tmdb_api_key = config.TMDB_API_KEY  # chiave API TMDb
                tmdb_params = {
                    'api_key': tmdb_api_key,
                    'query': title,
                    'year': year
                }

                if tipo == 'show':
                    tmdb_response = requests.get('https://api.themoviedb.org/3/search/tv', params=tmdb_params)
                
                elif tipo == 'movie':
                    tmdb_response = requests.get('https://api.themoviedb.org/3/search/movie', params=tmdb_params)
                    

                if tmdb_response.status_code == 200:
                    tmdb_data = tmdb_response.json()
                    if tmdb_data.get('results'):
                        serie_info = tmdb_data['results'][0]
                        descrizione = serie_info.get('overview')
                        url_immagine = serie_info.get('backdrop_path')
                        return descrizione, url_immagine
                    else:
                        return "Serie TV non trovata", None
                else:
                    return f"Errore nell'API TMDb: {tmdb_response.status_code}", None
        else:
            # Se TVDB restituisce un errore o nessun risultato, prova automaticamente TMDb
            tmdb_api_key = config.TMDB_API_KEY  # chiave API TMDb
            tmdb_params = {
                'api_key': tmdb_api_key,
                'query': title,
                'year': year
            }

            # Effettua la richiesta GET all'API TMDb per la ricerca di serie TV
            if tipo == 'show':
                tmdb_url = 'https://api.themoviedb.org/3/search/tv'
            elif tipo == 'movie':
                tmdb_url = 'https://api.themoviedb.org/3/search/movie'
            
            tmdb_response = requests.get(tmdb_url, params=tmdb_params)

            try:
                if tmdb_response.status_code == 200:
                    tmdb_data = tmdb_response.json()
                    
                    # Stampa l'URL della richiesta e lo stato della risposta
                    print("URL della richiesta TMDb:", tmdb_response.url)
                    print("Status Code TMDb:", tmdb_response.status_code)

                    # Verifica se ci sono risultati
                    if tmdb_data.get('results'):
                        serie_info = tmdb_data['results'][0]
                        serie_id = serie_info.get('id')  # Ottieni l'ID della serie
                        print(tmdb_data.get)
                        # Ottieni la descrizione in italiano se disponibile
                        tmdb_language_params = {
                            'api_key': tmdb_api_key,
                            'language': 'it'  # Imposta la lingua a italiano
                        }
                        if tipo == 'show':
                            tmdb_description_url = f'https://api.themoviedb.org/3/tv/{serie_id}&'
                        elif tipo == 'movie':
                            #tmdb_description_url = f'https://api.themoviedb.org/3/search/movie/{serie_id}'
                            tmdb_description_url = f'https://api.themoviedb.org/3/movie/{serie_id}'

                            
                        tmdb_description_response = requests.get(tmdb_description_url, params=tmdb_language_params)
                        
                        if tmdb_description_response.status_code == 200:
                            tmdb_description_data = tmdb_description_response.json()
                            descrizione = tmdb_description_data.get('overview')

                            # Limita la descrizione a 700 caratteri (puoi cambiare il numero a seconda delle tue preferenze)
                            if descrizione and len(descrizione) > 700:
                                descrizione = descrizione[:700] + "..."

                        else:
                            descrizione = serie_info.get('overview')
                        
                            # Limita la descrizione a 700 caratteri (puoi cambiare il numero a seconda delle tue preferenze)
                            if descrizione and len(descrizione) > 700:
                                descrizione = descrizione[:700] + "..."

                        # Ottieni il poster_path
                        poster_path = serie_info.get('poster_path')
                        backdrop_path = serie_info.get('backdrop_path')
                        #backdrop_path
                        print(poster_path)
                        if poster_path:
                            base_image_url = 'https://image.tmdb.org/t/p/original'
                            url_immagine = f"{base_image_url}{poster_path}"
                            print(url_immagine)
                        elif backdrop_path:
                            base_image_url = 'https://image.tmdb.org/t/p/original'
                            url_immagine = f"{base_image_url}{backdrop_path}"
                            print(url_immagine)
                        else:
                            url_immagine = 'https://i.ibb.co/Trd84Lc/nocopertina.jpg'
                        
                        return descrizione, url_immagine
                    else:
                        return "Serie TV non trovata", None
                else:
                    return f"Errore nell'API TMDb: {tmdb_response.status_code}", None
            except requests.exceptions.RequestException as e:
                return f"Errore nella richiesta API: {str(e)}", None

    except Exception as e:
        return f"Errore sconosciuto: {str(e)}", None


#scarica l'immagine temporaneamente di copertina e invia
def send_image_to_telegram(chat_id, image_url, caption=None, reply_markup=None):    
    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()  # Solleva un'eccezione in caso di errori

        with response.raw as image:
            sent_message = bot.send_photo(chat_id, image, caption=caption, reply_markup=reply_markup)
            interazioni.save_message(chat_id, caption, is_user=False, forwarded_from=None, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=sent_message.message_id)
        return sent_message  # Restituisci il messaggio inviato
    except Exception as e:
        msg = bot.send_message(chat_id, f"Errore nell'invio dell'immagine: {str(e)}")
        interazioni.save_message(chat_id, f"Errore nell'invio dell'immagine: {str(e)}", is_user=False, forwarded_from=None, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
                    
        return None  # Restituisci None in caso di errore

# Cerca l'immagine e la descrizione per il film
series_description, series_image_url = get_series_info(series_title, series_year, content_type)