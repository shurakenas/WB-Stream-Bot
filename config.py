# -*- coding: utf-8 -*-

# Telegram
BOT_TOKEN = ''
ALLOWED_USER_IDS = []  # ТВОЙ ID (можно добавить других через запятую)

# Фиксированное имя комнаты (менять не нужно будет)
FIXED_ROOM_NAME = ""

# Путь к папке с куками
COOKIES_DIR = "/opt/WB-Stream-Bot/cookies"

# Список файлов кук (для ротации аккаунтов)
COOKIES_FILES = [
    "acc1.json",
    "acc2.json",
]

CREATOR_BIN = "/opt/WB-Stream-Bot/headless/headless-wbstream-creator"

# Интервалы ротации в минутах (случайный выбор)
ROTATION_INTERVALS = [25, 45, 65]

# Пауза между переключением аккаунтов (секунды)
SWITCH_DELAY = 5
