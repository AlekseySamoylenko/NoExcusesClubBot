from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import TZ, WEEKLY_REPORT_TIME, MONTH_RESULT_TIME
from reports import send_weekly_report
from monthly_report import send_monthly_report


def setup_scheduler(bot):
    scheduler = AsyncIOScheduler(timezone=ZoneInfo(TZ))

    report_hour, report_minute = map(
        int, WEEKLY_REPORT_TIME.split(":")
    )

    scheduler.add_job(
        send_weekly_report,
        trigger="cron",
        day_of_week="sun",
        hour=report_hour,
        minute=report_minute,
        args=[bot],
        id="weekly_report",
        replace_existing=True
    )

    month_hour, month_minute = map(
        int, MONTH_RESULT_TIME.split(":")
    )

    scheduler.add_job(
        send_monthly_report,
        trigger="cron",
        day=1,
        hour=month_hour,
        minute=month_minute,
        args=[bot],
        id="monthly_report",
        replace_existing=True
    )

    print(
        f"Еженедельный отчёт запланирован: "
        f"каждое воскресенье в {WEEKLY_REPORT_TIME} ({TZ})"
    )

    print(
        f"Месячные итоги запланированы: "
        f"1-го числа каждого месяца в {MONTH_RESULT_TIME} ({TZ})"
    )

    return scheduler
