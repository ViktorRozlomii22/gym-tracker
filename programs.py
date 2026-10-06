"""Persisted AI coaching with actual-workout feedback and approval."""
import json
import math
from datetime import date, datetime, timedelta
import database as db

from exercise_catalog import NAMES
# The catalog contains references, not hardcoded workout prescriptions.
from coach_rag import references
CATALOG = references()

def load(uid):
    defaults={'profile':{},'prs':{},'program':None,'cursor':0,'health':'ready','return_left':0,
        'completed':[], 'events':[], 'feedback':{},'pending':None,'block':None,'block_draft':None,
        'swap_draft':None,'checkin':None,'exercise_feedback':[],'weekly_enabled':False}
    return dict(defaults,**db.setting(f'coach:{uid}',{}))

def save(uid, state):
    db.set_setting(f'coach:{uid}', state)

def number(value, low, high):
    try:
        result = float(str(value).replace(',','.'))
    except (ValueError, TypeError):
        raise ValueError('Потрібне число.') from None
    if not math.isfinite(result) or not low <= result <= high:
        raise ValueError(f'Значення має бути від {low:g} до {high:g}.')
    return result

def exercise_id(value):
    value = ' '.join(value.lower().split())
    for key, name in NAMES.items():
        if value in (key, name.lower()):
            return key
    raise ValueError('Невідома вправа. Назви: ' + ', '.join(NAMES.values()))

def profile(state, text):
    """Validate entire update before changing stored state."""
    fields = dict(state['profile'])
    limits = {'вік':(18,100), 'зріст':(100,230), 'вага':(30,300), 'досвід':(0,80), 'крок':(.5,10)}
    choices = {'мета':('сила','м’язи','загальна'), 'обладнання':('зал',)}
    for part in text.split(';'):
        bits = part.strip().split(maxsplit=1)
        if len(bits)!=2:
            raise ValueError('Приклад: /profile вік 30; зріст 180; вага 80; досвід 1; крок 2,5; мета м’язи; обладнання зал')
        key, value = bits
        if key in limits:
            fields[key] = number(value,*limits[key])
        elif key in choices and value in choices[key]:
            fields[key] = value
        else:
            raise ValueError('Поля: вік, зріст (см), вага (кг), досвід (роки), крок (кг), мета (сила/м’язи/загальна), обладнання зал. Обхвати: /measure.')
    state['profile'] = fields
    state['pending'] = None
    state['swap_draft'] = None
    state['block_draft'] = None

def add_pr(state, text, today):
    bits = [x.strip() for x in text.split(';')]
    if len(bits)!=4:
        raise ValueError('Приклад: /pr Жим лежачи; 60; 8; 2026-10-06 — вага, повторення (1–10), дата. Лише вже виконаний підхід, не тестуй максимум спеціально.')
    key = exercise_id(bits[0])
    weight, reps = number(bits[1],.5,500), number(bits[2],1,10)
    if not reps.is_integer():
        raise ValueError('Повторення — ціле число.')
    try:
        day = date.fromisoformat(bits[3])
    except ValueError:
        raise ValueError('Дата: РРРР-ММ-ДД.') from None
    if day > today:
        raise ValueError('Дата PR не може бути в майбутньому.')
    state['prs'][key] = {'weight':weight,'reps':int(reps),'date':day.isoformat(),
                         'e1rm':weight if reps==1 else weight*(1+reps/30)}
    state['feedback'] = {k:v for k,v in state['feedback'].items() if not k.startswith(key+':')}
    state['pending'] = None
    state['swap_draft'] = None

def recent(state, now):
    return [x for x in state['completed'] if now-timedelta(days=7) < datetime.fromisoformat(x['at']) <= now]

def round_down(weight, step):
    return round(math.floor((weight+1e-9)/step)*step, 2)

def make_plan(state, now, bonus=False):
    if state['health'] in ('sick','pain'):
        raise ValueError('План на паузі. При хворобі чи болю силове тренування не пропоную. За болю у грудях, задишки чи непритомності звернися по медичну допомогу. Після одужання: /status одужав; після болю та дозволу фахівця: /status дозволено.')
    if state['program'] not in CATALOG:
        raise ValueError('Спочатку обери програму: /programs')
    if any(x not in state['profile'] for x in ('вік','зріст','вага','досвід','мета','обладнання')):
        raise ValueError('Спочатку /profile: вік, зріст, вага, досвід, мета, обладнання. Приклад є в /coachhelp.')
    workouts = recent(state, now)
    if workouts and now-datetime.fromisoformat(workouts[-1]['at']) < timedelta(hours=48):
        raise ValueError('Від останньої записаної сесії ще не минуло 48 годин. Зараз відновлення; план доступний пізніше.')
    if bonus:
        from coach_rag import fatigued
        if state['health']!='good' or fatigued(state,now) or state.get('status_day')!=now.date().isoformat() or state['return_left'] or len(workouts)!=3 or any(x['bonus'] or x['rir']<3 for x in workouts):
            raise ValueError('Додатковий день доступний після 3 основних сесій за 7 днів, за доброго самопочуття (/status добре), без повернення після паузи. Він легкий і не змінює основний цикл.')
    elif sum(not x['bonus'] for x in workouts)>=3 or len(workouts)>=4:
        raise ValueError('Три основні сесії за останні 7 днів уже виконано. Відпочинь або перевір /extra.')
    pending = state['pending']
    if pending and pending['day']==now.date().isoformat() and pending['bonus']==bonus:
        return pending
    gap = (now-datetime.fromisoformat(state['completed'][-1]['at'])).days if state['completed'] else 0
    recovery = state['return_left']>0 or gap>=14
    from coach_rag import generate
    from training_cycle import current_session
    if not bonus:
        current_session(state)  # Detect an exhausted block before starting inference.
    proposal = generate(state,now,bonus,recovery)
    plan = dict(proposal,day=now.date().isoformat(),cursor=state['cursor'],bonus=bonus,
                recovery=recovery,program=state['program'])
    state['pending'] = plan
    return plan


def render(plan):
    from coach_rag import source_text
    lines = ['🧠 '+('Легка додаткова сесія' if plan['bonus'] else 'Індивідуальна сесія ШІ'),
             'Орієнтир: '+CATALOG[plan['program']]['title'],
             'Це пропозиція ШІ за джерелами, не оригінальний план автора.']
    for item in plan['items']:
        weight = f'{item["weight"]:g} кг' if item['weight'] is not None else 'легка вага після розминки'
        lines.append(f'• {NAMES[item["key"]]}: {item["sets"]}×{item["reps"]}, {weight}, запас {item["rir"]}\n  {item["basis"]} '+','.join('['+x+']' for x in item['citations']))
    lines += [plan['rationale'],'Невизначеність: '+plan['uncertainty'],source_text(plan['sources']),
              'Вага штанги разом із грифом; гантелі — одна. Перевір вагу на розминці. Зупинись при болю.',
              '✅ Прийнято. Записуй фактичні підходи, потім /done 3 (мінімальний запас за сесію).' if plan.get('approved') else 'Прийняти: /planconfirm. Відхилити: /planreject. Виконане зберігається лише через щоденник і /done.']
    return '\n'.join(lines)


def complete(state, uid, rir, now):
    plan = state['pending']
    if not plan or plan['day']!=now.date().isoformat():
        raise ValueError('Немає сьогоднішнього плану. Відкрий /plan або /extra.')
    if not plan.get('approved'):
        raise ValueError('Спочатку переглянь і прийми пропозицію: /planconfirm.')
    if state['health'] in ('sick','pain'):
        raise ValueError('План на паузі.')
    # Only actual diary entries from a fresh, unused training may support progress.
    used = {x['training_id'] for x in state['completed']}
    trainings = db.get_user_trainings(uid,include_active=True)
    from bot_utils import parse_training_datetime, normalize_exercise_sets
    candidates = [t for t in trainings if t['training_id'] not in used and parse_training_datetime(t['date_start']).date()==now.date()]
    if not candidates:
        raise ValueError('Спочатку запиши фактично виконані підходи в щоденник.')
    training = candidates[0]
    actual = {}
    for exercise in training['exercises']:
        try:
            key = exercise_id(exercise['name'])
        except ValueError:
            continue
        actual.setdefault(key,[]).extend(normalize_exercise_sets(exercise['sets']))
    if not any(actual.get(item['key']) for item in plan['items']):
        raise ValueError('У щоденнику немає вправ із цього плану. Використовуй назви з плану.')
    exercise_feedback={x['key']:x for x in state.get('exercise_feedback',[]) if x['training_id']==training['training_id']}
    reported=[x['rir'] for x in exercise_feedback.values()]
    effective_rir=min([rir]+reported)
    state['completed'].append({'at':now.isoformat(),'bonus':plan['bonus'],'training_id':training['training_id'],
        'plan':plan,'rir':effective_rir,'actual':actual,'feedback':exercise_feedback,'checkin':state.get('checkin')})
    if not plan['bonus']:
        state['cursor'] += 1
        state['return_left'] = max(0,state['return_left']-1)
        # A long gap starts two more reduced sessions after the first return session.
        if plan['recovery'] and len(state['completed'])>1 and (now-datetime.fromisoformat(state['completed'][-2]['at'])).days>=14:
            state['return_left'] = max(2,state['return_left'])
    state['pending'] = None
    state['swap_draft'] = None
    state['health'] = 'ready'
    if not training['date_end']:
        db.finish_training(training['training_id'])

def set_status(state, text):
    actions = {'хворію':'sick','біль':'pain','втома':'tired','добре':'good'}
    if text in ('одужав','дозволено'):
        if state['health']=='pain' and text!='дозволено':
            raise ValueError('Після болю повернення лише після оцінки фахівця: /status дозволено.')
        if state['health'] not in ('sick','pain'):
            raise ValueError('Пауза через хворобу або біль не активна.')
        state['health']='ready'
        state['return_left']=3
        result = 'Повернення: 3 полегшені сесії. Лише якщо симптоми минули; якщо вони повертаються — зупинись.'
    elif text in actions:
        if state['health']=='pain' and text!='біль':
            raise ValueError('Пауза через біль активна. /status дозволено — лише після оцінки фахівця.')
        if state['health'] in ('sick','pain') and text in ('добре','втома'):
            raise ValueError('Пауза активна. Спочатку явно підтвердь одужання або дозвіл після болю.')
        state['health']=actions[text]
        result = 'Стан збережено. План перебудовано; /plan.' if text in ('добре','втома') else 'Тренування призупинено. При температурі не тренуйся. При болю в грудях, задишці чи непритомності звернися по медичну допомогу.'
    else:
        raise ValueError('/status хворію | біль | втома | добре | одужав | дозволено')
    state['pending']=None
    state['swap_draft']=None
    state['block_draft']=None
    state['status_day']=date.today().isoformat()
    return result

HELP = '''🧭 Програми · 3 рази на тиждень
/programs — вибір п’яти адаптованих програм
/profile вік 30; зріст 180; вага 80; досвід 4; крок 2,5; мета м’язи; обладнання зал
Зріст у см, вага в кг, досвід у роках; наразі потрібен зал зі штангою та блоками. Обхвати: /measure.
/pr Жим лежачи; 60; 8; 2026-10-06
PR — вже виконана вага; повторення 1–10; фактична дата. Для кожної вправи окремо. Старші за 90 днів — лише історія.
/plan — наступна сесія; щонайменше 48 год відпочинку
/done 3 — завершити після запису фактичних підходів, мінімальний запас повторень (RIR) 0–5
/skip робота — пропуск, наступна сесія лишається тією самою
/status хворію — пауза; /status одужав — поступове повернення
/status біль — пауза; /status дозволено — після оцінки фахівця
/status втома або /status добре — самопочуття
/extra — легкий четвертий день після трьох основних
/checkin — сон, енергія, крепатура та час перед сесією, кнопками
/block 4 — структура на 4–6 тижнів; /blockconfirm — прийняти
/feedback Жим лежачи; 2; ні; 4; важкий останній підхід — RIR, біль, складність, примітка
/swap Жим лежачи; лавка зайнята — заміна; /swapconfirm — прийняти
/weekly — факти за 7 днів; /weeklyai — висновки ШІ з джерелами
/weeklyremind on — автозвіт у неділю о 18:00; off — вимкнути
/backup — локальна резервна копія; /backups — перелік; відновлення через RESTORE.cmd
/coach вчора пропустив через роботу — локальний ШІ розбирає повідомлення; зміна тільки після /coachconfirm
ШІ використовує локальні джерела (/sources), профіль і фактичну історію. /ask — питання до бази. /planconfirm — прийняти план, /planreject — відхилити.
Розрахунок — стартова оцінка, не точне визначення твоєї сили. Зріст та обхвати не визначають кг. Усі плани — адаптації бота для дорослих; оригінали: /programs.'''

COMMANDS = {'/programs','/program','/profile','/pr','/plan','/done','/skip','/status','/extra','/coachhelp','/coach','/coachconfirm','/ask','/sources','/planconfirm','/planreject'}
from training_tools import COMMANDS as EXTRA_COMMANDS
COMMANDS |= EXTRA_COMMANDS

async def handle(update, context, cmd, arg):
    import asyncio
    uid, now = update.effective_user.id, datetime.now()
    state = load(uid)
    event = f'{update.message.message_id}:{cmd}'
    if event in state['events']:
        await update.message.reply_text('Цю зміну вже збережено. /plan — поточний план.')
        return
    mutating = True
    if cmd in EXTRA_COMMANDS:
        from training_tools import handle as extra_handle
        text,mutating=await extra_handle(update,context,cmd,arg,state,now)
    elif cmd=='/coachhelp':
        text=HELP; mutating=False
    elif cmd=='/programs':
        text='Обери одну програму. Це добірка, не науковий рейтинг; усі версії адаптовані ботом.\n\n'+'\n\n'.join(f'{p["title"]}\n/program {k}\n{p["url"]}' for k,p in CATALOG.items())
        mutating=False
    elif cmd=='/program':
        if arg not in CATALOG:
            raise ValueError('Обери: /program hypertrophy | madcow | 531 | bridge | fullbody')
        if state.get('block'):
            state.setdefault('block_history',[]).append(state['block'])
        state.update(program=arg,cursor=0,pending=None,feedback={},block=None,block_draft=None,swap_draft=None)
        text='✅ Програму обрано. Дані й PR: /coachhelp. План: /plan.'
    elif cmd=='/profile':
        if not arg:
            text='Профіль: '+json.dumps(state['profile'],ensure_ascii=False)+'\nНалаштування: /coachhelp'; mutating=False
        else:
            profile(state,arg); text='✅ Профіль оновлено. Обхвати зберігай через /measure; PR через /pr.'
    elif cmd=='/pr':
        add_pr(state,arg,now.date()); text='✅ PR збережено. /plan — оцінка робочої ваги.'
    elif cmd in ('/plan','/extra'):
        state['measurements']=[{'date':m['date'],'measurements':m['measurements'][:500]} for m in db.get_measurements_history(uid,limit=3)]
        await update.message.reply_text('🧠 Шукаю джерела й готую сесію локально. На слабкому ПК запит може тривати до 6 хвилин…')
        text=render(await asyncio.to_thread(make_plan,state,now,cmd=='/extra'))
    elif cmd=='/planconfirm':
        if not state['pending'] or state['pending']['day']!=now.date().isoformat():
            raise ValueError('Немає актуальної пропозиції. /plan')
        if state['health'] in ('sick','pain'):
            raise ValueError('План на паузі.')
        state['pending']['approved']=True
        text='✅ План прийнято. Виконай розминку; записуй фактичні підходи й заверши через /done. /plan — перегляд.'
    elif cmd=='/planreject':
        state['pending']=None
        state['swap_draft']=None
        text='Пропозицію відхилено. Можна оновити профіль/PR/самопочуття й повторити /plan.'
    elif cmd=='/sources':
        from coach_rag import library, source_text
        data=library()
        text='Локальна база '+data['version']+'; короткі огляди джерел, не навчені ваги моделі.\n'+source_text(data['cards'])
        mutating=False
    elif cmd=='/ask':
        from coach_rag import answer
        await update.message.reply_text('🧠 Шукаю відповідь у локальній базі джерел…')
        text=await asyncio.to_thread(answer,arg,state,now)
        mutating=False
    elif cmd=='/status':
        text=set_status(state,arg)
    elif cmd=='/skip':
        if not arg or len(arg)>300:
            raise ValueError('Приклад: /skip робота. Якщо хворієш — /status хворію.')
        state['pending']=None
        state['swap_draft']=None
        state.setdefault('skips',[]).append({'day':now.date().isoformat(),'reason':arg})
        text='Пропуск записано. Цикл не просувається, пропущені підходи не наздоганяємо. /plan'
    elif cmd=='/done':
        rir=number(arg,0,5)
        if not rir.is_integer():
            raise ValueError('RIR — ціле число 0–5.')
        complete(state,uid,int(rir),now)
        text='✅ Фактичну сесію враховано. ШІ врахує фактичні підходи та запас у наступній пропозиції. /plan після відпочинку.'
    elif cmd=='/coach':
        from local_ai import propose_coach
        context.user_data.pop('coach_pending',None)
        intent=await asyncio.to_thread(propose_coach,arg)
        context.user_data['coach_pending']=intent
        text='ШІ пропонує команду: '+intent+'\nЗастосувати: /coachconfirm. Скасувати: /cancel.'
        mutating=False
    elif cmd=='/coachconfirm':
        intent=context.user_data.pop('coach_pending',None)
        if not intent:
            raise ValueError('Немає пропозиції ШІ.')
        bits=intent.split(maxsplit=1)
        await handle(update,context,bits[0],bits[1] if len(bits)>1 else '')
        return
    if mutating:
        state['events'].append(event)
        save(uid,state)
    from diary import send_chunks
    if text:
        await send_chunks(update.message,text)
