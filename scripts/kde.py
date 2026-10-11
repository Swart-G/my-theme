#!/usr/bin/env python3
"""User scoped, transactional KDE configuration controller. No shell evaluation."""
import argparse
import ast
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(os.environ.get('BART_ENHANCEMENT_ROOT', Path(__file__).resolve().parents[1]))
HOME = Path.home()
CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', HOME / '.config'))
DATA = Path(os.environ.get('XDG_DATA_HOME', HOME / '.local/share'))
STATE = Path(os.environ.get('XDG_STATE_HOME', HOME / '.local/state')) / 'bart-enhancement'
def find_qdbus():
    return next((str(p) for p in [Path('/usr/lib64/qt6/bin/qdbus'), Path('/usr/lib/qt6/bin/qdbus')]
              if p.is_file()), shutil.which('qdbus6') or shutil.which('qdbus') or '')

QDBUS = find_qdbus()


def run(args, check=True):
    env = os.environ.copy()
    if Path(str(args[0])).name in ['kscreen-doctor', 'plasmashell']:
        env.pop('QT_QPA_PLATFORM', None)
    p = subprocess.run([str(x) for x in args], text=True, capture_output=True, timeout=20, env=env)
    if check and p.returncode:
        raise RuntimeError(f'{args[0]}: {p.stderr.strip() or p.stdout.strip()}')
    return p.stdout.strip()


def log(message):
    print(message, flush=True)
    if STATE.exists():
        with (STATE / 'setup.log').open('a') as f:
            f.write(f'{dt.datetime.now().isoformat()} {message}\n')


def dbus(service, path, method, *args):
    if not QDBUS:
        raise RuntimeError('Нет qdbus Qt6: установите qt6-qttools.')
    return run([QDBUS, service, path, method, *map(str, args)])


def gcall(method, *args):
    return run(['gdbus', 'call', '--session', '--dest', 'org.kde.kglobalaccel',
                '--object-path', '/kglobalaccel', '--method', 'org.kde.KGlobalAccel.' + method, *args])


def variant(value):
    return json.dumps(value, ensure_ascii=False)


def evaluate(js):
    result = dbus('org.kde.plasmashell', '/PlasmaShell', 'org.kde.PlasmaShell.evaluateScript', js)
    if 'Error' in result or 'error:' in result.lower():
        raise RuntimeError('Plasma scripting: ' + result)
    return result


def probe():
    result = evaluate("print('MG_RESULT='+JSON.stringify({version:applicationVersion,"
        "screens:Array.from({length:screenCount},(_,i)=>({id:i,width:screenGeometry(i).width,"
        "height:screenGeometry(i).height})),widgets:knownWidgetTypes,"
        "panels:panels().map(p=>({id:p.id,screen:p.screen,floating:p.floating,opacity:p.opacity,"
        "role:(p.currentConfigGroup=['BartEnhancement'],p.readConfig('Role',''))}))}));")
    return json.loads(result.split('MG_RESULT=')[-1].strip())


def detect():
    info = {'os': Path('/etc/os-release').read_text(), 'session': os.environ.get('XDG_SESSION_TYPE', 'unknown'),
            'tools': {t: shutil.which(t) for t in ['plasmashell', 'kwriteconfig6', 'kreadconfig6',
                       'gdbus', 'kpackagetool6', 'plasma-apply-colorscheme']}, 'qdbus': QDBUS}
    for cmd in ['plasmashell', 'kwin_wayland', 'kwin_x11']:
        if shutil.which(cmd):
            info[cmd] = run([cmd, '--version'], False)
    try:
        info['plasma'] = probe()
        info['effects'] = dbus('org.kde.KWin', '/Effects', 'org.kde.kwin.Effects.listOfEffects').splitlines()
        info['loaded_effects'] = dbus('org.kde.KWin', '/Effects', 'org.kde.kwin.Effects.loadedEffects').splitlines()
        info['desktop_count'] = int(dbus('org.kde.KWin', '/VirtualDesktopManager', 'org.kde.KWin.VirtualDesktopManager.count'))
    except (RuntimeError, ValueError) as e:
        info['session_error'] = str(e)
    try:
        from PySide6.QtCore import qVersion
        info['qt'] = qVersion()
    except ImportError:
        info['qt'] = 'Нет python3-pyside6 (нужен для Qt KeySequence)'
    info['shortcut_file'] = str(CONFIG / 'kglobalshortcutsrc')
    info['shortcuts'] = [{'group': g, 'action': k, 'assigned': v.split(',')[0]}
                         for g, k, v in entries(CONFIG / 'kglobalshortcutsrc') if not k.startswith('_')]
    info['primary_plasma_screen'] = 0  # ScreenPool::primaryScreen() is the first screen in Plasma's output order.
    if shutil.which('kscreen-doctor'):
        try:
            outputs = json.loads(run(['kscreen-doctor', '-j'], False))['outputs']
            info['outputs'] = [{k: o.get(k) for k in ['name', 'connected', 'enabled', 'priority', 'scale', 'size', 'pos']}
                               for o in outputs]
        except (ValueError, KeyError, subprocess.TimeoutExpired) as e:
            info['output_details_error'] = str(e)
    return info


# Preserve comments, unknown groups, key casing and all unrelated keys in KConfig files.
def entries(path):
    group = ''
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        if line.startswith('['):
            group = line
        elif '=' in line and not line.startswith(('#', ';')):
            key, val = line.split('=', 1)
            yield group, key, val


def write_key(path, group, key, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text().splitlines() if path.exists() else []
    current = ''
    start = None
    end = len(lines)
    replaced = False
    for i, line in enumerate(lines):
        if line.startswith('['):
            if current == group:
                end = i
                break
            current = line
            if current == group:
                start = i
        elif current == group and line.startswith(key + '='):
            lines[i] = key + '=' + str(value)
            replaced = True
            break
    if not replaced:
        if start is None:
            lines.extend(['', group, key + '=' + str(value)])
        else:
            lines.insert(end, key + '=' + str(value))
    temp = path.with_name(path.name + '.bart-enhancement.tmp')
    temp.write_text('\n'.join(lines) + '\n')
    if path.exists():
        shutil.copymode(path, temp)
    else:
        temp.chmod(0o600)
    temp.replace(path)


def get_key(path, group, key, default=''):
    return next((v for g, k, v in entries(path) if (g, k) == (group, key)), default)


def managed_files():
    files = [CONFIG / x for x in ['kglobalshortcutsrc','kwinrc','plasmashellrc',
        'plasma-org.kde.plasma.desktop-appletsrc','autostart/modular-glass-layout.desktop',
        'autostart/bart-enhancement-layout.desktop']]
    for package, ident in [('system-monitor','local.bart.systemmonitor'),('media-controller','local.bart.mediacontroller'),
                           ('modular-panel','local.bart.modularpanel'),('desktop-numbers','local.bart.desktopnumbers')]:
        files += [DATA / 'plasma/plasmoids' / ident / p.relative_to(ROOT / 'plasmoids' / package)
                  for p in (ROOT / 'plasmoids' / package).rglob('*') if p.is_file()]
    files += [DATA / 'bart-enhancement' / p for p in ['scripts/kde.py','scripts/layout-watch.py','scripts/controller.py','plasma/layout.js']]
    files += [DATA/'kwin/scripts/bart-modular-control'/p.relative_to(ROOT/'kwin') for p in (ROOT/'kwin').rglob('*') if p.is_file()]
    for ident in ['local.bart.systemmonitor','local.bart.mediacontroller','local.bart.modularpanel','local.bart.desktopnumbers']:
        files += [p for p in (DATA/'plasma/plasmoids'/ident).rglob('*') if p.is_file()]
    return list(dict.fromkeys(files))


def snapshot(directory, info):
    directory.mkdir(parents=True, exist_ok=False)
    manifest = {'created': dt.datetime.now().isoformat(), 'system': info, 'files': []}
    for n, path in enumerate(managed_files()):
        if path.is_symlink():
            raise RuntimeError(f'Отказ изменять символьную ссылку: {path}')
        item = {'path': str(path), 'exists': path.exists(), 'copy': str(n)}
        if path.exists():
            shutil.copy2(path, directory / str(n))
            item['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest['files'].append(item)
    (directory / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    directory.chmod(0o700)
    return manifest


def backup(info):
    backups = STATE / 'backups'
    backups.mkdir(parents=True, exist_ok=True)
    baseline = STATE / 'baseline'
    stamp = dt.datetime.now().strftime('%Y%m%dT%H%M%S%f')
    transaction = backups / stamp
    snapshot(transaction, info)
    if not baseline.exists():
        baseline.write_text(str(transaction))
    else:
        # Extend the original baseline only for files newly introduced by later project versions.
        original = Path(baseline.read_text().strip())
        old = json.loads((original / 'manifest.json').read_text())
        names = {x['path'] for x in old['files']}
        for item in json.loads((transaction / 'manifest.json').read_text())['files']:
            if item['path'] not in names:
                new = dict(item, copy=str(len(old['files'])))
                if item['exists']:
                    shutil.copy2(transaction / item['copy'], original / new['copy'])
                old['files'].append(new)
        (original / 'manifest.json').write_text(json.dumps(old, ensure_ascii=False, indent=2))
    log(f'Резервная копия: {transaction}')
    return transaction


def restore_files(directory):
    manifest = json.loads((directory / 'manifest.json').read_text())
    allowed = {str(p) for p in managed_files()}
    for item in manifest['files']:
        path = Path(item['path'])
        if str(path) not in allowed or path.is_symlink():
            raise RuntimeError(f'Небезопасный путь в манифесте: {path}')
        if item['exists']:
            src = directory / item['copy']
            if hashlib.sha256(src.read_bytes()).hexdigest() != item['sha256']:
                raise RuntimeError(f'Повреждена резервная копия: {src}')
    for item in manifest['files']:
        path = Path(item['path'])
        if item['exists']:
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(directory / item['copy'], path)
        else:
            path.unlink(missing_ok=True)


def restore():
    baseline = STATE / 'baseline'
    if not baseline.exists():
        raise RuntimeError('Нет исходной резервной копии.')
    # Both processes cache configuration and can overwrite a disk-only restoration.
    if run(['pgrep', '-u', str(os.getuid()), '-x', 'plasmashell'], False) or \
       run(['pgrep', '-u', str(os.getuid()), '-x', 'kwin_wayland'], False) or \
       run(['pgrep', '-u', str(os.getuid()), '-x', 'kwin_x11'], False):
        raise RuntimeError('Для точного отката выйдите из KDE, перейдите в TTY (Ctrl+Alt+F3), '
                           'войдите тем же пользователем и выполните ./setup.sh --restore. '
                           'KWin и display manager не будут принудительно остановлены.')
    restore_files(Path(baseline.read_text().strip()))
    baseline.unlink()
    (STATE / 'pending.json').unlink(missing_ok=True)
    log('Исходные настройки восстановлены. Войдите в KDE.')


def target_actions():
    result = [('kwin', f'Switch to Desktop {n}', f'Meta+{n}') for n in range(1, 5)]
    result += [('kwin', f'Window to Desktop {n}', f'Meta+Shift+{n}') for n in range(1, 5)]
    result += [('org.kde.krunner.desktop', '_launch', 'Meta+F'),
               ('plasmashell', 'show-on-mouse-pos', 'Meta+V')]
    return result


def qt_key(text):
    from PySide6.QtGui import QKeySequence
    seq = QKeySequence.fromString(text, QKeySequence.SequenceFormat.PortableText)
    if seq.isEmpty() or seq.count() != 1:
        raise RuntimeError('Неверное сочетание Qt: ' + text)
    return seq[0].toCombined()


def action_id(component, action):
    return [component, action, component, action]


def active_keys(component, action):
    output = gcall('shortcut', variant(action_id(component, action)))
    # gdbus prints ai as ([int, ...],), with an explicit type on empty arrays.
    return [int(n) for n in re.findall(r'-?\d+', output)]


def set_keys(component, action, keys):
    gcall('setForeignShortcut', variant(action_id(component, action)), '@ai ' + variant(keys))
    # KGlobalAccel can reorder alternative bindings; their order is not semantic.
    if set(active_keys(component, action)) != set(keys):
        raise RuntimeError('KGlobalAccel не подтвердил назначение: ' + action)


def shortcut_plan():
    # Enumerate the live daemon, including registered actions missing from config.
    components = ast.literal_eval(gcall('allMainComponents'))[0]
    actions = []
    for component in components:
        actions += ast.literal_eval(gcall('allActionsForComponent', variant(component)))[0]
    registered = {(a[0], a[1]) for a in actions}
    for c, a, _ in target_actions():
        if (c, a) not in registered:
            raise RuntimeError(f'Системное действие не зарегистрировано: {c}/{a}. '
                               'Запустите KRunner/Klipper и повторите.')
    desired = {qt_key(s): (c, a) for c, a, s in target_actions()}
    changes = {}
    for a in actions:
        c, action = a[:2]
        keys = active_keys(c, action)
        remaining = [k for k in keys if k not in desired or desired[k] == (c, action)]
        if remaining != keys:
            changes[(c, action)] = (keys, remaining)
    for c, a, s in target_actions():
        old = active_keys(c, a)
        kept = changes.get((c, a), (old, old))[1]
        new = list(dict.fromkeys(kept + [qt_key(s)]))
        changes[(c, a)] = (old, new)
    return changes


def save_shortcut_key(component, action, keys):
    from PySide6.QtGui import QKeySequence
    text = '\\t'.join(QKeySequence(k).toString(QKeySequence.SequenceFormat.PortableText) for k in keys) or 'none'
    path = CONFIG / 'kglobalshortcutsrc'
    group = f'[services][{component}]' if component.endswith('.desktop') else f'[{component}]'
    old = get_key(path, group, action, '')
    parts = old.split(',', 2)
    # Launch service shortcuts use a single field; ordinary actions have default and label.
    value = text if component.endswith('.desktop') else ','.join([text] + (parts[1:] if len(parts) > 1 else ['none', action]))
    write_key(path, group, action, value)


def shortcuts(plan):
    desired = {qt_key(s): (c, a) for c, a, s in target_actions()}
    # Release every conflicting key before assigning any target, including cross-target conflicts.
    for (c, a), (old, _) in plan.items():
        released = [k for k in old if k not in desired or desired[k] == (c, a)]
        if released != old:
            set_keys(c, a, released)
    for (c, a), (old, new) in plan.items():
        if old != new:
            log(f'Горячая клавиша: {c}/{a}: {old} → {new}')
            set_keys(c, a, new)
    # Flush the daemon's queued KConfig writes before patching persistence.
    time.sleep(1)
    for (c, a), (_, new) in plan.items():
        save_shortcut_key(c, a, new)


def desktops():
    count = int(dbus('org.kde.KWin', '/VirtualDesktopManager', 'org.kde.KWin.VirtualDesktopManager.count'))
    for position in range(count, 4):
        dbus('org.kde.KWin', '/VirtualDesktopManager', 'org.kde.KWin.VirtualDesktopManager.createDesktop', position, position + 1)
    # Preserve all existing desktop UUIDs and additional desktops.
    count = int(dbus('org.kde.KWin', '/VirtualDesktopManager', 'org.kde.KWin.VirtualDesktopManager.count'))
    if count < 4:
        raise RuntimeError('KWin не создал четыре рабочих стола.')
    write_key(CONFIG / 'kwinrc', '[Desktops]', 'Number', count)

