// SPDX-License-Identifier: MIT
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PC
import org.kde.kirigami as Kirigami
import org.kde.taskmanager as TaskManager
import org.kde.plasma.workspace.dbus as DBus

PlasmoidItem {
    id: root
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    preferredRepresentation: fullRepresentation
    Layout.minimumWidth: desktops.numberOfDesktops * 28 - 4
    Layout.minimumHeight: 24
    property var currentDesktopId
    function updateCurrentDesktop() {
        currentDesktopId = desktops.currentDesktopByScreenGeometry(Plasmoid.containment.screenGeometry);
    }
    Component.onCompleted: updateCurrentDesktop()
    TaskManager.VirtualDesktopInfo { id: desktops }
    Connections {
        target: desktops
        function onCurrentDesktopChanged() { root.updateCurrentDesktop(); }
        function onCurrentDesktopForScreenChanged(screenName) { root.updateCurrentDesktop(); }
        function onDesktopIdsChanged() { root.updateCurrentDesktop(); }
    }
    Connections {
        target: Plasmoid.containment
        function onScreenGeometryChanged() { root.updateCurrentDesktop(); }
    }
    fullRepresentation: Item {
    // Accumulate high-resolution wheel ticks; one notch switches one desktop.
    WheelHandler {
        target: null
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        property real remainder: 0
        onWheel: event => {
            const delta = event.angleDelta.y !== 0 ? event.angleDelta.y : event.angleDelta.x;
            if (delta === 0) return;
            event.accepted = true;
            remainder += delta;
            const steps = Math.trunc(remainder / 120);
            if (steps === 0) return;
            remainder -= steps * 120;
            const ids = desktops.desktopIds;
            const currentIndex = ids.indexOf(root.currentDesktopId);
            if (currentIndex < 0 || ids.length < 2) return;
            const next = Math.max(0, Math.min(ids.length - 1, currentIndex - steps));
            if (next === currentIndex) return;
            DBus.SessionBus.asyncCall({service: "org.kde.KWin", path: "/KWin", iface: "org.kde.KWin", member: "setCurrentDesktop", arguments: [new DBus.int32(next + 1)]});
        }
    }

        implicitWidth: desktops.numberOfDesktops * 28 - 4
        implicitHeight: 24
        Row {
            anchors.centerIn: parent
            spacing: 4
            Repeater {
                model: desktops.desktopIds
                PC.ToolButton {
                    id: button
                    required property var modelData
                    required property int index
                    readonly property bool selected: root.currentDesktopId === modelData
                    width: 24; height: 24
                    text: String(index + 1)
                    Accessible.name: desktops.desktopNames[index] || qsTr("Рабочий стол %1").arg(index + 1)
                    contentItem: PC.Label {
                        text: button.text
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                        font.pixelSize: 11; font.bold: button.selected
                        color: button.selected ? Kirigami.Theme.textColor : Qt.alpha(Kirigami.Theme.textColor,0.65)
                    }
                    background: Rectangle {
                        radius: 7
                        color: Qt.alpha(Kirigami.Theme.highlightColor,button.selected ? 0.35 : button.hovered ? 0.12 : 0)
                        border.color: Qt.alpha(Kirigami.Theme.highlightColor,button.selected ? 0.75 : button.activeFocus ? 0.55 : 0)
                        Behavior on color { ColorAnimation { duration: 150 } }
                    }
                    onClicked: DBus.SessionBus.asyncCall({service:"org.kde.KWin",path:"/KWin",iface:"org.kde.KWin",member:"setCurrentDesktop",arguments:[new DBus.int32(button.index + 1)]})
                }
            }
        }
    }
}
