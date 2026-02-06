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


def load_config():
    with open(settings.CONFIG_FILE, "r", encoding="utf8") as f:
        return json.load(f)


def save_config():
    with open(settings.CONFIG_FILE, "w", encoding="utf8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


config = load_config()

TEXT = config["text"]
IMAGE = config["image"]
SEND_HOUR = config["hour"]
SEND_MINUTE = config["minute"]
SEND_SECOND = config["second"]


async def send_to_all_chats():
    result = await bot.get_chats()

    for chat in result.chats:
        try:
            await bot.send_message(
                chat_id=chat.chat_id,
                text=TEXT,
                attachments=IMAGE
            )
            await asyncio.sleep(0.3)
        except:
            pass


# ---------- КОМАНДЫ ----------

@dp.message_created(Command("start"))
async def start(event: MessageCreated):
    await event.message.answer(
        """
🤖 Бот рассылки

/settext ТЕКСТ — задать сообщение
/setphoto — отправь с картинкой
/settime HH:MM:SS — время рассылки
/preview — посмотреть сообщение
/sendnow — отправить сейчас

Пример:
/settime 18:30:00
"""
    )


@dp.message_created(Command("settext"))
async def set_text(event: MessageCreated):
    global TEXT

    parts = event.message.body.text.split(" ", 1)
    if len(parts) < 2:
        return await event.message.answer("Используй /settext текст")

    TEXT = parts[1]
    config["text"] = TEXT
    save_config()

    await event.message.answer("✅ Текст сохранён")


@dp.message_created(Command("setphoto"))
async def set_photo(event: MessageCreated):
    global IMAGE

    if not event.message.body.attachments:
        return await event.message.answer("Отправь команду вместе с картинкой")

    # Берём первую картинку
    img = event.message.body.attachments[0]

    # Сохраняем в JSON только attachment_id
    IMAGE = [
        {
            "type": "image",
            "attachment_id": img.attachment_id
        }
    ]

    config["image"] = IMAGE
    save_config()

    await event.message.answer("✅ Картинка сохранена")



@dp.message_created(Command("settime"))
async def set_time(event: MessageCreated):
    global SEND_HOUR, SEND_MINUTE, SEND_SECOND

    parts = event.message.body.text.split(" ", 1)

    try:
        h, m, s = map(int, parts[1].split(":"))
    except:
        return await event.message.answer("Формат: /settime 12:30:00")

    SEND_HOUR = h
    SEND_MINUTE = m
    SEND_SECOND = s

    config["hour"] = h
    config["minute"] = m
    config["second"] = s
    save_config()

    await event.message.answer(f"⏰ Время установлено {h}:{m}:{s}")


@dp.message_created(Command("preview"))
async def preview(event: MessageCreated):
    await event.message.answer(TEXT, attachments=IMAGE)


@dp.message_created(Command("sendnow"))
async def send_now(event: MessageCreated):
    await send_to_all_chats()
    await event.message.answer("🚀 Отправлено")


# ---------- ПЛАНИРОВЩИК ----------

async def scheduler():
    sent = False

    while True:
        now = datetime.now()

        if (
            now.hour == SEND_HOUR
            and now.minute == SEND_MINUTE
            and now.second == SEND_SECOND
        ):
            if not sent:
                await send_to_all_chats()
                sent = True
        else:
            sent = False

        await asyncio.sleep(1)


async def main():
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
