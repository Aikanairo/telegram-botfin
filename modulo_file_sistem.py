import telebot
import logging
import os
import time
import requests

import config
import verifica_permessi
import interazioni
import modulo_infousers
from database import Database
from bson import ObjectId
from telebot import types, apihelper
from fuzzywuzzy import fuzz
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Dizionario globale per lo stato di visualizzazione (es. ultimo messaggio inviato)
viewing_state_fs = {}

# Costante per la "root" (se i documenti root in DB hanno 'id'="0000000000")
ROOT_FOLDER_ID = "0000000000"

def now_time():
    """Restituisce data/ora corrente come stringa."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def setup_file_sistem_module(bot: telebot.TeleBot):
    """
    Registra:
      - L'handler /files
      - Tutti i callback per la navigazione (cartelle, file, parti, back, ecc.)
    Una volta chiamato, quando digiti /files verrà eseguito l'handler definito qui.
    """
    logging.info("Inizializzazione del modulo File System gerarchico...")

    database = Database()
    entries_coll = database.get_collection_entries()

    # ----------------------------------------------------------------------
    # Handler /files
    # ----------------------------------------------------------------------
    @bot.message_handler(commands=['files'])
    def handle_file_system(message):
        """
        Quando l'utente digita /files:
         1) Eliminare il messaggio /files
         2) Mostrare la root directory (folder_id=ROOT_FOLDER_ID)
        """
        ts = now_time()
        chat_id = message.chat.id
        user_id = message.from_user.id
        user_name = message.from_user.username or message.from_user.first_name

        print(f"DEBUG: /files ricevuto da {user_name} (ID={user_id})")
        logging.info(f"{ts} - /files ricevuto da {user_name}({user_id})")

        # Elimina il messaggio /files
        try:
            bot.delete_message(chat_id, message.message_id)
        except Exception as e:
            logging.error(f"{ts} - Errore eliminando messaggio /files: {e}")

        # Manda messaggio e mostra root
        try:
            bot.send_message(chat_id, "📂 Navigazione File System: ecco la ROOT directory:")
            show_folders_or_files(chat_id, ROOT_FOLDER_ID, user_id, user_name, offset=0)
        except Exception as e:
            logging.error(f"{ts} - Errore handle_file_system: {e}")
            bot.send_message(chat_id, f"Errore /files: {str(e)}")


    # ----------------------------------------------------------------------
    # show_folders_or_files
    # ----------------------------------------------------------------------
    def show_folders_or_files(chat_id, folder_id, user_id, user_name, offset=0):
        """
        Se la cartella folder_id ha sub-cartelle (type=folder) -> le mostriamo,
        altrimenti -> mostriamo i file (type != folder).
        """
        ts = now_time()

        try:
            # Se siamo in root, cerco subcartelle con parentfolder="0000000000"
            if folder_id == ROOT_FOLDER_ID:
                query_sub = {
                    "parentfolder": "0000000000",  # root
                    "type": "folder",
                    "state": "ACTIVE"
                }
            else:
                query_sub = {
                    "parentfolder": folder_id,
                    "type": "folder",
                    "state": "ACTIVE"
                }

            subfolders = list(entries_coll.find(query_sub).sort("filename", 1).skip(offset).limit(10))
            total_subfolders = entries_coll.count_documents(query_sub)

            if subfolders:
                # Abbiamo sub-cartelle -> mostriamo SOLO le cartelle
                kb = InlineKeyboardMarkup()

                for sf in subfolders:
                    sf_name = sf.get("filename", "SenzaNome")
                    sf_id   = sf.get("id", "")
                    btn_text= f"📁 {sf_name}"
                    cb_data = f"folder_fs:{sf_id}"
                    kb.add(InlineKeyboardButton(btn_text, callback_data=cb_data))

                # Paginazione cartelle
                nav_btns = []
                if offset > 0:
                    prev_offset = offset - 10
                    nav_btns.append(InlineKeyboardButton("⬅️ Indietro", callback_data=f"list_fold:{prev_offset}:{folder_id}"))
                if total_subfolders > offset + 10:
                    next_offset = offset + 10
                    nav_btns.append(InlineKeyboardButton("Avanti ➡️", callback_data=f"list_fold:{next_offset}:{folder_id}"))
                if nav_btns:
                    kb.row(*nav_btns)

                # Se non è root, aggiungi tasto "Cartella precedente"
                if folder_id != ROOT_FOLDER_ID:
                    kb.add(InlineKeyboardButton("🔙 Cartella precedente", callback_data=f"back_fs:{folder_id}"))

                # Elimina eventuale vecchio messaggio
                old_msg_id = viewing_state_fs.get(chat_id, {}).get("last_message_id_fs")
                if old_msg_id:
                    try:
                        bot.delete_message(chat_id, old_msg_id)
                    except apihelper.ApiException as e:
                        if "message to delete not found" not in str(e):
                            logging.error(f"{ts} - Errore delete old msg FS: {e}")

                # Calcolo pagine
                total_pages  = (total_subfolders + 9)//10
                current_page = (offset//10)+1
                text = f"📁 Sottocartelle (pagina {current_page}/{total_pages}):"

                # Invia
                new_msg = bot.send_message(chat_id, text, reply_markup=kb)
                # Salva
                interazioni.save_message(chat_id, text, is_user=False, user_id=user_id, user_name=user_name,
                                         bot_chat_id=bot.get_me().id, message_id=new_msg.message_id)
                # Aggiorna stato
                viewing_state_fs.setdefault(chat_id, {})["last_message_id_fs"] = new_msg.message_id

                logging.info(f"{ts} - {user_name}({user_id}) -> subcartelle di {folder_id}")
            else:
                # Non ci sono subcartelle, -> mostriamo i FILE
                if folder_id == ROOT_FOLDER_ID:
                    query_files = {
                        "parentfolder": "0000000000",
                        "type": {"$ne": "folder"},
                        "state": "ACTIVE"
                    }
                else:
                    query_files = {
                        "parentfolder": folder_id,
                        "type": {"$ne": "folder"},
                        "state": "ACTIVE"
                    }

                files = list(entries_coll.find(query_files).sort("filename", 1).skip(offset).limit(10))
                total_files = entries_coll.count_documents(query_files)

                kb = InlineKeyboardMarkup()
                if files:
                    for docf in files:
                        fname = docf.get("filename", "FileSenzaNome")
                        fid   = docf.get("id", "")
                        cb_data = f"file_fs:{fid}"
                        kb.add(InlineKeyboardButton(f"📄 {fname}", callback_data=cb_data))
                else:
                    kb.add(InlineKeyboardButton("Nessun file", callback_data="none_fs"))

                # Paginazione file
                nav_btns = []
                if offset>0:
                    prev_off = offset-10
                    nav_btns.append(InlineKeyboardButton("⬅️ Indietro", callback_data=f"list_file:{prev_off}:{folder_id}"))
                if total_files > offset+10:
                    next_off = offset+10
                    nav_btns.append(InlineKeyboardButton("Avanti ➡️", callback_data=f"list_file:{next_off}:{folder_id}"))
                if nav_btns:
                    kb.row(*nav_btns)

                # Se non è root, tasto "Cartella precedente"
                if folder_id != ROOT_FOLDER_ID:
                    kb.add(InlineKeyboardButton("🔙 Cartella precedente", callback_data=f"back_fs:{folder_id}"))

                # Elimina vecchio msg
                old_msg_id = viewing_state_fs.get(chat_id, {}).get("last_message_id_fs")
                if old_msg_id:
                    try:
                        bot.delete_message(chat_id, old_msg_id)
                    except apihelper.ApiException as e:
                        if "message to delete not found" not in str(e):
                            logging.error(f"{ts} - Errore old msg FS: {e}")

                # Calcolo pagine
                total_pages  = (total_files + 9)//10
                current_page = (offset//10)+1
                text = f"📄 File (pagina {current_page}/{total_pages}):"

                new_msg = bot.send_message(chat_id, text, reply_markup=kb)
                interazioni.save_message(chat_id, text, is_user=False, user_id=user_id, user_name=user_name,
                                         bot_chat_id=bot.get_me().id, message_id=new_msg.message_id)
                viewing_state_fs.setdefault(chat_id, {})["last_message_id_fs"] = new_msg.message_id

                logging.info(f"{ts} - {user_name}({user_id}) -> file di {folder_id}")

        except Exception as e:
            err_msg = bot.send_message(chat_id, f"Errore show_folders_or_files: {e}")
            interazioni.save_message(chat_id, str(e), is_user=False, user_id=user_id, user_name=user_name,
                                     bot_chat_id=bot.get_me().id, message_id=err_msg.message_id)
            logging.error(f"{ts} - show_folders_or_files: {e}")


    # ----------------------------------------------------------------------
    # Callback: list_fold
    # ----------------------------------------------------------------------
    @bot.callback_query_handler(func=lambda call: call.data.startswith("list_fold:"))
    def handle_list_folders_page(call):
        ts = now_time()
        chat_id  = call.message.chat.id
        user_id  = call.from_user.id
        user_name= call.from_user.username or call.from_user.first_name

        try:
            _, off_str, folder_id = call.data.split(":")
            offset = int(off_str)
            show_folders_or_files(chat_id, folder_id, user_id, user_name, offset=offset)
            bot.answer_callback_query(call.id)
        except Exception as e:
            logging.error(f"{ts} - handle_list_folders_page: {e}")
            bot.answer_callback_query(call.id, "Errore list_folders_page")

    # ----------------------------------------------------------------------
    # Callback: list_file
    # ----------------------------------------------------------------------
    @bot.callback_query_handler(func=lambda call: call.data.startswith("list_file:"))
    def handle_list_files_page(call):
        ts = now_time()
        chat_id  = call.message.chat.id
        user_id  = call.from_user.id
        user_name= call.from_user.username or call.from_user.first_name

        try:
            _, off_str, folder_id = call.data.split(":")
            offset = int(off_str)
            show_folders_or_files(chat_id, folder_id, user_id, user_name, offset=offset)
            bot.answer_callback_query(call.id)
        except Exception as e:
            logging.error(f"{ts} - handle_list_files_page: {e}")
            bot.answer_callback_query(call.id, "Errore list_files_page")

    # ----------------------------------------------------------------------
    # Callback: folder_fs
    # ----------------------------------------------------------------------
    @bot.callback_query_handler(func=lambda call: call.data.startswith("folder_fs:"))
    def handle_folder_fs(call):
        ts = now_time()
        chat_id  = call.message.chat.id
        user_id  = call.from_user.id
        user_name= call.from_user.username or call.from_user.first_name

        try:
            _, folder_id = call.data.split(":")
            show_folders_or_files(chat_id, folder_id, user_id, user_name, offset=0)
            bot.answer_callback_query(call.id)
        except Exception as e:
            logging.error(f"{ts} - handle_folder_fs: {e}")
            bot.answer_callback_query(call.id, "Errore folder_fs")

    # ----------------------------------------------------------------------
    # Callback: file_fs
    # ----------------------------------------------------------------------
    @bot.callback_query_handler(func=lambda call: call.data.startswith("file_fs:"))
    def handle_file_fs(call):
        ts = now_time()
        chat_id  = call.message.chat.id
        user_id  = call.from_user.id
        user_name= call.from_user.username or call.from_user.first_name

        try:
            _, file_id = call.data.split(":")
            doc = entries_coll.find_one({"id": file_id, "type": {"$ne": "folder"}, "state": "ACTIVE"})
            if not doc:
                bot.answer_callback_query(call.id, "File non trovato o inattivo.")
                return

            create_file_keyboard(chat_id, doc, user_id, user_name)
            bot.answer_callback_query(call.id)
        except Exception as e:
            logging.error(f"{ts} - handle_file_fs: {e}")
            bot.answer_callback_query(call.id, "Errore file_fs")

    def create_file_keyboard(chat_id, doc_file, user_id, user_name):
        ts = now_time()
        file_id   = doc_file["id"]
        filename  = doc_file.get("filename", "(SenzaNome)")
        channel   = doc_file.get("channel", "")
        parts     = doc_file.get("parts", [])

        text = f"📄 *{filename}*\n\nParti: {len(parts)}"

        kb = InlineKeyboardMarkup()
        if parts:
            for i, part in enumerate(parts):
                cb_data  = f"download_part_fs:{file_id}:{i}"
                btn_text = f"Scarica parte {i+1}"
                kb.add(InlineKeyboardButton(btn_text, callback_data=cb_data))

        # Tasto "Torna a /files"
        kb.add(InlineKeyboardButton("🔙 Torna a /files", callback_data="canali_fs"))

        # Elimina eventuale msg precedente
        old_id = viewing_state_fs.get(chat_id, {}).get("last_message_id_fs")
        if old_id:
            try:
                bot.delete_message(chat_id, old_id)
            except apihelper.ApiException as e:
                if "message to delete not found" not in str(e):
                    logging.error(f"{ts} - create_file_keyboard old msg: {e}")

        sent = bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=kb)
        interazioni.save_message(chat_id, text, is_user=False,
                                 user_id=user_id, user_name=user_name,
                                 bot_chat_id=bot.get_me().id, message_id=sent.message_id)
        viewing_state_fs.setdefault(chat_id, {})["last_message_id_fs"] = sent.message_id

        logging.info(f"{ts} -> create_file_keyboard (file={file_id})")

    # ----------------------------------------------------------------------
    # Callback: download_part_fs
    # ----------------------------------------------------------------------
    @bot.callback_query_handler(func=lambda call: call.data.startswith("download_part_fs:"))
    def handle_download_part_fs(call):
        ts = now_time()
        chat_id  = call.message.chat.id
        user_id  = call.from_user.id
        user_name= call.from_user.username or call.from_user.first_name

        try:
            _, file_id, part_index_str = call.data.split(":")
            part_index = int(part_index_str)

            doc = entries_coll.find_one({"id": file_id, "type": {"$ne": "folder"}, "state": "ACTIVE"})
            if not doc:
                bot.answer_callback_query(call.id, "File non trovato o inattivo.")
                return

            channel_id = doc.get("channel", "")
            parts = doc.get("parts", [])
            if part_index<0 or part_index>=len(parts):
                bot.answer_callback_query(call.id, "Parte non valida.")
                return

            part = parts[part_index]
            msg_id = part.get("messageid", None)
            if not msg_id or not channel_id:
                bot.answer_callback_query(call.id, "Dati non validi per download.")
                return

            # copy_message
            fwd = bot.copy_message(chat_id, channel_id, msg_id)
            interazioni.save_message(chat_id, "File inoltrato (parte)", is_user=False,
                                     user_id=user_id, user_name=user_name,
                                     bot_chat_id=bot.get_me().id, message_id=fwd.message_id)

            bot.answer_callback_query(call.id, f"Parte {part_index+1} inoltrata.")
            logging.info(f"{ts} - {user_name} scarica parte {part_index+1} del file {file_id}")
        except Exception as e:
            logging.error(f"{ts} - handle_download_part_fs: {e}")
            bot.answer_callback_query(call.id, f"Errore: {str(e)}")

    # ----------------------------------------------------------------------
    # Callback: back_fs
    # ----------------------------------------------------------------------
    @bot.callback_query_handler(func=lambda call: call.data.startswith("back_fs:"))
    def handle_back_fs(call):
        ts = now_time()
        chat_id  = call.message.chat.id
        user_id  = call.from_user.id
        user_name= call.from_user.username or call.from_user.first_name

        parts = call.data.split(":")
        if len(parts)<2:
            new_folder_id = ROOT_FOLDER_ID
        else:
            new_folder_id = parts[1]

        # Cancella i vecchi messaggi
        old_msgs = interazioni.select_cronologia_messaggi(user_id, user_name)
        for mid in old_msgs:
            try:
                bot.delete_message(chat_id, mid)
            except apihelper.ApiException as e:
                if "message to delete not found" not in str(e):
                    logging.error(f"{ts} - handle_back_fs: {e}")

        try:
            interazioni.attivazione_pulsante_back(user_id, user_name)
        except:
            pass

        # Ricarichiamo la cartella "new_folder_id"
        show_folders_or_files(chat_id, new_folder_id, user_id, user_name, offset=0)
        bot.answer_callback_query(call.id)

    # ----------------------------------------------------------------------
    # Callback: canali_fs
    # ----------------------------------------------------------------------
    @bot.callback_query_handler(func=lambda call: call.data == "canali_fs")
    def handle_back_to_files(call):
        """
        Tornare alla root (/files). Richiama handle_file_system(call.message).
        """
        ts = now_time()
        chat_id  = call.message.chat.id
        user_id  = call.from_user.id
        user_name= call.from_user.username or call.from_user.first_name

        # Cancella i vecchi messaggi
        old_msgs = interazioni.select_cronologia_messaggi(user_id, user_name)
        for mid in old_msgs:
            try:
                bot.delete_message(chat_id, mid)
            except apihelper.ApiException as e:
                if "message to delete not found" not in str(e):
                    logging.error(f"{ts} - handle_back_to_files: {e}")

        try:
            interazioni.attivazione_pulsante_back(user_id, user_name)
        except:
            pass

        # Richiamiamo la logica /files
        fake_message = call.message  # Simuliamo
        handle_file_system(fake_message)
        bot.answer_callback_query(call.id)

    logging.info("Modulo File System caricato correttamente.")
    print("DEBUG: Modulo File System caricato correttamente.")
