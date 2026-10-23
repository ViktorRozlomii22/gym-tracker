import asyncio
import copy
from datetime import date,datetime
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock,patch
import nextset.coaching.jobs as ai_jobs
import nextset.storage.database as db
import nextset.telegram.ui as ui
import nextset.telegram.methods as methods
import nextset.coaching.programs as p
import nextset.coaching.cycle as cycle
from nextset.visuals.calendar import calendar_rows,timetable
from tests.test_extensions import block_result
import nextset.ai.coach as rag

class Friendly(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=db.DB_PATH
        db.DB_PATH=Path(self.tmp.name)/'test.db';db.ensure_bot_schema()
        db.set_setting('owner',1)
        self.addCleanup(self.tmp.cleanup);self.addCleanup(setattr,db,'DB_PATH',self.old)
        self.message=SimpleNamespace(message_id=73,text='',reply_text=AsyncMock(),reply_photo=AsyncMock())
        self.update=SimpleNamespace(message=self.message,effective_user=SimpleNamespace(id=1))
        self.context=SimpleNamespace(user_data={},application=SimpleNamespace(bot_data={},create_task=asyncio.create_task))

    async def test_method_preview_does_not_mutate_then_explicit_confirm(self):
        state=p.load(1);state.update(program='madcow',cursor=6,block={'approved':True});p.save(1,state)
        for text in ('📖 '+p.CATALOG['dup']['title'],'✅ Обрати цей метод'):
            self.message.text=text;self.assertTrue(await methods.route(self.update,self.context))
            self.assertEqual(p.load(1)['program'],'madcow')
        self.message.text='🔄 Підтвердити зміну методу';await methods.route(self.update,self.context)
        saved=p.load(1);self.assertEqual(saved['program'],'dup');self.assertEqual(saved['block_history'],[{'approved':True}])

    async def test_natural_colon_profile_and_missing_question_no_invented_pr(self):
        self.message.text='/profile:27років,181см,78кг,5років, жим90кг, об’ємні плечі, обладнання типовий спортзал'
        self.assertTrue(await ui.route(self.update,self.context))
        saved=p.load(1)
        self.assertEqual(saved['profile']['досвід'],5);self.assertEqual(saved['profile']['вага'],78)
        self.assertEqual(saved['prs'],{})
        self.assertEqual(saved['profile']['мета'],'м’язи')
        self.assertFalse(db.setting('ui:1'))

    async def test_profile_wizard_validates_and_resumes_from_database(self):
        await ui.setup(self.update,self.context)
        self.message.text='17';await ui.route(self.update,self.context)
        self.assertNotIn('вік',p.load(1)['profile'])
        self.message.text='27';await ui.route(self.update,self.context)
        self.assertEqual(db.setting('ui:1')['field'],'зріст')
        self.context.user_data={};self.message.text='181';await ui.route(self.update,self.context)
        self.assertEqual(p.load(1)['profile']['зріст'],181)

    async def test_pr_wizard_requires_explicit_actual_date(self):
        for text in ('🏅 Додати PR','Жим лежачи','90','5'):
            self.message.text=text;await ui.route(self.update,self.context)
        self.assertEqual(p.load(1)['prs'],{})
        self.message.text='2099-01-01';await ui.route(self.update,self.context)
        self.assertEqual(p.load(1)['prs'],{})
        self.message.text='Сьогодні';await ui.route(self.update,self.context)
        self.assertEqual(p.load(1)['prs']['bench']['reps'],5)

    async def test_background_job_returns_before_model_completes_and_cancels(self):
        entered=asyncio.Event();release=asyncio.Event()
        async def handle(update,context,cmd,arg):
            entered.set();await release.wait()
            state=p.load(1);state['program']='dup';p.save(1,state)
            await update.message.reply_text('Відповідь')
        with patch.object(p,'handle',side_effect=handle):
            await ai_jobs.begin(self.update,self.context,'/ask','тренування')
            job=self.context.application.bot_data['training_ai_job']
            await entered.wait();self.assertFalse(job['task'].done())
            self.assertIn('ШІ працює',ai_jobs.status(1))
            self.assertIsNone(p.load(1)['program'])
            await ai_jobs.cancel(self.update,self.context);release.set();await job['task']
        self.assertIsNone(p.load(1)['program']);self.assertEqual(db.setting('ai-job:1')['status'],'canceled')

    async def run_job(self,change=None,delivery_error=False):
        async def handle(update,context,cmd,arg):
            state=p.load(1);state['program']='dup';p.save(1,state)
            if change:change()
            await update.message.reply_text('Збережена відповідь')
        deliver=AsyncMock(side_effect=RuntimeError('delivery') if delivery_error else None)
        with patch.object(p,'handle',side_effect=handle),patch.object(ui,'deliver',deliver):
            await ai_jobs.begin(self.update,self.context,'/ask','тренування')
            await self.context.application.bot_data['training_ai_job']['task']
        return deliver

    async def test_shared_ai_busy_does_not_read_other_users_status(self):
        task=SimpleNamespace(done=lambda:False)
        self.context.application.bot_data['training_ai_job']={'uid':2,'task':task}
        with patch.object(ai_jobs,'status',side_effect=AssertionError('foreign state read')):
            await ai_jobs.begin(self.update,self.context,'/ask','питання')
        text=self.message.reply_text.call_args.args[0]
        self.assertIn('зараз зайнятий',text)
        self.assertNotIn('/aicancel',text)
        self.assertIsNone(db.setting('ai-job:1'))
        self.assertIsNone(p.load(1)['program'])

    async def test_own_busy_request_keeps_status_and_cancellation_help(self):
        task=SimpleNamespace(done=lambda:False)
        self.context.application.bot_data['training_ai_job']={'uid':1,'task':task}
        with patch.object(ai_jobs,'status',return_value='Власний стан') as status:
            await ai_jobs.begin(self.update,self.context,'/ask','питання')
        status.assert_called_once_with(1)
        text=self.message.reply_text.call_args.args[0]
        self.assertIn('Власний стан',text)
        self.assertIn('/aicancel',text)

    async def test_stale_profile_or_diary_prevents_application(self):
        def change():
            state=p.load(1);state['health']='sick';db.set_setting('coach:1',state)
        await self.run_job(change)
        self.assertIsNone(p.load(1)['program']);self.assertEqual(db.setting('ai-job:1')['status'],'stale')
        before=ai_jobs.inputs(1,p.load(1));db.create_training(1)
        self.assertNotEqual(before,ai_jobs.inputs(1,p.load(1)))

    async def test_delivery_failure_keeps_saved_result_recoverable(self):
        await self.run_job(delivery_error=True)
        saved=db.setting('ai-job:1')
        self.assertEqual(saved['status'],'ready');self.assertIn('Збережена відповідь',saved['result'])
        self.assertEqual(p.load(1)['program'],'dup')

    async def test_generation_failure_is_visible_and_restart_marks_interruption(self):
        with patch.object(p,'handle',side_effect=ValueError('Немає даних')):
            await ai_jobs.begin(self.update,self.context,'/ask','тренування')
            await self.context.application.bot_data['training_ai_job']['task']
        self.assertIn('Немає даних',ai_jobs.status(1));self.assertIsNone(p.load(1)['program'])
        ai_jobs.record(1,status='running',instance='old',started=time.time())
        self.assertIn('перервано',ai_jobs.status(1))

class MethodAndCalendar(unittest.TestCase):
    def test_ten_complete_cards_and_compact_model_context(self):
        self.assertEqual(len(p.CATALOG),10)
        for key,card in p.CATALOG.items():
            self.assertIn('➕',methods.render(key));self.assertIn('➖',methods.render(key))
            self.assertLess(len(methods.render(key)),3800)
            self.assertEqual(set(methods.model_reference(key)),{'title','url','description'})
            self.assertTrue(card['sources']);self.assertTrue(card['suited_for'])

    def test_eight_week_proposal_stable_24_dates_and_png(self):
        result=block_result();result['weeks']*=2
        state={'program':'dup','profile':{'вік':27,'зріст':181,'вага':78,'досвід':5,'мета':'м’язи','обладнання':'зал'},'cursor':0,'completed':[],'prs':{},'health':'ready','feedback':{},'return_left':0}
        with patch.object(rag,'call_model',return_value=result):block=cycle.propose_block(state,8,datetime(2026,10,19))
        rows=calendar_rows(block,today=date(2026,11,1))
        self.assertEqual(len(rows),24);self.assertEqual(rows[0]['date'],date(2026,10,19))
        self.assertEqual(rows[-1]['week'],8)
        self.assertTrue(timetable(block).startswith(b'\x89PNG'))
        with self.assertRaises(ValueError):calendar_rows(block,weekdays=[0,0,2])

if __name__=='__main__':unittest.main()
