from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import unittest
from nextset.telegram.diary import send_chunks, exercise_description


class TextDelivery(unittest.IsolatedAsyncioTestCase):
    async def check_delivery(self, text):
        message=SimpleNamespace(reply_text=AsyncMock())
        await send_chunks(message,text,disable_notification=True)
        chunks=[call.args[0] for call in message.reply_text.await_args_list]
        self.assertEqual(''.join(chunks),text)
        for chunk in chunks:
            self.assertTrue(chunk)
            self.assertLessEqual(len(chunk.encode('utf-16-le'))//2,3800)
        self.assertTrue(all(call.kwargs.get('disable_notification') for call in message.reply_text.await_args_list))
        return chunks

    async def test_delivery_preserves_text_with_emoji_at_utf16_boundaries(self):
        for text in ('','а'*3801,'💪'*3800,'а'*3799+'💪'+'б','💪'*1899+'а💪','Результати\n'+('70 кг × 10 ✅💪\n'*500)):
            with self.subTest(length=len(text)):
                await self.check_delivery(text)

    async def test_long_emoji_notes_fit_telegram_messages_without_losing_sets(self):
        text=exercise_description(dict(exercise_id=1,name='Жим',details='Тренування',sets=[
            dict(weight=70,reps=10,note='💪'*1000),
            dict(weight=65,reps=8,note='✅'*1000),
            dict(weight=60,reps=12,note='📝'*1000)]))
        chunks=await self.check_delivery(text)
        self.assertGreater(len(chunks),1)

    async def test_measurement_history_splits_without_losing_records_or_keyboard(self):
        from nextset.telegram.handlers_measurements import show_measurements_history
        from nextset.core.constants import MAIN_MENU
        records = [dict(id=i, date='23.11.2026 10:00',
                        measurements=f'Талія {80+i} см; ' + '💪'*500)
                   for i in range(1, 11)]
        message = SimpleNamespace(from_user=SimpleNamespace(id=42), reply_text=AsyncMock())
        with patch('nextset.telegram.handlers_measurements.get_measurements_history',
                   return_value=records) as history:
            state = await show_measurements_history(SimpleNamespace(message=message), None)
        history.assert_called_once_with(42, limit=10)
        self.assertEqual(state, MAIN_MENU)
        calls = message.reply_text.await_args_list
        self.assertGreater(len(calls), 1)
        expected = '📏 Історія твоїх вимірів:\n\n'
        for row in records:
            expected += f"📅 #{row['id']} · {row['date']}\n   {row['measurements']}\n\n"
        expected += 'Усього записів: 10'
        self.assertEqual(''.join(call.args[0] for call in calls), expected)
        for call in calls:
            self.assertLessEqual(len(call.args[0].encode('utf-16-le'))//2, 3800)
        self.assertIsNotNone(calls[-1].kwargs.get('reply_markup'))
