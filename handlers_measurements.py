import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_measurements_history
from utils_constants import *

logger = logging.getLogger(__name__)

async def show_measurements_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать историю замеров"""
    user_id = update.message.from_user.id
    measurements = get_measurements_history(user_id, limit=10)
    
    if not measurements:
        await update.message.reply_text(
            "📏 У тебе ще немає збережених вимірів.\n"
            "Додай виміри перед тренуванням або командою /measure.",
            reply_markup=ReplyKeyboardMarkup([
                ['💪 Почати тренування', '📊 Історія тренувань'],
                ['📝 Мої вправи', '📈 Статистика', '📏 Мої виміри'],
                ['📤 Експорт даних', '❓ Довідка']
            ], resize_keyboard=True)
        )
        return MAIN_MENU
    
    measurements_text = "📏 Історія твоїх вимірів:\n\n"
    
    for i, measurement in enumerate(measurements, 1):
        measurements_text += f"📅 #{measurement['id']} · {measurement['date']}\n"
        measurements_text += f"   {measurement['measurements']}\n\n"
    
    measurements_text += f"Усього записів: {len(measurements)}"
    
    await update.message.reply_text(
        measurements_text,
        reply_markup=ReplyKeyboardMarkup([
            ['💪 Почати тренування', '📊 Історія тренувань'],
            ['📝 Мої вправи', '📈 Статистика', '📏 Мої виміри'],
            ['📤 Експорт даних', '❓ Довідка']
        ], resize_keyboard=True)
    )
    return MAIN_MENU
