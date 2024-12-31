# modulo_roy.py

import logging
import telebot
import config
import interazioni
import verifica_permessi
from database import Database
from datetime import datetime
from telebot.apihelper import ApiTelegramException


def now_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def setup_roy_module(bot: telebot.TeleBot):
    """
    Registra il comando /roy per promuovere come admin un "bot secondario"
    su tutti i canali che IL BOT CORRENTE gestisce come admin (o come preferisci).
    Esempio di sintassi: /roy @AltriBot
    """

    logging.info("Inizializzazione modulo Roy...")

    @bot.message_handler(commands=['roy'])
    def handle_roy_command(message: telebot.types.Message):
        """
        Esempio d'uso: /roy @AltroBot
        1) Verifica che l'utente che esegue /roy abbia i permessi necessari (perm >= 3).
        2) Tenta di risalire all'ID numerico di @AltroBot via bot.get_chat(...).
        3) Recupera la lista dei canali dal DB ("telegram-app", collezione "Canali")
           in cui il bot corrente è admin (o qualunque criterio tu abbia).
        4) Esegue promote_chat_member(...) su ogni canale, per aggiungere @AltroBot come admin.
        """
        ts = now_time()
        chat_id = message.chat.id
        user_id = message.from_user.id
        user_name = message.from_user.username or message.from_user.first_name

        # Parsing dell'argomento: /roy @NomeBot
        parts = message.text.strip().split(maxsplit=1)  # es.: ["@roy", "@AltriBot"]
        if len(parts) < 2:
            msg_err = bot.send_message(
                chat_id,
                "Uso corretto: /roy @NomeBot (es: /roy @AltriBot)."
            )
            interazioni.save_message(
                chat_id, "Manca l'argomento (username del bot secondario)",
                is_user=False, bot_chat_id=bot.get_me().id, 
                user_id=user_id, user_name=user_name, message_id=msg_err.message_id
            )
            return

        target_bot_username = parts[1]  # "@AltriBot"

        logging.info(f"{ts} - /roy eseguito da {user_name}({user_id}), target={target_bot_username}")

        # 1) Controllo permessi dell'utente che invoca /roy
        perm = verifica_permessi.estrai_permessi(user_id)
        if perm < 3:
            msg_err = bot.send_message(
                chat_id, 
                "Non hai i permessi per /roy (perm < 3)."
            )
            interazioni.save_message(
                chat_id, "Permessi insufficienti per /roy",
                is_user=False, bot_chat_id=bot.get_me().id,
                user_id=user_id, user_name=user_name,
                message_id=msg_err.message_id
            )
            return

        # 2) Ricava l'ID numerico di @AltriBot
        try:
            chat_info = bot.get_chat(target_bot_username)
            # chat_info è un telebot.types.Chat
            # Se l'username esiste e il tuo bot ha fatto /start su quell'utente/bot,
            # allora funziona. Altrimenti avrai un'eccezione
            target_bot_id = chat_info.id
        except ApiTelegramException as e:
            msg_err = bot.send_message(
                chat_id,
                f"Impossibile recuperare ID di {target_bot_username}:\n{e}"
            )
            interazioni.save_message(
                chat_id, f"Err get_chat {target_bot_username} - {str(e)}",
                is_user=False, bot_chat_id=bot.get_me().id,
                user_id=user_id, user_name=user_name,
                message_id=msg_err.message_id
            )
            return

        # 3) Otteniamo i canali dal DB (telegram-app, collezione "Canali")
        #    Adatta questa parte alla tua struttura e query.
        db = Database()
        my_db_app = db.get_db()  # di default => "telegram-app"
        canali_coll = my_db_app["Canali"]

        # Esempio di query: cerchiamo i canali dove "is_managed_by_my_bot"==True
        # e abbiamo un "chat_id" (l'ID telegram del canale)
        canali_da_gestire = list(canali_coll.find({"is_managed_by_my_bot": True}))
        # Oppure, se memorizzi diversamente, personalizza. 
        # Ad es. "channel" = -100..., "type"=folder, ecc. => decidi tu.

        if not canali_da_gestire:
            msg_info = bot.send_message(
                chat_id, 
                "Nessun canale trovato nel DB (Canali) da amministrare."
            )
            interazioni.save_message(
                chat_id, "Nessun canale da gestire per /roy",
                is_user=False, bot_chat_id=bot.get_me().id,
                user_id=user_id, user_name=user_name,
                message_id=msg_info.message_id
            )
            return

        success_count = 0
        fail_count = 0

        # 4) Per ogni canale trovato, tentiamo la promozione
        for c in canali_da_gestire:
            # Esempio: c["chat_id"] è l'ID numerico del canale (es. -1002340907415)
            channel_chat_id = c.get("chat_id")
            if not channel_chat_id:
                fail_count += 1
                continue

            # Tenta la "promote_chat_member"
            try:
                bot.promote_chat_member(
                    chat_id=channel_chat_id,
                    user_id=target_bot_id,
                    can_manage_chat=True,
                    can_change_info=True,
                    can_post_messages=True,
                    can_edit_messages=True,
                    can_delete_messages=True,
                    can_manage_video_chats=True,  # "can_manage_voice_chats" nelle versioni older
                    can_invite_users=True,
                    can_pin_messages=True,
                    can_promote_members=False,    # Se vuoi dare anche la facoltà di nominare altri admin
                    is_anonymous=False
                )
                success_count += 1

            except ApiTelegramException as ex:
                logging.error(f"Errore su canale={channel_chat_id} nomina {target_bot_username}: {ex}")
                fail_count += 1

        # Esito finale
        report_text = (
            f"Promozione di {target_bot_username} eseguita.\n\n"
            f"Canali totali: {len(canali_da_gestire)}\n"
            f"Successi: {success_count}\n"
            f"Fallimenti: {fail_count}"
        )
        msg_done = bot.send_message(chat_id, report_text)
        interazioni.save_message(
            chat_id, report_text, 
            is_user=False,
            bot_chat_id=bot.get_me().id,
            user_id=user_id, user_name=user_name,
            message_id=msg_done.message_id
        )

    logging.info("Modulo Roy caricato correttamente.")
