# 🤖 WB Stream Bot

Telegram бот для автоматической ротации аккаунтов WB Stream и поддержания активной WebRTC-комнаты 24/7.

## 🎯 Назначение

Бот решает проблему автоматического закрытия комнат в WB Stream. Он запускает `headless-wbstream-creator`, который сидит в комнате как постоянный участник и каждые 25-65 минут переключается между аккаунтами, имитируя активность реальных пользователей.

## ⚙️ Как это работает
```
Telegram Bot → управляет → headless-wbstream-creator
↓
WB Stream комната
↓
olcrtc (сервер) + olcbox (клиент)
```

1. **Бот запускается** → сразу стартует `headless-wbstream-creator` с первым аккаунтом.
2. **Creator заходит в комнату** с рандомным русским именем (пол и фамилия подбираются автоматически).
3. **Бот ротирует аккаунты** через случайные интервалы 25, 45 или 65 минут.
4. **Ты всегда используешь одну ссылку** в `olcbox` — комната остаётся активной 24/7.

## 📦 Требования

- Сервер с Linux (Ubuntu/Debian)
- Python 3.10+
- Собранный `headless-wbstream-creator` из [whitelist-bypass](https://github.com/kulikov0/whitelist-bypass) или скачать из релизов [whitelist-bypass-cli-linux-x64](https://github.com/kulikov0/whitelist-bypass/releases/download/v0.3.5/whitelist-bypass-cli-linux-x64.zip)
- Куки аккаунтов WB Stream, получить с помощью этого: ([WhitelistBypass.Creator](https://github.com/kulikov0/whitelist-bypass/releases/download/v0.3.6/WhitelistBypass.Creator-0.3.6-x64.exe))

## 🚀 Быстрый старт

### 1. Клонировать репозиторий

```
git clone https://github.com/shurakenas/WB-Stream-Bot.git
cd WB-Stream-Bot
```

### 2. Установить зависимости
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Настроить config.py
```
BOT_TOKEN = ''
ALLOWED_USER_IDS = []  # ТВОЙ ID (можно добавить других через запятую) - для ограничения достпа к боту
FIXED_ROOM_NAME = ""   # любое рандомное, можно вручную на WB создать комнату и взять оттуда
ROTATION_INTERVALS = [25, 45, 65]  # можно поменять свои
```
### 4. Получить куки
с помощью: [WhitelistBypass.Creator](https://github.com/kulikov0/whitelist-bypass/releases/download/v0.3.6/WhitelistBypass.Creator-0.3.6-x64.exe)
детали пропускаю, там всё интуитивно понятно

### 5. Запустить бота
```
python bot.py
```

## 🎮 Команды и кнопки
| Кнопка |	Действие |
| --- | --- |
| 📊 Статус	| Показывает текущий аккаунт, PID процесса и время до следующей ротации |
| 🔄 Ротация сейчас	| Принудительно переключает аккаунт и перезапускает таймер |
| 🛑 Остановить	| Останавливает ротацию и убивает процесс creator |
| ▶️ Запустить	| Запускает ротацию и creator заново |

## 📁 Структура проекта
```
WB-Stream-Bot/
├── bot.py              # Основной код
├── config.py           # Конфигурация
├── requirements.txt    # Зависимости
├── cookies/            # JSON-файлы кук аккаунтов
│   ├── acc1.json
│   └── acc2.json
└── headless/
    └── headless-wbstream-creator
└── log/                # создать вручную
└── tmp/                # создать вручную
```

## 🧠 Особенности
- Рандомные имена — каждый creator заходит с уникальным русским именем (пол и фамилия согласованы)

- Автовосстановление — при перезапуске бот удаляет старое сообщение и отправляет новое

- Одно сообщение — все действия обновляют одно и то же сообщение, без спама

- Таймер ротации — показывает точное время до следующей смены аккаунта

## ⚠️ Важно
- Аккаунты WB Stream должны быть действующими (куки не проверял насколько хватит, возможно придется обновлять раз в месяц)

- Комнату FIXED_ROOM_NAME нужно создать один раз вручную через браузер или придумать свое название

## 📝 Пример сообщения
```
🎥 WB Stream Bot

🔗 Ссылка для olcbox:
https://stream.wb.ru/room/test-123-456-789

🔄 Аккаунты ротируются с интервалами 25, 45, 65 мин
⏱ Следующая ротация: через 32 мин 15 сек
👤 Всего аккаунтов: 2

📊 Текущий статус:
👤 Аккаунт: acc1.json
🟢 Процесс creator активен (PID: 1261)

✅ Бот запущен
📱 Укажите ID комнаты в olcbox
```

## 🛠️ Установка как systemd-сервис
```
nano /etc/systemd/system/wb-bot.service
```
```
[Unit]
Description=OlcrtcWbStreamSankoBot Telegram
After=network.target

[Service]
# Запуск от непривилегированного пользователя
#User=botuser
#Group=botuser

# Папка, где лежит бот и venv
WorkingDirectory=/opt/WB-Stream-Bot

# Экспортируем переменную PATH так, чтобы "python" указывал на venv-версию
Environment="PATH=/opt/WB-Stream-Bot/venv/bin"

# Команда запуска
ExecStart=/opt/WB-Stream-Bot/venv/bin/python /opt/WB-Stream-Bot/bot.py

# Автоматически перезапускать, если упадёт
Restart=always
RestartSec=5

# Логи отправляются в journalctl
StandardOutput=journal
StandardError=journal
SyslogIdentifier=WB-Stream-Bot

[Install]
WantedBy=multi-user.target
```

```
systemctl daemon-reload
systemctl enable --now wb-bot.service
systemctl status wb-bot.service
```
## Настройка клиента
Выходит за рамки данного репозитория

# 🙏 Благодарности

* [openlibrecommunity/olcrtc](https://github.com/openlibrecommunity/olcrtc)
* [alananisimov/olcbox](https://github.com/alananisimov/olcbox)
* [kulikov0/whitelist-bypass](https://github.com/kulikov0/whitelist-bypass)
