#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Small recovery API shared with the event-driven output watcher."""
import json
import kde as k
KWIN_ID='bart-modular-control'
def create_layout(options):
 result=json.loads(k.evaluate('var BART_OPTIONS='+k.variant(options)+';\n'+(k.ROOT/'plasma/layout.js').read_text()).split('BART_RESULT=')[-1])
 (k.STATE/'layout.json').write_text(json.dumps(result,indent=2))
 return result
def reload_kwin_script():
 k.dbus('org.kde.KWin','/Scripting','org.kde.kwin.Scripting.unloadScript',KWIN_ID)
 ident=k.dbus('org.kde.KWin','/Scripting','org.kde.kwin.Scripting.loadScript',k.DATA/'kwin/scripts'/KWIN_ID/'contents/code/main.js',KWIN_ID)
 k.dbus('org.kde.KWin','/Scripting/Script'+ident,'org.kde.kwin.Script.run')
