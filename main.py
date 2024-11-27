import random
import hashlib
import json
from datetime import datetime
from threading import Thread
from flask import Flask
from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, InlineQueryHandler, CommandHandler, CallbackQueryHandler

# === Хранилище данных ===
results = {}  # user_id -> {'percent': 0, 'timestamp': datetime, 'attempts': 0, 'best_percent': 0, 'title': ''}
leaderboard = []  # [{user_id, username, percent, timestamp, title}]
fixed_uids = [1444745009]  # Вечные фембои
data_file = "data.json"  # Путь к файлу для сохранения данных

# === Flask-приложение для health checks ===
app = Flask('health_check')

@app.route('/')
def home():
    return "Бот работает!"  # Сообщение для проверки Render

def run_health_server():
    app.run(host="0.0.0.0", port=5000)  # Flask сервер на порту 5000

# === Функции для работы с датами ===
def datetime_to_str(dt):
    return dt.isoformat() if isinstance(dt, datetime) else dt

def str_to_datetime(dt_str):
    return datetime.fromisoformat(dt_str) if isinstance(dt_str, str) else dt_str

# === Загрузка и сохранение данных ===
def load_data():
    global results, leaderboard
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            results = {k: {**v, 'timestamp': str_to_datetime(v['timestamp'])} for k, v in data["results"].items()}
            leaderboard = [
                {**entry, 'timestamp': str_to_datetime(entry['timestamp'])}
                for entry in data["leaderboard"]
            ]
    except FileNotFoundError:
        results = {}
        leaderboard = []

def save_data():
    data = {
        "results": {
            k: {**v, 'timestamp': datetime_to_str(v['timestamp'])} for k, v in results.items()
        },
        "leaderboard": [
            {**entry, 'timestamp': datetime_to_str(entry['timestamp'])}
            for entry in leaderboard
        ]
    }
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# === Генерация фраз ===
def get_femboy_phrase(percent: float, user_id: int) -> str:
    if user_id in fixed_uids:
        return "Ты вечный фембой! 100% фембойности, и это не обсуждается! 🌟💖"
    if percent >= 90:
        return f"{percent}% фембойности! Ты настоящий няша из няш! 🌸💕"
    elif percent >= 70:
        return f"У тебя {percent}% фембойности! Очень близко к топу! 😻"
    elif percent >= 50:
        return f"{percent}% фембойности. Ты идешь в правильном направлении! ✨"
    elif percent >= 30:
        return f"У тебя {percent}% фембойности. Постарайся ещё немного! 💪"
    else:
        return f"{percent}% фембойности. Ну, ничего, быть собой — это главное! 🌟"

# === Обновление лидерборда ===
def update_leaderboard():
    global leaderboard
    leaderboard = sorted([entry for entry in leaderboard if entry['user_id'] not in fixed_uids], key=lambda x: x['percent'], reverse=True)[:5]

# === Inline-запрос ===
def inline_query(update: Update, context):
    query = update.inline_query
    user_id = query.from_user.id
    username = query.from_user.username or "Anonymous"
    now = datetime.now()

    user_data = results.get(user_id, {'percent': 0, 'timestamp': now, 'attempts': 0, 'best_percent': 0})
    user_data['attempts'] += 1

    # Шанс в диапазоне 0–100 с весом на средние значения
    luck_factor = min(1.3, 1 + (user_data['attempts'] / 100))
    percent = round(random.triangular(10, 90, 50) * luck_factor, 2)
    user_data['percent'] = percent
    user_data['timestamp'] = now
    user_data['best_percent'] = max(user_data['best_percent'], percent)
    results[user_id] = user_data

    phrase = f"Ваш результат: {user_data['percent']}%\n\n" + get_femboy_phrase(user_data['percent'], user_id)
    leaderboard_entry = next((entry for entry in leaderboard if entry['user_id'] == user_id), None)

    if leaderboard_entry:
        leaderboard_entry.update({'percent': percent, 'timestamp': now})
    else:
        leaderboard.append({'user_id': user_id, 'username': username, 'percent': percent, 'timestamp': now})

    update_leaderboard()

    result_id = hashlib.md5(f"{user_id}-{now}".encode()).hexdigest()
    result = InlineQueryResultArticle(
        id=result_id,
        title="Узнай свой фембой-процент!",
        input_message_content=InputTextMessageContent(phrase),
        description="Какой ты фембой? Узнай сейчас!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Посмотреть топ", callback_data="leaderboard")]])
    )
    context.bot.answer_inline_query(query.id, [result], cache_time=0)

# === Показ таблицы лидеров ===
def show_leaderboard(update: Update, context):
    query = update.callback_query
    leaderboard_text = "🏆 Лидерборд фембоев: 🏆\n\n"
    for idx, entry in enumerate(leaderboard):
        leaderboard_text += f"{idx + 1}. @{entry['username']} - {entry['percent']}%\n"
    leaderboard_text += "\n✨ Вечные фембои:\n" + "\n".join([f"@User{uid}" for uid in fixed_uids])
    query.answer("Лидерборд обновлён!")
    query.edit_message_text(leaderboard_text)

# === Основной код ===
if __name__ == "__main__":
    load_data()

    # Запуск Flask health check
    server_thread = Thread(target=run_health_server)
    server_thread.start()

    # Запуск бота
    updater = Updater("ВАШ_ТОКЕН").build()
    dispatcher = updater.dispatcher

    dispatcher.add_handler(InlineQueryHandler(inline_query))
    dispatcher.add_handler(CallbackQueryHandler(show_leaderboard, pattern="leaderboard"))

    updater.start_polling()
    updater.idle()

    save_data()
