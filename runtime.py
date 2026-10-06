import logging
import os
import secrets
from pathlib import Path
from dotenv import load_dotenv
from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, ApplicationHandlerStop, filters
import database as db
import handlers_common as common
import handlers_training as training
import handlers_exercises as exercises
import handlers_export as export
import diary
from utils_constants import *
from paths import DATA_DIR

ROOT = DATA_DIR
os.environ.setdefault('MPLCONFIGDIR',str(ROOT / '.mpl'))
logging.basicConfig(level=logging.WARNING,format='%(asctime)s %(name)s %(levelname)s %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)


async def guard(update,context):
    if not update.effective_chat or update.effective_chat.type != 'private' or not update.message:
        raise ApplicationHandlerStop
    owner = db.setting('owner')
    if owner is None:
        expected = '/start ' + context.application.bot_data['pair_code']
        if secrets.compare_digest(update.message.text or '',expected):
            db.set_setting('owner',update.effective_user.id)
            print('Owner paired. Bot is ready.',flush=True)
            return
        raise ApplicationHandlerStop
    if owner != update.effective_user.id:
        raise ApplicationHandlerStop


async def input_choice(update,context):
    text = update.message.text
    if text == '✅ Додати ще підходи':
        return await training.add_another_set(update,context)
    if text == '💾 Зберегти вправу':
        return await training.save_exercise(update,context)
    if text == '❌ Скасувати вправу':
        return await training.cancel_exercise(update,context)
    return await training.handle_set_input(update,context)


async def cancel(update,context):
    context.user_data.pop('checkin_wizard',None)
    context.user_data.pop('ai_pending',None)
    context.user_data.pop('coach_pending',None)
    context.user_data.pop('current_exercise',None)
    return await common.start(update,context)


async def errors(update,context):
    # Do not log exception messages or URLs: these may contain a bot token.
    logging.error('Помилка обробки: %s',type(context.error).__name__)
    if update and update.effective_message:
        await update.effective_message.reply_text('❌ Не вдалося виконати дію. Відкрий /history, щоб перевірити збережені записи, або /start, щоб повернутися в меню.')


async def ready(app):
    info = await app.bot.get_webhook_info()
    if info.url:
        raise RuntimeError('Для цього бота вже налаштовано webhook. Спершу вимкни інший запуск.')
    await app.bot.set_my_commands([BotCommand('start','Головне меню'),BotCommand('help','Як користуватися щоденником'),BotCommand('history','Історія тренувань і підходів'),BotCommand('exercise','Історія однієї вправи'),BotCommand('graph','Графік за 7, 30, 90 або 365 днів'),BotCommand('measure','Записати виміри тіла'),BotCommand('remind','Налаштувати нагадування'),BotCommand('ai','Розібрати текст локальним ШІ'),BotCommand('cancel','Скасувати введення')])
    await app.bot.set_my_description('Твій особистий щоденник тренувань: вправи, підходи, повторення, вага, виміри тіла та графіки прогресу. Українською.')
    await app.bot.set_my_short_description('Щоденник тренувань українською · вправи, повторення, кг та прогрес')
    await app.bot.set_my_name('Щоденник тренувань')
    commands = await app.bot.get_my_commands()
    await app.bot.set_my_commands(list(commands) + [BotCommand('programs','Обрати орієнтир на 3 дні'),BotCommand('coachhelp','Профіль, PR та адаптація плану'),BotCommand('plan','Наступна сесія з джерелами'),BotCommand('ask','Питання до наукової бази'),BotCommand('sources','Джерела локальної бази'),BotCommand('status','Самопочуття або хвороба'),BotCommand('extra','Легкий четвертий день'),BotCommand('checkin','Сон, енергія та час перед сесією'),BotCommand('block','План на 4–6 тижнів'),BotCommand('feedback','RIR, біль та складність вправи'),BotCommand('swap','Замінити вправу в плані'),BotCommand('weekly','Звіт за останні 7 днів'),BotCommand('weeklyai','Висновки за тиждень з джерелами'),BotCommand('backup','Локальна резервна копія')])
    print(f'Bot is running: https://t.me/{app.bot.username}',flush=True)
    if db.setting('owner') is None:
        print(f'To pair your account, send: /start {app.bot_data["pair_code"]}',flush=True)
        print(f'Open this link and press Start: https://t.me/{app.bot.username}?start={app.bot_data["pair_code"]}',flush=True)
    print('Keep this window open. Stop: Ctrl+C. Your data is saved in the data folder.',flush=True)
    app.job_queue.run_repeating(diary.reminder_job,interval=60,first=10)
    from training_tools import weekly_job
    from backups import backup_job
    app.job_queue.run_repeating(weekly_job,interval=60,first=15)
    app.job_queue.run_repeating(backup_job,interval=3600,first=1)
    async def check_stop(context):
        if (ROOT / 'stop.request').exists():
            (ROOT / 'stop.request').unlink()
            context.application.stop_running()
    app.job_queue.run_repeating(check_stop,interval=5,first=5)


def build_app(token,pair_code):
    builder = Application.builder().token(token).concurrent_updates(False).post_init(ready)
    try:
        from telegram.request import HTTPXRequest
        request = HTTPXRequest()
        polling = HTTPXRequest()
    except PermissionError:
        from windows_transport import WindowsRequest
        request, polling = WindowsRequest(), WindowsRequest()
    app = builder.request(request).get_updates_request(polling).build()
    app.bot_data['pair_code'] = pair_code
    app.add_handler(MessageHandler(filters.ALL,guard),group=-2)
    app.add_handler(MessageHandler(filters.TEXT,diary.extras),group=-1)
    states = {
        INACTIVE:common.handle_clear_data_choice,
        MAIN_MENU:common.handle_main_menu,
        STATS_MENU:diary.handle_statistics_menu,
        EXPORT_MENU:export.handle_export_menu,
        CLEAR_DATA_CONFIRM:common.handle_clear_data_confirmation,
        TRAINING_MENU:training.handle_training_menu_choice,
        ADD_EXERCISE_TYPE:training.add_custom_exercise_from_training,
        INPUT_MEASUREMENTS_CHOICE:training.handle_measurements_choice,
        INPUT_MEASUREMENTS:training.save_measurements,
        CHOOSE_STRENGTH_EXERCISE:training.handle_strength_exercise_selection,
        INPUT_SETS:input_choice,
        CHOOSE_CARDIO_EXERCISE:training.handle_cardio_exercise_selection,
        INPUT_NEW_CARDIO_EXERCISE:training.save_new_exercise_from_training,
        INPUT_NEW_STRENGTH_EXERCISE:training.save_new_exercise_from_training,
        CARDIO_TYPE_SELECTION:training.handle_cardio_type_selection,
        INPUT_CARDIO_MIN_METERS:training.handle_cardio_min_meters_input,
        INPUT_CARDIO_KM_H:training.handle_cardio_km_h_input,
        DELETE_EXERCISE_MENU:exercises.delete_exercise_handler,
        EXERCISES_MANAGEMENT:exercises.handle_exercises_management_choice,
        ADD_EXERCISE_TYPE_MGMT:exercises.add_custom_exercise_mgmt,
        INPUT_NEW_STRENGTH_EXERCISE_MGMT:exercises.save_new_strength_exercise_mgmt,
        INPUT_NEW_CARDIO_EXERCISE_MGMT:exercises.save_new_cardio_exercise_mgmt,
        CONFIRM_FINISH:training.handle_finish_confirmation,
    }
    handler = ConversationHandler(entry_points=[CommandHandler('start',common.start),CommandHandler('cancel',cancel)],states={key:[MessageHandler(filters.TEXT & ~filters.COMMAND,callback)] for key,callback in states.items()},fallbacks=[CommandHandler('start',common.start),CommandHandler('cancel',cancel)],allow_reentry=True)
    app.add_handler(handler)
    async def fallback(update,context):
        await update.message.reply_text('Відкрий /start для меню або /help для прикладів. Швидкий запис: Жим лежачи 3x10 60 кг')
    app.add_handler(MessageHandler(filters.ALL,fallback))
    app.add_error_handler(errors)
    return app


def main():
    import msvcrt
    ROOT.mkdir(parents=True, exist_ok=True)
    lock = (ROOT / '.running.lock').open('a+b')
    if lock.tell() == 0:
        lock.write(b'0'); lock.flush()
    lock.seek(0)
    try:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    except OSError:
        print('The bot is already running. A second instance is not needed.',flush=True)
        return
    load_dotenv(ROOT / '.env')
    token = os.getenv('BOT_TOKEN')
    if not token:
        print('Add BOT_TOKEN to your local .env file.',flush=True)
        return
    db.ensure_bot_schema()
    if (ROOT / 'stop.request').exists():
        (ROOT / 'stop.request').unlink()
    code = db.setting('pair_code') or secrets.token_hex(5)
    db.set_setting('pair_code',code)
    app = build_app(token,code)
    try:
        app.run_polling(drop_pending_updates=False,allowed_updates=['message'])
    finally:
        lock.close()

if __name__ == '__main__':
    main()
