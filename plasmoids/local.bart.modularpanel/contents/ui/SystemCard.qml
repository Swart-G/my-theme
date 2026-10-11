// SPDX-License-Identifier: MIT
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PC
import org.kde.ksysguard.sensors as Sensors
GlassCard {
    id: root
    required property string title
    required property string sensorId
    property string nameId: ""
    property string subtitle: ""
    required property color accent
    required property var metrics
    property bool active: true
    property bool percentage: true
    property bool ring: false
    property var history: []
    readonly property real reading: sensor.status === Sensors.Sensor.Ready ? Number(sensor.value) : 0
    Sensors.Sensor { id: sensor; sensorId: root.active ? root.sensorId : ""; updateRateLimit: 1500 }
    Sensors.Sensor { id: deviceName; sensorId: root.active ? root.nameId : ""; updateRateLimit: 10000 }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 14; spacing: 8
        RowLayout {
            Layout.fillWidth: true
            PC.Label { text: root.title; color: root.accent; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.5; Layout.fillWidth: true }
            PC.Label { visible: !root.ring; text: root.percentage ? Math.round(root.reading) + "%" : sensor.formattedValue; font.pixelSize: 22; font.weight: Font.Light }
        }
        PC.Label {
            Layout.fillWidth: true
            text: root.nameId && deviceName.status === Sensors.Sensor.Ready ? String(deviceName.value) : root.subtitle
            font.pixelSize: 12; opacity: 0.8; elide: Text.ElideRight
        }
        Rectangle {
            visible: !root.ring
            Layout.fillWidth: true; Layout.preferredHeight: 4; radius: 2
            color: Qt.alpha(Kirigami.Theme.textColor, 0.12)
            Rectangle { width: parent.width * Math.min(1, Math.max(0, root.reading / 100)); height: parent.height; radius: 2; color: root.accent; visible: root.percentage }
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 10
            Item {
                visible: root.ring
                Layout.preferredWidth: 78; Layout.preferredHeight: 78
                Canvas {
                    id: gauge
                    anchors.fill: parent
                    Connections { target: root; function onReadingChanged() { gauge.requestPaint(); } }
                    onPaint: {
                        const ctx=getContext("2d");ctx.clearRect(0,0,width,height);
                        const radius=width/2-6,start=Math.PI*0.75,span=Math.PI*1.5;
                        ctx.lineWidth=6;ctx.lineCap="round";
                        ctx.beginPath();ctx.arc(width/2,height/2,radius,start,start+span);ctx.strokeStyle=Qt.alpha(Kirigami.Theme.textColor,0.17);ctx.stroke();
                        if(root.reading>0){ctx.beginPath();ctx.arc(width/2,height/2,radius,start,start+span*Math.min(1,root.reading/100));ctx.strokeStyle=root.accent;ctx.stroke();}
                    }
                }
                PC.Label { anchors.centerIn: parent; text: Math.round(root.reading)+"%"; font.pixelSize: 20; font.weight: Font.Light }
            }
            ColumnLayout {
                Layout.fillWidth: true; spacing: 7
                Repeater {
                    model: root.metrics
                    Metric {
                        required property var modelData
                        title: modelData.title; sensorId: modelData.id; active: root.active
                        Layout.fillWidth: true
                    }
                }
            }
        }
        Item { Layout.fillHeight: true }
        Canvas {
            id: graph
            Layout.fillWidth: true; Layout.preferredHeight: 40
            onWidthChanged: requestPaint()
            onPaint: {
                const ctx = getContext("2d"); ctx.clearRect(0,0,width,height);
                const values = root.history;
                ctx.strokeStyle = Qt.alpha(Kirigami.Theme.textColor,0.10); ctx.lineWidth=1;
                ctx.beginPath(); ctx.moveTo(0,height-2); ctx.lineTo(width,height-2); ctx.stroke();
                if (values.length < 2) return;
                const max = root.percentage ? 100 : Math.max(1,...values) * 1.1;
                ctx.beginPath();
                for (let i=0;i<values.length;i++) {
                    const x = width*i/59, y = height-3-Math.max(0,Math.min(1,values[i]/max))*(height-6);
                    if (i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
                }
                ctx.lineWidth=1.6; ctx.strokeStyle=root.accent; ctx.stroke();
            }
        }
    }
    Timer {
        interval: 1500; running: root.active; repeat: true
        onTriggered: {
            if (sensor.status !== Sensors.Sensor.Ready) return;
            root.history = root.history.length ? root.history.slice(-59).concat([root.reading]) : Array(60).fill(root.reading); graph.requestPaint();
        }
    }
}
