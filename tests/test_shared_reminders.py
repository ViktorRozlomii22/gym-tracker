from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
import unittest
from tests.test_access import Access
import nextset.storage.database as db
from nextset.storage import access
from nextset.telegram import diary


class SharedReminders(Access,unittest.IsolatedAsyncioTestCase):
    def seed(self,uid):
        training=db.create_training(uid)
        db.add_exercise_to_training(training['training_id'],dict(name=f'Вправа {uid}',type='strength',sets=[dict(weight=50,reps=10)]))
        with db.connection() as connection:
            connection.execute('UPDATE trainings SET date_start=? WHERE training_id=?',('2026-10-01T18:00:00',training['training_id']))

    async def test_personal_reminders_and_failed_recipient_do_not_block_others(self):
        _,token=access.create_invite(1)
        access.redeem(2,token)
        self.seed(1);self.seed(2)
        db.set_setting('reminder_days',7)
        db.set_setting('reminder-days:2',10)
        bot=SimpleNamespace(send_message=AsyncMock(side_effect=[RuntimeError('delivery'),None]))
        with patch.object(diary,'datetime') as clock:
            clock.now.return_value=datetime(2026,10,23,19)
            await diary.reminder_job(SimpleNamespace(bot=bot))
        calls=bot.send_message.call_args_list
        self.assertEqual([call.args[0] for call in calls],[1,2])
        self.assertNotIn('Вправа 1',calls[1].args[1])
        self.assertIsNone(db.setting('last-reminder:1'))
        self.assertEqual(db.setting('last-reminder:2'),'2026-10-23')
        access.set_active(1,2,False)
        self.assertNotIn(2,access.recipients())

    async def test_weekly_opt_in_and_delivery_are_independent(self):
        from nextset.coaching import tools,programs
        _,token=access.create_invite(1)
        access.redeem(2,token)
        for uid in (1,2):
            state=programs.load(uid)
            state['weekly_enabled']=True
            programs.save(uid,state)
        bot=SimpleNamespace(send_message=AsyncMock(side_effect=[RuntimeError('delivery'),None]))
        with patch.object(tools,'datetime') as clock,patch.object(tools,'weekly_data',side_effect=lambda uid,now:{'uid':uid}),patch.object(tools,'weekly_text',side_effect=lambda data:f"Report {data['uid']}"):
            clock.now.return_value=datetime(2026,10,25,19)
            await tools.weekly_job(SimpleNamespace(bot=bot))
        self.assertEqual([call.args for call in bot.send_message.call_args_list],[(1,'Report 1'),(2,'Report 2')])
        self.assertNotIn('last_weekly',programs.load(1))
        self.assertEqual(programs.load(2)['last_weekly'],'2026-10-25')
