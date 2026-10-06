import math
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from database import (
    create_user, get_current_training, create_training, save_training_measurements,
    add_exercise_to_training, get_training_exercises, finish_training, get_user_trainings,
    save_measurement, add_custom_exercise, get_visible_exercise_lists,
)
from utils_constants import *

logger = logging.getLogger(__name__)

# ==================== ОСНОВНЫЕ ФУНКЦИИ ТРЕНИРОВКИ ====================

async def start_training(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало тренировки"""
    user = update.message.from_user
    user_id = user.id
    
    # Создаем пользователя если его нет
    create_user(user_id, user.username, user.first_name)
    
    # Проверяем есть ли текущая тренировка
    current_training = get_current_training(user_id)
    
    if current_training:
        # Продолжаем существующую тренировку
        context.user_data['current_training'] = current_training
        context.user_data['training_id'] = current_training['training_id']
        
        keyboard = [
            ['💪 Силові вправи', '🏃 Кардіо'],
            ['✏️ Додати власну вправу', '🏁 Завершити тренування']
        ]
        
        await update.message.reply_text(
            f"🎯 Продовжуємо тренування від {current_training['date_start']}!\n\n"
            "Вибери тип вправи:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return TRAINING_MENU
    else:
        # Создаем новую тренировку
        new_training = create_training(user_id)
        if not new_training:
            await update.message.reply_text("❌ Не вдалося створити тренування. Спробуй пізніше.")
            return MAIN_MENU
        
        context.user_data['current_training'] = new_training
        context.user_data['training_id'] = new_training['training_id']
        
        keyboard = [
            ['📝 Ввести виміри', '⏭️ Пропустити виміри'],
            ['🔙 Головне меню']
        ]
        
        await update.message.reply_text(
            f"🎯 Починаємо! Сьогодні {new_training['date_start']}\n\n"
            "📏 Хочеш записати виміри перед тренуванням?\n"
            "(наприклад: вага 65 кг, талія 70 см, стегна 95 см)",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return INPUT_MEASUREMENTS_CHOICE

async def show_finish_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Завершение тренировки - показ сводки"""
    training_id = context.user_data.get('training_id')
    
    if not training_id:
        await update.message.reply_text("❌ Немає активного тренування.")
        return MAIN_MENU
    
    # Получаем текущую тренировку с упражнениями
    current_training = get_current_training(update.message.from_user.id)
    
    if not current_training or not current_training['exercises']:
        await update.message.reply_text(
            "❌ У тренуванні ще немає вправ. Додай хоча б одну вправу перед завершенням.",
            reply_markup=ReplyKeyboardMarkup([
                ['💪 Силові вправи', '🏃 Кардіо'],
                ['✏️ Додати власну вправу', '🏁 Завершити тренування']
            ], resize_keyboard=True)
        )
        return TRAINING_MENU
    
    # Формируем сводку по тренировке
    report = "📊 ПІДСУМОК ТРЕНУВАННЯ\n\n"
    report += f"📅 Дата: {current_training['date_start']}\n\n"
    
    if current_training['measurements']:
        report += f"📏 Виміри: {current_training['measurements']}\n\n"
    
    report += "💪 Виконані вправи:\n\n"
    
    total_exercises = len(current_training['exercises'])
    strength_count = 0
    cardio_count = 0
    
    for i, exercise in enumerate(current_training['exercises'], 1):
        if exercise.get('is_cardio'):
            cardio_count += 1
            report += f"🏃 {i}. {exercise['name']}\n"
            report += f"   Подробиці: {exercise['details']}\n\n"
        else:
            strength_count += 1
            report += f"💪 {i}. {exercise['name']}\n"
            for j, set_data in enumerate(exercise['sets'], 1):
                report += f"   {j}. {set_data['weight']}кг × {set_data['reps']}\n"
            report += "\n"
    
    report += f"📊 Усього вправ: {total_exercises}\n"
    report += f"• Силових: {strength_count}\n"
    report += f"• Кардіо: {cardio_count}\n"
    
    keyboard = [
        ['✅ Підтвердити завершення', '✏️ Виправити'],
        ['🔙 Продовжити тренування']
    ]
    
    await update.message.reply_text(
        report,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return CONFIRM_FINISH

async def show_training_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать меню тренировки"""
    keyboard = [
        ['💪 Силові вправи', '🏃 Кардіо'],
        ['✏️ Додати власну вправу', '🏁 Завершити тренування']
    ]
    
    await update.message.reply_text(
        "Вибери тип вправи:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return TRAINING_MENU

async def handle_finish_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка подтверждения завершения тренировки"""
    choice = update.message.text
    training_id = context.user_data.get('training_id')
    user_id = update.message.from_user.id
    
    if choice == '🔙 Продовжити тренування':
        return await show_training_menu(update, context)
    
    elif choice == '✏️ Виправити':
        # TODO: Реализовать редактирование тренировки
        await update.message.reply_text(
            "Для виправлення скористайся /delete НОМЕР_ВПРАВИ, потім додай правильний запис.",
            reply_markup=ReplyKeyboardMarkup([
                ['✅ Підтвердити завершення'],
                ['🔙 Продовжити тренування']
            ], resize_keyboard=True)
        )
        return CONFIRM_FINISH
    
    elif choice == '✅ Підтвердити завершення':
        # ЯВНО импортируем функцию из database.py
        from database import finish_training as db_finish_training
        
        # Завершаем тренировку через БД функцию
        success = db_finish_training(training_id)
        
        if success:
            # Очищаем данные тренировки
            context.user_data.pop('current_training', None)
            context.user_data.pop('training_id', None)
            context.user_data.pop('current_exercise', None)
            context.user_data.pop('cardio_format', None)
            
            await update.message.reply_text(
                "🏆 Тренування завершено та збережено! 🏆",
                reply_markup=ReplyKeyboardMarkup([
                    ['💪 Почати тренування', '📊 Історія тренувань'],
                    ['📝 Мої вправи', '📈 Статистика', '📏 Мої виміри'],
                    ['📤 Експорт даних', '❓ Довідка']
                ], resize_keyboard=True)
            )
        else:
            await update.message.reply_text("❌ Не вдалося завершити тренування.")
        
        return MAIN_MENU
    
    else:  # ← ОДИН раз, а не два!
        await update.message.reply_text(
            "❌ Будь ласка, вибери дію за допомогою кнопок",
            reply_markup=ReplyKeyboardMarkup([
                ['✅ Підтвердити завершення', '✏️ Виправити'],
                ['🔙 Продовжити тренування']
            ], resize_keyboard=True)
        )
        return CONFIRM_FINISH

# ==================== ОБРАБОТЧИКИ МЕНЮ ТРЕНИРОВКИ ====================
async def handle_training_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора в меню тренировки - УПРОЩЕННАЯ ВЕРСИЯ"""
    text = update.message.text
    
    if text == '💪 Силові вправи':
        return await show_strength_exercises(update, context)
        
    elif text == '🏃 Кардіо':
        return await show_cardio_exercises(update, context)
        
    elif text == '✏️ Додати власну вправу':
        return await choose_exercise_type(update, context)
        
    elif text == '🏁 Завершити тренування':
        return await show_finish_summary(update, context)
        
    else:
        return await handle_training_menu_fallback(update, context)

async def handle_training_menu_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нераспознанных сообщений в меню тренировки"""
    text = update.message.text
    
    logger.info("TRAINING_MENU fallback для текста длиной %s", len(text or ""))
    
    # Показываем меню тренировки снова с подсказкой
    keyboard = [
        ['💪 Силові вправи', '🏃 Кардіо'],
        ['✏️ Додати власну вправу', '🏁 Завершити тренування']
    ]
    
    await update.message.reply_text(
        "❌ Будь ласка, скористайся кнопками тренування:\n\n"
        "Вибери тип вправи:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    
    return TRAINING_MENU

async def handle_measurements_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора ввода замеров перед тренировкой"""
    choice = update.message.text
    user_id = update.message.from_user.id
    
    if choice == '📝 Ввести виміри':
        await update.message.reply_text(
            "📏 Введи свої виміри:\n"
            "• Наприклад: вага 65 кг; талія 70 см; груди 95 см\n"
            "• Або: біцепс лівий 35 см; стегно праве 58 см\n"
            "• Або: вага 65 кг",
            reply_markup=ReplyKeyboardRemove()
        )
        return INPUT_MEASUREMENTS
        
    elif choice == '⏭️ Пропустити виміри':
        return await show_training_menu(update, context)
        
    elif choice == '🔙 Головне меню':
        from handlers_common import start
        return await start(update, context)
        
    else:
        # Если получен неизвестный текст, показываем клавиатуру снова
        await update.message.reply_text(
            "❌ Будь ласка, скористайся кнопками вибору:",
            reply_markup=ReplyKeyboardMarkup([
                ['📝 Ввести виміри', '⏭️ Пропустити виміри'],
                ['🔙 Головне меню']
            ], resize_keyboard=True)
        )
        return INPUT_MEASUREMENTS_CHOICE

async def save_measurements(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение замеров пользователя"""
    user_id = update.message.from_user.id
    measurements_text = update.message.text
    from diary import parse_measurements
    try:
        values = parse_measurements(measurements_text)
    except ValueError as error:
        await update.message.reply_text(str(error))
        return INPUT_MEASUREMENTS
    measurements_text = '; '.join(f'{n} {v:g} {u}' for n,v,u in values)
    training_id = context.user_data.get('training_id')
    
    
    if training_id:
        # Сохраняем замеры в тренировку
        success = save_training_measurements(training_id, measurements_text)
    
    # Также сохраняем в отдельную таблицу замеров
    save_success = save_measurement(user_id, measurements_text, f"measure:{user_id}:{update.message.message_id}")
    
    if save_success:
        await update.message.reply_text(
            f"✅ Виміри збережено!\n\n📏 Твої виміри: {measurements_text}",
            reply_markup=ReplyKeyboardMarkup([
                ['💪 Силові вправи', '🏃 Кардіо'],
                ['✏️ Додати власну вправу', '🏁 Завершити тренування']
            ], resize_keyboard=True)
        )
    else:
        await update.message.reply_text(
            "❌ Не вдалося зберегти виміри. Повертаємося до тренування...",
            reply_markup=ReplyKeyboardMarkup([
                ['💪 Силові вправи', '🏃 Кардіо'],
                ['✏️ Додати власну вправу', '🏁 Завершити тренування']
            ], resize_keyboard=True)
        )
    
    return TRAINING_MENU

# ==================== СИЛОВЫЕ УПРАЖНЕНИЯ ====================

async def show_strength_exercises(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать силовые упражнения"""
    user_id = update.message.from_user.id
    
    try:
        all_strength_exercises = get_visible_exercise_lists(user_id)["strength"]
        
        # Создаем клавиатуру с упражнениями
        keyboard = []
        for i in range(0, len(all_strength_exercises), 2):
            row = all_strength_exercises[i:i+2]
            keyboard.append(row)
        
        keyboard.append(['✏️ Додати силову вправу'])
        keyboard.append(['🔙 Назад до тренування'])
        
        await update.message.reply_text(
            "💪 Вибери силову вправу:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        
        return CHOOSE_STRENGTH_EXERCISE
        
    except Exception as e:
        logger.exception("Ошибка в show_strength_exercises: %s", e)
        # В случае ошибки возвращаемся в меню тренировки
        keyboard = [
            ['💪 Силові вправи', '🏃 Кардіо'],
            ['✏️ Додати власну вправу', '🏁 Завершити тренування']
        ]
        await update.message.reply_text(
            f"Помилка завантаження вправ: {e}\nПовертаємося до меню тренування...",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return TRAINING_MENU

async def handle_strength_exercise_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора силового упражнения"""
    exercise_name = update.message.text.strip()

    # ОБРАБОТКА ДОБАВЛЕНИЯ НОВОГО УПРАЖНЕНИЯ
    if exercise_name == '✏️ Додати силову вправу':
        context.user_data['adding_exercise_type'] = STRENGTH_TYPE
        
        await update.message.reply_text(
            "Введи назву нової силової вправи:",
            reply_markup=ReplyKeyboardRemove()
        )
        return INPUT_NEW_STRENGTH_EXERCISE
    
    if exercise_name == '🔙 Назад до тренування':
        return await show_training_menu(update, context)
    
    # Сохраняем выбранное вправа
    context.user_data['current_exercise'] = {
        'name': exercise_name,
        'type': STRENGTH_TYPE,
        'sets': []
    }
    
    await update.message.reply_text(
        f"💪 Вибрано: {exercise_name}\n\n"
        "Введи підходи у форматі (кожен з нового рядка):\n"
        "**Вага_кг Кількість_повторень**\n\n"
        "📝 Приклад:\n"
        "50 12\n"
        "55 10\n"
        "60 8\n\n"
        "Або введи один підхід: 50 12",
        reply_markup=ReplyKeyboardRemove()
    )
    return INPUT_SETS

async def handle_set_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода подходов"""
    text = update.message.text
    
    # Разівбиваем на строки для обработки нескольких подходов
    lines = text.strip().split('\n')
    valid_sets = []
    errors = []
    
    for line_num, line in enumerate(lines, 1):
        if not line.strip():
            continue
            
        line_clean = line.replace(',', '.').replace('/', ' ').replace('х', ' ').replace('x', ' ')
        parts = line_clean.split()
        
        if len(parts) == 2:
            try:
                weight = float(parts[0])
                reps = int(parts[1])
                if not math.isfinite(weight) or not 0 <= weight <= 1000 or not 1 <= reps <= 1000:
                    raise ValueError('invalid range')
                
                valid_sets.append({
                    'weight': weight,
                    'reps': reps
                })
                
            except (ValueError, IndexError):
                errors.append(f"Рядок {line_num}: неправильний формат '{line}'")
        else:
            errors.append(f"Рядок {line_num}: недостатньо даних '{line}'")
    
    if errors:
        await update.message.reply_text("❌ Перевір рядки. Нічого не додано. Вага: 0–1000 кг, повторення: 1–1000.\n" + "\n".join(errors))
        return INPUT_SETS
    if valid_sets:
        if 'current_exercise' not in context.user_data:
            context.user_data['current_exercise'] = {'sets': []}
        
        if len(context.user_data['current_exercise']['sets']) + len(valid_sets) > 100:
            await update.message.reply_text('Максимум 100 підходів на вправу.')
            return INPUT_SETS
        context.user_data['current_exercise']['sets'].extend(valid_sets)
        
        sets_count = len(context.user_data['current_exercise']['sets'])
        sets_text = "✅ Поточні підходи:\n"
        for i, set_data in enumerate(context.user_data['current_exercise']['sets'], 1):
            sets_text += f"{i}. {set_data['weight']}кг × {set_data['reps']} повторень\n"
        
        error_text = ""
        if errors:
            error_text = "\n❌ Помилки:\n" + "\n".join(errors) + "\n"
        
        keyboard = [['✅ Додати ще підходи', '💾 Зберегти вправу'], ['❌ Скасувати вправу']]
        
        await update.message.reply_text(
            f"{sets_text}\n"
            f"Усього підходів: {sets_count}\n"
            f"{error_text}\n"
            "Вибери дію:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        
        return INPUT_SETS
    else:
        await update.message.reply_text(
            "❌ Не вдалося розпізнати підходи.\n\n"
            "Введи підходи у форматі (кожен з нового рядка):\n"
            "**Вага_кг Кількість_повторень**\n\n"
            "📝 Приклад:\n"
            "50 12\n"
            "55 10\n"
            "60 8\n\n"
            "Або введи один підхід: 50 12"
        )
        return INPUT_SETS

async def add_another_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Добавление еще подходов"""
    await update.message.reply_text(
        "Введи наступні підходи (кожен з нового рядка):\n"
        "**Вага_кг Кількість_повторень**\n\n"
        "📝 Приклад:\n"
        "65 6\n"
        "70 4\n\n"
        "Або введи один підхід: 65 6",
        reply_markup=ReplyKeyboardRemove()
    )
    return INPUT_SETS

async def save_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение упражнения с подходами"""
    training_id = context.user_data.get('training_id')
    
    if 'current_exercise' not in context.user_data or not training_id:
        await update.message.reply_text("❌ Немає даних для збереження.")
        return await show_training_menu(update, context)
    
    exercise_data = context.user_data['current_exercise']
    exercise_data['source_key'] = f"guided:{update.effective_user.id}:{update.message.message_id}"
    
    # Сохраняем вправа в БД
    success = add_exercise_to_training(training_id, exercise_data)
    
    if success:
        # Формируем текст сохраненного упражнения
        exercise_text = f"💪 {exercise_data['name']}:\n"
        for i, set_data in enumerate(exercise_data['sets'], 1):
            exercise_text += f"{i}. {set_data['weight']}кг × {set_data['reps']} повторень\n"
        
        # Очищаем временные данные
        context.user_data.pop('current_exercise', None)
        
        await update.message.reply_text(
            f"✅ Вправу збережено!\n\n{exercise_text}",
            reply_markup=ReplyKeyboardMarkup([
                ['💪 Силові вправи', '🏃 Кардіо'],
                ['✏️ Додати власну вправу', '🏁 Завершити тренування']
            ], resize_keyboard=True)
        )
    else:
        await update.message.reply_text("❌ Не вдалося зберегти вправу.")
    
    return TRAINING_MENU

# ==================== КАРДИО УПРАЖНЕНИЯ ====================

async def show_cardio_exercises(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать кардио упражнения"""
    user_id = update.message.from_user.id
    all_cardio_exercises = get_visible_exercise_lists(user_id)["cardio"]
    
    keyboard = [[exercise] for exercise in all_cardio_exercises]
    keyboard.append(['✏️ Додати кардіовправу'])
    keyboard.append(['🔙 Назад до тренування'])
    
    await update.message.reply_text(
        "🏃 Вибери кардіовправу:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return CHOOSE_CARDIO_EXERCISE

async def handle_cardio_exercise_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора кардио упражнения"""
    exercise_name = update.message.text.strip()
    
    if exercise_name == '✏️ Додати кардіовправу':
        
        context.user_data['adding_exercise_type'] = CARDIO_TYPE
        
        await update.message.reply_text(
            "Введи назву нової кардіовправи:",
            reply_markup=ReplyKeyboardRemove()
        )
        return INPUT_NEW_CARDIO_EXERCISE
    
    if exercise_name == '🔙 Назад до тренування':
        return await show_training_menu(update, context)
    
    # Сохраняем выбранное кардио вправа
    context.user_data['current_exercise'] = {
        'name': exercise_name,
        'type': CARDIO_TYPE
    }
    
    keyboard = [
        ['⏱️ Хв/Метри', '🚀 Км/Год'],
        ['🔙 Назад до кардіо']
    ]
    
    await update.message.reply_text(
        f"🏃 Вибрано: {exercise_name}\n\n"
        "Вибери формат ввода:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return CARDIO_TYPE_SELECTION

async def handle_cardio_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора формата кардио"""
    choice = update.message.text
    
    if choice == '🔙 Назад до кардіо':
        return await show_cardio_exercises(update, context)
    
    if choice not in ['⏱️ Хв/Метри', '🚀 Км/Год']:
        await update.message.reply_text(
            "❌ Будь ласка, вибери формат за допомогою кнопок",
            reply_markup=ReplyKeyboardMarkup([
                ['⏱️ Хв/Метри', '🚀 Км/Год'],
                ['🔙 Назад до кардіо']
            ], resize_keyboard=True)
        )
        return CARDIO_TYPE_SELECTION
    
    context.user_data['cardio_format'] = choice
    
    if choice == '⏱️ Хв/Метри':
        await update.message.reply_text(
            "Введи час і відстань у форматі:\n"
            "**Час_у_хвилинах Відстань_у_метрах**\n\n"
            "📝 Приклад: 30 5000 (30 хвилин, 5000 метрів)",
            reply_markup=ReplyKeyboardRemove()
        )
        return INPUT_CARDIO_MIN_METERS
    elif choice == '🚀 Км/Год':
        await update.message.reply_text(
            "Введи час і швидкість у форматі:\n"
            "**Час_у_хвилинах Швидкість_км/год**\n\n"
            "📝 Приклад: 30 10 (30 хвилин, 10 км/год)",
            reply_markup=ReplyKeyboardRemove()
        )
        return INPUT_CARDIO_KM_H

async def handle_cardio_min_meters_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода кардио в формате хвилины/метры"""
    return await save_cardio_exercise(update, context, 'min_meters')

async def handle_cardio_km_h_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода кардио в формате км/год"""
    return await save_cardio_exercise(update, context, 'km_h')

async def save_cardio_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE, format_type: str):
    """Сохранение кардио упражнения"""
    training_id = context.user_data.get('training_id')
    text = update.message.text
    
    if 'current_exercise' not in context.user_data or not training_id:
        await update.message.reply_text("❌ Немає даних для збереження.")
        return await show_training_menu(update, context)
    
    try:
        parts = text.split()
        if len(parts) != 2:
            raise ValueError("Потрібно ввести два числа")
        
        time_minutes = int(parts[0])
        value = float(parts[1].replace(',', '.'))
        if not math.isfinite(value) or not 0 < time_minutes <= 1440 or not 0 < value <= (1000000 if format_type == 'min_meters' else 100):
            raise ValueError('invalid range')
        
        exercise_data = context.user_data['current_exercise'].copy()
        exercise_data['source_key'] = f"cardio:{update.effective_user.id}:{update.message.message_id}"
        
        if format_type == 'min_meters':
            # ПРЕОБРАЗУЕМ В INT для distance_meters
            distance_meters = int(value)  # ← ВАЖНО!
            
            exercise_data.update({
                'time_minutes': time_minutes,
                'distance_meters': distance_meters,  # ← целое число
                'details': f"{time_minutes} хвилин, {distance_meters} метрів"
            })
        else:  # km_h
            # speed_kmh может быть float
            exercise_data.update({
                'time_minutes': time_minutes,
                'speed_kmh': value,
                'details': f"{time_minutes} хвилин, {value} км/год"
            })
        
        # Сохраняем вправа в БД
        success = add_exercise_to_training(training_id, exercise_data)
        
        if success:
            # Очищаем временные данные
            context.user_data.pop('current_exercise', None)
            context.user_data.pop('cardio_format', None)
            
            await update.message.reply_text(
                f"✅ Кардіо збережено!\n{exercise_data['name']}: {exercise_data['details']}",
                reply_markup=ReplyKeyboardMarkup([
                    ['💪 Силові вправи', '🏃 Кардіо'],
                    ['✏️ Додати власну вправу', '🏁 Завершити тренування']
                ], resize_keyboard=True)
            )
        else:
            await update.message.reply_text("❌ Не вдалося зберегти кардіо.")
        
        return TRAINING_MENU
        
    except (ValueError, IndexError):
        if format_type == 'min_meters':
            await update.message.reply_text(
                "❌ Неправильний формат. Введи два цілі числа:\n"
                "**Час_у_хвилинах Відстань_у_метрах**\n\n"
                "📝 Приклад: 30 5000"
            )
            return INPUT_CARDIO_MIN_METERS
        else:
            await update.message.reply_text(
                "❌ Неправильний формат. Введи два числа:\n"
                "**Час_у_хвилинах Швидкість_км/год**\n\n"
                "📝 Приклад: 30 10"
            )
            return INPUT_CARDIO_KM_H

# ==================== ДОБАВЛЕНИЕ УПРАЖНЕНИЙ ====================

async def choose_exercise_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выбор типа упражнения для добавления"""
    keyboard = [
        ['💪 Силова вправа', '🏃 Кардіовправа'],
        ['🔙 Назад до тренування']
    ]
    
    await update.message.reply_text(
        "Вибери тип вправи для додавання:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return ADD_EXERCISE_TYPE

async def add_custom_exercise_from_training(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Добавление пользовательского упражнения из тренировки"""
    choice = update.message.text
    
    if choice == '🔙 Назад до тренування':
        return await show_training_menu(update, context)
    
    if '💪 Силова' in choice:
        context.user_data['adding_exercise_type'] = STRENGTH_TYPE
        await update.message.reply_text(
            "Введи назву нової силової вправи:",
            reply_markup=ReplyKeyboardRemove()
        )
        return INPUT_NEW_STRENGTH_EXERCISE
        
    elif '🏃 Кардіо' in choice:
        context.user_data['adding_exercise_type'] = CARDIO_TYPE
        await update.message.reply_text(
            "Введи назву нової кардіовправи:",
            reply_markup=ReplyKeyboardRemove()
        )
        return INPUT_NEW_CARDIO_EXERCISE
    else:
        await update.message.reply_text(
            "❌ Будь ласка, вибери тип вправи за допомогою кнопок",
            reply_markup=ReplyKeyboardMarkup([
                ['💪 Силова вправа', '🏃 Кардіовправа'],
                ['🔙 Назад до тренування']
            ], resize_keyboard=True)
        )
        return ADD_EXERCISE_TYPE

async def save_new_exercise_from_training(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение нового упражнения из тренировки"""
    user_id = update.message.from_user.id
    exercise_name = update.message.text.strip()
    exercise_type = context.user_data.get('adding_exercise_type', STRENGTH_TYPE)

    visible = get_visible_exercise_lists(user_id)
    bucket = "strength" if exercise_type == STRENGTH_TYPE else "cardio"
    if exercise_name in visible[bucket]:
        await update.message.reply_text(
            f"❌ Вправа «{exercise_name}» вже є у твоєму списку.",
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data.pop('adding_exercise_type', None)
        if exercise_type == STRENGTH_TYPE:
            return await show_strength_exercises(update, context)
        return await show_cardio_exercises(update, context)
    
    # Добавляем вправа в БД
    success = add_custom_exercise(user_id, exercise_name, exercise_type)
    
    if success:
        await update.message.reply_text(f"✅ Вправа '{exercise_name}' додано до твого списку!")
    else:
        await update.message.reply_text("❌ Не вдалося додати вправу.")
    
    # Очищаем временные данные
    context.user_data.pop('adding_exercise_type', None)
    
    # Возвращаемся к соответствующему выбору упражнений
    if exercise_type == STRENGTH_TYPE:
        return await show_strength_exercises(update, context)
    else:
        return await show_cardio_exercises(update, context)

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

async def show_training_history(update, context):
    from diary import send_history
    await send_history(update, context)
    return MAIN_MENU

async def cancel_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Скасувати текущего упражнения"""
    exercise_name = context.user_data.get('current_exercise', {}).get('name', 'вправа')
    context.user_data.pop('current_exercise', None)
    context.user_data.pop('cardio_format', None)
    
    await update.message.reply_text(
        f"❌ {exercise_name} - видалено",
        reply_markup=ReplyKeyboardMarkup([
            ['💪 Силові вправи', '🏃 Кардіо'],
            ['✏️ Додати власну вправу', '🏁 Завершити тренування']
        ], resize_keyboard=True)
    )
    
    return TRAINING_MENU

async def continue_training(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Продолжение текущей тренировки"""
    user_id = update.message.from_user.id
    current_training = get_current_training(user_id)
    
    if not current_training:
        await update.message.reply_text(
            "❌ Поточного тренування не знайдено. Починаємо нове.",
            reply_markup=ReplyKeyboardMarkup([
                ['💪 Силові вправи', '🏃 Кардіо'],
                ['✏️ Додати власну вправу', '🏁 Завершити тренування']
            ], resize_keyboard=True)
        )
        return TRAINING_MENU
    
    context.user_data['current_training'] = current_training
    context.user_data['training_id'] = current_training['training_id']
    
    training_info = f"""
🏃‍♂️ Продовжуємо тренування від {current_training['date_start']}

Уже додано вправ: {len(current_training['exercises'])}
    """
    
    await update.message.reply_text(
        training_info,
        reply_markup=ReplyKeyboardMarkup([
            ['💪 Силові вправи', '🏃 Кардіо'],
            ['✏️ Додати власну вправу', '🏁 Завершити тренування']
        ], resize_keyboard=True)
    )
    return TRAINING_MENU

async def handle_training_menu_simple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Упрощенный обработчик меню тренировки"""
    text = update.message.text
    
    if text == '💪 Силові вправи':
        await update.message.reply_text("✅ Переходимо до силових вправ!")
        return await show_strength_exercises(update, context)
    elif text == '🏃 Кардіо':
        await update.message.reply_text("✅ Переходимо до кардіо!")
        return await show_cardio_exercises(update, context)
    elif text == '✏️ Додати власну вправу':
        await update.message.reply_text("✅ Додаємо вправу!")
        return await choose_exercise_type(update, context)
    elif text == '🏁 Завершити тренування':
        await update.message.reply_text("✅ Завершуємо тренування!")
        return await show_finish_summary(update, context)
    else:
        # Показываем меню снова
        keyboard = [
            ['💪 Силові вправи', '🏃 Кардіо'],
            ['✏️ Додати власну вправу', '🏁 Завершити тренування']
        ]
        
        await update.message.reply_text(
            f"Отримано: '{text}'. Скористайся кнопками тренування:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return TRAINING_MENU


















