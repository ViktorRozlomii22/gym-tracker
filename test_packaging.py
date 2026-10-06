import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import launcher

class PackagingTests(unittest.TestCase):
    def test_config_is_private_and_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'data'/'.env'
            with self.assertRaises(ValueError):
                launcher.save_token('not-a-token',path)
            self.assertFalse(path.exists())
            launcher.save_token('123456:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',path)
            self.assertTrue(path.read_text().startswith('BOT_TOKEN='))
            self.assertFalse(path.with_suffix('.tmp').exists())

    def test_setup_skips_existing_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)
            launcher.save_token('123456:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',path/'.env')
            with patch.object(launcher,'DATA_DIR',path),patch('getpass.getpass',side_effect=AssertionError('should not prompt')):
                launcher.configure()

    def test_token_update_preserves_ai_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'.env'
            path.write_text('NEXTSET_AI=1\nOLLAMA_MODEL=qwen3:1.7b\nBOT_TOKEN=old\n')
            launcher.save_token('123456:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',path)
            lines=path.read_text().splitlines()
            self.assertIn('NEXTSET_AI=1',lines)
            self.assertIn('OLLAMA_MODEL=qwen3:1.7b',lines)
            self.assertEqual(sum(x.startswith('BOT_TOKEN=') for x in lines),1)

    def test_portable_path_does_not_use_extraction_folder(self):
        root=Path(__file__).parent
        with tempfile.TemporaryDirectory() as tmp:
            # Windows CI can return an 8.3 TEMP path (RUNNER~1); compare canonical paths.
            script="import sys; from pathlib import Path; sys.frozen=True; sys.executable=sys.argv[1]; import paths; expected=(Path(sys.argv[1]).parent/'data').resolve(); assert paths.DATA_DIR == expected, (paths.DATA_DIR, expected); print('ok')"
            env=dict(os.environ,PYTHONPATH=str(root))
            env.pop('NEXTSET_DATA_DIR',None)
            result=subprocess.run([sys.executable,'-c',script,str(Path(tmp)/'NextSet.exe')],env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':
    unittest.main()
