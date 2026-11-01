# SPDX-License-Identifier: MIT
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('noctalia_installer', ROOT / 'scripts/install-noctalia.py')
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)


class NoctaliaInstallerTests(unittest.TestCase):
    def test_backup_restores_contents_modes_and_absent_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old, new = root / 'old', root / 'new'
            old.write_text('original'); old.chmod(0o600)
            n.snapshot(root / 'backup', [old, new])
            old.write_text('changed'); old.chmod(0o644); new.write_text('created')
            n.restore_files(root / 'backup', [old, new])
            self.assertEqual(old.read_text(), 'original')
            self.assertEqual(old.stat().st_mode & 0o777, 0o600)
            self.assertFalse(new.exists())

    def test_restore_validates_entire_manifest_before_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); victim = root / 'victim'; victim.write_text('keep')
            backup = root / 'backup'; backup.mkdir()
            (backup / 'manifest.json').write_text(json.dumps([
                {'path': str(victim), 'exists': False, 'copy': '0'},
                {'path': '/unexpected', 'exists': False, 'copy': '1'}]))
            with self.assertRaises(RuntimeError):
                n.restore_files(backup, [victim])
            self.assertEqual(victim.read_text(), 'keep')

    def test_restore_rejects_backup_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); victim = root / 'victim'; victim.write_text('keep')
            (root / 'manifest.json').write_text(json.dumps([
                {'path': str(victim), 'exists': True, 'copy': '../secret'}]))
            with self.assertRaises(RuntimeError): n.restore_files(root, [victim])
            self.assertEqual(victim.read_text(), 'keep')

    def test_snapshot_rejects_symlink_ancestors(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); target = root / 'target'; target.mkdir()
            (target / 'config').write_text('keep'); (root / 'linked').symlink_to(target)
            with self.assertRaises(RuntimeError):
                n.snapshot(root / 'backup', [root / 'linked/config'])

    def test_render_handles_spaces_quotes_and_different_home(self):
        result = n.render('path="@CONFIG@/wall"\nuser="@USER@"\nscale=@SCALE@\n',
                          Path('/home/alice/a "quote"'), Path('/home/alice/bin'), 'alice', 1.5)
        parsed = n.tomllib.loads(result)
        self.assertEqual(parsed['path'], '/home/alice/a "quote"/wall')
        self.assertEqual(parsed['scale'], 1.5)

    def test_greetd_merge_preserves_autologin_and_vt(self):
        source = '# keep\n[terminal]\nvt = 7\nswitch = false\n[default_session] # existing greeter\nuser="greeter"\ncommand="old"\n[initial_session]\nuser="alice"\ncommand="niri-session"\n'
        result = n.set_toml(source, 'default_session', {'command': 'new', 'user': 'greeter'})
        parsed = n.tomllib.loads(result)
        self.assertEqual(parsed['terminal'], {'vt': 7, 'switch': False})
        self.assertEqual(parsed['initial_session'], {'user': 'alice', 'command': 'niri-session'})
        self.assertEqual(parsed['default_session'], {'command': 'new', 'user': 'greeter'})
        self.assertIn('# keep', result)

    def test_download_checksum_mismatch_writes_no_wallpaper(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / 'wall'
            with patch.object(n.urllib.request, 'urlopen', return_value=io.BytesIO(b'changed upstream')):
                with self.assertRaisesRegex(RuntimeError, 'сумма'): n.wallpaper(dest)
            self.assertFalse(dest.exists())

    def test_custom_wallpaper_does_not_access_network_and_rejects_text(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / 'image'; source.write_bytes(b'\xff\xd8\xffimage')
            with patch.object(n.urllib.request, 'urlopen', side_effect=AssertionError('network')):
                n.wallpaper(root / 'dest', source)
                self.assertEqual((root / 'dest').read_bytes(), source.read_bytes())
                source.write_text('not an image')
                with self.assertRaisesRegex(RuntimeError, 'JPEG'): n.wallpaper(root / 'dest', source)

    def test_dry_run_creates_nothing_and_never_elevates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            env = {'HOME': temp, 'XDG_CONFIG_HOME': str(root / 'config'), 'XDG_STATE_HOME': str(root / 'state'),
                   'XDG_DATA_HOME': str(root / 'data')}
            with patch.dict(os.environ, env), patch.object(n.os, 'geteuid', return_value=1000), \
                 patch('sys.argv', ['install-noctalia.py', '--dry-run']), \
                 patch.object(n, 'elevated', side_effect=AssertionError('authorization')), \
                 contextlib.redirect_stdout(io.StringIO()):
                n.main()
            self.assertEqual(list(root.iterdir()), [])

    def test_staged_includes_and_profile_do_not_depend_on_old_config(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); image = root / 'image'; image.write_bytes(b'\xff\xd8\xffimage')
            stage = root / 'stage'; stage.mkdir()
            n.stage_files(stage, root / 'config', root / 'bin', 'alice', 1.5, image)
            self.assertIn(str(stage / 'niri/basicsettings.kdl'), (stage / 'niri/config.kdl').read_text())
            self.assertNotIn('/home/rodip', (stage / 'niri/keybinds.kdl').read_text())
            conf = n.tomllib.loads((stage / 'greeter.toml').read_text())
            self.assertEqual(conf['user']['default'], 'alice')
            self.assertEqual(conf['output']['scale'], 1.5)

    def test_failed_user_apply_restores_previous_config(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); config = root / 'config'; state = root / 'state'; binary = root / 'bin'
            existing = config / 'noctalia/config.toml'; existing.parent.mkdir(parents=True)
            existing.write_text('original')
            image = root / 'image'; image.write_bytes(b'\xff\xd8\xffimage')
            with patch.object(n, 'user_paths', return_value=(config, state, binary, root / 'data')), \
                 patch.object(n.os, 'geteuid', return_value=1000), \
                 patch('sys.argv', ['script', '--desktop-only', '--skip-packages', '--wallpaper', str(image)]), \
                 patch.object(n, 'validate'), patch.object(n, 'run', side_effect=RuntimeError('daemon failed')), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, 'daemon failed'): n.main()
            self.assertEqual(existing.read_text(), 'original')
            self.assertFalse((config / 'niri/config.kdl').exists())
            self.assertFalse((binary / 'niri-show-desktop').exists())

    def test_system_failure_restores_files_before_package_service_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); managed = root / 'greetd.toml'; managed.write_text('original')
            backup = root / 'backups/run'
            n.snapshot(backup, [managed]); (backup / 'service.json').write_text('{"previous":"plasmalogin.service"}')
            managed.write_text('changed')
            with patch.object(n, 'SYSTEM_BACKUPS', root / 'backups'), \
                 patch.object(n, 'SYSTEM_PATHS', [managed]), patch.object(n, 'run') as run, \
                 patch.object(n.subprocess, 'run') as subprocess_run, \
                 patch.object(n.shutil, 'which', return_value=None), contextlib.redirect_stdout(io.StringIO()):
                n.system_restore(backup)
            self.assertEqual(managed.read_text(), 'original')
            run.assert_any_call(['systemctl', 'enable', '--force', 'plasmalogin.service'])
            self.assertFalse(any('--now' in str(c) for c in run.call_args_list))
            subprocess_run.assert_called_once()

    def test_late_system_failure_rolls_back_configuration_and_boot_manager(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); stage = root / 'stage'; stage.mkdir()
            image = root / 'image'; image.write_bytes(b'\xff\xd8\xffimage')
            n.stage_files(stage, root / 'config', root / 'bin', 'alice', 1.25, image)
            paths = [root / name for name in ('greetd/config.toml', 'state/greeter.toml',
                     'state/sync.toml', 'wallpaper', 'repo', 'key')]
            paths[0].parent.mkdir(); paths[0].write_text('[default_session]\nuser="greetd"\ncommand="old"\n')
            original = paths[0].read_text()
            alias = root / 'display-manager.service'; alias.symlink_to('/usr/lib/systemd/system/plasmalogin.service')
            calls = []
            def execute(command, **kwargs):
                calls.append(command)
                if command == ['systemctl', 'enable', '--force', 'greetd.service']:
                    raise RuntimeError('switch failed')
                return 'Niri\nPlasma' if command == ['noctalia-greeter', 'sessions'] else ''
            with patch.object(n, 'fedora44'), patch.object(n, 'SYSTEM_PATHS', paths), \
                 patch.object(n, 'SYSTEM_BACKUPS', root / 'backups'), patch.object(n, 'DISPLAY_ALIAS', alias), \
                 patch.object(n.pwd, 'getpwnam', return_value=SimpleNamespace(pw_uid=1000, pw_gid=1000)), \
                 patch.object(n.os, 'chown'), patch.object(n.shutil, 'which', return_value='/usr/bin/tool'), \
                 patch.object(n, 'run', side_effect=execute), patch.object(n.subprocess, 'run'), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, 'switch failed'):
                    n.system_install(stage, 'alice', 1.25, True)
            self.assertEqual(paths[0].read_text(), original)
            self.assertFalse(paths[1].exists())
            self.assertFalse(paths[3].exists())
            self.assertIn(['systemctl', 'enable', '--force', 'plasmalogin.service'], calls)
            self.assertFalse(any('--now' in command for command in calls))


if __name__ == '__main__':
    unittest.main()
