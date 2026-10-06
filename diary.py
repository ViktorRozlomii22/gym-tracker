"""Ukrainian diary, quick entry, history, graphs and optional local parsing."""
import asyncio
import io
import json
import math
import os
import re
from datetime import date, datetime, timedelta
from telegram import ReplyKeyboardMarkup, InputFile
from telegram.ext import ApplicationHandlerStop
import database as db
from bot_utils import normalize_exercise_sets, parse_training_datetime
from utils_constants import MAIN_MENU, STATS_MENU

HELP = '''📔 Щоденник тренувань

/programs — обрати програму на 3 дні
/coachhelp — профіль, PR, план і зміни після пропусків/хвороби
/plan — наступна сесія; /extra — легкий четвертий день

Швидкий запис:
Жим лежачи 3x10 60 кг
Присідання 8 80 кг
Або натисни «💪 Почати тренування» та обери вправу.
У покроковому режимі кожен рядок: вага повторення
60 10
65 8

/history — останні тренування з усіма підходами
/history 2 — друга сторінка історії
/exercise Жим лежачи — історія однієї вправи
/graph 30 — графік за 30 днів
/graph 90 Жим лежачи — графік вправи
Періоди: 7, 30, 90, 365 днів, включно із сьогодні.

/measure біцепс лівий 35,5 см; талія 82 см; вага 80 кг
/graph 365 біцепс лівий — графік вимірів
/delete 12 — видалити запис вправи №12
/measure_delete 3 — видалити вимір №3
/remind 10 — щодня о 18:00 нагадувати про вправи без записів 10 днів
/remind 0 — вимкнути нагадування
/tips — підказки до щоденника
/ai сьогодні жим лежачи 3 по 10 на 60 кг — локальний ШІ (потрібен Ollama)
/cancel — скасувати пропозицію ШІ та повернутися в меню

Швидкі записи додаються до поточного тренування. Заверши його через меню.
Збережені вправи є в історії одразу. Незбережені підходи в покроковому режимі — чернетка.
Використовуй однакові назви й одиниці. Вправи без додаткової ваги записуй як 0 кг.'''


def norm(value):
    return ' '.join(value.lower().split())


def quick_parse(text):
    m = re.fullmatch(r'(.+?)\s+(?:(\d+)\s*[xх×]\s*)?(\d+)\s+(\d+(?:[.,]\d+)?)\s*(?:кг|kg)', text.strip(), re.I)
    if not m:
        return None
    name, count, reps, weight = m.groups()
    count, reps, weight = int(count or 1), int(reps), float(weight.replace(',', '.'))
    if not 1 <= len(name) <= 80 or not 1 <= count <= 100 or not 1 <= reps <= 1000 or not 0 <= weight <= 1000:
        raise ValueError('Перевір значення: 1–100 підходів, 1–1000 повторень, 0–1000 кг.')
    return {'name':name.strip(), 'type':'strength', 'sets':[{'weight':weight,'reps':reps} for _ in range(count)]}


def parse_measurements(text):
    result = []
    for part in text.split(';'):
        m = re.fullmatch(r'\s*(.+?)\s+(\d+(?:[.,]\d+)?)\s*(см|кг|cm|kg)\s*', part, re.I)
        if not m:
            raise ValueError('Приклад: /measure біцепс лівий 35,5 см; талія 82 см; вага 80 кг')
        name, value, unit = m.groups()
        value, name = float(value.replace(',', '.')), norm(name)
        unit = {'cm':'см', 'kg':'кг'}.get(unit.lower(), unit.lower())
        if not 0 < value <= 500 or not 1 <= len(name) <= 60:
            raise ValueError('Вимір має бути більше 0 та не перевищувати 500; назва — до 60 символів.')
        if unit == 'кг' and name not in ('вага', 'маса тіла', 'вага тіла'):
            raise ValueError('Використовуй кг для ваги тіла, см — для обхватів.')
        if unit == 'кг':
            name = 'вага'
        result.append((name,value,unit))
    return result


async def send_chunks(message, text, **kwargs):
    for start in range(0, len(text), 3800):
        await message.reply_text(text[start:start+3800], **kwargs)


def exercise_description(e):
    title = f'#{e["exercise_id"]} · {e["name"]}'
    if e.get('is_cardio'):
        return title + '\n' + e.get('details','')
    return title + '\n' + '\n'.join(f'  {i}. {s["weight"]:g} кг × {s["reps"]} повт.' for i,s in enumerate(normalize_exercise_sets(e['sets']),1))


async def send_history(update, context, target=None, page=1):
    trainings = db.get_user_trainings(update.effective_user.id, limit=100000, include_active=True)
    if target:
        trainings = [dict(t, exercises=[e for e in t['exercises'] if norm(e['name']) == norm(target)]) for t in trainings]
        trainings = [t for t in trainings if t['exercises']]
    selection = trainings[(page-1)*5:page*5]
    if not selection:
        await update.message.reply_text('На цій сторінці ще немає записів.')
        return
    for t in selection:
        status = 'завершено' if t['date_end'] else 'триває'
        text = f'📔 Тренування №{t["training_id"]} · {t["date_start"]} · {status}\n\n'
        text += '\n\n'.join(exercise_description(e) for e in t['exercises']) or 'Вправ ще немає.'
        await send_chunks(update.message,text)
    if page*5 < len(trainings):
        await update.message.reply_text(f'Наступна сторінка: /history {page+1}' if not target else f'Показано 5 останніх тренувань цієї вправи. Повний перелік доступний через експорт.')


def graph_rows(user_id, days, target=None, today=None):
    today = today or date.today()
    start = today - timedelta(days=days-1)
    rows = []
    for t in db.get_user_trainings(user_id, limit=100000, include_active=True):
        day = parse_training_datetime(t['date_start']).date()
        if not start <= day <= today:
            continue
        for e in t['exercises']:
            if e.get('is_cardio') or target and norm(e['name']) != norm(target):
                continue
            for s in normalize_exercise_sets(e['sets']):
                rows.append(dict(kind='training', name=e['name'], day=day.isoformat(), sets=1, reps=s['reps'],value=s['weight'],unit='кг'))
    if target and not rows:
        for m in reversed(db.get_measurements_history(user_id, limit=100000)):
            day = parse_training_datetime(m['date']).date()
            if not start <= day <= today:
                continue
            try:
                values = parse_measurements(m['measurements'])
            except ValueError:
                continue
            for label,value,unit in values:
                if norm(target) == label:
                    rows.append(dict(kind='measurement',name=label,day=day.isoformat(),sets=0,reps=0,value=value,unit=unit))
    return sorted(rows,key=lambda r:r['day'])


async def show_graph(update, context, args):
    from charts import chart
    bits = args.split(maxsplit=1)
    days = int(bits[0]) if bits else 30
    if days not in (7,30,90,365):
        raise ValueError('Обери 7, 30, 90 або 365 днів.')
    target = bits[1] if len(bits)>1 else None
    rows = graph_rows(update.effective_user.id,days,target)
    if not rows:
        await update.message.reply_text('Немає даних за цей період. Перевір назву вправи або виміру.')
        return
    image = await asyncio.to_thread(chart,rows,days,target)
    caption = f'Останні {days} днів. Обсяг = вага × повторення. Враховано збережені вправи, зокрема поточне тренування.'
    if rows[0]['kind'] == 'measurement':
        caption = f'{target}: {rows[0]["value"]:g} → {rows[-1]["value"]:g} {rows[-1]["unit"]}. На графіку — останній вимір кожного дня.'
    await update.message.reply_photo(InputFile(io.BytesIO(image),filename='progress.png'),caption=caption)


async def show_statistics_menu(update, context):
    await update.message.reply_text('📈 Обери період графіка. Для окремої вправи: /graph 30 Жим лежачи', reply_markup=ReplyKeyboardMarkup([['📊 7 днів','📊 30 днів'],['📊 90 днів','📊 365 днів'],['🔙 Головне меню']],resize_keyboard=True))
    return STATS_MENU


async def handle_statistics_menu(update, context):
    if update.message.text == '🔙 Головне меню':
        from handlers_common import start
        return await start(update,context)
    m = re.fullmatch(r'📊 (7|30|90|365) днів',update.message.text)
    if m:
        await show_graph(update,context,m[1])
        return STATS_MENU
    return await show_statistics_menu(update,context)


async def save_quick(update, context, e, prefix='quick'):
    uid = update.effective_user.id
    t = db.get_current_training(uid) or db.create_training(uid)
    e['source_key'] = f'{prefix}:{uid}:{update.message.message_id}'
    db.add_exercise_to_training(t['training_id'],e)
    db.add_custom_exercise(uid,e['name'],'strength')
    context.user_data['training_id'] = t['training_id']
    context.user_data['current_training'] = db.get_current_training(uid)
    await update.message.reply_text('✅ Збережено: ' + e['name'] + '\n' + '\n'.join(f'{i}. {s["weight"]:g} кг × {s["reps"]} повт.' for i,s in enumerate(e['sets'],1)) + '\nПерегляд: /history')


async def extras(update, context):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    from training_tools import checkin_input
    if await checkin_input(update,context):
        raise ApplicationHandlerStop
    parts = text.split(maxsplit=1)
    cmd, arg = parts[0].split('@')[0].lower(), parts[1] if len(parts)>1 else ''
    buttons={'🧭 Програми':'/programs','📋 Мій план':'/plan','🧠 Налаштувати план':'/coachhelp',
        '✅ Перед тренуванням':'/checkin','🗓 Блок тренувань':'/block','📆 Звіт за тиждень':'/weekly','💾 Резервна копія':'/backup'}
    if text in buttons:
        cmd,arg=buttons[text],''
    try:
        import programs
        if cmd in programs.COMMANDS:
            await programs.handle(update,context,cmd,arg)
        elif cmd in ('/help','/tips'):
            await update.message.reply_text(HELP if cmd == '/help' else '💡 Записуй вправи під однаковими назвами. Порівнюй не лише вагу, а й повторення та підходи. Для гантелей обери одну схему: вага однієї гантелі або сумарна — і дотримуйся її. Вимірюй обхвати в тому самому місці. Це підказки до щоденника, а не індивідуальний план тренувань.')
        elif cmd == '/history':
            page = int(arg or '1')
            if page < 1:
                raise ValueError('Номер сторінки має бути від 1.')
            await send_history(update,context,page=page)
        elif cmd == '/exercise':
            if not arg:
                raise ValueError('Приклад: /exercise Жим лежачи')
            await send_history(update,context,target=arg)
        elif cmd == '/graph':
            await show_graph(update,context,arg)
        elif cmd == '/measure':
            values = parse_measurements(arg)
            normalized = '; '.join(f'{n} {v:g} {u}' for n,v,u in values)
            db.save_measurement(update.effective_user.id,normalized,f'measure:{update.effective_user.id}:{update.message.message_id}')
            await update.message.reply_text('✅ Виміри збережено: ' + normalized)
        elif cmd in ('/delete','/measure_delete'):
            uid, record = update.effective_user.id, int(arg)
            if cmd == '/delete':
                success = db.delete_exercise_record(uid,record)
            else:
                with db.connection() as c:
                    success = c.execute('DELETE FROM user_measurements WHERE id=? AND user_id=?',(record,uid)).rowcount
            await update.message.reply_text('Запис видалено.' if success else 'Запису з таким номером немає.')
        elif cmd == '/remind':
            days = int(arg)
            if not 0 <= days <= 365:
                raise ValueError('Вкажи 0–365 днів; 0 вимикає нагадування.')
            db.set_setting('reminder_days',days)
            await update.message.reply_text(f'Нагадування: після {days} днів без запису вправи, о 18:00 за часом ПК.' if days else 'Нагадування вимкнено.')
        elif cmd == '/ai':
            from local_ai import propose
            if not arg:
                raise ValueError('Приклад: /ai сьогодні жим лежачи 3 по 10 на 60 кг')
            await update.message.reply_text('🧠 Розбираю запис локально. Це може зайняти до хвилини…')
            e = await asyncio.to_thread(propose,arg)
            context.user_data['ai_pending'] = e
            await update.message.reply_text('Пропозиція: ' + e['name'] + '\n' + '\n'.join(f'{s["weight"]:g} кг × {s["reps"]}' for s in e['sets']) + '\nЗберегти? /confirm або /cancel')
        elif cmd == '/confirm':
            e = context.user_data.get('ai_pending')
            if not e:
                raise ValueError('Немає пропозиції для підтвердження.')
            await save_quick(update,context,e,'ai')
            context.user_data.pop('ai_pending',None)
        elif not text.startswith('/'):
            e = quick_parse(text)
            if e is None:
                return
            await save_quick(update,context,e)
        else:
            return
    except (ValueError,RuntimeError) as error:
        message = str(error)
        if message.startswith('invalid literal'):
            message = 'Потрібне ціле число. Приклади: /graph 30, /history 2, /delete 12, /remind 10.'
        await update.message.reply_text(message)
    raise ApplicationHandlerStop


async def reminder_job(context):
    uid = db.setting('owner')
    if uid:
        from programs import load
        if load(uid)['health'] in ('sick','pain'):
            return
    days = db.setting('reminder_days',0)
    now = datetime.now()
    if not uid or not days or now.hour < 18 or db.setting('last_reminder') == now.date().isoformat():
        return
    last = {}
    for t in db.get_user_trainings(uid,limit=100000,include_active=True):
        day = parse_training_datetime(t['date_start']).date()
        for e in t['exercises']:
            last[e['name']] = max(last.get(e['name'],day),day)
    due = [(n,(now.date()-d).days) for n,d in last.items() if (now.date()-d).days >= days]
    if due:
        text = '🔔 Давно не було записів:\n' + '\n'.join(f'• {n}: {age} днів' for n,age in due) + '\nВимкнути: /remind 0'
        for start in range(0,len(text),3800):
            await context.bot.send_message(uid,text[start:start+3800])
    db.set_setting('last_reminder',now.date().isoformat())
