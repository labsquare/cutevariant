import QtQuick 2.0
import QtQuick.Controls 2


Pane {

Column{
RangeSlider {
    from: 1
    to: 100
    first.value: 25
    second.value: 75
}

   Switch {
        text: qsTr("Bluetooth")
    }

       Switch {
        text: qsTr("Bluetooth")
    }


}
}
