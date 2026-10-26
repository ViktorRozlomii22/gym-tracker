from datetime import date
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

import nextset.storage.database as db
from nextset.coaching import programs as p
from nextset.telegram import plan_logging as logging


class PlanLogging(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        old = db.DB_PATH
        db.DB_PATH = Path(self.tmp.name) / 'test.db'
        db.ensure_bot_schema()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(setattr, db, 'DB_PATH', old)
        self.message = SimpleNamespace(text='', message_id=1, reply_text=AsyncMock())
        self.update = SimpleNamespace(message=self.message, effective_user=SimpleNamespace(id=1))
        self.context = SimpleNamespace(user_data={})
        state = p.load(1)
        state['pending'] = dict(day=date.today().isoformat(), approved=True, bonus=False,
                                cursor=0, recovery=False, items=[dict(key='bench', sets=3, reps=10, rir=2, weight=60)])
        p.save(1, state)

    async def send(self, text):
        self.message.text = text
        self.message.message_id += 1
        return await logging.route(self.update, self.context)

    async def test_actual_values_saved_and_session_completed(self):
        await self.send('✍️ Жим лежачи')
        self.assertEqual(db.get_user_trainings(1, include_active=True), [])
        await self.send('55 8\n50,5 9')
        actual = logging.actual_sets(1, p.load(1))['bench']
        self.assertEqual(actual, [{'weight':55, 'reps':8}, {'weight':50.5, 'reps':9}])
        self.assertIn('Записано 2 підх.', str(self.message.reply_text.call_args_list))
        await self.send('🏁 Завершити сесію')
        await self.send('2')
        self.assertEqual(p.load(1)['cursor'], 1)
        self.assertIsNone(p.load(1)['pending'])
        self.assertIsNone(db.get_current_training(1))

    async def test_invalid_input_and_changed_session_do_not_save(self):
        await self.send('✍️ Жим лежачи')
        await self.send('60 0')
        self.assertIsNone(db.get_current_training(1))
        state = p.load(1)
        state['pending']['items'][0]['weight'] = 50
        p.save(1, state)
        await self.send('60 10')
        self.assertIsNone(db.get_current_training(1))
        self.assertFalse(db.setting('ui:1'))

    async def test_unapproved_plan_and_empty_finish_do_not_advance(self):
        await self.send('🏁 Завершити сесію')
        await self.send('2')
        self.assertEqual(p.load(1)['cursor'], 0)
        state = p.load(1)
        state['pending']['approved'] = False
        p.save(1, state)
        await self.send('✍️ Жим лежачи')
        self.assertFalse(db.setting('ui:1'))

    async def test_cancel_preserves_diary(self):
        await self.send('✍️ Жим лежачи')
        await self.send('/cancel')
        self.assertFalse(db.setting('ui:1'))
        self.assertIsNone(db.get_current_training(1))

    async def test_command_navigation_clears_pending_set_or_finish_input(self):
        for button in ('✍️ Жим лежачи', '🏁 Завершити сесію'):
            for command in ('/history', '/help', '/plan', '/unknown'):
                with self.subTest(button=button, command=command):
                    await self.send(button)
                    self.assertTrue(db.setting('ui:1'))
                    self.assertFalse(await self.send(command))
                    self.assertFalse(db.setting('ui:1'))
                    self.assertFalse(await self.send('60 10'))
                    self.assertFalse(await self.send('2'))
                    self.assertIsNone(db.get_current_training(1))
                    self.assertEqual(p.load(1)['cursor'], 0)

    async def test_account_navigation_exits_pending_input_in_full_ui_router(self):
        from nextset.telegram import ui
        db.set_setting('owner',1)
        for button in ('✍️ Жим лежачи','🏁 Завершити сесію'):
            for destination in ('/account','/members','👥 Учасники'):
                with self.subTest(button=button,destination=destination):
                    await self.send(button)
                    self.message.text=destination
                    self.assertTrue(await ui.route(self.update,self.context))
                    self.assertFalse(db.setting('ui:1'))
                    self.assertFalse(await self.send('60 10'))
                    self.assertFalse(await self.send('2'))
                    self.assertIsNone(db.get_current_training(1))
                    self.assertEqual(p.load(1)['cursor'],0)
