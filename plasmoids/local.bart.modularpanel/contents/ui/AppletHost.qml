// SPDX-License-Identifier: MIT
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PC
import org.kde.plasma.plasmoid

Item {
    id: host
    required property Item applet
    required property var panelRoot
    readonly property string plugin: applet.plasmoid.pluginName
    readonly property bool isClock: plugin === "org.kde.plasma.digitalclock"
    readonly property bool isPager: plugin === "local.bart.desktopnumbers"
    readonly property bool isTray: plugin === "org.kde.plasma.systemtray"
    readonly property bool dashboardOnly: ["local.bart.desktopnumbers", "local.bart.systemmonitor", "org.kde.plasma.mediacontroller"].includes(plugin)
    readonly property bool isTasks: plugin === "org.kde.plasma.icontasks"
    readonly property bool hiddenInPanel: (dashboardOnly && !isPager) || isTasks || plugin === "org.kde.plasma.kickoff"
    visible: !hiddenInPanel
    readonly property real naturalWidth: hiddenInPanel ? 0 : isTasks ? Math.min(560, Math.max(180, applet.Layout.minimumWidth)) : isClock ? Math.min(340, Math.max(240, applet.Layout.minimumWidth))
        : isPager ? Math.max(24, applet.Layout.minimumWidth)
        : isTray ? Math.max(32, applet.Layout.minimumWidth) : 32
    property date now: new Date()
    Timer { interval: 1000; running: host.isClock; repeat: true; onTriggered: host.now = new Date() }
    PC.Label {
        anchors.centerIn: parent
        visible: host.isClock
        text: host.now.toLocaleDateString(Qt.locale("ru_RU"), "ddd, d MMM") + " · " + Qt.formatTime(host.now, "HH:mm")
        font.pointSize: 11
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
    width: naturalWidth
    height: panelRoot.moduleHeight - 8
    Component.onCompleted: {
        applet.parent = host;
        applet.anchors.fill = host;
        applet.visible = true;
        if (plugin === "org.kde.plasma.kickoff") {
            applet.anchors.fill = undefined;
            applet.anchors.centerIn = host;
            applet.width = 22;
            applet.height = 22;
        }
        if (isClock) { applet.opacity = 0; applet.toolTipMainText = ""; applet.toolTipSubText = ""; applet.toolTipItem = null; }
    }

    Connections {
        target: host.applet
        function onExpandedChanged() {
            if (!host.isTasks && !host.isTray && !host.dashboardOnly && host.applet.expanded) host.panelRoot.closeOtherPopups(host.applet);
        }
    }
    // The native tray has its own popup coordinator and status propagation.
    Connections {
        target: host.isTray ? host.applet.systemTrayState : null
        function onExpandedChanged() {
            if (host.applet.systemTrayState.expanded) host.panelRoot.closeOtherPopups(host.applet);
        }
    }
}
