# Clicker Bot 🤖

Telegram-бот кликер с мини-играми, донат-магазином и админ-панелью.

## Настройка переменных окружения (BotHost / Railway / Heroku)

В панели хостинга добавьте следующие переменные:

| Переменная | Описание | Пример |
|------------|----------|--------|
| `BOT_TOKEN` | Токен от @BotFather | `123456789:ABCdef...` |
| `ADMIN_ID` | Ваш Telegram ID | `123456789` |
| `ADMIN_IDS` | ID всех админов через запятую | `123456789,987654321` |
| `YOUR_BOT_USERNAME` | Имя бота без @ | `my_clicker_bot` |
| `DATA_FILE` | Имя файла данных (опционально) | `clicker_data.json` |

### Как узнать свой Telegram ID?
Напишите боту [@userinfobot](https://t.me/userinfobot)

## Деплой на BotHost

1. Загрузите код на GitHub
2. В BotHost подключите репозиторий
3. Добавьте переменные окружения в панели
4. Запустите!

## Локальный запуск (для теста)

```bash
# Установка зависимостей
pip install -r requirements.txt

# Установка переменных (Linux/Mac)
export BOT_TOKEN="your_token"
export ADMIN_ID="your_id"
export YOUR_BOT_USERNAME="your_bot"

# Запуск
python main.py
```

```bash
# Windows PowerShell
$env:BOT_TOKEN="your_token"
$env:ADMIN_ID="your_id"
python main.py
```

## Структура проекта

- `config.py` — конфигурация из переменных окружения
- `data_manager.py` — работа с данными пользователей
- `game_logic.py` — игровая механика
- `minigames.py` — мини-игры (краш, рулетка, дуэль)
- `shop.py` — магазины
- `admin.py` — админ-команды
- `handlers.py` — основные обработчики
- `payments.py` — платежи Telegram Stars
- `reminders.py` — фоновые задачи
- `main.py` — точка входа
