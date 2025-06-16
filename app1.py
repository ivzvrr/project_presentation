import sqlite3
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import aiohttp
from aiogram import types

# Версия с идентификацией пользователя
# Настройки
API_URL = "http://127.0.0.1:5715/getmpzzreport"
BOT_TOKEN = "8043399839:AAGsMi50XOV4xPcGIMq5IfuhvSKC-QswVLc"

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Клавиатура главного меню
def main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="📥 Скачать презентацию"))
    builder.add(types.KeyboardButton(text="📅 Выбрать дату"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# Клавиатура с датами
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
    url = f"{API_URL}/{date}" if date else API_URL
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                content = await response.read()
                return content
            return None

# Обработчики

async def is_user_allowed(user_id: int) -> bool:
    cursor.execute("SELECT 1 FROM allowed_users WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

@dp.message(Command("start"))
async def start(message: types.Message):
    if not await is_user_allowed(message.from_user.id):
        await message.answer("⛔ Доступ запрещен!")
        return
    
    await message.answer("Добро пожаловать! 🚀")
    

@dp.message(F.text == "📥 Скачать презентацию")
async def download_presentation(message: types.Message):
    content = await get_presentation()
    if content:
        with open("presentation.pptx", "wb") as f:
            f.write(content)
        await message.answer_document(
            FSInputFile("presentation.pptx"),
            caption="Ваша презентация:"
        )
    else:
        await message.answer("Презентация не найдена")

@dp.message(F.text == "📅 Выбрать дату")
async def select_date(message: types.Message):
    await message.answer(
        "Выберите дату:",
        reply_markup=dates_keyboard()
    )

@dp.message(F.text == "❌ Отмена")
async def cancel_date_selection(message: types.Message):
    await message.answer(
        "Действие отменено",
        reply_markup=main_keyboard()
    )

@dp.message(lambda message: message.text in ['2020-12-31', '2021-12-31', '2022-12-31', '2023-12-31', '2024-12-31'])
async def handle_date_selection(message: types.Message):
    content = await get_presentation(message.text)
    if content:
        filename = f"presentation_{message.text}.pptx"
        with open(filename, "wb") as f:
            f.write(content)
        await message.answer_document(
            FSInputFile(filename),
            caption=f"Презентация за {message.text}:",
            reply_markup=main_keyboard()
        )
    else:
        await message.answer(
            f"Презентация за {message.text} не найдена",
            reply_markup=main_keyboard()
        )

# Запуск бота
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
