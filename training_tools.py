"""Check-in, actual exercise feedback, weekly summaries and Telegram controls."""
import asyncio
from datetime import datetime, timedelta
from telegram import ReplyKeyboardMarkup
import database as db
from bot_utils import normalize_exercise_sets, parse_training_datetime

CHECK_STEPS=[('sleep','😴 Скільки годин ти спав?', ['4','6','8','9']),
             ('energy','⚡ Енергія: 1 — дуже мало, 5 — багато', ['1','2','3','4','5']),
             ('soreness','🦵 Крепатура: 0 — немає, 5 — сильна. Біль через травму: /status біль', ['0','1','2','3','4','5']),
             ('minutes','⏱ Скільки хвилин маєш на тренування?', ['20','30','45','60','90'])]
LIMITS={'sleep':(0,14),'energy':(1,5),'soreness':(0,5),'minutes':(15,120)}

async def checkin_prompt(message, step):
    _,text,choices=CHECK_STEPS[step]
    await message.reply_text(text,reply_markup=ReplyKeyboardMarkup([choices,['❌ Скасувати перевірку']],resize_keyboard=True,one_time_keyboard=True))

async def start_checkin(update,context):
    context.user_data['checkin_wizard']={'step':0,'values':{}}
    await checkin_prompt(update.message,0)

async def checkin_input(update,context):
    wizard=context.user_data.get('checkin_wizard')
    if wizard is None or not update.message or not update.message.text or update.message.text.startswith('/'):
        return False
    from programs import number, load, save
    text=update.message.text.strip()
    if text=='❌ Скасувати перевірку':
        context.user_data.pop('checkin_wizard',None)
        await update.message.reply_text('Перевірку скасовано. /plan — план.',
            reply_markup=ReplyKeyboardMarkup([['📋 Мій план','✅ Перед тренуванням']],resize_keyboard=True))
        return True
    key=CHECK_STEPS[wizard['step']][0]
    try:
        value=number(text,*LIMITS[key])
        if key!='sleep' and not value.is_integer():
            raise ValueError('Потрібне ціле число.')
    except ValueError as error:
        await update.message.reply_text(str(error))
        return True
    wizard['values'][key]=value
    wizard['step']+=1
    if wizard['step']<len(CHECK_STEPS):
        await checkin_prompt(update.message,wizard['step'])
    else:
        state=load(update.effective_user.id)
        apply_checkin(state,wizard['values'],datetime.now())
        save(update.effective_user.id,state)
        context.user_data.pop('checkin_wizard',None)
        await update.message.reply_text('✅ Самопочуття збережено. ШІ врахує його в /plan.',
            reply_markup=ReplyKeyboardMarkup([['📋 Мій план','🗓 Блок тренувань'],['📆 Звіт за тиждень','🔙 Головне меню']],resize_keyboard=True))
    return True

def apply_checkin(state, values, now):
    from programs import number
    checked={k:number(values.get(k),*limits) for k,limits in LIMITS.items()}
    for k in ('energy','soreness','minutes'):
        if not checked[k].is_integer():
            raise ValueError('Потрібні цілі оцінки та хвилини.')
    state['checkin']=dict(checked,day=now.date().isoformat())
    state['pending']=None
    state['swap_draft']=None
    # A check-in never clears an illness or pain pause.

def add_feedback(state, uid, text, now):
    from programs import number, exercise_id, set_status
    parts=[x.strip() for x in text.split(';')]
    if len(parts) not in (4,5):
        raise ValueError('Приклад: /feedback Жим лежачи; 2; ні; 4; останній підхід важкий — RIR 0–5, біль так/ні, складність 1–5, примітка необов’язкова.')
    key=exercise_id(parts[0]); rir=number(parts[1],0,5); difficulty=number(parts[3],1,5)
    if not rir.is_integer() or not difficulty.is_integer() or parts[2] not in ('так','ні') or (len(parts)==5 and len(parts[4])>200):
        raise ValueError('RIR і складність — цілі; біль: так або ні; примітка до 200 символів.')
    trainings=db.get_user_trainings(uid,include_active=True)
    matching=[]
    for training in trainings:
        if parse_training_datetime(training['date_start']).date()!=now.date():
            continue
        for e in training['exercises']:
            try:
                match=exercise_id(e['name'])==key
            except ValueError:
                match=False
            if match and normalize_exercise_sets(e['sets']):
                matching.append(training); break
    if not matching:
        raise ValueError('Спочатку запиши сьогоднішні фактичні підходи цієї вправи.')
    training_id=matching[0]['training_id']
    feedback={'training_id':training_id,'key':key,'rir':int(rir),'pain':parts[2]=='так',
              'difficulty':int(difficulty),'note':parts[4] if len(parts)==5 else '', 'at':now.isoformat()}
    state['exercise_feedback']=[x for x in state.get('exercise_feedback',[]) if (x['training_id'],x['key'])!=(training_id,key)]+[feedback]
    for session in state['completed']:
        if session['training_id']==training_id:
            session['feedback']={x['key']:x for x in state['exercise_feedback'] if x['training_id']==training_id}
            session['rir']=min(session['rir'],int(rir))
    if feedback['pain']:
        set_status(state,'біль')
    return feedback

def weekly_data(uid, now):
    from programs import load
    today=now.date(); start=today-timedelta(days=6); previous=start-timedelta(days=7)
    trainings=db.get_user_trainings(uid,limit=100000,include_active=True)
    sessions=[]; best={}; old={}; volume=0; exercises=0
    for t in trainings:
        day=parse_training_datetime(t['date_start']).date()
        if day>today or day<previous:
            continue
        current=day>=start
        if current and t['exercises']:
            sessions.append({'id':t['training_id'],'day':day.isoformat(),'finished':bool(t['date_end'])})
        for e in t['exercises']:
            if e.get('is_cardio'):
                continue
            sets=normalize_exercise_sets(e['sets'])
            if current:
                exercises+=len(sets)
                volume+=sum(s['weight']*s['reps'] for s in sets)
            for s in sets:
                if 1<=s['reps']<=10 and s['weight']>0:
                    estimate=s['weight'] if s['reps']==1 else s['weight']*(1+s['reps']/30)
                    values=best if current else old
                    values[e['name']]=max(values.get(e['name'],0),estimate)
    measurement={}
    from diary import parse_measurements
    for row in reversed(db.get_measurements_history(uid,limit=10000)):
        day=parse_training_datetime(row['date']).date()
        if not today-timedelta(days=35)<=day<=today:
            continue
        try:
            values=parse_measurements(row['measurements'])
        except ValueError:
            continue
        for name,value,unit in values:
            measurement.setdefault(name,[]).append({'day':day.isoformat(),'value':value,'unit':unit})
    state=load(uid)
    skipped=[x for x in state.get('skips',[]) if start<=datetime.fromisoformat(x['day']).date()<=today]
    return {'start':start.isoformat(),'end':today.isoformat(),'sessions':sessions,'sets':exercises,
            'volume':round(volume,1),'best':best,'previous_best':old,'measurements':measurement,
            'skips':skipped,'health':state['health']}

def weekly_text(data):
    lines=[f'📆 Звіт {data["start"]} — {data["end"]}',
        f'Сесій із записами: {len(data["sessions"])} (завершено {sum(x["finished"] for x in data["sessions"])})',
        f'Робочих підходів: {data["sets"]}; записаний обсяг: {data["volume"]:g} кг×повт.',
        f'Пропусків: {len(data["skips"])}.']
    for name,value in sorted(data['best'].items())[:12]:
        prior=data['previous_best'].get(name)
        delta=f' ({value-prior:+.1f} кг до попередніх 7 днів)' if prior is not None else ' (немає попередньої оцінки)'
        lines.append(f'• {name}: оцінка 1ПМ {value:.1f} кг'+delta)
    for name,rows in sorted(data['measurements'].items())[:12]:
        first,last=rows[0],rows[-1]
        lines.append(f'📏 {name}: {first["value"]:g} → {last["value"]:g} {last["unit"]} ({first["day"]} → {last["day"]})')
    lines.append('Оцінка 1ПМ приблизна; техніка й обладнання мають бути однаковими. Виміри — доступні точки за 35 днів.')
    lines.append('Поради за джерелами: /weeklyai. Автозвіт у неділю о 18:00: /weeklyremind on; вимкнути: /weeklyremind off.')
    return '\n'.join(lines)

async def weekly_job(context):
    from programs import load, save
    from diary import send_chunks
    now=datetime.now(); uid=db.setting('owner')
    if not uid or now.weekday()!=6 or now.hour<18:
        return
    state=load(uid)
    if not state.get('weekly_enabled') or state.get('last_weekly')==now.date().isoformat():
        return
    text=weekly_text(weekly_data(uid,now))
    # No model runs automatically for a scheduled report.
    for start in range(0,len(text),3800):
        await context.bot.send_message(uid,text[start:start+3800])
    state['last_weekly']=now.date().isoformat(); save(uid,state)

COMMANDS={'/checkin','/feedback','/block','/blockconfirm','/blockreject','/swap','/swapconfirm','/swapreject',
          '/weekly','/weeklyai','/weeklyremind','/backup','/backups'}

async def handle(update,context,cmd,arg,state,now):
    from programs import number, exercise_id, render
    from training_cycle import propose_block, render_block, swap_proposal, accept_swap
    uid=update.effective_user.id
    if cmd=='/checkin':
        await start_checkin(update,context)
        return '',False
    if cmd=='/feedback':
        feedback=add_feedback(state,uid,arg,now)
        return '✅ Відгук про вправу збережено.'+(' Через біль план призупинено. /status дозволено — після оцінки фахівця.' if feedback['pain'] else ''),True
    if cmd=='/block':
        if not arg and state.get('block'):
            return render_block(state['block']),False
        value=number(arg or '4',4,6)
        if not value.is_integer():
            raise ValueError('Довжина блоку — 4, 5 або 6 тижнів.')
        await update.message.reply_text('🧠 Готую структуру блоку за джерелами…')
        draft=await asyncio.to_thread(propose_block,state,int(value),now)
        state['block_draft']=draft
        return render_block(draft),True
    if cmd=='/blockconfirm':
        draft=state.get('block_draft')
        if not draft or state['health'] in ('sick','pain'):
            raise ValueError('Немає доступної пропозиції блоку або план на паузі.')
        if state.get('block'):
            state.setdefault('block_history',[]).append(state['block'])
        draft.update(approved=True,start_cursor=state['cursor'])
        state.update(block=draft,block_draft=None,pending=None,swap_draft=None)
        return '✅ Блок прийнято. Вправи стабільні; ШІ адаптує навантаження за відгуками. /checkin → /plan',True
    if cmd=='/blockreject':
        state['block_draft']=None
        return 'Пропозицію блоку відхилено. Поточний прийнятий блок збережено.',True
    if cmd=='/swap':
        parts=[x.strip() for x in arg.split(';',1)]
        if len(parts)!=2 or not 1<=len(parts[1])<=200:
            raise ValueError('Приклад: /swap Жим лежачи; лавка зайнята')
        if any(word in parts[1].lower() for word in ('бол','травм','pain','injur')):
            raise ValueError('При болю або травмі: /status біль. Заміна не призначена для лікування.')
        await update.message.reply_text('🧠 Підбираю альтернативу того самого руху…')
        state['swap_draft']=await asyncio.to_thread(swap_proposal,state,exercise_id(parts[0]),parts[1],now)
        preview=render(state['swap_draft']['plan']).rsplit('\n',1)[0]
        return preview+'\nПрийняти саме заміну: /swapconfirm; відхилити: /swapreject.',True
    if cmd=='/swapconfirm':
        if state['health'] in ('sick','pain') or not state.get('swap_draft') or state['swap_draft']['plan']['day']!=now.date().isoformat():
            raise ValueError('Немає актуальної заміни або план на паузі.')
        accept_swap(state)
        return '✅ Заміна внесена. Перевір повний план: /plan; прийняти сесію: /planconfirm. Вага між вправами не переноситься.',True
    if cmd=='/swapreject':
        state['swap_draft']=None
        return 'Пропозицію заміни відхилено.',True
    if cmd in ('/weekly','/weeklyai'):
        data=weekly_data(uid,now)
        text=weekly_text(data)
        if cmd=='/weeklyai':
            from coach_rag import weekly_advice
            await update.message.reply_text('🧠 Готую висновки за тиждень з джерелами…')
            text=await asyncio.to_thread(weekly_advice,data,state,now)
        return text,False
    if cmd=='/weeklyremind':
        if arg not in ('on','off'):
            raise ValueError('/weeklyremind on або /weeklyremind off')
        state['weekly_enabled']=arg=='on'
        return 'Автозвіт увімкнено: неділя 18:00 за часом ПК.' if arg=='on' else 'Автозвіт вимкнено.',True
    if cmd=='/backup':
        from backups import create_backup
        path=await asyncio.to_thread(create_backup)
        return '💾 Локальна копія: '+path.name+'\nПапка data/backups. Для іншого ПК скопіюй архів. Відновлення: RESTORE.cmd при зупиненому боті. Токен не входить до копії.',False
    if cmd=='/backups':
        from backups import list_backups
        paths=list_backups()
        return '💾 Локальні копії:\n'+('\n'.join(x.name for x in paths[:14]) or 'Ще немає. /backup'),False
    raise ValueError('Невідома дія.')
