import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PC
import org.kde.ksysguard.sensors as Sensors

ColumnLayout {
    id: root
    required property string label
    required property string sensorId
    property int refreshMs: 1500
    property bool active: true
    property real graphMaximum: 100
    property var history: []
    readonly property bool available: sensor.status === Sensors.Sensor.Ready
    readonly property string reading: available ? sensor.formattedValue : "—"
    readonly property color accent: Kirigami.Theme.highlightColor
    readonly property color foreground: Kirigami.Theme.textColor
    spacing: 2
    Sensors.Sensor {
        id: sensor
        sensorId: root.active ? root.sensorId : ""
        updateRateLimit: root.refreshMs
    }
    RowLayout {
        Layout.fillWidth: true
        PC.Label { text: root.label; color: root.foreground; Layout.fillWidth: true }
        PC.Label { text: root.reading; color: root.foreground }
    }
    Canvas {
        id: graph
        Layout.fillWidth: true
        Layout.preferredHeight: 22
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        Connections { target: root; function onAccentChanged() { graph.requestPaint(); } }
        onPaint: {
            const ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);
            if (root.history.length < 2) return;
            const maximum = root.graphMaximum > 0 ? root.graphMaximum : Math.max(1, ...root.history);
            ctx.lineWidth = 1.5;
            ctx.strokeStyle = root.accent;
            ctx.beginPath();
            for (let i = 0; i < root.history.length; ++i) {
                const x = width * i / 59;
                const y = height - 2 - Math.max(0, Math.min(1, root.history[i] / maximum)) * (height - 4);
                if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
            }
            ctx.stroke();
        }
    }
    Timer {
        interval: root.refreshMs
        running: root.active && root.visible
        repeat: true
        onTriggered: {
            if (!root.available) return;
            const values = root.history.slice(-59);
            const value = Number(sensor.value);
            if (!Number.isFinite(value)) return;
            values.push(value);
            root.history = values;
            graph.requestPaint();
        }
    }
}
