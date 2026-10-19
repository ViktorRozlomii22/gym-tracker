"""Small Ukrainian home screen, explicit profile questions and plan previews."""
import asyncio
import io
import re
from datetime import date
from telegram import InputFile, ReplyKeyboardMarkup
import nextset.storage.database as db

HOME=[['💪 Почати тренування'],['🗓 Мій план','📈 Мій прогрес'],['👤 Мій профіль','⚙️ Ще']]
FIELDS=[('вік','Скільки тобі років?'),('зріст','Твій зріст у сантиметрах?'),
    ('вага','Твоя вага в кілограмах?'),('досвід','Скільки років ти тренуєшся?'),
    ('мета','Яка основна мета?'),('обладнання','Де тренуєшся?')]

def keyboard(rows):return ReplyKeyboardMarkup(rows,resize_keyboard=True)

async def home(update,context):
    await update.message.reply_text('Що робимо сьогодні?',reply_markup=keyboard(HOME))

async def setup(update,context):
    import nextset.coaching.programs as p
    state=p.load(update.effective_user.id)
    missing=[key for key,_ in FIELDS if key not in state['profile']]
    if missing:
        db.set_setting(f'ui:{update.effective_user.id}',{'kind':'profile','field':missing[0]})
        await question(update,missing[0]);return
    db.set_setting(f'ui:{update.effective_user.id}',{})
    if not state['program']:
        from nextset.telegram.methods import menu
        await menu(update,context);return
    await update.message.reply_text('✅ Профіль готовий. Додай уже виконаний підхід як орієнтир ваги або переходь до плану. Без PR потрібна калібровка на розминці.',
        reply_markup=keyboard([['🏅 Додати PR'],['🗓 Обрати дні'],['✨ Створити 8 тижнів'],['🔙 Головне меню']]))

async def question(update,field):
    choices={'мета':[['м’язи','сила','загальна']], 'обладнання':[['зал']]}
    await update.message.reply_text(dict(FIELDS)[field],reply_markup=keyboard(choices.get(field,[])+[['❌ Скасувати налаштування']]))

def natural_profile(text):
    """Extract explicit units only; never convert an ambiguous lift into a PR."""
    values={}
    for key,pattern in [('зріст',r'(\d+(?:[.,]\d+)?)\s*(?:см|cm)\b'),('вага',r'(\d+(?:[.,]\d+)?)\s*(?:кг|kg)\b')]:
        match=re.search(pattern,text,re.I)
        if match:values[key]=match[1]
    years=re.findall(r'(\d+(?:[.,]\d+)?)\s*(?:роки|років|рік|року|years?)\b',text,re.I)
    if years:
        if float(years[0].replace(',','.'))>=18:values['вік']=years.pop(0)
        if years:values['досвід']=years[0]
    if re.search(r'спортзал|тренажерн|типовий зал|типічний.*зал|обладнання\s*[-–:]?\s*зал',text,re.I):values['обладнання']='зал'
    if re.search(r'м[’\x27ʼ]?яз|мас[аиу]|об[’\x27ʼ]?єм',text,re.I):values['мета']='м’язи'
    elif re.search(r'мета\s*[-–:]?\s*сила',text,re.I):values['мета']='сила'
    return '; '.join(key+' '+value for key,value in values.items())

async def show_profile(update,context):
    import nextset.coaching.programs as p
    profile=p.load(update.effective_user.id)['profile']
    units={'вік':'років','зріст':'см','вага':'кг','досвід':'років','крок':'кг'}
    text='👤 Твій профіль\n'+'\n'.join(f'{key.capitalize()}: {value} {units.get(key,"")}' for key,value in profile.items()) if profile else '👤 Спочатку заповни профіль — по одному короткому питанню.'
    await update.message.reply_text(text,reply_markup=keyboard([['✏️ Налаштувати профіль','🏅 Додати PR'],['🧭 Усі методи','🗓 Обрати дні'],['🔙 Головне меню']]))

async def calendar(update,context):
    import nextset.coaching.programs as p
    from nextset.coaching.presentation import overview
    from nextset.telegram.diary import send_chunks
    state=p.load(update.effective_user.id)
    block=state.get('block_draft') or state.get('block')
    if not block:
        await update.message.reply_text('Створимо план із трьома тренуваннями на тиждень. Спочатку профіль і метод, потім графік.',
            reply_markup=keyboard([['✨ Створити 8 тижнів'],['👤 Мій профіль','🧭 Усі методи'],['🔙 Головне меню']]))
        return
    rows=[['🏋️ Наступна сесія','📄 Деталі плану']]
    if not block.get('approved'):rows.insert(0,['✅ Прийняти блок','❌ Відхилити блок'])
    rows += [['📑 План Excel'],['✨ Створити 8 тижнів'],['🔙 Головне меню']]
    for message in overview(block,state):
        await send_chunks(update.message,message,reply_markup=keyboard(rows))

async def export_plan(update,context):
    import nextset.coaching.programs as p
    from nextset.telegram.plan_export import workbook_bytes
    state=p.load(update.effective_user.id)
    block=state.get('block_draft') or state.get('block')
    if not block:
        await calendar(update,context);return
    data=await asyncio.to_thread(workbook_bytes,block,state)
    await update.message.reply_document(InputFile(io.BytesIO(data),filename='training-plan.xlsx'),
        caption='План за тижнями. Порожні кг ще не розраховано; пропущені тренування не вважаються виконаними.')

async def session(update,context):
    import nextset.coaching.programs as p
    state=p.load(update.effective_user.id);plan=state.get('pending')
    if not plan or plan['day']!=date.today().isoformat():
        from nextset.coaching.jobs import begin
        await begin(update,context,'/plan','');return
    from nextset.core.exercises import NAMES
    from nextset.telegram.plan_logging import actual_sets
    recorded=actual_sets(update.effective_user.id,state)
    lines=['🏋️ Наступна сесія · '+('прийнято' if plan.get('approved') else 'проєкт')]
    for item in plan['items']:
        weight=f"{item['weight']:g} кг" if item['weight'] is not None else 'підібрати на розминці'
        lines.append(f"• {NAMES[item['key']]}: {item['sets']}×{item['reps']} · {weight} · RIR {item['rir']}")
        actual=recorded.get(item['key'],[])
        if actual:
            lines.append(f'  ✅ Записано {len(actual)} підх.: '+', '.join(f"{s['weight']:g} кг × {s['reps']}" for s in actual[-5:]))
            if len(actual)>5:lines.append('  Останні 5 підходів; усі — /history')
        else:lines.append('  ⬜ Ще не записано')
    rows=[] if plan.get('approved') else [['✅ Прийняти сесію','❌ Відхилити сесію']]
    if plan.get('approved'):
        rows += [['✍️ '+NAMES[item['key']]] for item in plan['items']]
        rows += [['🏁 Завершити сесію']]
    rows += [['📄 Деталі сесії','✅ Перед тренуванням'],['🔙 Головне меню']]
    from nextset.telegram.diary import send_chunks
    await send_chunks(update.message,'\n'.join(lines),reply_markup=keyboard(rows))

async def deliver(update,context,command,messages):
    if command=='/block':await calendar(update,context)
    elif command in ('/plan','/extra'):await session(update,context)
    else:
        from nextset.telegram.diary import send_chunks
        # First messages are transient wait notices, not the answer.
        for message in messages:
            if not message.startswith('🧠 '):await send_chunks(update.message,message)

async def route(update,context):
    import nextset.coaching.programs as p
    from nextset.telegram.plan_logging import route as logging_route
    if await logging_route(update,context):return True
    text=update.message.text.strip();uid=update.effective_user.id
    ui=db.setting(f'ui:{uid}',{})
    if text in ('/start','/cancel','❌ Скасувати налаштування','🔙 Головне меню') or text.startswith('/start '):
        db.set_setting(f'ui:{uid}',{})
        if text=='❌ Скасувати налаштування':await home(update,context);return True
        return False
    if text=='👤 Мій профіль':await show_profile(update,context);return True
    if text=='✏️ Налаштувати профіль':
        db.set_setting(f'ui:{uid}',{'kind':'profile','field':'вік','editing':True})
        await question(update,'вік');return True
    if text=='🏅 Додати PR':
        db.set_setting(f'ui:{uid}',{'kind':'pr','step':0,'values':[]})
        await update.message.reply_text('Обери вправу для вже виконаного підходу. Не потрібно спеціально тестувати максимум.',reply_markup=keyboard([[p.NAMES[k]] for k in ('bench','squat','deadlift','press','row') if k in p.NAMES]+[['❌ Скасувати налаштування']]))
        return True
    if text=='🗓 Обрати дні':
        await update.message.reply_text('Які три дні зручні? Цей вибір діє для нового блоку.',reply_markup=keyboard([['Пн · Ср · Пт','Вт · Чт · Сб'],['🔙 Головне меню']]))
        return True
    if text in ('Пн · Ср · Пт','Вт · Чт · Сб'):
        state=p.load(uid);state['weekdays']=[0,2,4] if text.startswith('Пн') else [1,3,5];p.save(uid,state)
        await setup(update,context);return True
    if text=='🗓 Мій план':await calendar(update,context);return True
    if text in ('📑 План Excel','/planexcel'):await export_plan(update,context);return True
    if text in ('🏋️ Наступна сесія','📋 Мій план') or text=='/plan':await session(update,context);return True
    if text=='📈 Мій прогрес':
        await update.message.reply_text('Покажи фактичний прогрес за період:',reply_markup=keyboard([['📊 7 днів','📊 30 днів'],['📊 56 днів','📊 90 днів','📊 365 днів'],['🔙 Головне меню']]))
        return True
    if re.fullmatch(r'📊 (7|30|56|90|365) днів',text):
        from nextset.telegram.diary import show_graph
        await show_graph(update,context,text.split()[1]);return True
    if text=='⚙️ Ще':
        await update.message.reply_text('Додаткові можливості. Усі команди також доступні через /help і /coachhelp.',reply_markup=keyboard([
            ['🧭 Усі методи','✅ Перед тренуванням'],['📆 Звіт за тиждень','💾 Резервна копія'],
            ['🧠 Стан ШІ','🛑 Скасувати ШІ'],['📏 Мої виміри','📤 Експорт даних'],
            ['📝 Мої вправи','📊 Історія тренувань'],['❓ Довідка','🔙 Головне меню']]))
        return True
    aliases={'✨ Створити 8 тижнів':('/block','8'),'✅ Прийняти блок':('/blockconfirm',''),
        '❌ Відхилити блок':('/blockreject',''),'✅ Прийняти сесію':('/planconfirm',''),
        '❌ Відхилити сесію':('/planreject',''),'🧠 Стан ШІ':('/aistatus',''),
        '🛑 Скасувати ШІ':('/aicancel',''),'📄 Деталі сесії':('/sessiondetails',''),'📄 Деталі плану':('/blockdetails','')}
    match=re.match(r'^(/\w+)(?:@\w+)?\s*:?\s*(.*)$',text,re.S)
    cmd,arg=aliases.get(text,(match[1].lower(),match[2]) if match else ('',''))
    if cmd=='/profile' and arg:
        try:
            state=p.load(uid)
            try:p.profile(state,arg)
            except ValueError:
                parsed=natural_profile(arg)
                if not parsed:raise ValueError('Не вдалося розібрати профіль. Натисни «Налаштувати профіль» — запитаю по одному полю.')
                p.profile(state,parsed)
            p.save(uid,state)
            await update.message.reply_text('✅ Зрозумілі поля профілю збережено. Для PR потрібні вправа, вага, повторення й дата окремо.')
            await setup(update,context)
        except ValueError as error:await update.message.reply_text(str(error))
        return True
    if cmd in ('/aistatus','/aicancel','/airesult'):
        import nextset.coaching.jobs as ai_jobs
        if cmd=='/aicancel':await ai_jobs.cancel(update,context)
        elif cmd=='/airesult':
            from nextset.telegram.diary import send_chunks
            value=db.setting(f'ai-job:{uid}',{})
            if value.get('status')=='ready':await deliver(update,context,value['command'],value.get('result',[]))
            else:await update.message.reply_text(ai_jobs.status(uid))
        else:await update.message.reply_text(ai_jobs.status(uid)+'\n/airesult — останній результат')
        return True
    if cmd in ('/block','/extra','/ask','/coach','/swap','/weeklyai'):
        if cmd=='/block' and not arg and (p.load(uid).get('block_draft') or p.load(uid).get('block')):
            await calendar(update,context);return True
        from nextset.coaching.jobs import begin
        await begin(update,context,cmd,arg);return True
    if cmd in ('/sessiondetails','/blockdetails'):
        from nextset.telegram.diary import send_chunks
        state=p.load(uid)
        if cmd=='/sessiondetails':value=state.get('pending');output=p.render(value) if value else 'Ще немає сесії.'
        else:
            from nextset.coaching.cycle import render_block
            value=state.get('block_draft') or state.get('block');output=render_block(value) if value else 'Ще немає блоку.'
        await send_chunks(update.message,output);return True
    if text in aliases:
        await p.handle(update,context,cmd,arg)
        if cmd.startswith('/block'):await calendar(update,context)
        elif cmd=='/planconfirm':await session(update,context)
        return True
    if ui and not text.startswith('/'):
        try:
            if ui['kind']=='profile':
                field=ui['field'];state=p.load(uid);p.profile(state,field+' '+text);p.save(uid,state)
                index=[k for k,_ in FIELDS].index(field)+1
                if ui.get('editing') and index<len(FIELDS):
                    ui['field']=FIELDS[index][0];db.set_setting(f'ui:{uid}',ui);await question(update,ui['field'])
                else:await setup(update,context)
            elif ui['kind']=='pr':
                step=ui['step']
                if step==0:value=p.exercise_id(text)
                elif step==1:value=str(p.number(text,.5,500))
                elif step==2:
                    number=p.number(text,1,10)
                    if not number.is_integer():raise ValueError('Повторення — ціле число 1–10.')
                    value=str(int(number))
                else:
                    value=date.today().isoformat() if text=='Сьогодні' else text
                    state=p.load(uid);p.add_pr(state,'; '.join(ui['values']+[value]),date.today());p.save(uid,state)
                    db.set_setting(f'ui:{uid}',{});await update.message.reply_text('✅ Фактичний підхід збережено.');await setup(update,context);return True
                ui['values'].append(value);ui['step']+=1;db.set_setting(f'ui:{uid}',ui)
                prompt=['','Скільки кг? Штанга — разом із грифом, гантеля — одна.','Скільки повторень було виконано (1–10)?','Коли виконано? РРРР-ММ-ДД або «Сьогодні».'][ui['step']]
                rows=[['Сьогодні']] if ui['step']==3 else []
                await update.message.reply_text(prompt,reply_markup=keyboard(rows+[['❌ Скасувати налаштування']]))
        except ValueError as error:await update.message.reply_text(str(error))
        return True
    return False
