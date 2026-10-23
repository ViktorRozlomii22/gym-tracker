from pathlib import Path
import tempfile
import unittest
import nextset.storage.database as db


class UserDataDeletion(unittest.TestCase):
    def test_clear_removes_saved_personal_state_only_for_requested_user(self):
        with tempfile.TemporaryDirectory() as directory:
            original = db.DB_PATH
            db.DB_PATH = Path(directory) / 'test.sqlite3'
            try:
                db.ensure_bot_schema()
                for uid in (1, 12):
                    training = db.create_training(uid)
                    db.add_exercise_to_training(training['training_id'], dict(
                        name='Жим', type='strength', sets=[dict(weight=60, reps=10, note='Запис')]))
                    db.save_measurement(uid, 'вага 80 кг')
                    for prefix in ('coach', 'ui', 'ai-job','reminder-days','last-reminder'):
                        db.set_setting(f'{prefix}:{uid}', {'private': 'saved profile or plan'})
                db.set_setting('owner', 1)
                db.set_setting('last_daily_backup', '2026-10-22')
                self.assertTrue(db.delete_all_user_data(1))
                self.assertEqual(db.get_user_trainings(1, include_active=True), [])
                self.assertEqual(db.get_measurements_history(1), [])
                for prefix in ('coach', 'ui', 'ai-job','reminder-days','last-reminder'):
                    self.assertIsNone(db.setting(f'{prefix}:1'))
                    self.assertIsNotNone(db.setting(f'{prefix}:12'))
                self.assertTrue(db.get_user_trainings(12, include_active=True)[0]['exercises'])
                self.assertTrue(db.get_measurements_history(12))
                self.assertEqual(db.setting('owner'), 1)
                self.assertEqual(db.setting('last_daily_backup'), '2026-10-22')
                self.assertTrue(db.delete_all_user_data(1))
                self.assertEqual(db.setting('data-epoch:1'),2)
            finally:
                db.DB_PATH = original
