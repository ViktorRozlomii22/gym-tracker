import copy
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
import zipfile
import database_sqlite as db
import programs as p
import coach_rag as rag
import training_cycle as cycle
import training_tools as tt
import backups
from ai_evaluation import athlete
from diary import quick_parse, extras
from telegram.ext import ApplicationHandlerStop

def block_result():
    return {'insufficient':False,'rationale':'Стабільні сесії з урахуванням відновлення.',
        'citations':['acsm2026'],'weeks':['Оцінюй запас і фактичні підходи.']*4,
        'sessions':[{'title':f'Сесія {i}','items':[{'exercise':'squat','sets':[2,3],'reps':[5,8],'rir':[2,4]}]} for i in range(3)]}

def plan_result(key='squat',kg=50,sets=2):
    return {'insufficient':False,'rationale':'Враховано дані.','uncertainty':'Реакція індивідуальна.',
        'citations':['acsm2026'],'items':[{'exercise':key,'sets':sets,'reps':5,'rir':3,'kg':kg,
        'reason':'Стартова оцінка, перевір на розминці.','citations':['acsm2026']}]}

class Extensions(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.patch=patch.object(db,'DB_PATH',self.root/'test.sqlite3'); self.patch.start()
        self.bp=patch.object(backups,'DATA_DIR',self.root); self.bp.start()
        db.ensure_bot_schema(); self.now=datetime.now(); self.state=athlete(self.now)
        self.cards=rag.library()['cards']
    def tearDown(self):
        self.bp.stop(); self.patch.stop(); self.tmp.cleanup()
    def block(self):
        b=cycle.validate_block(block_result(),4,self.cards); b.update(approved=True,start_cursor=0)
        self.state['block']=b; return b
    def actual(self,key='squat'):
        t=db.create_training(1)
        db.add_exercise_to_training(t['training_id'],quick_parse(p.NAMES[key]+' 2x5 50 кг'))
        return t
    def test_existing_profiles_migrate_without_losing_data(self):
        db.set_setting('coach:1',{'profile':{'досвід':4},'cursor':8})
        s=p.load(1); self.assertEqual(s['cursor'],8); self.assertIsNone(s['block']); self.assertEqual(s['exercise_feedback'],[])
    def test_block_repeats_and_exhausts_without_skips_advancing(self):
        self.block(); self.assertEqual(cycle.current_session(self.state)['week'],1)
        self.state['cursor']=3; self.assertEqual(cycle.current_session(self.state)['week'],2)
        self.state['cursor']=12
        with self.assertRaises(ValueError): cycle.current_session(self.state)
    def test_malformed_blocks_are_rejected(self):
        for change in ('id','range','count','source'):
            b=block_result()
            if change=='id': b['sessions'][0]['items'][0]['exercise']=[]
            if change=='range': b['sessions'][0]['items'][0]['reps']=[8,5]
            if change=='count': b['weeks'].pop()
            if change=='source': b['citations']=['madeup']
            with self.assertRaises(ValueError): cycle.validate_block(b,4,self.cards)
    def test_generated_session_obeys_approved_blueprint(self):
        self.block()
        with patch.object(rag,'call_model',return_value=plan_result('bench')):
            with self.assertRaises(ValueError): p.make_plan(self.state,self.now)
        self.assertIsNone(self.state['pending'])
        with patch.object(rag,'call_model',return_value=plan_result()):
            plan=p.make_plan(self.state,self.now)
        self.assertEqual(plan['block_week'],1)
    def test_checkin_invalidates_plan_without_clearing_health_pause(self):
        self.state.update(health='sick',pending={'test':1},swap_draft={'test':1})
        tt.apply_checkin(self.state,{'sleep':8,'energy':5,'soreness':0,'minutes':60},self.now)
        self.assertEqual(self.state['health'],'sick'); self.assertIsNone(self.state['pending'])
        with self.assertRaises(ValueError): tt.apply_checkin(self.state,{'sleep':8,'energy':2.5,'soreness':0,'minutes':60},self.now)
    def test_fatigued_load_and_short_time_guards(self):
        tt.apply_checkin(self.state,{'sleep':4,'energy':2,'soreness':4,'minutes':15},self.now)
        with self.assertRaises(ValueError): rag.validate_plan(plan_result(kg=90),self.state,self.now,self.cards,False,False)
        with self.assertRaises(ValueError): rag.validate_plan(plan_result(sets=3),self.state,self.now,self.cards,False,False)
        self.assertEqual(rag.context_for(self.state,self.now)['checkin']['energy'],2)
        self.assertIsNone(rag.context_for(self.state,self.now+timedelta(days=1))['checkin'])
    def test_feedback_requires_actual_and_pain_pauses(self):
        with self.assertRaises(ValueError): tt.add_feedback(self.state,1,'squat; 2; ні; 4',self.now)
        t=self.actual(); tt.add_feedback(self.state,1,'squat; 2; ні; 4',self.now)
        self.assertEqual(self.state['exercise_feedback'][0]['training_id'],t['training_id'])
        tt.add_feedback(self.state,1,'squat; 1; так; 5',self.now)
        self.assertEqual(len(self.state['exercise_feedback']),1); self.assertEqual(self.state['health'],'pain')
    def test_negative_checkin_blocks_bonus_even_after_good_status(self):
        self.state['completed']=[{'at':(self.now-timedelta(days=n)).isoformat(),'bonus':False,'rir':4} for n in (6,4,2)]
        self.state.update(health='good',status_day=self.now.date().isoformat())
        tt.apply_checkin(self.state,{'sleep':8,'energy':1,'soreness':0,'minutes':60},self.now)
        with patch.object(rag,'call_model',side_effect=AssertionError('must gate before inference')):
            with self.assertRaises(ValueError): p.make_plan(self.state,self.now,True)
    def test_feedback_controls_bonus_eligibility_after_completion(self):
        self.actual()
        with patch.object(rag,'call_model',return_value=plan_result()): plan=p.make_plan(self.state,self.now)
        plan['approved']=True
        tt.add_feedback(self.state,1,'squat; 1; ні; 5',self.now)
        p.complete(self.state,1,4,self.now)
        self.assertEqual(self.state['completed'][0]['rir'],1)
        self.assertEqual(self.state['completed'][0]['feedback']['squat']['difficulty'],5)
        tt.add_feedback(self.state,1,'squat; 0; ні; 5',self.now)
        self.assertEqual(self.state['completed'][0]['rir'],0)
    def test_swap_uses_own_reference_and_keeps_unrelated_items(self):
        b=self.block()
        with patch.object(rag,'call_model',return_value=plan_result()): p.make_plan(self.state,self.now)
        original=copy.deepcopy(self.state['pending'])
        with patch.object(rag,'call_model',return_value=plan_result('legpress',50)):
            with self.assertRaises(ValueError): cycle.swap_proposal(self.state,'squat','зайнято',self.now)
        with patch.object(rag,'call_model',return_value=plan_result('legpress',None)):
            draft=cycle.swap_proposal(self.state,'squat','зайнято',self.now)
        self.assertEqual(self.state['pending'],original)
        self.state['swap_draft']=draft; cycle.accept_swap(self.state)
        self.assertIsNone(self.state['pending']['items'][0]['weight'])
        self.assertFalse(self.state['pending']['approved'])
        self.assertEqual(cycle.current_session(self.state)['items'][0]['exercise'],'legpress')
        self.assertEqual(b['sessions'][0]['items'][0]['exercise'],'squat')
    def test_weekly_actual_sessions_and_comparison_boundaries(self):
        t=self.actual(); db.finish_training(t['training_id'])
        past=db.create_training(1)
        db.add_exercise_to_training(past['training_id'],quick_parse('Присідання 1x5 40 кг'))
        db.finish_training(past['training_id'])
        with db.connection() as c: c.execute('UPDATE trainings SET date_start=? WHERE training_id=?',((self.now-timedelta(days=7)).isoformat(),past['training_id']))
        data=tt.weekly_data(1,self.now)
        self.assertEqual(len(data['sessions']),1); self.assertEqual(data['sets'],2)
        self.assertAlmostEqual(data['best']['Присідання'],50*(1+5/30))
        self.assertAlmostEqual(data['previous_best']['Присідання'],40*(1+5/30))
    def test_backup_roundtrip_preserves_coach_and_excludes_token(self):
        self.actual(); p.save(1,self.state)
        (self.root/'.env').write_text('private marker')
        archive=backups.create_backup()
        with zipfile.ZipFile(archive) as z: self.assertEqual(set(z.namelist()),{'manifest.json','nextset.sqlite3'})
        db.set_setting('coach:1',{'cursor':99}); backups.restore_backup(archive)
        self.assertEqual(p.load(1)['profile']['досвід'],4)
        self.assertEqual((self.root/'.env').read_text(),'private marker')
        self.assertEqual(len(db.get_user_trainings(1,include_active=True)),1)
    def test_corrupt_backups_leave_current_database_untouched(self):
        db.set_setting('marker','safe'); bad=self.root/'bad.zip'
        for mode in ('checksum','schema','entries'):
            raw=b'not sqlite'
            manifest={'format':1,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest() if mode=='schema' else 'wrong'}
            with zipfile.ZipFile(bad,'w') as z:
                z.writestr('nextset.sqlite3',raw); z.writestr('manifest.json',json.dumps(manifest))
                if mode=='entries': z.writestr('../unexpected','x')
            with self.assertRaises(Exception): backups.restore_backup(bad)
            self.assertEqual(db.setting('marker'),'safe')
    def test_backup_retention_and_daily_deduplication(self):
        self.assertIsNotNone(backups.daily_backup()); self.assertIsNone(backups.daily_backup())
        for _ in range(15): backups.create_backup()
        self.assertEqual(len(backups.list_backups()),14)
    @unittest.skipUnless(__import__('sys').platform=='win32','Windows instance lock')
    def test_restore_refuses_a_running_instance_before_prompting(self):
        import msvcrt
        lock=(self.root/'.running.lock').open('w+b'); lock.write(b'0'); lock.flush(); lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
            with patch('builtins.input',side_effect=AssertionError('must refuse before prompt')):
                with self.assertRaises(RuntimeError): backups.restore_console()
        finally:
            lock.close()
    def test_missing_real_model_cannot_report_mocked_pass(self):
        from ai_evaluation import run_suite
        with patch('ai_setup.available_models',return_value=None):
            with self.assertRaises(RuntimeError): run_suite(self.root/'eval')
        self.assertFalse((self.root/'eval').exists())

class TelegramExtensions(unittest.IsolatedAsyncioTestCase):
    async def test_menu_buttons_do_not_pass_caption_as_command_argument(self):
        update=SimpleNamespace(message=SimpleNamespace(text='🗓 Блок тренувань'),effective_user=SimpleNamespace(id=1))
        context=SimpleNamespace(user_data={})
        with patch.object(p,'handle',new_callable=AsyncMock) as handler:
            with self.assertRaises(ApplicationHandlerStop): await extras(update,context)
        self.assertEqual(handler.call_args.args[2:],('/block',''))
    async def test_checkin_wizard_validates_and_saves_four_steps(self):
        now=datetime.now(); state=athlete(now)
        update=SimpleNamespace(message=SimpleNamespace(text='',reply_text=AsyncMock()),effective_user=SimpleNamespace(id=1))
        context=SimpleNamespace(user_data={})
        await tt.start_checkin(update,context)
        with patch.object(p,'load',return_value=state), patch.object(p,'save') as save:
            for text in ('bad','8','4','1','45'):
                update.message.text=text; self.assertTrue(await tt.checkin_input(update,context))
            save.assert_called_once(); self.assertEqual(state['checkin']['minutes'],45)
        self.assertNotIn('checkin_wizard',context.user_data)
    async def test_weekly_delivery_requires_opt_in_and_sends_once(self):
        now=datetime(2026,10,11,18,1); state={'weekly_enabled':False}
        context=SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock()))
        with patch.object(tt,'datetime') as clock,patch.object(tt.db,'setting',return_value=1),patch.object(p,'load',return_value=state),patch.object(p,'save'),patch.object(tt,'weekly_data',return_value={}),patch.object(tt,'weekly_text',return_value='report'):
            clock.now.return_value=now
            await tt.weekly_job(context); context.bot.send_message.assert_not_called()
            state['weekly_enabled']=True
            await tt.weekly_job(context); await tt.weekly_job(context)
        context.bot.send_message.assert_awaited_once_with(1,'report')

if __name__=='__main__': unittest.main()
