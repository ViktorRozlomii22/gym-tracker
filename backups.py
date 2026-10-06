"""Consistent SQLite backups and offline, validated recovery. No token files."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime
import database_sqlite as db
from paths import DATA_DIR

FORMAT=1
MAX_DB=256*1024*1024

def folder():
    return DATA_DIR/'backups'

def list_backups():
    return sorted(folder().glob('nextset-*.zip'),key=lambda x:x.name,reverse=True)

def validate_db(path):
    with closing(sqlite3.connect(f'{Path(path).resolve().as_uri()}?mode=ro',uri=True)) as c:
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise ValueError('Backup database failed its integrity check.')
        tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'settings','trainings','training_exercises','users','user_measurements'}.issubset(tables):
            raise ValueError('This archive is not a NextSet database backup.')

def create_backup():
    if not db.DB_PATH.exists():
        raise ValueError('No database to back up yet.')
    target_folder=folder(); target_folder.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    target=target_folder/f'nextset-{stamp}.zip'
    with tempfile.TemporaryDirectory(prefix='backup-',dir=target_folder) as tmp:
        snapshot=Path(tmp)/'nextset.sqlite3'
        with closing(sqlite3.connect(db.DB_PATH)) as source,closing(sqlite3.connect(snapshot)) as destination:
            source.backup(destination)
        validate_db(snapshot)
        size=snapshot.stat().st_size
        if size>MAX_DB:
            raise ValueError('Database exceeds the supported 256 MB backup limit.')
        raw=snapshot.read_bytes()
        manifest={'format':FORMAT,'created':datetime.now().isoformat(),'bytes':size,
                  'sha256':hashlib.sha256(raw).hexdigest(),'token_included':False}
        temporary=Path(tmp)/'archive.zip'
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('manifest.json',json.dumps(manifest))
            z.writestr('nextset.sqlite3',raw)
        temporary.replace(target)
    # Only generated files in this exact backup folder are retained/pruned.
    for old in list_backups()[14:]:
        if old.parent.resolve()==target_folder.resolve():
            old.unlink()
    return target

def daily_backup():
    today=datetime.now().date().isoformat()
    if db.setting('last_daily_backup')==today:
        return None
    result=create_backup()
    db.set_setting('last_daily_backup',today)
    return result

async def backup_job(context):
    import asyncio
    try:
        await asyncio.to_thread(daily_backup)
    except (OSError,sqlite3.Error,ValueError):
        import logging
        logging.warning('Automatic backup failed. Use /backup to retry.')

def restore_backup(archive):
    """Caller must hold runtime's instance lock. Validate before touching current DB."""
    archive=Path(archive)
    db.DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        if sorted(z.namelist())!=['manifest.json','nextset.sqlite3']:
            raise ValueError('Unexpected backup entries; nothing restored.')
        if z.getinfo('manifest.json').file_size>4096 or z.getinfo('nextset.sqlite3').file_size>MAX_DB:
            raise ValueError('Backup is too large; nothing restored.')
        manifest=json.loads(z.read('manifest.json'))
        raw=z.read('nextset.sqlite3')
    if not isinstance(manifest,dict) or manifest.get('format')!=FORMAT or manifest.get('bytes')!=len(raw) or manifest.get('sha256')!=hashlib.sha256(raw).hexdigest():
        raise ValueError('Backup checksum or format is invalid; nothing restored.')
    with tempfile.TemporaryDirectory(prefix='restore-',dir=db.DB_PATH.parent) as tmp:
        incoming=Path(tmp)/'nextset.sqlite3'; incoming.write_bytes(raw)
        validate_db(incoming)
        if db.DB_PATH.exists():
            create_backup()
        # A running bot is excluded by the instance lock. SQLite sidecars must
        # not be carried over to the restored database.
        for suffix in ('-wal','-shm','-journal'):
            sidecar=Path(str(db.DB_PATH)+suffix)
            if sidecar.exists():
                sidecar.unlink()
        incoming.replace(db.DB_PATH)
    return db.DB_PATH

def restore_console():
    import msvcrt
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    lock=(DATA_DIR/'.running.lock').open('a+b')
    if lock.tell()==0:
        lock.write(b'0'); lock.flush()
    lock.seek(0)
    try:
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    except OSError:
        lock.close()
        raise RuntimeError('Stop NextSet first. Restore never runs while the bot is active.') from None
    try:
        paths=list_backups()
        if not paths:
            raise ValueError('No backups found. Copy a nextset-*.zip archive into data/backups.')
        print('\nRESTORE DATABASE\nYour current database will be backed up first. Your local bot token is preserved.\n')
        for i,path in enumerate(paths,1):
            print(f'{i}. {path.name}')
        choice=input('Backup number (Enter to cancel): ').strip()
        if not choice:
            return
        if not choice.isdigit() or not 1<=int(choice)<=len(paths):
            raise ValueError('Invalid backup number.')
        if input('Type RESTORE to confirm replacing the database: ').strip()!='RESTORE':
            print('Cancelled.'); return
        restore_backup(paths[int(choice)-1])
        print('Restore complete. Close this window and start NextSet normally.')
    finally:
        lock.close()
