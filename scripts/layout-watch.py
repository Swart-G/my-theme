#!/usr/bin/env python3
"""Event-driven output/session recovery, no periodic subprocess polling."""
import os
os.environ.pop('BART_ENHANCEMENT_ROOT',None)
os.environ.pop('QT_QPA_PLATFORM',None)
import fcntl
import json
from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtDBus import QDBusConnection,QDBusServiceWatcher
import controller as c
import kde as k

if not (k.STATE/'baseline').exists():raise SystemExit(0)
with (k.STATE/'watch.lock').open('w') as singleton:
    try:fcntl.flock(singleton,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise SystemExit(0)
    app=QGuiApplication([])
    timer=QTimer();timer.setSingleShot(True);timer.setInterval(750)
    def update():
        if (k.STATE/'pending.json').exists():timer.start(1000);return
        try:
            with (k.STATE/'lock').open('w') as lock:
                fcntl.flock(lock,k.fcntl.LOCK_EX|k.fcntl.LOCK_NB)
                report=json.loads((k.STATE/'report.json').read_text())
                if report['mode']!='apply':return
                c.create_layout(report['options']);c.reload_kwin_script()
        except Exception as error:
            k.log('Output recovery: '+str(error))
    def connect_screen(screen):
        screen.geometryChanged.connect(lambda *_:timer.start());timer.start()
    timer.timeout.connect(update)
    for screen in app.screens():connect_screen(screen)
    app.screenAdded.connect(connect_screen);app.screenRemoved.connect(lambda *_:timer.start())
    watchers=[]
    for service in ['org.kde.plasmashell','org.kde.KWin']:
        watcher=QDBusServiceWatcher(service,QDBusConnection.sessionBus(),QDBusServiceWatcher.WatchModeFlag.WatchForRegistration)
        watcher.serviceRegistered.connect(lambda *_:timer.start());watchers.append(watcher)
    app.exec()
