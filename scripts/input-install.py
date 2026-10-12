#!/usr/bin/python3
# SPDX-License-Identifier: MIT
"""Set up seat-scoped access for the user Meta + wheel service."""
import argparse, datetime, json, os, shutil, subprocess
from pathlib import Path

RULE=Path('/etc/udev/rules.d/70-rodip-glass-input.rules')
MODULE=Path('/etc/modules-load.d/rodip-glass-uinput.conf')
BACKUPS=Path('/var/lib/rodip-glass/input-backups')
RULE_TEXT='''# Access follows the active local graphical session through systemd-logind.
SUBSYSTEM=="input", KERNEL=="event*", ENV{ID_INPUT_KEYBOARD}=="1", TAG+="uaccess"
SUBSYSTEM=="input", KERNEL=="event*", ENV{ID_INPUT_MOUSE}=="1", TAG+="uaccess"
SUBSYSTEM=="misc", KERNEL=="uinput", TAG+="uaccess"
'''

def refresh():
 subprocess.run(['udevadm','control','--reload-rules'],check=True)
 for subsystem in ['input','misc']:
  subprocess.run(['udevadm','trigger','--action=change','--subsystem-match='+subsystem],check=True)
 subprocess.run(['udevadm','settle'],check=True)

def restore(backup):
 backup=backup.resolve()
 if backup.parent!=BACKUPS:raise RuntimeError('Unexpected input backup path')
 state=json.loads((backup/'previous.json').read_text())
 for i,path in enumerate([RULE,MODULE]):
  if state[str(i)]:shutil.copy2(backup/str(i),path)
  else:path.unlink(missing_ok=True)
 refresh()

def install():
 backup=BACKUPS/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 backup.mkdir(parents=True,mode=0o700)
 state={}
 for i,path in enumerate([RULE,MODULE]):
  if path.is_symlink():raise RuntimeError('Refusing symlink: '+str(path))
  state[str(i)]=path.exists()
  if path.exists():shutil.copy2(path,backup/str(i))
 (backup/'previous.json').write_text(json.dumps(state))
 try:
  for path,value in [(RULE,RULE_TEXT),(MODULE,'uinput\n')]:
   path.parent.mkdir(parents=True,exist_ok=True);path.write_text(value);path.chmod(0o644)
  subprocess.run(['modprobe','uinput'],check=True)
  if shutil.which('restorecon'):subprocess.run(['restorecon',str(RULE),str(MODULE)],check=True)
  refresh()
 except BaseException:
  restore(backup);raise
 return {'backup':str(backup),'rule':str(RULE)}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--restore',type=Path);args=parser.parse_args()
 if os.geteuid()!=0:raise SystemExit('Administrator authentication is required for input access.')
 if args.restore:restore(args.restore)
 else:print(json.dumps(install()))
