import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BufferedInputFile
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import aiohttp
from datetime import datetime

# Конфигурация
API_URL = "http://127.0.0.1:5715/getmpzzreport"
BOT_TOKEN = "8043399839:AAGsMi50XOV4xPcGIMq5IfuhvSKC-QswVLc"
DB_FILE = "presentation_bot.db"

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Кеш презентаций {date: bytes}
presentation_cache = {}

# Инициализация БД
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            access_granted BOOLEAN DEFAULT 0,
            first_seen TIMESTAMP,
            last_active TIMESTAMP
        )""")
        conn.commit()

# Проверка прав доступа
async def check_access(user_id: int) -> bool:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT access_granted FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else False

# Функция регистрации/обновления пользователя
async def update_user_info(user: types.User):
    with sqlite3.connect(DB_FILE) as conn:
        # Сначала проверяем, есть ли пользователь в базе
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user.id,))
        exists = cursor.fetchone()
        
        if not exists:
            # Если пользователя нет - создаем новую запись
            conn.execute("""
            INSERT INTO users 
            (user_id, username, full_name, first_seen, last_active)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (user.id, user.username, user.full_name))
            conn.commit()
        else:
            # Если пользователь уже есть - только обновляем last_active
            conn.execute("""
            UPDATE users SET 
            last_active = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """, (user.id,))
            conn.commit()


# Клавиатуры
def main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="📥 Скачать текущую презентацию"))
    builder.add(types.KeyboardButton(text="📅 Выбрать дату"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def dates_keyboard():
    dates = ['2020-12-31', '2021-12-31', '2022-12-31', '2023-12-31', '2024-12-31']
    builder = ReplyKeyboardBuilder()
    for date in dates:
        builder.add(types.KeyboardButton(text=date))
    builder.add(types.KeyboardButton(text="❌ Отмена"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# Запрос к API
async def get_presentation(date=None):
    cache_key = date or "current"
    if cache_key in presentation_cache:
        return presentation_cache[cache_key]
    
    url = f"{API_URL}/{date}" if date else API_URL
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                content = await response.read()
                presentation_cache[cache_key] = content  # Кешируем
                return content
            return None

# Обработчики
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Проверяем, есть ли пользователь в базе
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (message.from_user.id,))
        user_exists = cursor.fetchone()
    
    # Если пользователя нет - добавляем
    if not user_exists:
        await update_user_info(message.from_user)
    
    has_access = await check_access(message.from_user.id)
    
    if has_access:
        await message.answer(
            "Добро пожаловать в систему презентаций!",
            reply_markup=main_keyboard()
        )
    else:
        await message.answer(
            "⛔ Доступ запрещен.",
            reply_markup=types.ReplyKeyboardRemove()
        )

@dp.message(F.text == "📥 Скачать текущую презентацию")
async def download_current(message: types.Message):
    if not await check_access(message.from_user.id):
        return await message.answer("⛔ Нет прав доступа")
    
    content = await get_presentation()
    if content:
        await message.answer_document(
            BufferedInputFile(content, filename="current_presentation.pptx"),
            caption="Актуальная презентация"
        )
    else:
        await message.answer("Презентация не найдена")

@dp.message(F.text == "📅 Выбрать дату")
async def select_date(message: types.Message):
    if not await check_access(message.from_user.id):
        return
    
    await message.answer(
        "Выберите дату презентации:",
        reply_markup=dates_keyboard()
    )

@dp.message(F.text.in_(['2020-12-31', '2021-12-31', '2022-12-31', '2023-12-31', '2024-12-31']))
async def handle_date(message: types.Message):
    if not await check_access(message.from_user.id):
        return
    
    content = await get_presentation(message.text)
    if content:
        await message.answer_document(
            BufferedInputFile(content, filename=f"presentation_{message.text}.pptx"),
            caption=f"Презентация за {message.text}"
        )
    else:
        await message.answer(f"Презентация за {message.text} не найдена")

@dp.message(F.text == "❌ Отмена")
async def cancel_action(message: types.Message):
    await message.answer(
        "Действие отменено",
        reply_markup=main_keyboard()
    )


async def main():
    # Удаляем возможный активный webhook
    await bot.delete_webhook(drop_pending_updates=True)
    # Инициализация БД
    init_db()
    # Запуск бота в режиме polling
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)


def grant_access(user_id: int):
    """Выдать права доступа пользователю"""
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
        INSERT OR REPLACE INTO users 
        (user_id, access_granted, last_active) 
        VALUES (?, 1, CURRENT_TIMESTAMP)
        """, (user_id,))
        conn.commit()

if __name__ == "__main__":
    import asyncio
    # При необходимости выдачи прав доступа
    # grant_access(id пользователя)
    asyncio.run(main())