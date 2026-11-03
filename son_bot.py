"""
Бот-автоответчик на aiogram 3 для Render.

Переменные окружения (задаются в настройках Render, НЕ в коде):
  BOT_TOKEN  - токен от @BotFather
  OWNER_ID   - ваш числовой Telegram ID (узнать у @userinfobot)
  IS_AWAY    - "true" / "false": стартовое состояние автоответчика (по умолчанию true)
  PORT       - порт HTTP-сервера (Render задаёт сам; по умолчанию 10000)
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

# Текст автоответа: меняйте здесь
AWAY_TEXT = "Привет! Сейчас меня нет на месте / я занят. Отвечу, как освобожусь!"

# Кулдаун: не чаще одного автоответа одному человеку раз в N секунд
COOLDOWN_SECONDS = 15 * 60

# Имитация "человек печатает": случайная пауза в этом диапазоне (секунды)
DELAY_MIN, DELAY_MAX = 2.0, 4.0

# Флаг: True = автоответчик включён. Переключается командами /away и /online
IS_AWAY = os.getenv("IS_AWAY", "true").strip().lower() in ("1", "true", "yes", "on")
# =========================================================

if not BOT_TOKEN or not OWNER_ID:
    raise RuntimeError("Не заданы переменные окружения: BOT_TOKEN, OWNER_ID")
OWNER_ID = int(OWNER_ID)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Бот работает только в личных сообщениях: группы, чаты и каналы игнорируются
dp.message.filter(F.chat.type == "private")

# user_id -> время последнего автоответа (unix-время)
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
    last_reply.clear()  # при следующем уходе все получат ответ заново
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
    # Фиксируем время сразу, чтобы несколько быстрых сообщений подряд
    # не вызвали несколько ответов, пока идёт пауза
    last_reply[user.id] = now

    # Имитация набора текста
    await bot.send_chat_action(message.chat.id, "typing")
    await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    await message.answer(AWAY_TEXT)


# ---------- HTTP-сервер для Render ----------
async def health(request: web.Request) -> web.Response:
    return web.Response(text="OK")


async def start_web_server() -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, host="0.0.0.0", port=PORT).start()
    logging.info("HTTP-сервер запущен на порту %s", PORT)
    return runner

import os
from aiohttp import web

# --- ВЕБ-СЕРВЕР ДЛЯ UPTIMEROBOT ---
async def handle(request):
    return web.Response(text="I am alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# --- ОСНОВНАЯ ФУНКЦИЯ ЗАПУСКА ---
async def main():
    # Запускаем веб-сервер для пинга
    await start_web_server()
    
    # Запускаем бота
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
