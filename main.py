import asyncio
import logging

from monthly_report import send_monthly_report
from scheduler import setup_scheduler
from aiogram import Bot, Dispatcher, F
from aiogram.types import BotCommand
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.filters.command import CommandObject
from time_utils import local_date, parse_day_arg
from db import (
    init_db,
    add_note,
    upsert_member,
    remove_note,
    get_month_scores,
    get_all_month_results,
    get_user_total_score,
    get_user_titles
)
from config import BOT_TOKEN, CHAT_ID

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Создаём бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Обработчик команды /start
@dp.message(CommandStart())
async def start_handler(message: Message):
    user = message.from_user

    if user and message.chat.type == "private":
        upsert_member(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name
        )

    await message.answer(
        "💪 Добро пожаловать в NoExcusesClub!\n\n"
        "Здесь каждая тренировка приносит тебе очко.\n"
        "Готовься участвовать в турнире!\n\n"
        "📊 /mystats — моя статистика\n"
        "🏆 /mytitles — мои титулы"
    )

@dp.message(
    F.chat.type == "private",
    Command("mystats")
)
async def my_stats_handler(message: Message):
    user = message.from_user

    if user is None or user.is_bot:
        return

    total = get_user_total_score(user.id)

    await message.answer(
        f"📊 ТВОЯ СТАТИСТИКА NoExcusesClub\n\n"
        f"👤 {user.full_name}\n"
        f"💪 Всего тренировок: {total}\n\n"
        f"Продолжай в том же духе!"
    )

@dp.message(
    F.chat.type == "private",
    Command("mytitles")
)
async def my_titles_handler(message: Message):
    user = message.from_user

    if user is None or user.is_bot:
        return

    titles = get_user_titles(user.id)

    if not titles:
        await message.answer(
            "🏆 У тебя пока нет чемпионских титулов.\n\n"
            "Продолжай тренироваться — твоя победа впереди!"
        )
        return

    lines = [
        "🏆 ТВОИ ТИТУЛЫ NoExcusesClub",
        ""
    ]

    for title in titles:
        month = title["month"]
        month_display = f"{month[5:7]}.{month[:4]}"

        lines.append(
            f"🥇 {month_display} — "
            f"{title['winner_score']} очк."
        )

    lines.append(
        f"\nВсего титулов: {len(titles)}"
    )

    await message.answer("\n".join(lines))

# @dp.message(F.text == "/getid")
# async def show_chat_id(message: Message):
#     print(f"CHAT ID: {message.chat.id}")
#     print(f"CHAT TITLE: {message.chat.title}")

#     await message.answer(
#         f"ID этой группы: {message.chat.id}"
#     )

@dp.message(
    F.chat.id == CHAT_ID,
    Command("done")
)
async def done_handler(message: Message):

    if message.from_user is None or message.from_user.is_bot:
        return

    # Получаем аргумент команды
    parts = (message.text or "").split(maxsplit=1)
    argument = parts[1] if len(parts) > 1 else ""

    # Определяем дату отметки
    try:
        target_date = parse_day_arg(argument)
    except ValueError as error:
        await message.answer(str(error))
        return

    today = local_date()

    # Не разрешаем переносить отметку на предыдущий месяц
    if target_date.month != today.month or target_date.year != today.year:
        await message.answer(
            "❌ Нельзя отметить вчерашний день, "
            "если он относится к предыдущему месяцу."
        )
        return

    date_str = target_date.isoformat()
    month_str = target_date.strftime("%Y-%m")

    user = message.from_user

    # Сохраняем участника
    upsert_member(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name
    )

    # Добавляем отметку
    added = add_note(
        user_id=user.id,
        date=date_str,
        month=month_str,
        source="command_done",
        message_id=message.message_id
    )

    if added:
        await message.answer(
            f"💪 {user.full_name}, +1 очко! "
            f"Отметка за {date_str} засчитана!"
        )
    else:
        await message.answer(
            f"ℹ️ {user.full_name}, тренировка за "
            f"{date_str} уже засчитана!"
        )

@dp.message(
    F.chat.id == CHAT_ID,
    Command("undo")
)
async def undo_handler(
    message: Message,
    command: CommandObject
):
    if message.from_user is None or message.from_user.is_bot:
        return

    argument = command.args or ""

    try:
        target_date = parse_day_arg(argument)
    except ValueError as error:
        await message.answer(str(error))
        return

    today = local_date()

    if target_date.month != today.month or target_date.year != today.year:
        await message.answer(
            "❌ Нельзя отменить отметку за предыдущий месяц."
        )
        return

    date_str = target_date.isoformat()
    user = message.from_user

    removed = remove_note(
        user_id=user.id,
        date=date_str
    )

    if removed:
        await message.answer(
            f"↩️ {user.full_name}, отметка за {date_str} отменена."
        )
    else:
        await message.answer(
            f"ℹ️ {user.full_name}, отметка за {date_str} не найдена."
        )

@dp.message(
    F.chat.id == CHAT_ID,
    Command("stats")
)
async def stats_handler(message: Message):
    today = local_date()
    month_str = today.strftime("%Y-%m")

    scores = get_month_scores(month_str)

    if not scores:
        await message.answer(
            "📊 Пока в этом месяце никто не набрал очков."
        )
        return

    # Сортируем участников по количеству очков
    scores.sort(
        key=lambda member: member["score"],
        reverse=True
    )

    lines = [
        f"🏆 Рейтинг NoExcusesClub за {today.strftime('%m.%Y')}",
        ""
    ]

    for position, member in enumerate(scores, start=1):
        name = (
            member["full_name"]
            or member["username"]
            or f"Участник {member['user_id']}"
        )

        score = member["score"]

        lines.append(
            f"{position}. {name} — {score} очк."
        )

    await message.answer("\n".join(lines))

# Временная команда для проверки недельного отчёта
# @dp.message(
#     F.chat.id == CHAT_ID,
#     Command("testreport")
# )
# async def test_report_handler(message: Message):
#     await send_weekly_report(bot)

# @dp.message(
#     F.chat.id == CHAT_ID,
#     Command("testmonthly")
# )
# async def test_monthly_handler(message: Message):
#     await send_monthly_report(bot, test_mode=True)

# @dp.message(
#     F.chat.id == CHAT_ID,
#     Command("testmonthlyreal")
# )
# async def test_monthly_real_handler(message: Message):
#     await send_monthly_report(bot)

@dp.message(
    F.chat.id == CHAT_ID,
    Command("winners")
)
async def winners_handler(message: Message):
    results = get_all_month_results()

    if not results:
        await message.answer("🏆 История победителей пока пуста.")
        return

    lines = [
        "🏆 ИСТОРИЯ ПРОШЛЫХ СЕЗОНОВ NoExcusesClub",
        ""
    ]

    for result in results:
        month = result["month"]
        winner_name = result["winner_name"]
        winner_score = result["winner_score"]

        month_display = (
            f"{month[5:7]}.{month[:4]}"
        )

        if winner_name:
            lines.append(
                f"🗓 {month_display}\n"
                f"🥇 {winner_name} — {winner_score} очк.\n"
            )
        else:
            lines.append(
                f"📅 {month_display}\n"
                "Победителей пока нет.\n"
            )

    await message.answer("\n".join(lines))

# Обработчик видео-кружков только из целевой группы
@dp.message(
    F.chat.id == CHAT_ID,
    F.video_note
)
async def video_note_handler(message: Message):

    # Игнорируем сообщения без обычного пользователя
    if message.from_user is None:
        return

    # Игнорируем сообщения от ботов
    if message.from_user.is_bot:
        return

    user = message.from_user

    # Получаем текущую дату
    today = local_date()
    date_str = today.isoformat()
    month_str = today.strftime("%Y-%m")

    # Сохраняем информацию об участнике
    upsert_member(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name
    )

    # Пытаемся добавить спортивную отметку
    added = add_note(
        user_id=user.id,
        date=date_str,
        month=month_str,
        source="video_note",
        message_id=message.message_id
    )

    # Если отметка уже существует — ничего не отправляем
    if not added:
        logging.info(
            f"Повторный кружок: {user.full_name}, {date_str}"
        )
        return

    # Подтверждаем начисление очка
    await message.answer(
        f"💪 {user.full_name}, +1 очко! Отличная работа!"
    )

    logging.info(
        f"Засчитано +1 очко: {user.full_name}, {date_str}"
    )


# Главная функция

# Главная функция
async def main():
    logging.info("Initializing database...")

    # Инициализация базы данных
    init_db()

    # Создание планировщика
    scheduler = setup_scheduler(bot)

    # Регистрация команд бота
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="done", description="Засчитать тренировку"),
        BotCommand(command="undo", description="Отменить отметку"),
        BotCommand(command="stats", description="Текущий рейтинг"),
        BotCommand(command="winners", description="История победителей"),
        BotCommand(command="mystats", description="Моя статистика"),
        BotCommand(command="mytitles", description="Мои титулы"),
    ])

    try:
        # Запуск планировщика
        logging.info("Запускаем планировщик...")
        scheduler.start()

        logging.info("NoExcusesClub запускается...")

        # Запуск Telegram-бота
        await dp.start_polling(bot)

    finally:
        # Корректное завершение работы
        logging.info("Останавливаем планировщик...")
        if scheduler.running:
            scheduler.shutdown(wait=False)

        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
