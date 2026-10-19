"""Record actual sets from a session without copying prescribed performance."""
from datetime import date
import re

from nextset.core.exercises import NAMES
from nextset.core.formatting import normalize_exercise_sets, parse_training_datetime
import nextset.storage.database as db


def actual_sets(uid, state):
    used = {entry['training_id'] for entry in state['completed']}
    candidates = [training for training in db.get_user_trainings(uid, include_active=True)
                  if training['training_id'] not in used
                  and parse_training_datetime(training['date_start']).date() == date.today()]
    result = {}
    if candidates:
        from nextset.coaching.programs import exercise_id
        for exercise in candidates[0]['exercises']:
            try:
                key = exercise_id(exercise['name'])
            except ValueError:
                continue
            result.setdefault(key, []).extend(normalize_exercise_sets(exercise['sets']))
    return result


def parse_sets(text):
    lines = text.strip().splitlines()
    if not 1 <= len(lines) <= 100:
        raise ValueError('Введи 1–100 підходів, кожен окремим рядком: кг повторення.')
    sets = []
    for line in lines:
        match = re.fullmatch(r'\s*(\d+(?:[.,]\d+)?)\s+(\d+)\s*', line)
        if not match:
            raise ValueError('Кожен рядок: кг повторення. Наприклад: 60 10')
        weight, reps = float(match[1].replace(',', '.')), int(match[2])
        if not 0 <= weight <= 1000 or not 1 <= reps <= 1000:
            raise ValueError('Перевір значення: 0–1000 кг, 1–1000 повторень.')
        sets.append(dict(weight=weight, reps=reps))
    return sets


async def route(update, context):
    from nextset.coaching import programs as p
    from nextset.telegram.ui import keyboard, session, home
    from nextset.telegram.diary import save_quick
    uid = update.effective_user.id
    text = update.message.text.strip()
    setting = db.setting(f'ui:{uid}', {})
    active = setting.get('kind') in ('plan_sets', 'plan_finish')
    if text in ('↩️ До сесії', '/cancel', '🔙 Головне меню') and active:
        db.set_setting(f'ui:{uid}', {})
        if text == '↩️ До сесії':
            await session(update, context)
        else:
            await home(update, context)
        return True
    selecting = text.startswith('✍️ ')
    finishing = text == '🏁 Завершити сесію'
    if not selecting and not finishing and not (active and not text.startswith('/')):
        return False
    # Other menu buttons remain navigable while an input is pending.
    if active and not selecting and not finishing and any(text.startswith(x) for x in ('🗓', '📈', '👤', '⚙️', '🏋️', '📄', '✅')):
        db.set_setting(f'ui:{uid}', {})
        return False
    state = p.load(uid)
    plan = state.get('pending')
    if not plan or plan.get('day') != date.today().isoformat() or not plan.get('approved'):
        db.set_setting(f'ui:{uid}', {})
        await update.message.reply_text('Спочатку відкрий і прийми сьогоднішню сесію: /plan.')
        return True
    if selecting or finishing:
        key = next((item['key'] for item in plan['items'] if '✍️ ' + NAMES[item['key']] == text), None)
        if selecting and key is None:
            await update.message.reply_text('Цієї вправи вже немає в поточній сесії. Відкрий /plan.')
            return True
        db.set_setting(f'ui:{uid}', dict(kind='plan_finish' if finishing else 'plan_sets',
                       key=key, plan=plan))
        prompt = ('Який найменший запас повторень був за сесію? Введи 0–5. Це завершить сесію за фактичними записами.'
                  if finishing else f'{NAMES[key]}\nВведи фактично виконані підходи, кожен окремим рядком: кг повторення.\nНаприклад:\n60 10\n60 9\n55 10\nНові рядки додаються до записаних. Для вправ без додаткової ваги — 0 кг.')
        await update.message.reply_text(prompt, reply_markup=keyboard([['↩️ До сесії']]))
        return True
    if setting.get('plan') != plan:
        db.set_setting(f'ui:{uid}', {})
        await update.message.reply_text('Сесія змінилася. Відкрий /plan і знову обери вправу.')
        return True
    try:
        if setting['kind'] == 'plan_finish':
            if not re.fullmatch('[0-5]', text):
                raise ValueError('Введи ціле число від 0 до 5.')
            await p.handle(update, context, '/done', text)
            db.set_setting(f'ui:{uid}', {})
            await home(update, context)
        else:
            sets = parse_sets(text)
            current = db.get_current_training(uid)
            if current and parse_training_datetime(current['date_start']).date() != date.today():
                raise ValueError('Є незавершене тренування за інший день. Заверши його через меню тренування перед новим записом.')
            await save_quick(update, context, dict(name=NAMES[setting['key']], type='strength', sets=sets), 'plan')
            db.set_setting(f'ui:{uid}', {})
            await session(update, context)
    except ValueError as error:
        await update.message.reply_text(str(error))
    return True
