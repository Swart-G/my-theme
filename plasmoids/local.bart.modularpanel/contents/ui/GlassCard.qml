// SPDX-License-Identifier: MIT
import QtQuick
import org.kde.kirigami as Kirigami
Rectangle {
    radius: 14
    color: Qt.alpha(Kirigami.Theme.backgroundColor, 0.40)
    border.width: 1
    border.color: Qt.alpha(Kirigami.Theme.textColor, 0.16)
    Rectangle {
        x: parent.radius; y: 0; width: parent.width - parent.radius * 2; height: 1
        color: Qt.alpha(Kirigami.Theme.textColor, 0.13)
    }
}
