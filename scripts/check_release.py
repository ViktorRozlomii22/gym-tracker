"""Fail before publishing credentials or local data. Report paths, never secrets."""
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
TOKEN=re.compile(rb'\b[0-9]{8,12}:[A-Za-z0-9_-]{30,}\b')
BLOCKED={'.env','nextset.sqlite3','config.json','run.log','error.log','bot.pid'}
SKIP={'.git','.packages','.venv','__pycache__','data','build','dist','release','.mpl'}

def check(paths):
    problems=[]
    for path in paths:
        rel=path.relative_to(ROOT)
        if any(part in {'data','.packages','.venv'} for part in rel.parts) or path.name in BLOCKED or path.suffix in {'.sqlite3','.db','.log','.pid'}:
            problems.append(f'Private/generated file: {rel}')
        if path.is_file() and TOKEN.search(path.read_bytes()):
            problems.append(f'Possible Telegram token: {rel}')
    return problems

def main():
    paths=[p for p in ROOT.rglob('*') if p.is_file() and not any(part in SKIP for part in p.relative_to(ROOT).parts)]
    result=check(paths)
    # Check tracked files too, including anything mistakenly added despite .gitignore.
    if (ROOT/'.git').exists():
        tracked=subprocess.run(['git','ls-files','-z'],cwd=ROOT,capture_output=True,check=True).stdout.decode().split('\0')
        result+=check([ROOT/p for p in tracked if p and (ROOT/p).is_file()])
    if result:
        raise SystemExit('\n'.join(sorted(set(result))))
    print(f'Release scan passed ({len(paths)} source files).')

if __name__=='__main__':
    main()
