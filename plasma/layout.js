// SPDX-License-Identifier: MIT
(function() {
    const o = BART_OPTIONS;
    const required = ['org.kde.plasma.kickoff', 'org.kde.plasma.icontasks', 'local.bart.desktopnumbers', 'org.kde.plasma.digitalclock',
        'org.kde.plasma.mediacontroller', 'local.bart.systemmonitor',
        'org.kde.plasma.networkmanagement', 'org.kde.plasma.bluetooth',
        'org.kde.plasma.volume', 'org.kde.plasma.battery',
        'org.kde.plasma.notifications', 'org.kde.plasma.systemtray', 'KdeControlStation'];
    required.forEach(t => { if (!knownWidgetTypes.includes(t)) throw new Error('Missing widget: ' + t); });
    const all = panels();
    const owned = all.filter(p => {p.currentConfigGroup=['BartEnhancement'];return p.readConfig('Role','') === 'control';});
    const oldTray = all.filter(p => !owned.some(x=>x.id===p.id)).reduce((items,p)=>items.concat(p.widgets('org.kde.plasma.systemtray')),[])[0];
    let result = [];
    for (let screen=0; screen<screenCount; ++screen) {
        const geometry = screenGeometry(screen);
        if (geometry.width < 800) throw new Error('Screen too narrow: ' + geometry.width);
        let p = owned.find(p => p.screen === screen);
        if (!p) {
            p = new Panel('local.bart.modularpanel');
            p.currentConfigGroup=['BartEnhancement'];p.writeConfig('Role','control');
        }
        p.screen=screen;p.location='top';p.alignment='left';p.offset=0;
        p.height=o.height+o.edge_margin*2;p.currentConfigGroup=['General'];p.floating=!p.readConfig('unified',false);p.opacity='translucent';
        p.lengthMode='fill';p.minimumLength=geometry.width;p.maximumLength=geometry.width;
        p.currentConfigGroup=['General'];p.writeConfig('moduleHeight',o.height);p.writeConfig('edgeMargin',o.edge_margin);p.writeConfig('cpuModel',o.cpu_model||'CPU');
        required.forEach(type => {
            let w = p.widgets(type)[0];
            const created = !w;
            if (!w) w=p.addWidget(type);
            if (type === 'org.kde.plasma.digitalclock') {
                w.currentConfigGroup=['Appearance'];w.writeConfig('use24hFormat',2);w.writeConfig('showDate',true);
                w.writeConfig('dateDisplayFormat',1);w.writeConfig('dateFormat','custom');
                w.writeConfig('customDateFormat',geometry.width<1300?'ddd, d MMM':o.date_format);
                w.writeConfig('autoFontAndSize',false);w.writeConfig('fontSize',11);w.writeConfig('fontWeight',400);
            }
            if (created && type === 'local.bart.systemmonitor') {
                w.currentConfigGroup=['General'];w.writeConfig('refreshMs',o.refresh_ms);
                w.writeConfig('temperatureSensor',o.temperature_sensor || '');w.writeConfig('gpuSensor',o.gpu_sensor || '');
                w.writeConfig('swapSensor',o.swap_sensor || '');w.writeConfig('showNetwork',o.show_network);
            }
            if (type === 'org.kde.plasma.kickoff' && screen === 0) {
                w.globalShortcut='';w.globalShortcut='Meta+K';
            }
            if (type === 'KdeControlStation') {
                w.currentConfigGroup=['Appearance'];
                w.writeConfig('layout',0);w.writeConfig('animations',true);w.writeConfig('transparency',true);
                w.writeConfig('transparencyLevel',28);w.writeConfig('showAvatar',false);w.writeConfig('showBorders',true);
                w.writeConfig('showBattery',!!o.has_battery);w.writeConfig('icon','configure-toolbars');
                if(screen===0){w.globalShortcut='';w.globalShortcut='Meta+Shift+K';}
            }
            if (type === 'org.kde.plasma.systemtray') {
                w.currentConfigGroup=['BartEnhancement'];
                if (!w.readConfig('TrayImported',false)) {
                    if (oldTray) {
                        oldTray.currentConfigGroup=['General'];w.currentConfigGroup=['General'];
                        ['hiddenItems','shownItems','showAllItems','extraItems','disabledStatusNotifiers','knownItems','iconSpacing','scaleIconsToFit'].forEach(key=>{
                            if (oldTray.configKeys.includes(key)) w.writeConfig(key,oldTray.readConfig(key));
                        });
                    }
                    w.currentConfigGroup=['BartEnhancement'];w.writeConfig('TrayImported',true);
                }
                w.currentConfigGroup=['General'];
                const extra = String(w.readConfig('extraItems','')).split(',').filter(t=>t && !required.includes(t));
                w.writeConfig('extraItems',extra);w.writeConfig('scaleIconsToFit',false);w.writeConfig('iconSpacing',2);
            }
            w.reloadConfig();
        });
        p.currentConfigGroup=['General'];
        p.writeConfig('AppletOrder',required.map(t=>p.widgets(t)[0].id).join(';'));p.reloadConfig();
        result.push({id:p.id,role:'control',screen:screen,widgets:p.widgets().map(w=>({id:w.id,type:w.type}))});
    }
    print('BART_RESULT='+JSON.stringify(result));
})();
