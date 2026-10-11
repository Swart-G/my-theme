// SPDX-License-Identifier: MIT
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.ksvg as KSvg
import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PC

ContainmentItem {
    id: root
    // Native panel effects keep the blur region valid after resizes and restarts.
    Plasmoid.backgroundHints: PlasmaCore.Types.StandardBackground
    Layout.fillWidth: true
    Layout.preferredWidth: 1920
    Layout.preferredHeight: moduleHeight + edgeMargin * 2
    readonly property int moduleHeight: Plasmoid.configuration.moduleHeight
    readonly property int edgeMargin: Plasmoid.configuration.edgeMargin
    readonly property bool unified: true
    readonly property bool windowCoversScreen: Plasmoid.configuration.unified || Plasmoid.configuration.fullscreen
    property real joined: unified ? 1 : 0
    property var hosts: []
    property Item toolBox
    readonly property real rightLimit: Math.max(100, (width - clockSurface.width) / 2 - edgeMargin * 3 - 20)
    readonly property bool overflow: rightRow.width > rightLimit
    Behavior on joined { NumberAnimation { duration: Kirigami.Units.longDuration; easing.type: Easing.OutCubic } }
    // Plasma's existing "Focus Panels" shortcut (Meta+Alt+P) is the fullscreen fallback.
    Plasmoid.onActivated: {
        Plasmoid.status = Plasmoid.status === PlasmaCore.Types.AcceptingInputStatus
            ? PlasmaCore.Types.PassiveStatus : PlasmaCore.Types.AcceptingInputStatus;
    }

    function closeOtherPopups(keep) {
        if (keep) drawerWanted = false;
        for (const host of hosts) {
            const item = host.applet;
            if (item === keep) continue;
            if (host.isTray) item.systemTrayState.expanded = false;
            else if (!host.isTasks && !host.dashboardOnly) item.expanded = false;
        }
    }
    function addApplet(applet) {
        if (hosts.some(h => h.applet.plasmoid.id === applet.id)) return;
        const item = root.itemFor(applet);
        if (!item) return;
        const parent = ["local.bart.desktopnumbers", "org.kde.plasma.icontasks", "org.kde.plasma.kickoff"].includes(applet.pluginName) ? leftRow
            : applet.pluginName === "org.kde.plasma.digitalclock" ? centerRow : rightRow;
        const host = hostComponent.createObject(parent, {applet: item, panelRoot: root});
        hosts = hosts.concat(host);
    }
    function reorderApplets(order) {
        // Keep the panel scripting API's index/reorder support.
        const rank = id => { const n = order.indexOf(String(id)); return n < 0 ? 9999 : n; };
        const sorted = hosts.slice().sort((a,b) => rank(a.applet.plasmoid.id) - rank(b.applet.plasmoid.id));
        for (const host of sorted) {
            const group = host.parent;
            host.parent = null;
            host.parent = group;
        }
    }
    function syncApplets() {
        Containment.applets.forEach(root.addApplet);
        reorderApplets(String(Plasmoid.configuration.AppletOrder).split(";"));
    }
    Containment.onAppletAdded: applet => Qt.callLater(root.syncApplets)
    Containment.onAppletRemoved: applet => {
        const host = hosts.find(h => h.applet.plasmoid.id === applet.id);
        if (host) { hosts = hosts.filter(h => h !== host); host.destroy(); }
    }
    Component.onCompleted: Qt.callLater(root.syncApplets)
    Timer {
        interval: 500
        running: true
        onTriggered: {
            root.syncApplets();
            Plasmoid.configuration.health = JSON.stringify({width: root.width, height: root.height,
                hosts: root.hosts.map(h=>({id:h.applet.plasmoid.id,plugin:h.plugin,width:h.width,height:h.height,x:h.mapToItem(root,0,0).x})),
                clockCenter: centerRow.x+centerRow.width/2, rightStart: rightSurface.x, covered: root.windowCoversScreen, contentCenter: leftRow.y+leftRow.height/2});
        }
    }
    Component { id: hostComponent; AppletHost {} }

    Rectangle {
        id: bar
        anchors.fill: parent
        radius: root.windowCoversScreen ? 0 : 16
        clip: true
        color: Qt.alpha(Kirigami.Theme.backgroundColor, root.windowCoversScreen ? 0.85 : 0.28)
        Behavior on color { ColorAnimation { duration: 240; easing.type: Easing.InOutQuad } }
        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: "#05080c"
            opacity: root.windowCoversScreen ? 0.24 : 0
            Behavior on opacity { NumberAnimation { duration: 240; easing.type: Easing.InOutQuad } }
        }
        Rectangle {
            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
            visible: root.windowCoversScreen
            height: 1; color: Qt.alpha(Kirigami.Theme.textColor, root.windowCoversScreen ? 0.06 : 0.10)
        }
    }
    component ModuleSurface: KSvg.FrameSvgItem {
        imagePath: "widgets/panel-background"
        prefix: ["floating", ""]
        opacity: 1 - root.joined
        height: root.moduleHeight
        y: root.edgeMargin
    }
    ModuleSurface {
        id: leftSurface
        x: root.edgeMargin
        width: leftRow.width + 20
    }
    ModuleSurface {
        id: clockSurface
        x: (root.width - width) / 2
        width: centerRow.width + 20
    }
    ModuleSurface {
        id: rightSurface
        x: root.width - width - root.edgeMargin
        width: Math.min(rightRow.width, root.rightLimit) + 20
    }
    Row {
        id: leftRow
        x: leftSurface.x + 10
        y: (root.height - height) / 2
        height: root.moduleHeight - 8
        spacing: Kirigami.Units.smallSpacing
    }
    Row {
        id: centerRow
        x: (root.width - width) / 2
        y: (root.height - height) / 2
        height: root.moduleHeight - 8
    }
    Flickable {
        id: rightViewport
        x: rightSurface.x + 10 + (root.overflow ? 28 : 0)
        y: (root.height - height) / 2
        width: rightSurface.width - 20 - (root.overflow ? 56 : 0)
        height: root.moduleHeight - 8
        contentWidth: rightRow.width
        contentHeight: height
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.HorizontalFlick
        Row {
            id: rightRow
            height: root.moduleHeight - 8
            spacing: Kirigami.Units.smallSpacing
        }
    }
    PC.ToolButton {
        visible: root.overflow
        x: rightSurface.x + 6
        y: (root.height - height) / 2
        width: 28; height: root.moduleHeight - 8
        icon.name: "go-previous"
        enabled: rightViewport.contentX > 0
        onClicked: rightViewport.contentX = Math.max(0,rightViewport.contentX-rightViewport.width)
        Accessible.name: qsTr("Предыдущие значки управления")
    }
    PC.ToolButton {
        visible: root.overflow
        x: rightSurface.x + rightSurface.width - 34
        y: (root.height - height) / 2
        width: 28; height: root.moduleHeight - 8
        icon.name: "go-next"
        enabled: rightViewport.contentX + rightViewport.width < rightViewport.contentWidth
        onClicked: rightViewport.contentX = Math.min(rightViewport.contentWidth-rightViewport.width,rightViewport.contentX+rightViewport.width)
        Accessible.name: qsTr("Следующие значки управления")
    }
    property bool drawerWanted: false
    property real drawerProgress: drawerWanted ? 1 : 0
    readonly property bool popupBusy: hosts.some(h => h.isTray ? h.applet.systemTrayState.expanded : (!h.isTasks && !h.dashboardOnly && h.applet.expanded))
    Behavior on drawerProgress { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
    function scheduleDrawerClose() {
        openDelay.stop();
        closeDelay.restart();
    }
    // Observe only the clock area; passive hover leaves applet clicks intact.
    Item {
        x: clockSurface.x
        width: clockSurface.width
        height: root.height
        HoverHandler {
            id: centerHover
            onHoveredChanged: {
                if (hovered) { closeDelay.stop(); if (!root.popupBusy) openDelay.restart(); }
                else root.scheduleDrawerClose();
            }
        }
    }
    Timer { id: openDelay; interval: 280; onTriggered: { if (centerHover.hovered && !root.popupBusy) root.drawerWanted = true; } }
    Timer { id: closeDelay; interval: 350; onTriggered: { if (!centerHover.hovered && !drawerHover.hovered) root.drawerWanted = false; } }
    PlasmaCore.Dialog {
        id: drawer
        visualParent: root
        location: PlasmaCore.Types.TopEdge
        type: PlasmaCore.Dialog.AppletPopup
        flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
        hideOnWindowDeactivate: false
        visible: root.drawerWanted || root.drawerProgress > 0.001
        mainItem: Item {
            width: Math.min(1380, root.width - 40)
            height: Math.max(1, 550 * root.drawerProgress)
            clip: true
            HoverDashboard {
                width: parent.width; height: 550
                y: -18 * (1-root.drawerProgress)
                opacity: root.drawerProgress
                cpuModel: Plasmoid.configuration.cpuModel
                active: drawer.visible
                screenGeometry: Plasmoid.containment.screenGeometry
            }
            HoverHandler {
                id: drawerHover
                onHoveredChanged: {
                    if (hovered) closeDelay.stop();
                    else root.scheduleDrawerClose();
                }
            }
        }
    }

}
