from database import Database
import datetime

# Crea un'istanza della classe Database
database_instance = Database()
db = database_instance.get_db()

def fetch_user_info(message, bot):
    db = database_instance.get_db()
    
    # Trova il documento relativo all'utente
    user_doc = db.Users.find_one({"user_id": message.from_user.id})
    
    if user_doc:
        # Estrae le informazioni necessarie
        user_id = user_doc.get('user_id')
        bot_chat_id = user_doc.get('bot_chat_id')
        chat_id = user_doc.get('chat_id')
        is_logged = user_doc.get('is_logged', False)
        permessi = user_doc.get('permessi')
        user_name = user_doc.get('user_name')
        
        if is_logged:
            return {
                'user_id': user_id,
                'bot_chat_id': bot_chat_id,
                'chat_id': chat_id,
                'is_logged': is_logged,
                'permessi': permessi,
                'user_name': user_name
            }
        else:
            bot.send_message(chat_id=chat_id, text="Non sei loggato, premi /start per loggarti.")
            return 
    else:
        bot.send_message(chat_id=message.chat.id, text="Non sei loggato, premi /start per loggarti.")
        return 
