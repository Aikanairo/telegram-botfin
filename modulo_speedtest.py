import speedtest
import requests
import os
from telebot import types

def setup_speedtest_module(bot):
    @bot.message_handler(commands=['speedtest'])
    def run_speedtest(message):
        # Elimina il messaggio contenente il comando /speedtest
        bot.delete_message(message.chat.id, message.message_id)

        # gestione dei mess per il processo di speedtest
        msg = bot.send_message(message.chat.id, "⚡️ Avvio Speedtest")

        try:
            test = speedtest.Speedtest()
            test.get_best_server()

            msg = bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text="⚡️ Sto effettuando la misurazione del Download..")
            download_speed = test.download() / 1024 / 1024  # Convert to Mbps

            msg = bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text="⚡️ Sto effettuando la misurazione dell'Upload...")
            upload_speed = test.upload() / 1024 / 1024  # Convert to Mbps

            test.results.share()
            result = test.results.dict()
        except Exception as e:
            bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=str(e))
            return

        finish = bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text="🔄 Attendi il risultato")

        try:
            headers = {'User-Agent': 'Mozilla/5.0 ...'}
            response = requests.get(result["share"], headers=headers)
            response.raise_for_status()
            content = response.content

            path = "speedtest_result.png"
            with open(path, "wb") as file:
                file.write(content)
        except requests.exceptions.RequestException as req_err:
            bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=f"Error downloading: {req_err}")
            return

        output = f"""💡 <b>Risultato SpeedTest</b>
<b>ISP:</b> {result['client']['isp']}
<b>Country:</b> {result['client']['country']}
<u><b>Server:</b></u>
<b>Name:</b> {result['server']['name']}
<b>Country:</b> {result['server']['country']}, {result['server']['cc']}
<b>Sponsor:</b> {result['server']['sponsor']}
⚡️ <b>Ping:</b> {result['ping']}
🚀 <b>Download Speed:</b> {download_speed:.2f} Mbps
🚀 <b>Upload Speed:</b> {upload_speed:.2f} Mbps"""

        # Creazione della tastiera inline
        keyboard = types.InlineKeyboardMarkup()
        back_button = types.InlineKeyboardButton("✖️ Chiudi", callback_data="chiudi")
        keyboard.add(back_button)

        with open(path, "rb") as photo:
            bot.send_photo(chat_id=message.chat.id, photo=photo, caption=output, reply_markup=keyboard, parse_mode='HTML')
            # Elimina il messaggio contenente il comando /speedtest
            bot.delete_message(message.chat.id, finish.message_id)
        os.remove(path)
