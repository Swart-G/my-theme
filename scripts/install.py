#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One-command install for the complete Rodip Glass Plasma 6 appearance."""
import argparse,datetime,fcntl,json,os,re,shutil,signal,subprocess,sys,time
from pathlib import Path
from urllib.parse import unquote,urlparse
ROOT=Path(__file__).resolve().parents[1]
os.environ['BART_ENHANCEMENT_ROOT']=str(ROOT)
import kde as k
import controller as c
STATE=Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'rodip-glass'
IDS=['local.bart.modularpanel','local.bart.desktopnumbers','local.bart.systemmonitor','KdeControlStation']
RPM_PACKAGES=['plasma-workspace','plasma-desktop','plasma-nm','plasma-pa','kdeplasma-addons','python3-pyside6','qt6-qttools','ksystemstats','libksysguard','kde-connect','qt6-qt5compat','qt6-qtdeclarative']
CONFIG_NAMES=['kdeglobals','plasmarc','kwinrc','plasmashellrc','plasma-org.kde.plasma.desktop-appletsrc','kglobalshortcutsrc','autostart/bart-enhancement-layout.desktop','autostart/modular-glass-layout.desktop']
def run(args,**kwargs):
 result=subprocess.run([str(x) for x in args],capture_output=True,text=True,**kwargs)
 if result.returncode:raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f'{args[0]} failed')
 return result.stdout.strip()
def elevated(args):
 if shutil.which('pkexec'):return run(['pkexec',*args])
 if shutil.which('sudo'):return run(['sudo',*args])
 raise RuntimeError('Для системной части нужен pkexec или sudo. Можно установить только рабочий стол: --desktop-only.')
def check(dependencies=False,desktop_only=False):
 distro=dict(line.split('=',1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
 missing=[]
 if distro.get('ID','').strip('"')=='fedora':
  for package in RPM_PACKAGES + ([] if desktop_only else ['sddm']):
   if subprocess.run(['rpm','-q',package],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:missing.append(package)
 if missing and dependencies:
  print('Устанавливаю зависимости Fedora: '+', '.join(missing),flush=True)
  elevated(['dnf','install','-y',*missing]);missing=[]
 if missing:return {'missing_packages':missing,'ready':False}
 k.QDBUS=k.find_qdbus()
 for tool in ['plasmashell','kwriteconfig6','plasma-apply-desktoptheme','plasma-apply-colorscheme']:
  if not shutil.which(tool):raise RuntimeError('Нет команды '+tool+'; установите компоненты KDE Plasma 6.')
 from PySide6.QtCore import qVersion
 probe=k.probe()
 version=tuple(int(x) for x in re.findall(r'\d+',probe['version'])[:2])
 if len(version)<2 or version[0]!=6 or version[1]<7:raise RuntimeError('Нужна активная сессия KDE Plasma 6.7 или новее в ветке 6.x.')
 return {'ready':True,'plasma':probe['version'],'qt':qVersion(),'screens':probe['screens'],'missing_packages':[]}
def managed():
 return [k.CONFIG/name for name in CONFIG_NAMES]+[k.DATA/'plasma/plasmoids'/ident for ident in IDS]+[k.DATA/'plasma/desktoptheme/zhelly0-glass',k.DATA/'color-schemes/RodipGlass.colors',k.DATA/'kwin/scripts/bart-modular-control',k.DATA/'bart-enhancement',k.STATE,k.DATA/'sddm/themes/rodip-glass']
def snapshot(destination,paths):
 destination.mkdir(parents=True,mode=0o700)
 items=[]
 for i,path in enumerate(paths):
  if path.is_symlink():raise RuntimeError('Не изменяю символьную ссылку: '+str(path))
  exists=path.exists();directory=path.is_dir()
  items.append({'path':str(path),'exists':exists,'directory':directory,'copy':str(i)})
  if exists:
   if directory:shutil.copytree(path,destination/str(i))
   else:shutil.copy2(path,destination/str(i))
 (destination/'manifest.json').write_text(json.dumps(items,indent=2))
 return items
def restore_files(backup,paths):
 allowed={str(p) for p in paths};items=json.loads((backup/'manifest.json').read_text())
 if any(item['path'] not in allowed or Path(item['path']).is_symlink() for item in items):raise RuntimeError('Недопустимый путь в резервной копии')
 for item in items:
  path=Path(item['path'])
  if path.is_dir():shutil.rmtree(path)
  else:path.unlink(missing_ok=True)
  if item['exists']:
   path.parent.mkdir(parents=True,exist_ok=True)
   if item['directory']:shutil.copytree(backup/item['copy'],path)
   else:shutil.copy2(backup/item['copy'],path)
def stop_watchers():
 for project in ['bart-enhancement','modular-glass']:
  watch=k.DATA/project/'scripts/layout-watch.py'
  for pid in subprocess.run(['pgrep','-u',str(os.getuid()),'-f',str(watch)],capture_output=True,text=True).stdout.split():
   try:
    if str(watch).encode() in (Path('/proc')/pid/'cmdline').read_bytes().split(b'\0'):os.kill(int(pid),signal.SIGTERM)
   except (FileNotFoundError,ProcessLookupError):pass
  (k.CONFIG/'autostart'/f'{project}-layout.desktop').unlink(missing_ok=True)
def restart_shell():
 if subprocess.run(['systemctl','--user','is-active','--quiet','plasma-plasmashell.service']).returncode:
  raise RuntimeError('Для безопасного применения требуется plasma-plasmashell.service в активной сессии.')
 expected=min(sum(p['role']=='control' and p['screen']>=0 for p in k.probe()['panels']),len(k.probe()['screens']))
 run(['systemctl','--user','restart','plasma-plasmashell.service'])
 for _ in range(35):
  try:
   current=k.probe()
   ready=sum(p['role']=='control' and p['screen']>=0 for p in current['panels'])
   if ready>=expected:return
  except RuntimeError:pass
  time.sleep(.3)
 raise RuntimeError('Plasma не ответила после перезапуска оболочки.')
def start_watch():
 subprocess.Popen([sys.executable,str(k.DATA/'bart-enhancement/scripts/layout-watch.py')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
def cpu_model():
 for line in Path('/proc/cpuinfo').read_text().splitlines():
  if line.startswith('model name'):return line.split(':',1)[1].strip()
 return 'CPU'
def options():
 return {'height':36,'edge_margin':6,'date_format':'ddd, d MMM','refresh_ms':1500,'show_network':True,'show_gpu':True,'cpu_model':cpu_model(),'has_battery':any(Path('/sys/class/power_supply').glob('BAT*'))}
def copy_packages():
 for ident in IDS:
  dest=k.DATA/'plasma/plasmoids'/ident
  if dest.exists():shutil.rmtree(dest)
  shutil.copytree(ROOT/'plasmoids'/ident,dest)
 dest=k.DATA/'plasma/desktoptheme/zhelly0-glass'
 if dest.exists():shutil.rmtree(dest)
 shutil.copytree(ROOT/'theme',dest)
 dest=k.DATA/'color-schemes/RodipGlass.colors';dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'colors/RodipGlass.colors',dest)
 shutil.copytree(ROOT/'kwin',k.DATA/'kwin/scripts/bart-modular-control',dirs_exist_ok=True)
 for name in ['scripts/kde.py','scripts/controller.py','scripts/layout-watch.py','plasma/layout.js']:
  target=k.DATA/'bart-enhancement'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
def validate(expected_ids=None):
 result=k.evaluate("print(JSON.stringify(panels().map(p=>{p.currentConfigGroup=['BartEnhancement'];const role=p.readConfig('Role','');p.currentConfigGroup=['General'];return {id:p.id,screen:p.screen,role:role,health:p.readConfig('health','')};})));" )
 panels=[p for p in json.loads(result) if p['role']=='control' and p['screen']>=0 and (expected_ids is None or p['id'] in expected_ids)]
 if len(panels)!=len(k.probe()['screens']):raise RuntimeError('Не на всех экранах создана панель.')
 for panel in panels:
  health=json.loads(panel['health']);hosts={h['plugin']:h for h in health['hosts']}
  for ident in ['local.bart.desktopnumbers','org.kde.plasma.digitalclock','KdeControlStation']:
   if hosts.get(ident,{}).get('width',0)<=0:raise RuntimeError('Не загрузился виджет '+ident)
  if abs(health['clockCenter']-health['width']/2)>2:raise RuntimeError('Часы не выровнены по центру.')
 return panels
def wallpaper():
 try:
  value=k.evaluate("var d=desktops().find(d=>d.screen===0);d.currentConfigGroup=['Wallpaper','org.kde.image','General'];print(d.readConfig('Image',''));" )
  path=Path(unquote(urlparse(value).path))
  if path.is_file():return path
  images=list((path/'contents/images').glob('*'))
  images=[p for p in images if p.suffix.lower() in ['.jpg','.jpeg','.png','.webp']]
  if images:return max(images,key=lambda p:p.stat().st_size)
 except (RuntimeError,OSError):pass
 return None
def prepare_sddm():
 dest=k.DATA/'sddm/themes/rodip-glass'
 if dest.exists():shutil.rmtree(dest)
 shutil.copytree(ROOT/'sddm',dest)
 image=wallpaper()
 if image:
  suffix=image.suffix.lower()
  if suffix not in ['.png','.jpg','.jpeg','.webp']:suffix='.png'
  target=dest/('wallpaper'+suffix);shutil.copy2(image,target)
  p=dest/'theme.conf';p.write_text(p.read_text().replace('background=background.svg','background='+target.name))
 return dest
def restore(backup):
 if not backup:backup=Path((STATE/'latest').read_text().strip())
 else:backup=backup.resolve()
 if backup.parent!=STATE/'backups':raise RuntimeError('Резервная копия должна находиться в '+str(STATE/'backups'))
 # Exact restoration is performed from a TTY so Plasma/KWin cannot overwrite cached settings.
 if any(subprocess.run(['pgrep','-u',str(os.getuid()),'-x',name],stdout=subprocess.DEVNULL).returncode==0 for name in ['plasmashell','kwin_wayland','kwin_x11']):
  raise RuntimeError('Выйдите из KDE, войдите в TTY (Ctrl+Alt+F3) и запустите install.sh --restore. Приложения не будут закрыты автоматически.')
 receipt=backup/'sddm.json'
 if receipt.exists():elevated([sys.executable,ROOT/'scripts/system-install.py','--restore',json.loads(receipt.read_text())['backup']])
 restore_files(backup,managed())
 print('Настройки восстановлены. Войдите в KDE.',flush=True)
def apply(args):
 status=check(dependencies=True,desktop_only=args.desktop_only)
 if not status['ready']:raise RuntimeError('Не установлены зависимости: '+', '.join(status['missing_packages']))
 STATE.mkdir(parents=True,exist_ok=True,mode=0o700);STATE.chmod(0o700)
 with (STATE/'lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  backup=STATE/'backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
  snapshot(backup,managed());(STATE/'latest').write_text(str(backup))
  print('Резервная копия: '+str(backup),flush=True)
  try:
   stop_watchers();copy_packages()
   run(['plasma-apply-colorscheme','RodipGlass']);run(['plasma-apply-desktoptheme','zhelly0-glass'])
   k.write_key(k.CONFIG/'kdeglobals','[General]','accentColorFromWallpaper','true')
   for key,value in [('BlurStrength',8),('NoiseStrength',3)]:k.write_key(k.CONFIG/'kwinrc','[Effect-blur]',key,value)
   k.write_key(k.CONFIG/'kwinrc','[Plugins]','blurEnabled','true')
   k.write_key(k.CONFIG/'kwinrc','[Plugins]','bart-modular-controlEnabled','true')
   restart_shell();k.desktops();opts=options();k.STATE.mkdir(parents=True,exist_ok=True)
   layout=c.create_layout(opts);expected_ids=[p['id'] for p in layout];k.dbus('org.kde.KWin','/KWin','reconfigure');c.reload_kwin_script()
   try:k.dbus('org.kde.KWin','/Effects','org.kde.kwin.Effects.loadEffect','blur')
   except RuntimeError:pass
   for _ in range(20):
    time.sleep(.4)
    try:panels=validate(expected_ids);break
    except (RuntimeError,json.JSONDecodeError,KeyError):continue
   else:raise RuntimeError('Новые панели не прошли проверку; прежние панели ещё не удалены.')
   k.evaluate('const keep='+json.dumps(expected_ids)+";panels().forEach(p=>{p.currentConfigGroup=['BartEnhancement'];if(p.readConfig('Role','')!=='control'||!keep.includes(p.id))p.remove();});")
   if not (k.STATE/'baseline').exists():(k.STATE/'baseline').write_text(str(backup))
   (k.STATE/'report.json').write_text(json.dumps({'mode':'apply','version':3,'options':opts},indent=2))
   auto=k.CONFIG/'autostart/bart-enhancement-layout.desktop';auto.parent.mkdir(parents=True,exist_ok=True)
   auto.write_text('[Desktop Entry]\nType=Application\nName=Rodip Glass panel recovery\nOnlyShowIn=KDE;\nExec=python3 '+json.dumps(str(k.DATA/'bart-enhancement/scripts/layout-watch.py'),ensure_ascii=False)+'\n')
   start_watch()
   if not args.desktop_only:
    print('Установка экрана входа SDDM: может потребоваться системный пароль администратора.',flush=True)
    result=elevated([sys.executable,ROOT/'scripts/system-install.py','--source',prepare_sddm()])
    (backup/'sddm.json').write_text(json.dumps(json.loads(result),indent=2))
   (STATE/'report.json').write_text(json.dumps({'backup':str(backup),'system':status,'desktop_only':args.desktop_only,'panels':[p['id'] for p in panels]},indent=2))
   print('Готово. Панель применена.' + ('' if args.desktop_only else ' Экран входа SDDM применяется при следующем запуске SDDM.'),flush=True)
  except BaseException as error:
   (backup/'failure.txt').write_text(str(error))
   print('Установка не завершена. Резервная копия сохранена: '+str(backup)+'\nДля точного отката: install.sh --restore из TTY.',file=sys.stderr)
   raise
if __name__=='__main__':
 parser=argparse.ArgumentParser(description='Rodip Glass: панель, dashboard, Control Station, цвета и SDDM одной командой.')
 group=parser.add_mutually_exclusive_group()
 group.add_argument('--check',action='store_true');group.add_argument('--dry-run',action='store_true')
 group.add_argument('--restore',nargs='?',const='latest',metavar='BACKUP')
 parser.add_argument('--desktop-only',action='store_true',help='Без системного экрана входа SDDM')
 args=parser.parse_args()
 try:
  if os.geteuid()==0:raise RuntimeError('Запускайте install.sh обычным пользователем, без sudo.')
  if args.restore:restore(None if args.restore=='latest' else Path(args.restore))
  elif args.check or args.dry_run:
   print(json.dumps({'system':check(desktop_only=args.desktop_only),'options':options(),'plan':['backup','install source packages','apply glass theme and wallpaper accent','create and verify floating panels','replace previous panels','activate output recovery']+([] if args.desktop_only else ['install matching SDDM with administrator authentication']),'changes':False},ensure_ascii=False,indent=2))
  else:apply(args)
 except Exception as error:print('Ошибка: '+str(error),file=sys.stderr);sys.exit(1)
