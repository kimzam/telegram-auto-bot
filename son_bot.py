"""
Бот-автоответчик на aiogram 3 для Render.
"""

import asyncio
import logging
import os
import random
import time

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

# ======================= НАСТРОЙКИ =======================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")
PORT = int(os.getenv("PORT", "10000"))

AWAY_TEXT = "Привет! Сейчас меня нет на месте / я занят. Отвечу, как освобожусь!"
COOLDOWN_SECONDS = 10  # Уменьшено для теста, потом можно вернуть 15 * 60
DELAY_MIN, DELAY_MAX = 2.0, 4.0

IS_AWAY = os.getenv("IS_AWAY", "true").strip().lower() in ("1", "true", "yes", "on")
# =========================================================

if not BOT_TOKEN or not OWNER_ID:
    raise RuntimeError("Не заданы переменные окружения: BOT_TOKEN, OWNER_ID")
OWNER_ID = int(OWNER_ID)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Бот работает только в личных сообщениях
dp.message.filter(F.chat.type == "private")

last_reply: dict[int, float] = {}


# ---------- Команды владельца ----------
@dp.message(Command("away"), F.from_user.id == OWNER_ID)
async def cmd_away(message: Message):
    global IS_AWAY
    IS_AWAY = True
    await message.answer("🔴 Автоответчик включён.")


@dp.message(Command("online"), F.from_user.id == OWNER_ID)
async def cmd_online(message: Message):
    global IS_AWAY
    IS_AWAY = False
    last_reply.clear()
    await message.answer("🟢 Автоответчик выключен, вы в сети.")


@dp.message(Command("status"), F.from_user.id == OWNER_ID)
async def cmd_status(message: Message):
    state = "включён 🔴" if IS_AWAY else "выключен 🟢"
    await message.answer(f"Автоответчик {state}")


# ---------- Автоответ всем остальным ----------
@dp.message()
async def autoreply(message: Message):
    user = message.from_user
    if user is None or user.is_bot or user.id == OWNER_ID:
        return
    if not IS_AWAY:
        return

    now = time.time()
    if now - last_reply.get(user.id, 0) < COOLDOWN_SECONDS:
        return
    last_reply[user.id] = now

    await bot.send_chat_action(message.chat.id, "typing")
    await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
    await message.answer(AWAY_TEXT)


# ---------- HTTP-сервер для Render / UptimeRobot ----------
async def handle(request: web.Request) -> web.Response:
    return web.Response(text="I am alive!")


async def start_web_server() -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    logging.info("HTTP-сервер запущен на порту %s", PORT)
    return runner


# ---------- ОСНОВНАЯ ТОЧКА ЗАПУСКА ----------
async def main():
    # Запускаем веб-сервер для пингов
    runner = await start_web_server()
    
    try:
        # Сбрасываем старые вебхуки/сессии, чтобы избежать конфликтов
        await bot.delete_webhook(drop_pending_updates=True)
        print("Бот запущен и слушает обновления...")
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
