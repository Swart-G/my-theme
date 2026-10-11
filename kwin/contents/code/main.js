// SPDX-License-Identifier: MIT
// Event-driven KWin 6 script. Match outputs by geometry, never index order.
(function () {
    const timer = new QTimer();
    timer.singleShot = true;
    timer.interval = 45;
    let publishing = false;
    let pending = false;
    function schedule() { timer.start(); }
    function stateFor(output) {
        const desktop = workspace.currentDesktopForScreen(output);
        let maximized = false, fullscreen = false;
        for (const w of workspace.windowList()) {
            if (w.deleted || w.minimized || w.dock || w.desktopWindow || w.appletPopup || w.output !== output) continue;
            if (!w.normalWindow && !w.dialog) continue;
            if (!w.onAllDesktops && !w.desktops.some(d => d === desktop)) continue;
            if (w.activities.length && !w.activities.includes(workspace.currentActivity)) continue;
            maximized = maximized || w.maximizeMode === 3; // KWin::MaximizeFull, verified on KWin 6.7.5
            fullscreen = fullscreen || w.fullScreen;
        }
        return {geometry: output.geometry, maximized: maximized, fullscreen: fullscreen};
    }
    function publish() {
        if (publishing) { pending = true; return; }
        const states = workspace.screens.map(stateFor);
        const signature = JSON.stringify(states);
        publishing = true;
        const js = "const states=" + signature + ";panels().forEach(p=>{" +
            "p.currentConfigGroup=['BartEnhancement'];if(p.readConfig('Role','')!=='control')return;" +
            "const g=screenGeometry(p.screen);const s=states.find(s=>s.geometry.x===g.x&&s.geometry.y===g.y&&s.geometry.width===g.width&&s.geometry.height===g.height);" +
            "if(!s)return;p.currentConfigGroup=['General'];" +
            "p.writeConfig('unified',s.maximized||s.fullscreen);p.writeConfig('fullscreen',s.fullscreen);p.reloadConfig();" +
            "const floating=!(s.maximized||s.fullscreen);if(p.floating!==floating)p.floating=floating;" +
            "const hiding=s.fullscreen?'autohide':'none';if(p.hiding!==hiding)p.hiding=hiding;});";
        callDBus("org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell", "evaluateScript", js, function(result) {
            publishing = false;
            if (typeof result === "string" && /error/i.test(result)) console.warn("Bart panel state:", result);
            if (pending) { pending = false; schedule(); }
        });
    }
    function watch(w) {
        for (const signal of ["maximizedChanged", "fullScreenChanged", "minimizedChanged", "desktopsChanged", "activitiesChanged", "outputChanged", "windowShown", "windowHidden"]) {
            if (w[signal] && typeof w[signal].connect === "function") w[signal].connect(schedule);
        }
        schedule();
    }
    timer.timeout.connect(function() { publish(); });
    workspace.windowList().forEach(watch);
    workspace.windowAdded.connect(watch);
    workspace.windowRemoved.connect(schedule);
    workspace.windowActivated.connect(schedule);
    workspace.currentDesktopChanged.connect(schedule);
    workspace.currentActivityChanged.connect(schedule);
    workspace.screensChanged.connect(schedule);
    workspace.virtualScreenGeometryChanged.connect(schedule);
    publish();
})();
