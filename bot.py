import telebot
import config
import time
import modulo_stat   # gestisce il comando /stat modulo-stat.p
import modulo_check   # gestisce il comando /check modulo-check.p
import modulo_canali  # gestisce il comando /canali modulo-canali.py
import modulo_speedtest  # Importa il nuovo modulo per lo speedtest
#import modulo_chiudi # Importa il modulo modulo_chiudi
import modulo_infousers
import modulo_registrazioni  # gestisce il comando /registrazioni modulo-registrazioni.py
import modulo_admin_registrazioni  # modulo gestione utenti
import verifica_permessi #gestione dei permessi
import interazioni  # gestisce il salvatagio nel db delle interazioni tra utente e bot


# token bot che risiede su config.py
bot = telebot.TeleBot(config.TELEGRAM_TOKEN)

# Gestisci il comando /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    user = message.from_user
    user_id = message.from_user.id

    # Controllo permessi
    permesso = verifica_permessi.estrai_permessi(user_id)
    if permesso:
        if permesso == 1:  # messaggio per gli admin
            sent_message = bot.send_message(message.chat.id,
                f"Benvenuto, {user.first_name}! Il bot gestisce i tuoi canali multimediali (serie tv e film) e li cataloga.\n\n"
                "<b>Comandi disponibili:</b>\n"
                "/canali - Lista dei canali gestiti\n"
                "/stat - Consultare le statistiche\n"
                "/speedtest - Effettuo uno speedtest della tua connessione\n"
                "/diventa_premium - Effetua richiesta Per avere accesso illimitato ai file\n\n",
                parse_mode="HTML"
            )

        if permesso == 2:  # messaggio per gli admin
            sent_message = bot.send_message(message.chat.id,
                f"Benvenuto, {user.first_name}! Il bot gestisce i tuoi canali multimediali (serie tv e film) e li cataloga.\n\n"
                "<b>Comandi disponibili:</b>\n"
                "/canali - Lista dei canali gestiti\n"
                "/stat - Consulta le statistiche\n"
                "/speedtest - Effettuo uno speedtest della tua connessione\n",
                parse_mode="HTML"
            )

        #print(permesso)
        if permesso >= 3:  # messaggio per gli admin
            sent_message = bot.send_message(message.chat.id,
                f"Benvenuto, {user.first_name}! Il bot gestisce i tuoi canali multimediali (serie tv e film) e li cataloga.\n\n"
                "<b>Comandi disponibili:</b>\n"
                "/canali - Lista dei canali gestiti\n"
                "/stat - Consultare le statistiche\n"
                "/speedtest - Effettuo uno speedtest della tua connessione\n"
                "/registrazione - Per consultare i file\n"
                "/diventa_premium - Per avere accesso illimitato\n\n"
                "<b>Amministrazioni:</b>\n"
                "/admin_registrazioni - per accedere alle funzioni da admin\n"
                "/check - Verifica episodi mancanti",
                parse_mode="HTML"
            )
        # Elimina il messaggio contenente il comando /canali
        bot.delete_message(message.chat.id, message.message_id)

        try:
            # Aggiungi il messaggio inviato dall'utente nel database
            interazioni.save_message(message.chat.id, "/Start Contenuto", is_user=False, bot_chat_id=bot.get_me().id, user_id=message.from_user.id, user_name=message.from_user.username, message_id=sent_message.message_id)
        
        except Exception as e:
            msg = sent_message = bot.send_message(message.chat.id, f"Errore: {str(e)}")
            interazioni.save_message(message.chat.id, f"Errore: {str(e)}", is_user=False, bot_chat_id=bot.get_me().id, user_id=message.from_user.id, user_name=message.from_user.username, message_id=msg.message_id)
    else:
        sent_message = bot.send_message(message.chat.id,
            f"Benvenuto, {user.first_name}! Il bot gestisce i tuoi canali multimediali (serie tv e film) e li cataloga.\n\n"
            "<b>Comandi disponibili:</b>\n"
            "/canali - Lista dei canali gestiti\n"
            "/stat - Consultare le statistiche\n"
            "/speedtest - Effettuo uno speedtest della tua connessione\n"
            "/registrazione - Per consulare i file\n"
            "/diventa_premium - Effetua richiesta Per avere accesso illimitato ai file\n\n",
            parse_mode="HTML"
        )
        try:
            # Aggiungi il messaggio inviato dall'utente nel database
            interazioni.save_message(message.chat.id, "/Start Contenuto", is_user=False, bot_chat_id=bot.get_me().id, user_id=message.from_user.id, user_name=message.from_user.username, message_id=sent_message.message_id)
        
        except Exception as e:
            msg = sent_message = bot.send_message(message.chat.id, f"Errore: {str(e)}")
            interazioni.save_message(message.chat.id, f"Errore: {str(e)}", is_user=False, bot_chat_id=bot.get_me().id, user_id=message.from_user.id, user_name=message.from_user.username, message_id=msg.message_id)

@bot.message_handler(commands=['getid'])
def get_id(message):
    chat_id_group = message.chat.id
    bot.send_message(chat_id_group, f"L'ID di questa chat è {chat_id_group}.")


# Gestisci il comando /registrazione
@bot.message_handler(commands=['registrazione'])
def handle_registrazione(message):
    modulo_registrazioni.setup_registrazioni_module(message, bot, "utente")

# Gestisci il comando /diventa_premium
@bot.message_handler(commands=['diventa_premium'])
def handle_registrazione(message):
    modulo_registrazioni.setup_registrazioni_module(message, bot, "utente premium")

# modulo speedtes
modulo_speedtest.setup_speedtest_module(bot) 

# gestisce il comendo admin_registrazioni
modulo_admin_registrazioni.setup_admin_module(bot)

# gestisce il comando stat
modulo_stat.setup_stat_module(bot)

# Gestisci il comando /check
modulo_check.setup_check_module(bot)

# Gestisci il comando /canali
handle_canali_function = modulo_canali.setup_canali_module(bot)

# Funzione per la riconnessione del bot
def start_bot():
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Errore nella connessione: {e}")
            bot.stop_polling()
            time.sleep(10)  # Aspetta 10 secondi prima di riprovare

if __name__ == "__main__":
    start_bot()