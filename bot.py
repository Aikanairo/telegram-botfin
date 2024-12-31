# bot.py

import telebot
import logging
import time

import config
import modulo_stat
import modulo_check
import modulo_canali
import modulo_file_sistem  # <-- Import del modulo con la logica FS
import modulo_roy
import modulo_speedtest
import modulo_infousers
import modulo_registrazioni
import modulo_admin_registrazioni
import verifica_permessi
import interazioni

from telebot import apihelper

# Configura il logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

# Inizializza il bot con il token dal file config.py
bot = telebot.TeleBot(config.TELEGRAM_TOKEN)
modulo_file_sistem.setup_file_sistem_module(bot)
# Registra il modulo Roy
modulo_roy.setup_roy_module(bot)

# ------------------------------------------------------------
# Gestisci il comando /start
# ------------------------------------------------------------
@bot.message_handler(commands=['start'])
def handle_start(message):
    user = message.from_user
    user_id = user.id
    user_name = user.username or user.first_name

    # Esempio di permessi
    permesso = verifica_permessi.estrai_permessi(user_id)

    # Differenziazione messaggi in base ai permessi
    if permesso >= 3:
        sent_message = bot.send_message(
            message.chat.id,
            f"Benvenuto, {user.first_name} (admin avanzato)! \n"
            "<b>Comandi</b>:\n"
            "/canali - Lista delle cartelle\n"
            "/files - Lista del file system\n"
            "/stat - Consultare le statistiche\n"
            "/speedtest - Effettua uno speedtest della tua connessione\n"
            "/registrazione - Per consultare i file\n"
            "/diventa_premium - Per avere accesso illimitato\n\n"
            "<b>Amministrazioni:</b>\n"
            "/admin_registrazioni - Per accedere alle funzioni da admin\n"
            "/check - Verifica episodi mancanti",
            parse_mode="HTML"
        )
    elif permesso == 1:
        sent_message = bot.send_message(
            message.chat.id,
            f"Benvenuto, {user.first_name} (admin)! \n"
            "<b>Comandi</b>:\n"
            "/canali - Lista delle cartelle\n"
            "/files - Lista del file system\n"
            "/stat - Consultare le statistiche\n"
            "/speedtest - Effettua uno speedtest della tua connessione\n"
            "/diventa_premium - Effettua richiesta per avere accesso illimitato ai file",
            parse_mode="HTML"
        )
    else:
        sent_message = bot.send_message(
            message.chat.id,
            f"Benvenuto, {user.first_name}! \n"
            "<b>Comandi</b>:\n"
            "/canali - Lista delle cartelle\n"
            "/files - Lista del file system\n"
            "/stat - Consulta le statistiche\n"
            "/speedtest - Effettua uno speedtest della tua connessione\n"
            "/registrazione - Per consultare i file\n"
            "/diventa_premium - Effettua richiesta per avere accesso illimitato ai file",
            parse_mode="HTML"
        )

    # Elimina il messaggio originale con /start
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except telebot.apihelper.ApiException as e:
        logging.warning(f"Errore eliminando /start: {e}")

    # Salva il messaggio inviato nel database
    try:
        interazioni.save_message(
            message.chat.id, "/start", is_user=False,
            bot_chat_id=bot.get_me().id, user_id=user_id,
            user_name=user_name, message_id=sent_message.message_id
        )
    except Exception as e:
        logging.error(f"Errore salvando il messaggio /start: {e}")

# ------------------------------------------------------------
# Gestisci il comando /files
# ------------------------------------------------------------
@bot.message_handler(commands=['files'])
def handle_files(message):
    """
    Handler del comando /files.
    Chiama la logica definita nel modulo_file_sistem.
    """
    print("DEBUG: /files scattato in bot.py!")
    logging.info("DEBUG: /files scattato in bot.py!")
    modulo_file_sistem.handle_files_logic(bot, message)

# ------------------------------------------------------------
# Altri comandi
# ------------------------------------------------------------
@bot.message_handler(commands=['getid'])
def get_id(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, f"L'ID di questa chat è {chat_id}.")

@bot.message_handler(commands=['registrazione'])
def handle_registrazione(message):
    modulo_registrazioni.setup_registrazioni_module(message, bot, "utente")

@bot.message_handler(commands=['diventa_premium'])
def handle_diventa_premium(message):
    modulo_registrazioni.setup_registrazioni_module(message, bot, "utente premium")

# ------------------------------------------------------------
# Setup di altri moduli
# ------------------------------------------------------------
modulo_speedtest.setup_speedtest_module(bot)
modulo_admin_registrazioni.setup_admin_module(bot)
modulo_stat.setup_stat_module(bot)
modulo_check.setup_check_module(bot)
modulo_canali.setup_canali_module(bot)

# (NON CHIAMARE "setup_file_sistem_module(bot)" perché non esiste più.)
# modulo_file_sistem.setup_file_sistem_module(bot)   <-- Rimosso

# ------------------------------------------------------------
# Callback Query Handlers per File System (redirect)
# ------------------------------------------------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith("list_fold:"))
def handle_list_folders(call):
    print("DEBUG: handle_list_folders callback scattato in bot.py!")
    logging.info("DEBUG: handle_list_folders callback scattato in bot.py!")
    try:
        _, offset_str, folder_id = call.data.split(":")
        offset = int(offset_str)
        modulo_file_sistem.handle_list_fold_callback(bot, call, offset, folder_id)
        bot.answer_callback_query(call.id)
    except Exception as e:
        logging.error(f"handle_list_folders error: {e}")
        bot.answer_callback_query(call.id, f"Errore list_folders: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("list_file:"))
def handle_list_files(call):
    print("DEBUG: handle_list_files callback scattato in bot.py!")
    logging.info("DEBUG: handle_list_files callback scattato in bot.py!")
    try:
        _, offset_str, folder_id = call.data.split(":")
        offset = int(offset_str)
        modulo_file_sistem.handle_list_file_callback(bot, call, offset, folder_id)
        bot.answer_callback_query(call.id)
    except Exception as e:
        logging.error(f"handle_list_files error: {e}")
        bot.answer_callback_query(call.id, f"Errore list_files: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("folder_fs:"))
def handle_folder_fs(call):
    print("DEBUG: handle_folder_fs callback scattato in bot.py!")
    logging.info("DEBUG: handle_folder_fs callback scattato in bot.py!")
    try:
        _, folder_id = call.data.split(":")
        modulo_file_sistem.handle_folder_fs_callback(bot, call, folder_id)
        bot.answer_callback_query(call.id)
    except Exception as e:
        logging.error(f"handle_folder_fs error: {e}")
        bot.answer_callback_query(call.id, f"Errore folder_fs: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("file_fs:"))
def handle_file_fs(call):
    print("DEBUG: handle_file_fs callback scattato in bot.py!")
    logging.info("DEBUG: handle_file_fs callback scattato in bot.py!")
    try:
        _, file_id = call.data.split(":")
        modulo_file_sistem.handle_file_fs_callback(bot, call, file_id)
        bot.answer_callback_query(call.id)
    except Exception as e:
        logging.error(f"handle_file_fs error: {e}")
        bot.answer_callback_query(call.id, f"Errore file_fs: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("download_part_fs:"))
def handle_download_part_fs(call):
    print("DEBUG: handle_download_part_fs callback scattato in bot.py!")
    logging.info("DEBUG: handle_download_part_fs callback scattato in bot.py!")
    try:
        _, file_id, part_str = call.data.split(":")
        part_idx = int(part_str)
        modulo_file_sistem.handle_download_part_fs_callback(bot, call, file_id, part_idx)
        bot.answer_callback_query(call.id)
    except Exception as e:
        logging.error(f"handle_download_part_fs error: {e}")
        bot.answer_callback_query(call.id, f"Errore download_part_fs: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("back_fs:"))
def handle_back_fs(call):
    print("DEBUG: handle_back_fs callback scattato in bot.py!")
    logging.info("DEBUG: handle_back_fs callback scattato in bot.py!")
    try:
        _, folder_id = call.data.split(":")
        modulo_file_sistem.handle_back_fs_callback(bot, call, folder_id)
        bot.answer_callback_query(call.id)
    except Exception as e:
        logging.error(f"handle_back_fs error: {e}")
        bot.answer_callback_query(call.id, f"Errore back_fs: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "canali_fs")
def handle_canali_fs(call):
    print("DEBUG: handle_canali_fs callback scattato in bot.py!")
    logging.info("DEBUG: handle_canali_fs callback scattato in bot.py!")
    try:
        modulo_file_sistem.handle_canali_fs_callback(bot, call)
        bot.answer_callback_query(call.id)
    except Exception as e:
        logging.error(f"handle_canali_fs error: {e}")
        bot.answer_callback_query(call.id, f"Errore canali_fs: {str(e)}")

# ------------------------------------------------------------
# Funzione per la riconnessione del bot
# ------------------------------------------------------------
def start_bot():
    while True:
        try:
            logging.info("Avvio BOT...")
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(f"Errore nella connessione: {e}")
            time.sleep(10)

if __name__ == "__main__":
    start_bot()
