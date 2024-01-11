import interazioni # gestisce il salvatagio nel db delle interazioni tra utente e bot
from database import Database
import datetime

# Crea un'istanza della classe Database
database_instance = Database()
db = database_instance.get_db()

# Funzione per gestire il comando /registrazione e /deventa_premium
def setup_registrazioni_module(message, bot, tipo_richiesta):
    user_id = message.from_user.id
    user_name = message.from_user.username

    # Controllo per comando /registrazione
    if tipo_richiesta == "utente":
        existing_user = db.Users.find_one({"user_id": user_id, "user_name": user_name})
        if existing_user is not None and existing_user.get("permessi", 0) > 0:
            msg = bot.send_message(message.chat.id, "Sei già registrato.")
            interazioni.save_message(message.chat.id, "Sei già registrato.", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
            return
        existing_request = db.Registrazioni.find_one({"user_id": user_id, "tipo_richiesta": "utente"})
        if existing_request is not None:
            date = existing_request["date"].strftime("%Y-%m-%d")
            msg_text = f'<a href="tg://user?id={user_name}">{user_name}</a> hai già effettuato la richiesta per diventare <b>Utente ⭐️⭐️</b> in data <b>{date}</b> \n Attendi che un admin ti accetti.'
            msg = bot.send_message(message.chat.id, msg_text, parse_mode='HTML')
            interazioni.save_message(message.chat.id, msg_text, is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
            return

    # Controllo per comando /diventa_premium
    elif tipo_richiesta == "utente premium":
        existing_user = db.Users.find_one({"user_id": user_id, "user_name": user_name})
        if existing_user is not None and existing_user.get("permessi", 0) > 1:
            msg = bot.send_message(message.chat.id, "Sei già un Utente Premium.")
            interazioni.save_message(message.chat.id, "Sei già un Utente Premium.", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
            return
        existing_request = db.Registrazioni.find_one({"user_id": user_id, "tipo_richiesta": "utente premium"})
        if existing_request is not None:
            date = existing_request["date"].strftime("%Y-%m-%d")
            msg_text = f'<a href="tg://user?id={user_name}">{user_name}</a> hai già effettuato la richiesta per diventare <b>Utente Premium ⭐️⭐️⭐️</b> in data <b>{date}</b> \n Attendi che un admin ti accetti.'
            msg = bot.send_message(message.chat.id, msg_text, parse_mode='HTML')
            interazioni.save_message(message.chat.id, msg_text, is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
            return
    
    # Se nessuno dei controlli precedenti ha avuto successo, inserisce la richiesta in "Registrazioni"
    db.Registrazioni.insert_one({
        "user_id": user_id,
        "user_name": user_name,
        "date": datetime.datetime.now(),
        "tipo_richiesta": tipo_richiesta,
        "stato": "in lavorazione"
    })
    msg = bot.send_message(message.chat.id, f"Perfetto, {user_name}! hai effettuato correttamente la richiesta di registrazione come {tipo_richiesta}. Attendi che un admin accetti la tua candidatura.")
    interazioni.save_message(message.chat.id, f"Perfetto, {user_name}! hai effettuato correttamente la richiesta di registrazione come {tipo_richiesta}. Attendi che un admin accetti la tua candidatura.", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
    
    # Invia il messaggio di conferma nel gruppo specifico
    group_chat_id = -1002097637563
    msg_text = f'<a href="tg://user?id={user_name}">{user_name}</a> ha effettuato la richiesta di registrazione per ottenere i permessi di: <b>{tipo_richiesta}</b>'
    msg = bot.send_message(group_chat_id, msg_text, parse_mode='HTML')

    # Trova gli utenti con "permessi" >= 3 in "Users" e invia un messaggio
    admin_users = db.Users.find({"permessi": {"$gte": 3}})
    for admin_user in admin_users:
        admin_id = admin_user['user_id']
        msg = bot.send_message(admin_id, f"L'utente {user_name}(user_id={user_id}) ha effettuato la richiesta di registrazione. Entra nel bot ed esegui il comando /admin_registrazioni per accettare o rifiutare la sua richiesta.")
        interazioni.save_message(message.chat.id, "Sei già registrato.", is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)
