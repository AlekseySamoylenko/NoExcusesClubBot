
from datetime import timedelta

from aiogram import Bot
from time_utils import local_date

from config import CHAT_ID
from db import (
    get_month_winners,
    get_month_scores,
    save_month_result,
    was_reported,
    log_report
)


async def send_monthly_report(
    bot: Bot,
    test_mode: bool = False
):
    today = local_date()

    # Определяем предыдущий месяц
    first_day_current_month = today.replace(day=1)
    last_day_previous_month = first_day_current_month - timedelta(days=1)

    month = last_day_previous_month.strftime("%Y-%m")
    month_name = last_day_previous_month.strftime("%m.%Y")

    report_date = today.isoformat()

    # Проверяем повторную отправку
    if not test_mode and was_reported(report_date, "monthly"):
        print("Monthly report already sent.")
        return

    # Получаем полный рейтинг и победителей
    scores = get_month_scores(month)
    winners = get_month_winners(month)

    if not scores:
        report_text = (
            f"🏆 ИТОГИ NoExcusesClub за {month_name}\n\n"
            "В этом месяце нет участников с набранными очками."
        )

        winner_names = None
        winner_score = None

    else:
        winner_names = [
            member["full_name"]
            or member["username"]
            or f"Участник {member['user_id']}"
            for member in winners
        ]

        winner_score = winners[0]["score"]

        # Блок победителей
        report_text = (
            f"🏆 ИТОГИ NoExcusesClub за {month_name}\n\n"
            "🥇 Победитель"
            + ("и:" if len(winners) > 1 else ":")
            + "\n"
        )

        report_text += "\n".join(
            f"• {name}" for name in winner_names
        )

        report_text += (
            f"\n\n💪 Результат: {winner_score} очк."
        )

        # Остальные участники
        other_members = [
            member for member in scores
            if member["score"] < winner_score
        ]

        if other_members:
            report_text += "\n\n📊 Остальные участники:\n"

            current_rank = 0
            previous_score = None

            for index, member in enumerate(other_members, start=1):
                if member["score"] != previous_score:
                    current_rank = len(winners) + index

                name = (
                    member["full_name"]
                    or member["username"]
                    or f"Участник {member['user_id']}"
                )

                report_text += (
                    f"{current_rank}. {name} — "
                    f"{member['score']} очк.\n"
                )

                previous_score = member["score"]

        report_text += (
            "\n🔥 Каждый результат имеет значение. Продолжаем!"
        )

    # Отправляем сообщение в группу
    await bot.send_message(
        chat_id=CHAT_ID,
        text=report_text
    )

    # В тестовом режиме базу не изменяем
    if test_mode:
        print("Monthly report test sent. Database unchanged.")
        return

    # Сохраняем результат турнира
    save_month_result(
    month=month,
    winner_name=", ".join(winner_names) if winner_names else None,
    winner_score=winner_score,
    winner_user_ids=[
        member["user_id"] for member in winners
    ] if winners else None
    )   

    # Регистрируем отправку
    log_report(report_date, "monthly")
