// SPDX-License-Identifier: MIT
import QtQuick
import QtQuick.Effects
Rectangle {
    id: panel
    required property Item wallpaper
    property color tint: "#7a151818"
    property color outline: "#28c9d4e6"
    color: "transparent"
    radius: 20
    border.color: outline
    border.width: 1
    readonly property point backgroundOffset: {
        wallpaper.width; wallpaper.height; parent.width; parent.height; x; y;
        return mapToItem(wallpaper, 0, 0);
    }
    ShaderEffectSource {
        id: backdrop
        visible: false
        sourceItem: panel.wallpaper
        sourceRect: Qt.rect(panel.backgroundOffset.x, panel.backgroundOffset.y, panel.width, panel.height)
        textureSize: Qt.size(Math.max(1,panel.width),Math.max(1,panel.height))
        live: false
    }
    Rectangle { id: roundedMask; anchors.fill: parent; radius: panel.radius; color: "white"; layer.enabled: true; visible: false }
    MultiEffect {
        anchors.fill: parent
        source: backdrop
        blurEnabled: true; blurMax: 64; blur: 1.0
        autoPaddingEnabled: false
        maskEnabled: true; maskSource: roundedMask
    }
    Rectangle { anchors.fill: parent; radius: panel.radius; color: panel.tint; border.color: panel.outline; border.width: 1 }
}
