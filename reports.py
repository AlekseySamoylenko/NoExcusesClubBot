
from datetime import timedelta

from aiogram import Bot

from config import CHAT_ID
from db import get_week_scores, was_reported, log_report
from time_utils import local_date


async def send_weekly_report(bot: Bot):
    today = local_date()

    # Определяем начало и конец недели
    start_date = today - timedelta(days=today.weekday())
    end_date = today

    start_str = start_date.isoformat()
    end_str = end_date.isoformat()

    # Проверяем, не отправляли ли уже отчёт за эту дату
    report_date = end_str

    if was_reported(report_date, "weekly"):
        print("Weekly report already sent.")
        return

    # Получаем статистику
    scores = get_week_scores(start_str, end_str)

    # Формируем заголовок
    lines = [
        "📊 ЕЖЕНЕДЕЛЬНЫЙ ОТЧЁТ NoExcusesClub",
        "",
        f"📅 Период: {start_date.strftime('%d.%m.%Y')} — "
        f"{end_date.strftime('%d.%m.%Y')}",
        ""
    ]

    if not scores:
        lines.append("На этой неделе пока нет отметок.")
    else:
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

    lines.extend([
        "",
        "💪 Продолжаем работать над собой!"
    ])

    report_text = "\n".join(lines)

    # Отправляем отчёт в группу
    await bot.send_message(
        chat_id=CHAT_ID,
        text=report_text
    )

    # Регистрируем отправленный отчёт
    log_report(report_date, "weekly")
