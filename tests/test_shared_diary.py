from concurrent.futures import ThreadPoolExecutor
from tests.test_access import Access
from nextset.storage import access
import nextset.storage.database as db
from nextset.telegram.handlers_export import generate_csv_export


class SharedDiary(Access):
    def test_concurrent_redemption_consumes_invitation_once(self):
        _,token=access.create_invite(1)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda uid:access.redeem(uid,token),(2,3)))
        self.assertEqual(sorted(results),[False,True])
        self.assertEqual(len(access.list_members(1)),1)

    def test_diary_note_export_and_deletion_isolation_across_members(self):
        identifiers={}
        for uid in (2,3):
            _,token=access.create_invite(1)
            access.redeem(uid,token)
            training=db.create_training(uid)
            db.add_exercise_to_training(training['training_id'],dict(name=f'PrivateExercise{uid}',type='strength',
                sets=[dict(weight=uid*10,reps=8,note=f'PrivateSet{uid}')],details=f'PrivateNote{uid}'))
            identifiers[uid]=db.get_training_exercises(training['training_id'])[0]['exercise_id']
            db.update_diary_note(uid,'training',training['training_id'],f'PrivateTraining{uid}')
            db.finish_training(training['training_id'])
        with self.assertRaises(ValueError):db.update_diary_note(2,'exercise',identifiers[3],'intrusion')
        self.assertFalse(db.delete_exercise_record(2,identifiers[3]))
        export=generate_csv_export(2)
        self.assertIn('PrivateExercise2',export)
        self.assertIn('PrivateSet2',export)
        self.assertNotIn('PrivateExercise3',export)
        self.assertNotIn('PrivateSet3',export)
        access.set_active(1,2,False)
        db.delete_all_user_data(2)
        self.assertFalse(access.allowed(2))
        self.assertTrue(db.get_user_trainings(3))
        self.assertIsNone(generate_csv_export(2))
