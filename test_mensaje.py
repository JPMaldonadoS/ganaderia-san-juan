import asyncio, sys
sys.path.insert(0, '/home/rafamaldonadojimenez/ganaderia-san-juan/bot_telegram')
import config
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from zoneinfo import ZoneInfo

async def test():
    bot = Bot(config.TOKEN)
    hoy_display = datetime.now(ZoneInfo('America/Bogota')).strftime('%d/%m/%Y')
    msg = (
        f"🐄 *Hola Adriana\\! Es hora del reporte — {hoy_display}*\n\n"
        "Son solo unas pregunticas, toca los botones para responder\\.\n\n"
        "_Si en algún momento te equivocas, escribe_ /corregir"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Comenzar reporte", callback_data='iniciar_auto')]])
    await bot.send_message(chat_id=config.ADRIANA_CHAT_ID, text=msg, parse_mode='MarkdownV2', reply_markup=kb)
    print('OK - mensaje enviado sin error')

asyncio.run(test())
