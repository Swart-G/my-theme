#!/usr/bin/env python3
"""Wallpaper-accent Aurorae extension and glass Konsole; never edits Bart."""
import argparse, configparser, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path
HOME=Path.home(); CONFIG=Path(os.environ.get('XDG_CONFIG_HOME',HOME/'.config')); DATA=Path(os.environ.get('XDG_DATA_HOME',HOME/'.local/share')); STATE=Path(os.environ.get('XDG_STATE_HOME',HOME/'.local/state'))/'rodip-style'
FILES=[CONFIG/'kwinrc',CONFIG/'konsolerc',CONFIG/'fish/conf.d/rodip-glass.fish',DATA/'konsole/RodipGlass.profile',DATA/'konsole/RodipGlass.colorscheme',CONFIG/'autostart/rodip-style.desktop']

def run(*args):
 return subprocess.run(args,check=True,text=True,capture_output=True).stdout

def key(file,group,name,value):
 run('kwriteconfig6','--file',str(file),'--group',group,'--key',name,str(value))

def accent():
 p=configparser.ConfigParser(interpolation=None);p.read(CONFIG/'kdeglobals')
 rgb=p.get('General','AccentColor',fallback=p.get('Colors:Selection','BackgroundNormal',fallback='109,121,60'))
 return '#'+''.join(f'{int(v):02x}' for v in rgb.split(',')[:3])

def sync():
 color=accent(); stamp=STATE/'accent.json'
 old=json.loads(stamp.read_text()) if stamp.exists() else {}
 if old.get('color')==color:return
 variant='B' if old.get('variant')=='A' else 'A'; name='Bart-Wallpaper-'+variant
 src=DATA/'aurorae/themes/Bart'
 if not src.exists():src=DATA/'rodip-style/decoration-source'
 dest=DATA/'aurorae/themes'/name
 if dest.exists():shutil.rmtree(dest)
 shutil.copytree(src,dest)
 for f in dest.glob('*.svg'):
  s=f.read_text();s=s.replace('#d95a3c',color).replace('#ff8263',color).replace('#993f2b',color)
  f.write_text(s)
 (dest/'Bartrc').rename(dest/(name+'rc'))
 for f in dest.glob('metadata.*'):
  if f.suffix=='.json':
   obj=json.loads(f.read_text());obj['KPlugin']['Id']=name;obj['KPlugin']['Name']='Bart · Wallpaper accent';f.write_text(json.dumps(obj,indent=2))
  else:f.write_text(f.read_text().replace('Name=Bart','Name='+name).replace('X-KDE-PluginInfo-Name=Bart','X-KDE-PluginInfo-Name='+name))
 key(CONFIG/'kwinrc','org.kde.kdecoration2','theme','__aurorae__svg__'+name)
 run('qdbus','org.kde.KWin','/KWin','reconfigure')
 stamp.write_text(json.dumps({'color':color,'variant':variant}))
 print('Decoration accent:',color,flush=True)

def apply():
 STATE.mkdir(parents=True,exist_ok=True)
 (STATE/'disabled').unlink(missing_ok=True)
 bundled=Path(__file__).resolve().parents[1]/'terminal/decoration-source'
 if bundled.exists():shutil.copytree(bundled,DATA/'rodip-style/decoration-source',dirs_exist_ok=True)
 manifest=STATE/'backup.json'
 if not manifest.exists():
  entries={}
  for i,p in enumerate(FILES):
   entries[str(p)]=p.exists()
   if p.exists():shutil.copy2(p,STATE/str(i))
  manifest.write_text(json.dumps(entries,indent=2))
 terminal=DATA/'konsole';terminal.mkdir(parents=True,exist_ok=True)
 scheme='[General]\nDescription=Rodip Glass · Wallpaper\nOpacity=0.76\nBlur=true\nWallpaper=\n'
 colors={'Background':'20,23,24','BackgroundIntense':'20,23,24','BackgroundFaint':'26,29,30','Foreground':'228,233,224','ForegroundIntense':'248,250,245','ForegroundFaint':'163,173,158'}
 palette=['34,39,34','223,118,108','163,185,116','218,191,128','135,176,192','181,151,190','128,189,174','220,227,216']
 for i,c in enumerate(palette):
  for suffix in ['', 'Intense','Faint']:colors['Color'+str(i)+suffix]=c
 for section,c in colors.items():scheme+=f'\n[{section}]\nColor={c}\n'
 (terminal/'RodipGlass.colorscheme').write_text(scheme)
 (terminal/'RodipGlass.profile').write_text('[General]\nName=Rodip Glass\nParent=FALLBACK/\nCommand=/usr/bin/fish\nTerminalColumns=110\nTerminalRows=30\nTerminalMargin=14\nShowTerminalSizeHint=false\n\n[Appearance]\nColorScheme=RodipGlass\nAntiAliasFonts=true\n\n[Scrolling]\nHistoryMode=1\nHistorySize=10000\nScrollBarPosition=2\n')
 key(CONFIG/'konsolerc','Desktop Entry','DefaultProfile','RodipGlass.profile')
 greeting=CONFIG/'fish/conf.d/rodip-glass.fish';greeting.parent.mkdir(parents=True,exist_ok=True)
 greeting.write_text('''# Rodip Glass: only interactive Konsole shells; no login-shell changes.
if status is-interactive; and set -q KONSOLE_VERSION
    function fish_greeting
        if type -q fastfetch
            fastfetch --structure Title:Separator:OS:Kernel:Uptime:Shell:DE:Terminal:CPU:GPU:Memory:Disk:Break:Colors
        end
    end
end
''')
 installed=DATA/'rodip-style/finish-style.py';installed.parent.mkdir(parents=True,exist_ok=True)
 if Path(__file__).resolve()!=installed.resolve():shutil.copy2(__file__,installed)
 auto=CONFIG/'autostart/rodip-style.desktop';auto.parent.mkdir(parents=True,exist_ok=True)
 auto.write_text('[Desktop Entry]\nType=Application\nName=Wallpaper Window Accent\nExec=/usr/bin/python3 '+str(installed)+' --watch\nOnlyShowIn=KDE;\n')
 key(CONFIG/'kwinrc','Plugins','blurEnabled','true')
 sync()
 run('qdbus','org.kde.KWin','/Effects','loadEffect','blur')
 print('Glass profile applied. Backup:',STATE)

def watch():
 import fcntl
 from PySide6.QtCore import QCoreApplication,QFileSystemWatcher,QTimer
 app=QCoreApplication(sys.argv); lock=open(STATE/'watch.lock','w')
 try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:return
 watcher=QFileSystemWatcher([str(CONFIG)]);timer=QTimer();timer.setSingleShot(True);timer.setInterval(500)
 def update():
  if (STATE/'disabled').exists():app.quit();return
  try:sync()
  except Exception as e:print(e,file=sys.stderr,flush=True)
 timer.timeout.connect(update);watcher.directoryChanged.connect(lambda _:timer.start());update();app.exec()

def restore():
 (STATE/'disabled').touch()
 entries=json.loads((STATE/'backup.json').read_text())
 for i,(name,existed) in enumerate(entries.items()):
  p=Path(name)
  if existed:shutil.copy2(STATE/str(i),p)
  else:p.unlink(missing_ok=True)
 for variant in ['A','B']:shutil.rmtree(DATA/'aurorae/themes'/('Bart-Wallpaper-'+variant),ignore_errors=True)
 run('qdbus','org.kde.KWin','/KWin','reconfigure')
 print('Restored saved configuration.')

if __name__=='__main__':
 parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
 for flag in ['apply','watch','restore']:group.add_argument('--'+flag,action='store_true')
 args=parser.parse_args()
 if args.apply:apply()
 elif args.watch:watch()
 else:restore()
