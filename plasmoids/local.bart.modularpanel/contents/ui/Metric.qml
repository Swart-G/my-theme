// SPDX-License-Identifier: MIT
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PC
import org.kde.ksysguard.sensors as Sensors
RowLayout {
    id: root
    required property string title
    required property string sensorId
    property bool active: true
    property bool percentage: false
    readonly property real value: sensor.status === Sensors.Sensor.Ready ? Number(sensor.value) : 0
    readonly property string reading: sensor.status === Sensors.Sensor.Ready ? sensor.formattedValue : "—"
    Sensors.Sensor { id: sensor; sensorId: root.active ? root.sensorId : ""; updateRateLimit: 1500 }
    PC.Label { text: root.title; opacity: 0.65; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
    PC.Label { text: root.reading; font.pixelSize: 12 }
}
