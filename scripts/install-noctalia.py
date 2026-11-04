#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independent Niri/Noctalia installer; privileged operations use fixed paths."""
import argparse
import configparser
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'noctalia'
WALLPAPER_URL = 'https://raw.githubusercontent.com/orangci/walls/master/train-station.jpg'
WALLPAPER_SHA256 = '29d0626d45b607f85b617e11987a7c645c5d1214276b2ed9c59bf2452ec59995'
PACKAGES = ['niri', 'noctalia', 'alacritty', 'fish', 'vlc', 'loupe', 'dolphin', 'plasma-integration', 'playerctl', 'brightnessctl',
            'wireplumber', 'xwayland-satellite', 'xdg-desktop-portal-gnome',
            'adwaita-sans-fonts', 'source-foundry-hack-fonts', 'breeze-cursor-theme',
            'breeze-icon-theme', 'libnotify', 'dbus', 'polkit', 'glibc-langpack-ru',
            'google-noto-sans-fonts', 'python3-evdev', 'xdg-desktop-portal-gtk']
SYSTEM_PATHS = [Path(p) for p in (
    '/etc/greetd/config.toml', '/var/lib/noctalia-greeter/greeter.toml',
    '/var/lib/noctalia-greeter/sync.toml',
    '/usr/local/share/wallpapers/rodip-noctalia/wallpaper',
    '/etc/yum.repos.d/rodip-noctalia.repo',
    '/etc/pki/rpm-gpg/RPM-GPG-KEY-terra44')]
SYSTEM_BACKUPS = Path('/var/backups/rodip-noctalia')
DISPLAY_ALIAS = Path('/etc/systemd/system/display-manager.service')


def run(command, **kwargs):
    result = subprocess.run([str(s) for s in command], text=True, capture_output=True, **kwargs)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'Ошибка: ' + str(command))
    return result.stdout.strip()


def elevated(arguments):
    tool = shutil.which('pkexec') or shutil.which('sudo')
    if not tool:
        raise RuntimeError('Нужен pkexec или sudo для установки системных компонентов.')
    # Stream package progress and authentication prompts to the invoking terminal.
    subprocess.run([tool, sys.executable, str(Path(__file__).resolve()), *map(str, arguments)], check=True)


def location(variable, fallback):
    value = Path(os.environ.get(variable, str(fallback))).expanduser()
    if not value.is_absolute():
        raise RuntimeError(variable + ' должен быть абсолютным путём.')
    return value


def user_paths():
    home = Path.home()
    config = location('XDG_CONFIG_HOME', home / '.config')
    state = location('XDG_STATE_HOME', home / '.local/state')
    binary = home / '.local/bin'
    data = location('XDG_DATA_HOME', home / '.local/share')
    return config, state, binary, data


def files_for_user(config, state, binary, data):
    result = {ASSETS / 'niri' / name: config / 'niri' / name for name in
              ('config.kdl', 'basicsettings.kdl', 'keybinds.kdl', 'alacritty.toml', 'super-tap.py')}
    result.update({ASSETS / 'alacritty.toml': config / 'alacritty/alacritty.toml',
                   ASSETS / 'shell/config.toml': config / 'noctalia/config.toml',
                   ASSETS / 'shell/settings.toml': state / 'noctalia/settings.toml',
                   ASSETS / 'shell/noctalia.service': config / 'systemd/user/noctalia.service',
                   ASSETS / 'shell/niri-super-tap.service': config / 'systemd/user/niri-super-tap.service',
                   ASSETS / 'shell/meta-wheel-niri.conf': config / 'systemd/user/meta-wheel-desktops.service.d/niri.conf',
                   ASSETS / 'shell/niri-portals.conf': config / 'xdg-desktop-portal/niri-portals.conf'})
    result.update({ASSETS / 'bin' / name: binary / name for name in
                   ('niri-show-desktop', 'niri-open-obsidian', 'niri-open-discord')})
    result[ASSETS / 'kde/org.kde.dolphin.desktop'] = data / 'applications/org.kde.dolphin.desktop'
    result[ASSETS / 'kde/Noctalia.colors'] = data / 'color-schemes/Noctalia.colors'
    plugins = ASSETS / 'plugins'
    result.update({p: data / 'noctalia/plugins' / p.relative_to(plugins)
                   for p in sorted(plugins.rglob('*')) if p.is_file()})
    theme = ASSETS / 'gtk/Lavanda-Sea'
    result.update({p: data / 'themes/Lavanda-Sea' / p.relative_to(theme)
                   for p in sorted(theme.rglob('*')) if p.is_file()})
    # Each GTK version has the same theme preferences, but a separate destination.
    result[ASSETS / 'gtk/settings.ini'] = config / 'gtk-3.0/settings.ini'
    result[ASSETS / 'gtk/settings4.ini'] = config / 'gtk-4.0/settings.ini'
    for version in ('gtk-3.0', 'gtk-4.0'):
        for name in ('gtk.css', 'colors.css'):
            result[ASSETS / 'gtk' / version / name] = config / version / name
    return result


def default_apps(config, data):
    """Merge media defaults while retaining unrelated MIME associations."""
    def ini():
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.optionxform = str
        return parser

    target = config / 'mimeapps.list'
    associations = ini()
    associations.read(target)
    directories = [data, *map(Path, os.environ.get(
        'XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':'))]
    for desktop, prefix in [('vlc.desktop', 'video/'), ('org.gnome.Loupe.desktop', 'image/')]:
        source = next((directory / 'applications' / desktop for directory in directories
                       if (directory / 'applications' / desktop).is_file()), None)
        if source is None:
            raise RuntimeError('Не найдено приложение: ' + desktop + '. Установите VLC и Loupe.')
        entry = ini()
        entry.read(source)
        types = [mime for mime in entry['Desktop Entry']['MimeType'].split(';')
                 if mime.startswith(prefix)]
        for section in ('Default Applications', 'Added Associations'):
            if not associations.has_section(section):
                associations.add_section(section)
            for mime in types:
                previous = associations[section].get(mime, '').split(';')
                apps = [desktop] + [app for app in previous if app and app != desktop]
                associations[section][mime] = ';'.join(apps) + ';'
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('w') as stream:
        associations.write(stream, space_around_delimiters=False)


def dolphin_colors(config):
    """Select Dolphin's own palette while preserving its other settings verbatim."""
    target = config / 'dolphinrc'
    text = target.read_text() if target.exists() else ''
    lines = text.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if line.strip() == '[UiSettings]'), None)
    if start is None:
        text += ('\n' if text and not text.endswith('\n') else '') + '[UiSettings]\nColorScheme=Noctalia\n'
    else:
        end = next((i for i in range(start + 1, len(lines))
                    if lines[i].lstrip().startswith('[')), len(lines))
        body = [line for line in lines[start + 1:end]
                if not re.match(r'^\s*ColorScheme\s*=', line)]
        if body and not body[-1].endswith('\n'):
            body[-1] += '\n'
        if not lines[start].endswith('\n'):
            lines[start] += '\n'
        text = ''.join(lines[:start + 1] + body + ['ColorScheme=Noctalia\n'] + lines[end:])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)


def refuse_links(path):
    for part in (path, *path.parents):
        if part.is_symlink():
            raise RuntimeError('Не изменяю путь через символьную ссылку: ' + str(part))


def snapshot(destination, paths):
    destination.mkdir(parents=True, mode=0o700)
    records = []
    for index, path in enumerate(paths):
        refuse_links(path)
        if path.exists() and not path.is_file():
            raise RuntimeError('Ожидался обычный файл: ' + str(path))
        record = {'path': str(path), 'exists': path.exists(), 'copy': str(index)}
        if record['exists']:
            record.update(uid=path.stat().st_uid, gid=path.stat().st_gid)
        records.append(record)
        if record['exists']:
            shutil.copy2(path, destination / str(index))
    (destination / 'manifest.json').write_text(json.dumps(records, indent=2))


def restore_files(backup, allowed):
    records = json.loads((backup / 'manifest.json').read_text())
    allowed = {str(p) for p in allowed}
    # Validate the complete manifest before modifying any destination.
    for record in records:
        if record['path'] not in allowed or not re.fullmatch(r'\d+', record['copy']):
            raise RuntimeError('Недопустимый путь в резервной копии.')
        path = Path(record['path'])
        refuse_links(path)
        source = backup / record['copy']
        if record['exists'] and (source.is_symlink() or not source.is_file()):
            raise RuntimeError('Повреждена резервная копия: ' + str(source))
    for record in records:
        path = Path(record['path'])
        if record['exists']:
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup / record['copy'], path)
            if os.geteuid() == 0:
                os.chown(path, record['uid'], record['gid'])
        else:
            path.unlink(missing_ok=True)


def render(text, config, binary, username, scale):
    # Tokens occur inside TOML/KDL quoted strings; encode embedded quotes/backslashes.
    values = {'CONFIG': str(config), 'BIN': str(binary), 'USER': username}
    for name, value in values.items():
        text = text.replace('@' + name + '@', json.dumps(value, ensure_ascii=False)[1:-1])
    return text.replace('@SCALE@', str(scale))


def wallpaper(destination, source=None):
    if source:
        if not source.is_file() or source.stat().st_size > 50 * 1024 * 1024:
            raise RuntimeError('Обои должны быть обычным изображением размером до 50 МБ.')
        shutil.copyfile(source, destination)
    else:
        with urllib.request.urlopen(WALLPAPER_URL, timeout=45) as response:
            payload = response.read(50 * 1024 * 1024 + 1)
        if hashlib.sha256(payload).hexdigest() != WALLPAPER_SHA256:
            raise RuntimeError('Контрольная сумма обоев изменилась. Используйте --wallpaper ФАЙЛ.')
        destination.write_bytes(payload)
    header = destination.read_bytes()[:16]
    if not (header.startswith((b'\xff\xd8\xff', b'\x89PNG\r\n\x1a\n', b'GIF87a', b'GIF89a'))
            or (header.startswith(b'RIFF') and header[8:12] == b'WEBP')):
        raise RuntimeError('Для обоев используйте JPEG, PNG, WebP или GIF.')


def set_toml(text, section, values):
    """Replace only requested keys; retain unrelated sections, including initial_session."""
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines)
                  if re.fullmatch(r'\s*\[' + re.escape(section) + r'\]\s*(?:#.*)?', line)), None)
    if start is None:
        lines += ['', '[' + section + ']']
        start = len(lines) - 1
    end = next((i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith('[')), len(lines))
    body = lines[start + 1:end]
    for key, value in values.items():
        body = [line for line in body if not re.match(r'^\s*' + re.escape(key) + r'\s*=', line)]
        body.append(key + ' = ' + json.dumps(value, ensure_ascii=False))
    result = '\n'.join(lines[:start + 1] + body + lines[end:]) + '\n'
    tomllib.loads(result)
    return result


def fedora44():
    release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
    if release.get('ID', '').strip('"') != 'fedora' or release.get('VERSION_ID', '').strip('"') != '44':
        raise RuntimeError('Автоматическая установка пакетов и Greeter рассчитана на Fedora 44. '
                           'На другой системе используйте --desktop-only --skip-packages.')


def system_restore(backup):
    if backup.parent != SYSTEM_BACKUPS or backup.is_symlink():
        raise RuntimeError('Недопустимая системная резервная копия.')
    receipt = json.loads((backup / 'service.json').read_text())
    previous = receipt['previous']
    if previous and not re.fullmatch(r'[\w@.:-]+\.service', previous):
        raise RuntimeError('Недопустимая служба в резервной копии.')
    restore_files(backup, SYSTEM_PATHS)
    # greetd may not exist if its package installation failed.
    subprocess.run(['systemctl', 'disable', 'greetd.service'], capture_output=True)
    if previous:
        run(['systemctl', 'enable', '--force', previous])
    run(['systemctl', 'daemon-reload'])
    existing = [p for p in SYSTEM_PATHS if p.exists()]
    if existing and shutil.which('restorecon'):
        run(['restorecon', '-RF', *existing])
    print('Системное оформление восстановлено. Сеансы не перезапускались.')


def system_install(stage, username, scale, skip_packages):
    fedora44()
    account = pwd.getpwnam(username)
    if account.pw_uid == 0:
        raise RuntimeError('Укажите обычного пользователя.')
    for name in ('wallpaper', 'greeter.toml', 'RPM-GPG-KEY-terra44'):
        path = stage / name
        if path.is_symlink() or not path.is_file():
            raise RuntimeError('Неполный комплект установки: ' + name)
    conf = tomllib.loads((stage / 'greeter.toml').read_text())
    if conf['user']['default'] != username or conf['output']['scale'] != scale:
        raise RuntimeError('Параметры Greeter не совпадают с параметрами установки.')
    backup = SYSTEM_BACKUPS / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    snapshot(backup, SYSTEM_PATHS)
    alias = DISPLAY_ALIAS
    previous = alias.resolve().name if alias.is_symlink() else None
    (backup / 'service.json').write_text(json.dumps({'previous': previous}))
    print('Системная резервная копия: ' + str(backup), flush=True)
    # Publish the receipt before mutations, so interrupted/failed installs remain restorable.
    (stage / 'system-backup.txt').write_text(str(backup))
    try:
        if not skip_packages:
            key = SYSTEM_PATHS[-1]
            key.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(stage / key.name, key)
            run(['rpm', '--import', key])
            repo = SYSTEM_PATHS[-2]
            repo.write_text('[rodip-noctalia]\nname=Noctalia Greeter (Terra)\n'
                            'baseurl=https://repos.fyralabs.com/terra$releasever\n'
                            'enabled=1\ngpgcheck=1\n'
                            'gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-terra44\n'
                            'includepkgs=noctalia-greeter\n')
            subprocess.run(['dnf', '--repo=fedora', '--repo=updates', '--repo=rodip-noctalia',
                            '-y', 'install', 'greetd', 'greetd-selinux', 'wlroots', 'noctalia-greeter'], check=True)
        for binary in ('greetd', 'noctalia-greeter', 'noctalia-greeter-session', 'noctalia-greeter-compositor'):
            if not shutil.which(binary):
                raise RuntimeError('Не найдена зависимость: ' + binary)
        run(['systemd-sysusers'])
        greetd_config = SYSTEM_PATHS[0]
        existing = greetd_config.read_text() if greetd_config.exists() else '[terminal]\nvt = 1\n'
        old = tomllib.loads(existing)
        greeter_user = old.get('default_session', {}).get('user', 'greetd')
        greeter = pwd.getpwnam(greeter_user)
        existing = set_toml(existing, 'default_session', {
            'command': 'env LANG=ru_RU.UTF-8 LC_TIME=ru_RU.UTF-8 /usr/bin/noctalia-greeter-session',
            'user': greeter_user})
        greetd_config.parent.mkdir(parents=True, exist_ok=True)
        greetd_config.write_text(existing)
        greetd_config.chmod(0o644)
        state = SYSTEM_PATHS[1].parent
        refuse_links(state)
        state.mkdir(parents=True, exist_ok=True)
        state.chmod(0o750)
        os.chown(state, greeter.pw_uid, greeter.pw_gid)
        shutil.copyfile(stage / 'greeter.toml', SYSTEM_PATHS[1])
        for path in SYSTEM_PATHS[1:3]:
            if path.exists():
                path.chmod(0o640)
                os.chown(path, greeter.pw_uid, greeter.pw_gid)
        target = SYSTEM_PATHS[3]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(stage / 'wallpaper', target)
        target.chmod(0o644)
        run(['runuser', '-u', greeter_user, '--', 'test', '-r', target])
        sessions = run(['noctalia-greeter', 'sessions']).splitlines()
        if 'Niri' not in sessions:
            raise RuntimeError('Greeter не обнаружил установленный сеанс Niri.')
        if 'not found' in run(['ldd', '/usr/bin/noctalia-greeter-compositor']):
            raise RuntimeError('Не найдены библиотеки графического компонента Greeter.')
        if shutil.which('restorecon'):
            run(['restorecon', '-RF', *[p for p in SYSTEM_PATHS if p.exists()]])
        # Never use --now: switching a running display manager would end the session.
        if previous and previous != 'greetd.service':
            run(['systemctl', 'disable', previous])
        run(['systemctl', 'enable', '--force', 'greetd.service'])
    except BaseException:
        print('Ошибка; восстанавливаю системные файлы и прежний экран входа.', file=sys.stderr)
        system_restore(backup)
        raise


def validate(stage):
    run(['niri', 'validate', '--config', stage / 'niri/config.kdl'])
    run(['noctalia', 'config', 'validate', stage / 'shell/config.toml'])
    # Noctalia validates config.toml; runtime overrides must also parse as TOML.
    tomllib.loads((stage / 'shell/settings.toml').read_text())
    tomllib.loads((stage / 'greeter.toml').read_text())
    tomllib.loads((stage / 'niri/alacritty.toml').read_text())


def stage_files(stage, config, binary, username, scale, image):
    for folder in ('niri', 'shell', 'bin'):
        (stage / folder).mkdir(parents=True)
        for source in (ASSETS / folder).iterdir():
            if not source.is_file():
                continue
            target = stage / folder / source.name
            target.write_text(render(source.read_text(), config, binary, username, scale))
            target.chmod(source.stat().st_mode & 0o777)
    # Validation must resolve the staged includes, not a possibly old installed config.
    main = stage / 'niri/config.kdl'
    main.write_text(main.read_text().replace('include "basicsettings.kdl"',
                    'include ' + json.dumps(str(stage / 'niri/basicsettings.kdl'))).replace(
                    'include "keybinds.kdl"', 'include ' + json.dumps(str(stage / 'niri/keybinds.kdl'))))
    (stage / 'greeter.toml').write_text(render((ASSETS / 'system/greeter.toml').read_text(),
                                             config, binary, username, scale))
    shutil.copyfile(ASSETS / 'system/RPM-GPG-KEY-terra44', stage / 'RPM-GPG-KEY-terra44')
    wallpaper(stage / 'wallpaper', image)


def main():
    parser = argparse.ArgumentParser(description='Полное оформление Niri + Noctalia, второй установщик my-theme.')
    parser.add_argument('--dry-run', action='store_true', help='план без записи файлов, сети и авторизации')
    parser.add_argument('--desktop-only', action='store_true', help='без системного экрана входа')
    parser.add_argument('--skip-packages', action='store_true', help='зависимости уже установлены')
    parser.add_argument('--wallpaper', type=Path, help='своё изображение вместо загрузки городского фона')
    parser.add_argument('--scale', type=float, default=1.25, help='масштаб Greeter (по умолчанию 1.25)')
    parser.add_argument('--restore', nargs='?', const='latest', help='откат последней или указанной копии')
    parser.add_argument('--system-install', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--system-restore', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--user', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 0.5 <= args.scale <= 4:
        parser.error('--scale должен быть от 0.5 до 4')
    if args.system_install or args.system_restore:
        if os.geteuid() != 0:
            raise RuntimeError('Системный шаг требует прав администратора.')
        if args.system_restore:
            system_restore(args.system_restore)
        else:
            system_install(args.system_install, args.user, args.scale, args.skip_packages)
        return
    if os.geteuid() == 0:
        raise RuntimeError('Запускайте установщик обычным пользователем, без sudo.')
    config, state, binary, data = user_paths()
    project_state = state / 'rodip-noctalia'
    files = files_for_user(config, state, binary, data)
    image_target = config / 'niri/wallpaper-city.jpg'
    managed = [*files.values(), image_target, config / 'mimeapps.list', config / 'dolphinrc']
    if args.dry_run:
        if args.restore:
            print('Откат ' + args.restore + '; пользовательские копии: ' + str(project_state / 'backups'))
            print('Системная часть восстанавливается только при наличии квитанции в выбранной копии.')
            return
        print('Niri + Noctalia: ' + ', '.join(str(p) for p in managed if not p.is_relative_to(data)))
        print('Dolphin: Noctalia — ' + str(data / 'color-schemes/Noctalia.colors'))
        print('Discord Voice: локальная версия с исправлением значка; native/Flatpak launcher.')
        print('GTK Lavanda-Sea: ' + str(data / 'themes/Lavanda-Sea'))
        print('Приложения по умолчанию: видео — VLC, изображения — Loupe; Alacritty — fish, US/RU.')
        print('Обои: ' + (str(args.wallpaper) if args.wallpaper else WALLPAPER_URL + ' (SHA256 проверяется)'))
        print('Пакеты Fedora: ' + ('пропущены' if args.skip_packages else ', '.join(PACKAGES)))
        print('Экран входа: ' + ('пропущен' if args.desktop_only else 'greetd + Noctalia Greeter, Terra только для noctalia-greeter'))
        print('Откат: ' + str(project_state / 'backups'))
        return
    project_state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (project_state / 'install.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.restore:
            backup = Path((project_state / 'latest').read_text()) if args.restore == 'latest' else Path(args.restore).absolute()
            if backup.parent != project_state / 'backups' or backup.is_symlink():
                raise RuntimeError('Выберите копию из ' + str(project_state / 'backups'))
            receipt = backup / 'system-backup.txt'
            if receipt.exists():
                elevated(['--system-restore', receipt.read_text().strip()])
            restore_files(backup, managed)
            run(['systemctl', '--user', 'daemon-reload'])
            print('Файлы восстановлены. Перезайдите в Niri для применения.')
            return
        if not args.desktop_only or not args.skip_packages:
            fedora44()
        if not args.skip_packages:
            tool = shutil.which('pkexec') or shutil.which('sudo')
            if not tool:
                raise RuntimeError('Нужен pkexec или sudo.')
            subprocess.run([tool, 'dnf', '--repo=fedora', '--repo=updates', '-y', 'install', *PACKAGES], check=True)
        username = pwd.getpwuid(os.getuid()).pw_name
        backup = project_state / 'backups' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        with tempfile.TemporaryDirectory(prefix='rodip-noctalia-') as temp:
            stage = Path(temp)
            stage_files(stage, config, binary, username, args.scale, args.wallpaper)
            validate(stage)
            snapshot(backup, managed)
            (project_state / 'latest').write_text(str(backup))
            print('Резервная копия: ' + str(backup), flush=True)
            system_applied = False
            try:
                for source, target in files.items():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if (source.is_relative_to(ASSETS / 'gtk/Lavanda-Sea')
                            or source.suffix in ('.png', '.webp')):
                        shutil.copyfile(source, target)
                    else:
                        target.write_text(render(source.read_text(), config, binary, username, args.scale))
                    target.chmod(0o755 if source.parent.name == 'bin' else 0o644)
                shutil.copyfile(stage / 'wallpaper', image_target)
                default_apps(config, data)
                dolphin_colors(config)
                if not args.desktop_only:
                    try:
                        elevated(['--system-install', stage, '--user', username, '--scale', args.scale,
                                  *(['--skip-packages'] if args.skip_packages else [])])
                        system_applied = True
                    finally:
                        receipt = stage / 'system-backup.txt'
                        if receipt.exists():
                            shutil.copyfile(receipt, backup / receipt.name)
                run(['systemctl', '--user', 'daemon-reload'])
            except BaseException:
                try:
                    if system_applied:
                        elevated(['--system-restore', (backup / 'system-backup.txt').read_text().strip()])
                finally:
                    restore_files(backup, managed)
                print('Пользовательские файлы восстановлены. Копия: ' + str(backup), file=sys.stderr)
                raise
        print('Готово. Перезайдите в Niri. ' +
              ('' if args.desktop_only else 'Экран входа применится при следующей загрузке. ') +
              'Текущий сеанс не перезапускался.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError, ValueError) as error:
        print('Ошибка: ' + str(error), file=sys.stderr)
        sys.exit(1)
