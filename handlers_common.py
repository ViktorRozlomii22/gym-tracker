import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from database import (
    create_user, get_custom_exercises, get_user_trainings, 
    get_current_training, finish_training, create_training,
    delete_all_user_data
)
from utils_constants import *

logger = logging.getLogger(__name__)

def is_new_user(user_id):
    """Определяет новый ли пользователь (нет никаких записей в БД)"""
    # Проверяем есть ли ЛЮБЫЕ записи пользователя
    trainings = get_user_trainings(user_id, limit=1)
    current_training = get_current_training(user_id)
    custom_exercises = get_custom_exercises(user_id)
    
    has_any_data = (
        len(trainings) > 0 or 
        current_training is not None or
        len(custom_exercises['strength']) > 0 or 
        len(custom_exercises['cardio']) > 0
    )
    
    return not has_any_data

async def handle_unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений, когда бот не в активном состоянии"""
    if context.user_data.get('in_conversation'):
        return await handle_main_menu(update, context)
    
    user = update.message.from_user
    user_id = user.id
    
    # Создаем пользователя в БД если его нет
    create_user(user_id, user.username, user.first_name)
    
    # Определяем тип пользователя
    if is_new_user(user_id):
        return await show_welcome_new_user(update, context)
    else:
        return await show_welcome_existing_user(update, context)

async def show_welcome_new_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Привітствие для нового пользователя"""
    user = update.message.from_user
    
    welcome_text = f"""
👋 Привіт, {user.first_name}! 

Я твій щоденник тренувань! Допоможу записувати вправи, підходи, повторення, вагу та відстежувати прогрес.

Натисни «🚀 Почати», щоб розпочати!
    """
    
    keyboard = [['🚀 Почати']]
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return INACTIVE

async def show_welcome_existing_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Привітствие для существующего пользователя"""
    user = update.message.from_user
    user_id = user.id
    
    # Проверяем есть ли текущая тренировка
    current_training = get_current_training(user_id)
    
    if current_training:
        return await show_welcome_with_current_training(update, context, current_training)
    else:
        return await show_welcome_without_current_training(update, context)

async def show_welcome_with_current_training(update: Update, context: ContextTypes.DEFAULT_TYPE, current_training):
    """Привітствие когда есть текущая тренировка"""
    user = update.message.from_user
    
    welcome_text = f"""
👋 З поверненням, {user.first_name}! 

У тебе є незавершене тренування від {current_training['date_start']}.

Вибери дію:
    """
    
    keyboard = [
        ['🏃‍♂️ Продовжити тренування'],
        ['🆕 Почати нове тренування'],
        ['🗑️ Очистити історію']
    ]
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return INACTIVE

async def show_welcome_without_current_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Привітствие когда нет текущей тренировки"""
    user = update.message.from_user
    
    welcome_text = f"""
👋 З поверненням, {user.first_name}! 

Історію твоїх тренувань збережено.

Вибери дію:
    """
    
    keyboard = [
        ['🚀 Продовжити'],
        ['🗑️ Очистити історію']
    ]
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return INACTIVE

async def start_from_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка нажатия кнопки старта"""
    context.user_data['in_conversation'] = True
    return await start(update, context)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало работы с ботом - переход в главное меню"""
    user = update.message.from_user
    user_id = user.id
    
    # Создаем/обновляем пользователя в БД
    create_user(user_id, user.username, user.first_name)
    
    # Устанавливаем флаг активной конверсации
    context.user_data['in_conversation'] = True
    
    welcome_text = f"""
🎉 Вітаю, {user.first_name}! 

Вибери дію:
    """
    
    keyboard = [
        ['💪 Почати тренування', '📊 Історія тренувань'],
        ['🧭 Програми', '📋 Мій план', '🧠 Налаштувати план'],
        ['📝 Мої вправи', '📈 Статистика', '📏 Мої виміри'],
        ['📤 Експорт даних', '❓ Довідка']
    ]
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return MAIN_MENU

# Тексты кнопок главного меню (если пользователь в INACTIVE, но клавиатура осталась от главного меню)
_MAIN_MENU_BUTTON_TEXTS = frozenset(
    {
        "💪 Почати тренування",
        "📊 Історія тренувань",
        "📝 Мої вправи",
        "📈 Статистика",
        "📏 Мої виміри",
        "📤 Експорт даних",
        "❓ Довідка",
    }
)


async def handle_clear_data_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора в неактивном состоянии"""
    choice = (update.message.text or "").strip()
    user_id = update.message.from_user.id
    
    if choice == '🚀 Почати':
        return await start(update, context)
    
    elif choice == '🚀 Продовжити':
        return await start(update, context)
    
    elif choice == '🏃‍♂️ Продовжити тренування':
        from handlers_training import continue_training
        return await continue_training(update, context)
    
    elif choice == '🆕 Почати нове тренування':
        # Завершаем текущую тренировку и начинаем новую
        current_training = get_current_training(user_id)
        if current_training:
            finish_training(current_training['training_id'], "Автозавершена")
        
        from handlers_training import start_training
        return await start_training(update, context)
    
    elif choice == '🗑️ Очистити історію':
        return await show_clear_data_confirmation(update, context)

    elif choice in _MAIN_MENU_BUTTON_TEXTS:
        context.user_data["in_conversation"] = True
        return await handle_main_menu(update, context)
    
    else:
        # Показываем соответствующие кнопки
        if is_new_user(user_id):
            return await show_welcome_new_user(update, context)
        else:
            current_training = get_current_training(user_id)
            if current_training:
                return await show_welcome_with_current_training(update, context, current_training)
            else:
                return await show_welcome_without_current_training(update, context)

async def show_clear_data_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ подтверждения очистки данных"""
    warning_text = """
⚠️ УВАГА: ти збираєшся видалити всі свої дані!

Ця дія:
• Видалить усі тренування та виміри
• Видалить усі твої власні вправи
• Стандартні вправи залишаться
• Скасувати цю дію буде неможливо

Підтвердь дію:
    """
    
    keyboard = [
        ['✅ Так, видалити всі дані'],
        ['❌ Скасувати']
    ]
    
    await update.message.reply_text(
        warning_text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return CLEAR_DATA_CONFIRM

async def handle_clear_data_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка подтверждения очистки данных"""
    choice = update.message.text
    user_id = update.message.from_user.id
    
    if choice == '❌ Скасувати':
        return await start(update, context)
    
    elif choice == '✅ Так, видалити всі дані':
        # Удаляем все данные пользователя
        success = delete_all_user_data(user_id)
        
        if success:
            await update.message.reply_text(
                "✅ Усі твої дані видалено!",
                reply_markup=ReplyKeyboardRemove()
            )
            # Показываем приветствие для нового пользователя
            return await show_welcome_new_user(update, context)
        else:
            await update.message.reply_text(
                "❌ Не вдалося видалити дані. Спробуй пізніше.",
                reply_markup=ReplyKeyboardMarkup([['🚀 Продовжити']], resize_keyboard=True)
            )
            return INACTIVE
    
    else:
        await update.message.reply_text(
            "❌ Будь ласка, скористайся кнопками для підтвердження",
            reply_markup=ReplyKeyboardMarkup([
                ['✅ Так, видалити всі дані'],
                ['❌ Скасувати']
            ], resize_keyboard=True)
        )
        return CLEAR_DATA_CONFIRM

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Довідка"""
    help_text = """
🤖 **Щоденник тренувань — довідка**

💪 **Силові вправи:**
1. Вибери вправу зі списку
2. Додавай підходи у форматі: "Вага_кг Повторення"
3. Можна ввести кілька підходів одразу (кожен з нового рядка)

🏃 **Кардіо упражнения:**
1. Вибери кардіо зі списку
2. Вибери формат: Хв/Метри или Км/Год
3. Введи час і параметри

✏️ **Додавання вправ:**
- Нові вправи зберігаються у твоєму списку

📊 **Історія тренувань** - перегляд минулих тренувань
📈 **Статистика** - статистика за вибраний період
📏 **Мої виміри** - історія твоїх вимірів
📤 **Експорт даних** - Excel (підсумок + подробиці) или CSV для Google Таблиць
    """
    
    from diary import HELP
    await update.message.reply_text(HELP)
    return MAIN_MENU

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка главного меню"""
    msg = update.effective_message
    if not msg:
        return MAIN_MENU
    text = (msg.text or "").strip()
    user_id = msg.from_user.id
    
    if text == '💪 Почати тренування':
        from handlers_training import start_training
        return await start_training(update, context)
    elif text == '📊 Історія тренувань':
        from handlers_training import show_training_history
        return await show_training_history(update, context)
    elif text == '📝 Мої вправи':
        from handlers_exercises import show_exercises_management
        return await show_exercises_management(update, context)
    elif text == '📈 Статистика':
        from handlers_statistics import show_statistics_menu
        return await show_statistics_menu(update, context)
    elif text == '📏 Мої виміри':
        from handlers_measurements import show_measurements_history
        return await show_measurements_history(update, context)
    elif text == '📤 Експорт даних':
        from handlers_export import show_export_menu
        return await show_export_menu(update, context)
    elif text == '❓ Довідка':
        return await help_command(update, context)
    else:
        await msg.reply_text(
            "❌ Будь ласка, скористайся кнопками меню",
            reply_markup=ReplyKeyboardMarkup([
                ['💪 Почати тренування', '📊 Історія тренувань'],
                ['📝 Мої вправи', '📈 Статистика', '📏 Мої виміри'],
                ['📤 Експорт даних', '❓ Довідка']
            ], resize_keyboard=True)
        )
        return MAIN_MENU
