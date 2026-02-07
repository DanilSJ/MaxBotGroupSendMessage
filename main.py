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

SEND_TIMES = config.get("times", [])



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
    global SEND_TIMES

    parts = event.message.body.text.split(" ", 1)

    if len(parts) < 2:
        return await event.message.answer("Формат:\n/settime 12:00:00 15:30:00\nили\n/settime 0")

    # Сброс
    if parts[1].strip() == "0":
        SEND_TIMES = []
        config["times"] = []
        save_config()
        return await event.message.answer("🗑 Расписание очищено")

    raw_times = parts[1].split()

    if len(raw_times) > 7:
        return await event.message.answer("❌ Максимум 7 времён")

    parsed = []

    try:
        for t in raw_times:
            h, m, s = map(int, t.split(":"))
            parsed.append((h, m, s))
    except:
        return await event.message.answer("❌ Формат времени: HH:MM:SS")

    SEND_TIMES = parsed
    config["times"] = parsed
    save_config()

    text = "\n".join([f"{h:02}:{m:02}:{s:02}" for h, m, s in parsed])

    await event.message.answer(f"⏰ Установлены времена:\n{text}")


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
    sent_today = set()

    while True:
        now = datetime.now()
        current = (now.hour, now.minute, now.second)

        for t in SEND_TIMES:
            key = (now.date(), t)

            if current == tuple(t) and key not in sent_today:
                await send_to_all_chats()
                sent_today.add(key)

        # очищаем каждый день
        sent_today = {k for k in sent_today if k[0] == now.date()}

        await asyncio.sleep(1)

# ---------------- Главная функция ---------------- #

async def main():
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
