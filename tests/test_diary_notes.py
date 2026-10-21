import csv
import io
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from openpyxl import load_workbook
import nextset.storage.database as db
from nextset.core.diary_entries import parse_sets
from nextset.telegram.diary import quick_parse, exercise_description
from nextset.telegram.handlers_export import generate_excel_report, generate_csv_export
from nextset.telegram.notes import route


class DiaryNotes(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        old=db.DB_PATH
        db.DB_PATH=Path(self.temp.name)/'diary.sqlite3'
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(setattr,db,'DB_PATH',old)
        db.ensure_bot_schema()
        self.training=db.create_training(1)['training_id']
        db.add_exercise_to_training(self.training,dict(name='Жим',type='strength',
            sets=parse_sets('70x10; коліно\n60 8; відмова'),details=' Важкий день'))
        self.exercise=db.get_training_exercises(self.training)[0]['exercise_id']

    def test_round_trip_edit_delete_and_finish_preserves_note(self):
        db.update_diary_note(1,'training',self.training,' Погано спав')
        db.update_diary_note(1,'set',self.exercise,' Змінено',2)
        db.update_diary_note(1,'exercise',self.exercise,'')
        db.finish_training(self.training)
        db.ensure_bot_schema()
        training=db.get_user_trainings(1)[0]
        self.assertEqual(training['comment'],' Погано спав')
        self.assertEqual(training['exercises'][0]['sets'][1]['note'],' Змінено')
        self.assertIn('Змінено',exercise_description(training['exercises'][0]))
        self.assertEqual(training['exercises'][0]['details'],'')

    def test_ownership_invalid_index_and_validation(self):
        for kind in ('training','exercise','set'):
            with self.assertRaises(ValueError):
                db.update_diary_note(2,kind,self.training if kind=='training' else self.exercise,'wrong',1)
        with self.assertRaises(ValueError):db.update_diary_note(1,'set',self.exercise,'wrong',0)
        with self.assertRaises(ValueError):parse_sets('70 10; '+ 'a'*1001)
        with self.assertRaises(ValueError):parse_sets('70 10; ok\n60 0; invalid')
        self.assertEqual(parse_sets('70/10')[0],dict(weight=70,reps=10))
        self.assertEqual(quick_parse('Жим 3x10 70 кг; Нотатка')['details'],' Нотатка')

    def test_exports_keep_all_three_note_scopes(self):
        db.update_diary_note(1,'training',self.training,'Сон')
        db.update_diary_note(1,'set',self.exercise,'=1+1',1)
        db.finish_training(self.training)
        rows=list(csv.reader(io.StringIO(generate_csv_export(1))))
        self.assertTrue(all(len(row)==12 for row in rows))
        self.assertEqual(rows[1][-3:],[' Важкий день',"'=1+1",'Сон'])
        book=load_workbook(io.BytesIO(generate_excel_report(1,'all_time')))
        self.assertEqual(book['Тренування']['D2'].value,'Сон')
        detail=book.worksheets[2]
        self.assertEqual(detail['J2'].value,' Важкий день')
        self.assertNotEqual(detail['K2'].data_type,'f')
        self.assertEqual(detail['K3'].value,' відмова')


class NoteCommands(DiaryNotes,unittest.IsolatedAsyncioTestCase):
    async def test_command_edit_clear_and_pain_clarification(self):
        message=SimpleNamespace(text=f'/setnote {self.exercise} 1; боліло коліно',reply_text=AsyncMock())
        update=SimpleNamespace(message=message,effective_user=SimpleNamespace(id=1))
        self.assertTrue(await route(update,None))
        self.assertEqual(message.reply_text.await_count,2)
        message.text=f'/setnote {self.exercise} 1;'
        await route(update,None)
        self.assertEqual(db.get_training_exercises(self.training)[0]['sets'][0]['note'],'')
