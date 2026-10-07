"""Optional local Ollama setup, separate from normal first-run bot setup."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request
import webbrowser
from paths import DATA_DIR

MODEL = 'qwen3:4b-instruct-2507-q4_K_M'

def ollama_executable():
    found=shutil.which('ollama')
    if found:
        return found
    candidate=Path(os.environ.get('LOCALAPPDATA',''))/'Programs'/'Ollama'/'ollama.exe'
    return str(candidate) if candidate.is_file() else None

def available_models():
    try:
        with urllib.request.urlopen('http://127.0.0.1:11434/api/tags',timeout=2) as response:
            return [m['name'] for m in json.load(response).get('models',[])]
    except (OSError,ValueError,KeyError):
        return None

def ensure_server(executable):
    models=available_models()
    if models is not None:
        return models
    # No token is forwarded to the independent AI process.
    env={k:v for k,v in os.environ.items() if k not in ('BOT_TOKEN','GH_TOKEN','GITHUB_TOKEN')}
    subprocess.Popen([executable,'serve'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
    for _ in range(15):
        time.sleep(1)
        models=available_models()
        if models is not None:
            return models
    raise RuntimeError('Ollama did not start. Open Ollama manually and try again.')

def setup():
    from dotenv import set_key
    print('\nOPTIONAL LOCAL AI\nModel: Qwen3 4B Instruct (about 2.5 GB download). No cloud service.\n')
    executable=ollama_executable()
    if not executable:
        print('Install Ollama from the official Windows installer, then run SETUP_AI.cmd again.')
        print('https://ollama.com/download/windows')
        webbrowser.open('https://ollama.com/download/windows')
        return
    models=ensure_server(executable)
    if MODEL not in models:
        if input('Download the model now? [y/N]: ').strip().lower()!='y':
            print('Skipped. Normal bot features are ready without AI.')
            return
        result=subprocess.run([executable,'pull',MODEL],check=False)
        if result.returncode:
            raise RuntimeError('Model download failed. Run SETUP_AI.cmd again to retry.')
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    config=DATA_DIR/'.env'
    config.touch(exist_ok=True)
    set_key(str(config),'NEXTSET_AI','1',quote_mode='never')
    set_key(str(config),'OLLAMA_MODEL',MODEL,quote_mode='never')
    print('Local AI is enabled. Restart NextSet if it is running, then use /ai in Telegram.')

def start_if_enabled():
    if os.getenv('NEXTSET_AI')!='1':
        return
    executable=ollama_executable()
    if not executable:
        print('Optional AI: Ollama is missing. Run SETUP_AI.cmd. Normal logging still works.')
        return
    try:
        models=ensure_server(executable)
        if os.getenv('OLLAMA_MODEL',MODEL) not in models:
            print('Optional AI: model missing. Run SETUP_AI.cmd. Normal logging still works.')
        else:
            print('Local AI service is ready. The model loads only when you use /ai.')
    except RuntimeError as error:
        print(str(error)+' Normal logging still works.')
