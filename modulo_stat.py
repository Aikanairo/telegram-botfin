from database import Database
from telebot import types
#import modulo_chiudi # Importa il modulo modulo_chiudi
import interazioni # gestisce il salvatagio nel db delle interazioni tra utente e bot

# Chiamata la funzione per gestire il comando /chiudi
#modulo_chiudi.setup_chiudi_module(bot)

# Crea un'istanza della classe Database
database_instance = Database()
db = database_instance.get_db()

def setup_stat_module(bot):
    @bot.message_handler(commands=['stat'])
    def stat_command(message):
        stat(message, bot)

        # Elimina il messaggio contenente il comando /canali
        bot.delete_message(message.chat.id, message.message_id)

def convert_size_to_giga_tera(total_size_in_bytes):
    # Converte da byte a gigabyte o terabyte in base alla dimensione
    if total_size_in_bytes < 1e9:
        return f"{total_size_in_bytes / 1e9:.2f} GB"
    else:
        return f"{total_size_in_bytes / 1e12:.2f} TB"

def sum_sizes_in_document(document):
    total_size_in_bytes = 0
    # Itera su tutti i risultati all'interno del documento
    for result in document.get('Seasons', []):
        for episode in result.get('Episodes', []):
            for content in episode.get('Contents', []):
                size = content.get('Size', 0)
                if isinstance(size, int):
                    total_size_in_bytes += size
                elif isinstance(size, dict) and '$numberLong' in size:
                    total_size_in_bytes += int(size['$numberLong'])
    return total_size_in_bytes

def stat(message, bot):
    user_id = message.from_user.id
    user_name = message.from_user.username

    # Trova tutti i documenti nel database che iniziano per "Libreria"
    library_names = db.list_collection_names(filter={"name": {"$regex": "^Libreria: "}})
    
    result_message = "📊 *Statistiche delle Librerie gestite:*\n\n"
    
    for library_name in library_names:
        # Inizializza il totale delle dimensioni per la libreria corrente
        total_size_in_bytes = 0
        
        # Cerca tutti i documenti nella collezione corrente
        library_documents = db[library_name].find({})
        
        # Conta il numero di risultati
        total_results = 0
        
        # Calcola il totale delle dimensioni sommando i campi "Size" di tutti i risultati
        for document in library_documents:
            total_size_in_bytes += sum_sizes_in_document(document)
            total_results += 1
        
        # Converte il totale delle dimensioni in gigabyte o terabyte
        total_size = convert_size_to_giga_tera(total_size_in_bytes)
        
        # Formatta il messaggio per la libreria corrente utilizzando Markdown
        result_message += f"📂 `{library_name}`\n🖥*Contenuti:* `{total_results}`\n🗄 *Dimensione*: `{total_size}`\n\n"
    
    # Creazione della inline keyboard con il pulsante "Chiudi"
    markup = types.InlineKeyboardMarkup()
    close_button = types.InlineKeyboardButton("✖️ Chiudi", callback_data="chiudi")
    markup.add(close_button)
    
    # Invia il messaggio al chat_id specificato con la inline keyboard
    msg = bot.send_message(chat_id=message.chat.id, text=result_message, parse_mode='Markdown', reply_markup=markup)
    
    # Salva il messaggio nel db
    interazioni.save_message(message.chat.id, result_message, is_user=False, bot_chat_id=bot.get_me().id, user_id=user_id, user_name=user_name, message_id=msg.message_id)