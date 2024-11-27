import random
import hashlib
import json
from datetime import datetime
from telegram import (
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    InlineQueryHandler,
    CallbackQueryHandler,
)
from telegram.constants import ParseMode

# Хранилище данных
results = {}
leaderboard = []
fixed_uids = [1444745009]  # Вечные фембои
data_file = "data.json"


def datetime_to_str(dt):
    return dt.isoformat() if isinstance(dt, datetime) else dt


def str_to_datetime(dt_str):
    return datetime.fromisoformat(dt_str) if isinstance(dt_str, str) else dt_str


def load_data():
    global results, leaderboard
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            results = {
                k: {**v, "timestamp": str_to_datetime(v["timestamp"])} for k, v in data["results"].items()
            }
            leaderboard = [
                {**entry, "timestamp": str_to_datetime(entry["timestamp"])}
                for entry in data["leaderboard"]
            ]
    except FileNotFoundError:
        results = {}
        leaderboard = []


def save_data():
    data = {
        "results": {
            k: {**v, "timestamp": datetime_to_str(v["timestamp"])} for k, v in results.items()
        },
        "leaderboard": [
            {**entry, "timestamp": datetime_to_str(entry["timestamp"])} for entry in leaderboard
        ],
    }
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_femboy_phrase(percent: int, user_id: int) -> str:
    if user_id in fixed_uids:
        return "Ты вечный фембой! 100% фембойности, и это не обсуждается! 🌟💖"
    if percent == 100:
        return "Ты совершенство! Чистые 100% фембойности, няша из няш! 🌸💕"
    elif percent >= 80:
        return f"{percent}% фембой! Уровень милоты зашкаливает! 😻"
    elif percent >= 50:
        return f"У тебя {percent}% фембойности. Почти няша! ✨"
    elif percent >= 20:
        return f"Только {percent}% фембойности... Но ты можешь добиться большего! 💪"
    else:
        return f"Всего {percent}% фембойности. Эх, это не твоя тема, но быть собой — это главное! 🌟"


def update_leaderboard():
    global leaderboard
    leaderboard = sorted(
        [entry for entry in leaderboard if entry["user_id"] not in fixed_uids],
        key=lambda x: x["percent"],
        reverse=True,
    )[:5]


def calculate_femboy_percent(user_id: int, luck_factor: float = 1.0) -> float:
    """
    Рассчитывает фембой-процент с учетом удачи.
    Шансы распределены гиперболически для редкости высоких значений.
    """
    base_chance = random.random()  # Случайное значение от 0 до 1
    adjusted_chance = min(base_chance * luck_factor, 1.0)  # Учитываем удачу (макс. 1.3x)

    # Преобразование шанса в процент
    if user_id in fixed_uids:
        percent = 100
    elif adjusted_chance < 0.5:
        percent = adjusted_chance * 50  # 0-50% чаще
    else:
        percent = 50 + (adjusted_chance - 0.5) * 50  # 50-100% реже

    return round(percent, 1)  # Округляем до десятичного знака
# Функция для преобразования процентов в строку с одним десятичным знаком
def format_percent(percent: float) -> str:
    """Форматирует процентное значение с одним десятичным знаком."""
    return f"{percent:.1f}%"

# Обновление лидерборда
def update_leaderboard():
    global leaderboard
    # Сортируем по убыванию процентов и обрезаем до 5 позиций
    leaderboard = sorted(
        [entry for entry in leaderboard if entry['user_id'] not in fixed_uids],
        key=lambda x: x['percent'],
        reverse=True
    )[:5]

# Обработка inline-запроса
# Inline-запрос
async def inline_query(update: Update, context):
    query = update.inline_query
    if query is None:
        return

    try:
        user_id = query.from_user.id
        username = query.from_user.username or "Anonymous"
        now = datetime.now()

        # Рассчитываем процент с шансами и удачей
        luck_factor = 1.0 + random.uniform(0, 0.3)  # Удача от 1.0 до 1.3
        user_data = results.get(user_id, {'percent': 0, 'timestamp': now, 'attempts': 0, 'best_percent': 0})
        user_data['attempts'] += 1
        user_data['percent'] = calculate_femboy_percent(user_id, luck_factor)
        user_data['timestamp'] = now
        user_data['best_percent'] = max(user_data['best_percent'], user_data['percent'])
        results[user_id] = user_data

        # Генерируем текст ответа
        phrase = f"Ваш результат: {format_percent(user_data['percent'])}\n\n"
        phrase += get_femboy_phrase(user_data['percent'], user_id)
        phrase += f"\n\nЛучший результат: {format_percent(user_data['best_percent'])}"

        # Добавляем в лидерборд
        leaderboard_entry = next((entry for entry in leaderboard if entry['user_id'] == user_id), None)
        if leaderboard_entry:
            leaderboard_entry.update({'percent': user_data['percent'], 'timestamp': now})
        else:
            leaderboard.append({'user_id': user_id, 'username': username, 'percent': user_data['percent'], 'timestamp': now})

        update_leaderboard()

        # Рассчитываем позицию пользователя
        sorted_leaderboard = sorted(leaderboard, key=lambda x: x['percent'], reverse=True)
        user_position = next((idx + 1 for idx, entry in enumerate(sorted_leaderboard) if entry['user_id'] == user_id), "неизвестно")
        phrase += f"\n\nВаше место в лидерборде: {user_position}"

        # Inline-результат
        result_id = hashlib.md5(f"{user_id}-{now}".encode()).hexdigest()
        result = InlineQueryResultArticle(
            id=result_id,
            title="Узнай свой фембой-процент!",
            input_message_content=InputTextMessageContent(phrase),
            description="Какой ты фембой? Узнай сейчас!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Посмотреть топ", callback_data="leaderboard")]])
        )
        await query.answer([result], cache_time=0)

    except Exception as e:
        print(f"Ошибка при обработке inline-запроса: {e}")


# Получить имя пользователя через API Telegram
async def get_username(bot, user_id):
    try:
        user = await bot.get_chat(user_id)
        return f"@{user.username}" if user.username else f"{user.first_name} {user.last_name or ''}".strip()
    except Exception as e:
        return f"User{user_id}"  # Если не удалось получить данные

# Обработка показа таблицы лидеров
async def show_leaderboard(update: Update, context):
    query = update.callback_query

    # Формируем текст для лидерборда
    leaderboard_text = "🏆 Лидерборд фембоев: 🏆\n\n"
    for idx, entry in enumerate(leaderboard):
        leaderboard_text += f"{idx + 1}. @{entry['username']} - {entry['percent']}%\n"

    # Формируем текст для вечных фембоев
    eternal_femboys = []
    for uid in fixed_uids:
        username = await get_username(context.bot, uid)
        eternal_femboys.append(username)

    if eternal_femboys:
        leaderboard_text += f"\n✨ Вечные фембои:\n" + "\n".join(eternal_femboys)

    # Отправляем алерт
    await query.answer(leaderboard_text, show_alert=True)

if __name__ == "__main__":
    load_data()

    app = Application.builder().token("7843135403:AAFzvWumgrO5GnQ18B0yuhjqZ4LppkmYFwc").build()

    app.add_handler(InlineQueryHandler(inline_query))
    app.add_handler(CallbackQueryHandler(show_leaderboard, pattern="leaderboard"))

    app.run_polling()
    save_data()

