import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from database import Database
from config import ADMIN_IDS

# Настройка логирования
logger = logging.getLogger(__name__)
db = Database()

# Состояния для админ-панели
ADMIN_ADD_POINTS_USER, ADMIN_ADD_POINTS_AMOUNT = range(2)
ADMIN_REMOVE_POINTS_USER, ADMIN_REMOVE_POINTS_AMOUNT = range(2, 4)
ADMIN_ADD_PURCHASE_USER, ADMIN_ADD_PURCHASE_AMOUNT = range(4, 6)

def get_bot():
    from main import application
    return application

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /admin"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Доступ запрещен")
        return

    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 Список пользователей", callback_data="admin_users")],
        [InlineKeyboardButton("⭐ Начислить баллы", callback_data="admin_add_points")],
        [InlineKeyboardButton("💰 Добавить покупку (5%)", callback_data="admin_add_purchase")],
        [InlineKeyboardButton("➖ Списать баллы", callback_data="admin_remove_points")],
        [InlineKeyboardButton("🔄 Запросы на списание", callback_data="admin_redemptions")],
        [InlineKeyboardButton("📢 Сделать рассылку", callback_data="admin_broadcast")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👑 Панель администратора\n\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )


async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок админ-панели"""
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        await query.edit_message_text("❌ Доступ запрещен")
        return

    if query.data == "admin_stats":
        await show_admin_stats(query)
    elif query.data == "admin_users":
        await show_users_list(query)
    elif query.data == "admin_redemptions":
        await show_redemption_requests(query)
    elif query.data == "admin_add_points":
        await start_add_points(query, context)
    elif query.data == "admin_remove_points":
        await start_remove_points(query, context)
    elif query.data == "admin_add_purchase":
        await start_add_purchase(query, context)
    elif query.data.startswith("admin_approve_"):
        await process_redemption_request(query, approve=True)
    elif query.data.startswith("admin_reject_"):
        await process_redemption_request(query, approve=False)
    elif query.data == "admin_back":
        await admin_back_handler(query, context)


async def show_admin_stats(query):
    """Показать статистику системы"""
    users = db.get_all_users()
    total_users = len(users)
    total_points = sum(user[5] for user in users)

    # Получаем pending запросы
    pending_requests = db.get_pending_redemption_requests()
    total_pending_points = sum(req[2] for req in pending_requests)

    stats_text = f"""
📊 Статистика системы:

👥 Всего пользователей: {total_users}
💎 Всего баллов в системе: {total_points}
⭐ Средний баланс: {total_points / total_users if total_users > 0 else 0:.1f}

🔄 Ожидающие запросы: {len(pending_requests)}
💎 Сумма запросов: {total_pending_points} баллов

💰 Общая стоимость баллов: {total_points} руб.
    """

    keyboard = [[InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(stats_text, reply_markup=reply_markup)


async def show_users_list(query):
    """Показать список пользователей"""
    users = db.get_all_users()

    if not users:
        await query.edit_message_text("👥 Пользователи не найдены")
        return

    users_text = "👥 Список пользователей:\n\n"
    for user in users[:15]:  # Показываем первые 15
        users_text += f"🆔 {user[0]} | 👤 {user[2]} {user[3]}\n"
        users_text += f"   📱 {user[4]} | 💎 {user[5]} баллов\n\n"

    if len(users) > 15:
        users_text += f"... и еще {len(users) - 15} пользователей"

    keyboard = [[InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(users_text, reply_markup=reply_markup)


async def show_redemption_requests(query):
    """Показать ожидающие запросы на списание"""
    requests = db.get_pending_redemption_requests()

    if not requests:
        await query.edit_message_text("✅ Нет ожидающих запросов на списание")
        return

    requests_text = "🔄 Ожидающие запросы на списание:\n\n"
    for req in requests:
        req_id, user_id, points, first_name, last_name, phone = req
        requests_text += f"📅 Запрос #{req_id}\n"
        requests_text += f"👤 {first_name} {last_name} (ID: {user_id})\n"
        requests_text += f"📱 {phone}\n"
        requests_text += f"💎 {points} баллов | 💰 {points} руб.\n"
        requests_text += "   ✅ / ❌\n\n"

    # Добавляем кнопки для каждого запроса
    keyboard = []
    for req in requests:
        req_id = req[0]
        keyboard.append([
            InlineKeyboardButton(f"✅ Одобрить #{req_id}", callback_data=f"admin_approve_{req_id}"),
            InlineKeyboardButton(f"❌ Отклонить #{req_id}", callback_data=f"admin_reject_{req_id}")
        ])

    keyboard.append([InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(requests_text, reply_markup=reply_markup)


async def process_redemption_request(query, approve=True):
    """Обработать запрос на списание баллов"""
    request_id = int(query.data.split('_')[2])

    try:
        result = db.process_redemption_request(request_id, query.from_user.id, approve)
        if not result:
            await query.edit_message_text("❌ Запрос не найден или уже обработан")
            return

        user_id, points_amount = result
        user = db.get_user_by_id(user_id)

        if not user:
            await query.edit_message_text("❌ Пользователь не найден")
            return

        # Уведомляем пользователя
        bot_app = get_bot()
        try:
            if approve:
                user_message = f"""
✅ Ваш запрос на списание одобрен!

💎 Списано баллов: {points_amount}
💰 Сумма: {points_amount} руб.
🎫 Номер заявки: #{request_id}

💳 Обратитесь к администратору для получения средств.
                """
            else:
                user_message = f"""
❌ Ваш запрос на списание отклонен

💎 Запрошенные баллы: {points_amount}
🎫 Номер заявки: #{request_id}

📞 Для уточнения причин обратитесь к администратору.
                """

            await bot_app.bot.send_message(user[1], user_message)
        except Exception as e:
            logger.error(f"Ошибка уведомления пользователя: {e}")

        # Обновляем сообщение админу
        status = "ОДОБРЕН" if approve else "ОТКЛОНЕН"
        emoji = "✅" if approve else "❌"

        result_text = f"""
{emoji} Запрос #{request_id} {status}

👤 Пользователь: {user[2]} {user[3]}
🆔 ID: {user[0]}
💎 Баллов: {points_amount}
💰 Сумма: {points_amount} руб.
👑 Обработал: {query.from_user.first_name}
        """

        keyboard = [[InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(result_text, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Ошибка обработки запроса: {e}")
        await query.edit_message_text(f"❌ Ошибка обработки запроса: {str(e)}")


# ===== НАЧИСЛЕНИЕ БАЛЛОВ =====
async def start_add_points(query, context: ContextTypes.DEFAULT_TYPE):
    """Начать процесс начисления баллов"""
    await query.edit_message_text(
        "⭐ Начисление баллов\n\n"
        "Введите ID пользователя или номер телефона:"
    )
    return ADMIN_ADD_POINTS_USER


async def get_user_for_add_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить пользователя для начисления баллов"""
    user_input = update.message.text.strip()

    try:
        if user_input.isdigit() and len(user_input) <= 4:  # ID пользователя
            user_id = int(user_input)
            user = db.get_user_by_id(user_id)
        else:  # Поиск по телефону
            users = db.get_all_users()
            user = next((u for u in users if u[4] == user_input), None)

        if not user:
            await update.message.reply_text("❌ Пользователь не найден. Попробуйте снова:")
            return ADMIN_ADD_POINTS_USER

        context.user_data['admin_add_user'] = user
        await update.message.reply_text(
            f"👤 Найден пользователь:\n"
            f"🆔 ID: {user[0]}\n"
            f"👤 Имя: {user[2]} {user[3]}\n"
            f"📱 Телефон: {user[4]}\n"
            f"💎 Текущий баланс: {user[5]}\n\n"
            f"Введите количество баллов для начисления:"
        )
        return ADMIN_ADD_POINTS_AMOUNT

    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Введите ID (число) или телефон:")
        return ADMIN_ADD_POINTS_USER


async def get_amount_for_add_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить количество баллов для начисления"""
    try:
        amount = int(update.message.text.strip())
        if amount <= 0:
            await update.message.reply_text("❌ Количество баллов должно быть положительным. Введите снова:")
            return ADMIN_ADD_POINTS_AMOUNT

        user = context.user_data['admin_add_user']

        # Начисляем баллы
        db.update_user_points(user[0], amount, f"Начисление администратором")

        # Уведомляем пользователя
        bot_app = get_bot()
        try:
            await bot_app.bot.send_message(
                user[1],
                f"🎉 Вам начислены бонусные баллы!\n\n"
                f"💎 +{amount} баллов\n"
                f"📝 Причина: Начисление администратором\n"
                f"💳 Новый баланс: {user[5] + amount}"
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления пользователя: {e}")

        await update.message.reply_text(
            f"✅ Баллы успешно начислены!\n\n"
            f"👤 Пользователь: {user[2]} {user[3]}\n"
            f"🆔 ID: {user[0]}\n"
            f"💎 Начислено: +{amount} баллов\n"
            f"💳 Новый баланс: {user[5] + amount}"
        )

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ Введите корректное число:")
        return ADMIN_ADD_POINTS_AMOUNT


# ===== ДОБАВЛЕНИЕ ПОКУПКИ (5% КЭШБЕК) =====
async def start_add_purchase(query, context: ContextTypes.DEFAULT_TYPE):
    """Начать процесс добавления покупки"""
    await query.edit_message_text(
        "💰 Добавление покупки (5% кэшбек)\n\n"
        "Введите ID пользователя или номер телефона:"
    )
    return ADMIN_ADD_PURCHASE_USER


async def get_user_for_add_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить пользователя для добавления покупки"""
    user_input = update.message.text.strip()

    try:
        if user_input.isdigit() and len(user_input) <= 4:  # ID пользователя
            user_id = int(user_input)
            user = db.get_user_by_id(user_id)
        else:  # Поиск по телефону
            users = db.get_all_users()
            user = next((u for u in users if u[4] == user_input), None)

        if not user:
            await update.message.reply_text("❌ Пользователь не найден. Попробуйте снова:")
            return ADMIN_ADD_PURCHASE_USER

        context.user_data['admin_purchase_user'] = user
        await update.message.reply_text(
            f"👤 Найден пользователь:\n"
            f"🆔 ID: {user[0]}\n"
            f"👤 Имя: {user[2]} {user[3]}\n"
            f"📱 Телефон: {user[4]}\n"
            f"💎 Текущий баланс: {user[5]}\n\n"
            f"Введите сумму покупки (руб.):"
        )
        return ADMIN_ADD_PURCHASE_AMOUNT

    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Введите ID (число) или телефон:")
        return ADMIN_ADD_PURCHASE_USER


async def get_amount_for_add_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить сумму покупки и начислить кэшбек"""
    try:
        amount = int(update.message.text.strip())
        if amount <= 0:
            await update.message.reply_text("❌ Сумма должна быть положительной. Введите снова:")
            return ADMIN_ADD_PURCHASE_AMOUNT

        user = context.user_data['admin_purchase_user']

        # Начисляем кэшбек 5%
        cashback = db.add_purchase(user[0], amount)

        # Уведомляем пользователя
        bot_app = get_bot()
        try:
            await bot_app.bot.send_message(
                user[1],
                f"🎉 Вам начислен кэшбек за покупку!\n\n"
                f"💰 Сумма покупки: {amount} руб.\n"
                f"💎 Начислено баллов: +{cashback} (5%)\n"
                f"💳 Новый баланс: {user[5] + cashback}"
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления пользователя: {e}")

        await update.message.reply_text(
            f"✅ Покупка добавлена!\n\n"
            f"👤 Пользователь: {user[2]} {user[3]}\n"
            f"🆔 ID: {user[0]}\n"
            f"💰 Сумма покупки: {amount} руб.\n"
            f"💎 Начислено баллов: +{cashback} (5%)\n"
            f"💳 Новый баланс: {user[5] + cashback}"
        )

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ Введите корректную сумму:")
        return ADMIN_ADD_PURCHASE_AMOUNT


# ===== ПРИНУДИТЕЛЬНОЕ СПИСАНИЕ БАЛЛОВ =====
async def start_remove_points(query, context: ContextTypes.DEFAULT_TYPE):
    """Начать процесс принудительного списания баллов"""
    await query.edit_message_text(
        "➖ Принудительное списание баллов\n\n"
        "Введите ID пользователя или номер телефона:"
    )
    return ADMIN_REMOVE_POINTS_USER


async def get_user_for_remove_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить пользователя для списания баллов"""
    user_input = update.message.text.strip()

    try:
        if user_input.isdigit() and len(user_input) <= 4:  # ID пользователя
            user_id = int(user_input)
            user = db.get_user_by_id(user_id)
        else:  # Поиск по телефону
            users = db.get_all_users()
            user = next((u for u in users if u[4] == user_input), None)

        if not user:
            await update.message.reply_text("❌ Пользователь не найден. Попробуйте снова:")
            return ADMIN_REMOVE_POINTS_USER

        context.user_data['admin_remove_user'] = user
        await update.message.reply_text(
            f"👤 Найден пользователь:\n"
            f"🆔 ID: {user[0]}\n"
            f"👤 Имя: {user[2]} {user[3]}\n"
            f"📱 Телефон: {user[4]}\n"
            f"💎 Текущий баланс: {user[5]}\n\n"
            f"Введите количество баллов для списания:"
        )
        return ADMIN_REMOVE_POINTS_AMOUNT

    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Введите ID (число) или телефон:")
        return ADMIN_REMOVE_POINTS_USER


async def get_amount_for_remove_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить количество баллов для списания"""
    try:
        amount = int(update.message.text.strip())
        user = context.user_data['admin_remove_user']

        if amount <= 0:
            await update.message.reply_text("❌ Количество баллов должно быть положительным. Введите снова:")
            return ADMIN_REMOVE_POINTS_AMOUNT

        if amount > user[5]:
            await update.message.reply_text(
                f"❌ Недостаточно баллов. Доступно: {user[5]}\n"
                f"Введите другое количество:"
            )
            return ADMIN_REMOVE_POINTS_AMOUNT

        # Списываем баллы
        db.update_user_points(user[0], -amount, f"Списание администратором")

        # Уведомляем пользователя
        bot_app = get_bot()
        try:
            await bot_app.bot.send_message(
                user[1],
                f"📋 Уведомление о списании баллов\n\n"
                f"💎 Списано: {amount} баллов\n"
                f"📝 Причина: Списание администратором\n"
                f"💳 Новый баланс: {user[5] - amount}"
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления пользователя: {e}")

        await update.message.reply_text(
            f"✅ Баллы успешно списаны!\n\n"
            f"👤 Пользователь: {user[2]} {user[3]}\n"
            f"🆔 ID: {user[0]}\n"
            f"💎 Списано: {amount} баллов\n"
            f"💳 Новый баланс: {user[5] - amount}"
        )

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ Введите корректное число:")
        return ADMIN_REMOVE_POINTS_AMOUNT


async def admin_back_handler(query, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться в главное меню админки"""
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 Список пользователей", callback_data="admin_users")],
        [InlineKeyboardButton("⭐ Начислить баллы", callback_data="admin_add_points")],
        [InlineKeyboardButton("💰 Добавить покупку (5%)", callback_data="admin_add_purchase")],
        [InlineKeyboardButton("➖ Списать баллы", callback_data="admin_remove_points")],
        [InlineKeyboardButton("🔄 Запросы на списание", callback_data="admin_redemptions")],
        [InlineKeyboardButton("📢 Сделать рассылку", callback_data="admin_broadcast")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "👑 Панель администратора\n\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )


async def cancel_admin_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена операции админ-панели"""
    await update.message.reply_text("❌ Операция отменена.")
    context.user_data.clear()
    return ConversationHandler.END


# Создание ConversationHandler для админ-панели
def get_admin_conversation_handlers():
    """Возвращает все ConversationHandler для админ-панели"""

    admin_add_points_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_points, pattern='^admin_add_points$')],
        states={
            ADMIN_ADD_POINTS_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_user_for_add_points)],
            ADMIN_ADD_POINTS_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount_for_add_points)]
        },
        fallbacks=[CommandHandler('cancel', cancel_admin_operation)],
        name="admin_add_points"
    )

    admin_remove_points_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_remove_points, pattern='^admin_remove_points$')],
        states={
            ADMIN_REMOVE_POINTS_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_user_for_remove_points)],
            ADMIN_REMOVE_POINTS_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount_for_remove_points)]
        },
        fallbacks=[CommandHandler('cancel', cancel_admin_operation)],
        name="admin_remove_points"
    )

    admin_add_purchase_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_purchase, pattern='^admin_add_purchase$')],
        states={
            ADMIN_ADD_PURCHASE_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_user_for_add_purchase)],
            ADMIN_ADD_PURCHASE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount_for_add_purchase)]
        },
        fallbacks=[CommandHandler('cancel', cancel_admin_operation)],
        name="admin_add_purchase"
    )

    return [admin_add_points_conv, admin_remove_points_conv, admin_add_purchase_conv]