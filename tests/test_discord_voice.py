# SPDX-License-Identifier: MIT
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('discord_installer', ROOT / 'scripts/install-noctalia.py')
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)


class DiscordVoiceTests(unittest.TestCase):
    def test_complete_plugin_installation_and_restore(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files = n.files_for_user(root / 'config', root / 'state', root / 'bin', root / 'data')
            plugin = n.ASSETS / 'plugins/discord-voice'
            pairs = [(src, dst) for src, dst in files.items() if src.is_relative_to(plugin)]
            self.assertEqual({src.relative_to(plugin).as_posix() for src, _ in pairs}, {
                'plugin.toml', 'bar.luau', 'panel.luau', 'service.luau', 'discord_bridge.py',
                'README.md', 'ORIGIN.md', 'thumbnail.webp', 'translations/en.json'})
            previous = root / 'data/noctalia/plugins/discord-voice/bar.luau'
            previous.parent.mkdir(parents=True)
            previous.write_text('previous plugin')
            n.snapshot(root / 'backup', [dst for _, dst in pairs])
            for src, dst in pairs:
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.suffix == '.webp':
                    shutil.copyfile(src, dst)
                else:
                    dst.write_text(n.render(src.read_text(), root / 'config', root / 'bin', 'alice', 1.25))
            installed = tomllib.loads((previous.parent / 'plugin.toml').read_text())
            executable = next(s for s in installed['setting'] if s['key'] == 'discord_binary')
            self.assertEqual(executable['default'], str(root / 'bin/niri-open-discord'))
            self.assertEqual((previous.parent / 'thumbnail.webp').read_bytes(), (plugin / 'thumbnail.webp').read_bytes())
            n.restore_files(root / 'backup', [dst for _, dst in pairs])
            self.assertEqual(previous.read_text(), 'previous plugin')
            self.assertFalse((previous.parent / 'plugin.toml').exists())

    @unittest.skipUnless(shutil.which('luajit'), 'LuaJIT is needed for the native widget regression')
    def test_native_glyph_during_voice_changes(self):
        subprocess.run(['luajit', str(ROOT / 'tests/discord_bar.lua'),
                        str(n.ASSETS / 'plugins/discord-voice/bar.luau')], check=True, capture_output=True)
