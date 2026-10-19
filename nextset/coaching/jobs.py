"""One local inference at a time, responsive Telegram handlers and stale-result guards."""
import asyncio
import copy
import hashlib
import json
import time
import uuid
from contextvars import ContextVar
from datetime import datetime
from types import SimpleNamespace
import nextset.storage.database as db

CAPTURE=ContextVar('coach_save_capture',default=None)
INSTANCE=uuid.uuid4().hex
PULSE_SECONDS=20

def fingerprint(state):
    return hashlib.sha256(json.dumps({k:v for k,v in state.items() if k!='events'},sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def inputs(uid,state):
    return fingerprint({'coach':{k:v for k,v in state.items() if k!='events'},
        'diary':db.get_user_trainings(uid,limit=100000,include_active=True),
        'measurements':db.get_measurements_history(uid,limit=3)})

def record(uid, **values):
    value=db.setting(f'ai-job:{uid}',{})
    value.update(values)
    db.set_setting(f'ai-job:{uid}',value)
    return value

def status(uid):
    value=db.setting(f'ai-job:{uid}',{})
    if value.get('status') in ('running','canceling') and value.get('instance')!=INSTANCE:
        value=record(uid,status='interrupted',error='Попередній запуск перервано. Збережений план не змінено.')
    labels={'running':'ШІ працює','canceling':'Скасовано; очікую завершення обчислення',
            'ready':'Готово — результат збережено','failed':'Не вдалося завершити',
            'stale':'Дані змінилися — старий результат не застосовано',
            'interrupted':'Попередній запуск перервано','canceled':'Запит скасовано'}
    if not value:return 'Зараз немає запиту до ШІ.'
    elapsed=int(max(0,time.time()-value['started'])) if value.get('status') in ('running','canceling') else value.get('seconds',0)
    return f"⏱ {labels.get(value.get('status'),'Запит')} · {elapsed//60:02d}:{elapsed%60:02d}\n"+value.get('error','')

class Buffer:
    def __init__(self,message):
        self.message_id=message.message_id
        self.text=getattr(message,'text','')
        self.messages=[]
    async def reply_text(self,text,**kwargs):
        self.messages.append(text)

async def begin(update,context,command,arg):
    import nextset.coaching.programs as p
    uid=update.effective_user.id
    active=context.application.bot_data.get('training_ai_job')
    if active and not active['task'].done():
        await update.message.reply_text('ШІ вже зайнятий одним запитом. Меню, записи й графіки доступні.\n'+status(active['uid'])+'\nСтатус: /aistatus · скасувати: /aicancel')
        return
    state=p.load(uid)
    if command=='/block':
        value=p.number(arg or '8',4,8)
        if not value.is_integer():raise ValueError('Кількість тижнів — ціле число від 4 до 8.')
    # Fail immediately for incomplete profiles; never display a fake wait.
    if command in ('/block','/plan','/extra'):
        if state['health'] in ('sick','pain'):
            await update.message.reply_text('План на паузі через хворобу або біль. Самопочуття: /status')
            return
        if state['program'] not in p.CATALOG or any(k not in state['profile'] for k in ('вік','зріст','вага','досвід','мета','обладнання')):
            from nextset.telegram.ui import setup
            await setup(update,context)
            return
    progress=await update.message.reply_text('🧠 Запит прийнято · 00:00\nПідготовка локальної відповіді. Це може тривати кілька хвилин; точного відсотка ще немає.\n/aistatus — стан · /aicancel — скасувати. Інші функції працюють.')
    job={'uid':uid,'id':uuid.uuid4().hex,'cancel':False,'command':command,'started':time.time()}
    record(uid,status='running',instance=INSTANCE,started=job['started'],command=command,error='',result=[])
    job['task']=context.application.create_task(run(update,context,job,arg,progress,inputs(uid,state)))
    context.application.bot_data['training_ai_job']=job

async def run(update,context,job,arg,progress,original):
    import nextset.coaching.programs as p
    uid=job['uid'];buffer=Buffer(update.message);capture={}
    proxy=SimpleNamespace(effective_user=update.effective_user,message=buffer)
    local_context=SimpleNamespace(user_data=copy.deepcopy(context.user_data),application=context.application)
    async def pulse():
        while True:
            await asyncio.sleep(PULSE_SECONDS)
            seconds=int(time.time()-job['started'])
            wording='Скасування прийнято. Результат не буде застосовано.' if job['cancel'] else 'Локальний ШІ ще обчислює відповідь. Відсоток недоступний.'
            try:await progress.edit_text(f'🧠 {seconds//60:02d}:{seconds%60:02d}\n{wording}\n/aistatus · /aicancel. Записи й графіки доступні.')
            except Exception:pass  # A failed status edit must not discard the actual result.
    ticker=asyncio.create_task(pulse())
    token=CAPTURE.set(capture);committed=False
    try:
        # Each local HTTP request has its own finite timeout. Do not cancel the
        # thread early: retain the slot until inference really returns.
        await p.handle(proxy,local_context,job['command'],arg)
        if job['cancel']:
            record(uid,status='canceled')
            await update.message.reply_text('Запит скасовано. Результат не застосовано.')
            return
        current=p.load(uid)
        if inputs(uid,current)!=original or datetime.now().date().isoformat()!=datetime.fromtimestamp(job['started']).date().isoformat():
            record(uid,status='stale')
            await update.message.reply_text('Профіль, стан або план змінилися під час обчислення. Стару відповідь не застосовано. Повтори запит з актуальними даними.')
            return
        if uid in capture:
            capture[uid]['events']=list(dict.fromkeys(current['events']+capture[uid]['events']))
            db.set_setting(f'coach:{uid}',capture[uid])
        for key in ('coach_pending',):
            if key in local_context.user_data:context.user_data[key]=local_context.user_data[key]
        record(uid,status='ready',result=buffer.messages,seconds=int(time.time()-job['started']))
        committed=True
        CAPTURE.reset(token);token=None
        from nextset.telegram.ui import deliver
        await deliver(update,context,job['command'],buffer.messages)
    except Exception as error:
        if committed:
            record(uid,error='Результат збережено, але не вдалося надіслати повідомлення. Відкрий /airesult або «Мій план».')
            return
        # Neither exception URLs nor arbitrary internals reach chat/logs.
        text=str(error) if isinstance(error,(ValueError,RuntimeError)) else 'Помилка зв’язку або обробки. Спробуй ще раз; збережений план не змінено.'
        record(uid,status='failed',error=text,seconds=int(time.time()-job['started']))
        try:await update.message.reply_text('❌ ШІ не завершив запит.\n'+text+'\n/aistatus — стан. Можна повторити запит.')
        except Exception:pass
    finally:
        if token is not None:CAPTURE.reset(token)
        ticker.cancel()
        try:await ticker
        except asyncio.CancelledError:pass
        try:await progress.edit_text('✅ Готово. Результат нижче або в «Мій план».' if db.setting(f'ai-job:{uid}',{}).get('status')=='ready' else status(uid))
        except Exception:pass

async def cancel(update,context):
    job=context.application.bot_data.get('training_ai_job')
    if job and job['uid']==update.effective_user.id and not job['task'].done():
        job['cancel']=True;record(job['uid'],status='canceling')
        await update.message.reply_text('Скасування прийнято. План не буде змінено. Поточне обчислення може допрацювати; новий запит доступний після його завершення.')
    else:await update.message.reply_text('Немає активного запиту до ШІ.')
