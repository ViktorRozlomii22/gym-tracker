"""Keep portable user data beside the executable, never in its extraction folder."""
import os
import sys
from pathlib import Path

APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get('NEXTSET_DATA_DIR', str(APP_DIR / 'data'))).resolve()
RESOURCE_DIR = Path(__file__).resolve().parent
