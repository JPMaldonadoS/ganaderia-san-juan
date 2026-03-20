"""
Script de un solo uso para obtener el Chat ID de Adriana (y el tuyo).
Instrucciones:
  1. Corre este script:  python get_chat_id.py
  2. Adriana abre Telegram, busca el bot y escribe cualquier cosa
  3. Aquí aparece su Chat ID
  4. Copia ese número y ponlo en el .env como ADRIANA_CHAT_ID=...
"""
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')


async def capturar_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    nombre  = update.effective_user.full_name
    print(f"\n✅ Mensaje recibido de: {nombre}")
    print(f"   Chat ID: {chat_id}")
    print(f"\n   → Agrega esto al .env:")
    print(f"   ADRIANA_CHAT_ID={chat_id}\n")
    await update.message.reply_text(
        f"✅ ¡Hola {nombre}!\n\nTu Chat ID es: `{chat_id}`\n\n"
        "Comparte este número con Juan Pablo para activar los reportes diarios.",
        parse_mode='Markdown'
    )


def main():
    print("Esperando mensajes... (Adriana debe enviar cualquier cosa al bot)")
    print("Presiona Ctrl+C para detener.\n")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, capturar_id))
    app.run_polling()


if __name__ == '__main__':
    main()
