"""Guard package boundaries, portable resources and secure transport wiring."""
import ast
import os
from pathlib import Path
import ssl
import subprocess
import sys
import unittest
import re
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
LEGACY={'database','database_sqlite','paths','programs','coach_rag','training_tools','training_cycle','runtime','diary','friendly_ui','method_browser','ai_jobs','exercise_catalog','local_ai'}

class Architecture(unittest.TestCase):
    def test_public_commands_and_legacy_backup_directory_remain_stable(self):
        from nextset.telegram.commands import BOT_COMMANDS
        from nextset.storage import backups
        self.assertTrue(all(re.fullmatch(r'[a-z0-9_]{1,32}',name) for name,_ in BOT_COMMANDS))
        self.assertEqual(len({name for name,_ in BOT_COMMANDS}),len(BOT_COMMANDS))
        self.assertIn('programs',{name for name,_ in BOT_COMMANDS})
        self.assertEqual(backups.folder().name,'backups')

    def test_transient_windows_file_lock_has_bounded_retry(self):
        from unittest.mock import Mock
        from nextset.platform.files import atomic_replace
        source=SimpleNamespace(replace=Mock(side_effect=[PermissionError(),None]))
        with patch('nextset.platform.files.os.name','nt'),patch('nextset.platform.files.time.sleep'):
            atomic_replace(source,'target')
        self.assertEqual(source.replace.call_count,2)
        source.replace.side_effect=PermissionError()
        with patch('nextset.platform.files.os.name','nt'),patch('nextset.platform.files.time.sleep'):
            with self.assertRaises(PermissionError):atomic_replace(source,'target')
        self.assertEqual(source.replace.call_count,9)
    def test_no_flat_application_modules_or_ambiguous_internal_imports(self):
        self.assertEqual({p.name for p in ROOT.glob('*.py')},{'launcher.py'})
        for file in (ROOT/'nextset').rglob('*.py'):
            tree=ast.parse(file.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                names=[alias.name for alias in node.names] if isinstance(node,ast.Import) else [node.module] if isinstance(node,ast.ImportFrom) else []
                self.assertFalse(set(names)&LEGACY,(file,names))

    def test_catalog_and_core_do_not_load_telegram_or_ai_backend(self):
        code='from nextset.knowledge.catalog import references; from nextset.core.loads import round_down; import sys; assert len(references())==10; assert round_down(43,2.5)==42.5; assert "telegram" not in sys.modules; assert "nextset.ai.coach" not in sys.modules'
        result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_resources_resolve_from_package_not_working_directory(self):
        from nextset.platform.paths import RESOURCE_DIR
        self.assertEqual(RESOURCE_DIR,ROOT)
        self.assertTrue((RESOURCE_DIR/'knowledge/programs.json').is_file())
        self.assertTrue((RESOURCE_DIR/'windows_http.ps1').is_file())

class Transport(unittest.IsolatedAsyncioTestCase):
    async def test_both_telegram_transports_keep_certificate_validation(self):
        from telegram.request import HTTPXRequest
        from nextset.telegram.runtime import build_app
        with patch.dict(os.environ):
            os.environ.pop('SSLKEYLOGFILE',None)
            with patch('telegram.request.HTTPXRequest',wraps=HTTPXRequest) as factory:
                app=build_app('123456:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA','test')
                calls=[call for call in factory.call_args_list if 'httpx_kwargs' in call.kwargs]
                self.assertEqual(len(calls),2)
                for call in calls:
                    context=call.kwargs['httpx_kwargs']['verify']
                    self.assertIsInstance(context,ssl.SSLContext)
                    self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)
                    self.assertTrue(context.check_hostname)
                await app.bot.request.shutdown()
                await app.bot._request[0].shutdown()
