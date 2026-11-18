
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from config import TZ


# Часовой пояс проекта
MOSCOW_TZ = ZoneInfo(TZ)


def local_now() -> datetime:
    """Возвращает текущее время проекта."""
    return datetime.now(MOSCOW_TZ)


def local_date() -> date:
    """Возвращает сегодняшнюю локальную дату."""
    return local_now().date()


def parse_day_arg(argument: str = "") -> date:
    """
    Пустой аргумент = сегодня.
    yesterday = вчера.
    """

    argument = argument.strip().lower()

    if not argument:
        return local_date()

    if argument == "yesterday":
        return local_date() - timedelta(days=1)

    raise ValueError(
        "Использование: /done или /done yesterday"
    )


def prev_month() -> str:
    """Возвращает предыдущий месяц в формате YYYY-MM."""

    today = local_date()

    first_day = today.replace(day=1)
    last_day_previous_month = first_day - timedelta(days=1)

    return last_day_previous_month.strftime("%Y-%m")
