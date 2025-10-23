import sqlite3
import logging
from config import BOT_CONFIG

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_name='loyalty.db'):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_name, check_same_thread=False)

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                bonus_points INTEGER DEFAULT 100,
                registration_complete BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица транзакций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                points_change INTEGER,
                description TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        # Таблица бронирований
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                guests INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        # Таблица запросов на списание
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS redemption_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                points_amount INTEGER,
                status TEXT DEFAULT 'pending',
                admin_id INTEGER,
                processed_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        conn.commit()
        conn.close()
        logger.info("База данных инициализирована")

    def create_user(self, telegram_id, first_name, last_name, phone):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Проверяем максимальный user_id
            cursor.execute('SELECT MAX(user_id) FROM users')
            max_id = cursor.fetchone()[0] or 0

            if max_id >= BOT_CONFIG['max_user_id']:
                raise Exception("Достигнут лимит пользователей")

            new_user_id = max_id + 1

            # Создаем пользователя
            cursor.execute('''
                INSERT INTO users (user_id, telegram_id, first_name, last_name, phone, bonus_points, registration_complete)
                VALUES (?, ?, ?, ?, ?, ?, TRUE)
            ''', (new_user_id, telegram_id, first_name, last_name, phone, BOT_CONFIG['welcome_bonus']))

            # Записываем приветственные бонусы
            cursor.execute('''
                INSERT INTO transactions (user_id, points_change, description)
                VALUES (?, ?, ?)
            ''', (new_user_id, BOT_CONFIG['welcome_bonus'], 'Приветственные бонусы за регистрацию'))

            conn.commit()
            logger.info(f"Создан пользователь {new_user_id}: {first_name} {last_name}")
            return new_user_id

        except sqlite3.IntegrityError:
            conn.rollback()
            raise Exception("Пользователь уже зарегистрирован")
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_user_by_telegram_id(self, telegram_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, telegram_id, first_name, last_name, phone, bonus_points, registration_complete
            FROM users WHERE telegram_id = ?
        ''', (telegram_id,))
        user = cursor.fetchone()
        conn.close()
        return user

    def get_user_by_id(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user

    def get_all_users(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, telegram_id, first_name, last_name, phone, bonus_points 
            FROM users WHERE registration_complete = TRUE
        ''')
        users = cursor.fetchall()
        conn.close()
        return users

    def update_user_points(self, user_id, points_change, description):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Обновляем баллы пользователя
            cursor.execute('''
                UPDATE users SET bonus_points = bonus_points + ? 
                WHERE user_id = ? AND bonus_points + ? >= 0
            ''', (points_change, user_id, points_change))

            if cursor.rowcount == 0:
                raise Exception("Недостаточно баллов")

            # Записываем транзакцию
            cursor.execute('''
                INSERT INTO transactions (user_id, points_change, description)
                VALUES (?, ?, ?)
            ''', (user_id, points_change, description))

            conn.commit()
            logger.info(f"Обновлены баллы пользователя {user_id}: {points_change}")

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def add_purchase(self, user_id, amount):
        cashback = int(amount * BOT_CONFIG['cashback_percent'] / 100)
        self.update_user_points(user_id, cashback, f'Кэшбек {BOT_CONFIG["cashback_percent"]}% с покупки {amount} руб.')
        return cashback

    def create_redemption_request(self, user_id, points_amount):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Проверяем достаточно ли баллов
            cursor.execute('SELECT bonus_points FROM users WHERE user_id = ?', (user_id,))
            current_points = cursor.fetchone()[0]

            if current_points < points_amount:
                raise Exception("Недостаточно баллов")

            cursor.execute('''
                INSERT INTO redemption_requests (user_id, points_amount)
                VALUES (?, ?)
            ''', (user_id, points_amount))

            request_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Создан запрос на списание {points_amount} баллов от пользователя {user_id}")
            return request_id

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_pending_redemption_requests(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.id, r.user_id, r.points_amount, u.first_name, u.last_name, u.phone
            FROM redemption_requests r
            JOIN users u ON r.user_id = u.user_id
            WHERE r.status = 'pending'
        ''')
        requests = cursor.fetchall()
        conn.close()
        return requests

    def process_redemption_request(self, request_id, admin_id, approve=True):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Получаем информацию о запросе
            cursor.execute('''
                SELECT user_id, points_amount FROM redemption_requests 
                WHERE id = ? AND status = 'pending'
            ''', (request_id,))
            request = cursor.fetchone()

            if not request:
                raise Exception("Запрос не найден или уже обработан")

            user_id, points_amount = request

            if approve:
                # Списание баллов
                self.update_user_points(user_id, -points_amount, f'Списание бонусов по заявке #{request_id}')

            # Обновляем статус запроса
            cursor.execute('''
                UPDATE redemption_requests 
                SET status = ?, admin_id = ?, processed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', ('approved' if approve else 'rejected', admin_id, request_id))

            conn.commit()
            logger.info(f"Запрос на списание {request_id} {'одобрен' if approve else 'отклонен'}")
            return user_id, points_amount

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def create_booking(self, user_id, date, time, guests):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO bookings (user_id, date, time, guests)
                VALUES (?, ?, ?, ?)
            ''', (user_id, date, time, guests))

            booking_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Создано бронирование {booking_id} для пользователя {user_id}")
            return booking_id

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_user_transactions(self, user_id, limit=10):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT points_change, description, timestamp 
            FROM transactions 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (user_id, limit))
        transactions = cursor.fetchall()
        conn.close()
        return transactions