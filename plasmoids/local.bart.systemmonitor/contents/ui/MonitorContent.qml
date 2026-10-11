import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PC

ColumnLayout {
    id: root
    property string temperatureSensor: ""
    property string gpuSensor: ""
    property bool showNetwork: true
    property int refreshMs: 1500
    property bool active: true
    property bool showCpu: true
    property bool showMemory: true
    property string swapSensor: ""
    readonly property color accent: Kirigami.Theme.highlightColor
    readonly property color foreground: Kirigami.Theme.textColor
    readonly property string cpuReading: cpu.reading
    readonly property string memoryReading: memory.reading
    Layout.minimumWidth: 220
    Layout.minimumHeight: 150
    Layout.preferredWidth: 300
    Layout.preferredHeight: implicitHeight
    spacing: 8
    PC.Label { text: qsTr("Ресурсы системы"); font.bold: true; color: root.foreground }
    SensorRow { id: cpu; label: "CPU"; sensorId: "cpu/all/usage"; visible: root.showCpu; active: root.active && root.showCpu; refreshMs: root.refreshMs; Layout.fillWidth: true }
    SensorRow { id: memory; label: "RAM"; sensorId: "memory/physical/usedPercent"; visible: root.showMemory; active: root.active && root.showMemory; refreshMs: root.refreshMs; Layout.fillWidth: true }
    SensorRow { label: qsTr("Температура CPU"); sensorId: root.temperatureSensor; active: root.active; visible: sensorId !== "" && available; refreshMs: root.refreshMs; Layout.fillWidth: true }
    SensorRow { label: "GPU"; sensorId: root.gpuSensor; active: root.active; visible: sensorId !== "" && available; refreshMs: root.refreshMs; Layout.fillWidth: true }
    SensorRow { label: "SWAP"; sensorId: root.swapSensor; active: root.active; visible: sensorId !== "" && available; refreshMs: root.refreshMs; Layout.fillWidth: true }
    SensorRow { label: qsTr("Приём сети"); sensorId: "network/all/download"; active: root.active && root.showNetwork; visible: root.showNetwork && available; graphMaximum: 0; refreshMs: root.refreshMs; Layout.fillWidth: true }
    SensorRow { label: qsTr("Передача сети"); sensorId: "network/all/upload"; active: root.active && root.showNetwork; visible: root.showNetwork && available; graphMaximum: 0; refreshMs: root.refreshMs; Layout.fillWidth: true }
    Item { Layout.fillHeight: true }
}
