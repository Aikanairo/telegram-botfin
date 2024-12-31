#!/usr/bin/env python3

import telebot
import logging
import time
import traceback

# ========== CONFIG ==========
# Se hai un file config.py, carica da lì:
# import config
# TELEGRAM_TOKEN = config.TELEGRAM_TOKEN
# Oppure, per test, metti qui un token fittizio
TELEGRAM_TOKEN = "6401590878:AAE_6f-pOH4QqnPNlBSAYeALCX1EPEni6dg"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ========== BOT INIT ==========
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ESEMPIO: se hai un DB, puoi importare la logica qui
# from database import Database
# from interazioni import ...
# etc.

# Per test, una finta interazione
def save_message_test(chat_id, text, is_user, user_id, user_name, bot_chat_id, message_id):
    logging.info(f"[SAVE] chat_id={chat_id}, text={text[:30]}..., user_id={user_id}, name={user_name}, msg_id={message_id}")

# ========== STATO DI NAVIGAZIONE PER IL FILE SYSTEM ==========
viewing_state_fs = {}

# ESEMPIO: root folder e parent
ROOT_FOLDER_ID = "0000000000"
ROOT_PARENT_VALUE = ""

# Simulazione di collezione entries
# In un DB vero, userai Database().get_collection_entries()
mock_entries = [
    # La root
    {
      "id": "0000000000",    # root
      "filename": "root",
      "parentfolder": "",    # root parent -> stringa vuota
      "type": "folder",
      "state": "ACTIVE"
    },
    # Una cartella "Film"
    {
      "id": "5h7gwg5ch0",
      "filename": "Film",
      "parentfolder": "0000000000",
      "type": "folder",
      "state": "ACTIVE"
    },
    # Sottocartella "Arrival (2016)"
    {
      "id": "1o4jwv59li",
      "filename": "Arrival (2016)",
      "parentfolder": "5h7gwg5ch0",
      "type": "folder",
      "state": "ACTIVE"
    },
    # Un file dentro "Arrival (2016)"
    {
      "id": "whe0c2xo02",
      "filename": "Arrival (2016) - 4K.mkv",
      "parentfolder": "1o4jwv59li",
      "type": "video/x-matroska",
      "channel": "-1002340907415",
      "parts": [
        {"messageid": 5, "originalfilename":"...001", "index": 0},
        {"messageid": 6, "originalfilename":"...002", "index": 1}
      ],
      "state": "ACTIVE"
    }
]

# ========== FUNZIONI DI SUPPORTO DB (mock) ==========
def entries_find(query):
    """
    finto .find() su mock_entries
    """
    results = []
    for doc in mock_entries:
        # check query
        match = True
        for k,v in query.items():
            # Se v è un dict col $ne, $eq etc. semplifico
            if isinstance(v, dict):
                if "$ne" in v:
                    if doc.get(k, None) == v["$ne"]:
                        match = False
                else:
                    # Non gestisco tutti i possibili operatori per brevità
                    pass
            else:
                if doc.get(k) != v:
                    match = False
        if match:
            results.append(doc)
    return results

def entries_count(query):
    return len(entries_find(query))

def now_time():
    return time.strftime("%Y-%m-%d %H:%M:%S")

# ========== LOGICA FILE SYSTEM ==========

@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(message.chat.id, "Benvenuto! Digita /files per testare la navigazione file system.")

@bot.message_handler(commands=['files'])
def handle_file_system(message):
    ts = now_time()
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_name = message.from_user.username

    logging.info(f"[DEBUG] /files ricevuto da {user_name} (ID={user_id})")

    # Elimina /files
    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception as e:
        logging.warning(f"Non riesco a cancellare /files: {e}")

    # Manda la root
    try:
        bot.send_message(chat_id, "📂 Navigazione File System: ecco la root directory:")
        show_folders_or_files(chat_id, ROOT_FOLDER_ID, user_id, user_name, offset=0)
    except Exception as e:
        logging.error(f"Errore handle_file_system: {e}")
        bot.send_message(chat_id, f"Errore: {str(e)}")

def show_folders_or_files(chat_id, folder_id, user_id, user_name, offset=0):
    ts = now_time()
    try:
        # Cerco cartelle
        if folder_id == ROOT_FOLDER_ID:
            query_sub = {
                "parentfolder": ROOT_PARENT_VALUE,
                "type": "folder",
                "state": "ACTIVE"
            }
        else:
            query_sub = {
                "parentfolder": folder_id,
                "type": "folder",
                "state": "ACTIVE"
            }

        subfolders = entries_find(query_sub)
        total_sub = len(subfolders)

        # Paginazione simulata
        subfolders = subfolders[offset: offset+10]

        if subfolders:
            # Mostra solo cartelle
            kb = telebot.types.InlineKeyboardMarkup()
            for sf in subfolders:
                sf_name = sf.get("filename","SenzaNome")
                sf_id   = sf.get("id","")
                btn_text = f"📁 {sf_name}"
                cb_data  = f"folder_fs:{sf_id}"
                kb.add(telebot.types.InlineKeyboardButton(btn_text, callback_data=cb_data))

            # Paginazione
            nav_btns = []
            if offset>0:
                prev_off = offset-10
                nav_btns.append(telebot.types.InlineKeyboardButton("⬅️ Indietro", callback_data=f"list_fold:{prev_off}:{folder_id}"))
            if total_sub > offset+10:
                next_off = offset+10
                nav_btns.append(telebot.types.InlineKeyboardButton("Avanti ➡️", callback_data=f"list_fold:{next_off}:{folder_id}"))
            if nav_btns:
                kb.row(*nav_btns)

            if folder_id != ROOT_FOLDER_ID:
                # Tasto back
                kb.add(telebot.types.InlineKeyboardButton("🔙 Cartella precedente", callback_data=f"back_fs:{folder_id}"))

            old_id = viewing_state_fs.get(chat_id,{}).get("last_message_id_fs")
            if old_id:
                try:
                    bot.delete_message(chat_id, old_id)
                except:
                    pass

            total_pages  = (total_sub+9)//10
            curr_page    = (offset//10) + 1
            text = f"📁 Sottocartelle (pagina {curr_page}/{total_pages}):"

            new_msg = bot.send_message(chat_id, text, reply_markup=kb)
            # Salva
            viewing_state_fs.setdefault(chat_id,{})["last_message_id_fs"] = new_msg.message_id

        else:
            # Non ci sono subcartelle => mostra i file
            if folder_id == ROOT_FOLDER_ID:
                query_files = {
                    "parentfolder": ROOT_PARENT_VALUE,
                    "type": {"$ne": "folder"},
                    "state":"ACTIVE"
                }
            else:
                query_files = {
                    "parentfolder": folder_id,
                    "type": {"$ne": "folder"},
                    "state":"ACTIVE"
                }

            allfiles = entries_find(query_files)
            total_files = len(allfiles)
            files = allfiles[offset:offset+10]

            kb = telebot.types.InlineKeyboardMarkup()
            if files:
                for fdoc in files:
                    fname = fdoc.get("filename","FileSenzaNome")
                    fid   = fdoc.get("id","")
                    btn_text = f"📄 {fname}"
                    cb_data  = f"file_fs:{fid}"
                    kb.add(telebot.types.InlineKeyboardButton(btn_text, callback_data=cb_data))
            else:
                kb.add(telebot.types.InlineKeyboardButton("Nessun file", callback_data="none_fs"))

            # Pag
            nav_btns = []
            if offset>0:
                prev_off = offset-10
                nav_btns.append(telebot.types.InlineKeyboardButton("⬅️ Indietro", callback_data=f"list_file:{prev_off}:{folder_id}"))
            if total_files> offset+10:
                next_off = offset+10
                nav_btns.append(telebot.types.InlineKeyboardButton("Avanti ➡️", callback_data=f"list_file:{next_off}:{folder_id}"))
            if nav_btns:
                kb.row(*nav_btns)

            if folder_id!=ROOT_FOLDER_ID:
                kb.add(telebot.types.InlineKeyboardButton("🔙 Cartella precedente", callback_data=f"back_fs:{folder_id}"))

            old_id = viewing_state_fs.get(chat_id,{}).get("last_message_id_fs")
            if old_id:
                try:
                    bot.delete_message(chat_id, old_id)
                except:
                    pass

            tot_pages = (total_files+9)//10
            c_page    = (offset//10)+1
            text = f"📄 File (pagina {c_page}/{tot_pages}):"
            new_msg = bot.send_message(chat_id, text, reply_markup=kb)
            viewing_state_fs.setdefault(chat_id,{})["last_message_id_fs"] = new_msg.message_id

    except Exception as e:
        bot.send_message(chat_id, f"Errore show_folders_or_files: {str(e)}")
        logging.error(f"show_folders_or_files: {e}\n{traceback.format_exc()}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("folder_fs:"))
def handle_folder_fs(call):
    try:
        _, folder_id = call.data.split(":")
        show_folders_or_files(call.message.chat.id, folder_id, call.from_user.id, call.from_user.username)
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Err folder_fs: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("list_fold:"))
def handle_list_fold(call):
    try:
        _, offset_str, folder_id = call.data.split(":")
        offset = int(offset_str)
        show_folders_or_files(call.message.chat.id, folder_id, call.from_user.id, call.from_user.username, offset=offset)
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Err list_fold: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("list_file:"))
def handle_list_file(call):
    try:
        _, offset_str, folder_id = call.data.split(":")
        offset = int(offset_str)
        show_folders_or_files(call.message.chat.id, folder_id, call.from_user.id, call.from_user.username, offset=offset)
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Err list_file: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("file_fs:"))
def handle_file_fs(call):
    try:
        _, file_id = call.data.split(":")
        doc = None
        for x in mock_entries:
            if x.get("id") == file_id and x.get("type")!="folder" and x.get("state")=="ACTIVE":
                doc = x
                break
        if doc is None:
            bot.answer_callback_query(call.id, "File non trovato.")
            return
        create_file_keyboard(call.message.chat.id, doc, call.from_user.id, call.from_user.username)
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Err file_fs: {str(e)}")

def create_file_keyboard(chat_id, doc_file, user_id, user_name):
    file_id  = doc_file["id"]
    fname    = doc_file.get("filename","(no name)")
    channel  = doc_file.get("channel","")
    parts    = doc_file.get("parts", [])

    text = f"📄 *{fname}*\n\nParti: {len(parts)}"
    kb   = telebot.types.InlineKeyboardMarkup()
    if parts:
        for i,p in enumerate(parts):
            cb_data = f"download_part_fs:{file_id}:{i}"
            btext   = f"Scarica parte {i+1}"
            kb.add(telebot.types.InlineKeyboardButton(btext, callback_data=cb_data))

    kb.add(telebot.types.InlineKeyboardButton("🔙 Torna a /files", callback_data="canali_fs"))

    # Cancella
    old_id = viewing_state_fs.get(chat_id,{}).get("last_message_id_fs")
    if old_id:
        try:
            bot.delete_message(chat_id, old_id)
        except:
            pass

    sent = bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=kb)
    viewing_state_fs.setdefault(chat_id,{})["last_message_id_fs"] = sent.message_id

@bot.callback_query_handler(func=lambda call: call.data.startswith("download_part_fs:"))
def handle_download_part_fs(call):
    try:
        _, file_id, part_str = call.data.split(":")
        part_idx = int(part_str)
        doc = None
        for x in mock_entries:
            if x.get("id")==file_id and x.get("type","folder")!="folder" and x.get("state")=="ACTIVE":
                doc = x
                break
        if doc is None:
            bot.answer_callback_query(call.id, "File non trovato.")
            return
        channel_id = doc.get("channel","")
        parts = doc.get("parts",[])
        if part_idx<0 or part_idx>=len(parts):
            bot.answer_callback_query(call.id, "Parte non valida.")
            return

        msg_id = parts[part_idx].get("messageid", None)
        if not msg_id:
            bot.answer_callback_query(call.id, "Manca messageid.")
            return

        # ESEMPIO: inoltro/copia
        # Se fosse un canale esistente e un messageID reale
        # fwd = bot.copy_message(call.message.chat.id, channel_id, msg_id)
        # Ma qui non avviene nulla perché è mock
        bot.answer_callback_query(call.id, f"Parte {part_idx+1} inoltrata (mock).")

    except Exception as e:
        bot.answer_callback_query(call.id, f"Err download_part_fs: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "canali_fs")
def handle_canali_fs(call):
    # In questo esempio, ricarichiamo la root
    try:
        old_id = viewing_state_fs.get(call.message.chat.id,{}).get("last_message_id_fs")
        if old_id:
            bot.delete_message(call.message.chat.id, old_id)
    except:
        pass
    handle_file_system(call.message)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("back_fs:"))
def handle_back_fs(call):
    try:
        # ignoriamo il vero meccanismo "parentfolder" e ricarichiamo la root
        old_msgs = viewing_state_fs.get(call.message.chat.id,{})
        if "last_message_id_fs" in old_msgs:
            try:
                bot.delete_message(call.message.chat.id, old_msgs["last_message_id_fs"])
            except:
                pass
        # ricarica root
        handle_file_system(call.message)
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, str(e))

def main():
    logging.info("Avvio BOT...")
    bot.infinity_polling()

if __name__ == "__main__":
    main()
