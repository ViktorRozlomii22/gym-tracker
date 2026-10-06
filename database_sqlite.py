"""SQLite implementation of the NextSet database interface for Windows."""
import json
import math
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from paths import DATA_DIR
from utils_constants import DEFAULT_STRENGTH_EXERCISES, DEFAULT_CARDIO_EXERCISES

STRENGTH_TYPE, CARDIO_TYPE = 'strength', 'cardio'
DB_PATH = Path(os.getenv('NEXTSET_DB', str(DATA_DIR / 'nextset.sqlite3')))

@contextmanager
def connection():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        with conn:
            yield conn
    finally:
        conn.close()

def ensure_bot_schema():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connection() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT);
        CREATE TABLE IF NOT EXISTS trainings(training_id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
          date_start TEXT NOT NULL, date_end TEXT, comment TEXT DEFAULT '', measurements TEXT DEFAULT '');
        CREATE UNIQUE INDEX IF NOT EXISTS one_active ON trainings(user_id) WHERE date_end IS NULL;
        CREATE TABLE IF NOT EXISTS training_exercises(exercise_id INTEGER PRIMARY KEY,
          training_id INTEGER NOT NULL REFERENCES trainings(training_id) ON DELETE CASCADE,
          name TEXT NOT NULL, type TEXT NOT NULL, sets TEXT DEFAULT '[]', time_minutes REAL,
          distance_meters REAL, speed_kmh REAL, details TEXT DEFAULT '', source_key TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS custom_exercises(user_id INTEGER, name TEXT, type TEXT, PRIMARY KEY(user_id,name,type));
        CREATE TABLE IF NOT EXISTS user_hidden_defaults(user_id INTEGER, name TEXT, type TEXT, PRIMARY KEY(user_id,name,type));
        CREATE TABLE IF NOT EXISTS user_measurements(id INTEGER PRIMARY KEY,user_id INTEGER,
          measurement_date TEXT NOT NULL, measurements TEXT NOT NULL, source_key TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        ''')

def setting(key, default=None):
    with connection() as c:
        r = c.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        return json.loads(r[0]) if r else default

def set_setting(key, value):
    with connection() as c:
        c.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, json.dumps(value)))

def create_user(user_id, username, first_name):
    with connection() as c:
        c.execute('INSERT OR IGNORE INTO users VALUES (?,?,?)', (user_id,username,first_name))
    return True

def _training(row):
    if not row:
        return None
    result = dict(row)
    for key in ('date_start', 'date_end'):
        result[key] = datetime.fromisoformat(result[key]).strftime('%d.%m.%Y %H:%M') if result[key] else None
    result['exercises'] = get_training_exercises(result['training_id'])
    return result

def get_current_training(user_id):
    with connection() as c:
        row = c.execute('SELECT * FROM trainings WHERE user_id=? AND date_end IS NULL', (user_id,)).fetchone()
    return _training(row)

def create_training(user_id):
    with connection() as c:
        c.execute('INSERT OR IGNORE INTO trainings(user_id,date_start) VALUES (?,?)', (user_id,datetime.now().isoformat()))
    return get_current_training(user_id)

def finish_training(training_id, comment=''):
    with connection() as c:
        return bool(c.execute('UPDATE trainings SET date_end=?, comment=? WHERE training_id=? AND date_end IS NULL', (datetime.now().isoformat(),comment,training_id)).rowcount)

def get_user_trainings(user_id, limit=10000, include_active=False):
    with connection() as c:
        rows = c.execute('SELECT * FROM trainings WHERE user_id=?' + ('' if include_active else ' AND date_end IS NOT NULL') + ' ORDER BY date_start DESC,training_id DESC LIMIT ?', (user_id,limit)).fetchall()
    return [_training(r) for r in rows]

def save_training_measurements(training_id, measurements):
    with connection() as c:
        return bool(c.execute('UPDATE trainings SET measurements=? WHERE training_id=?', (measurements,training_id)).rowcount)

def add_exercise_to_training(training_id, exercise_data):
    e = exercise_data
    if not isinstance(e.get('name'), str) or not 1 <= len(e['name'].strip()) <= 80:
        raise ValueError('Назва вправи має містити від 1 до 80 символів.')
    sets = e.get('sets', [])
    if e['type'] == STRENGTH_TYPE:
        if not 1 <= len(sets) <= 100:
            raise ValueError('Додай від 1 до 100 підходів.')
        for s in sets:
            if not math.isfinite(s['weight']) or not 0 <= s['weight'] <= 1000 or not isinstance(s['reps'], int) or not 1 <= s['reps'] <= 1000:
                raise ValueError('Вага: 0–1000 кг; повторення: 1–1000.')
    elif e['type'] != CARDIO_TYPE:
        raise ValueError('Невідомий тип вправи.')
    with connection() as c:
        if not c.execute('SELECT 1 FROM trainings WHERE training_id=? AND date_end IS NULL', (training_id,)).fetchone():
            return False
        c.execute('''INSERT OR IGNORE INTO training_exercises
          (training_id,name,type,sets,time_minutes,distance_meters,speed_kmh,details,source_key)
          VALUES (?,?,?,?,?,?,?,?,?)''', (training_id,e['name'].strip(),e['type'],json.dumps(sets),e.get('time_minutes'),e.get('distance_meters'),e.get('speed_kmh'),e.get('details',''),e.get('source_key')))
    return True

def get_training_exercises(training_id):
    with connection() as c:
        rows = c.execute('SELECT * FROM training_exercises WHERE training_id=? ORDER BY exercise_id', (training_id,)).fetchall()
    result = []
    for row in rows:
        e = dict(row)
        e['sets'] = json.loads(e['sets'])
        e['is_cardio'] = e['type'] == CARDIO_TYPE
        result.append(e)
    return result

def delete_exercise_record(user_id, exercise_id):
    with connection() as c:
        return bool(c.execute('DELETE FROM training_exercises WHERE exercise_id=? AND training_id IN (SELECT training_id FROM trainings WHERE user_id=?)', (exercise_id,user_id)).rowcount)

def get_custom_exercises(user_id):
    result = {'strength': [], 'cardio': []}
    with connection() as c:
        for r in c.execute('SELECT name,type FROM custom_exercises WHERE user_id=? ORDER BY name', (user_id,)):
            result[r['type']].append(r['name'])
    return result

def get_hidden_defaults(user_id):
    result = {'strength': set(), 'cardio': set()}
    with connection() as c:
        for r in c.execute('SELECT name,type FROM user_hidden_defaults WHERE user_id=?', (user_id,)):
            result[r['type']].add(r['name'])
    return result

def get_visible_exercise_lists(user_id):
    hidden, custom = get_hidden_defaults(user_id), get_custom_exercises(user_id)
    return {kind: list(dict.fromkeys([n for n in defaults if n not in hidden[kind]] + custom[kind])) for kind,defaults in [('strength',DEFAULT_STRENGTH_EXERCISES),('cardio',DEFAULT_CARDIO_EXERCISES)]}

def add_custom_exercise(user_id, name, type_):
    if not 1 <= len(name.strip()) <= 80 or type_ not in ('strength','cardio'):
        return False
    with connection() as c:
        c.execute('INSERT OR IGNORE INTO custom_exercises VALUES (?,?,?)', (user_id,name.strip(),type_))
    return True

def remove_exercise_from_user_catalog(user_id, name, exercise_type):
    if name not in get_visible_exercise_lists(user_id)[exercise_type]:
        return False
    with connection() as c:
        c.execute('DELETE FROM custom_exercises WHERE user_id=? AND name=? AND type=?', (user_id,name,exercise_type))
        c.execute('INSERT OR IGNORE INTO user_hidden_defaults VALUES (?,?,?)', (user_id,name,exercise_type))
    return True

def save_measurement(user_id, measurements, source_key=None):
    with connection() as c:
        c.execute('INSERT OR IGNORE INTO user_measurements(user_id,measurement_date,measurements,source_key) VALUES (?,?,?,?)', (user_id,datetime.now().isoformat(),measurements,source_key))
    return True

def get_measurements_history(user_id, limit=10000):
    with connection() as c:
        rows = c.execute('SELECT * FROM user_measurements WHERE user_id=? ORDER BY measurement_date DESC,id DESC LIMIT ?', (user_id,limit)).fetchall()
    return [{'id':r['id'], 'date':datetime.fromisoformat(r['measurement_date']).strftime('%d.%m.%Y %H:%M'), 'measurements':r['measurements']} for r in rows]

def delete_all_user_data(user_id):
    with connection() as c:
        c.execute('DELETE FROM settings WHERE key=?',(f'coach:{user_id}',))
        for table in ('trainings','custom_exercises','user_hidden_defaults','user_measurements'):
            c.execute(f'DELETE FROM {table} WHERE user_id=?', (user_id,))
    return True
