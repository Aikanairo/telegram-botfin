import telebot
import config
import os
import urllib.parse
import time
import requests
import logging
import verifica_permessi
import interazioni
import modulo_infousers
from database import Database
from bson import ObjectId
from telebot import types
from fuzzywuzzy import fuzz
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


#sistema di log
#logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

ora_attuale = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def setup_canali_module(bot):
    # Ottieni l'istanza del database
    database = Database()
    db = database.get_db()

    # Dizionario per memorizzare lo stato di visualizzazione
    viewing_state = {}

    # Inizializza una pila vuota per ogni utente
    user_states = {}

    # Dizionario per memorizzare le informazioni sul contenuto selezionato
    selected_content = {}

    #tengo in memoria i messaggi inoltrari per le funzioni torna indietro
    forwarded_messages = {}
    message_ids = {}
    message_ids_movie = {}
    
    # crea i pulsanti delle librerie
    def create_library_keyboard(chat_id, channel_name, user_id, user_name, offset=0):
        try:
            libreria_document = db[f"Libreria: {channel_name}"].find_one()

            if libreria_document:
                # Estrai solo 10 documenti dalla libreria in base all'offset
                documents = db[f"Libreria: {channel_name}"].find().sort('Title', 1).skip(offset).limit(10)

                # Calcola il numero della pagina corrente e il totale delle pagine
                totale_documenti = db[f"Libreria: {channel_name}"].count_documents({})
                pagina_corrente = (offset // 10) + 1
                totale_pagine = (totale_documenti + 9) // 10

                # Creare tastiere inline per le serie TV
                keyboard = telebot.types.InlineKeyboardMarkup()

                # Aggiungi pulsanti per tutti i titoli
                for doc in documents:
                    content_id = str(doc['_id'])  # Estrai l'ID del documento come content_id
                    button_text = f"{doc['Title']} ({doc['Year']})"
                    callback_data = f"contenuto_id:{content_id}:{channel_name}"
                    button = telebot.types.InlineKeyboardButton(button_text, callback_data=callback_data)
                    keyboard.add(button)

                # Aggiungi i pulsanti "Avanti" e "Indietro" se necessario
                buttons = []

                # Aggiungi il pulsante "Cerca" alla tastiera
                cerca_button = telebot.types.InlineKeyboardButton("🔍 Cerca", callback_data=f"cerca:{channel_name}")
                keyboard.row(cerca_button, *buttons)


                if offset > 0:
                    callback_data = f"load_more:{offset - 10}:{channel_name}"
                    prev_button = telebot.types.InlineKeyboardButton("⬅️ Indietro", callback_data=callback_data)
                    buttons.append(prev_button)

                # Verifica se ci sono più risultati disponibili
                more_results_available = totale_documenti > offset + 10
                if more_results_available:
                    callback_data = f"load_more:{offset + 10}:{channel_name}"
                    next_button = telebot.types.InlineKeyboardButton("Avanti ➡️", callback_data=callback_data)
                    buttons.append(next_button)

                if buttons:
                    keyboard.row(*buttons)

                # Cancella l'ultimo messaggio inviato solo se esiste e se è presente nella chat
                if 'last_message_id' in viewing_state.get(chat_id, {}):
                    last_message_id = viewing_state[chat_id]['last_message_id']
                    try:
                        bot.delete_message(chat_id, last_message_id)
                        #print(f"Eliminato il messaggio con message_id {last_message_id}")
                    except telebot.apihelper.ApiException as e:
                        if "message to delete not found" in str(e):
                            # Il messaggio non è stato trovato, non fare nulla
                            pass
                        else:
                            print(f"Il messaggio è gia stato cancellato{last_message_id}: {e}")

                #bottone tona alle librerie
                back_button = telebot.types.InlineKeyboardButton("🔚Torna alla lista dei Canali", callback_data="canali")
                keyboard.row(back_button)
                msg = bot.send_message(chat_id, f"Seleziona un contenuto: Pagina {pagina_corrente}/{totale_pagine}", reply_markup=keyboard)
                interazioni.save_message(chat_id, f"Libreria: {channel_name}", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
                print(f"{ora_attuale}: L'utente \"{user_name}({user_id})\" ha selezionato \"{channel_name}\"")
                viewing_state[chat_id]['last_message_id'] = msg.message_id

            else:
                msg = bot.send_message(chat_id, f"Spiacenti, non ho trovato informazioni per '{channel_name}'.")
                interazioni.save_message(chat_id, f"Spiacenti, non ho trovato informazioni per '{channel_name}'.", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)

        except Exception as e:
            msg = bot.send_message(chat_id, f"Errore: {str(e)} Linea: 103")
            interazioni.save_message(chat_id, f"Errore: {str(e)} Linea: 103", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
    
    # Gestisci la ricerca quando il pulsante "Cerca" viene premuto
    @bot.callback_query_handler(func=lambda call: call.data.startswith('cerca:'))
    def handle_search(call):
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        user_name = call.from_user.username

        try:
            # Estrai il channel_name dal callback_data
            channel_name = call.data[len('cerca:'):]

            msg = bot.send_message(chat_id, "Inserisci il nome del contenuto che desideri cercare:")
            interazioni.save_message(chat_id, "Inserisci il nome del contenuto che desideri cercare:", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
            print(f"{ora_attuale}: L'utente \"{user_name}({user_id})\" ha selezionato il tasto cerca")
            bot.register_next_step_handler(call.message, process_search, channel_name)
            #viewing_state[chat_id]['last_message_id'] = msg.message_id

        except Exception as e:
            msg = bot.send_message(chat_id, f"Errore: {str(e)}")
            interazioni.save_message(chat_id, f"Errore: {str(e)}", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)

    # Gestisci la ricerca effettiva e visualizza i risultati
    def process_search(message, channel_name):
        chat_id = message.chat.id
        user_id = message.from_user.id
        user_name = message.from_user.username

        try:
            search_query = message.text

            # Esegui la ricerca fuzzy e ottieni i risultati migliori
            documents = db[f"Libreria: {channel_name}"].find()
            results = []
            for doc in documents:
                title = doc.get('Title', '')
                ratio = fuzz.ratio(search_query.lower(), title.lower())
                if ratio > 60:  # Soglia per considerare un risultato valido (puoi modificare questo valore)
                    results.append((title, doc['_id']))

            # Limita i risultati a un massimo di 15
            if len(results) > 15:
                results = results[:15]

            # Costruisci la tastiera inline con i risultati
            keyboard = InlineKeyboardMarkup()
            for title, content_id in results:
                button_text = f"{title} ({doc['Year']})"
                callback_data = f"contenuto_id:{content_id}:{channel_name}"
                button = InlineKeyboardButton(button_text, callback_data=callback_data)
                keyboard.add(button)

            # Aggiungi i pulsanti "Effettua nuova ricerca" e "Chiudi"
            nuova_ricerca_button = InlineKeyboardButton("🔍 Effettua nuova ricerca", callback_data=f"cerca:{channel_name}")
            chiudi_button = InlineKeyboardButton("✖️ Chiudi", callback_data="chiudi")
            keyboard.row(nuova_ricerca_button, chiudi_button)

            msg = bot.send_message(chat_id, "Ecco i risultati della ricerca:", reply_markup=keyboard)
            interazioni.save_message(chat_id, f"Risultati della ricerca: {search_query}", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
            print(f"{ora_attuale}: L'utente \"{user_name}({user_id})\" ha ricercato \"{search_query}\"")
            #viewing_state[chat_id]['last_message_id'] = msg.message_id
        except Exception as e:
            msg = bot.send_message(chat_id, f"Errore durante la ricerca: {str(e)}")
            interazioni.save_message(chat_id, f"Errore durante la ricerca: {str(e)}", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)

    # Funzione per creare la tastiera inline per le stagioni di una serie TV
    def create_seasons_keyboard(chat_id, channel_name, content_id, series_title, series_year, user_id, user_name):
        try:
            libreria_document = db[f"Libreria: {channel_name}"].find_one({'_id': content_id})
            if libreria_document is not None:
                content_type = libreria_document['Type']  # Aggiunto per verificare il tipo di contenuto

                # Verifica se il contenuto è di tipo "movie"
                if content_type == "movie":
                    permesso = verifica_permessi.estrai_permessi(user_id)
                    #print(permesso)
                    if permesso < 1:  # 2 è il permesso per "Utente Premium"
                        msg = bot.send_message(chat_id, "Accesso negato. Devi registrarti per accedere al contenuto /registrazione")
                        # Salva il messaggio nel database o esegui altre operazioni di logging qui
                        interazioni.save_message(chat_id, "Accesso negato. Devi registrarti per accedere al contenuto", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
                        return  # Interrompe l'esecuzione della funzione
                    id_canale = libreria_document['Canale ID']
                    # Se è un film, inoltra direttamente il contenuto
                    contents = libreria_document.get('Seasons', [{}])[0].get('Episodes', [{}])[0].get('Contents', [])
                    if contents:        
                        # Cerca l'immagine e la descrizione per il film
                        try:
                            file_path = f'/home/aik/Scrivania/script/app-telegram-full/scrapers/grafica/Libreria: {channel_name}/{series_title} ({series_year})/copertina.jpg'
                            print(f"{ora_attuale}: L'utente \"{user_name}({user_id})\" ha selezionato da\"{channel_name}\" il film: \"{series_title} ({series_year})\" ")
                            
                            if os.path.exists(file_path):

                                # estrazione dei dati
                                descrizione_breve = libreria_document['Descrizione'][:850]
                                IDTmdb =  libreria_document['IDTmdb']
                                Popolarità =  libreria_document['Popolarità']
                                Valutazione =  libreria_document['Valutazione']
                                VotiTotali =  libreria_document['VotiTotali']
                                Voto =  libreria_document['Voto']

                                with open(file_path, 'rb') as image:
                                    caption_text = (
                                    f"🖥 *{series_title} ({series_year})*\n\n"
                                    f"{descrizione_breve}\n\n"
                                    f"⭐️*Valutazione*: {Valutazione}\n"
                                    f"🗳*Voti Totali*: {VotiTotali}\n"
                                    f"🔗[Link TMDB](https://www.themoviedb.org/tv/{IDTmdb}?language=it-IT)"
                                    )

                                    msg = bot.send_photo(chat_id, image, caption=caption_text, parse_mode='Markdown')
                            else:
                                with open('/home/aik/Scrivania/script/app-telegram-full/img/movie.png', 'rb') as image:
                                    caption_text = f"Immagine non disponibile per '{series_title} ({series_year})"
                                    msg = bot.send_photo(chat_id, image, caption=caption_text)

                            interazioni.save_message(chat_id, caption_text, is_user=False, forwarded_from=None, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
                        except Exception as e:
                            msg = bot.send_message(chat_id, f"Errore nell'invio dell'immagine: {str(e)}")
                            interazioni.save_message(chat_id, f"Errore nell'invio dell'immagine: {str(e)}", is_user=False, forwarded_from=None, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)

                        for content_item in contents:
                            message_id = content_item.get('Message ID')
                            
                            if message_id:
                                forwarded_msg = bot.copy_message(chat_id, id_canale, message_id)

                                interazioni.save_message(chat_id, "Messaggio inoltrato", is_user=False, forwarded_from=None, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=forwarded_msg.message_id)

                        # bottone che gestisce il torna indietro
                        keyboard = telebot.types.InlineKeyboardMarkup()
                        back_button = telebot.types.InlineKeyboardButton("🔚Torna indietro", callback_data=f"back:{channel_name}")
                        keyboard.add(back_button)
                        msg = bot.send_message(chat_id, "Seleziona un'opzione:", reply_markup=keyboard)
                        interazioni.save_message(chat_id, f"Libreria: {channel_name}", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)

                    else:
                        msg = bot.send_message(chat_id, f"Spiacenti, non ho trovato contenuti per '{series_title} ({series_year})'.")
                        interazioni.save_message(chat_id, f"Spiacenti, non ho trovato contenuti per '{series_title} ({series_year})'.", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
                else:
                    seasons = libreria_document.get('Seasons', [])

                    # Memorizza le informazioni sul contenuto selezionato
                    selected_content[chat_id] = {
                        'channel_name': channel_name,
                        'content_id': content_id,
                        'series_title': series_title,
                        'series_year': series_year,     
                    }

                    if seasons:
                        # Crea tastiere inline per le stagioni della serie TV
                        keyboard = telebot.types.InlineKeyboardMarkup()
                        current_row = []
                        for season in seasons:
                            season_number = season['SeasonNumber']
                            button_text = f"S{int(season_number)}"
                            callback_data = f"season:{channel_name}:{content_id}:{season_number}"
                            button = telebot.types.InlineKeyboardButton(button_text, callback_data=callback_data)
                            current_row.append(button)
                            
                            if len(current_row) == 5:
                                keyboard.row(*current_row)
                                current_row = []
                        
                        if current_row:
                            keyboard.row(*current_row)
                        
                        # bottone torna indietro
                        #back_button = telebot.types.InlineKeyboardButton("🔚Torna indietro", callback_data=f"back:{channel_name}")
                        #keyboard.row(back_button)

                        # pulsante chiudi
                        back_button = telebot.types.InlineKeyboardButton("✖️ Chiudi", callback_data=f"chiudi")
                        keyboard.row(back_button)
                        #
                        try:
                            file_path = f'/home/aik/Scrivania/script/app-telegram-full/scrapers/grafica/Libreria: {channel_name}/{series_title} ({series_year})/copertina.jpg'
                            print(f"{ora_attuale}: L'utente \"{user_name}({user_id})\" ha selezionato da\"{channel_name}\" la serie \"{series_title} ({series_year})\" ")
                            if os.path.exists(file_path):

                                # estrazione dei dati
                                descrizione_breve = libreria_document['Descrizione'][:850]
                                IDTmdb =  libreria_document['IDTmdb']
                                Popolarità =  libreria_document['Popolarità']
                                Valutazione =  libreria_document['Valutazione']
                                VotiTotali =  libreria_document['VotiTotali']
                                Voto =  libreria_document['Voto']

                                with open(file_path, 'rb') as image:
                                    caption_text = (
                                    f"🖥 *{series_title} ({series_year})*\n\n"
                                    f"{descrizione_breve}\n\n"
                                    f"⭐️*Valutazione*: {Valutazione}\n"
                                    f"🗳*Voti Totali*: {VotiTotali}\n"
                                    f"🔗[Link TMDB](https://www.themoviedb.org/tv/{IDTmdb}?language=it-IT)"
                                    )

                                    msg = bot.send_photo(chat_id, image, caption=caption_text, parse_mode='Markdown', reply_markup=keyboard)

                            else:
                                with open('/home/aik/Scrivania/script/app-telegram-full/img/shows.png', 'rb') as image:
                                    caption_text = f"Immagine non disponibile per '{series_title} ({series_year})"
                                    msg = bot.send_photo(chat_id, image, caption=caption_text, reply_markup=keyboard)

                            interazioni.save_message(chat_id, caption_text, is_user=False, forwarded_from=None, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
                        except Exception as e:
                            msg = bot.send_message(chat_id, f"Errore nell'invio dell'immagine: {str(e)} Linea: 284")
                            interazioni.save_message(chat_id, f"Errore nell'invio dell'immagine: {str(e)} Linea: 284", is_user=False, forwarded_from=None, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)

                        if chat_id not in user_states:
                            user_states[chat_id] = []  # Inizializza una lista vuota se non esiste già
                        user_states[chat_id].append('seasons')  # Aggiungi 'seasons' allo stato dell'utente

                    else:
                        msg = bot.send_message(chat_id, f"Spiacenti, non ho trovato stagioni per '{series_title} ({series_year})'.")
                        interazioni.save_message(chat_id, f"Spiacenti, non ho trovato stagioni per '{series_title} ({series_year})'.", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
            else:
                msg = bot.send_message(chat_id, f"Spiacenti, non ho trovato informazioni per il contenuto selezionato.")
                interazioni.save_message(chat_id, f"Libreria: {channel_name}", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)

        except Exception as e:
            msg = bot.send_message(chat_id, f"Errore: {str(e)} Linea: 213")
            interazioni.save_message(chat_id, f"Errore: {str(e)} Linea: 213", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)

    # Funzione per creare la tastiera inline per gli episodi di una stagione
    def create_episode_keyboard(chat_id, channel_name, content_id, season_number, series_title, series_year, user_id, user_name):
        try:
            libreria_document = db[f"Libreria: {channel_name}"].find_one({'_id': content_id})

            if libreria_document is not None:
                content_type = libreria_document['Type']  # Aggiunto per verificare il tipo di contenuto

                # Verifica se il contenuto è di tipo "movie"
                if content_type == "show":
                    seasons = libreria_document.get('Seasons', [])

                    # Trova la stagione selezionata
                    selected_season = None
                    for season in seasons:
                        if season['SeasonNumber'] == int(season_number):
                            selected_season = season
                            break
                    #
                    if selected_season:
                        episodes = selected_season.get('Episodes', [])

                        # Memorizza le informazioni sul contenuto selezionato
                        selected_content[chat_id]['season_number'] = int(season_number)

                        if episodes:
                            #print(episodes)
                            keyboard = telebot.types.InlineKeyboardMarkup()
                            current_row = []
                            for episode in episodes:
                                episode_number = episode['EpisodeNumber']
                                button_text = f"E{int(episode_number)}"
                                callback_data = f"episode:{content_id}:{season_number}:{episode_number}:{channel_name}"
                                button = telebot.types.InlineKeyboardButton(button_text, callback_data=callback_data)
                                current_row.append(button)
                                
                                if len(current_row) == 5:
                                    keyboard.row(*current_row)
                                    current_row = []
                            
                            if current_row:
                                keyboard.row(*current_row)

                            # scarica tutti gli episodi
                            download_all_button = telebot.types.InlineKeyboardButton("⬇️ Download tutti episodi", callback_data=f"download_all:{content_id}:{season_number}:{channel_name}")
                            keyboard.row(download_all_button)

                            # pulsante chiudi
                            back_button = telebot.types.InlineKeyboardButton("✖️ Chiudi", callback_data=f"chiudi")
                            keyboard.row(back_button)

                            file_path = f'/home/aik/Scrivania/script/app-telegram-full/scrapers/grafica/Libreria: {channel_name}/{series_title} ({series_year})/statione || {season_number} .jpg'
                            #print(file_path)
                            if os.path.exists(file_path):

                                # estrazione dei dati
                                descrizione_breve = season['Overview'][:850]
                                IDTmdb =  libreria_document['IDTmdb']
                                Data = season['Data']
                                Voto = season['Voto']

                                with open(file_path, 'rb') as image:
                                    caption_text = (
                                    f"🖥 *{series_title} ({series_year})*\n"
                                    f"⭐️*Voto Stagione*: {Voto}\n"
                                    f"🔗[Link TMDB](https://www.themoviedb.org/tv/{IDTmdb}/season/{season_number}?language=it-IT)\n"

                                    f"{descrizione_breve}"
                                    )

                                    bot_message_episodi = bot.send_photo(chat_id, image, caption=caption_text, parse_mode='Markdown', reply_markup=keyboard)
                            else:
                                bot_message_episodi = bot.send_message(chat_id, f"Episodi di '{series_title}', Stagione {season_number}:", reply_markup=keyboard)
                            
                            interazioni.save_message(chat_id, f"Episodi di '{series_title}', Stagione {season_number}:", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=bot_message_episodi.message_id)    
                            print(f"{ora_attuale}: L'utente \"{user_name}({user_id})\" ha selezionato da\"{channel_name}\" gli episodi di \"{series_title} ({series_year})\" della stagione \"{season_number}\"")
                        else:
                            msg = bot.send_message(chat_id, f"Spiacenti, non ho trovato episodi per la stagione {season_number}.")
                            interazioni.save_message(chat_id, f"Spiacenti, non ho trovato episodi per la stagione {season_number}.", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
                    else:
                        msg = bot.send_message(chat_id, f"Spiacenti, non ho trovato la stagione {season_number}.")
                        interazioni.save_message(chat_id, f"Spiacenti, non ho trovato la stagione {season_number}.", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
            else:
                msg = bot.send_message(chat_id, f"Spiacenti, non ho trovato informazioni per il contenuto selezionato.")
                interazioni.save_message(chat_id, f"Spiacenti, non ho trovato informazioni per il contenuto selezionato.", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)

        except Exception as e:
            msg = bot.send_message(chat_id, f"Errore: {str(e)}")
            interazioni.save_message(chat_id, f"Errore: {str(e)} Linea 279", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)

    # Funzione torna indietro - cancella i messaggi dal db
    @bot.callback_query_handler(func=lambda call: call.data.startswith('back'))
    def handle_back_button(call):

        #print("Pulsante 'torna indietro' premuto!")
        chat_id = call.message.chat.id
        user_id = call.from_user.id  # Otteniamo l'ID dell'utente qui
        user_name = call.from_user.username  # Otteniamo l'ID dell'utente qui

        # Estrai il nome del canale dai dati della callback
        data_parts = call.data.split(':')
        action = data_parts[0]
        channel_name = data_parts[1] if len(data_parts) > 1 else None

        # Se si tratta del pulsante 'back' e il nome del canale esiste
        if action == 'back' and channel_name:
            # Esegui la logica per eliminare i messaggi dell'utente dalla chat Telegram
            messaggi_da_eliminare = interazioni.select_cronologia_messaggi(user_id, user_name)

            for message_id in messaggi_da_eliminare:
                try:
                    bot.delete_message(call.message.chat.id, message_id)
                    #print(f"Eliminato il messaggio con message_id {message_id} dalla chat Telegram")

                except telebot.apihelper.ApiException as e:
                    if "message to delete not found" in str(e):
                        # Il messaggio non è stato trovato, passa al prossimo
                        continue
                    else:
                        print(f"Errore durante l'eliminazione del messaggio con message_id {message_id}: {e}")
            try:
                # Chiamata per eliminare il messaggio dal database
                interazioni.attivazione_pulsante_back(user_id, user_name)
                print(f"Pulito il database dai messaggi")
            except Exception as db_error:
                print(f"Errore durante l'eliminazione del messaggio dal database: {db_error}")
        # Richiama il messaggio
        create_library_keyboard(call.message.chat.id, channel_name, user_id, user_name)
        call.message.chat.id
  
    # bottone chiudi
    @bot.callback_query_handler(func=lambda call: call.data == "chiudi")
    def chiudi_callback(call):
        user_id = call.from_user.id  # Otteniamo l'ID dell'utente qui
        user_name = call.from_user.username  # Otteniamo l'ID dell'utente qui

        # Cancella il messaggio in cui è stato premuto il pulsante "Chiudi"
        bot.delete_message(call.message.chat.id, call.message.message_id)

        message_id = call.message.message_id
        # Chiamata per eliminare il messaggio dal database
        interazioni.chiudi_messaggio(user_id, user_name, message_id)
        #print(f"Eliminato il messaggio con message_id {message_id} dal database")
    
    # Gestore per la callback query del bottone "Torna alla lista dei Canali"
    @bot.callback_query_handler(func=lambda call: call.data == 'canali')
    def handle_back_button(call):
        # Esegui il codice per il comando /canali
        user_id = call.from_user.id  # Otteniamo l'ID dell'utente qui
        user_name = call.from_user.username  # Otteniamo l'ID dell'utente qui

        handle_canali(call.message)
        #print(handle_canali)

    # Gestisci il comando /canali
    @bot.message_handler(commands=['canali'])
    def handle_canali(message):

        user_id = message.from_user.id
        user_name = message.from_user.username

        channels = db['Canali'].find()
        markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)  # Cambia row_width da 1 a 2

        buttons = []  # Lista per conservare i bottoni temporaneamente
        for channel in channels:
            button_text = f"{channel['Canale']}"
            button = telebot.types.KeyboardButton(button_text)
            buttons.append(button)

        markup.add(*buttons)  # Aggiungi tutti i bottoni alla tastiera

        # Elimina il messaggio contenente il comando /canali
        bot.delete_message(message.chat.id, message.message_id)

        # salva nel db
        msg = bot.send_message(message.chat.id, "Ecco la lista dei canali:", reply_markup=markup)
        interazioni.save_message(message.chat.id, "Ecco la lista dei canali:", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
        print(f"{ora_attuale}: L'utente \"{user_name}({user_id})\" ha selezionato la  lista dei canali")
    # Gestisci la selezione del canale
    @bot.message_handler(func=lambda message: True)
    def handle_channel_selection(message):
        try:
            channel_name = message.text
            channel = db['Canali'].find_one({'Canale': channel_name})

            if channel:
                chat_id = message.chat.id
                user_id = message.from_user.id
                user_name = message.from_user.username

                # Salva nel db l'interazione dell'untente con i pulsanti della tastiera inline (canali)
                interazioni.save_message(chat_id, channel_name, is_user=True, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=message.message_id)

                # Verifica se il chat_id ha già una selezione precedente
                if chat_id not in viewing_state:
                    viewing_state[chat_id] = {'channels': [], 'offset': 0}

                # Aggiungi il canale selezionato alla lista delle selezioni
                viewing_state[chat_id]['channels'].append({'channel': channel_name})
                create_library_keyboard(chat_id, channel_name, user_id, user_name)

        except Exception as e:
            msg = bot.send_message(message.chat.id, f"Errore: {str(e)} Linea: 396")
            interazioni.save_message(chat_id, f"Errore: {str(e)} Linea: 396", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)

    # Gestisci il callback per la selezione della serie TV, stagione o l'inoltro del messaggio
    @bot.callback_query_handler(func=lambda call: call.data.startswith(('contenuto_id', 'season', 'episode', 'forward_message', 'load_more', 'download_all'))) 
    def handle_title_year_season_or_forward(call):
        user_id = call.from_user.id  # Otteniamo l'ID dell'utente qui
        user_name = call.from_user.username  # Otteniamo il nome dell'utente qui
        chat_id = call.message.chat.id
        data_parts = call.data.split(':')
        channel_name = data_parts[2]

        if call.data.startswith('contenuto_id'):
            # Estrai il content_id dal testo del pulsante
            content_id_str = data_parts[1]

            # Converti content_id in un ObjectId
            content_id = ObjectId(content_id_str)

            # Ora puoi estrarre i valori di Title e Year dal database
            libreria_document = db[f"Libreria: {channel_name}"].find_one({'_id': content_id})

            if libreria_document:
                series_title = libreria_document['Title']
                series_year = libreria_document['Year']

                # Ora hai estratto con successo
                create_seasons_keyboard(chat_id, channel_name, content_id, series_title, series_year, user_id, user_name)

        elif call.data.startswith('season'):
            # Estrai il content_id dal testo del pulsante
            content_id_str = data_parts[2]
            # Converti content_id in un ObjectId
            content_id = ObjectId(content_id_str)
            season_number = data_parts[3]
            channel_name = data_parts[1]

            # Ora puoi estrarre i valori di Title e Year dal database
            libreria_document = db[f"Libreria: {channel_name}"].find_one({'_id': content_id})

            if libreria_document:
                series_title = libreria_document['Title']
                series_year = libreria_document['Year']
                tipo = libreria_document['Type']

            create_episode_keyboard(chat_id, channel_name, content_id, season_number, series_title, series_year, user_id, user_name)

        elif call.data.startswith('episode'):
            # Estrai il content_id dal testo del pulsante
            content_id_str = data_parts[1]
            content_id = ObjectId(content_id_str)
            season_number = data_parts[2]
            episode_number = data_parts[3]
            channel_name = data_parts[4]

            try:
                # Converti content_id in un ObjectId
                content_id = ObjectId(content_id_str)

                # Recupera le informazioni sul contenuto selezionato
                content_info = selected_content.get(chat_id, {})

                if content_info:
                    # Utilizza l'ID del contenuto catturato per cercare il contenuto all'interno della stessa libreria
                    libreria_document = db[f"Libreria: {channel_name}"].find_one({'_id': content_id})
                    # Recupero l'id del canale per l'inoltro
                    canale_id = libreria_document['Canale ID']
                    if libreria_document:
                        selected_season = None
                        seasons = libreria_document.get('Seasons', [])
                        for season in seasons:
                            if season['SeasonNumber'] == int(season_number):
                                selected_season = season
                                break

                        if selected_season:
                            episodes = selected_season.get('Episodes', [])

                            selected_episode = None
                            for episode in episodes:
                                if episode['EpisodeNumber'] == int(episode_number):
                                    selected_episode = episode
                                    break

                            if selected_episode:
                                permesso = verifica_permessi.estrai_permessi(user_id)
                                #print(permesso)
                                if permesso < 1:  # 2 è il permesso per "Utente Premium"
                                    msg = bot.send_message(chat_id, "Accesso negato. Devi registrarti per accedere al contenuto /registrazione")
                                    # Salva il messaggio nel database o esegui altre operazioni di logging qui
                                    interazioni.save_message(chat_id, "Accesso negato. Devi registrarti per accedere al contenuto", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
                                    return  # Interrompe l'esecuzione della funzione
                                    # Creare tastiere inline per gli episodi della stagione
                                    # Inoltra il messaggio dalla chat del canale alla chat del bot
                                for content_item in selected_episode['Contents']:
                                    message_id = content_item['Message ID']
                                    forwarded_msg = bot.copy_message(chat_id, canale_id, message_id)
                                    
                                    interazioni.save_message(chat_id, "Messaggio inoltrato", is_user=False, forwarded_from=None, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=forwarded_msg.message_id)

                                # bottone che gestisce il torna indietro
                                keyboard = telebot.types.InlineKeyboardMarkup()
                                back_button = telebot.types.InlineKeyboardButton(f"🔚Concludi la visione e torna a {channel_name}", callback_data=f"back:{channel_name}")
                                keyboard.add(back_button)
                                msg = bot.send_message(chat_id, "Seleziona un'opzione:", reply_markup=keyboard)
                                interazioni.save_message(chat_id, f"Libreria: {channel_name}", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)

                            else:
                                msg = bot.send_message(chat_id, f"Episodio {episode_number} non trovato.")
                                interazioni.save_message(chat_id, f"Episodio {episode_number} non trovato.", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
                        else:
                            msg = bot.send_message(chat_id, f"Stagione {season_number} non trovata.")
                            interazioni.save_message(chat_id, f"Stagione {season_number} non trovata.", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
                    else:
                        msg = bot.send_message(chat_id, f"Contenuto non trovato.")
                        interazioni.save_message(chat_id, f"Contenuto non trovato.", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
            except telebot.apihelper.ApiException as e:
                msg = bot.send_message(chat_id, f"Errore durante l'inoltro del messaggio: {str(e)} Linea: 511")
                interazioni.save_message(chat_id, f"Errore durante l'inoltro del messaggio: {str(e)} Linea: 511", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)

        elif call.data.startswith('download_all'):
            permesso = verifica_permessi.estrai_permessi(user_id)
            #print(permesso)
            if permesso <= 1:  # 2 è il permesso per "Utente Premium"
                msg = bot.send_message(chat_id, "Accesso negato. Devi essere un utente premium per utilizzare questa funzione. /diventa_premium")
                # Salva il messaggio nel database o esegui altre operazioni di logging qui
                interazioni.save_message(chat_id, "Accesso negato. Devi essere un utente premium per utilizzare questa funzione.", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
                return  # Interrompe l'esecuzione della funzione
            else:
                #Estrai tutti gli episodi
                content_id_str = data_parts[1]
                season_number = data_parts[2]
                channel_name = data_parts[3]
                content_id = ObjectId(content_id_str)

                try:
                    # Converti content_id in un ObjectId
                    content_id = ObjectId(content_id_str)

                    # Recupera le informazioni sul contenuto selezionato
                    content_info = selected_content.get(chat_id, {})
                    libreria_document = db[f"Libreria: {channel_name}"].find_one({'_id': content_id})

                    # Recupero l'id del canale per l'inoltro
                    if libreria_document:
                        selected_season = None
                        seasons = libreria_document.get('Seasons', [])
                        for season in seasons:
                            if season['SeasonNumber'] == int(season_number):
                                selected_season = season
                                break

                        if selected_season:
                            episodes = selected_season.get('Episodes', [])
                            canale_id = libreria_document['Canale ID']

                            # Inoltra tutti gli episodi della stagione selezionata
                            for episode in episodes:
                                #logging.debug(f"Inoltro dell'episodio: {episode}")
                                for content_item in episode['Contents']:
                                    message_id = content_item['Message ID']
                                    forwarded_msg = bot.copy_message(chat_id, canale_id, message_id)
                                    
                                    interazioni.save_message(chat_id, episode, is_user=False, forwarded_from=None, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=forwarded_msg.message_id)
                                    
                            # bottone che gestisce il torna indietro
                            keyboard = telebot.types.InlineKeyboardMarkup()
                            back_button = telebot.types.InlineKeyboardButton("🔚Torna indietro", callback_data=f"back:{channel_name}")
                            print(f"{ora_attuale}: L'utente \"{user_name}({user_id})\" da\"{channel_name}\" da selezionato il tasto download tutti gli espisodi")
                            keyboard.add(back_button)

                            # Invia il messaggio
                            msg = bot.send_message(chat_id, "Seleziona un'opzione:", reply_markup=keyboard)
                            interazioni.save_message(chat_id, episode, is_user=False, forwarded_from=None, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)

                            # Recupera l'ID del messaggio appena inviato
                            message_id = msg.message_id
                            # Ora puoi salvare l'ID del messaggio nel database
                            interazioni.save_message(chat_id, "Torna Indietro - Episodi", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=message_id)

                        else:
                            msg = bot.send_message(chat_id, f"Stagione {season_number} non trovata.")
                            interazioni.save_message(chat_id, f"Stagione {season_number} non trovata.", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
                    else:
                        msg = bot.send_message(chat_id, "Contenuto non trovato")
                        interazioni.save_message(chat_id, "Contenuto non trovato", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)

                except telebot.apihelper.ApiException as e:
                    msg = bot.send_message(chat_id, f"Errore durante lo scaricamento di tutti gli episodi: {str(e)} Linea: 580")
                    interazioni.save_message(chat_id, f"Errore durante lo scaricamento di tutti gli episodi: {str(e)} Linea: 580", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)

        elif call.data.startswith('load_more'):
            offset = int(data_parts[1])
            create_library_keyboard(chat_id, channel_name, user_id, user_name, offset)

