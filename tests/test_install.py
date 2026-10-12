# SPDX-License-Identifier: MIT
import importlib.util,json,os,re,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import install
spec=importlib.util.spec_from_file_location('system_install',ROOT/'scripts/system-install.py')
system=importlib.util.module_from_spec(spec);spec.loader.exec_module(system)
class InstallationTests(unittest.TestCase):
 def test_new_dependencies_refresh_qdbus_location(self):
  from types import SimpleNamespace
  qt=SimpleNamespace(qVersion=lambda:'6.11.2')
  probe={'version':'plasmashell 6.7.5','screens':[]}
  with patch.object(install.Path,'read_text',return_value='ID=fedora\n'),patch.object(install.subprocess,'run',return_value=SimpleNamespace(returncode=1)),patch.object(install,'elevated') as elevate,patch.object(install.shutil,'which',return_value='/usr/bin/tool'),patch.object(install.k,'probe',return_value=probe),patch.object(install.k,'find_qdbus',return_value='/new/qt6/qdbus'),patch.object(install.k,'QDBUS',''),patch.dict(sys.modules,{'PySide6.QtCore':qt}):
   result=install.check(dependencies=True)
   self.assertTrue(result['ready']);self.assertEqual(install.k.QDBUS,'/new/qt6/qdbus')
   self.assertEqual(elevate.call_args.args[0][:3],['dnf','install','-y'])
 def test_backup_restores_directories_config_and_previously_absent_paths(self):
  with tempfile.TemporaryDirectory() as temp:
   base=Path(temp);cfg=base/'config';cfg.write_text('original\n');tree=base/'tree';tree.mkdir();(tree/'original').write_text('data')
   absent=base/'new';paths=[cfg,tree,absent]
   install.snapshot(base/'backup',paths)
   cfg.write_text('changed');(tree/'original').unlink();(tree/'extra').write_text('extra');absent.mkdir();(absent/'new').write_text('new')
   install.restore_files(base/'backup',paths)
   self.assertEqual(cfg.read_text(),'original\n');self.assertEqual((tree/'original').read_text(),'data');self.assertFalse((tree/'extra').exists());self.assertFalse(absent.exists())
 def test_restore_rejects_manifest_path_outside_managed_set(self):
  with tempfile.TemporaryDirectory() as temp:
   base=Path(temp);backup=base/'backup';backup.mkdir();victim=base/'victim';victim.write_text('safe')
   (backup/'manifest.json').write_text(json.dumps([{'path':str(victim),'exists':False}]))
   with self.assertRaises(RuntimeError):install.restore_files(backup,[base/'allowed'])
   self.assertEqual(victim.read_text(),'safe')
 def test_snapshot_refuses_symlink(self):
  with tempfile.TemporaryDirectory() as temp:
   base=Path(temp);target=base/'target';target.write_text('safe');link=base/'link';link.symlink_to(target)
   with self.assertRaises(RuntimeError):install.snapshot(base/'backup',[link])
 def test_sddm_install_and_restore_preserve_previous_theme(self):
  with tempfile.TemporaryDirectory() as temp:
   base=Path(temp);source=base/'source';source.mkdir()
   for name in ['Main.qml','GlassPanel.qml','metadata.desktop','theme.conf','background.svg']:(source/name).write_text(name)
   dest=base/'themes/rodip-glass';dest.mkdir(parents=True);(dest/'old').write_text('old theme')
   conf=base/'conf.d/zz-rodip-glass.conf';conf.parent.mkdir();conf.write_text('[Theme]\nCurrent=previous\n')
   main=base/'sddm.conf';original='# Preserve me\n[Autologin]\nUser=alice\n[Theme]\nCurrent=other\nThemeDir=/other/themes\n';main.write_text(original)
   with patch.object(system,'DEST',dest),patch.object(system,'CONF',conf),patch.object(system,'MAIN_CONF',main),patch.object(system,'BACKUPS',base/'backups'),patch.object(system.os,'chown'),patch.object(system.shutil,'which',return_value=None):
    system.install(source)
    self.assertEqual(conf.read_text(),'[Theme]\nCurrent=rodip-glass\nThemeDir='+str(dest.parent)+'\n');self.assertEqual((dest/'Main.qml').read_text(),'Main.qml')
    self.assertIn('Current=rodip-glass',main.read_text());self.assertIn('ThemeDir='+str(dest.parent),main.read_text())
    self.assertIn('# Preserve me\n[Autologin]\nUser=alice',main.read_text())
    self.assertFalse((dest/'old').exists())
    backup=next((base/'backups').iterdir());system.restore(backup)
    self.assertEqual(conf.read_text(),'[Theme]\nCurrent=previous\n');self.assertEqual((dest/'old').read_text(),'old theme')
    self.assertEqual(main.read_text(),original)
 def test_screen_failure_reports_completed_locker_and_failed_login(self):
  with tempfile.TemporaryDirectory() as temp:
   base=Path(temp);backup=base/'backup';backup.mkdir();package=base/'package'
   (package/'contents/lockscreen').mkdir(parents=True);(package/'contents/lockscreen/LockScreen.qml').write_text('native')
   with patch.object(install,'STATE',base),patch.object(install.k,'CONFIG',base/'config'),patch.object(install.lockscreen,'build',return_value=package),patch.object(install,'wallpaper',return_value=None),patch.object(install,'prepare_sddm',return_value=base/'source'),patch.object(install,'elevated',side_effect=RuntimeError('authorization failed')):
    with self.assertRaisesRegex(RuntimeError,'authorization failed'):install.install_screens(backup,False)
   screens=json.loads((base/'report.json').read_text())['screens']
   self.assertTrue(screens['lockscreen']['installed']);self.assertFalse(screens['login']['installed'])
   self.assertEqual(screens['login']['reason'],'system-install-failed')
 def test_fish_palette_survives_later_config_and_applies_outside_konsole(self):
  if not shutil.which('fish'):self.skipTest('fish is not installed')
  spec=importlib.util.spec_from_file_location('finish_style',ROOT/'scripts/finish-style.py')
  style=importlib.util.module_from_spec(spec);spec.loader.exec_module(style)
  with tempfile.TemporaryDirectory() as temp:
   base=Path(temp);config=base/'fish';(config/'conf.d').mkdir(parents=True)
   (config/'conf.d/rodip-glass.fish').write_text(style.FISH_CONFIG)
   (config/'config.fish').write_text('set -g fish_color_autosuggestion brblack\n')
   env=os.environ.copy();env.update(XDG_CONFIG_HOME=temp,XDG_DATA_HOME=str(base/'data'),XDG_STATE_HOME=str(base/'state'));env.pop('KONSOLE_VERSION',None)
   result=subprocess.run(['fish','-i','-c','emit fish_prompt; printf "palette=%s\\n" $fish_color_autosuggestion $fish_pager_color_description; emit fish_prompt; printf "palette=%s\\n" $fish_color_autosuggestion'],env=env,capture_output=True,text=True,check=True)
   self.assertEqual(re.findall(r'palette=([a-z0-9]+)',result.stdout),['b5bfb0']*3)
 def test_sddm_rejects_unexpected_files_before_writing(self):
  with tempfile.TemporaryDirectory() as temp:
   source=Path(temp)
   for name in ['Main.qml','GlassPanel.qml','metadata.desktop','theme.conf','secret']:(source/name).write_text('data')
   with self.assertRaises(RuntimeError):system.install(source)
 def test_wallpaper_decoration_works_without_installed_bart_and_preserves_source(self):
  spec=importlib.util.spec_from_file_location('finish_style',ROOT/'scripts/finish-style.py')
  style=importlib.util.module_from_spec(spec);spec.loader.exec_module(style)
  with tempfile.TemporaryDirectory() as temp:
   base=Path(temp);data=base/'data';state=base/'state';state.mkdir()
   import shutil
   source=data/'rodip-style/decoration-source'
   shutil.copytree(ROOT/'terminal/decoration-source',source)
   original=(source/'decoration.svg').read_bytes()
   with patch.object(style,'DATA',data),patch.object(style,'STATE',state),patch.object(style,'accent',return_value='#123456'),patch.object(style,'key') as key,patch.object(style,'run'):
    style.sync()
    self.assertEqual((source/'decoration.svg').read_bytes(),original)
    generated=data/'aurorae/themes/Bart-Wallpaper-A'
    self.assertIn('#123456',(generated/'decoration.svg').read_text())
    self.assertNotIn('#d95a3c',(generated/'decoration.svg').read_text())
    self.assertTrue((generated/'Bart-Wallpaper-Arc').exists())
    style.sync();self.assertEqual(key.call_count,1)
    with patch.object(style,'accent',return_value='#654321'):style.sync()
    self.assertTrue((data/'aurorae/themes/Bart-Wallpaper-B/decoration.svg').exists())
 def test_accent_helper_finds_fedora_qdbus_outside_path(self):
  spec=importlib.util.spec_from_file_location('finish_style',ROOT/'scripts/finish-style.py')
  style=importlib.util.module_from_spec(spec);spec.loader.exec_module(style)
  with patch.object(style.Path,'is_file',side_effect=lambda:True),patch.object(style.shutil,'which',return_value=None),patch.object(style,'run',return_value='ok') as run:
   self.assertEqual(style.dbus('org.kde.KWin','/KWin','reconfigure'),'ok')
   self.assertEqual(run.call_args.args[0],'/usr/lib64/qt6/bin/qdbus')
  with patch.object(style.Path,'is_file',return_value=False),patch.object(style.shutil,'which',return_value=None):
   with self.assertRaisesRegex(RuntimeError,'qt6-qttools'):style.dbus('org.kde.KWin')
 def test_locker_reuses_native_authentication_and_shell_fallback(self):
  import lockscreen
  with tempfile.TemporaryDirectory() as temp:
   base=Path(temp);native=base/'native';native.mkdir()
   for name in ['LockScreen.qml','LockScreenUi.qml','PasswordSync.qml','NoPasswordUnlock.qml','config.xml']:
    (native/name).write_text('authenticator.respond' if name=='LockScreenUi.qml' else name)
   (native/'MainBlock.qml').write_text('SessionManagementScreen {\n\tid: sessionManager\nfunction login() { sessionManager.startLogin() }\n}\n')
   package=lockscreen.build(base/'data',native)
   metadata=json.loads((package/'metadata.json').read_text())
   self.assertEqual(metadata['X-Plasma-FallbackPackage'],'org.kde.plasma.desktop')
   for name in ['LockScreen.qml','LockScreenUi.qml','PasswordSync.qml','NoPasswordUnlock.qml']:
    self.assertEqual((package/'contents/lockscreen'/name).read_bytes(),(native/name).read_bytes())
   main=(package/'contents/lockscreen/MainBlock.qml').read_text()
   self.assertIn('authenticator.respond', (package/'contents/lockscreen/LockScreenUi.qml').read_text())
   self.assertIn('sessionManager.startLogin()',main)
   self.assertIn('data: [Rectangle',main)
   (native/'MainBlock.qml').write_text('unsupported KDE API')
   with self.assertRaises(RuntimeError):lockscreen.build(base/'data',native)
   self.assertEqual((package/'contents/lockscreen/MainBlock.qml').read_text(),main)
 def test_global_theme_has_native_metadata_defaults_and_preview(self):
  package=ROOT/'look-and-feel';metadata=json.loads((package/'metadata.json').read_text())
  self.assertEqual(metadata['KPackageStructure'],'Plasma/LookAndFeel')
  self.assertEqual(metadata['KPlugin']['Id'],'org.rodip.glass.desktop')
  defaults=(package/'contents/defaults').read_text()
  self.assertIn('ShellPackage=org.rodip.glass.shell',defaults)
  self.assertIn('ColorScheme=RodipGlass',defaults)
  self.assertNotIn('[Wallpaper]',defaults)
  self.assertTrue((package/'contents/previews/preview.png').is_file())
 def test_bundle_does_not_require_machine_paths_or_native_binary(self):
  for path in ROOT.rglob('*'):
   if not path.is_file() or '.git' in path.parts or path.relative_to(ROOT).parts[0]=='tests':continue
   self.assertNotEqual(path.suffix,'.so',str(path))
   if path.suffix in ['.qml','.js','.py','.xml','.conf']:
    text=path.read_text();self.assertNotIn('/home/rodip',text,str(path));self.assertNotIn('Ryzen 7 5700X',text,str(path))
  self.assertTrue((ROOT/'theme/LICENSE').exists());self.assertTrue((ROOT/'plasmoids/KdeControlStation/LICENSE').exists())
if __name__=='__main__':unittest.main()
