import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import database_sqlite as db
import programs as p
import local_ai
import coach_rag as rag

class Programs(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old=db.DB_PATH
        db.DB_PATH=Path(self.tmp.name)/'test.db'
        db.ensure_bot_schema()
        self.now=datetime.now()
        def model(system,payload,schema):
            key='squat'
            return {'insufficient':False,'rationale':'План з урахуванням історії.',
                'uncertainty':'Індивідуальна реакція невідома.','citations':['acsm2026'],
                'items':[{'exercise':key,'sets':2,'reps':5,'rir':3,
                    'kg':30 if key in payload['estimated_strength_references'] else None,
                    'reason':'Помірний обсяг.','citations':['acsm2026']}]}
        self.model=patch.object(rag,'call_model',side_effect=model)
        self.mock_model=self.model.start()
        self.addCleanup(self.model.stop)
        self.s=p.load(1)
        self.s['program']='madcow'
        p.profile(self.s,'вік 30; зріст 180; вага 80; досвід 1; крок 2,5; мета м’язи; обладнання зал')
        for key in p.NAMES:
            p.add_pr(self.s,f'{key}; 80; 5; {self.now.date()}',self.now.date())

    def tearDown(self):
        db.DB_PATH=self.old
        self.tmp.cleanup()

    def test_five_selectable_templates_and_stable_preview(self):
        for key in p.CATALOG:
            self.s.update(program=key,pending=None)
            plan=p.make_plan(self.s,self.now)
            self.assertEqual(plan,p.make_plan(self.s,self.now))
            self.assertIn('пропозиція ШІ',p.render(plan))
            self.assertTrue(all(0<x['weight']<95 for x in plan['items']))
        self.assertEqual(self.s['cursor'],0)

    def test_invalid_profile_and_pr_atomic(self):
        before=dict(self.s['profile'])
        for value in ['вага nan','вік 17','зріст 180; вага -2','обладнання дім']:
            with self.assertRaises(ValueError): p.profile(self.s,value)
            self.assertEqual(before,self.s['profile'])
        for weight in ('inf','-1','5000'):
            with self.assertRaises(ValueError): p.add_pr(self.s,f'bench; {weight}; 5; {self.now.date()}',self.now.date())

    def test_no_anthropometric_strength_inference_stale_or_missing_pr(self):
        self.s['prs']={}
        plan=p.make_plan(self.s,self.now)
        self.assertTrue(all(x['weight'] is None for x in plan['items']))
        p.add_pr(self.s,f'bench; 100; 1; {(self.now-timedelta(days=91)).date()}',self.now.date())
        self.assertTrue(all(x['weight'] is None for x in p.make_plan(self.s,self.now)['items']))

    def test_illness_cannot_be_overridden_by_feeling_good(self):
        p.set_status(self.s,'хворію')
        for action in ('добре','втома'):
            with self.assertRaises(ValueError): p.set_status(self.s,action)
        with self.assertRaises(ValueError): p.make_plan(self.s,self.now,True)
        p.set_status(self.s,'одужав')
        plan=p.make_plan(self.s,self.now)
        self.assertTrue(plan['recovery'])
        self.assertEqual(self.s['return_left'],3)
        self.assertTrue(all(x['sets']==2 for x in plan['items']))

    def test_pain_requires_explicit_clearance(self):
        p.set_status(self.s,'біль')
        for action in ('одужав','хворію','добре'):
            with self.assertRaises(ValueError): p.set_status(self.s,action)
        p.set_status(self.s,'дозволено')
        self.assertEqual(self.s['return_left'],3)

    def seed_history(self, days=(6,4,2)):
        self.s['completed']=[{'at':(self.now-timedelta(days=n)).isoformat(),'bonus':False,'rir':3,'training_id':100+n} for n in days]

    def test_bonus_and_weekly_limits(self):
        self.seed_history()
        with self.assertRaises(ValueError): p.make_plan(self.s,self.now)
        with self.assertRaises(ValueError): p.make_plan(self.s,self.now,True)
        p.set_status(self.s,'добре')
        self.assertTrue(p.make_plan(self.s,self.now,True)['bonus'])
        self.s['completed'][-1]['rir']=0
        with self.assertRaises(ValueError): p.make_plan(self.s,self.now,True)

    def test_rest_and_long_gap(self):
        self.seed_history((1,))
        with self.assertRaises(ValueError): p.make_plan(self.s,self.now)
        self.seed_history((20,))
        self.assertTrue(p.make_plan(self.s,self.now)['recovery'])

    def test_completion_requires_actual_sets_and_progresses_once(self):
        plan=p.make_plan(self.s,self.now)
        with self.assertRaises(ValueError): p.complete(self.s,1,3,self.now)
        plan['approved']=True
        t=db.create_training(1)
        for item in plan['items']:
            db.add_exercise_to_training(t['training_id'],{'name':p.NAMES[item['key']],'type':'strength',
                'sets':[{'weight':item['weight'],'reps':item['reps']}]*item['sets']})
        p.complete(self.s,1,3,self.now)
        self.assertEqual(self.s['cursor'],1)
        self.assertIsNone(db.get_current_training(1))
        with self.assertRaises(ValueError): p.complete(self.s,1,3,self.now)
        self.assertTrue(self.s['completed'][-1]['actual'])

    def test_actual_failed_sets_reach_model_context_without_invented_progress(self):
        plan=p.make_plan(self.s,self.now)
        plan['approved']=True
        t=db.create_training(1)
        item=plan['items'][0]
        db.add_exercise_to_training(t['training_id'],{'name':p.NAMES[item['key']],'type':'strength','sets':[{'weight':item['weight'],'reps':1}]})
        p.complete(self.s,1,0,self.now)
        context=rag.context_for(self.s,self.now)
        self.assertEqual(context['last_sessions'][-1]['actual'][item['key']][0]['reps'],1)
        self.assertEqual(context['last_sessions'][-1]['rir'],0)

    def test_delete_also_deletes_coach_profile(self):
        p.save(1,self.s)
        db.delete_all_user_data(1)
        self.assertEqual(p.load(1)['profile'],{})

class EvidenceValidation(unittest.TestCase):
    def test_retrieval_in_ukrainian_and_no_match(self):
        self.assertTrue(rag.retrieve('гіпертрофія обсяг'))
        self.assertIn('illness',[c['id'] for c in rag.retrieve('хвороба температура')])
        self.assertEqual(rag.retrieve('quantum teleportation'),[])

    def test_fabricated_citations_rejected(self):
        with self.assertRaises(ValueError): rag.citations(['invented'],rag.library()['cards'])

    def test_no_citation_or_unsupported_answer_refuses(self):
        with patch.object(rag,'call_model') as model:
            with self.assertRaises(ValueError): rag.answer('quantum teleportation',{},datetime.now())
            model.assert_not_called()

    def test_numeric_and_missing_reference_guards(self):
        state={'prs':{},'completed':[],'profile':{},'health':'ready'}
        card=rag.library()['cards'][0]
        result={'insufficient':False,'rationale':'Тест','uncertainty':'Оцінка','citations':[card['id']],
            'items':[{'exercise':'bench','sets':3,'reps':8,'rir':2,'kg':60,'reason':'Оцінка','citations':[card['id']]}]}
        with self.assertRaises(ValueError): rag.validate_plan(result,state,datetime.now(),[card],False,False)
        state['prs']['bench']={'e1rm':100,'date':datetime.now().date().isoformat()}
        result['items'][0]['kg']=900
        with self.assertRaises(ValueError): rag.validate_plan(result,state,datetime.now(),[card],False,False)
        result['items'][0]['kg']=50
        self.assertEqual(rag.validate_plan(result,state,datetime.now(),[card],False,False)['items'][0]['weight'],50)
        with self.assertRaises(ValueError): rag.validate_plan(result,state,datetime.now(),[card],True,False)
        result['items'][0]['sets']=True
        with self.assertRaises(ValueError): rag.validate_plan(result,state,datetime.now(),[card],False,False)

class Routing(unittest.IsolatedAsyncioTestCase):
    async def test_persisted_plan_approval_actual_logging_and_replay(self):
        import diary
        from telegram.ext import ApplicationHandlerStop
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DB_PATH',Path(tmp)/'test.db'):
            db.ensure_bot_schema()
            message=SimpleNamespace(message_id=0,text='',reply_text=AsyncMock())
            update=SimpleNamespace(message=message,effective_user=SimpleNamespace(id=1))
            context=SimpleNamespace(user_data={})
            async def send(text):
                message.message_id+=1
                message.text=text
                with self.assertRaises(ApplicationHandlerStop):
                    await diary.extras(update,context)
            await send('/program hypertrophy')
            await send('/profile вік 30; зріст 180; вага 80; досвід 4; крок 2,5; мета м’язи; обладнання зал')
            await send(f'/pr squat; 80; 5; {datetime.now().date()}')
            result={'insufficient':False,'rationale':'Індивідуальна оцінка.','uncertainty':'Перевір на розминці.',
                    'citations':['acsm2026'],'items':[{'exercise':'squat','sets':2,'reps':5,'rir':3,'kg':40,
                    'reason':'Контроль обсягу.','citations':['acsm2026']}]}
            with patch.object(rag,'call_model',return_value=result):
                await send('/plan')
            self.assertFalse(p.load(1)['pending']['approved'])
            self.assertIsNone(db.get_current_training(1))
            await send('/planconfirm')
            await send('Присідання 2x5 40 кг')
            await send('/done 3')
            self.assertEqual(p.load(1)['cursor'],1)
            self.assertEqual(p.load(1)['completed'][0]['actual']['squat'][0]['weight'],40)
            with self.assertRaises(ApplicationHandlerStop):
                await diary.extras(update,context)
            self.assertEqual(p.load(1)['cursor'],1)

    async def test_ai_only_proposes_and_confirmation_uses_validated_command(self):
        state={'events':[],'health':'ready'}
        message=SimpleNamespace(message_id=1,reply_text=AsyncMock())
        update=SimpleNamespace(message=message,effective_user=SimpleNamespace(id=1))
        context=SimpleNamespace(user_data={})
        with patch.object(p,'load',return_value=state),patch.object(p,'save') as save,patch.object(local_ai,'propose_coach',return_value='/status хворію'):
            await p.handle(update,context,'/coach','хворію')
            save.assert_not_called()
            self.assertEqual(context.user_data['coach_pending'],'/status хворію')
            await p.handle(update,context,'/coachconfirm','')
            self.assertEqual(state['health'],'sick')
            save.assert_called_once()

if __name__=='__main__': unittest.main()
