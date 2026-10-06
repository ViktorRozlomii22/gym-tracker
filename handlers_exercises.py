import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from handlers_common import start

from database import (
    get_custom_exercises,
    add_custom_exercise,
    get_visible_exercise_lists,
    remove_exercise_from_user_catalog,
)
from utils_constants import *

logger = logging.getLogger(__name__)

async def show_exercises_management(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать управление упражнениями"""
    user_id = update.message.from_user.id
    visible = get_visible_exercise_lists(user_id)
    all_strength = visible["strength"]
    all_cardio = visible["cardio"]
    
    exercises_text = "📝 Твої вправи:\n\n"
    exercises_text += "💪 Силові:\n"
    for ex in all_strength:
        exercises_text += f"• {ex}\n"
    
    exercises_text += "\n🏃 Кардіо:\n"
    for ex in all_cardio:
        exercises_text += f"• {ex}\n"
    
    keyboard = [
        ['➕ Додати вправу', '🗑️ Видалити вправу'],
        ['🔙 Головне меню']
    ]
    
    await update.message.reply_text(
        exercises_text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return EXERCISES_MANAGEMENT

async def handle_exercises_management_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора в управлении упражнениями"""
    text = update.message.text
    
    if text == '➕ Додати вправу':
        return await choose_exercise_type_mgmt(update, context)
    
    elif text == '🗑️ Видалити вправу':
        return await show_delete_exercise_menu(update, context)
    
    elif text == '🔙 Головне меню':
        return await start(update, context)
    
    else:
        return await show_exercises_management(update, context)
                                              
async def choose_exercise_type_mgmt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выбор типа упражнения для добавления (из управления)"""
    keyboard = [
        ['💪 Силова вправа', '🏃 Кардіовправа'],
        ['🔙 Назад до керування вправами']
    ]
    
    await update.message.reply_text(
        "Вибери тип вправи для додавання:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return ADD_EXERCISE_TYPE_MGMT

async def add_custom_exercise_mgmt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора типа упражнения в управлении"""
    choice = update.message.text
    
    if choice == '🔙 Назад до керування вправами':
        return await show_exercises_management(update, context)
    
    if '💪 Силова' in choice:
        context.user_data['adding_exercise_type'] = STRENGTH_TYPE
        await update.message.reply_text(
            "Введи назву нової силової вправи:",
            reply_markup=ReplyKeyboardRemove()
        )
        return INPUT_NEW_STRENGTH_EXERCISE_MGMT
    elif '🏃 Кардіо' in choice:
        context.user_data['adding_exercise_type'] = CARDIO_TYPE
        await update.message.reply_text(
            "Введи назву нової кардіовправи:",
            reply_markup=ReplyKeyboardRemove()
        )
        return INPUT_NEW_CARDIO_EXERCISE_MGMT
    else:
        await update.message.reply_text(
            "❌ Будь ласка, вибери тип вправи за допомогою кнопок",
            reply_markup=ReplyKeyboardMarkup([
                ['💪 Силова вправа', '🏃 Кардіовправа'],
                ['🔙 Назад до керування вправами']
            ], resize_keyboard=True)
        )
        return ADD_EXERCISE_TYPE_MGMT

async def save_new_strength_exercise_mgmt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение нового силового упражнения из управления"""
    return await save_new_exercise_mgmt(update, context, STRENGTH_TYPE)

async def save_new_cardio_exercise_mgmt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение нового кардио упражнения из управления"""
    return await save_new_exercise_mgmt(update, context, CARDIO_TYPE)

async def save_new_exercise_mgmt(update: Update, context: ContextTypes.DEFAULT_TYPE, exercise_type: str) -> int:
    """Сохранение нового упражнения из управления"""
    user_id = update.message.from_user.id
    exercise_name = update.message.text
    
    visible = get_visible_exercise_lists(user_id)
    key = "strength" if exercise_type == STRENGTH_TYPE else "cardio"
    if exercise_name in visible[key]:
        await update.message.reply_text(
            f"❌ Вправа «{exercise_name}» вже є у твоєму списку.",
            reply_markup=ReplyKeyboardMarkup([
                ['➕ Додати вправу', '🗑️ Видалити вправу'],
                ['🔙 Головне меню']
            ], resize_keyboard=True)
        )
        return EXERCISES_MANAGEMENT
    
    # Добавляем вправа в БД
    success = add_custom_exercise(user_id, exercise_name, exercise_type)
    
    if success:
        await update.message.reply_text(
            f"✅ Вправа '{exercise_name}' додано до твого списку!",
            reply_markup=ReplyKeyboardMarkup([
                ['➕ Додати вправу', '🗑️ Видалити вправу'],
                ['🔙 Головне меню']
            ], resize_keyboard=True)
        )
    else:
        await update.message.reply_text(
            "❌ Не вдалося додати вправу.",
            reply_markup=ReplyKeyboardMarkup([
                ['➕ Додати вправу', '🗑️ Видалити вправу'],
                ['🔙 Головне меню']
            ], resize_keyboard=True)
        )
    
    # Очищаем временные данные
    context.user_data.pop('adding_exercise_type', None)
    
    return EXERCISES_MANAGEMENT

async def show_delete_exercise_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать меню удаления упражнений"""
    user_id = update.message.from_user.id
    visible = get_visible_exercise_lists(user_id)

    if not visible["strength"] and not visible["cardio"]:
        await update.message.reply_text(
            "❌ У списку немає вправ. Додай власну вправу.",
            reply_markup=ReplyKeyboardMarkup([
                ['➕ Додати вправу', '🗑️ Видалити вправу'],
                ['🔙 Головне меню']
            ], resize_keyboard=True)
        )
        return EXERCISES_MANAGEMENT
    
    keyboard = []
    for ex in visible["strength"]:
        keyboard.append([f"💪 {ex}"])
    for ex in visible["cardio"]:
        keyboard.append([f"🏃 {ex}"])
    
    keyboard.append(['🔙 Назад до керування вправами'])
    
    await update.message.reply_text(
        "🗑️ Вибери вправу, яку потрібно прибрати зі списку:\n"
        "(власні видаляються з каталогу, стандартні приховуються; історія залишається)",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return DELETE_EXERCISE_MENU

async def delete_exercise_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Удаление выбранного упражнения"""
    user_id = update.message.from_user.id
    exercise_with_emoji = update.message.text
    
    if exercise_with_emoji == '🔙 Назад до керування вправами':
        return await show_exercises_management(update, context)
    
    # Извлекаем название упражнения и тип из текста
    if exercise_with_emoji.startswith('💪 '):
        exercise_name = exercise_with_emoji.split(' ', 1)[1]  # Убираем "💪 "
        exercise_type = STRENGTH_TYPE
    elif exercise_with_emoji.startswith('🏃 '):
        exercise_name = exercise_with_emoji.split(' ', 1)[1]  # Убираем "🏃 "
        exercise_type = CARDIO_TYPE
    else:
        await update.message.reply_text(
            "❌ Не вдалося розпізнати вправу.",
            reply_markup=ReplyKeyboardMarkup([
                ['➕ Додати вправу', '🗑️ Видалити вправу'],
                ['🔙 Головне меню']
            ], resize_keyboard=True)
        )
        return EXERCISES_MANAGEMENT
    
    success = remove_exercise_from_user_catalog(user_id, exercise_name, exercise_type)
    
    if success:
        await update.message.reply_text(
            f"✅ Вправа '{exercise_name}' видалено!",
            reply_markup=ReplyKeyboardMarkup([
                ['➕ Додати вправу', '🗑️ Видалити вправу'],
                ['🔙 Головне меню']
            ], resize_keyboard=True)
        )
    else:
        await update.message.reply_text(
            f"❌ Не вдалося видалити вправу '{exercise_name}'.",
            reply_markup=ReplyKeyboardMarkup([
                ['➕ Додати вправу', '🗑️ Видалити вправу'],
                ['🔙 Головне меню']
            ], resize_keyboard=True)
        )
    

    return EXERCISES_MANAGEMENT


