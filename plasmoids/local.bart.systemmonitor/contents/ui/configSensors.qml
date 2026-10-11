import QtQuick
import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PC
Kirigami.FormLayout {
    property alias cfg_showCpu: cpu.checked
    property alias cfg_showMemory: memory.checked
    property alias cfg_showNetwork: network.checked
    property alias cfg_temperatureSensor: temperature.text
    property alias cfg_gpuSensor: gpu.text
    property alias cfg_swapSensor: swap.text
    property alias cfg_refreshMs: rate.value
    PC.CheckBox { id: cpu; text: "CPU" }
    PC.CheckBox { id: memory; text: "RAM" }
    PC.CheckBox { id: network; text: qsTr("Сеть") }
    PC.TextField { id: temperature; Kirigami.FormData.label: qsTr("Датчик температуры:") }
    PC.TextField { id: gpu; Kirigami.FormData.label: qsTr("Датчик GPU:") }
    PC.TextField { id: swap; Kirigami.FormData.label: qsTr("Датчик SWAP:") }
    PC.SpinBox { id: rate; from: 1000; to: 10000; stepSize: 500; Kirigami.FormData.label: qsTr("Интервал, мс:") }
    PC.Label { text: qsTr("Идентификаторы датчиков доступны в ./setup.sh --check. Пустое поле скрывает показатель."); wrapMode: Text.WordWrap }
}
