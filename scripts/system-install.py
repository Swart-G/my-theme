#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""The only elevated step: install or restore the SDDM theme, without restarting it."""
import argparse,datetime,json,os,shutil,subprocess,tempfile
from pathlib import Path
DEST=Path('/usr/share/sddm/themes/rodip-glass')
CONF=Path('/etc/sddm.conf.d/zz-rodip-glass.conf')
BACKUPS=Path('/var/lib/sddm/rodip-glass-backups')
def restore(backup):
 backup=backup.resolve()
 if backup.parent!=BACKUPS:raise RuntimeError('Unexpected backup path')
 state=json.loads((backup/'previous.json').read_text())
 if state['override']:shutil.copy2(backup/'override.conf',CONF)
 else:CONF.unlink(missing_ok=True)
 if DEST.exists():shutil.rmtree(DEST)
 if state['theme']:shutil.copytree(backup/'theme',DEST)
 if shutil.which('restorecon'):subprocess.run(['restorecon','-RF',str(CONF.parent),str(DEST.parent)],check=True)
 print(json.dumps({'restored':str(backup),'restart_performed':False}))
def install(source):
 allowed={'metadata.desktop','theme.conf','Main.qml','GlassPanel.qml','background.svg','wallpaper.png','wallpaper.jpg','wallpaper.jpeg','wallpaper.webp'}
 names={p.name for p in source.iterdir()}
 if names-allowed or not {'metadata.desktop','theme.conf','Main.qml','GlassPanel.qml'}.issubset(names):raise RuntimeError('Invalid SDDM theme files')
 if any((source/name).is_symlink() or not (source/name).is_file() for name in names):raise RuntimeError('Theme must contain regular files')
 DEST.parent.mkdir(parents=True,exist_ok=True)
 backup=BACKUPS/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 backup.mkdir(parents=True,mode=0o700)
 (backup/'previous.json').write_text(json.dumps({'theme':DEST.exists(),'override':CONF.exists()}))
 if DEST.exists():shutil.copytree(DEST,backup/'theme')
 if CONF.exists():shutil.copy2(CONF,backup/'override.conf')
 staging=Path(tempfile.mkdtemp(prefix='.rodip-glass-',dir=DEST.parent))
 try:
  for name in names:
   target=staging/name;shutil.copyfile(source/name,target);target.chmod(0o644);os.chown(target,0,0)
  staging.chmod(0o755);os.chown(staging,0,0)
  if DEST.exists():shutil.rmtree(DEST)
  staging.rename(DEST)
  CONF.parent.mkdir(parents=True,exist_ok=True)
  temp=CONF.with_suffix('.tmp');temp.write_text('[Theme]\nCurrent=rodip-glass\n');temp.chmod(0o644);os.chown(temp,0,0);temp.replace(CONF)
  if shutil.which('restorecon'):subprocess.run(['restorecon','-RF',str(DEST),str(CONF)],check=True)
 except BaseException:
  if staging.exists():shutil.rmtree(staging)
  restore(backup)
  raise
 print(json.dumps({'theme':str(DEST),'config':str(CONF),'backup':str(backup),'restart_performed':False}))
if __name__=='__main__':
 parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
 group.add_argument('--source',type=Path);group.add_argument('--restore',type=Path);args=parser.parse_args()
 if os.geteuid()!=0:raise SystemExit('Administrator authentication is required for SDDM.')
 if args.restore:restore(args.restore)
 else:install(args.source)
