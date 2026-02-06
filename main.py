import asyncio
import logging
import json
from datetime import datetime

from maxapi import Bot, Dispatcher
from maxapi.types import MessageCreated, Command

from core.config import settings

logging.basicConfig(level=logging.INFO)

bot = Bot(token=settings.TOKEN)
dp = Dispatcher()

# Загружаем конфиг
def load_config():
    with open(settings.CONFIG_FILE, "r", encoding="utf8") as f:
        return json.load(f)

def save_config():
    with open(settings.CONFIG_FILE, "w", encoding="utf8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

config = load_config()
MESSAGE_URL = config.get("message_url", None)
SEND_HOUR = config.get("hour", 0)
SEND_MINUTE = config.get("minute", 0)
SEND_SECOND = config.get("second", 0)


# ---------------- Команды бота ---------------- #

@dp.message_created(Command("start"))
async def start(event: MessageCreated):
    await event.message.answer(
        """
🤖 Бот рассылки через URL сообщений

/settext ТЕКСТ + картинка (опционально) — задаёт сообщение для рассылки и сохраняет его URL
/settime HH:MM:SS — время рассылки
/preview — посмотреть сообщение
/sendnow — отправить сейчас

Пример:
/settext Привет! (отправь фото вместе с текстом)
"""
    )


from maxapi.methods.get_message import GetMessage
from maxapi.types import MessageCreated, Command
from maxapi.types.attachments.image import Image

SAVED_MESSAGE = None

@dp.message_created(Command("settext"))
async def set_text(event: MessageCreated):
    global SAVED_MESSAGE

    # Текст
    parts = event.message.body.text.split(" ", 1)
    text = parts[1].strip() if len(parts) > 1 else ""

    # Изображения
    attachments = []
    for att in event.message.body.attachments:
        if isinstance(att, Image):
            attachments.append(att)

    if not text and not attachments:
        return await event.message.answer("❌ Сообщение должно содержать текст или картинку")

    # Сохраняем в глобальную переменную
    SAVED_MESSAGE = {
        "text": text,
        "attachments": attachments
    }

    # Сохраняем только текст в config (чтобы JSON не ломался)
    config["saved_message"] = {
        "text": text
    }
    save_config()

    await event.message.answer("✅ Сообщение с текстом и картинками сохранено для рассылки")



@dp.message_created(Command("preview"))
async def preview(event: MessageCreated):
    if not SAVED_MESSAGE:
        return await event.message.answer("❌ Сообщение для рассылки не задано")

    await event.message.answer(
        text=SAVED_MESSAGE.get("text", None),
        attachments=SAVED_MESSAGE.get("attachments", None)
    )

@dp.message_created(Command("sendnow"))
async def send_now(event: MessageCreated):
    await send_to_all_chats()
    await event.message.answer("🚀 Сообщение разослано")


@dp.message_created(Command("settime"))
async def set_time(event: MessageCreated):
    global SEND_HOUR, SEND_MINUTE, SEND_SECOND
    parts = event.message.body.text.split(" ", 1)
    try:
        h, m, s = map(int, parts[1].split(":"))
    except:
        return await event.message.answer("Формат: /settime 12:30:00")

    SEND_HOUR, SEND_MINUTE, SEND_SECOND = h, m, s
    config["hour"], config["minute"], config["second"] = h, m, s
    save_config()
    await event.message.answer(f"⏰ Время рассылки установлено на {h}:{m}:{s}")


# ---------------- Отправка сообщений по URL ---------------- #

async def send_to_all_chats():
    if not SAVED_MESSAGE:
        logging.warning("❌ Сообщение для рассылки не задано")
        return

    result = await bot.get_chats()
    text = SAVED_MESSAGE.get("text", "")
    attachments = SAVED_MESSAGE.get("attachments", [])

    for chat in result.chats:
        try:
            await bot.send_message(
                chat_id=chat.chat_id,
                text=text if text else None,
                attachments=attachments if attachments else None
            )
            await asyncio.sleep(0.3)
        except Exception as e:
            logging.warning(f"Не удалось отправить в чат {chat.chat_id}: {e}")

# ---------------- Планировщик ---------------- #

async def scheduler():
    sent = False
    while True:
        now = datetime.now()
        if (now.hour, now.minute, now.second) == (SEND_HOUR, SEND_MINUTE, SEND_SECOND):
            if not sent:
                await send_to_all_chats()
                sent = True
        else:
            sent = False
        await asyncio.sleep(1)


# ---------------- Главная функция ---------------- #

async def main():
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
