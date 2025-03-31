import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

TOKEN = "7523103857:AAEESZumYaFuYzenJ80nCi5obGE65W0je1w"
ADMIN_ID = 2031798627 

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

conn = sqlite3.connect("raffle_bot.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    phone TEXT,
    age INTEGER
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS raffles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT,
    link TEXT
)
""")
conn.commit()

phone_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton("Поделиться номером", request_contact=True)
)

def get_raffles():
    cursor.execute("SELECT text, link FROM raffles")
    return cursor.fetchall()

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    await message.answer("Привет! Чтобы участвовать в розыгрыше, подтвердите, что вы не бот. Отправьте свой номер телефона.", reply_markup=phone_kb)

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def process_contact(message: types.Message):
    phone = message.contact.phone_number
    user_id = message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id, phone) VALUES (?, ?)", (user_id, phone))
    conn.commit()
    await message.answer("Спасибо! Теперь укажите ваш возраст.")

@dp.message_handler(lambda message: message.text.isdigit())
async def process_age(message: types.Message):
    age = int(message.text)
    user_id = message.from_user.id
    if age < 18:
        await message.answer("Извините, участвовать могут только пользователи 18+.")
    else:
        cursor.execute("UPDATE users SET age = ? WHERE user_id = ?", (age, user_id))
        conn.commit()
        await message.answer("Вы прошли проверку, поздравляем! Вот первый розыгрыш:")
        await send_raffle(message)

async def send_raffle(message: types.Message, idx=0):
    raffles = get_raffles()
    if idx >= len(raffles):
        await message.answer("Розыгрыши закончились!")
        return
    text, link = raffles[idx]
    markup = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("Следующий конкурс"))
    await message.answer(f"🎁 {text}\n🔗 {link}", reply_markup=markup)
    dp.register_message_handler(lambda msg: send_raffle(msg, idx+1), text="Следующий конкурс")

@dp.message_handler(commands=['add_raffle'])
async def add_raffle_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав для этой команды.")
        return
    args = message.text.split(" ", 2)
    if len(args) < 3:
        await message.answer("Используйте: /add_raffle <текст> <ссылка>")
        return
    cursor.execute("INSERT INTO raffles (text, link) VALUES (?, ?)", (args[1], args[2]))
    conn.commit()
    await message.answer("Розыгрыш добавлен!")

@dp.message_handler(commands=['list_raffles'])
async def list_raffles_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав для этой команды.")
        return
    raffles = get_raffles()
    if not raffles:
        await message.answer("Список розыгрышей пуст.")
        return
    response = "\n".join([f"{i+1}. {text} - {link}" for i, (text, link) in enumerate(raffles)])
    await message.answer(response)

@dp.message_handler(commands=['delete_raffle'])
async def delete_raffle_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав для этой команды.")
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("Используйте: /delete_raffle <номер>")
        return
    idx = int(args[1]) - 1
    raffles = get_raffles()
    if idx < 0 or idx >= len(raffles):
        await message.answer("Неверный номер.")
        return
    cursor.execute("DELETE FROM raffles WHERE id = ?", (raffles[idx][0],))
    conn.commit()
    await message.answer("Розыгрыш удалён!")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)
