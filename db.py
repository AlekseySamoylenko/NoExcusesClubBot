
import sqlite3
from time_utils import local_now
from contextlib import contextmanager

from config import DATABASE_PATH


# ==========================================
# ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ
# ==========================================

@contextmanager
def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


# ==========================================
# СОЗДАНИЕ ТАБЛИЦ
# ==========================================

def init_db():
    with get_connection() as conn:

        # Таблица спортивных отметок
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                month TEXT NOT NULL,
                source TEXT NOT NULL,
                message_id INTEGER,
                created_at TEXT NOT NULL,

                UNIQUE(user_id, date)
            )
        """)

        # Индекс для быстрого поиска по месяцу
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_month
            ON notes(month)
        """)

        # Таблица участников
        conn.execute("""
            CREATE TABLE IF NOT EXISTS members (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                last_seen TEXT NOT NULL
            )
        """)

        # Таблица результатов турниров
        conn.execute("""
            CREATE TABLE IF NOT EXISTS month_results (
                month TEXT PRIMARY KEY,
                winner_name TEXT,
                winner_score INTEGER,
                announced_at TEXT NOT NULL
            )
        """)

        # Таблица личных титулов участников
        conn.execute("""
            CREATE TABLE IF NOT EXISTS month_winners (
                month TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                winner_name TEXT,
                winner_score INTEGER NOT NULL,

                PRIMARY KEY (month, user_id)
            )
        """)

        # Таблица отправленных отчётов
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports_log (
                date TEXT NOT NULL,
                kind TEXT NOT NULL,
                sent_at TEXT NOT NULL,

                PRIMARY KEY(date, kind)
            )
        """)

    print("Database initialized successfully!")


# ==========================================
# ДОБАВЛЕНИЕ СПОРТИВНОЙ ОТМЕТКИ
# ==========================================

def add_note(
    user_id: int,
    date: str,
    month: str,
    source: str,
    message_id: int | None = None
) -> bool:

    created_at = local_now().isoformat()

    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT OR IGNORE INTO notes (
                user_id,
                date,
                month,
                source,
                message_id,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            date,
            month,
            source,
            message_id,
            created_at
        ))

        return cursor.rowcount == 1


# ==========================================
# УДАЛЕНИЕ СПОРТИВНОЙ ОТМЕТКИ
# ==========================================

def remove_note(user_id: int, date: str) -> bool:

    with get_connection() as conn:
        cursor = conn.execute("""
            DELETE FROM notes
            WHERE user_id = ? AND date = ?
        """, (user_id, date))

        return cursor.rowcount == 1


# ==========================================
# ПОЛУЧЕНИЕ СТАТИСТИКИ ЗА МЕСЯЦ
# ==========================================

def get_month_scores(month: str) -> list[dict]:

    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                notes.user_id,
                COUNT(notes.id) AS score,
                members.username,
                members.full_name
            FROM notes
            LEFT JOIN members
                ON notes.user_id = members.user_id
            WHERE notes.month = ?
            GROUP BY notes.user_id
            ORDER BY score DESC, notes.user_id ASC
        """, (month,)).fetchall()

        return [dict(row) for row in rows]


# ==========================================
# ПОЛУЧЕНИЕ ПОБЕДИТЕЛЕЙ МЕСЯЦА
# ==========================================

def get_month_winners(month: str) -> list[dict]:
    scores = get_month_scores(month)

    if not scores:
        return []

    # Максимальное количество очков
    max_score = scores[0]["score"]

    # Все участники с максимальным результатом
    winners = [
        member
        for member in scores
        if member["score"] == max_score
    ]

    return winners


# ==========================================
# ПОЛУЧЕНИЕ СТАТИСТИКИ ЗА НЕДЕЛЮ
# ==========================================

def get_week_scores(
    start_date: str,
    end_date: str
) -> list[dict]:

    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                notes.user_id,
                COUNT(notes.id) AS score,
                members.username,
                members.full_name
            FROM notes
            LEFT JOIN members
                ON notes.user_id = members.user_id
            WHERE notes.date BETWEEN ? AND ?
            GROUP BY notes.user_id
            ORDER BY score DESC, notes.user_id ASC
        """, (start_date, end_date)).fetchall()

        return [dict(row) for row in rows]


# ==========================================
# ОБНОВЛЕНИЕ ИНФОРМАЦИИ ОБ УЧАСТНИКЕ
# ==========================================

def upsert_member(
    user_id: int,
    username: str | None,
    full_name: str
):
    last_seen = local_now().isoformat()

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO members (
                user_id,
                username,
                full_name,
                last_seen
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name,
                last_seen = excluded.last_seen
        """, (
            user_id,
            username,
            full_name,
            last_seen
        ))


# ==========================================
# СОХРАНЕНИЕ ИТОГОВ ТУРНИРА
# ==========================================

def save_month_result(
    month: str,
    winner_name: str | None,
    winner_score: int | None,
    winner_user_ids: list[int] | None = None
) -> bool:

    announced_at = local_now().isoformat()

    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT OR IGNORE INTO month_results (
                month,
                winner_name,
                winner_score,
                announced_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            month,
            winner_name,
            winner_score,
            announced_at
        ))

        # Если результат уже сохранён, повторно титулы не записываем
        if cursor.rowcount == 0:
            return False

        # Сохраняем каждого победителя отдельно
        if winner_user_ids and winner_score is not None:
            for user_id in winner_user_ids:
                conn.execute("""
                    INSERT OR IGNORE INTO month_winners (
                        month,
                        user_id,
                        winner_name,
                        winner_score
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    month,
                    user_id,
                    winner_name,
                    winner_score
                ))

        return True


# ==========================================
# ПРОВЕРКА И РЕГИСТРАЦИЯ ОТЧЁТОВ
# ==========================================

def was_reported(date: str, kind: str) -> bool:

    with get_connection() as conn:
        row = conn.execute("""
            SELECT 1
            FROM reports_log
            WHERE date = ? AND kind = ?
        """, (date, kind)).fetchone()

        return row is not None


def log_report(date: str, kind: str) -> bool:

    sent_at = local_now().isoformat()

    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT OR IGNORE INTO reports_log (
                date,
                kind,
                sent_at
            )
            VALUES (?, ?, ?)
        """, (date, kind, sent_at))

        return cursor.rowcount == 1

def get_all_month_results():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT month, winner_name, winner_score
            FROM month_results
            ORDER BY month ASC
        """).fetchall()

    return [dict(row) for row in rows]

# ==========================================
# ЛИЧНАЯ СТАТИСТИКА
# ==========================================

def get_user_total_score(user_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT COUNT(*) AS total
            FROM notes
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        return row["total"]


def get_user_titles(user_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT month, winner_name, winner_score
            FROM month_winners
            WHERE user_id = ?
            ORDER BY month DESC
        """, (user_id,)).fetchall()

        return [dict(row) for row in rows]