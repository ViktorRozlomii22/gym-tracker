"""Build an allowlisted, credential-free Windows archive and smoke-test it."""
import hashlib
from importlib import metadata
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def main():
    if sys.platform!='win32':
        raise SystemExit('Build on Windows x64 using Python 3.12.')
    subprocess.run([sys.executable,str(ROOT/'scripts'/'check_release.py')],check=True,cwd=ROOT)
    # No .env or personal data directories are used as PyInstaller input.
    args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onefile','--console',
          '--name','NextSet','--distpath',str(ROOT/'dist'),'--workpath',str(ROOT/'build'/'pyinstaller'),
          '--specpath',str(ROOT/'build'),'--add-data',str(ROOT/'windows_http.ps1')+';.',
          '--add-data',str(ROOT/'knowledge')+';knowledge',
          '--copy-metadata','APScheduler','--copy-metadata','python-telegram-bot',
          '--collect-data','matplotlib','--collect-data','tzdata',str(ROOT/'launcher.py')]
    subprocess.run(args,cwd=ROOT,check=True)
    executable=ROOT/'dist'/'NextSet.exe'
    with tempfile.TemporaryDirectory(prefix='nextset-check-') as temp:
        env=dict(os.environ,NEXTSET_DATA_DIR=temp,MPLCONFIGDIR=str(Path(temp)/'mpl'))
        subprocess.run([str(executable),'--check'],cwd=temp,env=env,check=True,timeout=120)
    release=ROOT/'release'
    release.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='nextset-release-') as tmp:
        stage=Path(tmp)
        for filename in ['QUICKSTART.txt','STOP.cmd','SETUP_AI.cmd','RESTORE.cmd','EVALUATE_AI.cmd','LICENSE']:
            shutil.copy2(ROOT/filename,stage/filename)
        shutil.copy2(executable,stage/'NextSet.exe')
        shutil.copy2(ROOT/'docs'/'PROGRAMS.md',stage/'PROGRAMS.md')
        shutil.copy2(ROOT/'docs'/'TRAINING_GUIDE.md',stage/'TRAINING_GUIDE.md')
        licenses=stage/'THIRD_PARTY_LICENSES'
        licenses.mkdir()
        runtime_names=[line.split('==')[0] for line in (ROOT/'requirements.lock').read_text().splitlines() if '==' in line]
        for package in runtime_names+['pyinstaller']:
            dist=metadata.distribution(package)
            dest=licenses/package
            dest.mkdir(exist_ok=True)
            meta=dist.read_text('METADATA')
            if meta:
                (dest/'METADATA.txt').write_text(meta,encoding='utf-8')
            for file in dist.files or []:
                if any(label in file.name.lower() for label in ['license','copying','notice']) and file.suffix.lower() not in ('.py','.pyc'):
                    src=Path(dist.locate_file(file))
                    if src.is_file():
                        target=dest/str(file).replace('/','_').replace('\\','_')
                        shutil.copy2(src,target)
        python_license=Path(sys.base_prefix)/'LICENSE.txt'
        if python_license.exists():
            shutil.copy2(python_license,licenses/'PYTHON-LICENSE.txt')
        archive=release/'NextSet-UA-Windows.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for path in sorted(stage.rglob('*')):
                if path.is_file():
                    z.write(path,'NextSet-UA/'+path.relative_to(stage).as_posix())
        digest=hashlib.sha256(archive.read_bytes()).hexdigest()
        archive.with_suffix('.zip.sha256').write_text(digest+'  '+archive.name+'\n',encoding='ascii')
        print(f'Built {archive.name}: {archive.stat().st_size/1024/1024:.1f} MiB; SHA256 {digest}')

if __name__=='__main__':
    main()
