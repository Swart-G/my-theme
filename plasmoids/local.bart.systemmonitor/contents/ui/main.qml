import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PC

PlasmoidItem {
    id: root
    Plasmoid.backgroundHints: PlasmaCore.Types.DefaultBackground
    preferredRepresentation: compactRepresentation
    toolTipMainText: qsTr("Ресурсы системы")
    toolTipSubText: qsTr("CPU, память, GPU, температуры и сеть")
    compactRepresentation: PC.ToolButton {
        icon.name: "utilities-system-monitor"
        onClicked: root.expanded = !root.expanded
        Accessible.name: root.toolTipMainText
    }
    fullRepresentation: MonitorContent {
        Layout.minimumWidth: 300
        Layout.preferredWidth: 360
        Layout.preferredHeight: implicitHeight
        showCpu: Plasmoid.configuration.showCpu
        showMemory: Plasmoid.configuration.showMemory
        swapSensor: Plasmoid.configuration.swapSensor
        temperatureSensor: Plasmoid.configuration.temperatureSensor
        gpuSensor: Plasmoid.configuration.gpuSensor
        showNetwork: Plasmoid.configuration.showNetwork
        refreshMs: Plasmoid.configuration.refreshMs
        active: root.expanded
    }
}
