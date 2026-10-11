#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Style the installed native Plasma 6.7 locker; leave authentication intact."""
import json, os, shutil
from pathlib import Path
IDENT='org.rodip.glass.shell'

def build(data):
 native=Path('/usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen')
 if not (native/'MainBlock.qml').exists():raise RuntimeError('Не найден штатный экран блокировки Plasma 6.7.')
 main=(native/'MainBlock.qml').read_text()
 marker='    id: sessionManager\n'
 if main.count(marker)!=1:raise RuntimeError('Изменился API экрана блокировки KDE; оформление не применено.')
 package=Path(data)/'plasma/shells'/IDENT
 package.mkdir(parents=True,exist_ok=True)
 destination=package/'contents/lockscreen'
 if destination.exists():shutil.rmtree(destination)
 shutil.copytree(native,destination)
 # Explicit data list keeps decoration out of the native authentication layout.
 glass='''
    data: [Rectangle {
        parent: sessionManager
        z: -1
        width: Math.min(sessionManager.width - 24, Kirigami.Units.gridUnit * 24)
        x: (sessionManager.width - width) / 2
        y: Math.max(0, sessionManager.userList.y - Kirigami.Units.largeSpacing * 2)
        height: Math.max(Kirigami.Units.gridUnit * 14, sessionManager.visibleBoundary - y + Kirigami.Units.largeSpacing * 3)
        radius: Kirigami.Units.cornerRadius * 3
        color: Qt.alpha(Kirigami.Theme.backgroundColor, 0.78)
        border.width: 1
        border.color: Qt.alpha(Kirigami.Theme.highlightColor, 0.55)
    }]
'''
 (destination/'MainBlock.qml').write_text(main.replace(marker,marker+glass))
 # Preserve the shipped password/PAM/fingerprint logic and Qt API on every install.
 (package/'metadata.json').write_text(json.dumps({'KPackageStructure':'Plasma/Shell','KPlugin':{'Id':IDENT,'Name':'Rodip Glass lock screen','Version':'1.0','License':'GPL-2.0-or-later'},'X-Plasma-APIVersion':'2','X-Plasma-FallbackPackage':'org.kde.plasma.desktop'},indent=2))
 return package

if __name__=='__main__':
 print(build(Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))))
