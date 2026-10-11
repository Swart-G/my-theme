// SPDX-License-Identifier: MIT
import QtQuick
import QtQuick.Effects
import QtQuick.Layouts
import QtQuick.Controls as Controls
import org.kde.kirigami as Kirigami
import org.kde.plasma.private.keyboardindicator as KeyboardIndicator

Item {
    id: root
    width: 1600; height: 900
    readonly property color accent: config.accent || "#6d793c"
    readonly property color ink: config.textColor || "#c9d4e6"
    property date now: new Date()
    property bool loggingIn: false
    property string errorMessage: ""
    property bool otherUser: false
    readonly property string selectedUser: otherUser ? username.text.trim() : users.currentItem?.loginName ?? ""
    Timer { interval: 1000; running: true; repeat: true; onTriggered: root.now = new Date() }
    KeyboardIndicator.KeyState { id: capsLock; key: Qt.Key_CapsLock }
    function login() {
        if (loggingIn || !selectedUser) return;
        errorMessage = "";
        loggingIn = true;
        sddm.login(selectedUser, password.text, sessions.currentIndex);
    }
    Connections {
        target: sddm
        function onLoginFailed() {
            root.loggingIn = false;
            root.errorMessage = "Не удалось войти. Проверьте пароль.";
            password.selectAll(); password.forceActiveFocus();
        }
        function onLoginSucceeded() { root.errorMessage = ""; }
    }
    Item {
        id: wallpaper
        anchors.fill: parent
        Rectangle { anchors.fill: parent; color: "#151818" }
        Image {
            anchors.fill: parent
            source: config.background.startsWith("/") ? "file://" + config.background : Qt.resolvedUrl(config.background)
            fillMode: Image.PreserveAspectCrop
            sourceSize: Qt.size(root.width,root.height)
        }
        Rectangle { anchors.fill: parent; color: "#20101518" }
        Rectangle {
            anchors.fill: parent
            gradient: Gradient { GradientStop { position: 0; color: "#00101518" } GradientStop { position: 1; color: "#70101518" } }
        }
    }
    component GlassButton: Controls.Button {
        id: button
        implicitHeight: 42
        padding: 12
        font.pixelSize: 13
        contentItem: Text {
            text: button.text; color: root.ink; font: button.font
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 12
            color: button.down ? "#55545f33" : button.hovered ? "#333f482a" : "#1515191c"
            border.width: 1
            border.color: button.activeFocus ? root.accent : "#26c9d4e6"
            Behavior on color { ColorAnimation { duration: 150 } }
        }
    }
    component GlassField: Controls.TextField {
        id: field
        implicitHeight: 48
        color: root.ink; placeholderTextColor: "#8aacb4c4"; font.pixelSize: 15
        leftPadding: 16; rightPadding: 16
        selectionColor: root.accent; selectedTextColor: "white"
        background: Rectangle {
            radius: 12; color: "#58101416"
            border.width: 1; border.color: field.activeFocus ? root.accent : "#26c9d4e6"
            Behavior on border.color { ColorAnimation { duration: 150 } }
        }
    }
    component GlassCombo: Controls.ComboBox {
        id: combo
        implicitHeight: 36; implicitWidth: 160
        padding: 10; rightPadding: 28
        font.pixelSize: 12
        background: Rectangle { radius: 10; color: combo.hovered ? "#25343b2a" : "transparent"; border.color: combo.activeFocus ? root.accent : "transparent" }
        contentItem: Text { text: combo.displayText; color: root.ink; font: combo.font; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
        indicator: Text { text: "⌄"; color: root.ink; font.pixelSize: 17; x: combo.width-width-10; anchors.verticalCenter: parent.verticalCenter }
        popup: Controls.Popup {
            objectName: "glass-popup"
            y: combo.height + 8; width: Math.max(combo.width,220); padding: 6
            implicitHeight: Math.min(300,contentItem.implicitHeight+12)
            background: Rectangle { radius: 14; color: "#f0151818"; border.color: "#38c9d4e6" }
            contentItem: ListView {
                clip: true; implicitHeight: contentHeight
                model: combo.popup.visible ? combo.delegateModel : null
                currentIndex: combo.highlightedIndex
            }
        }
        delegate: Controls.ItemDelegate {
            required property int index
            width: Math.max(combo.width,220)-12; height: 38
            text: combo.textAt(index)
            contentItem: Text { text: parent.text; color: root.ink; font.pixelSize: 13; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
            background: Rectangle { radius: 8; color: parent.highlighted ? "#66545f33" : "transparent" }
            highlighted: combo.highlightedIndex === index
        }
    }
    GlassPanel {
        id: topbar
        wallpaper: wallpaper
        x: 16; y: 12; width: parent.width-32; height: 48; radius: 16
        Text {
            anchors.centerIn: parent
            text: root.now.toLocaleDateString(Qt.locale("ru_RU"),"ddd, d MMM") + " · " + Qt.formatTime(root.now,"HH:mm")
            color: root.ink; font.pixelSize: 14
        }
        RowLayout {
            anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 8
            GlassCombo {
                id: keyboardLayouts
                model: keyboard.layouts; textRole: "longName"; currentIndex: keyboard.currentLayout
                visible: keyboard.layouts.length > 1
                implicitWidth: 145
                Accessible.name: "Раскладка клавиатуры"
                onActivated: { keyboard.currentLayout=currentIndex; password.forceActiveFocus(); }
            }
            GlassCombo {
                id: sessions; objectName: "sessions"
                model: sessionModel; textRole: "name"; currentIndex: Math.max(0,sessionModel.lastIndex)
                implicitWidth: 170
                Accessible.name: "Сеанс рабочего стола"
                onActivated: password.forceActiveFocus()
            }
        }
    }
    Column {
        id: content
        anchors.horizontalCenter: parent.horizontalCenter
        y: Math.max(88,(root.height-height)/2+22)
        width: Math.min(460,root.width-48)
        spacing: 24
        Column {
            anchors.horizontalCenter: parent.horizontalCenter; spacing: 2
            Text { anchors.horizontalCenter: parent.horizontalCenter; text: Qt.formatTime(root.now,"HH:mm"); font.family: "Noto Sans"; font.pixelSize: 72; font.weight: Font.Light; color: root.ink }
            Text { anchors.horizontalCenter: parent.horizontalCenter; text: root.now.toLocaleDateString(Qt.locale("ru_RU"),"dddd, d MMMM"); font.pixelSize: 15; color: root.ink; opacity: 0.8 }
        }
        GlassPanel {
            id: card
            wallpaper: wallpaper; width: parent.width
            height: form.implicitHeight + 56
            ColumnLayout {
                id: form
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                anchors.margins: 28
                spacing: 14
                ListView {
                    id: users
                    Layout.fillWidth: true; Layout.preferredHeight: 156
                    orientation: ListView.Horizontal; clip: true
                    model: userModel
                    currentIndex: Math.max(0,userModel.lastIndex)
                    visible: !root.otherUser && count>0
                    highlightRangeMode: ListView.StrictlyEnforceRange
                    preferredHighlightBegin: width/2-80; preferredHighlightEnd: preferredHighlightBegin
                    interactive: count>1
                    delegate: Item {
                        id: user
                        required property var model
                        required property int index
                        readonly property string loginName: model.name
                        width: 160; height: 156
                        opacity: ListView.isCurrentItem ? 1 : 0.45
                        Rectangle {
                            id: avatar
                            anchors.horizontalCenter: parent.horizontalCenter
                            y: 6; width: 86; height: 86; radius: 43
                            color: "#304b552f"; border.color: root.accent; border.width: 1
                            Image {
                                id: face; sourceSize: Qt.size(86,86); anchors.fill: parent; anchors.margins: 3
                                source: user.model.icon || ""; fillMode: Image.PreserveAspectCrop
                                layer.enabled: true; layer.effect: MultiEffect { maskEnabled: true; maskSource: avatarMask }
                            }
                            Rectangle { id: avatarMask; anchors.fill: face; radius: width/2; visible: false; layer.enabled: true }
                            Text {
                                anchors.centerIn: parent
                                visible: face.status !== Image.Ready
                                text: (user.model.realName || user.loginName).charAt(0).toUpperCase()
                                font.pixelSize: 30; font.weight: Font.Light; color: root.ink
                            }
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter; y: 109
                            width: parent.width; horizontalAlignment: Text.AlignHCenter
                            text: user.model.realName || user.loginName; color: root.ink; font.pixelSize: 21
                            elide: Text.ElideRight
                        }
                        MouseArea { anchors.fill: parent; onClicked: { users.currentIndex=user.index; password.clear(); password.forceActiveFocus(); } }
                    }
                    onCurrentIndexChanged: { if(password)password.clear(); }
                    Keys.onLeftPressed: decrementCurrentIndex()
                    Keys.onRightPressed: incrementCurrentIndex()
                }
                Text { Layout.alignment: Qt.AlignHCenter; text: "Вход в систему"; font.pixelSize: 22; color: root.ink; visible: root.otherUser }
                GlassField { id: username; objectName: "username"; Layout.fillWidth: true; visible: root.otherUser; placeholderText: "Имя пользователя"; text: userModel.lastUser || ""; onAccepted: password.forceActiveFocus(); Accessible.name: "Имя пользователя" }
                GlassField {
                    id: password; objectName: "password"
                    Layout.fillWidth: true; placeholderText: "Пароль"
                    echoMode: TextInput.Password; focus: true; enabled: !root.loggingIn
                    Accessible.name: "Пароль"
                    onAccepted: root.login()
                    Keys.onEscapePressed: { clear(); root.errorMessage=""; }
                }
                Text {
                    Layout.fillWidth: true; Layout.preferredHeight: 20
                    horizontalAlignment: Text.AlignHCenter; color: root.errorMessage ? "#ecb5b5" : root.ink
                    text: root.errorMessage || (capsLock.locked ? "Caps Lock включён" : "")
                    font.pixelSize: 12; textFormat: Text.PlainText; elide: Text.ElideRight
                    Accessible.role: Accessible.AlertMessage
                }
                GlassButton {
                    Layout.fillWidth: true; implicitHeight: 46
                    text: root.loggingIn ? "Вход…" : "Войти"
                    enabled: !root.loggingIn && root.selectedUser.length>0
                    background: Rectangle { radius: 12; color: parent.down ? "#56622e" : parent.hovered ? "#7c8949" : root.accent; border.color: "#3ec9d4e6" }
                    font.pixelSize: 15
                    onClicked: root.login()
                }
                Controls.Button {
                    Layout.alignment: Qt.AlignHCenter; implicitHeight: 28
                    text: root.otherUser ? "Вернуться к пользователю" : "Другой пользователь"
                    visible: userModel.count>0; enabled: !root.loggingIn
                    background: Item {}
                    contentItem: Text { text: parent.text; color: root.ink; opacity: parent.hovered?1:0.65; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    onClicked: { root.otherUser=!root.otherUser; password.clear(); Qt.callLater(()=>root.otherUser ? username.forceActiveFocus() : password.forceActiveFocus()); }
                }
            }
        }
        Row {
            anchors.horizontalCenter: parent.horizontalCenter; spacing: 10
            GlassButton { text: "Сон"; visible: sddm.canSuspend; enabled: !root.loggingIn; onClicked: sddm.suspend() }
            GlassButton { text: "Перезагрузка"; visible: sddm.canReboot; enabled: !root.loggingIn; onClicked: sddm.reboot() }
            GlassButton { text: "Выключение"; visible: sddm.canPowerOff; enabled: !root.loggingIn; onClicked: sddm.powerOff() }
        }
    }
    Component.onCompleted: {
        if(userModel.count===0)root.otherUser=true;
        Qt.callLater(()=>root.otherUser ? username.forceActiveFocus() : password.forceActiveFocus());
    }
}
