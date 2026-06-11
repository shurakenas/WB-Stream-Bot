import asyncio
import subprocess
import json
import os
import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage

import config

# === НАСТРОЙКА ===
logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Файл для хранения ID сообщения
MESSAGE_STATE_FILE = "/opt/WB-Stream-Bot/tmp/wb_bot_message_state.json"

# Списки для рандомных имён
MALE_FIRST_NAMES = [
    "Александр", "Дмитрий", "Максим", "Иван", "Артём", "Владимир", "Сергей", "Павел",
    "Андрей", "Алексей", "Михаил", "Николай", "Виктор", "Егор", "Даниил", "Тимофей"
]

FEMALE_FIRST_NAMES = [
    "Анна", "Екатерина", "Мария", "Ольга", "Татьяна", "Светлана", "Ксения", "Ирина",
    "Наталья", "Елена", "Юлия", "Анастасия", "Дарья", "Полина", "Виктория", "Евгения"
]

MALE_LAST_NAMES = [
    "Кузнецов", "Попов", "Соколов", "Иванов", "Петров", "Сидоров", "Лебедев", "Козлов",
    "Новиков", "Морозов", "Волков", "Зайцев", "Павлов", "Григорьев", "Степанов", "Николаев",
    "Михайлов", "Фёдоров", "Семёнов", "Егоров", "Алексеев"
]

FEMALE_LAST_NAMES = [
    "Кузнецова", "Попова", "Соколова", "Иванова", "Петрова", "Сидорова", "Лебедева", "Козлова",
    "Новикова", "Морозова", "Волкова", "Зайцева", "Павлова", "Григорьева", "Степанова", "Николаева",
    "Михайлова", "Фёдорова", "Семёнова", "Егорова", "Алексеева"
]

def random_name():
    gender = random.choice(["male", "female"])
    if gender == "male":
        return f"{random.choice(MALE_FIRST_NAMES)} {random.choice(MALE_LAST_NAMES)}"
    else:
        return f"{random.choice(FEMALE_FIRST_NAMES)} {random.choice(FEMALE_LAST_NAMES)}"

# Глобальные переменные
current_process = None
current_account = None
rotation_task = None
current_room_link = f"https://stream.wb.ru/room/{config.FIXED_ROOM_NAME}"
main_message = None
next_rotation_time = None

def save_message_state(chat_id, message_id):
    """Сохраняет chat_id и message_id в файл"""
    try:
        with open(MESSAGE_STATE_FILE, 'w') as f:
            json.dump({'chat_id': chat_id, 'message_id': message_id}, f)
    except Exception as e:
        logging.error(f"Failed to save message state: {e}")

def load_and_clear_message_state():
    """Загружает chat_id и message_id из файла и удаляет файл"""
    try:
        if os.path.exists(MESSAGE_STATE_FILE):
            with open(MESSAGE_STATE_FILE, 'r') as f:
                data = json.load(f)
            os.remove(MESSAGE_STATE_FILE)
            return data.get('chat_id'), data.get('message_id')
    except Exception as e:
        logging.error(f"Failed to load message state: {e}")
    return None, None

async def delete_old_message():
    """Удаляет старое сообщение, если оно есть в файле"""
    chat_id, message_id = load_and_clear_message_state()
    if chat_id and message_id:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
            logging.info(f"Deleted old message {message_id} in chat {chat_id}")
        except Exception as e:
            logging.warning(f"Failed to delete old message: {e}")

# === КЛАВИАТУРЫ ===
def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статус", callback_data="status"),
            InlineKeyboardButton(text="🔄 Ротация сейчас", callback_data="rotate_now")
        ],
        [
            InlineKeyboardButton(text="🛑 Остановить", callback_data="stop_bot"),
            InlineKeyboardButton(text="▶️ Запустить", callback_data="start_bot")
        ]
    ])
    return keyboard

# === УПРАВЛЕНИЕ ПРОЦЕССОМ ===
def kill_current_process():
    global current_process
    if current_process and current_process.poll() is None:
        try:
            current_process.terminate()
            current_process.wait(timeout=5)
            logging.info(f"Creator process terminated for {current_account}")
        except subprocess.TimeoutExpired:
            current_process.kill()
            logging.info(f"Creator process killed for {current_account}")
    current_process = None

def start_creator(cookie_file):
    cookie_path = os.path.join(config.COOKIES_DIR, cookie_file)
    if not os.path.exists(cookie_path):
        logging.error(f"Cookie file not found: {cookie_path}")
        return None
    
    display_name = random_name()
    
    cmd = [
        config.CREATOR_BIN,
        "--cookies", cookie_path,
        "--room", config.FIXED_ROOM_NAME,
        "--name", display_name
    ]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        logging.info(f"Creator started for {cookie_file} with name '{display_name}' in room {config.FIXED_ROOM_NAME}")
        return process
    except Exception as e:
        logging.error(f"Failed to start creator: {e}")
        return None

# === ФОРМИРОВАНИЕ СООБЩЕНИЯ ===
def get_status_text():
    status_text = (
        f"🎥 **WB Stream Bot**\n\n"
        f"🔗 **Ссылка для olcbox:**\n`{current_room_link}`\n\n"
        f"🔄 **Аккаунты ротируются** с интервалами {config.ROTATION_INTERVALS} мин\n"
        f"{get_next_rotation_text()}\n"
        f"👤 **Всего аккаунтов:** {len(config.COOKIES_FILES)}\n\n"
        f"📊 **Текущий статус:**\n"
        f"👤 Аккаунт: `{current_account or 'не запущен'}`\n"
    )
    
    if current_process and current_process.poll() is None:
        status_text += f"🟢 Процесс creator активен (PID: {current_process.pid})\n"
    else:
        status_text += f"🔴 Процесс creator не активен\n"
    
    status_text += f"\n✅ Бот запущен\n"
    status_text += f"📱 Укажите ID комнаты в olcbox"
    
    return status_text

async def send_new_status_message(target_message):
    """Отправляет новое сообщение со статусом"""
    global main_message

    # Удаляем старое сообщение из файла (если есть)
    await delete_old_message()

    text = get_status_text()
    main_message = await target_message.answer(
        text,
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

    # Сохраняем ID нового сообщения
    save_message_state(main_message.chat.id, main_message.message_id)

# === ЛОГИКА РОТАЦИИ ===
async def rotate_account():
    """Ротирует аккаунт без отправки сообщения"""
    global current_account, current_process, next_rotation_time
    
    kill_current_process()
    await asyncio.sleep(config.SWITCH_DELAY)
    
    if current_account is None:
        next_index = 0
    else:
        try:
            current_index = config.COOKIES_FILES.index(current_account)
            next_index = (current_index + 1) % len(config.COOKIES_FILES)
        except ValueError:
            next_index = 0
    
    next_account = config.COOKIES_FILES[next_index]
    
    process = start_creator(next_account)
    if process:
        current_account = next_account
        current_process = process
        logging.info(f"Rotated to account: {next_account}")
        return True
    else:
        logging.error(f"Failed to start creator for {next_account}")
        return False

async def rotation_loop():
    global next_rotation_time
    while True:
        if current_account:
            interval_minutes = random.choice(config.ROTATION_INTERVALS)
            interval_seconds = interval_minutes * 60
            next_rotation_time = asyncio.get_event_loop().time() + interval_seconds
            logging.info(f"Next rotation in {interval_minutes} minutes")
            await asyncio.sleep(interval_seconds)
            await rotate_account()
        else:
            await rotate_account()
            await asyncio.sleep(60)

def get_next_rotation_text():
    """Возвращает строку с информацией о следующей ротации"""
    if next_rotation_time is None or not current_account:
        return "⏱ Следующая ротация: не запланирована"
    
    import datetime
    remaining = max(0, next_rotation_time - asyncio.get_event_loop().time())
    minutes = int(remaining // 60)
    seconds = int(remaining % 60)
    
    if minutes > 0:
        return f"⏱ Следующая ротация: через {minutes} мин {seconds} сек"
    else:
        return f"⏱ Следующая ротация: через {seconds} сек"

# === ЗАПУСК И ОСТАНОВКА ===
async def start_bot_engine():
    global rotation_task, current_account, current_process
    
    if rotation_task is None or rotation_task.done():
        if config.COOKIES_FILES:
            process = start_creator(config.COOKIES_FILES[0])
            if process:
                current_account = config.COOKIES_FILES[0]
                current_process = process
        
        rotation_task = asyncio.create_task(rotation_loop())
        logging.info("Rotation engine started")
        return True
    return False

async def stop_bot_engine():
    global rotation_task, current_account, current_process
    
    if rotation_task and not rotation_task.done():
        rotation_task.cancel()
        try:
            await rotation_task
        except asyncio.CancelledError:
            pass
        rotation_task = None
    
    kill_current_process()
    current_account = None
    logging.info("Rotation engine stopped")

# === ОБРАБОТЧИКИ TELEGRAM ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id not in config.ALLOWED_USER_IDS:
        await message.answer("⛔ Доступ запрещен")
        return
    
    await start_bot_engine()
    await send_new_status_message(message)

@dp.callback_query(lambda c: c.data == "status")
async def process_status(callback_query: types.CallbackQuery):
    # Отправляем новое
    await send_new_status_message(callback_query.message)
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "rotate_now")
async def process_rotate_now(callback_query: types.CallbackQuery):
    global rotation_task, next_rotation_time

    await callback_query.answer("🔄 Ротация...")

    # Останавливаем текущий цикл ротации
    if rotation_task and not rotation_task.done():
        rotation_task.cancel()
        try:
            await rotation_task
        except asyncio.CancelledError:
            pass

    await rotate_account()
    rotation_task = asyncio.create_task(rotation_loop())
    await asyncio.sleep(2)
    await send_new_status_message(callback_query.message)

@dp.callback_query(lambda c: c.data == "stop_bot")
async def process_stop_bot(callback_query: types.CallbackQuery):
    global next_rotation_time
    await callback_query.answer("🛑 Остановка...")
    await stop_bot_engine()
    next_rotation_time = None
    await send_new_status_message(callback_query.message)

@dp.callback_query(lambda c: c.data == "start_bot")
async def process_start_bot(callback_query: types.CallbackQuery):
    await callback_query.answer("▶️ Запуск...")
    await start_bot_engine()
    await send_new_status_message(callback_query.message)

# === ЗАПУСК ===
async def main():
    global main_message
    
    print(f"🚀 Запуск бота с фиксированной комнатой: {config.FIXED_ROOM_NAME}")
    print(f"📁 Файлы кук: {config.COOKIES_FILES}")
    print(f"🔄 Интервалы ротации: {config.ROTATION_INTERVALS} мин")
    
    # Запускаем движок
    await start_bot_engine()
    
    # Пытаемся восстановить сообщение после перезапуска
    chat_id, message_id = load_and_clear_message_state()
    if chat_id:
        # Удаляем старое сообщение
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
            logging.info(f"Deleted old message {message_id} in chat {chat_id}")
        except Exception as e:
            logging.warning(f"Failed to delete old message: {e}")
        
        # Отправляем новое сообщение в тот же чат
        text = get_status_text()
        main_message = await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
        save_message_state(main_message.chat.id, main_message.message_id)
        logging.info(f"Sent new message to chat {chat_id}")
    else:
        # Нет сохранённого чата — ждём команду /start
        logging.info("No saved message state, waiting for /start command")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
