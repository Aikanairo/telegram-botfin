import interazioni # gestisce il salvatagio nel db delle interazioni tra utente e bot
from bson import ObjectId
from database import Database
from telebot import types
from fuzzywuzzy import fuzz
from datetime import datetime
from config import group_chat_id


# Crea un'istanza della classe Database
database_instance = Database()
db = database_instance.get_db()

# gestione cambio ruoli (permessi)
# Dizionario per tradurre i ruoli in numeri
role_to_number = {
    "visitatore": 0,
    "utente": 1,
    "utente premium": 2,
    "admin": 3,
    "gestore": 4
}

def handle_permission_command(message, bot):
    user_id = message.from_user.id  # Otteniamo l'ID dell'utente qui
    user_name = message.from_user.username  # Otteniamo l'ID dell'utente qui
    instruction = "<b>Per assegnare il ruolo segui le istruzioni</b>\n\n Esempio:\n <b>Aik - admin</b>\n\n <b>Leggenda:</b>\n⭐️(visitatore)\n⭐️⭐️(utente)\n ⭐️⭐️⭐️(utente premium)\n⭐️⭐️⭐️⭐️(admin)\n⭐️⭐️⭐️⭐️⭐️(gestore)"
    
    # Creazione della inline keyboard con il pulsante "Chiudi"
    markup = types.InlineKeyboardMarkup()
    close_button = types.InlineKeyboardButton("✖️ Chiudi", callback_data="chiudi")
    markup.add(close_button)
    
    # Invia messaggio
    msg = bot.send_message(message.chat.id, instruction, parse_mode='HTML', reply_markup=markup)
    interazioni.save_message(message.chat.id, instruction, is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)

def update_user_permission(message, bot):

    # Otteniamo informazioni utente
    user_id = message.from_user.id 
    user_name = message.from_user.username 

    # Ottieni le informazioni sull'utente che invia il comando
    command_sender = message.from_user.username
    sender_info = db.Users.find_one({"user_name": command_sender})

    role_to_assign = None  # Inizializza la variabile per il ruolo da assegnare

    if sender_info and sender_info.get('permessi', -1) >= 3:
        try:
            user, role_text = message.text.split(" - ")
            role_number = role_to_number.get(role_text.lower(), None)
            role_to_assign = role_text  # Memorizza il ruolo da assegnare per usarlo più avanti

            if role_number is None:  # Il ruolo non è valido
                instruction = "Leggenda:\n⭐️(visitatore)\n⭐️⭐️(utente)\n⭐️⭐️⭐️(utente premium)\n⭐️⭐️⭐️⭐️(admin)\n⭐️⭐️⭐️⭐️⭐️(gestore)"
                
                # Creazione della inline keyboard con il pulsante "Chiudi"
                markup = types.InlineKeyboardMarkup()
                close_button = types.InlineKeyboardButton("✖️ Chiudi", callback_data="chiudi")
                markup.add(close_button)

                msg = bot.send_message(message.chat.id, f"Il ruolo: <b>{role_text}</b> non esiste.\nFai attenzione a digitare il permesso da assegnare.\n{instruction}", parse_mode='HTML', reply_markup="markup")
                interazioni.save_message(message.chat.id, f"Il ruolo: <b>{role_text}</b> non esiste.\nFai attenzione a digitare il permesso da assegnare.\n{instruction}", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)

                return

            # cerca l'utente
            all_users = db.Users.find({})

            if all_users:  
                possible_matches = []

                for u in all_users:
                    if fuzz.ratio(user, u['user_name']) >= 50:
                        possible_matches.append(u)

                if possible_matches:
                    markup = types.InlineKeyboardMarkup()
                    for match in possible_matches:
                        user_name = match['user_name']
                        data_to_pass = f"{user_name}|{role_to_assign}"
                        data_to_pass = f"match:{user_name}|{role_to_assign}"
                        markup.add(types.InlineKeyboardButton(text=user_name, callback_data=data_to_pass))


                    msg = bot.send_message(message.chat.id, f"Premi uno dei nomi per assegnare il permesso: {role_to_assign}", reply_markup=markup)
                    interazioni.save_message(message.chat.id, f"Premi uno dei nomi per assegnare il permesso: {role_to_assign}", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
                else:
                    msg = bot.send_message(message.chat.id, "Nessuna corrispondenza trovata.")
                    interazioni.save_message(message.chat.id, "Nessuna corrispondenza trovata.", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)

        except ValueError:
            msg = bot.send_message(message.chat.id, "Formato non corretto. Usa: [nome utente] - [ruolo]")
            interazioni.save_message(message.chat.id, "Formato non corretto. Usa: [nome utente] - [ruolo]", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)

    else:
        msg = bot.send_message(message.chat.id, "Non hai i permessi per eseguire questa operazione.")
        interazioni.save_message(message.chat.id, "Non hai i permessi per eseguire questa operazione.", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)

# gestione lista utenti
def fetch_users(db):
    users = db.Users.find({})
    messages = []
    current_message = ""
    for user in users:
        user_id = user['user_id']
        user_name = user['user_name']
        permesso = user.get('permessi', None)

        if permesso is None:
            role = "🌥(Guest)"
        elif permesso == 0:
            role = "⭐️(Visitatore)"
        elif permesso == 1:
            role = "⭐️⭐️(Utente)"
        elif permesso == 2:
            role = "⭐️⭐️⭐️(Utente Premium)"
        elif permesso == 3:
            role = "⭐️⭐️⭐️⭐️(Admin)"
        elif permesso == 4:
            role = "⭐️⭐️⭐️⭐️⭐️(Gestore)"

        line = f"<a href=\"tg://user?id={user_id}\">{user_name}</a> - <b>Ruolo</b>: {role}\n"

        if len(current_message + line) > 4096:  # Limiti di Telegram
            messages.append(current_message)
            current_message = ""

        current_message += line

    if current_message:
        messages.append(current_message)

    return messages

def handle_admin_command(message, bot):
    user_id = message.from_user.id  # Otteniamo l'ID dell'utente qui
    user_name = message.from_user.username  # Otteniamo l'ID dell'utente qui
    markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    itembtn1 = types.KeyboardButton('📘 Utenti')
    itembtn2 = types.KeyboardButton('📕 Permessi')
    itembtn3 = types.KeyboardButton('📗 Richieste')
    markup.add(itembtn1, itembtn2, itembtn3)
    risultato = bot.send_message(message.chat.id, "Scegli una delle seguenti opzioni:", reply_markup=markup)
    interazioni.save_message(message.chat.id, "Scegli una delle seguenti opzioni:", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=risultato.message_id)


def handle_button_click(message, bot):
    user_id = message.from_user.id  # Otteniamo l'ID dell'utente qui
    user_name = message.from_user.username  # Otteniamo l'ID dell'utente qui

    if message.text == "📗 Richieste":
        # Elimina il messaggio "📗 Richieste" inviato dall'utente
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except telebot.apihelper.ApiTelegramException as e:
            # Gestisci l'errore se il messaggio non è stato trovato
            if "Bad Request: message to delete not found" in str(e):
                pass
        
        # Gestisci le richieste
        handle_requests("📗 Richieste", message, bot)

    elif message.text == "📘 Utenti":
        # Elimina il messaggio "📘 Utenti" inviato dall'utente
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except telebot.apihelper.ApiTelegramException as e:
            # Gestisci l'errore se il messaggio non è stato trovato
            if "Bad Request: message to delete not found" in str(e):
                pass

        # Mostra la lista degli utenti
        user_messages = fetch_users(db)
        for msg in user_messages:
            # Creazione della inline keyboard con il pulsante "Chiudi"
            markup = types.InlineKeyboardMarkup()
            close_button = types.InlineKeyboardButton("✖️ Chiudi", callback_data="chiudi")
            markup.add(close_button)

            risultato = bot.send_message(message.chat.id, msg, parse_mode='HTML', reply_markup=markup)
            interazioni.save_message(message.chat.id, msg, is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=risultato.message_id)

    elif message.text == "📕 Permessi":
        handle_permission_command(message, bot)
        
        # Elimina il messaggio inviato dall'utente che ha attivato la funzione
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except telebot.apihelper.ApiTelegramException as e:
            # Gestisci l'errore se il messaggio non è stato trovato
            if "Bad Request: message to delete not found" in str(e):
                pass


# gestione delle richieste
def handle_requests(button_text, message, bot):
    user_id = message.from_user.id  # Otteniamo l'ID dell'utente qui
    user_name = message.from_user.username  # Otteniamo l'ID dell'utente qui

    # Estrai tutti gli user_name nel cui campo "stato" sia uguale a "in lavorazione"
    requests = db.Registrazioni.find({"stato": "in lavorazione"})

    for request in requests:
        _id = request.get("_id", "")  # Ottieni l'ID della richiesta
        tipo_richiesta = request.get("tipo_richiesta", "")
        user_name_richiesta = request.get("user_name", "")

        # Costruisci il messaggio da inviare all'utente
        messaggio = f"Utente <a href=\"tg://user?id={user_name_richiesta}\">{user_name_richiesta}</a> ha effettuato la registrazione per ottenere i permessi di <b>{tipo_richiesta}</b>"
        markup = types.InlineKeyboardMarkup(row_width=2)
        approva_button = types.InlineKeyboardButton("✅ Approva", callback_data=f"approve:{_id}:{user_name_richiesta}:{tipo_richiesta}")
        respingi_button = types.InlineKeyboardButton("🚷 Respingi", callback_data=f"reject:{_id}:{user_name_richiesta}")
        markup.add(approva_button, respingi_button)

        # Invia il messaggio con i pulsanti all'admin
        risultato = bot.send_message(message.chat.id, messaggio, parse_mode='HTML', reply_markup=markup)
        interazioni.save_message(message.chat.id, messaggio, is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=risultato.message_id)

def setup_admin_module(bot):
    @bot.message_handler(commands=['admin_registrazioni'])
    def admin_registrazioni_command(message):
        handle_admin_command(message, bot)
        bot.delete_message(message.chat.id, message.message_id)

    # attivazione del nome matchato per l'assegnazione del ruolo     
    @bot.callback_query_handler(func=lambda call: call.data.startswith('match:'))   
    def callback_inline(call):
        #print(f"Pulsante match premuto: {call.data}")
        actual_data = call.data[len('match:'):]
        
        # Estrai le informazioni dall'oggetto call
        user_who_clicked = call.from_user.username
        user_who_clicked_id = call.from_user.id
        data_received = actual_data.split("|")
        user_to_update = data_received[0]
        role_to_assign = data_received[1]
        role_number = role_to_number.get(role_to_assign, None)

        # Trova le informazioni degli utenti nel database
        target_user = db.Users.find_one({"user_name": user_to_update})
        sender_info = db.Users.find_one({"user_name": user_who_clicked})

        if sender_info is not None and target_user is not None:
            # Controlli sui permessi
            if sender_info.get('permessi') == 3 and role_number == 4:
                print("Condizione 1: Non hai i permessi per assegnare il ruolo di Gestore.")
                bot.answer_callback_query(call.id, "Non hai i permessi per assegnare il ruolo di Gestore.")
                return
            if sender_info.get('permessi') == 3 and target_user.get('permessi') == 4 and role_number < 4:
                print("Condizione 2: Non hai i permessi per declassare un Gestore.")
                bot.answer_callback_query(call.id, "Non hai i permessi per declassare un Gestore.")
                return

            # Esegui l'aggiornamento del database
            esito = db.Users.update_one({"user_name": user_to_update}, {"$set": {"permessi": role_number}})

            if esito:
                bot.answer_callback_query(call.id, f"Operazione Eseguita! {user_who_clicked} ora è {role_to_assign}")
            else:
                bot.answer_callback_query(call.id, f"Errore! {user_who_clicked} non è stato possibile assegnargli il ruolo di: {role_to_assign}")
                return

            # Invia il messaggio di conferma nel gruppo specifico
            #group_chat_id = 
            msg_text = f'<a href="tg://user?id={user_who_clicked_id}">{user_who_clicked}</a> ha modificato il ruolo di <a href="tg://user?id={user_to_update}">{user_to_update}</a> in: <b>{role_to_assign}</b>'
            msg = bot.send_message(group_chat_id, msg_text, parse_mode='HTML')
            user_id = call.from_user.id  # Otteniamo l'ID dell'utente qui
            user_name = call.from_user.username  # Otteniamo l'ID dell'utente qui
            #interazioni.save_message(message.chat.id, msg_text, is_user=False, bot_chat_id=bot.get_me().id, user_id=user_who_clicked_id, user_name=user_who_clicked, message_id=msg.message_id)

            # Log l'azione nell'Admin Log
            admin_log = db.get_collection('Log Admin')
            if admin_log is None:
                db.create_collection('Log Admin')
                admin_log = db.get_collection('Log Admin')

            log_entry = {
                'user_admin': user_who_clicked,
                'user': user_to_update,
                'azione': f'ha cambiato il ruolo in : {role_to_assign}',
                'data': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            admin_log.insert_one(log_entry)

            # Elimina il messaggio "Premi uno dei nomi per assegnare il permesso"
            bot.delete_message(call.message.chat.id, call.message.message_id)

    # Aggiungi un altro gestore per catturare il messaggio successivo per aggiornare i permessi
    @bot.message_handler(func=lambda message: " - " in message.text)
    def handle_permission_update(message):
        update_user_permission(message, bot)

    @bot.message_handler(func=lambda message: message.text in ["📘 Utenti", "📕 Permessi", "📗 Richieste"])
    def handle_buttons(message):
        handle_button_click(message, bot)
    
    # Funzione per gestire le azioni di approvazione e respingimento
    @bot.callback_query_handler(func=lambda call: call.data.startswith('approve:') or call.data.startswith('reject:'))
    def handle_request_action(call):
        user_id = call.from_user.id  # Otteniamo l'ID dell'utente qui
        user_name = call.from_user.username  # Otteniamo l'ID dell'utente qui

        # Eseguire l'azione di Approvazione o Respinta qui
        data = call.data.split(":")
        action = data[0]
        _id = data[1]  # Aggiunto _id come parametro
        user_name_richiesta = data[2]

        # Recupera il valore di 'tipo_richiesta' dal documento del database
        db_entry = db.Registrazioni.find_one({"_id": ObjectId(_id)})
        tipo_richiesta = db_entry.get("tipo_richiesta", "Tipo Richiesta Sconosciuto")

        if action == 'approve':
            # Aggiorna lo stato nel documento Registrazioni
            db.Registrazioni.update_one({"_id": ObjectId(_id)}, {"$set": {"stato": "approvato", "data_esito": datetime.now(), "admin_esito": user_name}})
            
            # Imposta il campo permessi in base al tipo di richiesta
            permessi = 1 if tipo_richiesta == "utente" else 2 if tipo_richiesta == "utente premium" else None
            if permessi is not None:
                db.Users.update_one({"user_name": user_name_richiesta}, {"$set": {"permessi": permessi}})
            
            # Invia un messaggio all'utente
            messaggio_utente = f"La richiesta per diventare <b>{tipo_richiesta}</b> è stata accolta."
            bot.send_message(call.message.chat.id, messaggio_utente, parse_mode='HTML')
            
        elif action == 'reject':
            # Aggiorna lo stato nel documento Registrazioni
            db.Registrazioni.update_one({"_id": ObjectId(_id)}, {"$set": {"stato": "respinto", "data_esito": datetime.now(), "admin_esito": user_name}})
            
            # Invia un messaggio all'utente
            messaggio_utente = "La richiesta è stata respinta."
            bot.send_message(call.message.chat.id, messaggio_utente)

        # Elimina il messaggio con i pulsanti
        bot.delete_message(call.message.chat.id, call.message.message_id)

        # Invia un messaggio nel gruppo specifico
        #group_chat_id = sostato su config
        msg_text = f'{user_name} ha {action} la richiesta di {user_name_richiesta} per diventare {tipo_richiesta}'
        bot.send_message(group_chat_id, msg_text)