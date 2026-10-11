# SPDX-License-Identifier: MIT
import importlib.util,json,sys,tempfile,unittest
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
   with patch.object(system,'DEST',dest),patch.object(system,'CONF',conf),patch.object(system,'BACKUPS',base/'backups'),patch.object(system.os,'chown'),patch.object(system.shutil,'which',return_value=None):
    system.install(source)
    self.assertEqual(conf.read_text(),'[Theme]\nCurrent=rodip-glass\n');self.assertEqual((dest/'Main.qml').read_text(),'Main.qml')
    self.assertFalse((dest/'old').exists())
    backup=next((base/'backups').iterdir());system.restore(backup)
    self.assertEqual(conf.read_text(),'[Theme]\nCurrent=previous\n');self.assertEqual((dest/'old').read_text(),'old theme')
 def test_sddm_rejects_unexpected_files_before_writing(self):
  with tempfile.TemporaryDirectory() as temp:
   source=Path(temp)
   for name in ['Main.qml','GlassPanel.qml','metadata.desktop','theme.conf','secret']:(source/name).write_text('data')
   with self.assertRaises(RuntimeError):system.install(source)
 def test_bundle_does_not_require_machine_paths_or_native_binary(self):
  for path in ROOT.rglob('*'):
   if not path.is_file() or '.git' in path.parts or path.relative_to(ROOT).parts[0]=='tests':continue
   self.assertNotEqual(path.suffix,'.so',str(path))
   if path.suffix in ['.qml','.js','.py','.xml','.conf']:
    text=path.read_text();self.assertNotIn('/home/rodip',text,str(path));self.assertNotIn('Ryzen 7 5700X',text,str(path))
  self.assertTrue((ROOT/'theme/LICENSE').exists());self.assertTrue((ROOT/'plasmoids/KdeControlStation/LICENSE').exists())
if __name__=='__main__':unittest.main()
