// SPDX-License-Identifier: MIT
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PC
import org.kde.plasma.private.mpris as Mpris
import org.kde.taskmanager as TaskManager
import org.kde.plasma.workspace.dbus as DBus
Item {
    id: root
    property string cpuModel: "CPU"
    property bool active: false
    property rect screenGeometry
    property date now: new Date()
    readonly property var player: players.currentPlayer
    readonly property bool playing: player?.playbackStatus === Mpris.PlaybackStatus.Playing
    Mpris.Mpris2Model { id: players }
    property var currentDesktopId
    function updateCurrentDesktop() {
        currentDesktopId = desktops.currentDesktopByScreenGeometry(root.screenGeometry);
    }
    onScreenGeometryChanged: updateCurrentDesktop()
    Component.onCompleted: updateCurrentDesktop()
    TaskManager.VirtualDesktopInfo { id: desktops }
    Connections {
        target: desktops
        function onCurrentDesktopChanged() { root.updateCurrentDesktop(); }
        function onCurrentDesktopForScreenChanged(screenName) { root.updateCurrentDesktop(); }
        function onDesktopIdsChanged() { root.updateCurrentDesktop(); }
    }
    Timer { interval: 1000; running: root.active; repeat: true; onTriggered: { root.now = new Date(); if(root.playing) root.player?.updatePosition(); } }
    function switchDesktop(index) {
        DBus.SessionBus.asyncCall({service:"org.kde.KWin",path:"/KWin",iface:"org.kde.KWin",member:"setCurrentDesktop",arguments:[new DBus.int32(index+1)]});
    }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 18; spacing: 14
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 100
            Column {
                anchors.centerIn: parent
                spacing: 0
                PC.Label {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: Qt.formatTime(root.now, "HH:mm")
                    font.pixelSize: 64; font.weight: Font.Light
                }
                PC.Label {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: root.now.toLocaleDateString(Qt.locale("ru_RU"), "dddd, d MMMM")
                    font.pixelSize: 15; opacity: 0.75
                }
            }
        }
        RowLayout {
            Layout.alignment: Qt.AlignHCenter; spacing: 10
            Repeater {
                model: desktops.desktopIds
                GlassCard {
                    id: tab
                    required property string modelData
                    required property int index
                    readonly property bool selected: root.currentDesktopId === modelData
                    Layout.preferredWidth: Math.min(156, (root.width-100)/Math.max(1,desktops.numberOfDesktops))
                    Layout.preferredHeight: 66
                    color: Qt.alpha(Kirigami.Theme.backgroundColor, selected ? 0.58 : 0.28)
                    border.color: selected ? Kirigami.Theme.highlightColor : Qt.alpha(Kirigami.Theme.textColor,0.16)
                    border.width: selected ? 2 : 1
                    Column {
                        anchors.centerIn: parent; spacing: 6
                        PC.Label {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: desktops.desktopNames[tab.index] || qsTr("Desktop %1").arg(tab.index+1)
                            font.pixelSize: 13; font.bold: tab.selected
                        }
                        Row {
                            anchors.horizontalCenter: parent.horizontalCenter; spacing: 5
                            Repeater {
                                model: TaskManager.TasksModel {
                                    virtualDesktop: tab.modelData; filterByVirtualDesktop: true
                                    filterByScreen: true; screenGeometry: root.screenGeometry
                                }
                                Kirigami.Icon {
                                    required property var model
                                    required property int index
                                    visible: index < 6
                                    width: visible ? 20 : 0; height: 20; source: model.decoration
                                }
                            }
                            Kirigami.Icon { source: "view-grid"; width: 20; height: 20; opacity: 0.45; visible: parent.children.length < 3 }
                        }
                    }
                    MouseArea { anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.switchDesktop(tab.index) }
                }
            }
        }
        GlassCard {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: Math.min(680,root.width-50); Layout.preferredHeight: 80
            RowLayout {
                anchors.fill: parent; anchors.margins: 12; spacing: 12
                Item {
                    Layout.preferredWidth: 52; Layout.preferredHeight: 52
                    Image { id: artwork; anchors.fill: parent; source: root.player?.artUrl ?? ""; asynchronous: true; fillMode: Image.PreserveAspectCrop }
                    Kirigami.Icon { anchors.fill: parent; visible: artwork.status !== Image.Ready; source: "media-optical-audio"; opacity: 0.65 }
                }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 1
                    PC.Label { Layout.fillWidth: true; text: root.player?.track || qsTr("Ready when you are"); font.bold: true; elide: Text.ElideRight }
                    PC.Label { Layout.fillWidth: true; text: root.player?.artist || qsTr("Play music or video to see it here"); opacity: 0.6; font.pixelSize: 12; elide: Text.ElideRight }
                    PC.Slider { Layout.fillWidth: true; Layout.preferredHeight: 16; from: 0; to: Math.max(1,root.player?.length ?? 0); value: root.player?.position ?? 0; enabled: root.player?.canSeek ?? false; onMoved: root.player.position = value }
                }
                PC.ToolButton { icon.name: "media-skip-backward"; enabled: root.player?.canGoPrevious ?? false; onClicked: root.player.Previous() }
                PC.ToolButton { icon.name: root.playing ? "media-playback-pause" : "media-playback-start"; enabled: root.playing ? (root.player?.canPause ?? false) : (root.player?.canPlay ?? false); onClicked: root.playing ? root.player.Pause() : root.player.Play() }
                PC.ToolButton { icon.name: "media-skip-forward"; enabled: root.player?.canGoNext ?? false; onClicked: root.player.Next() }
            }
        }
        Item { Layout.fillHeight: true; Layout.minimumHeight: 4 }
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 202; spacing: 10
            SystemCard {
                Layout.fillWidth: true; Layout.preferredWidth: 1; Layout.fillHeight: true; active: root.active
                title: "CPU"; accent: "#61c8e3"; sensorId: "cpu/all/usage"; subtitle: root.cpuModel; ring: true
                metrics: [{title:"Frequency",id:"cpu/cpu0/frequency"},{title:"Temperature",id:"cpu/cpu0/temperature"}]
            }
            SystemCard {
                Layout.fillWidth: true; Layout.preferredWidth: 1; Layout.fillHeight: true; active: root.active
                title: "GPU"; accent: "#58cb91"; sensorId: "gpu/all/usage"; nameId: "gpu/gpu0/name"; ring: true
                metrics: [{title:"VRAM",id:"gpu/all/usedVram"},{title:"Temperature",id:"gpu/gpu0/temperature"}]
            }
            SystemCard {
                Layout.fillWidth: true; Layout.preferredWidth: 1; Layout.fillHeight: true; active: root.active
                title: "MEMORY"; accent: "#c295e4"; sensorId: "memory/physical/usedPercent"; subtitle: "Physical memory"
                metrics: [{title:"Used",id:"memory/physical/used"},{title:"Total",id:"memory/physical/total"}]
            }
            SystemCard {
                Layout.fillWidth: true; Layout.preferredWidth: 1; Layout.fillHeight: true; active: root.active
                title: "STORAGE"; accent: "#eeb56b"; sensorId: "disk/all/usedPercent"; subtitle: "All mounted volumes"
                metrics: [{title:"Used",id:"disk/all/used"},{title:"Read",id:"disk/all/read"},{title:"Write",id:"disk/all/write"}]
            }
            SystemCard {
                Layout.fillWidth: true; Layout.preferredWidth: 1; Layout.fillHeight: true; active: root.active
                title: "NETWORK"; accent: "#71b3ec"; sensorId: "network/all/download"; percentage: false; subtitle: "All interfaces"
                metrics: [{title:"Download",id:"network/all/download"},{title:"Upload",id:"network/all/upload"}]
            }
        }
    }
}
